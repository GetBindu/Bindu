"""
Web scraping service for marketplace product information
Enhanced with market intelligence and negotiation insights
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
import re
import logging
from datetime import datetime
import json
import random

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime
import json
from models import Product
import logging

# Import enhanced scraper
try:
    from enhanced_scraper import EnhancedMarketplaceScraper
    ENHANCED_SCRAPER_AVAILABLE = True
except ImportError:
    ENHANCED_SCRAPER_AVAILABLE = False
    logging.warning("Enhanced scraper not available, using fallback")

logger = logging.getLogger(__name__)

class MarketplaceScraper:
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    async def __aenter__(self):
        # User agent rotation for better success rate
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        ]
        
        self.session = aiohttp.ClientSession(
            headers={
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced scrape product information from marketplace URL
        Uses multiple strategies for better success rate
        """
        try:
            # Validate URL first
            if not self._is_valid_product_url(url):
                logger.warning(f"Invalid or non-product URL detected: {url}")
                return self._create_fallback_product(url)
            
            # Try enhanced scraper first if available
            if ENHANCED_SCRAPER_AVAILABLE:
                try:
                    async with EnhancedMarketplaceScraper() as enhanced_scraper:
                        result = await enhanced_scraper.scrape_product(url)
                        
                        # Better validation of scraping success
                        if self._validate_scraped_result(result, url):
                            logger.info(f"✅ Enhanced scraper succeeded for {url}")
                            return result
                        else:
                            logger.warning(f"⚠️ Enhanced scraper returned invalid data for {url}")
                except Exception as e:
                    logger.warning(f"Enhanced scraper failed: {e}, falling back to legacy scraper")
            
            # Fallback to legacy scraper
            domain = urlparse(url).netloc.lower()
            
            if 'olx' in domain:
                result = await self._scrape_olx(url)
            elif 'facebook' in domain:
                result = await self._scrape_facebook(url)
            elif 'quikr' in domain:
                result = await self._scrape_quikr(url)
            else:
                # Generic scraper for unknown platforms
                result = await self._scrape_generic(url)
            
            # Validate the result
            if self._validate_scraped_result(result, url):
                return result
            else:
                logger.warning(f"Legacy scraper returned invalid data for {url}")
                return self._create_fallback_product(url)
                
        except Exception as e:
            error_msg = str(e) or "Unknown error occurred during scraping"
            logger.error(f"Error scraping {url}: {error_msg}")
            logger.exception("Full exception details:")
            
            # Return fallback product instead of None
            return self._create_fallback_product(url)
    
    async def _scrape_olx(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape OLX product listing with robust fallback handling"""
        try:
            # Add retry logic with much shorter timeout for better reliability
            for attempt in range(3):  # Max 3 attempts
                try:
                    logger.info(f"Scraping OLX attempt {attempt + 1}: {url}")
                    timeout = aiohttp.ClientTimeout(total=8, connect=3)  # Much shorter timeout
                    
                    # Add random delay between attempts
                    if attempt > 0:
                        await asyncio.sleep(random.uniform(1, 2))
                    
                    async with self.session.get(url, timeout=timeout) as response:
                        if response.status != 200:
                            logger.warning(f"OLX returned status {response.status} for {url} (attempt {attempt + 1})")
                            if attempt == 1:  # Last attempt
                                return self._create_fallback_product(url)
                            continue
                        
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Check if page loaded properly
                        if not soup.find('title'):
                            logger.warning(f"OLX page appears to be empty for {url} (attempt {attempt + 1})")
                            if attempt == 1:  # Last attempt
                                return self._create_fallback_product(url)
                            continue
                        
                        # Extract product information with fallbacks
                        title = self._extract_olx_title(soup) or self._extract_title_from_url(url)
                        price = self._extract_olx_price(soup)
                        description = self._extract_olx_description(soup) or "Product description not available"
                        seller_info = self._extract_olx_seller(soup)
                        location = self._extract_olx_location(soup) or "Location not specified"
                        images = self._extract_olx_images(soup)
                        features = self._extract_olx_features(soup)
                        posted_date = self._extract_olx_date(soup)
                        
                        # If we couldn't extract basic info, try again or use fallback
                        # Debug logging
                        logger.info(f"Extracted title: '{title}', price: ₹{price}")
                        
                        if not title or price == 0:
                            logger.warning(f"Could not extract basic info from OLX {url} (attempt {attempt + 1})")
                            logger.info(f"Page title from HTML: {soup.find('title').get_text() if soup.find('title') else 'No title'}")
                            if attempt == 1:  # Last attempt
                                return self._create_fallback_product(url, title, price)
                            continue
                        
                        logger.info(f"Successfully scraped OLX product: {title} - ₹{price}")
                        return {
                            'title': title,
                            'description': description,
                            'price': price,
                            'original_price': price,
                            'seller_name': seller_info.get('name', 'OLX Seller'),
                            'seller_contact': seller_info.get('contact', 'Contact via OLX'),
                            'location': location,
                            'url': url,
                            'platform': 'OLX',
                            'category': self._categorize_product(title),
                            'condition': self._extract_condition(description),
                            'images': images,
                            'features': features,
                            'posted_date': posted_date,
                            'is_available': True,
                            'scraped_successfully': True
                        }
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout scraping OLX {url} (attempt {attempt + 1})")
                    if attempt == 2:  # Last attempt
                        logger.info("Max attempts reached, creating intelligent fallback")
                        return self._create_fallback_product(url)
                except Exception as e:
                    logger.warning(f"Error in scraping attempt {attempt + 1}: {str(e)}")
                    if attempt == 2:  # Last attempt
                        logger.info("Max attempts reached due to error, creating intelligent fallback")
                        return self._create_fallback_product(url)
                
        except Exception as e:
            error_msg = str(e) or "Unknown scraping error"
            logger.error(f"Error scraping OLX {url}: {error_msg}")
            logger.exception("Full exception details:")
            return self._create_fallback_product(url)

    def _create_fallback_product(self, url: str, title: str = None, price: int = None) -> Dict[str, Any]:
        """Create a fallback product when scraping fails"""
        extracted_title = title or self._extract_title_from_url(url)
        
        # Smart price estimation based on URL or title
        estimated_price = self._estimate_price_from_context(url, extracted_title) or price or 50000
        
        # Better platform detection
        domain = urlparse(url).netloc.lower()
        platform_name = 'OLX' if 'olx' in domain else 'Facebook Marketplace' if 'facebook' in domain else 'Marketplace'
        
        # Create more realistic description based on detected product type
        product_type = self._categorize_product(extracted_title)
        description = f"This {product_type.lower()} is available on {platform_name}. The AI negotiation agent will work with the seller to get you the best deal based on your target price and requirements."
        
        return {
            'title': extracted_title,
            'description': description,
            'price': estimated_price,
            'original_price': estimated_price,
            'seller_name': f'{platform_name} Seller',
            'seller_contact': f'Contact via {platform_name}',
            'location': 'India',
            'url': url,
            'platform': platform_name,
            'category': product_type,
            'condition': 'Used',
            'images': [],
            'features': ['AI-powered negotiation', 'Market price analysis', 'Smart offers'],
            'posted_date': datetime.now().isoformat(),
            'is_available': True,
            'scraped_successfully': False,
            'fallback_used': True,
            'note': f'AI will negotiate for this {extracted_title} based on your preferences. Product details will be confirmed during negotiation.'
        }

    def _is_valid_product_url(self, url: str) -> bool:
        """Validate if URL is a valid product listing URL"""
        domain = urlparse(url).netloc.lower()
        
        if 'olx' in domain:
            # OLX product URLs should contain /item/ and iid-
            return '/item/' in url and 'iid-' in url
        elif 'facebook' in domain:
            # Facebook marketplace URLs
            return '/marketplace/' in url and '/item/' in url
        elif 'quikr' in domain:
            # Quikr product URLs
            return '/p/' in url or '/item/' in url
        
        return True  # Allow other domains
    
    def _validate_scraped_result(self, result: Dict[str, Any], original_url: str) -> bool:
        """Validate if scraped result contains actual product data"""
        if not result:
            return False
        
        title = result.get('title', '')
        price = result.get('price', 0)
        
        # Check if we got redirected to a category page
        suspicious_phrases = [
            'buy & sell',
            'second hand',
            'used cars in',
            'mobiles in',
            'for sale',
            'listings in',
            'browse all'
        ]
        
        title_lower = title.lower()
        for phrase in suspicious_phrases:
            if phrase in title_lower and len(title_lower) > 50:
                logger.warning(f"Detected category/listing page: {title}")
                return False
        
        # Basic validation
        if not title or len(title) < 5:
            return False
        
        if price <= 0:
            logger.warning(f"Invalid price detected: {price}")
            return False
        
        return True

    def _estimate_price_from_context(self, url: str, title: str) -> int:
        """Estimate price based on title keywords only - DO NOT extract from URL to avoid IDs"""
        # REMOVED: URL-based price extraction to prevent ID confusion
        # The URL contains item IDs which should not be treated as prices
        
        # Price estimation based on product category keywords
        title_lower = title.lower()
        if any(word in title_lower for word in ['laptop', 'computer', 'macbook']):
            return 35000
        elif any(word in title_lower for word in ['phone', 'mobile', 'iphone', 'samsung']):
            return 15000
        elif any(word in title_lower for word in ['car', 'vehicle', 'auto']):
            return 300000
        elif any(word in title_lower for word in ['bike', 'motorcycle', 'scooter']):
            return 80000
        elif any(word in title_lower for word in ['furniture', 'sofa', 'table', 'chair']):
            return 25000
        elif any(word in title_lower for word in ['tv', 'television', 'monitor']):
            return 20000
        
        return 50000  # Default fallback

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a meaningful title from URL when scraping fails"""
        try:
            # Parse the URL to get meaningful parts
            parsed = urlparse(url)
            path = parsed.path
            
            # For OLX URLs, extract product info from path
            if 'olx.in' in parsed.netloc:
                # Extract category and location from OLX URL structure
                # Example: /en-in/item/mobile-phones-c1453-used-iphone-in-arumbakkam-chennai-iid-1821022551
                parts = path.split('/')
                
                # Look for meaningful parts
                product_info = []
                for part in parts:
                    if 'iphone' in part.lower():
                        product_info.append('iPhone')
                    elif 'samsung' in part.lower():
                        product_info.append('Samsung Phone')
                    elif 'mobile-phone' in part.lower():
                        product_info.append('Mobile Phone')
                    elif 'laptop' in part.lower():
                        product_info.append('Laptop')
                    elif 'bike' in part.lower():
                        product_info.append('Bike')
                    elif 'car' in part.lower():
                        product_info.append('Car')
                    
                    # Extract location
                    if any(city in part.lower() for city in ['chennai', 'mumbai', 'delhi', 'bangalore', 'hyderabad', 'pune', 'kolkata']):
                        location_part = part.replace('-', ' ').title()
                        if len(location_part) > 3:
                            product_info.append(f"in {location_part}")
                
                if product_info:
                    return ' '.join(product_info)
            
            # Fallback to generic extraction
            title_parts = re.sub(r'[/_\-]', ' ', path).strip()
            title_parts = re.sub(r'\d+', '', title_parts)  # Remove numbers
            words = [word.capitalize() for word in title_parts.split() if len(word) > 2]
            
            # Filter out common URL words
            filtered_words = [word for word in words if word.lower() not in ['item', 'iid', 'www', 'com', 'in', 'en']]
            
            return ' '.join(filtered_words[:6]) if filtered_words else "Marketplace Product"
            
        except Exception as e:
            logger.warning(f"Error extracting title from URL: {e}")
            return "Marketplace Product"
    
    def _extract_olx_title(self, soup: BeautifulSoup) -> str:
        """Extract product title from OLX with multiple fallback strategies"""
        # Updated selectors for current OLX structure
        selectors = [
            'h1[data-aut-id="itemTitle"]',
            '[data-testid="ad-title"]',
            'h1.pds-ad-title',
            'h1._1k7g5',
            'h1.kY95w',
            '.ad-title h1',
            '.it-ttl',
            'h1',  # Any h1 tag
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                title = element.get_text(strip=True)
                # Validate title - should not be category page indicators
                if (title and len(title) > 5 and len(title) < 200 and 
                    not self._is_category_title(title)):
                    logger.info(f"Found valid title with selector '{selector}': {title}")
                    return title[:100]  # Limit length
        
        # Try meta title as fallback
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content')
            if not self._is_category_title(title):
                return title[:100]
        
        # Try page title as last resort
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Extract product name from page title
            title = re.sub(r'\s*\|\s*OLX.*$', '', title)  # Remove " | OLX..." suffix
            if not self._is_category_title(title) and len(title) > 5:
                return title[:100]
        
        return None
    
    def _is_category_title(self, title: str) -> bool:
        """Check if title indicates a category/listing page rather than product page"""
        title_lower = title.lower()
        category_indicators = [
            'buy & sell',
            'second hand',
            'used cars in',
            'mobiles in',
            'bikes in',
            'for sale',
            'listings in',
            'browse all',
            'find ads',
            'classified',
            'olx.in'
        ]
        
        return any(indicator in title_lower for indicator in category_indicators)
    
    def _extract_olx_price(self, soup: BeautifulSoup) -> int:
        """Extract price from OLX listing prioritizing rupee symbol"""
        # PRIORITY 1: OLX-specific price selectors
        priority_selectors = [
            'span[data-aut-id="itemPrice"]',      # Primary OLX price selector
            '[data-testid="ad-price"]',           # Alternative price selector
            'span.notranslate',                   # Price often in notranslate spans
        ]
        
        # PRIORITY 2: Generic price selectors
        secondary_selectors = [
            '.price-text',
            '.ad-price',
            '._6eme8',
            '.x-1f6kntn',
            '.kxOcF',
            'span[class*="Price"]',               # Any span with "Price" in class
            'div[class*="price"]',                # Any div with "price" in class
        ]
        
        # PRIORITY 1: Try OLX-specific selectors first
        for selector in priority_selectors:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get_text(strip=True)
                if price_text and ('₹' in price_text or 'Rs' in price_text):
                    price = self._parse_price(price_text)
                    if price > 0:
                        logger.info(f"OLX price found via priority selector {selector}: ₹{price}")
                        return price
        
        # PRIORITY 2: Try secondary selectors
        for selector in secondary_selectors:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get_text(strip=True)
                if price_text:
                    price = self._parse_price(price_text)
                    if price > 0:
                        logger.info(f"OLX price found via secondary selector {selector}: ₹{price}")
                        return price
        
        # Search for price in structured data (JSON-LD)
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'offers' in data:
                    offers = data['offers']
                    if isinstance(offers, dict) and 'price' in offers:
                        price = int(float(offers['price']))
                        if price > 0:
                            logger.info(f"Found price in JSON-LD: ₹{price}")
                            return price
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        # Last resort: search all text but be more selective
        price_containers = soup.find_all(['div', 'span'], class_=re.compile(r'price|cost|amount'))
        for container in price_containers:
            price_text = container.get_text(strip=True)
            price = self._parse_price(price_text)
            if price > 0:
                logger.info(f"Found price in price container: ₹{price}")
                return price
        
        return 0

    def _parse_price(self, text: str) -> int:
        """Parse price from text with Indian Rupee symbol priority"""
        if not text:
            return 0
            
        # Remove common non-price text but preserve rupee symbols
        text = re.sub(r'(per|month|year|day|week)', '', text, flags=re.IGNORECASE)
        
        # PRIORITY 1: Indian Rupee symbol patterns (₹)
        rupee_patterns = [
            r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',      # ₹50,000 or ₹50000.00
            r'₹\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac)', # ₹5.5 lakh
            r'₹\s*(\d+(?:\.\d+)?)\s*(?:crore)',    # ₹1.2 crore
        ]
        
        for pattern in rupee_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = match.replace(',', '')
                    price = float(price_str)
                    
                    # Handle lakh/crore multipliers
                    if 'lakh' in text.lower() or 'lac' in text.lower():
                        price = int(price * 100000)  # 1 lakh = 1,00,000
                    elif 'crore' in text.lower():
                        price = int(price * 10000000)  # 1 crore = 1,00,00,000
                    else:
                        price = int(price)
                    
                    # Reasonable price range check for Indian market
                    if 50 <= price <= 50000000:  # ₹50 to ₹5 crore
                        logger.info(f"Found price with ₹ symbol: ₹{price:,}")
                        return price
                except (ValueError, TypeError):
                    continue
        
        # PRIORITY 2: Alternative Indian currency formats
        alt_patterns = [
            r'Rs\.?\s*(\d+(?:,\d+)*)',            # Rs.50000 or Rs. 50,000
            r'INR\s*(\d+(?:,\d+)*)',              # INR 50000
            r'rupees?\s*(\d+(?:,\d+)*)',          # rupees 50000
            r'(\d+(?:\.\d+)?)\s*lakh',            # 5 lakh or 5.5 lakh
            r'(\d+(?:\.\d+)?)\s*crore',           # 2 crore or 2.5 crore
        ]
        
        for pattern in alt_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Handle lakh/crore conversion
                    if 'lakh' in pattern:
                        price = int(float(match) * 100000)  # Convert lakh to number
                        logger.info(f"Found price in lakh: ₹{price:,}")
                    elif 'crore' in pattern:
                        price = int(float(match) * 10000000)  # Convert crore to number
                        logger.info(f"Found price in crore: ₹{price:,}")
                    else:
                        price = int(match.replace(',', ''))
                        logger.info(f"Found price with Rs/INR: ₹{price:,}")
                    
                    if 50 <= price <= 50000000:
                        return price
                except ValueError:
                    continue
        
        # PRIORITY 3: Numbers only (be more selective to avoid IDs)
        # Only consider numbers that appear in price-like contexts
        number_patterns = [
            r'(?:price|cost|amount|value|worth)[\s:]*(\d{3,}(?:,\d+)*)',  # "Price: 50000"
            r'(\d{3,}(?:,\d+)*)\s*(?:only|/-|/\-)',                      # "50000 only" or "50000/-"
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price = int(match.replace(',', ''))
                    # More restrictive range for bare numbers
                    if 500 <= price <= 10000000:
                        logger.info(f"Found price from context: ₹{price:,}")
                        return price
                except ValueError:
                    continue
        
        return 0
    
    def _extract_olx_description(self, soup: BeautifulSoup) -> str:
        """Extract product description from OLX"""
        selectors = [
            '[data-aut-id="itemDescriptionText"]',
            '.description-text',
            '.ad-description'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return ""
    
    def _extract_olx_seller(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract seller information from OLX"""
        seller_info = {'name': 'Unknown', 'contact': ''}
        
        # Try to find seller name
        name_selectors = [
            '[data-aut-id="profileName"]',
            '.seller-name',
            '.profile-name'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                seller_info['name'] = element.get_text(strip=True)
                break
        
        # Try to find contact (usually hidden, may need interaction)
        contact_selectors = [
            '[data-aut-id="chatButton"]',
            '.contact-number',
            '.seller-phone'
        ]
        
        for selector in contact_selectors:
            element = soup.select_one(selector)
            if element and 'href' in element.attrs:
                # Extract phone from tel: link
                tel_match = re.search(r'tel:(\d+)', element['href'])
                if tel_match:
                    seller_info['contact'] = tel_match.group(1)
                    break
        
        return seller_info
    
    def _extract_olx_location(self, soup: BeautifulSoup) -> str:
        """Extract location from OLX listing"""
        selectors = [
            '[data-aut-id="itemLocation"]',
            '.location-text',
            '.ad-location'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return "Unknown Location"
    
    def _extract_olx_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract product images from OLX"""
        images = []
        
        # Look for image elements
        img_selectors = [
            '.gallery-image img',
            '.image-gallery img',
            '[data-aut-id="defaultImg"]'
        ]
        
        for selector in img_selectors:
            elements = soup.select(selector)
            for img in elements:
                src = img.get('src') or img.get('data-src')
                if src and src not in images:
                    images.append(src)
        
        return images[:5]  # Limit to 5 images
    
    def _extract_olx_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract product features/specifications from OLX"""
        features = []
        
        # Look for feature lists
        feature_selectors = [
            '.features-list li',
            '.specifications li',
            '.details-list li'
        ]
        
        for selector in feature_selectors:
            elements = soup.select(selector)
            for element in elements:
                feature_text = element.get_text(strip=True)
                if feature_text and feature_text not in features:
                    features.append(feature_text)
        
        return features[:10]  # Limit to 10 features
    
    def _extract_olx_date(self, soup: BeautifulSoup) -> datetime:
        """Extract posting date from OLX"""
        date_selectors = [
            '[data-aut-id="itemCreationDate"]',
            '.post-date',
            '.ad-date'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                # Parse various date formats
                return self._parse_date(date_text)
        
        return datetime.now()  # Default to current date
    
    async def _scrape_facebook(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape Facebook Marketplace listing"""
        # Facebook has heavy anti-scraping measures
        # This is a placeholder - in production, you'd need:
        # 1. Facebook API access
        # 2. Selenium with proper browser automation
        # 3. Proxy rotation
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Basic extraction (limited due to Facebook's dynamic content)
                title = soup.find('title')
                title_text = title.get_text() if title else "Facebook Marketplace Item"
                
                return {
                    'title': title_text,
                    'description': "Facebook Marketplace listing - detailed scraping requires API access",
                    'price': 0,
                    'original_price': 0,
                    'seller_name': 'Facebook User',
                    'seller_contact': '',
                    'location': 'Facebook Marketplace',
                    'url': url,
                    'platform': 'Facebook Marketplace',
                    'category': 'Unknown',
                    'condition': 'Unknown',
                    'images': [],
                    'features': [],
                    'posted_date': datetime.now(),
                    'is_available': True
                }
                
        except Exception as e:
            logger.error(f"Error scraping Facebook {url}: {e}")
            return None
    
    async def _scrape_quikr(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape Quikr listing"""
        # Similar implementation to OLX but with Quikr-specific selectors
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract basic information
                title = soup.find('h1')
                title_text = title.get_text(strip=True) if title else "Quikr Item"
                
                return {
                    'title': title_text,
                    'description': "Quikr listing - implementing specific selectors",
                    'price': 0,
                    'original_price': 0,
                    'seller_name': 'Quikr User',
                    'seller_contact': '',
                    'location': 'India',
                    'url': url,
                    'platform': 'Quikr',
                    'category': 'Unknown',
                    'condition': 'Unknown',
                    'images': [],
                    'features': [],
                    'posted_date': datetime.now(),
                    'is_available': True
                }
                
        except Exception as e:
            logger.error(f"Error scraping Quikr {url}: {e}")
            return None
    
    async def _scrape_generic(self, url: str) -> Optional[Dict[str, Any]]:
        """Generic scraper for unknown marketplaces"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract basic meta information
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else "Marketplace Item"
                
                description = soup.find('meta', attrs={'name': 'description'})
                desc_text = description.get('content', '') if description else ""
                
                return {
                    'title': title_text,
                    'description': desc_text,
                    'price': 0,
                    'original_price': 0,
                    'seller_name': 'Unknown Seller',
                    'seller_contact': '',
                    'location': 'Unknown',
                    'url': url,
                    'platform': urlparse(url).netloc,
                    'category': 'Unknown',
                    'condition': 'Unknown',
                    'images': [],
                    'features': [],
                    'posted_date': datetime.now(),
                    'is_available': True
                }
                
        except Exception as e:
            logger.error(f"Error with generic scraper {url}: {e}")
            return None
    
    def _categorize_product(self, title: str) -> str:
        """Categorize product based on title keywords"""
        title_lower = title.lower()
        
        # Electronics
        if any(word in title_lower for word in ['iphone', 'samsung', 'mobile', 'phone', 'smartphone']):
            return 'Mobile Phones'
        elif any(word in title_lower for word in ['laptop', 'macbook', 'computer', 'pc']):
            return 'Laptops & Computers'
        elif any(word in title_lower for word in ['tv', 'television', 'led', 'lcd']):
            return 'Electronics'
        
        # Vehicles
        elif any(word in title_lower for word in ['car', 'honda', 'maruti', 'hyundai', 'tata']):
            return 'Cars'
        elif any(word in title_lower for word in ['bike', 'motorcycle', 'activa', 'scooty']):
            return 'Vehicles'
        
        # Gaming
        elif any(word in title_lower for word in ['ps5', 'xbox', 'playstation', 'nintendo']):
            return 'Gaming'
        
        # Home & Garden
        elif any(word in title_lower for word in ['furniture', 'sofa', 'bed', 'table']):
            return 'Home & Garden'
        
        return 'Other'
    
    def _extract_condition(self, description: str) -> str:
        """Extract product condition from description"""
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ['excellent', 'perfect', 'like new', 'mint']):
            return 'Excellent'
        elif any(word in desc_lower for word in ['good', 'working', 'fine']):
            return 'Good'
        elif any(word in desc_lower for word in ['fair', 'used', 'normal wear']):
            return 'Fair'
        elif any(word in desc_lower for word in ['poor', 'damaged', 'broken']):
            return 'Poor'
        
        return 'Good'  # Default
    
    def _parse_date(self, date_text: str) -> datetime:
        """Parse various date formats"""
        try:
            date_lower = date_text.lower().strip()
            
            if 'today' in date_lower or 'just now' in date_lower:
                return datetime.now()
            elif 'yesterday' in date_lower:
                return datetime.now().replace(day=datetime.now().day - 1)
            elif 'days ago' in date_lower:
                days_match = re.search(r'(\d+)\s*days?\s*ago', date_lower)
                if days_match:
                    days = int(days_match.group(1))
                    return datetime.now().replace(day=datetime.now().day - days)
            
            # Try standard date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_text, fmt)
                except ValueError:
                    continue
            
        except Exception:
            pass
        
        return datetime.now()  # Fallback


class MarketIntelligence:
    """Enhanced market intelligence gathering for comprehensive product analysis"""
    
    def __init__(self):
        self.scraper = None
        self.category_price_ranges = {
            'Mobile Phones': {'min': 5000, 'max': 150000, 'depreciation': 0.2},
            'Laptops & Computers': {'min': 15000, 'max': 300000, 'depreciation': 0.25},
            'Cars': {'min': 100000, 'max': 5000000, 'depreciation': 0.15},
            'Vehicles': {'min': 20000, 'max': 200000, 'depreciation': 0.18},
            'Electronics': {'min': 2000, 'max': 100000, 'depreciation': 0.3},
            'Gaming': {'min': 5000, 'max': 80000, 'depreciation': 0.2},
            'Home & Garden': {'min': 1000, 'max': 150000, 'depreciation': 0.1}
        }
    
    async def comprehensive_product_analysis(self, product_data: Dict[str, Any], user_target: int, user_budget: int) -> Dict[str, Any]:
        """
        Perform comprehensive product analysis including market intelligence,
        negotiation points, and strategic recommendations
        """
        logger.debug(f"Starting comprehensive analysis with product_data type: {type(product_data)}")
        
        # Robust input validation
        if product_data is None:
            logger.warning("product_data is None, creating fallback")
            product_data = {
                'title': 'Unknown Product',
                'price': user_budget if user_budget > 0 else 10000,
                'category': 'Other',
                'condition': 'Good',
                'location': 'Unknown',
                'description': 'Product description not available'
            }
        elif not isinstance(product_data, dict):
            logger.warning(f"product_data is not a dict (type: {type(product_data)}), creating fallback")
            product_data = {
                'title': 'Unknown Product',
                'price': user_budget if user_budget > 0 else 10000,
                'category': 'Other',
                'condition': 'Good',
                'location': 'Unknown',
                'description': 'Product description not available'
            }
        elif not product_data:  # Empty dict
            logger.warning("product_data is empty dict, creating fallback")
            product_data = {
                'title': 'Unknown Product',
                'price': user_budget if user_budget > 0 else 10000,
                'category': 'Other',
                'condition': 'Good',
                'location': 'Unknown',
                'description': 'Product description not available'
            }
        
        try:
            
            title = product_data.get('title', 'Unknown Product')
            price = product_data.get('price', user_budget if user_budget > 0 else 10000)
            category = product_data.get('category', 'Other')
            condition = product_data.get('condition', 'Good')
            location = product_data.get('location', 'Unknown')
            description = product_data.get('description', 'Product description not available')
            
            # 1. Market Price Analysis
            market_analysis = await self.analyze_market_price(title, category, price)
            
            # 2. Product Condition Assessment  
            condition_analysis = self._analyze_product_condition(description, condition, price)
            
            # 3. Price Justification Analysis
            price_justification = self._analyze_price_justification(product_data, market_analysis)
            
            # 4. Generate Negotiation Talking Points
            talking_points = self._generate_negotiation_points(
                product_data, market_analysis, condition_analysis, user_target, user_budget
            )
            
            # 5. Strategic Recommendations
            strategy = self._generate_negotiation_strategy(
                price, user_target, user_budget, market_analysis, condition_analysis, product_data
            )
            
            # 6. Risk Assessment
            risk_analysis = self._assess_negotiation_risks(product_data, market_analysis)
            
            return {
                'market_analysis': market_analysis,
                'condition_analysis': condition_analysis,
                'price_justification': price_justification,
                'negotiation_points': talking_points,
                'strategy': strategy,
                'risk_assessment': risk_analysis,
                'confidence_score': self._calculate_confidence_score(market_analysis, condition_analysis),
                'recommended_actions': self._generate_action_plan(strategy, talking_points)
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            
            # Create fallback using product_data parameter (which is guaranteed to exist)
            try:
                # Safely access product_data parameter
                fallback_product_data = product_data if (product_data and isinstance(product_data, dict)) else {
                    'title': 'Unknown Product',
                    'price': user_budget if user_budget > 0 else 10000,
                    'category': 'Other',
                    'condition': 'Good',
                    'location': 'Unknown',
                    'description': 'Product description not available'
                }
            except NameError as ne:
                logger.error(f"NameError accessing product_data in fallback: {ne}")
                # This should never happen since product_data is a method parameter
                fallback_product_data = {
                    'title': 'Emergency Fallback Product',
                    'price': user_budget if user_budget > 0 else 10000,
                    'category': 'Other',
                    'condition': 'Good',
                    'location': 'Unknown',
                    'description': 'Emergency fallback due to scope issue'
                }
            
            return self._get_fallback_analysis(fallback_product_data, user_target, user_budget)
    
    async def analyze_market_price(self, product_title: str, category: str, current_price: int) -> Dict[str, Any]:
        """Enhanced market price analysis with category-specific intelligence"""
        try:
            # Get category-specific price ranges
            category_info = self.category_price_ranges.get(category, {
                'min': 1000, 'max': 100000, 'depreciation': 0.2
            })
            
            # Estimate market value based on category and features
            estimated_market_value = self._estimate_market_value(product_title, category, current_price)
            
            # Calculate depreciation factors
            depreciation_factor = self._calculate_depreciation(product_title, category)
            
            # Generate price insights
            price_insights = self._analyze_pricing_patterns(current_price, estimated_market_value, category_info)
            
            return {
                'estimated_market_value': estimated_market_value,
                'category_price_range': category_info,
                'price_comparison': {
                    'vs_category_min': ((current_price - category_info['min']) / category_info['min']) * 100,
                    'vs_category_max': ((current_price - category_info['max']) / category_info['max']) * 100,
                    'vs_estimated_value': ((current_price - estimated_market_value) / estimated_market_value) * 100
                },
                'depreciation_factor': depreciation_factor,
                'price_insights': price_insights,
                'market_position': self._determine_market_position(current_price, estimated_market_value),
                'negotiation_potential': self._assess_negotiation_potential(current_price, estimated_market_value)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market price: {e}")
            return self._get_fallback_market_analysis(current_price, category)
    
    def _analyze_product_condition(self, description: str, condition: str, price: int) -> Dict[str, Any]:
        """Analyze product condition and its impact on pricing"""
        desc_lower = description.lower()
        
        # Condition indicators
        positive_indicators = []
        negative_indicators = []
        
        # Positive condition keywords
        positive_keywords = [
            'excellent', 'perfect', 'mint', 'brand new', 'like new', 'unused',
            'warranty', 'box pack', 'original', 'pristine', 'immaculate'
        ]
        
        # Negative condition keywords  
        negative_keywords = [
            'damaged', 'broken', 'scratched', 'dent', 'crack', 'issue',
            'problem', 'fault', 'repair needed', 'not working', 'defect'
        ]
        
        # Maintenance keywords
        maintenance_keywords = [
            'serviced', 'maintained', 'cleaned', 'tested', 'working perfectly'
        ]
        
        for keyword in positive_keywords:
            if keyword in desc_lower:
                positive_indicators.append(keyword.title())
        
        for keyword in negative_keywords:
            if keyword in desc_lower:
                negative_indicators.append(keyword.title())
        
        maintenance_score = sum(1 for keyword in maintenance_keywords if keyword in desc_lower)
        
        # Calculate condition impact on price
        condition_multiplier = {
            'Excellent': 0.95,
            'Good': 0.85,
            'Fair': 0.75,
            'Poor': 0.60
        }.get(condition, 0.85)
        
        return {
            'condition': condition,
            'positive_indicators': positive_indicators,
            'negative_indicators': negative_indicators,
            'maintenance_score': maintenance_score,
            'condition_multiplier': condition_multiplier,
            'condition_adjustment': f"{int((1 - condition_multiplier) * 100)}% discount expected for condition",
            'red_flags': negative_indicators,
            'selling_points': positive_indicators
        }
    
    def _analyze_price_justification(self, product_data: Dict, market_analysis: Dict) -> Dict[str, Any]:
        """Analyze if the current price is justified"""
        current_price = product_data.get('price', 0)
        estimated_value = market_analysis.get('estimated_market_value', current_price)
        
        price_difference = current_price - estimated_value
        price_difference_pct = (price_difference / estimated_value) * 100 if estimated_value > 0 else 0
        
        justification_factors = []
        overpricing_reasons = []
        
        # Check for premium factors
        description = product_data.get('description', '').lower()
        title = product_data.get('title', '').lower()
        
        premium_keywords = ['warranty', 'original', 'accessories', 'bill', 'invoice', 'sealed']
        discount_keywords = ['urgent', 'quick sale', 'moving', 'need cash', 'negotiable']
        
        for keyword in premium_keywords:
            if keyword in description or keyword in title:
                justification_factors.append(f"Includes {keyword}")
        
        for keyword in discount_keywords:
            if keyword in description or keyword in title:
                overpricing_reasons.append(f"Seller indicates {keyword}")
        
        if price_difference_pct > 20:
            overpricing_reasons.append("Priced significantly above market average")
        elif price_difference_pct < -10:
            justification_factors.append("Competitively priced below market average")
        
        return {
            'is_overpriced': price_difference_pct > 15,
            'price_difference': price_difference,
            'price_difference_percentage': round(price_difference_pct, 1),
            'justification_factors': justification_factors,
            'overpricing_reasons': overpricing_reasons,
            'fair_price_estimate': int(estimated_value),
            'negotiation_room': max(0, int(price_difference * 0.7)) if price_difference > 0 else 0
        }
    
    def _generate_negotiation_points(self, product_data: Dict, market_analysis: Dict, 
                                   condition_analysis: Dict, user_target: int, user_budget: int) -> Dict[str, Any]:
        """Generate comprehensive negotiation talking points"""
        
        talking_points = {
            'opening_points': [],
            'price_justification': [],
            'condition_concerns': [],
            'market_comparisons': [],
            'urgency_factors': [],
            'value_propositions': [],
            'closing_arguments': []
        }
        
        current_price = product_data.get('price', 0)
        estimated_value = market_analysis.get('estimated_market_value', current_price)
        
        # Opening negotiation points
        talking_points['opening_points'] = [
            f"I'm interested in this {product_data.get('category', 'item')}",
            "I've been researching similar products in the market",
            f"My budget is around ₹{user_target:,} for this type of product"
        ]
        
        # Price justification points
        if current_price > estimated_value:
            diff_pct = ((current_price - estimated_value) / estimated_value) * 100
            talking_points['price_justification'].append(
                f"Based on market research, similar items are selling for around ₹{estimated_value:,}"
            )
            talking_points['price_justification'].append(
                f"Your asking price is {diff_pct:.0f}% above the market average"
            )
        
        # Condition-based points
        if condition_analysis['negative_indicators']:
            talking_points['condition_concerns'].extend([
                f"I noticed the listing mentions: {', '.join(condition_analysis['negative_indicators'][:2])}",
                "Given the condition, I'd need to factor in potential repair or replacement costs"
            ])
        
        if condition_analysis['condition'] != 'Excellent':
            expected_discount = int((1 - condition_analysis['condition_multiplier']) * 100)
            talking_points['condition_concerns'].append(
                f"For {condition_analysis['condition'].lower()} condition items, "
                f"I typically expect around {expected_discount}% off retail value"
            )
        
        # Market comparison points
        category_range = market_analysis.get('category_price_range', {})
        if category_range and current_price > category_range.get('min', 0):
            talking_points['market_comparisons'].append(
                f"I've seen similar {product_data.get('category', 'items')} "
                f"starting from ₹{category_range['min']:,} in the market"
            )
        
        # Urgency and seller motivation
        description_lower = product_data.get('description', '').lower()
        urgent_keywords = ['urgent', 'quick sale', 'moving', 'immediate', 'asap']
        if any(keyword in description_lower for keyword in urgent_keywords):
            talking_points['urgency_factors'].append(
                "I can proceed immediately if we can agree on a fair price"
            )
            talking_points['urgency_factors'].append(
                "I understand you're looking for a quick sale"
            )
        
        # Value propositions for seller
        talking_points['value_propositions'] = [
            "I'm a serious buyer with cash ready",
            "No financing delays or complications",
            "Can complete the transaction quickly"
        ]
        
        # Calculate target offer
        target_offer = min(user_target, int(estimated_value * 0.9))
        talking_points['closing_arguments'] = [
            f"I can offer ₹{target_offer:,} for an immediate purchase",
            "This is a fair offer considering the current market conditions",
            "Let me know if this works for you"
        ]
        
        return talking_points
    
    def _generate_negotiation_strategy(self, current_price: int, user_target: int, 
                                     user_budget: int, market_analysis: Dict, condition_analysis: Dict, 
                                     product_data: Dict = None) -> Dict[str, Any]:
        """Generate comprehensive negotiation strategy"""
        
        estimated_value = market_analysis.get('estimated_market_value', current_price)
        negotiation_room = market_analysis.get('negotiation_potential', 0.15)
        
        # Calculate strategy parameters
        max_reasonable_offer = int(estimated_value * (1 - negotiation_room))
        opening_offer = min(user_target, max_reasonable_offer)
        fallback_offer = min(user_budget, int(estimated_value * 0.95))
        
        strategy = {
            'approach': 'data_driven',  # vs emotional, aggressive, etc.
            'opening_offer': opening_offer,
            'target_price': user_target,
            'maximum_budget': user_budget,
            'fallback_offer': fallback_offer,
            'estimated_fair_value': int(estimated_value),
            'negotiation_phases': [],
            'key_tactics': [],
            'success_probability': 0.0,
            'recommended_timeline': 'immediate'  # vs gradual, patient
        }
        
        # Phase 1: Market-based opening
        strategy['negotiation_phases'].append({
            'phase': 1,
            'name': 'Market Research Opening',
            'offer': opening_offer,
            'message_tone': 'professional_analytical',
            'key_points': ['market research', 'fair pricing', 'serious buyer']
        })
        
        # Phase 2: Condition-based adjustment
        if condition_analysis['negative_indicators']:
            phase_2_offer = min(user_target, opening_offer + int((fallback_offer - opening_offer) * 0.3))
            strategy['negotiation_phases'].append({
                'phase': 2,
                'name': 'Condition Assessment',
                'offer': phase_2_offer,
                'message_tone': 'concerned_practical',
                'key_points': ['product condition', 'repair costs', 'risk mitigation']
            })
        
        # Phase 3: Final offer
        strategy['negotiation_phases'].append({
            'phase': 'final',
            'name': 'Best and Final Offer',
            'offer': fallback_offer,
            'message_tone': 'decisive_final',
            'key_points': ['final offer', 'immediate purchase', 'no further negotiation']
        })
        
        # Key tactics based on analysis
        if current_price > estimated_value * 1.2:
            strategy['key_tactics'].append('price_anchoring_with_data')
        
        if condition_analysis['negative_indicators']:
            strategy['key_tactics'].append('condition_based_discount')
        
        if product_data and 'urgent' in str(product_data.get('description', '')).lower():
            strategy['key_tactics'].append('time_sensitive_offer')
        
        strategy['key_tactics'].extend(['market_comparison', 'cash_buyer_advantage', 'immediate_closure'])
        
        # Calculate success probability
        price_reasonableness = max(0, min(1, 1 - (abs(opening_offer - estimated_value) / estimated_value)))
        market_position = 0.8 if current_price > estimated_value else 0.6
        condition_factor = condition_analysis['condition_multiplier']
        
        strategy['success_probability'] = (price_reasonableness * 0.4 + market_position * 0.3 + condition_factor * 0.3) * 100
        
        return strategy
    
    def _assess_negotiation_risks(self, product_data: Dict, market_analysis: Dict) -> Dict[str, Any]:
        """Assess risks in the negotiation"""
        
        risks = {
            'high_risks': [],
            'medium_risks': [],
            'low_risks': [],
            'mitigation_strategies': [],
            'red_flags': [],
            'overall_risk_level': 'medium'
        }
        
        current_price = product_data.get('price', 0)
        estimated_value = market_analysis.get('estimated_market_value', current_price)
        
        # Price-based risks
        if current_price < estimated_value * 0.7:
            risks['high_risks'].append("Price significantly below market - possible hidden issues")
            risks['red_flags'].append("suspiciously_low_price")
        
        if current_price > estimated_value * 1.5:
            risks['medium_risks'].append("Overpriced product - seller may be inflexible on price")
        
        # Product-based risks
        description = product_data.get('description', '').lower()
        if any(word in description for word in ['damaged', 'broken', 'issue', 'problem']):
            risks['high_risks'].append("Product has disclosed defects or issues")
        
        if product_data.get('condition') == 'Poor':
            risks['high_risks'].append("Poor condition may lead to additional costs")
        
        # Seller-based risks
        if 'urgent' in description and current_price < estimated_value:
            risks['medium_risks'].append("Urgent sale at low price - verify authenticity")
        
        # Location-based risks
        location = product_data.get('location', '')
        if not location or location == 'Unknown':
            risks['medium_risks'].append("Location not specified - transportation costs unclear")
        
        # Mitigation strategies
        risks['mitigation_strategies'] = [
            "Request additional photos and detailed condition report",
            "Arrange physical inspection before finalizing",
            "Verify seller credentials and product authenticity",
            "Factor in potential repair/replacement costs",
            "Set clear terms for transaction and handover"
        ]
        
        # Calculate overall risk level
        total_high_risks = len(risks['high_risks'])
        total_medium_risks = len(risks['medium_risks'])
        
        if total_high_risks >= 2:
            risks['overall_risk_level'] = 'high'
        elif total_high_risks == 1 or total_medium_risks >= 3:
            risks['overall_risk_level'] = 'medium'
        else:
            risks['overall_risk_level'] = 'low'
        
        return risks
    
    def _estimate_market_value(self, title: str, category: str, current_price: int) -> int:
        """Estimate market value based on product details and category"""
        category_info = self.category_price_ranges.get(category, {'min': 1000, 'max': 100000})
        
        # Base estimation on category median
        category_median = (category_info['min'] + category_info['max']) / 2
        
        # Adjust based on title keywords
        title_lower = title.lower()
        
        # Premium brand multipliers
        premium_multipliers = {
            'apple': 1.3, 'iphone': 1.3, 'macbook': 1.4,
            'samsung': 1.2, 'sony': 1.2, 'lg': 1.1,
            'mercedes': 1.5, 'bmw': 1.4, 'audi': 1.4,
            'premium': 1.2, 'pro': 1.15, 'plus': 1.1
        }
        
        multiplier = 1.0
        for brand, mult in premium_multipliers.items():
            if brand in title_lower:
                multiplier = max(multiplier, mult)
                break
        
        # Age-based depreciation estimation
        age_keywords = {
            '2024': 0.95, '2023': 0.85, '2022': 0.75, '2021': 0.65,
            'new': 1.0, 'old': 0.7, 'vintage': 0.5
        }
        
        age_factor = 0.8  # Default age factor
        for keyword, factor in age_keywords.items():
            if keyword in title_lower:
                age_factor = factor
                break
        
        # Calculate estimated value
        estimated_value = int(category_median * multiplier * age_factor)
        
        # If current price is reasonable, blend with it
        if category_info['min'] <= current_price <= category_info['max'] * 1.5:
            estimated_value = int((estimated_value + current_price) / 2)
        
        return max(category_info['min'], min(estimated_value, category_info['max']))
    
    def _calculate_depreciation(self, title: str, category: str) -> float:
        """Calculate depreciation factor based on product age and category"""
        category_info = self.category_price_ranges.get(category, {'depreciation': 0.2})
        base_depreciation = category_info['depreciation']
        
        title_lower = title.lower()
        
        # Estimate age from title
        current_year = 2025
        for year in range(2020, current_year + 1):
            if str(year) in title_lower:
                age = current_year - year
                return min(base_depreciation * age, 0.8)  # Max 80% depreciation
        
        # Default depreciation for used items
        return base_depreciation * 2  # Assume 2 years old if no year mentioned
    
    def _analyze_pricing_patterns(self, current_price: int, estimated_value: int, category_info: Dict) -> List[str]:
        """Analyze pricing patterns and generate insights"""
        insights = []
        
        price_vs_estimate = (current_price - estimated_value) / estimated_value * 100
        
        if price_vs_estimate > 25:
            insights.append("Significantly overpriced - strong negotiation potential")
        elif price_vs_estimate > 10:
            insights.append("Moderately overpriced - good negotiation room")
        elif price_vs_estimate < -10:
            insights.append("Below market value - may indicate urgency or condition issues")
        else:
            insights.append("Reasonably priced according to market standards")
        
        # Category-specific insights
        if current_price < category_info['min'] * 1.2:
            insights.append("Price at lower end of category range")
        elif current_price > category_info['max'] * 0.8:
            insights.append("Price at higher end of category range")
        
        return insights
    
    def _determine_market_position(self, current_price: int, estimated_value: int) -> str:
        """Determine market position of the product"""
        ratio = current_price / estimated_value if estimated_value > 0 else 1
        
        if ratio > 1.3:
            return "premium_priced"
        elif ratio > 1.1:
            return "above_market"
        elif ratio < 0.8:
            return "below_market"
        elif ratio < 0.9:
            return "competitive"
        else:
            return "market_average"
    
    def _assess_negotiation_potential(self, current_price: int, estimated_value: int) -> float:
        """Assess negotiation potential as a percentage"""
        if estimated_value <= 0:
            return 0.15  # Default 15%
        
        overpricing = max(0, (current_price - estimated_value) / estimated_value)
        
        # Base negotiation potential: 10-30% depending on overpricing
        potential = 0.1 + (overpricing * 0.5)
        
        return min(potential, 0.3)  # Cap at 30%
    
    def _get_fallback_market_analysis(self, current_price: int, category: str) -> Dict[str, Any]:
        """Fallback market analysis when full analysis fails"""
        category_info = self.category_price_ranges.get(category, {'min': 1000, 'max': 100000})
        estimated_value = (category_info['min'] + category_info['max']) / 2
        
        return {
            'estimated_market_value': int(estimated_value),
            'category_price_range': category_info,
            'price_comparison': {
                'vs_category_min': ((current_price - category_info['min']) / category_info['min']) * 100,
                'vs_category_max': ((current_price - category_info['max']) / category_info['max']) * 100,
                'vs_estimated_value': ((current_price - estimated_value) / estimated_value) * 100
            },
            'depreciation_factor': 0.2,
            'price_insights': ["Market analysis based on category averages"],
            'market_position': self._determine_market_position(current_price, estimated_value),
            'negotiation_potential': 0.15
        }
    
    def _calculate_confidence_score(self, market_analysis: Dict, condition_analysis: Dict) -> float:
        """Calculate confidence score for the analysis"""
        
        # Base confidence factors
        price_confidence = 0.7  # Moderate confidence in price analysis
        condition_confidence = 0.8 if condition_analysis['positive_indicators'] or condition_analysis['negative_indicators'] else 0.6
        market_confidence = 0.6  # Limited market data confidence
        
        # Adjust based on available data quality
        if market_analysis.get('negotiation_potential', 0) > 0.2:
            price_confidence += 0.1
        
        if len(condition_analysis.get('positive_indicators', [])) > 2:
            condition_confidence += 0.1
        
        overall_confidence = (price_confidence * 0.4 + condition_confidence * 0.3 + market_confidence * 0.3)
        
        return min(0.95, max(0.3, overall_confidence))  # Clamp between 30% and 95%
    
    def _generate_action_plan(self, strategy: Dict, talking_points: Dict) -> List[str]:
        """Generate recommended action plan"""
        actions = []
        
        # Pre-negotiation actions
        actions.append("Research similar products in your area for comparison")
        actions.append("Prepare list of questions about product condition and history")
        
        # Negotiation approach
        success_prob = strategy.get('success_probability', 50)
        if success_prob > 70:
            actions.append("Approach with confidence - analysis shows favorable negotiation position")
        elif success_prob < 40:
            actions.append("Proceed cautiously - consider if this is the right deal for you")
        
        # Specific tactical actions
        actions.append(f"Start with opening offer of ₹{strategy.get('opening_offer', 0):,}")
        actions.append("Use market data to justify your offer")
        
        if talking_points.get('condition_concerns'):
            actions.append("Address condition concerns early in negotiation")
        
        actions.append(f"Be prepared to go up to ₹{strategy.get('fallback_offer', 0):,} maximum")
        actions.append("Set clear timeline for decision to create urgency")
        
        return actions
    
    def _get_fallback_analysis(self, product_data: Dict, user_target: int, user_budget: int) -> Dict[str, Any]:
        """Fallback analysis when comprehensive analysis fails"""
        current_price = product_data.get('price', 0)
        category = product_data.get('category', 'Other')
        
        return {
            'market_analysis': self._get_fallback_market_analysis(current_price, category),
            'condition_analysis': {
                'condition': product_data.get('condition', 'Good'),
                'condition_multiplier': 0.85,
                'positive_indicators': [],
                'negative_indicators': [],
                'selling_points': ['Marketplace listing']
            },
            'price_justification': {
                'is_overpriced': current_price > user_budget,
                'negotiation_room': max(0, current_price - user_target),
                'fair_price_estimate': user_target
            },
            'negotiation_points': {
                'opening_points': [f"I'm interested in this {category}"],
                'price_justification': [f"My budget is around ₹{user_target:,}"],
                'closing_arguments': [f"I can offer ₹{user_target:,} for immediate purchase"]
            },
            'strategy': {
                'opening_offer': user_target,
                'success_probability': 60,
                'key_tactics': ['cash_buyer_advantage', 'immediate_closure']
            },
            'risk_assessment': {
                'overall_risk_level': 'medium',
                'mitigation_strategies': ['Verify product condition before purchase']
            },
            'confidence_score': 0.5,
            'recommended_actions': [
                f"Start negotiation at ₹{user_target:,}",
                "Verify product condition",
                "Complete transaction quickly if price agreed"
            ]
        }