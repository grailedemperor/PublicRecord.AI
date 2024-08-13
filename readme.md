# Public Record Bot

## Overview
This project automates the process of filling and submitting forms on various websites using machine learning for field matching.

## Structure
- `main.py`: Entry point of the application.
- `models.py`: Machine learning model training and prediction.
- `database.py`: Database interactions.
- `form_filler.py`: Form filling and submission logic.
- `create_schema.py`: Script for creating database schema
- `load_data.py`: Script for loading data into the application
- `.env`: Environment variables.
- `.venv`: Virtual nvironment variables
- `requirements.txt`: Dependencies.
- `List of Individuals.csv`: List of individuals for initial database load

## Setup
1. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

2. Set up the `.env` file with your database credentials.

## Running the Application
Run the main script:
```sh
python main.py

Logging
Logs are stored in form_submission.log.

License
This project is licensed under the MIT License.

```