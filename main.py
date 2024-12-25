"""
Essential Points from Assignment:
1. Design and implement a web crawler to discover and list all product URLs across multiple e-commerce websites.
2. Input: A list of domains belonging to various e-commerce platforms.
3. The crawler should handle a minimum of 10 domains and scale to handle potentially hundreds.
4. Key Features:
   - URL Discovery: Intelligently discover product pages considering different URL patterns.
   - Scalability: Handle large websites with deep hierarchies and a large number of products efficiently.
   - Performance: Execute in parallel or asynchronously to minimize runtime.
   - Robustness: Handle edge cases such as infinite scrolling, dynamically loaded content, and variations in URL structures.
5. Output:
   - Github repo with all the code and documentation of the approach.
   - A structured list or file containing all discovered product URLs for each domain.
6. Use Python Fast API.
7. Optimize for concurrency.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import httpx
import asyncio
from bs4 import BeautifulSoup
import re

app = FastAPI(
    title="E-commerce Web Crawler",
    description="A FastAPI application to crawl e-commerce websites and discover product URLs.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

class DomainsInput(BaseModel):
    domains: List[str]

@app.post("/crawl", summary="Crawl Domains", response_description="List of discovered product URLs")
async def crawl_domains(domains_input: DomainsInput):
    """
    Crawl the provided list of e-commerce domains to discover product URLs.

    - **domains**: A list of e-commerce domain URLs to crawl.
    - **returns**: A dictionary with domain names as keys and lists of discovered product URLs as values.
    """
    domains = domains_input.domains
    if len(domains) < 1:
        raise HTTPException(status_code=400, detail="At least 10 domains are required.")
    
    product_urls = await discover_product_urls(domains)
    return product_urls

async def fetch_page(client, url):
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def discover_product_urls(domains: List[str]) -> Dict[str, List[str]]:
    product_url_patterns = [r'/product/', r'/item/', r'/p/', r'/proddetail/', r'/products/']
    product_urls = {}

    async def crawl_page(client, base_url, current_url, visited):
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
        urls = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/'):
                href = base_url.rstrip('/') + href
            elif not href.startswith(base_url):
                logger.debug(f"External URL filtered out: {href}")
                continue
            if any(re.search(pattern, href) for pattern in product_url_patterns):
                logger.info(f"Product URL found: {href}")
                urls.add(href)
            if href not in visited:
                urls.update(await crawl_page(client, base_url, href, visited))
        return urls

    async with httpx.AsyncClient() as client:
        tasks = []
        for domain in domains:
            logger.info(f"Starting crawl for domain: {domain}")
            visited = set()
            tasks.append(crawl_page(client, domain, domain, visited))
        
        results = await asyncio.gather(*tasks)
        for domain, urls in zip(domains, results):
            product_urls[domain] = list(urls)
            logger.info(f"Finished crawl for domain: {domain}. Found {len(product_urls[domain])} product URLs.")
    
    return product_urls
