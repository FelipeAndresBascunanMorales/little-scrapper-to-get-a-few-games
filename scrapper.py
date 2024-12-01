import requests
import concurrent.futures
from bs4 import BeautifulSoup
import pandas as pd
import os
from PIL import Image
import io
import urllib.parse

class MetacriticPaginatedScraper:
    def __init__(self):
        self.base_url = "https://www.metacritic.com/browse/game/"
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.session = requests.Session()

    def clean_image(self, img_data):
        try:
            img = Image.open(io.BytesIO(img_data))
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
            output = io.BytesIO()
            clean_img.save(output, format='JPEG', quality=95)
            return output.getvalue()
        except Exception as e:
            print(f"Error cleaning image: {str(e)}")
            return None

    def get_game_data_from_card(self, card):
        try:
            # Title
            title_elem = card.find('h3', class_='c-finderProductCard_titleHeading')
            title = title_elem.text.strip() if title_elem else 'N/A'
            
            # Score
            score_div = card.find('div', class_='c-siteReviewScore')
            metascore = score_div.text.strip() if score_div else 'N/A'
            
            # Description
            desc_div = card.find('div', class_='c-finderProductCard_description')
            description = desc_div.text.strip() if desc_div else 'N/A'
            
            # Release date and rating
            meta_div = card.find('div', class_='c-finderProductCard_meta')
            release_date = 'N/A'
            rating = 'N/A'
            
            if meta_div:
                date_span = meta_div.find('span', class_='u-text-uppercase')
                release_date = date_span.text.strip() if date_span else 'N/A'
                
                rating_span = meta_div.find('span', text=lambda t: t and 'Rated' in t)
                if rating_span and rating_span.parent:
                    rating = rating_span.parent.text.strip()

            # Image handling
            img_filename = 'N/A'
            img_container = card.find('div', class_='c-finderProductCard_img')
            if img_container and img_container.find('img'):
                img_url = img_container.find('img').get('src', '')
                if img_url:
                    # Ensure URL is absolute
                    if not img_url.startswith(('http://', 'https://')):
                        img_url = urllib.parse.urljoin('https://www.metacritic.com', img_url)
                    
                    try:
                        img_response = requests.get(img_url, headers=self.headers)
                        if img_response.status_code == 200:
                            clean_img_data = self.clean_image(img_response.content)
                            if clean_img_data:
                                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')])[:100]
                                img_filename = f"images/{safe_title}.jpg"
                                os.makedirs('images', exist_ok=True)
                                with open(img_filename, 'wb') as f:
                                    f.write(clean_img_data)
                    except Exception as e:
                        print(f"Error downloading image for {title}: {str(e)}")

            return {
                'title': title,
                'metascore': metascore,
                'description': description,
                'release_date': release_date,
                'rating': rating,
                'image_path': img_filename
            }
        except Exception as e:
            print(f"Error processing game card: {str(e)}")
            return None

    def scrape_platform_page(self, platform, page=1):
        try:
            url = f"{self.base_url}?platform={platform}&page={page}"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to get page {page} for {platform}: Status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            game_cards = soup.find_all('div', class_='c-finderProductCard')
            
            if not game_cards:
                print(f"No game cards found on page {page} for {platform}")
                return []
                
            games_data = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.get_game_data_from_card, card) 
                          for card in game_cards]
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        result['platform'] = platform
                        result['page'] = page
                        games_data.append(result)
            
            return games_data
        except Exception as e:
            print(f"Error scraping page {page} for {platform}: {str(e)}")
            return []

    def scrape_platform(self, platform, pages=10):
        all_games = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.scrape_platform_page, platform, page) 
                      for page in range(1, pages + 1)]
            
            for future in concurrent.futures.as_completed(futures):
                games = future.result()
                all_games.extend(games)
        
        return pd.DataFrame(all_games)

    def scrape_all(self):
        platforms = [
            'ps5', 'ps4', 'xbox-series-x', 'xbox-one', 
            'switch', 'pc', 'wii-u', '3ds'
        ]
        all_data = pd.DataFrame()
        
        for platform in platforms:
            print(f"Scraping {platform}...")
            platform_data = self.scrape_platform(platform)
            all_data = pd.concat([all_data, platform_data])
            print(f"Found {len(platform_data)} games for {platform}")
        
        # Save to CSV
        all_data.to_csv('metacritic_games_full.csv', index=False)
        print("\nScraping completed!")
        print(f"Total games scraped: {len(all_data)}")
        print("Data saved to metacritic_games_full.csv")

if __name__ == "__main__":
    scraper = MetacriticPaginatedScraper()
    scraper.scrape_all()