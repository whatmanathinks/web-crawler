import httpx
import logging

logger = logging.getLogger(__name__)

async def fetch_page(client, url):
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    return None
