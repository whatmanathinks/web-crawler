# E-commerce Web Crawler API

## Introduction

This web-crawler is designed to crawl product pages from e-commerce websites. Built using FastAPI, it supports crawling using BeautifulSoup and Playwright. It uses AI to determine which page is a product page, enhancing the accuracy of the crawling process. It is built keeping scalability in mind.


## Features
- **AI-Powered URL Discovery**: Uses AI to intelligently figure out product URLs within the website, enhancing the accuracy and efficiency of the crawling process.
- **Concurrent Crawling**: Efficiently crawl multiple domains at once with configurable concurrency settings.
- **Dual Crawling Methods**: Choose between Playwright for browser-based crawling or BeautifulSoup for HTTP-based crawling.
- **Dynamic Content Handling**: Supports infinite scrolling to capture content loaded dynamically.
- **Configurable Settings**: Easily adjust settings like concurrent requests per domain and across domains, download delays, and more.
- **Automatic URL Pattern Detection**: Utilizes regex patterns to identify and filter product URLs.
- **Comprehensive Logging**: Detailed logging for monitoring and debugging the crawling process.
- **RESTful API Interface**: Interact with the crawler through a well-documented API with Swagger support.



## Installation

1. **Clone the Repository**:
   ```bash
   git clone git@github.com:whatmanathinks/web-crawler.git
   cd web-crawler
   ```

2. **Install Dependencies**:
   Ensure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**:
   Copy the `.env.example` to `.env` and configure your environment variables as needed:
   ```bash
   cp .env.example .env
   ```


## Crawling Methods

### Playwright

- **Benefits**: Ideal for websites with dynamic content that requires JavaScript execution. It can handle complex interactions and infinite scrolling. Slower compared to BeautifulSoup crawler.
- **Usage**: Set `CRAWLER=playwright` in your environment configuration.

### BeautifulSoup

- **Benefits**: Lightweight and faster for static websites where JavaScript execution is not required. It uses HTTP requests to fetch page content.
- **Usage**: Set `CRAWLER=beautifulsoup` in your environment configuration.



## Startup Guide

1. **Run the Application**:
   Start the FastAPI server:
   ```bash
   fastapi dev main.py
   ```

2. **Access the API Documentation**:
   Open your browser and navigate to `http://localhost:8000/docs` to explore the API endpoints and test the crawler.

## Input and Output

### Input

- **Domains**: A list of domain URLs to crawl for product links.

### Output

- **Product URLs**: A dictionary containing the domain as the key and a list of discovered product URLs as the value.

## Example Usage

To crawl domains, send a POST request to the `/crawl` endpoint with a JSON body containing the list of domains:

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/crawl' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "domains": [
    "https://tiesta.in"
  ]
}'
```