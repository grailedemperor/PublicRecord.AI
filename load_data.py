import pandas as pd
from database import setup_database_connection, upsert_individual

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
            individual['address'], 
            individual['residential address'],
            individual['mailing address'], 
            individual['home-address'], 
            individual['residence'], 
            individual['ssn'], 
            individual['social security number'], 
            individual['birthday'], 
            individual['dob'], 
            individual['birthdate'], 
            individual['birth date'], 
            individual['date of birth'], 
            individual['gender'], 
            individual['gender abbreviation'], 
            individual['drivers license number'], 
            individual['license number'], 
            individual['license'])

if __name__ == "__main__":
    csv_file_path = '/Users/eleven23/Desktop/Enhance-Public-Record-Bot/PublicRecord.AI/List of Individuals.csv'
    load_individuals_from_csv(csv_file_path)
