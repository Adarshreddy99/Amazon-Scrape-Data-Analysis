from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import random
import re
import json

class AdvancedAmazonScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        # Enhanced stealth options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Execute script to hide automation
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 20)
        self.base_url = "https://www.amazon.in"
    
    def scrape_amazon_products(self, keyword="soft toys", max_pages=200):
        """Enhanced scraping with better data extraction - SPONSORED PRODUCTS ONLY"""
        products = []
        
        for page in range(1, max_pages + 1):
            print(f"\n🔍 Scraping page {page} for '{keyword}'...")
            
            # Construct proper search URL with category filter
            search_url = f"{self.base_url}/s?k={keyword.replace(' ', '+')}&rh=n%3A1350380031&ref=sr_pg_{page}&page={page}"
            
            try:
                self.driver.get(search_url)
                
                # Wait for page to load completely
                time.sleep(random.uniform(4, 7))
                
                # Verify we're on the right page
                page_title = self.driver.title
                print(f"📄 Page title: {page_title}")
                
                # Find product containers
                product_containers = self.wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"]'))
                )
                
                print(f"📦 Found {len(product_containers)} product containers")
                
                # Extract products
                page_products = []
                sponsored_count = 0
                
                for i, container in enumerate(product_containers[:25]):
                    try:
                        # **CRITICAL CHANGE**: Check if sponsored FIRST before extracting data
                        if not self.is_sponsored_product(container):
                            print(f"❌ Skipped non-sponsored product {i+1}")
                            continue
                        
                        sponsored_count += 1
                        print(f"✅ Found sponsored product {sponsored_count}")
                        
                        product_data = self.extract_comprehensive_product_data(container)
                        
                        # Double-check that it's a valid soft toy product
                        if self.is_valid_soft_toy_product(product_data, keyword):
                            # Ensure sponsored flag is set to True
                            product_data['sponsored'] = True
                            page_products.append(product_data)
                            print(f"✅ Added sponsored product {len(page_products)}: {product_data['title'][:60]}...")
                            print(f"🏷️  Brand: {product_data['brand']} | Price: ₹{product_data['price']} | Rating: {product_data['rating']}⭐")
                        else:
                            print(f"❌ Sponsored product {sponsored_count} failed soft toy validation")
                            
                    except Exception as e:
                        print(f"❌ Error extracting product {i+1}: {str(e)[:100]}...")
                        continue
                
                products.extend(page_products)
                print(f"📊 Page {page} summary: {len(page_products)} sponsored products extracted out of {sponsored_count} sponsored products found")
                
                # Random delay between pages
                time.sleep(random.uniform(4, 7))
                
            except Exception as e:
                print(f"❌ Error scraping page {page}: {e}")
                continue
        
        print(f"\n🎉 Total scraped: {len(products)} SPONSORED products!")
        return products
    
    def is_sponsored_product(self, container):
        """Check if a product is sponsored using multiple detection methods"""
        try:
            # Method 1: Look for "Sponsored" text in various locations
            sponsored_selectors = [
                './/span[contains(text(), "Sponsored")]',
                './/span[contains(text(), "sponsored")]',
                './/div[contains(text(), "Sponsored")]',
                './/div[contains(text(), "sponsored")]',
                './/span[@class="a-color-secondary" and contains(text(), "Sponsored")]',
                './/span[contains(@class, "puis-sponsored-label")]'
            ]
            
            for selector in sponsored_selectors:
                try:
                    sponsored_elem = container.find_element(By.XPATH, selector)
                    if sponsored_elem:
                        print(f"🏷️  Sponsored product detected via selector: {selector}")
                        return True
                except:
                    continue
            
            # Method 2: Check for sponsored-specific CSS classes
            sponsored_classes = [
                '.puis-sponsored-label',
                '.s-sponsored-label',
                '.a-sponsored-label',
                '[data-sponsored="true"]'
            ]
            
            for css_class in sponsored_classes:
                try:
                    sponsored_elem = container.find_element(By.CSS_SELECTOR, css_class)
                    if sponsored_elem:
                        print(f"🏷️  Sponsored product detected via CSS class: {css_class}")
                        return True
                except:
                    continue
            
            # Method 3: Check for sponsored-related attributes
            try:
                if container.get_attribute('data-sponsored'):
                    print(f"🏷️  Sponsored product detected via data-sponsored attribute")
                    return True
            except:
                pass
            
            # Method 4: Check container HTML for sponsored indicators
            try:
                container_html = container.get_attribute('innerHTML')
                if 'sponsored' in container_html.lower():
                    print(f"🏷️  Sponsored product detected via innerHTML search")
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking sponsored status: {e}")
            return False
    
    def extract_comprehensive_product_data(self, container):
        """Extract comprehensive product data"""
        
        product_data = {
            'title': 'N/A',
            'brand': 'N/A',
            'rating': 0.0,
            'reviews': 0,
            'price': 0,
            'image_url': 'N/A',
            'product_url': 'N/A',
            'sponsored': True  # Always True since we only extract sponsored products
        }
        
        try:
            # 1. Extract Title
            title_selectors = [
                'h2.a-size-mini a span',
                'h2 a span',
                '.a-size-base-plus',
                '.a-size-medium.a-color-base',
                'h2.s-size-14 span'
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = container.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_elem.text.strip()
                    if title_text and len(title_text) > 10:
                        product_data['title'] = title_text
                        break
                except:
                    continue
            
            # 2. Extract Product URL
            try:
                link_elem = container.find_element(By.CSS_SELECTOR, 'h2 a')
                href = link_elem.get_attribute('href')
                if href:
                    product_data['product_url'] = href
            except:
                pass
            
            # 3. Extract Brand (ENHANCED METHOD)
            product_data['brand'] = self.extract_brand_advanced(product_data['title'], container)
            
            # 4. Extract Rating
            rating_selectors = [
                '.a-icon-alt',
                '[aria-label*="out of 5 stars"]',
                '.a-star-mini .a-icon-alt'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elem = container.find_element(By.CSS_SELECTOR, selector)
                    rating_text = rating_elem.get_attribute('textContent') or rating_elem.get_attribute('aria-label')
                    if rating_text:
                        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                        if rating_match:
                            rating_value = float(rating_match.group(1))
                            if 0 <= rating_value <= 5:
                                product_data['rating'] = rating_value
                                break
                except:
                    continue
            
            # 5. Extract Reviews Count
            review_selectors = [
                '.a-size-base.s-underline-text',
                'a.a-link-normal span.a-size-base',
                '.a-size-base'
            ]
            
            for selector in review_selectors:
                try:
                    review_elems = container.find_elements(By.CSS_SELECTOR, selector)
                    for elem in review_elems:
                        text = elem.text.strip()
                        if text and ('(' in text or re.search(r'\d+', text)):
                            review_match = re.search(r'[\(]?([\d,]+)[\)]?', text)
                            if review_match:
                                reviews_count = int(review_match.group(1).replace(',', ''))
                                if reviews_count > 0:
                                    product_data['reviews'] = reviews_count
                                    break
                    if product_data['reviews'] > 0:
                        break
                except:
                    continue
            
            # 6. Extract Price
            price_selectors = [
                '.a-price-whole',
                '.a-price .a-offscreen',
                '.a-price-symbol'
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = container.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip() or price_elem.get_attribute('textContent')
                    if price_text:
                        price_match = re.search(r'([\d,]+)', price_text.replace('₹', '').replace(',', ''))
                        if price_match:
                            price_value = int(price_match.group(1))
                            if price_value > 0:
                                product_data['price'] = price_value
                                break
                except:
                    continue
            
            # 7. Extract Image URL
            try:
                img_elem = container.find_element(By.CSS_SELECTOR, 'img.s-image')
                src = img_elem.get_attribute('src')
                if src and src.startswith('http'):
                    product_data['image_url'] = src
            except:
                pass
            
        except Exception as e:
            print(f"Error in extract_comprehensive_product_data: {e}")
        
        return product_data
    
    def extract_brand_advanced(self, title, container):
        """Enhanced brand extraction using multiple dynamic methods"""
        
        # Method 1: Look for actual brand element on page
        brand_from_element = self.extract_brand_from_element(container)
        if brand_from_element:
            print(f"🏷️  Brand extracted from element: {brand_from_element}")
            return brand_from_element
        
        # Method 2: Extract from title using NLP patterns
        brand_from_title = self.extract_brand_from_title_nlp(title)
        if brand_from_title:
            print(f"🏷️  Brand extracted from title NLP: {brand_from_title}")
            return brand_from_title
        
        # Method 3: Fallback to predefined list
        brand_from_predefined = self.extract_brand_from_predefined_list(title)
        if brand_from_predefined != "Generic":
            print(f"🏷️  Brand extracted from predefined list: {brand_from_predefined}")
            return brand_from_predefined
        
        print(f"🏷️  Brand defaulted to: Generic")
        return "Generic"
    
    def extract_brand_from_element(self, container):
        """Extract brand from actual Amazon page elements"""
        brand_selectors = [
            '.a-size-base-plus',
            '.a-link-normal .a-size-base',
            '[data-cy="brand-name"]',
            '.s-size-base-plus',
            '.a-color-secondary',
            '.a-size-base.a-color-secondary',
            'span.a-size-base-plus',
            'span.a-size-base.a-color-secondary'
        ]
        
        for selector in brand_selectors:
            try:
                brand_elements = container.find_elements(By.CSS_SELECTOR, selector)
                for elem in brand_elements:
                    brand_text = elem.text.strip()
                    if brand_text and self.is_valid_brand_name(brand_text):
                        return brand_text
            except:
                continue
        
        return None
    
    def extract_brand_from_title_nlp(self, title):
        """Extract brand from title using NLP patterns"""
        if not title or title == 'N/A':
            return None
        
        # Clean the title
        title_clean = re.sub(r'[^\w\s&\-\.]', ' ', title)
        words = title_clean.split()
        
        # Pattern 1: Brand name usually comes first (check first 1-3 words)
        for i in range(min(3, len(words))):
            potential_brand = ' '.join(words[:i+1])
            if self.is_valid_brand_name(potential_brand):
                return potential_brand
        
        # Pattern 2: Brand name patterns in title
        brand_patterns = [
            r'by\s+([A-Za-z\s&\-\.]+?)(?:\s|$)',
            r'"([A-Za-z\s&\-\.]+?)"',
            r'Brand:\s*([A-Za-z\s&\-\.]+?)(?:\s|$)',
            r'from\s+([A-Za-z\s&\-\.]+?)(?:\s|$)'
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                potential_brand = match.group(1).strip()
                if self.is_valid_brand_name(potential_brand):
                    return potential_brand
        
        # Pattern 3: Check if any word looks like a brand (capitalized, reasonable length)
        for word in words[:5]:  # Check first 5 words
            if self.is_valid_brand_name(word) and word[0].isupper():
                return word
        
        return None
    
    def is_valid_brand_name(self, text):
        """Validate if text looks like a brand name"""
        if not text:
            return False
        
        text = text.strip()
        
        # Exclude common non-brand words
        exclude_words = {
            'soft', 'toy', 'toys', 'plush', 'stuffed', 'teddy', 'bear', 'doll',
            'cm', 'inch', 'inches', 'size', 'color', 'colour', 'piece', 'pieces',
            'pack', 'set', 'amazon', 'delivery', 'prime', 'deal', 'offer', 'sale',
            'new', 'old', 'big', 'small', 'large', 'medium', 'mini', 'giant',
            'cute', 'adorable', 'beautiful', 'lovely', 'sweet', 'nice', 'good',
            'best', 'top', 'premium', 'quality', 'super', 'ultra', 'max',
            'baby', 'kids', 'children', 'child', 'adult', 'boy', 'girl',
            'red', 'blue', 'green', 'yellow', 'pink', 'white', 'black', 'brown',
            'with', 'and', 'for', 'the', 'a', 'an', 'is', 'in', 'on', 'at',
            'gift', 'birthday', 'christmas', 'valentine', 'festival'
        }
        
        text_lower = text.lower()
        
        # Check if it's an excluded word
        if text_lower in exclude_words:
            return False
        
        # Check reasonable length
        if len(text) < 2 or len(text) > 30:
            return False
        
        # Check if it contains mostly valid characters
        if not re.match(r'^[a-zA-Z\s&\-\.0-9]+$', text):
            return False
        
        # Check if it's not all numbers
        if text.isdigit():
            return False
        
        # Check if it's not all special characters
        if re.match(r'^[^a-zA-Z0-9]+$', text):
            return False
        
        return True
    
    def extract_brand_from_predefined_list(self, title):
        """Extract brand from predefined list (fallback method)"""
        if not title or title == 'N/A':
            return "Generic"
        
        # Enhanced soft toy brands list
        soft_toy_brands = [
            'Babique', 'CozyHug', 'VIH-AAN', 'Storio', 'Niku', 'Webby',
            'Dimpy', 'Tickles', 'Frantic', 'Ultra', 'Cuddles', 'Mebby',
            'Archies', 'Toyshine', 'Babyhug', 'Deals India', 'FunBlast',
            'GUND', 'Ty', 'Melissa & Doug', 'LOVEY DOVEY', 'Aldea',
            'odinbirds', 'SCOOBA', 'MGP Creation', 'Richy Toys', 'One94Store',
            'WILD REPUBLIC', 'Storescent', 'YBN', 'Mirada', 'Amazon Brand',
            'Jam & Honey', 'Hamleys', 'Fisher-Price', 'Mattel', 'Steiff',
            'Build-A-Bear', 'Aurora', 'Jellycat', 'IKEA', 'Disney',
            'Funskool', 'Kiddieland', 'Chicco', 'Vtech', 'LeapFrog',
            'Tomy', 'Playgro', 'Manhattan Toy', 'Lamaze', 'Bright Starts'
        ]
        
        title_lower = title.lower()
        
        # Check for exact brand matches
        for brand in soft_toy_brands:
            if brand.lower() in title_lower:
                return brand
        
        # Check for partial matches (for compound brands)
        for brand in soft_toy_brands:
            brand_parts = brand.lower().split()
            if len(brand_parts) > 1:
                for part in brand_parts:
                    if len(part) > 3 and part in title_lower:
                        return brand
        
        # Last resort: extract first word if it looks like a brand
        words = title.split()
        if words:
            first_word = words[0]
            if self.is_valid_brand_name(first_word) and first_word[0].isupper():
                return first_word
        
        return "Generic"
    
    def is_valid_soft_toy_product(self, product_data, keyword):
        """Validate if the product is actually a soft toy"""
        title = product_data['title'].lower()
        
        # Soft toy related keywords
        soft_toy_keywords = [
            'soft toy', 'plush', 'stuffed', 'teddy', 'bear', 'doll',
            'unicorn', 'elephant', 'dog', 'cat', 'panda', 'rabbit',
            'penguin', 'octopus', 'dinosaur', 'animal', 'toy', 'cushion',
            'pillow', 'huggable', 'cuddly', 'fluffy', 'furry', 'plushie',
            'stuffie', 'cuddle', 'squeeze', 'snuggle', 'comfort'
        ]
        
        # Exclude non-toy items
        exclude_keywords = [
            'shoe', 'sandal', 'footwear', 'slipper', 'boot', 'sneaker',
            'clothing', 'dress', 'shirt', 'pant', 'electronics', 'mobile',
            'phone', 'charger', 'cable', 'book', 'pen', 'pencil', 'bag',
            'backpack', 'bottle', 'cup', 'plate', 'bowl', 'spoon', 'fork'
        ]
        
        # Check for exclusions first
        for exclude in exclude_keywords:
            if exclude in title:
                return False
        
        # Check for soft toy keywords
        keyword_found = False
        for keyword in soft_toy_keywords:
            if keyword in title:
                keyword_found = True
                break
        
        # Additional validation: check if it has reasonable toy price
        reasonable_price = 50 <= product_data['price'] <= 10000
        
        return keyword_found and reasonable_price
    
    def close(self):
        self.driver.quit()

# Main execution
if __name__ == "__main__":
    print("🚀 Starting Amazon Soft Toys Scraper (SPONSORED PRODUCTS ONLY)...")
    print("🔧 Enhanced with Dynamic Brand Extraction")
    
    scraper = AdvancedAmazonScraper()
    
    try:
        # Scrape products
        products = scraper.scrape_amazon_products("soft toys", max_pages=100)
        
        if products:
            # Create DataFrame
            df = pd.DataFrame(products)
            
            # Verify all products are sponsored
            print(f"\n🔍 Verification: All {len(df)} products are sponsored: {df['sponsored'].all()}")
            
            # Brand analysis
            unique_brands = df['brand'].nunique()
            brand_counts = df['brand'].value_counts()
            
            print(f"\n🏷️  Brand Analysis:")
            print(f"   • Total Unique Brands Found: {unique_brands}")
            print(f"   • Top 10 Brands:")
            for i, (brand, count) in enumerate(brand_counts.head(10).items(), 1):
                print(f"     {i:2d}. {brand:<20} : {count:3d} products")
            
            # Save to CSV
            df.to_csv('amazon_soft_toys_sponsored_enhanced.csv', index=False)
            print(f"\n✅ Saved {len(products)} SPONSORED products to 'amazon_soft_toys_sponsored_enhanced.csv'")
            
            # Display summary
            print("\n📊 Enhanced Scraping Summary (SPONSORED PRODUCTS ONLY):")
            print(f"Total sponsored products: {len(products)}")
            print(f"Products with ratings: {len(df[df['rating'] > 0])}")
            print(f"Products with reviews: {len(df[df['reviews'] > 0])}")
            print(f"Products with prices: {len(df[df['price'] > 0])}")
            print(f"Products with valid brands: {len(df[df['brand'] != 'Generic'])}")
            print(f"Brand extraction success rate: {len(df[df['brand'] != 'Generic'])/len(df)*100:.1f}%")
            
            # Show sample data
            print("\n📋 Sample Enhanced Sponsored Products Data:")
            print(df[['title', 'brand', 'rating', 'reviews', 'price', 'sponsored']].head(10))
            
        else:
            print("❌ No sponsored products were found and scraped.")
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        
    finally:
        scraper.close()
        print("\n🔚 Enhanced scraping completed!")
