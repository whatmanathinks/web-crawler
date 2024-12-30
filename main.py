from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from playwright.async_api import async_playwright, Error as PlaywrightError
from helpers.utils import get_best_regex_patterns, clean_and_filter_hrefs
import asyncio
import logging
import re
from settings import CONCURRENT_REQUESTS, DOWNLOAD_DELAY, CONCURRENT_REQUESTS_PER_DOMAIN, PLAYWRIGHT_BROWSER_TYPE, PLAYWRIGHT_LAUNCH_OPTIONS, CRAWLER
import httpx
from bs4 import BeautifulSoup
from helpers.http import fetch_page
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Configure logging
import os

log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    filename='log.txt',  # Log file name
    level=getattr(logging, log_level, logging.DEBUG),  # Log level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
)

logger = logging.getLogger(__name__)


app = FastAPI(
    title="E-commerce Web Crawler",
    description="A FastAPI application to crawl e-commerce websites and discover product URLs.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


url_data = {}

class DomainsInput(BaseModel):
    domains: List[str]

@app.post("/crawl", summary="Crawl Domains", response_description="List of discovered product URLs")
async def crawl_domains(domains_input: DomainsInput):
    domains = domains_input.domains
    try:
        url_data = await discover_product_urls(domains, CRAWLER)
        product_urls = {domain: list(url_data[domain]["domain_product_urls"]) for domain in url_data}
    except Exception as e:
        logger.error(f"Error during crawling: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during crawling.")
    
    return product_urls


async def discover_product_urls(domains: List[str], crawler_type: str) -> Dict[str, List[str]]:
    product_url_patterns = get_best_regex_patterns(domains)
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def sem_managed_crawling(domain, client_or_browser):
        async with semaphore:
            try:
                url_data[domain] = {
                    "urls_to_visit": set([domain]),
                    "domain_product_urls": set(),
                    "visited_urls": set()
                }
                if crawler_type == "playwright":
                    return await manage_crawling_playwright(client_or_browser, domain, product_url_patterns)
                else:
                    visited = set()
                    return await crawl_page_beautifulsoup(client_or_browser, domain, domain, visited, product_url_patterns)
            except Exception as e:
                logger.error(f"Error managing crawling for domain {domain}: {e}")
                return set()

    if crawler_type == "playwright":
        async with async_playwright() as p:
            try:
                browser = await p[PLAYWRIGHT_BROWSER_TYPE].launch(**PLAYWRIGHT_LAUNCH_OPTIONS)
                tasks = [sem_managed_crawling(domain, browser) for domain in domains]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for domain, result in zip(domains, results):
                    if isinstance(result, Exception):
                        logger.error(f"Error during crawling for domain {domain}: {result}")
                        url_data[domain] = {"domain_product_urls": set()}
                    else:
                        url_data[domain] = {"domain_product_urls": result}
            except PlaywrightError as e:
                logger.error(f"Playwright error: {e}")
                raise HTTPException(status_code=500, detail="An error occurred with Playwright.")
            finally:
                if 'browser' in locals():
                    await browser.close()
    else:
        async with httpx.AsyncClient() as client:
            tasks = [sem_managed_crawling(domain, client) for domain in domains]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for domain, result in zip(domains, results):
                if isinstance(result, Exception):
                    logger.error(f"Error during crawling for domain {domain}: {result}")
                    url_data[domain] = {"domain_product_urls": set()}
                else:
                    url_data[domain] = {"domain_product_urls": result}
                logger.info(f"Finished crawl for domain: {domain}. Found {len(url_data[domain]['domain_product_urls'])} product URLs.")

    return url_data


async def manage_crawling_playwright(browser, domain, product_url_patterns):
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS_PER_DOMAIN)
    domain = domain.rstrip('/')
    lock = asyncio.Lock()

    while url_data[domain]["urls_to_visit"]:
        current_urls = list(url_data[domain]["urls_to_visit"])

        async def visit_and_crawl(url):
            async with lock:
                url_data[domain]["visited_urls"].add(url)
                url_data[domain]["urls_to_visit"].remove(url)
            return await crawl_page_playwright(browser, domain, url, product_url_patterns, semaphore, lock)

        tasks = [visit_and_crawl(url) for url in current_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error crawling URL: {result}")

    return list(url_data[domain]["domain_product_urls"])

async def crawl_page_playwright(browser, domain, url, product_url_patterns, semaphore, lock):
    async with semaphore:
        logger.info(f"Starting crawl for URL: {url}")
        page = None
        try:
            page = await browser.new_page()
            retries = 3
            for attempt in range(retries):
                try:
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    break
                except Exception as e:
                    if attempt < retries - 1:
                        logger.warning(f"Retrying {url} due to error: {e}")
                    else:
                        logger.error(f"Failed to load {url} after {retries} attempts")
                        raise

            # Handle infinite scrolling
            max_scroll_attempts = 2  # Further reduced attempts for faster performance
            last_height = await page.evaluate("document.body.scrollHeight")
            for _ in range(max_scroll_attempts):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                await page.wait_for_timeout(int(DOWNLOAD_DELAY))
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            links = await page.query_selector_all("a")
            hrefs = await asyncio.gather(*[link.get_attribute("href") for link in links])
            logger.debug(f"Found hrefs: {hrefs}")
            
            cleaned_hrefs = await clean_and_filter_hrefs(hrefs, domain)

            async with lock:
                for href in cleaned_hrefs:
                    if any(re.search(pattern, href) for pattern in product_url_patterns):
                        href = href.split('?')[0]
                        if href not in url_data[domain]["domain_product_urls"]:
                            logger.info(f"Product URL found: {href}")
                            url_data[domain]["domain_product_urls"].add(href)
                    if href not in url_data[domain]["visited_urls"] and href not in url_data[domain]["urls_to_visit"]:
                        logger.debug(f"Adding href to visit: {href}")
                        url_data[domain]["urls_to_visit"].add(href)
                        
                logger.debug(f"Visited URLs: {url_data[domain]['visited_urls']}")
                logger.debug(f"To be visited: {url_data[domain]['urls_to_visit']}")
                logger.debug(f"Domain product URLs: {url_data[domain]['domain_product_urls']}")

            logger.info(f"Finished crawl for URL: {url}.")
        except Exception as e:
            logger.error(f"Error crawling URL {url}: {e}")
        finally:
            if page:
                await page.close()

async def crawl_page_beautifulsoup(client, base_url, current_url, visited, product_url_patterns):
    if current_url in visited:
        logger.debug(f"URL already visited: {current_url}")
        return set()
    visited.add(current_url)
    logger.info(f"Crawling URL: {current_url}")
    page = await fetch_page(client, current_url)
    if not page:
        logger.warning(f"Failed to fetch page for URL: {current_url}")
        return set()

    soup = BeautifulSoup(page, 'html.parser')
    links = soup.find_all('a', href=True)
    hrefs = [link['href'] for link in links]
    
    cleaned_hrefs = await clean_and_filter_hrefs(hrefs, base_url)

    urls = set()
    for href in cleaned_hrefs:
        if any(re.search(pattern, href) for pattern in product_url_patterns):
            logger.info(f"Product URL found: {href}")
            urls.add(href)
        if href not in visited:
            urls.update(await crawl_page_beautifulsoup(client, base_url, href, visited, product_url_patterns))

    return urls
