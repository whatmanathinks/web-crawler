def format_url(domain: str, url: str) -> str:
    """
    Format the given URL to match the original domain format.

    Args:
    - domain (str): The original domain.
    - url (str): The URL to be formatted.

    Returns:
    - str: The formatted URL.
    """
    from urllib.parse import urlparse, urlunparse

    domain_parts = urlparse(domain)
    url_parts = urlparse(url)

    formatted_url = urlunparse((
        domain_parts.scheme,  # Use the scheme from the original domain
        domain_parts.netloc,  # Use the network location from the original domain
        url_parts.path,
        url_parts.params,
        url_parts.query,
        url_parts.fragment
    ))

    return formatted_url
