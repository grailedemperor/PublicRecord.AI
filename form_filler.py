from bot_detection import setup_browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from database import load_websites, load_form_data, load_field_locators, load_individual_data, log_to_database, upsert_submission_record, check_submission_status, update_submission_status
from models import advanced_field_matching

# Function to identify form fields based on locator type and value
def identify_field(browser, wait, field_name, locator_type, locator_value):
    try:
        # Use CDP function to interact with the form element
        if locator_type == By.ID:
            return wait.until(lambda d: browser.cdp.click_on_element(selector=f'#{locator_value}'))
        elif locator_type == By.NAME:
            return wait.until(lambda d: browser.cdp.click_on_element(selector=f'[name="{locator_value}"]'))
        elif locator_type == By.XPATH:
            return wait.until(lambda d: browser.cdp.click_on_element(selector=locator_value))
        elif locator_type == By.CSS_SELECTOR:
            return wait.until(lambda d: browser.cdp.click_on_element(selector=locator_value))
    except Exception as e:
        logging.error(f"Error locating field {field_name}: {e}")
        return None

# Function to handle the form-filling process
def handle_form_filling(browser, wait, individual_data, form_data, field_locators, individual_name, website_name, connection, model=None, vectorizer=None):
    try:
        if model and vectorizer:
            matched_fields = advanced_field_matching(browser, model, vectorizer)
        else:
            matched_fields = {}

        for field_name, (locator_type, locator_value, is_optional) in field_locators.items():
            field_value = individual_data.get(field_name) or form_data.get(field_name)
            
            if not field_value and is_optional:
                continue

            if field_name in matched_fields:
                field = matched_fields[field_name]
            else:
                field = identify_field(browser, wait, field_name, locator_type, locator_value)

            if field:
                browser.cdp.click_on_element(selector=field)
                browser.cdp.set_input_value(selector=field, value=field_value)
            else:
                error_message = f"Failed to locate field '{field_name}' for {individual_name} on {website_name} ({browser.get_current_url()})"
                logging.error(error_message)
                log_to_database(connection, "ERROR", error_message)
    except Exception as e:
        error_message = f"Error in form filling for {individual_name} on {website_name}: {str(e)}"
        logging.error(error_message)
        raise

# Function to handle the first step in a multi-step form process
def handle_first_step(browser, wait, individual_name, website_name):
    try:
        browser.cdp.click_on_element(selector="//input[@type='radio' and @value='Opt-In']")
        browser.cdp.click_on_element(selector="//input[@type='submit']")
        logging.info(f"First step (Opt-In) handled for {individual_name} on {website_name}")
    except Exception as e:
        error_message = f"Error in first step for {individual_name} on {website_name}: {str(e)}"
        logging.error(error_message)
        raise

# Function to scroll to the bottom of the page, if necessary
def scroll_to_bottom(browser):
    browser.cdp.scroll_to_page_bottom()

# Main function to fill and submit forms
def fill_and_submit_form(browser, url, individual_data, form_data, field_locators, connection, model=None, vectorizer=None, website_id=None, category=None):
    retry_count = 0
    max_retries = 3
    individual_name = f"{individual_data.get('first_name')} {individual_data.get('last_name')}"
    website_name = form_data.get('website_name')

    while retry_count < max_retries:
        try:
            browser.get(url)
            wait = WebDriverWait(browser, 15)

            if category == "multi-step":
                handle_first_step(browser, wait, individual_name, website_name)
            
            handle_form_filling(browser, wait, individual_data, form_data, field_locators, individual_name, website_name, connection, model, vectorizer)

            if "captcha" in category:
                captcha_element = find_captcha_element(browser)
                if captcha_element:
                    handle_captcha(browser, connection, individual_name, website_name)
                else:
                    logging.info(f"No CAPTCHA found for {individual_name} on {website_name} ({url})")
            
            scroll_to_bottom(browser)  # Scroll to the bottom if necessary
            
            browser.cdp.click_on_element(selector="//input[@type='submit']")

            success_message = f"Form submitted successfully for {individual_name} on {website_name} ({url})"
            logging.info(success_message)
            log_to_database(connection, "INFO", success_message)
            update_submission_status(connection, individual_data['_id'], website_id)
            
            break
        except Exception as e:
            error_message = f"Error occurred while submitting form for {individual_name} on {website_name}: {str(e)}"
            logging.error(error_message)
            log_to_database(connection, "ERROR", error_message)
            retry_count += 1
            if retry_count >= max_retries:
                browser.cdp.take_screenshot(path=f"error_{url.split('//')[-1].split('.')[0]}.png")
                break

# Asynchronous function to process websites and submit forms for individuals
async def process_websites_async(websites, connection, model=None, vectorizer=None, max_workers=5):
    loop = asyncio.get_event_loop()
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        individual_data_list = load_individual_data(connection)
        for website in websites:
            url = website['url']
            website_id = website['_id']
            category = website['category']
            form_data = load_form_data(connection, website['name'])
            field_locators = load_field_locators(connection, website['name'])

            for individual_data in individual_data_list:
                upsert_submission_record(connection, individual_data['_id'], website_id)

                if check_submission_status(connection, individual_data['_id'], website_id):
                    logging.info(f"Skipping submission for {individual_data['first_name']} on {website['name']} as it's already completed.")
                    continue

                tasks.append(loop.run_in_executor(
                    executor, 
                    fill_and_submit_form, 
                    setup_browser(), 
                    url, 
                    individual_data, 
                    form_data, 
                    field_locators, 
                    connection, 
                    model, 
                    vectorizer, 
                    website_id,
                    category  
                ))

        await asyncio.gather(*tasks)
