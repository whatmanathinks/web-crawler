from urllib.parse import urlparse, urljoin, urlsplit
import logging

logger = logging.getLogger(__name__)

async def clean_and_filter_hrefs(hrefs, domain):
    cleaned_hrefs = set()
    for href in hrefs:
        if href is None:
            continue
        if not is_same_domain(domain, href):
            continue
        href = href.split('#')[0]
        href = href.rstrip('/')
        href = format_url(domain, href)
        cleaned_hrefs.add(href)
    
    logger.debug(f"Cleaned hrefs: {cleaned_hrefs}")
    
    # Filter out non-crawlable URLs
    cleaned_hrefs = {href for href in cleaned_hrefs if is_crawlable(href)}
    logger.debug(f"Filtered hrefs: {cleaned_hrefs}")
    
    return cleaned_hrefs

def is_same_domain(domain: str, url: str) -> bool:

    domain_parts = urlparse(domain)
    # If the URL is relative, convert it to an absolute URL using the domain
    if not urlparse(url).netloc:
        url = urljoin(domain, url)
    
    url_parts = urlparse(url)

    # Normalize the netloc by removing 'www.' if present
    domain_netloc = domain_parts.netloc.lstrip('www.')
    url_netloc = url_parts.netloc.lstrip('www.')

    return domain_netloc == url_netloc

def format_url(domain: str, url: str) -> str:
    """
    Format the given URL to match the original domain format, handle relative URLs, and remove trailing slash.

    Args:
    - domain (str): The original domain.
    - url (str): The URL to be formatted.

    Returns:
    - str: The formatted URL.
    """
    from urllib.parse import urlparse, urlunparse, urljoin

    domain_parts = urlparse(domain)

    # Handle relative URLs
    if url.startswith('//'):
        # Use the scheme from the domain for URLs starting with //
        url = f"{domain_parts.scheme}:{url}"
    elif url.startswith('/'):
        # Use urljoin to handle URLs starting with /
        url = urljoin(domain, url)

    url_parts = urlparse(url)

    # Remove trailing slash from path
    path = url_parts.path.rstrip('/')

    formatted_url = urlunparse((
        domain_parts.scheme, 
        domain_parts.netloc, 
        path,
        url_parts.params,
        url_parts.query,
        url_parts.fragment
    ))

    return formatted_url

import os

def get_best_regex_patterns(domains: list) -> list[str]:
    from openai import OpenAI

    # Ensure the API key is set correctly
    api_key = os.environ.get("OPENAPI_KEY")
    if not api_key:
        raise ValueError("The OPENAPI_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)

    # Initial regex patterns
    initial_patterns =    [r'/product/', r'/item/', r'/p/', r'/proddetail/', r'/products/', r'/detail/', r'/goods/', r'/buy/', r'/listing/', r'/catalog/']

    # Prepare the prompt for OpenAI
    prompt = (
        f"Given the following domains: {domains}, identify the patterns for product detail pages for these domains. "
        f"Check if the initial patterns list satisfies all product detail page patterns. "
        f"The initial patterns are: {initial_patterns}. "
        f"If these patterns are not sufficient, add specific patterns required to fulfill the given domains. "
        f"The output should be a JSON object where each key is a domain and the value is a list of additional regex patterns required for that domain. "
        f"Example format: {{\"domain1.com\": [\"pattern1\", \"pattern2\"], \"domain2.com\": [\"pattern3\"]}} "
        f"Provide accurate and specific patterns for product detail pages. "
        f"Keep output minimal and concise and don't explain."
        f"Output must be placed within ```json ```"
    )

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-4o-mini",
        )
        # Extract the suggested patterns from the response
        response_content = response.choices[0].message.content.strip().split("```json")[1].strip().split("```")[0].strip()
        
        # Parse the map from the response
        suggested_patterns_map = eval(response_content)
        logger.info(suggested_patterns_map)
        
        # Extract all unique regex patterns from the map
        additional_patterns = set()
        for _, patterns in suggested_patterns_map.items():
            for pattern in patterns:
                if pattern not in initial_patterns:
                    additional_patterns.add(pattern)
        # Combine initial patterns with additional patterns
        best_patterns = list(set(initial_patterns + list(additional_patterns)))
    except Exception as e:
        logger.error(f"Error using OpenAI API: {e}")
        best_patterns = initial_patterns

    return best_patterns

def is_crawlable(url: str) -> bool:
    non_crawlable_extensions = [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',  # Image files
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',  # Video files
        '.mp3', '.wav', '.aac', '.flac', '.ogg',          # Audio files
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Document files
        '.zip', '.rar', '.7z', '.tar', '.gz',             # Compressed files
        '.exe', '.bin', '.dll',                           # Executable files
        '.css', '.js', '.json', '.xml', '.csv'            # Other non-HTML files
    ]

    parsed_url = urlsplit(url)
    path = parsed_url.path.lower()

    # Remove query parameters from the path
    path = path.split('?')[0]
    
    if any(path.endswith(ext) for ext in non_crawlable_extensions):
        logger.debug(f"Non-crawlable URL: {url}")
        return False
    return True
