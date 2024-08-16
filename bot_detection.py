import asyncio
from playwright.async_api import async_playwright
import os
import logging

# Load environment variables for Scraping Browser credentials
from dotenv import load_dotenv

load_dotenv()

# Function to set up Playwright with Scraping Browser and Bright Data
async def setup_browser():
    try:
        # Bright Data Scraping Browser credentials
        auth = os.getenv('BRIGHTDATA_AUTH')  # Format: user:pass
        sbr_ws_cdp = f'wss://{auth}@brd.superproxy.io:9222'

        logging.info("Connecting to Scraping Browser...")

        # Initialize Playwright with Scraping Browser
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(sbr_ws_cdp)
            logging.info("Connected to Scraping Browser")
            return browser

    except Exception as e:
        logging.error(f"Error setting up browser: {e}")
        raise

# Function to close the browser
async def close_browser(browser):
    if browser:
        await browser.close()
        logging.info("Browser closed")

