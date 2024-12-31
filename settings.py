import os

# Configuration for concurrent requests
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", 10))  # Maximum number of concurrent requests

# Configuration for download delay
DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", 100))  # Delay between requests in milliseconds

# Configuration for concurrent requests per domain
CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv("CONCURRENT_REQUESTS_PER_DOMAIN", 5))  # Max concurrent requests per domain

# Configuration for Playwright browser type
PLAYWRIGHT_BROWSER_TYPE = os.getenv("PLAYWRIGHT_BROWSER_TYPE", "chromium")  # Browser type for Playwright

# Configuration for Playwright launch options
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": os.getenv("PLAYWRIGHT_HEADLESS", "True").lower() == "true"  # Launch browser in headless mode
}

# Configuration for crawler method
CRAWLER = os.getenv("CRAWLER", "beautifulsoup").lower()

if CRAWLER not in ["playwright", "beautifulsoup"]:
    CRAWLER = "beautifulsoup"  #