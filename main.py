from database import setup_database_connection, load_websites
from form_filler import process_websites_async
from models import train_field_matching_model
import asyncio
import logging

def setup_logging():
    logging.basicConfig(filename='form_submission.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main(max_workers=5):
    setup_logging()
    
    connection = None  # Initialize the connection variable
    
    try:
        connection = setup_database_connection()  # Attempt to set up the database connection
        
        if connection is not None:  # Corrected: explicitly compare with None
            websites = load_websites(connection)
            model, vectorizer = train_field_matching_model()
            asyncio.run(process_websites_async(websites, connection, model, vectorizer, max_workers))
    
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
    
    finally:
        if connection is not None:  # Corrected: explicitly compare with None
            connection.client.close()  # Close the MongoDB client connection

if __name__ == "__main__":
    main(max_workers=10)
