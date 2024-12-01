from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
from PIL import Image
import io
import os
import re

def get_original_image_url(resized_url):
    """Convert resized image URL to original format"""
    # Pattern to match: /a/img/resize/HASH/catalog/ -> /a/img/catalog/
    original_url = re.sub(r'/a/img/resize/[^/]+/catalog/', '/a/img/catalog/', resized_url)
    return original_url

def test_selenium_scrape():
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        print("Browser initialized")
        
        driver.get("https://www.metacritic.com/browse/game/")
        print("Page loaded")
        
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'c-finderProductCard')))
        time.sleep(2)
        
        card = driver.find_element(By.CLASS_NAME, 'c-finderProductCard')
        title = card.find_element(By.CLASS_NAME, 'c-finderProductCard_titleHeading').text
        print(f"Found game: {title}")
        
        images = card.find_elements(By.TAG_NAME, 'img')
        print(f"Found {len(images)} image elements")
        
        # Find main game image
        main_images = [img for img in images if img.get_attribute('src') and 
                      'metacritic.com' in img.get_attribute('src') and 
                      not img.get_attribute('src').endswith('must-play.svg')]
        
        if main_images:
            resized_url = main_images[0].get_attribute('src')
            original_url = get_original_image_url(resized_url)
            print(f"\nResized URL: {resized_url}")
            print(f"Original URL: {original_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Try original URL first, fallback to resized if needed
            img_response = requests.get(original_url, headers=headers)
            if img_response.status_code != 200:
                print("Original URL failed, trying resized URL...")
                img_response = requests.get(resized_url, headers=headers)
            
            if img_response.status_code == 200:
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')])[:100]
                img_filename = f"test_image_{safe_title}.jpg"
                
                # Save raw image directly without processing
                with open(img_filename, 'wb') as f:
                    f.write(img_response.content)
                print(f"Successfully saved original image to: {img_filename}")
                return True
        else:
            print("No suitable image found")
            driver.save_screenshot("page_screenshot.png")
            print("Saved page screenshot for debugging")
        
        return False
        
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        return False
        
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Starting test image scrape with Selenium...")
    success = test_selenium_scrape()
    print(f"Test completed! Success: {success}")