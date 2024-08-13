import os
import logging
from brightdata import ScrapingBrowser
from selenium.webdriver.common.by import By

# Initialize the Scraping Browser with Bright Data credentials and CAPTCHA solving enabled
def setup_browser():
    host = os.getenv('BRIGHTDATA_HOST')
    port = os.getenv('BRIGHTDATA_PORT')
    username = os.getenv('BRIGHTDATA_USERNAME')
    password = os.getenv('BRIGHTDATA_PASSWORD')

    # Create a Scraping Browser instance with Bright Data's options
    browser = ScrapingBrowser(
        host=host,
        port=port,
        username=username,
        password=password,
        solve_captcha=True,  # Enable CAPTCHA solving
        logging=True,        # Enable logging
        debug_mode=True      # Enable debugging mode
    )

    return browser

# Function to handle CAPTCHA solving and submission
def handle_captcha(browser, individual_name, website_name):
    try:
        # Automatically handle the CAPTCHA using Bright Data's built-in feature
        captcha_result = browser.solve_captcha()
        if captcha_result:
            logging.info(f"Captcha solved and form submitted successfully for {individual_name} on {website_name}")
        else:
            error_message = f"Failed to solve CAPTCHA for {individual_name} on {website_name}"
            logging.error(error_message)
    except Exception as e:
        error_message = f"Error occurred while solving captcha for {individual_name} on {website_name}: {str(e)}"
        logging.error(error_message)
        raise

# Previous CAPTCHA handling code (commented out)
'''
# Function to find the CAPTCHA element on the page
def find_captcha_element(browser):
    captcha_locators = [
        (By.ID, "captcha"),
        (By.NAME, "captcha"),
        (By.XPATH, "//img[@alt='captcha']"),
        (By.XPATH, "//input[@type='text' and contains(@placeholder, 'captcha')]"),
        (By.CSS_SELECTOR, "img.captcha"),
    ]
    
    for locator_type, locator_value in captcha_locators:
        try:
            captcha_element = browser.find_element(locator_type, locator_value)
            if captcha_element.is_displayed():
                return captcha_element
        except:
            continue
    
    return None

def solve_captcha_with_service(captcha_image):
    API_KEY = os.getenv('API_KEY')

    if not API_KEY:
        raise ValueError("No API key found. Please set the API_KEY environment variable.")

    captcha_file = {'file': ('captcha.png', captcha_image)}

    response = requests.post(f"http://2captcha.com/in.php?key={API_KEY}&method=post", files=captcha_file)

    if response.text.startswith('OK|'):
        captcha_id = response.text.split('|')[1]
    else:
        raise Exception("Failed to submit captcha to 2Captcha: " + response.text)

    time.sleep(10)

    result = requests.get(f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}")

    while 'CAPCHA_NOT_READY' in result.text:
        time.sleep(5)
        result = requests.get(f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}")

    if result.text.startswith('OK|'):
        captcha_text = result.text.split('|')[1]
    else:
        raise Exception("Failed to retrieve captcha solution from 2Captcha: " + result.text)

    return captcha_text
'''
