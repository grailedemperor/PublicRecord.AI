import os
import json
import pandas as pd
import difflib  # For fuzzy matching
from bson import ObjectId
import logging
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
from database import (
    setup_database_connection, load_websites, load_form_data, load_field_locators, 
    load_individual_data, log_to_database, upsert_submission_record, check_submission_status, 
    update_submission_status
)
from models import advanced_field_matching
import time

FIELD_MAPPING = {
    'opt-in': 'opt-in', 
    'last-name':'last name', 
    'first-name':'first name', 
    'name':'name', 
    'full name':'full name',
    'email':'email', 
    'email address':'email address', 
    'password':'password', 
    'pin':'pin', 
    'telephone':'telephone', 
    'cell #':'cell #',
    'phone':'phone', 
    'phone number':'phone number', 
    'phone-number':'phone-number', 
    'address-1':'address 1', 
    'address-2':'address 2', 
    'zip':'zip', 
    'zip code':'zip code', 
    'postal code':'postal code', 
    'city':'city', 
    'state':'state', 
    'country':'country', 
    'abbreviated-country':'abbreviated-country',
    'address':'address', 
    'residential address':'residential address',
    'mailing address':'mailing address', 
    'home-address':'home-address', 
    'residence':'residence', 
    'ssn':'ssn', 
    'social security number':'social security number', 
    'birthday':'birthday', 
    'dob':'dob', 
    'dob-formatted':'dob-formatted', 
    'birthdate':'birthdate', 
    'birth date':'birth date', 
    'date of birth':'date of birth', 
    'gender':'gender', 
    'gender abbreviation':'gender abbreviation', 
    'drivers license number':'drivers license number', 
    'license number':'license number', 
    'license':'license',
    'income':'income', 
    'phone_type':'phone_type', 
    'license-state':'license-state', 
    'employment-status':'employment-status', 
    'occupation':'occupation', 
    'paperless':'paperless', 
    'terms_conditions':'terms-conditions',
    'ssa-verification':'ssa-verification', 
    'citizen':'citizen',
    'secondary-citizen':'secondary-citizen', 
    'bank-account':'bank-account',
    'captcha':'captcha',
    'rent':'rent',
    'pin':'pin'
}  

# Function for fuzzy matching field names
def get_best_match(field_name, individual_data_keys):
    best_match = difflib.get_close_matches(field_name, individual_data_keys, n=1, cutoff=0.8)
    return best_match[0] if best_match else None

def convert_objectid(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, ObjectId):  # Check if the value is an ObjectId
                data[key] = str(value)  # Convert ObjectId to string
            elif isinstance(value, dict):  # Recursively handle dictionaries
                convert_objectid(value)
            elif isinstance(value, list):  # Recursively handle lists
                for item in value:
                    convert_objectid(item)
    elif isinstance(data, list):
        for i in range(len(data)):
            if isinstance(data[i], ObjectId):  # Check if list element is an ObjectId
                data[i] = str(data[i])  # Convert ObjectId to string
            elif isinstance(data[i], dict) or isinstance(data[i], list):  # Recursively handle nested structures
                convert_objectid(data[i])

SUCCESSFUL_SUBMISSION_DIR = 'successful_submission'
if not os.path.exists(SUCCESSFUL_SUBMISSION_DIR):
    os.makedirs(SUCCESSFUL_SUBMISSION_DIR)

def log_successful_submission(individual_name, website_name, submission_data, url):
    if 'final-submit' not in submission_data or submission_data['final-submit'] != 'clicked':
        raise RuntimeError(f"Submission for {individual_name} on {website_name} did not complete properly.")
    # Convert form_data (Pandas DataFrame) to a list of dictionaries
    if isinstance(submission_data, pd.DataFrame):
        submission_data = submission_data.to_dict(orient='records')  # Convert DataFrame to list of dicts

    #convert_objectid(individual_data)
    convert_objectid(submission_data)

    # Debugging: Log data after ObjectId conversion
    logging.info(f"Submission data after ObjectId conversion: {submission_data}")
    #logging.info(f"Individual data after ObjectId conversion: {individual_data}")

    # Ensure submission_data and individual_data are JSON serializable
    def ensure_json_serializable(data):
        if isinstance(data, pd.DataFrame):  # Convert DataFrame to a list of dictionaries
            return data.to_dict(orient='records')
        elif isinstance(data, pd.Series):  # Convert Series to a list
            return data.tolist()
        elif isinstance(data, dict):
            return {k: ensure_json_serializable(v) for k, v in data.items()}  # Recursively handle dicts
        elif isinstance(data, list):
            return [ensure_json_serializable(i) for i in data]  # Recursively handle lists
        return data  # If it's already a simple data type, return it as is

    submission_data_clean = ensure_json_serializable(submission_data)
    
    log_data = {
        "individual_name": individual_name,
        "website_name": website_name,
        "url": url,
        "submitted_data": submission_data_clean,
    }

    log_file_path = f"successful_submission/{individual_name}_{website_name}.json"
    with open(log_file_path, 'w') as f:
        json.dump(log_data, f, indent=4)

    logging.info(f"Logged successful submission for {individual_name} on {website_name}.")

async def identify_and_click_field(page, selector, field_name, field_type, individual_data, submission_data):
    try:
        logging.info(f"Waiting for element with selector: {selector}")

        # Strip and clean the field_name
        field_name_cleaned = field_name.strip().lower()
        
        # Get the actual data key from the mapping
        actual_data_key = FIELD_MAPPING.get(field_name_cleaned, field_name_cleaned)
        
        # Use fuzzy matching to improve the chance of finding the right field
        actual_data_key = get_best_match(actual_data_key, individual_data.keys()) or actual_data_key
        
        logging.info(f"Mapped field {field_name} to {actual_data_key}")

        if field_type == 'input':
            element = await page.wait_for_selector(f"input#{selector}, input[{selector}], input[name*='Confirm'], input[type='submit']", timeout=2000)
        elif field_name in ['submit', 'final-submit'] or field_type == 'button':
            element = await page.wait_for_selector(f"input[type='submit']#{selector}, button[{selector}], button#{selector}, input[value='Submit']", timeout=2000)
        elif field_type == 'select':
            element = await page.wait_for_selector(f"select#{selector}, select[{selector}]", timeout=2000)
        elif field_type == 'checkbox':
            element = await page.wait_for_selector(f"input[type='checkbox']#{selector}", timeout=2000)
        elif field_type == 'radio':
            element = await page.wait_for_selector(f"input[type='radio']#{selector}", timeout=2000)  
        else:
            logging.warning(f"Unknown field type: {field_type} for {field_name}. Defaulting to input.")
            element = await page.wait_for_selector(f"input#{selector}", timeout=2000)

        if element:
            logging.info(f"Element with selector: {selector} found.")
            await element.hover()

            # Handle input fields where data needs to be filled
            if field_type == 'input':
                if actual_data_key in individual_data and isinstance(individual_data[actual_data_key], str):
                    filled_value = individual_data[actual_data_key]
                    logging.info(f"Filling field {field_name} with data: {filled_value}")
                    try:
                        # Try using the fill method first
                        await element.fill(filled_value)  
                        submission_data[actual_data_key] = filled_value  # Log the **actual value** filled
                    except Exception as fill_error:
                        # If fill fails, fallback to the type method
                        logging.error(f"Error using element.fill for {field_name}: {fill_error}. Attempting to use page.type instead.")
            
                        try:
                            # Fallback: Mimic typing with a small delay
                            await page.type(selector, filled_value, delay=100)  
                            submission_data[actual_data_key] = filled_value  # Log the **actual value** filled
                        except Exception as type_error:
                            # Log if both fill and type fail
                            logging.error(f"Failed to type into field {field_name}: {type_error}")

            # Handle radio buttons
            elif field_type == 'radio' and not await element.is_checked():
                logging.info(f"Radio button {field_name} is not checked. Checking it now.")
                await element.click()
                submission_data[actual_data_key] = "checked"  # Log the radio button as "checked"

            # Handle buttons (like submit)
            elif field_type in ['submit', 'button']:
                logging.info(f"Clicking submit button {field_name}.")
                await element.click()
                submission_data[actual_data_key] = "clicked"  # Log that the button was clicked

            # Handle checkboxes
            elif field_type == 'checkbox':
                logging.info(f"Checking checkbox {field_name}.")
                await element.click()
                submission_data[actual_data_key] = "checked"  # Log that the checkbox was checked

            # Handle dropdowns
            elif field_type == 'select' and actual_data_key in individual_data:
                logging.info(f"Selecting option for {field_name}: {individual_data[actual_data_key]}")
                await element.select_option(individual_data[actual_data_key])
                submission_data[actual_data_key] = individual_data[actual_data_key]  # Log the selected option

            logging.info(f"Clicked {field_name} successfully.")
            return element
        else:
            logging.warning(f"Element with selector: {selector} not found. Attempting JavaScript fallback.")

            # JS Fallback using getElementById
            js_click_result = await page.evaluate(f'''
                var element = document.getElementById("{selector}");
                if (element) {{
                    element.click();
                    return true;
                }} else {{
                    return false;
                }}
            ''')

            if js_click_result:
                logging.info(f"JavaScript click for {field_name} was successful.")
                submission_data[actual_data_key] = "clicked"  # Log that the JS click was successful
                return True
            else:
                raise RuntimeError(f"JavaScript fallback failed to interact with {field_name} using selector '{selector}'")

    except Exception as e:
        logging.error(f"Error locating or clicking field (Selector: {selector}, Field: {field_name}): {e}")
        return None

async def scroll_to_element(page, selector):
    try:
        logging.info(f"Waiting for element with selector: {selector}")
        element = await page.wait_for_selector(selector)

        if not element:
            logging.error(f"Element with selector: {selector} not found on page.")
            return None

        logging.info(f"Scrolling to element with selector: {selector}")
        try:
            await page.evaluate(f"document.querySelector(\"{selector}\").scrollIntoView()")
            await asyncio.sleep(2)
            logging.info(f"Scrolled to element: {selector}")
        except Exception:
            logging.warning(f"Scroll failed for {selector}, attempting a click.")
            await element.click()

        return element
    except Exception as e:
        logging.error(f"Error scrolling to element {selector}: {e}")
        return None
            
# Updated function to handle the form-filling process
# Helper functions for splitting dob and ssn
def split_dob(dob):
    # Assuming dob is in 'MM/DD/YYYY' format
    dob_parts = dob.split('/')
    return {
        'dob_month': dob_parts[0],
        'dob_day': dob_parts[1],
        'dob_year': dob_parts[2]
    }

def split_ssn(ssn):
    # Assuming ssn is in 'XXX-XX-XXXX' format
    ssn_str = str(ssn)
    return {
        'ssn_part1': ssn_str[:3],
        'ssn_part2': ssn_str[3:5],
        'ssn_part3': ssn_str[5:],
    }

async def handle_form_filling(page, individual_data, form_data, field_locators, individual_name, website_name, connection, website_id):
    submission_data = {}  # Dictionary to store field names and values
    # Convert zip code to string if it exists in individual_data
    if 'zip' in individual_data:
        individual_data['zip'] = str(individual_data.get('zip', ''))

    # Split dob and ssn if present in individual_data
    if 'dob' in individual_data:
        dob_split = split_dob(individual_data['dob'])
        individual_data.update(dob_split)

    if 'ssn' in individual_data:
        ssn_split = split_ssn(individual_data['ssn'])
        individual_data.update(ssn_split)

    try:
        #logging.info(f"Field locators: {field_locators}")

        # Ensure we process fields in the correct order by rank, handle missing 'rank' case
        if 'rank' in field_locators.columns:
            field_locators = field_locators.sort_values('rank')  # Sort fields by rank
        else:
            logging.warning(f"No 'rank' field in field_locators for {website_name}. Proceeding without sort.")

        final_submit_found = False

        # Iterate through the field locators
        for index, row in field_locators.iterrows():
            field_name = row.get('field_name')
            selector = row.get('locator_value')  # Use selector (e.g., ID, class)
            field_type = row.get('field_type')
            logging.info(f"Processing field at index {index} (Rank: {row.get('rank', 'N/A')}): {row}")

            if field_name == 'final-submit':
                final_submit_found = True

            try:
                #logging.info(f"Field: {field_name}, Selector: {selector}, Type: {field_type}")

                # Scroll to the element before interacting
                await scroll_to_element(page, selector)

                # Locate and click/handle the field by selector, not field_name
                element = await identify_and_click_field(page, selector, field_name, field_type, individual_data, submission_data)

                # Instead of logging the field_type, log the actual value from individual_data
                actual_data_key = FIELD_MAPPING.get(field_name.lower(), field_name.lower())
                
                # If there's a corresponding key in individual_data, save the actual value
                if actual_data_key in individual_data:
                    submission_data[actual_data_key] = individual_data[actual_data_key]
                    logging.info(f"Logged {actual_data_key}: {individual_data[actual_data_key]} in submission_data")
                else:
                    logging.warning(f"No data found for {field_name} in individual_data.")

                # Add a small delay after each interaction
                await asyncio.sleep(1)

                # If the final-submit button was successfully clicked, take a screenshot after submission
                if field_name == 'final-submit' and final_submit_found and 'final-submit' in submission_data and submission_data['final-submit'] == 'clicked':
                    logging.info(f"Final submit button clicked for {individual_name} on {website_name}. Waiting for 2 seconds before taking screenshot.")
                    await asyncio.sleep(2)  # Wait for 2 seconds before taking the screenshot
                    screenshot_path = f"successful_submission/confirmation_screenshot_{website_name}_{individual_name}.png"
                    await page.screenshot(path=screenshot_path)
                    #logging.info(f"Screenshot taken and saved to {screenshot_path}")

            except Exception as e:
                logging.error(f"Error processing field at index {index}: {e}")
                raise

        if not final_submit_found:
            raise RuntimeError(f"Final-submit button not interacted with for {individual_name} on {website_name}")

    except Exception as e:
        error_message = f"Error in form filling for {individual_name} on {website_name}: {str(e)}"
        logging.error(error_message)
        raise

    finally:
        if final_submit_found:
            # Log the form submission data after all fields are filled
            log_successful_submission(individual_name, website_name, submission_data, form_data["url"].iloc[0])
            # After successful submission, update the database record to mark this submission as complete
            update_submission_status(connection, individual_data['_id'], website_id)
            logging.info(f"Marked submission as completed for {individual_name} on {website_name}.")


async def handle_captcha(page, individual_name, website_name, connection):
    try:
        logging.info(f"Checking for CAPTCHA on {website_name} for {individual_name}.")
        
        # Check if CAPTCHA is inside an iframe
        iframe = await page.wait_for_selector('iframe[src*="captcha"]')
        
        if iframe:
            logging.info(f"CAPTCHA detected inside iframe on {website_name}.")
            captcha_frame = await iframe.content_frame()

            # Use JavaScript or an external service to solve the CAPTCHA (implement your preferred solution here)
            solve_result = await captcha_frame.evaluate('captcha_solver_function()')  # Placeholder for actual solution
        else:
            logging.info(f"No iframe detected for CAPTCHA. Checking for div-based CAPTCHA.")
            # Handle CAPTCHA in a div, using external service or method
            solve_result = await page.evaluate('captcha_solver_function()')  # Placeholder for actual solution

        # Validate solve_result status
        if solve_result['status'] == 'solve_finished':
            logging.info(f"Captcha solved for {individual_name} on {website_name}")
            log_to_database(connection, "INFO", f"Captcha solved for {individual_name} on {website_name}")
        else:
            error_message = f"Captcha solve failed for {individual_name} on {website_name}: {solve_result['status']}"
            logging.error(error_message)
            log_to_database(connection, "ERROR", error_message)
    except Exception as e:
        error_message = f"Error occurred while solving CAPTCHA for {individual_name} on {website_name}: {str(e)}"
        logging.error(error_message)
        log_to_database(connection, "ERROR", error_message)

async def scroll_to_element(page, selector):
    try:
        logging.info(f"Waiting for element with selector: {selector}")
        element = await page.wait_for_selector(selector, timeout=2000)  # Increased timeout

        if not element:
            logging.error(f"Element with selector: {selector} not found on page.")
            return None

        logging.info(f"Scrolling to element with selector: {selector}")
        try:
            await page.evaluate(f"document.querySelector(\"{selector}\").scrollIntoView()")
            await asyncio.sleep(2)
            logging.info(f"Scrolled to element: {selector}")
        except Exception:
            logging.warning(f"Scroll failed for {selector}, attempting a click.")
            await element.click()

        return element
    except Exception as e:
        logging.error(f"Error scrolling to element {selector}: {e}")
        return None

# Adjust timeout values and retry count
PAGE_LOAD_TIMEOUT = 20000  # Set to 60 seconds
RETRY_COUNT = 3
RETRY_DELAY = 5  # Delay between retries (seconds)
INTERACTION_DELAY = 4  # Delay between interactions (seconds)

async def fill_and_submit_form(browser, url, individual_data, form_data, field_locators, connection, website_id=None, category=None):
    page = None
    success = False  # Flag to track if submission was successful

    try:
        # Ensure ObjectIds are converted and data is prepared
        convert_objectid(individual_data)
        convert_objectid(form_data)

        # Log individual and website details
        individual_name = f"{individual_data.get('first name', 'Unknown')} {individual_data.get('last name', 'Unknown')}"
        website_name = form_data['website_name'].iloc[0] if 'website_name' in form_data.columns and not form_data.empty else 'Unknown'
        logging.info(f"Attempting to create a new page for {individual_name} on {website_name}.")

        # Create or update submission record before attempting form submission
        #submission_record_id = upsert_submission_record(connection, individual_data['_id'], website_id)
        #logging.info(f"Submission record created or updated with ID: {submission_record_id}")

        # Ensure browser is initialized
        if not browser:
            raise RuntimeError("Browser instance is not initialized.")
        
        # Create a new browser context
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:129.0) Gecko/20100101 Firefox/129.0", viewport={"width": 2000, "height": 1099})
        page = await context.new_page()

        # Navigate to the URL
        logging.info(f"Navigating to URL: {url} for {website_name}.")
        response = await page.goto(url, timeout=7000)  # Increase timeout if necessary
        
        if response is None or not (200 <= response.status < 400):
            raise RuntimeError(f"Failed to load {url} with status code: {response.status if response else 'No response'}")

        # Proceed with form filling and submission
        logging.info(f"Page loaded successfully for {website_name} with status {response.status}.")
        await handle_form_filling(page, individual_data, form_data, field_locators, individual_name, website_name, connection, website_id)
        logging.info(f"Form submitted successfully for {individual_name} on {website_name}.")
        success = True  # Mark as success

    except Exception as e:
        error_message = f"Fatal error occurred while submitting form for {individual_name} on {website_name} ({url}): {str(e)}"
        logging.critical(error_message)

        # Take screenshot on error
        if page:
            try:
                screenshot_path = f"screenshot_error_{website_name}_{individual_name}.png"
                await page.screenshot(path=screenshot_path)
                logging.info(f"Screenshot captured for {individual_name} on {website_name}. Saved to {screenshot_path}")
            except Exception as screenshot_error:
                logging.error(f"Failed to capture screenshot for {individual_name} on {website_name}: {screenshot_error}")
        
        raise RuntimeError(f"Stopping processing due to fatal error on {website_name}: {str(e)}")

    finally:
        if page:
            try:
                if not page.is_closed():
                    await page.close()
            except Exception as e:
                logging.error(f"Error closing page: {e}")

        if context:
            try:
                await context.close()
            except Exception as e:
                logging.error(f"Error closing browser context: {e}")

        if success:
            # Only upsert the submission record if the process completed successfully
            submission_record_id = upsert_submission_record(connection, individual_data['_id'], website_id)
            logging.info(f"Upserted submission record with individual_id: {individual_data['_id']}, website_id: {website_id}")
            logging.info(f"Submission record created or updated with ID: {submission_record_id}")
            # After successful submission, update the database record to mark this submission as complete
            update_submission_status(connection, individual_data['_id'], website_id)
            logging.info(f"Moving to the next website for {individual_name}.")
        else:
            logging.error(f"Failed to complete the submission for {individual_name} on {website_name}.")


# Sequentially process websites and stop on the first fatal error but keep the browser open
async def process_websites_async(websites, db, model, vectorizer, browser):
    try:
        individual_data_list = load_individual_data(db)

        # Loop through each individual
        for individual_data in individual_data_list:
            individual_name = f"{individual_data.get('first name', 'Unknown')} {individual_data.get('last name', 'Unknown')}"
            logging.info(f"Starting submission process for individual: {individual_name} (ID: {individual_data['_id']})")

            # Convert individual_id to ObjectId if needed
            individual_id = ObjectId(individual_data['_id'])

            # Filter out websites where submission is already completed for this individual
            websites_to_process = [
                website for website in websites
                if not check_submission_status(db, individual_id, ObjectId(website['_id']))
            ]

            if not websites_to_process:
                logging.info(f"All submissions for {individual_name} are already completed. Skipping to the next individual.")
                continue

            # Loop through remaining websites for this individual
            for website in websites_to_process:
                website_id = ObjectId(website['_id'])
                url = website['url']
                category = website['category']
                website_name = website['name']

                logging.info(f"Processing submission for {individual_name} on {website_name} (Website ID: {website_id})")

                form_data = load_form_data(db, website_name)
                field_locators = load_field_locators(db, website_name)

                retry_count = 0
                while retry_count < RETRY_COUNT:
                    try:
                        # Submit the form for the current website
                        await fill_and_submit_form(browser, url, individual_data, form_data, field_locators, db, website_id, category)

                        # If submission was successful, break out of retry loop
                        logging.info(f"Submission successful for {individual_name} on {website_name}. Moving to the next website.")
                        break

                    except Exception as e:
                        retry_count += 1
                        logging.error(f"Error submitting form for {individual_name} on {website_name}: {str(e)}")
                        if retry_count >= RETRY_COUNT:
                            logging.critical(f"Failed to submit form for {individual_name} on {website_name} after {RETRY_COUNT} attempts.")
                            raise RuntimeError(f"Stopping after {RETRY_COUNT} failed attempts for {website_name}")

                        # Delay before retrying
                        await asyncio.sleep(RETRY_DELAY)

            # Log completion for the individual
            logging.info(f"All websites processed for {individual_name}. Moving to the next individual.")

        # After processing all individuals and their websites
        remaining_tasks = any(
            not check_submission_status(db, ObjectId(individual['_id']), ObjectId(website['_id']))
            for individual in individual_data_list
            for website in websites
        )

        if not remaining_tasks:
            logging.info("All tasks are complete. Closing the browser.")
            await close_browser(browser)
        else:
            logging.info("Some tasks remain. Keeping the browser open for additional processing.")

    except Exception as e:
        logging.error(f"An error occurred while processing websites: {str(e)}", exc_info=True)
        raise


# Function to close the browser
async def close_browser(browser):
    try:
        if browser:
            await browser.close()
            logging.info("Browser closed successfully.")
    except Exception as e:
        logging.error(f"Error closing the browser: {str(e)}")
        raise
