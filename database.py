import os
from pymongo import MongoClient
import pandas as pd
import logging
from urllib.parse import quote_plus  # Import this for URL encoding
from dotenv import load_dotenv

load_dotenv()

def setup_database_connection():
    try:
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_name = os.getenv('DB_NAME')

        # URL-encode the username and password
        db_user = quote_plus(db_user)
        db_password = quote_plus(db_password)

        # Construct the MongoDB connection string
        DATABASE_URL = f"mongodb://{db_user}:{db_password}@{db_host}/{db_name}"

        # Create the MongoDB client
        client = MongoClient(DATABASE_URL, authSource='admin')
        db = client[db_name]
        return db
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise

def load_websites(db):
    try:
        websites_collection = db['websites']
        websites = list(websites_collection.find())
        return websites
    except Exception as e:
        logging.error(f"Error loading websites: {e}")
        raise

def load_form_data(db, website_name):
    try:
        form_collection = db[f'{website_name}_form_data']
        form_data = pd.DataFrame(list(form_collection.find()))

        if form_data.empty:
            logging.warning(f"No form data found for {website_name}. Check the database.")
        else:
            logging.info(f"Form data loaded successfully for {website_name}.")

        return form_data
    except Exception as e:
        logging.error(f"Error loading form data for {website_name}: {e}")
        raise

def load_field_locators(db, website_name):
    try:
        locators_collection = db[f'{website_name}_locators']
        locators_data = pd.DataFrame(list(locators_collection.find()))
        return locators_data
    except Exception as e:
        logging.error(f"Error loading field locators for {website_name}: {e}")
        raise

def load_field_matching(db):
    try:
        field_matching_collection = db['field_matching']
        field_matching_data = pd.DataFrame(list(field_matching_collection.find()))
        return field_matching_data
    except Exception as e:
        logging.error(f"Error loading field matching data: {e}")
        raise

def insert_individual_data(db, individual_data):
    try:
        individuals_collection = db['individuals']
        individuals_collection.insert_many(individual_data)
    except Exception as e:
        logging.error(f"Error inserting individual data: {e}")
        raise

def load_individual_data(db):
    try:
        individuals_collection = db['individuals']
        individual_data = list(individuals_collection.find())
        return individual_data
    except Exception as e:
        logging.error(f"Error loading individual data: {e}")
        raise

def log_to_database(db, level, message):
    try:
        logs_collection = db['logs']
        log_entry = {"level": level, "message": message}
        logs_collection.insert_one(log_entry)
    except Exception as e:
        logging.error(f"Error logging to database: {e}")
        raise

def upsert_website(db, name, url, category):
    try:
        websites_collection = db['websites']
        website = {
            "name": name,
            "url": url,
            "category": category  # Include the category field
        }
        result = websites_collection.update_one(
            {"url": url},  # Use the URL as the unique identifier
            {"$set": website},
            upsert=True
        )
        logging.info(f"Website {name} upserted successfully with ID: {result.upserted_id}")
        return result.upserted_id or websites_collection.find_one({"url": url})['_id']

    except Exception as e:
        logging.error(f"Error upserting website: {e}")
        raise


def upsert_individual(db, opt_in, first_name, last_name, name, full_name, email, email_address, password, pin, telephone, cellphone, phone_number, phone, address_1, address_2, zip, zip_code, postal_code, city, state, country, address, residential_address, mailing_address, home_address, residence, ssn, social_security_number, birthday, dob, birthdate, birth_date, date_of_birth, gender, gender_abbreviation, drivers_license_number, license_number, license):
    try:
        individuals_collection = db['individuals']
        individual = {
             "opt-in": opt_in,
             "first name": first_name,
             "last name": last_name,
             "name": name,
             "full name": full_name,
             "email": email,
             "email address": email_address,
             "password": password,
             "pin": pin,
             "telephone": telephone,
             "cell #": cellphone,
             "phone number": phone_number,
             "phone-number": phone,
             "address 1": address_1,
             "address 2": address_2,
             "zip": zip,
             "zip code": zip_code,
             "postal code": postal_code,
             "city": city,
             "state": state,
             "country": country,
             "address": address,
             "residential address": residential_address,
             "mailing address": mailing_address,
             "home-address": home_address,
             "residence": residence,
             "ssn": ssn,
             "social security number": social_security_number,
             "birthday": birthday,
             "dob": dob,
             "birthdate": birthdate,
             "birth-date": birth_date,
             "date of birth": date_of_birth,
             "gender": gender,
             "gender abbreviation": gender_abbreviation,
             "drivers license number": drivers_license_number,
             "license number": license_number,
             "license": license,
        }
        result = individuals_collection.update_one(
            {"email": email},  # Use the email as the unique identifier
            {"$set": individual},
            upsert=True
        )
        return result.upserted_id or individuals_collection.find_one({"email": email})['_id']
    except Exception as e:
        logging.error(f"Error upserting individual: {e}")
        raise


def upsert_submission_record(db, individual_id, website_id):
    try:
        submissions_collection = db['submissions']
        submission_record = {
            "individual_id": individual_id,
            "website_id": website_id,
            "is_submitted": False  # Default to False, will be updated later
        }
        result = submissions_collection.update_one(
            {"individual_id": individual_id, "website_id": website_id},
            {"$setOnInsert": submission_record},  # Insert only if it doesn't already exist
            upsert=True
        )
        return result.upserted_id or submissions_collection.find_one({"individual_id": individual_id, "website_id": website_id})['_id']
    except Exception as e:
        logging.error(f"Error upserting submission record: {e}")
        raise


def check_submission_status(db, individual_id, website_id):
    try:
        submissions_collection = db['submissions']
        submission = submissions_collection.find_one({"individual_id": individual_id, "website_id": website_id})
        return submission and submission.get('is_submitted', False)
    except Exception as e:
        logging.error(f"Error checking submission status: {e}")
        raise

def update_submission_status(db, individual_id, website_id):
    try:
        submissions_collection = db['submissions']
        submissions_collection.update_one(
            {"individual_id": individual_id, "website_id": website_id},
            {"$set": {"is_submitted": True}}
        )
        logging.info(f"Marked submission as completed for individual {individual_id} on website {website_id}.")
    except Exception as e:
        logging.error(f"Error updating submission status: {e}")
        raise    