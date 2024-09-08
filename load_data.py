import logging
import pandas as pd
from database import setup_database_connection, upsert_individual, upsert_website
from pymongo.errors import DuplicateKeyError

def load_individuals_from_csv(csv_file_path):
    # Load the CSV data into a DataFrame
    individuals_df = pd.read_csv(csv_file_path)

    print(individuals_df.columns.tolist())  # Print the headers to see what's being read

    # Convert the DataFrame to a list of dictionaries
    individual_data = individuals_df.to_dict(orient='records')

    # Setup the database connection
    db = setup_database_connection()

    # Upsert each individual into the 'individuals' collection
    for individual in individual_data:
        upsert_individual(
            db, 
            individual['opt-in'], 
            individual['first name'], 
            individual['last name'], 
            individual['name'], 
            individual['full name'],
            individual['email'], 
            individual['email address'], 
            individual['password'], 
            individual['pin'], 
            individual['telephone'], 
            individual['cell #'], 
            individual['phone number'], 
            individual['phone-number'], 
            individual['address 1'], 
            individual['address 2'], 
            individual['zip'], 
            individual['zip code'], 
            individual['postal code'], 
            individual['city'], 
            individual['state'], 
            individual['country'], 
            individual['abbreviated-country'],
            individual['address'], 
            individual['residential address'],
            individual['mailing address'], 
            individual['home-address'], 
            individual['residence'], 
            individual['ssn'], 
            individual['social security number'], 
            individual['birthday'], 
            individual['dob'], 
            individual['dob-formatted'], 
            individual['birthdate'], 
            individual['birth date'], 
            individual['date of birth'], 
            individual['gender'], 
            individual['gender abbreviation'], 
            individual['drivers license number'], 
            individual['license number'], 
            individual['license'],
            individual['income'], 
            individual['phone_type'], 
            individual['license-state'], 
            individual['employment-status'], 
            individual['occupation'], 
            individual['paperless'], 
            individual['terms-conditions'],
            individual['ssa-verification'], 
            individual['citizen'],
            individual['secondary-citizen'], 
            individual['bank-account'],
            )

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
    {"name": "Fuel Rewards", "url": "https://www.fuelrewards.com/fuelrewards/signup.html", "category": "multi-step-captcha"}
]

def load_form_data_from_csv(csv_file_path):
    # Load the CSV data into a DataFrame
    form_data_df = pd.read_csv(csv_file_path)
    form_data_df.dropna(how='all', axis=1, inplace=True)  # Drop columns with all NaN values
    #logging.info(f"Cleaned form_data: {form_data_df}")

    # Setup the database connection
    db = setup_database_connection()

    websites = form_data_df['website_name'].unique()

    for website in websites:
        website_data_row = form_data_df[form_data_df['website_name'] == website]

        # Match category from website_data based on the website name
        matching_site = next((site for site in website_data if site['name'] == website), None)
        if matching_site:
            website_url = matching_site['url']
            website_category = matching_site['category']
        else:
            raise ValueError(f"Category for {website} not found")


        # Upsert website into the 'websites' collection
        website_id = upsert_website(db, website, website_url, website_category)

        # Insert form fields and locators for this website
        form_fields = website_data_row.to_dict(orient='records')

        form_collection = db[f"{website}_form_data"]

        for field in form_fields:
            try:
                # Insert or update form data (can add logic for handling existing fields)
                form_collection.update_one(
                    {"field_name": field['field_name']},  # Use field name as the unique identifier
                    {"$set": field},  # Update or insert the form field data
                    upsert=True
                )
            except DuplicateKeyError as e:
                print(f"Duplicate key error for {field['field_name']} in {website}: {e}")
            except Exception as e:
                print(f"Error upserting form data for {field['field_name']} in {website}: {e}")

if __name__ == "__main__":
    # Path to the CSV file containing individual data
    csv_file_path = r'C:\Users\slc\Enhance-Public-Record-Bot\PublicRecord.AI\List of Individuals.csv'
    load_individuals_from_csv(csv_file_path)

    # Path to the CSV file containing form data
    form_data_csv_file_path = r'C:\Users\slc\Enhance-Public-Record-Bot\PublicRecord.AI\form_data.csv'
    load_form_data_from_csv(form_data_csv_file_path)
