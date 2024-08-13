import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class FieldData(Base):
    __tablename__ = 'field_matching'
    id = Column(Integer, Sequence('field_data_id_seq'), primary_key=True)
    field = Column(String(50), nullable=False)
    description = Column(String(200), nullable=False)

def create_schema():
    # Load environment variables
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')

    # Construct the MySQL connection string
    DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"

    # Create the SQLAlchemy engine
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()

    # Define the table schema
    websites = Table('websites', metadata,
                     Column('id', Integer, primary_key=True),
                     Column('url', String, nullable=False),
                     Column('form_data', String, nullable=False))
    
    # Create the table
    metadata.create_all(engine)
    Base.metadata.create_all(engine)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Store sample data
    store_sample_data(session)

def store_sample_data(session):
    sample_data = [
        ("first name", "first-name"),
        ("last name", "last-name"),
        ("name", "Enter your full name", "full name", "full-name"),
        ("email", "Email address", "email-address"),
        ("phone", "cell #", "phone number", "phone-number"),
        ("address 1", "address-1"),
        ("address 2", "address-2"),
        ("address", "Home address", "residential address", "mailing address", "home-address", "residence"),
        ("zip","zip code","zip-code"),
        ("ssn", "social security number", "social-security-number"),
        ("date of birth", "dob", "birth date", "birthdate", "birth-date"),
        ("gender",),
        ("drivers-license-number", "drivers license number", "license number", "license", "license-#", "drivers license #")
    ]
    
    for field, *descriptions in sample_data:
        for desc in descriptions:
            field_data = FieldData(field=field, description=desc)
            session.add(field_data)
    
    session.commit()

if __name__ == "__main__":
    create_schema()