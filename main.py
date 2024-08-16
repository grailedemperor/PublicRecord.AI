from bot_detection import setup_browser, close_browser  # Import Playwright-based browser setup
from database import setup_database_connection, load_websites
from form_filler import process_websites_async
from models import train_field_matching_model
import asyncio
import logging

# Function to set up logging
def setup_logging():
    logging.basicConfig(filename='form_submission.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Main function for form filling and submission
async def main(max_workers=5):
    setup_logging()

    connection = None  # Initialize the database connection
    browser = None  # Initialize the browser variable

    try:
        # Setup the database connection
        logging.info("Setting up the database connection...")
        connection = setup_database_connection()
        logging.info("Database connection established.")

        # Set up the Playwright Scraping Browser
        logging.info("Setting up the Scraping Browser...")
        browser = await setup_browser()
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
            await process_websites_async(websites, connection, model, vectorizer, browser, max_workers)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}",exc_info=True)

    finally:
        # Close the browser
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
    asyncio.run(main(max_workers=10))


