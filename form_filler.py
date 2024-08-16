from bot_detection import setup_browser
from playwright.async_api import Page
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from database import load_websites, load_form_data, load_field_locators, load_individual_data, log_to_database, upsert_submission_record, check_submission_status, update_submission_status
from models import advanced_field_matching

# Function to identify form fields using Playwright
async def identify_field(page: Page, field_name, selector):
    try:
        # Wait for and click on the element
        await page.wait_for_selector(selector, timeout=2000)
        element = await page.query_selector(selector)
        return element
    except Exception as e:
        logging.error(f"Error locating field {field_name}: {e}")
        return None

# Function to handle the form-filling process
async def handle_form_filling(page: Page, individual_data, form_data, field_locators, individual_name, website_name, connection, model=None, vectorizer=None):
    try:
        if model and vectorizer:
            matched_fields = advanced_field_matching(page, model, vectorizer)
        else:
            matched_fields = {}

        for field_name, (selector, is_optional) in field_locators.items():
            field_value = individual_data.get(field_name) or form_data.get(field_name)

            if not field_value and is_optional:
                continue

            field = await identify_field(page, field_name, selector)

            if field:
                await field.fill(field_value)
            else:
                error_message = f"Failed to locate field '{field_name}' for {individual_name} on {website_name}"
                logging.error(error_message)
                log_to_database(connection, "ERROR", error_message)
    except Exception as e:
        error_message = f"Error in form filling for {individual_name} on {website_name}: {str(e)}"
        logging.error(error_message)
        raise

# Function to handle CAPTCHA solving
async def handle_captcha(page: Page, individual_name, website_name, connection):
    try:
        client = await page.context.new_cdp_session(page)
        solve_result = await client.send('Captcha.solve', {'detectTimeout': 30 * 1000})
        status = solve_result['status']

        if status == 'solve_finished':
            logging.info(f"Captcha solved for {individual_name} on {website_name}")
            log_to_database(connection, "INFO", f"Captcha solved for {individual_name} on {website_name}")
        else:
            error_message = f"Captcha solve failed for {individual_name} on {website_name}: {status}"
            logging.error(error_message)
            log_to_database(connection, "ERROR", error_message)
    except Exception as e:
        error_message = f"Error occurred while solving captcha for {individual_name} on {website_name}: {str(e)}"
        logging.error(error_message)
        log_to_database(connection, "ERROR", error_message)

# Function to scroll to the bottom of the page, if necessary
async def scroll_to_bottom(page: Page):
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

# Main function to fill and submit forms
async def fill_and_submit_form(browser, url, individual_data, form_data, field_locators, connection, model=None, vectorizer=None, website_id=None, category=None):
    retry_count = 0
    max_retries = 3

    # Log individual and form data for debugging
    logging.info(f"Received individual_data: {individual_data}")
    logging.info(f"Received form_data: {form_data}")

    individual_name = f"{individual_data.get('first name', 'Unknown')} {individual_data.get('last name', 'Unknown')}"
    website_name = form_data.get('website_name', 'Unknown')

    while retry_count < max_retries:
        try:
            logging.info(f"Attempting to create a new page for {individual_name} on {website_name}.")
            page = await browser.new_page()

            await page.goto(url)

            if category is None:
                logging.error(f"Category is missing for {website_name} ({url}) while processing {individual_name}. Skipping...")
                return

            logging.info(f"Processing category: {category} for {website_name}")

           # if category == "multi-step":
                #await handle_first_step(page, individual_name, website_name)

            await handle_form_filling(page, individual_data, form_data, field_locators, individual_name, website_name, connection, model, vectorizer)

            if "captcha" in category:
                await handle_captcha(page, individual_name, website_name, connection)

            await scroll_to_bottom(page)  # Scroll to the bottom if necessary

            await page.click("input[type='submit']")

            success_message = f"Form submitted successfully for {individual_name} on {website_name} ({url})"
            logging.info(success_message)
            log_to_database(connection, "INFO", success_message)
            update_submission_status(connection, individual_data['_id'], website_id)

            break
        except Exception as e:
            error_message = f"Error occurred while submitting form for {individual_name} on {website_name}({url}): {str(e)}"
            logging.error(error_message)
            log_to_database(connection, "ERROR", error_message)
            retry_count += 1
            if retry_count >= max_retries:
                await page.screenshot(path=f"error_{url.split('//')[-1].split('.')[0]}.png")
                break
        finally:
            await page.close()

# Asynchronous function to process websites and submit forms for individuals
async def process_websites_async(websites, connection, model=None, vectorizer=None, browser=None, max_workers=5):
    loop = asyncio.get_event_loop()
    tasks = []
    individual_data_list = load_individual_data(connection)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for website in websites:
            url = website['url']
            website_id = website['_id']
            category = website['category']

            if category is None:
                logging.error(f"Category missing for website: {website['name']} at {url}. Skipping...")
                continue

            form_data = load_form_data(connection, website['name'])
            field_locators = load_field_locators(connection, website['name'])

            for individual_data in individual_data_list:
                upsert_submission_record(connection, individual_data['_id'], website_id)

                if check_submission_status(connection, individual_data['_id'], website_id):
                    logging.info(f"Skipping submission for {individual_data['first_name']} on {website['name']} as it's already completed.")
                    continue

                tasks.append(asyncio.create_task(
                    fill_and_submit_form(
                        browser, 
                        url, 
                        individual_data, 
                        form_data, 
                        field_locators, 
                        connection, 
                        model, 
                        vectorizer, 
                        website_id,
                        category 
                    )
                ))

        await asyncio.gather(*tasks)


