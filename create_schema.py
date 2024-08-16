import os
from pymongo import MongoClient
from urllib.parse import quote_plus  # Import this for URL encoding
from dotenv import load_dotenv
from database import upsert_website  # Import the upsert_website function

load_dotenv()

def create_schema():
    # Load environment variables
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
    try:
        client = MongoClient(DATABASE_URL, authSource='admin')
        db = client[db_name]
        print("Successfully connected to MongoDB")
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")


    # Create the collections and insert sample data
    create_collections_and_insert_data(db)

def create_collections_and_insert_data(db):
    # Define the collections
    field_matching = db['field_matching']
    websites = db['websites']
    individuals = db['individuals']
    submissions = db['submissions']

    # Sample data for field_matching collection
    sample_data = [
        {"field": "opt-in", "description": "opt in"},
        {"field": "first name", "description": "first name"},
        {"field": "first-name", "description": "first name"},
        {"field": "last name", "description": "last name"},
        {"field": "last-name", "description": "last name"},
        {"field": "name", "description": "name"},
        {"field": "full name", "description": "name"},
        {"field": "full-name", "description": "name"},
        {"field": "Email", "description": "email"},
        {"field": "Email address", "description": "email"},
        {"field": "email-address", "description": "email"},
        {"field": "password", "description": "password"},
        {"field": "pin", "description": "pin"},
        {"field": "telephone", "description": "phone"},
        {"field": "cell #", "description": "phone"},
        {"field": "phone number", "description": "phone"},
        {"field": "phone-number", "description": "phone"},
        {"field": "address 1", "description": "address 1"},
        {"field": "address 2", "description": "address 2"},
        {"field": "zip", "description": "zip"},
        {"field": "zip code", "description": "zip"},
        {"field": "postal code", "description": "zip"},
        {"field": "city", "description": "city"},
        {"field": "state", "description": "state"},
        {"field": "country", "description": "country"},
        {"field": "Home address", "description": "address"},
        {"field": "residential address", "description": "address"},
        {"field": "mailing address", "description": "address"},
        {"field": "home-address", "description": "address"},
        {"field": "residence", "description": "address"},
        {"field": "ssn", "description": "ssn"},
        {"field": "social security number", "description": "ssn"},
        {"field": "social-security-number", "description": "ssn"},
        {"field": "birthday", "description": "birthday"},
        {"field": "dob", "description": "date of birth"},
        {"field": "birth date", "description": "date of birth"},
        {"field": "birthdate", "description": "date of birth"},
        {"field": "birth-date", "description": "date of birth"},
        {"field": "date of birth", "description": "date of birth"},
        {"field": "gender", "description": "gender"},
        {"field": "gender abbreviation", "description": "gender"},
        {"field": "drivers license number", "description": "drivers-license-number"},
        {"field": "license number", "description": "drivers-license-number"},
        {"field": "drivers-license-number", "description": "drivers-license-number"},
        {"field": "license", "description": "drivers-license-number"},
        {"field": "license #", "description": "drivers-license-number"},
        {"field": "drivers license #", "description": "drivers-license-number"}
    ]
    # Insert sample data into field_matching collection
    field_matching.insert_many(sample_data)

    # Website data for websites collection
    website_data = [
        {"name": "FactorTrust", "url": "https://factortrust.com/consumer/optout.aspx", "category": "multi-step"},
        {"name": "AMEX Prequalify", "url": "https://card.americanexpress.com/d/pre-qualified-offers/", "category": "single-step"},
        {"name": "Capital One Prequalify", "url": "https://www.capitalone.com/apply/credit-cards/preapprove/?landingPage=ehpnav", "category": "multi-step"},
        {"name": "American Airlines AAdvantage Enrollment", "url": "https://www.aa.com/loyalty/enrollment/enroll?v_locale=en_US&v_mobileUAFlag=AA", "category": "single-step"},
        {"name": "US Alliance Prequalify", "url": "https://www.usalliance.org/pre-qualification", "category": "multi-step"},
        {"name": "OptOutPreScreen", "url": "https://www.optoutprescreen.com", "category": "multi-step-captcha"},
        {"name": "ExxonRewards", "url": "https://rewards.exxon.com/welcome/enrollment?ctid=e_emrp_3stepbn_text", "category": "single-step"},
        {"name": "SageStream", "url": "https://forms.sagestreamllc.com/#/opt-self", "category": "captcha"},
        {"name": "Credit One Prequalify", "url": "https://www.creditonebank.com/pre-qualification/data-entry/index", "category": "single-step"},
        {"name": "IHG Rewards", "url": "https://www.ihg.com/rewardsclub/us/en/enrollment/join?scmisc=OSMAM-6C-US-EN-IHGRCMainPage-JoinCTA", "category": "single-step"},
        {"name": "Hyatt Rewards", "url": "https://www.hyatt.com/en-US/member/enroll", "category": "single-step"},
        {"name": "Fuel Rewards", "url": "https://www.fuelrewards.com/fuelrewards/signup.html", "category": "multi-step-captcha"}
    ]
    # Use the upsert function to insert or update each website
    for site in website_data:
        upsert_website(db, site['name'], site['url'], site['category'])

    # Create unique index on individual_id and website_id in submissions collection
    submissions.create_index([('individual_id', 1), ('website_id', 1)], unique=True)

    # Ensure the `category` column is included in the schema
    websites.create_index([('url', 1)], unique=True)

if __name__ == "__main__":
    create_schema()
