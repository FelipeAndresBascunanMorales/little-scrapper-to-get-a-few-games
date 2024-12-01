from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import pandas as pd
import os
import re
from datetime import datetime

class MetacriticScraper:
    def __init__(self):
        self.base_url = "https://www.metacritic.com/browse/game/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def get_original_image_url(self, resized_url):
        """Convert resized image URL to original format"""
        return re.sub(r'/a/img/resize/[^/]+/catalog/', '/a/img/catalog/', resized_url)

    def download_image(self, url, filename):
        """Download and save image, return True if successful"""
        try:
            img_response = requests.get(url, headers=self.headers)
            if img_response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(img_response.content)
                return True
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
        return False

    def extract_card_data(self, card, platform):
        """Extract all relevant data from a game card"""
        try:
            # Basic info
            title = card.find_element(By.CLASS_NAME, 'c-finderProductCard_titleHeading').text
            title = re.sub(r'^\d+\.\s*', '', title)  # Remove ranking number
            
            # Description
            description = card.find_element(By.CLASS_NAME, 'c-finderProductCard_description').text
            
            # Meta info (release date and rating)
            meta_div = card.find_element(By.CLASS_NAME, 'c-finderProductCard_meta')
            meta_spans = meta_div.find_elements(By.TAG_NAME, 'span')
            release_date = meta_spans[0].text if meta_spans else 'N/A'
            
            # Try to find rating
            rating = 'N/A'
            for span in meta_spans:
                if 'Rated' in span.text:
                    rating = span.text.replace('Rated', '').strip()
                    break
            
            # Metascore
            try:
                metascore = card.find_element(By.CLASS_NAME, 'c-siteReviewScore_xsmall').text
            except:
                metascore = 'N/A'
            
            # Game URL
            game_url = card.find_element(By.TAG_NAME, 'a').get_attribute('href')
            
            # Image handling
            images = card.find_elements(By.TAG_NAME, 'img')
            main_images = [img for img in images if img.get_attribute('src') and 
                          'metacritic.com' in img.get_attribute('src') and 
                          not img.get_attribute('src').endswith('must-play.svg')]
            
            image_filename = 'N/A'
            original_image_url = 'N/A'
            if main_images:
                resized_url = main_images[0].get_attribute('src')
                original_url = self.get_original_image_url(resized_url)
                
                # Create safe filename
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')])[:100]
                image_filename = f"images/{platform}/{safe_title}.jpg"
                original_image_url = original_url
                
                # Ensure directory exists
                os.makedirs(f"images/{platform}", exist_ok=True)
                
                # Download image
                if self.download_image(original_url, image_filename):
                    print(f"Downloaded image for: {title}")
                else:
                    print(f"Failed to download image for: {title}")
            
            return {
                'title': title,
                'platform': platform,
                'metascore': metascore,
                'release_date': release_date,
                'rating': rating,
                'description': description,
                'game_url': game_url,
                'image_filename': image_filename,
                'original_image_url': original_image_url
            }
            
        except Exception as e:
            print(f"Error extracting card data: {str(e)}")
            return None

    def scrape_platform(self, platform, pages=10):
        """Scrape specified number of pages for a platform"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=options)
            games_data = []
            
            for page in range(1, pages + 1):
                print(f"Scraping {platform} - Page {page}")
                url = f"{self.base_url}?platform={platform}&page={page}"
                driver.get(url)
                
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'c-finderProductCard')))
                time.sleep(2)
                
                cards = driver.find_elements(By.CLASS_NAME, 'c-finderProductCard')
                for card in cards:
                    data = self.extract_card_data(card, platform)
                    if data:
                        games_data.append(data)
                
                print(f"Processed {len(cards)} games on page {page}")
            
            return pd.DataFrame(games_data)
            
        except Exception as e:
            print(f"Error scraping platform {platform}: {str(e)}")
            return pd.DataFrame()
            
        finally:
            driver.quit()

    def scrape_all(self, platforms=None):
        """Scrape all specified platforms"""
        if platforms is None:
            platforms = ['ps5', 'ps4', 'xbox-series-x', 'xbox-one', 'switch', 'pc']
        
        all_data = pd.DataFrame()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for platform in platforms:
            print(f"\nStarting to scrape {platform}")
            platform_data = self.scrape_platform(platform)
            all_data = pd.concat([all_data, platform_data], ignore_index=True)
            
            # Save intermediate results
            platform_csv = f"data_{platform}_{timestamp}.csv"
            platform_data.to_csv(platform_csv, index=False, encoding='utf-8')
            print(f"Saved {platform} data to {platform_csv}")
        
        # Save complete dataset
        final_csv = f"metacritic_all_games_{timestamp}.csv"
        all_data.to_csv(final_csv, index=False, encoding='utf-8')
        print(f"\nComplete dataset saved to {final_csv}")
        print(f"Total games scraped: {len(all_data)}")
        
        return all_data

if __name__ == "__main__":
    scraper = MetacriticScraper()
    # Test with just one platform first
    scraper.scrape_all(['ps5'])  # Change this to scrape more platforms