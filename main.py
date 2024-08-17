import asyncio
from playwright.async_api import async_playwright
import os
import logging
from database import setup_database_connection, load_websites
from form_filler import process_websites_async
from models import train_field_matching_model
from dotenv import load_dotenv

load_dotenv()

# Function to set up logging
def setup_logging():
    logging.basicConfig(
        filename='form_submission.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

# Function to set up Playwright with Scraping Browser and Bright Data
async def setup_browser(pw):
    try:
        # Bright Data Scraping Browser credentials
        auth = os.getenv('BRIGHTDATA_AUTH')  # Format: user:pass
        sbr_ws_cdp = f'wss://{auth}@brd.superproxy.io:9222'

        logging.info("Connecting to Scraping Browser...")

        # Initialize Playwright with Scraping Browser
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

# Main function for form filling and submission
async def main():
    setup_logging()

    connection = None  # Initialize the database connection
    browser = None  # Initialize the browser variable

    try:
        # Setup the database connection
        logging.info("Setting up the database connection...")
        connection = setup_database_connection()
        logging.info("Database connection established.")

        # Use async_playwright to manage the Playwright instance
        async with async_playwright() as pw:
            # Set up the Playwright Scraping Browser
            logging.info("Setting up the Scraping Browser...")
            browser = await setup_browser(pw)  # Pass pw to setup_browser
            logging.info("Browser set up successfully.")

            if connection is not None and browser:
                # Load the websites to process
                logging.info("Loading websites from the database...")
                websites = load_websites(connection)
                logging.info(f"Websites loaded: {websites}")

                # Train the model for field matching
                logging.info("Training the field matching model...")
                model, vectorizer = train_field_matching_model()
                logging.info("Model training completed.")

                # Start processing the websites asynchronously
                logging.info("Starting to process websites asynchronously...")
                await process_websites_async(websites, connection, model, vectorizer, browser)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}", exc_info=True)

    finally:
        # Keep the browser open for debugging if an error occurs
        if browser and connection:
            logging.info("Keeping browser and connection open for debugging.")
        else:
            # Close the browser if no errors occurred and it's not needed anymore
            if browser:
                logging.info("Closing the browser...")
                await close_browser(browser)
                logging.info("Browser closed.")

            # Ensure the database connection is closed
            if connection is not None:
                logging.info("Closing the database connection...")
                connection.client.close()
                logging.info("Database connection closed.")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
