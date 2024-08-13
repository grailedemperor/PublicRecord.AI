import os
from brightdata import ScrapingBrowser

# Setup the Scraping Browser with Bright Data credentials and options
def setup_browser():
    host = os.getenv('BRIGHTDATA_HOST')
    port = os.getenv('BRIGHTDATA_PORT')
    username = os.getenv('BRIGHTDATA_USERNAME')
    password = os.getenv('BRIGHTDATA_PASSWORD')

    # Create a Scraping Browser instance with Bright Data's options
    browser = ScrapingBrowser(
        host=host,
        port=port,
        username=username,
        password=password,
        solve_captcha=True,  # Enable CAPTCHA solving
        proxy_country='US',  # Example of country targeting
        rotate_ips=True,     # Enable IP rotation
        logging=True,        # Enable logging
        debug_mode=True      # Enable debugging mode
    )

    return browser
