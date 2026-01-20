"""
Enhanced Web Scraping Service with Multiple Tools and Fallback Strategies
Supports: Playwright, Selenium, CloudScraper, and traditional HTTP requests
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime
import json
import random
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class EnhancedMarketplaceScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
        self.success_strategies = {}  # Track which strategies work for which sites
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15, connect=5),
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def scrape_product(self, url: str) -> Dict[str, Any]:
        """
        Enhanced scraping with multiple fallback strategies
        """
        domain = urlparse(url).netloc.lower()
        logger.info(f"Starting enhanced scraping for {domain}")
        
        # Strategy 1: Enhanced HTTP first (faster)
        try:
            logger.info(f"Trying enhanced HTTP for {domain}")
            result = await self._scrape_with_enhanced_http(url)
            if result.get('scraped_successfully'):
                logger.info(f"Enhanced HTTP successful for {domain}")
                return result
        except Exception as e:
            logger.warning(f"Enhanced HTTP failed for {domain}: {e}")
        
        # Strategy 2: CloudScraper (handles most anti-bot measures)
        try:
            logger.info(f"Trying CloudScraper for {domain}")
            result = await self._scrape_with_cloudscraper(url)
            if result.get('scraped_successfully'):
                logger.info(f"CloudScraper successful for {domain}")
                return result
        except Exception as e:
            logger.warning(f"CloudScraper failed for {domain}: {e}")
        
        # Strategy 3: Mobile User Agent approach
        try:
            logger.info(f"Trying mobile UA for {domain}")
            result = await self._scrape_with_mobile_ua(url)
            if result.get('scraped_successfully'):
                logger.info(f"Mobile UA successful for {domain}")
                return result
        except Exception as e:
            logger.warning(f"Mobile UA approach failed for {domain}: {e}")
        
        # Strategy 4: Playwright (JavaScript rendering)
        try:
            logger.info(f"Trying Playwright for {domain}")
            result = await self._scrape_with_playwright(url)
            if result.get('scraped_successfully'):
                logger.info(f"Playwright successful for {domain}")
                return result
        except Exception as e:
            logger.warning(f"Playwright failed for {domain}: {e}")
        
        # Fallback: Create intelligent product data based on URL analysis
        logger.warning(f"All scraping strategies failed for {url}, using intelligent fallback")
        return self._create_intelligent_fallback(url)

    async def _scrape_with_cloudscraper(self, url: str) -> Dict[str, Any]:
        """Scrape using CloudScraper to bypass Cloudflare protection"""
        try:
            import cloudscraper
            
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            
            # Reduced timeout to fail faster
            response = scraper.get(url, timeout=10)
            response.raise_for_status()
            
            return await self._parse_content(response.text, url)
            
        except ImportError:
            logger.warning("CloudScraper not available, install with: pip install cloudscraper")
            raise
        except Exception as e:
            logger.error(f"CloudScraper error: {e}")
            raise

    async def _scrape_with_enhanced_http(self, url: str) -> Dict[str, Any]:
        """Enhanced HTTP scraping with better headers and session management"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="120", "Chromium";v="120", "Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        
        # Add random delay to appear more human-like
        await asyncio.sleep(random.uniform(1, 3))
        
        async with self.session.get(url, headers=headers, ssl=False) as response:
            response.raise_for_status()
            content = await response.text()
            return await self._parse_content(content, url)

    async def _scrape_with_playwright(self, url: str) -> Dict[str, Any]:
        """Scrape using Playwright for JavaScript-heavy sites"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                    ]
                )
                
                context = await browser.new_context(
                    user_agent=self.ua.random,
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US'
                )
                
                page = await context.new_page()
                
                # Set additional headers
                await page.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                })
                
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                content = await page.content()
                await browser.close()
                
                return await self._parse_content(content, url)
                
        except ImportError:
            logger.warning("Playwright not available, install with: pip install playwright")
            raise
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            raise

    async def _scrape_with_mobile_ua(self, url: str) -> Dict[str, Any]:
        """Try scraping with mobile user agent (often less protected)"""
        mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        async with self.session.get(url, headers=mobile_headers, ssl=False) as response:
            response.raise_for_status()
            content = await response.text()
            return await self._parse_content(content, url)

    async def _parse_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse HTML content based on the platform"""
        domain = urlparse(url).netloc.lower()
        
        if 'olx' in domain:
            return self._parse_olx(html_content, url)
        elif 'facebook' in domain:
            return self._parse_facebook_marketplace(html_content, url)
        elif 'quikr' in domain:
            return self._parse_quikr(html_content, url)
        elif 'amazon' in domain:
            return self._parse_amazon(html_content, url)
        elif 'flipkart' in domain:
            return self._parse_flipkart(html_content, url)
        else:
            return self._parse_generic(html_content, url)

    def _parse_olx(self, html_content: str, url: str) -> Dict[str, Any]:
        """Enhanced OLX parser with multiple selectors"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Multiple selector strategies for title
        title_selectors = [
            'h1[data-aut-id="itemTitle"]',
            'h1.it-ttl',
            'h1.pds-box-title',
            'h1[class*="title"]',
            '.ad-title h1',
            'h1',
        ]
        
        title = None
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                title = element.get_text(strip=True)
                break
        
        # Enhanced selector strategies for price (OLX specific)
        price_selectors = [
            '[data-aut-id="itemPrice"]',
            'span.notranslate',
            '.price-text',
            '.ad-price',
            '[class*="price"]',
            'span[class*="Price"]',
            '.price',
            'h3.notranslate'
        ]
        
        price_text = None
        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                # Check if this looks like a price (contains ₹ or numbers)
                if text and ('₹' in text or re.search(r'\d{2,}', text)):
                    # Skip if it looks like an ID or phone number (too long)
                    numbers = re.findall(r'\d+', text)
                    if numbers and any(len(num) >= 10 for num in numbers):
                        continue  # Skip phone numbers/IDs
                    price_text = text
                    break
            if price_text:
                break
        
        # Extract numeric price
        price = self._extract_price(price_text) if price_text else None
        
        # Description with multiple selectors
        desc_selectors = [
            '[data-aut-id="itemDescriptionText"]',
            '.ad-description',
            '.description-text',
            '[class*="description"]'
        ]
        
        description = None
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                description = element.get_text(strip=True)
                break
        
        # Location
        location_selectors = [
            '[data-aut-id="item-location"]',
            '.location-text',
            '[class*="location"]'
        ]
        
        location = None
        for selector in location_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                location = element.get_text(strip=True)
                break
        
        return {
            'title': title or self._extract_title_from_url(url),
            'description': description or 'Product description not available',
            'price': price or self._estimate_price_from_context(url, title),
            'original_price': price,
            'location': location or 'India',
            'url': url,
            'platform': 'OLX',
            'category': self._categorize_product(title or ''),
            'condition': 'Used',
            'posted_date': datetime.now().isoformat(),
            'is_available': True,
            'scraped_successfully': bool(title and price),
            'seller_name': 'OLX Seller',
            'seller_contact': 'Contact via OLX platform',
            'images': self._extract_images(soup),
            'features': self._extract_features(description or '')
        }

    def _parse_generic(self, html_content: str, url: str) -> Dict[str, Any]:
        """Generic parser for unknown platforms"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try to find title
        title_candidates = [
            soup.find('h1'),
            soup.find('title'),
            soup.select_one('[class*="title"]'),
            soup.select_one('[id*="title"]')
        ]
        
        title = None
        for candidate in title_candidates:
            if candidate and candidate.get_text(strip=True):
                title = candidate.get_text(strip=True)
                break
        
        # Try to find price
        price_patterns = [
            r'₹[\s]*([0-9,]+)',
            r'Rs\.?[\s]*([0-9,]+)',
            r'INR[\s]*([0-9,]+)',
            r'\$[\s]*([0-9,]+)'
        ]
        
        price = None
        text_content = soup.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                price = int(match.group(1).replace(',', ''))
                break
        
        return {
            'title': title or self._extract_title_from_url(url),
            'description': 'Product available on marketplace',
            'price': price or self._estimate_price_from_context(url, title),
            'original_price': price,
            'location': 'India',
            'url': url,
            'platform': 'Marketplace',
            'category': self._categorize_product(title or ''),
            'condition': 'Used',
            'posted_date': datetime.now().isoformat(),
            'is_available': True,
            'scraped_successfully': bool(title and price),
            'seller_name': 'Seller',
            'seller_contact': 'Contact via platform',
            'images': [],
            'features': []
        }

    def _extract_price(self, price_text: str) -> Optional[int]:
        """Extract numeric price from text with better validation"""
        if not price_text:
            return None
        
        # Remove currency symbols and clean text
        clean_text = re.sub(r'[^\d,.]', '', price_text)
        clean_text = clean_text.replace(',', '')
        
        # Try to extract number
        numbers = re.findall(r'\d+(?:\.\d+)?', clean_text)
        if numbers:
            price_candidate = int(float(numbers[0]))
            
            # Validate price range - reject unrealistic prices
            if 100 <= price_candidate <= 50000000:  # Valid price range for most products
                # Additional check: reject if it looks like an ID (too many digits)
                if len(str(price_candidate)) > 8:  # IDs usually have 9+ digits
                    return None
                return price_candidate
        
        return None

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs from soup"""
        images = []
        img_tags = soup.find_all('img')
        
        for img in img_tags[:5]:  # Limit to first 5 images
            src = img.get('src') or img.get('data-src')
            if src and 'http' in src:
                images.append(src)
        
        return images

    def _extract_features(self, description: str) -> List[str]:
        """Extract key features from description"""
        if not description:
            return []
        
        features = []
        description_lower = description.lower()
        
        # Common feature keywords
        feature_keywords = [
            'brand new', 'like new', 'excellent condition', 'good condition',
            'warranty', 'bill available', 'box available', 'unused',
            'original', 'genuine', 'refurbished', 'working perfectly'
        ]
        
        for keyword in feature_keywords:
            if keyword in description_lower:
                features.append(keyword.title())
        
        return features[:5]  # Limit to 5 features

    def _extract_title_from_url(self, url: str) -> str:
        """Extract product title from URL"""
        try:
            path = urlparse(url).path
            # Extract meaningful part from URL path
            parts = path.split('/')
            for part in reversed(parts):
                if part and len(part) > 5 and not part.isdigit():
                    # Clean and format
                    title = part.replace('-', ' ').replace('_', ' ')
                    title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
                    return title.title()
        except:
            pass
        
        return "Product from Marketplace"

    def _estimate_price_from_context(self, url: str, title: str = None) -> int:
        """Estimate price based on URL and title context"""
        base_price = 10000  # Default base price
        
        # URL-based price hints
        if any(keyword in url.lower() for keyword in ['mobile', 'phone', 'smartphone']):
            base_price = 15000
        elif any(keyword in url.lower() for keyword in ['laptop', 'computer']):
            base_price = 30000
        elif any(keyword in url.lower() for keyword in ['car', 'vehicle']):
            base_price = 200000
        elif any(keyword in url.lower() for keyword in ['bike', 'motorcycle']):
            base_price = 50000
        
        # Title-based adjustments
        if title:
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ['iphone', 'samsung galaxy', 'oneplus']):
                base_price = max(base_price, 20000)
            elif any(keyword in title_lower for keyword in ['macbook', 'thinkpad']):
                base_price = max(base_price, 40000)
        
        return base_price

    def _categorize_product(self, title: str) -> str:
        """Categorize product based on title"""
        if not title:
            return 'Other'
        
        title_lower = title.lower()
        
        if any(keyword in title_lower for keyword in ['phone', 'mobile', 'smartphone', 'iphone', 'samsung']):
            return 'Mobile Phones'
        elif any(keyword in title_lower for keyword in ['laptop', 'computer', 'pc', 'macbook']):
            return 'Electronics'
        elif any(keyword in title_lower for keyword in ['car', 'vehicle', 'sedan', 'suv']):
            return 'Vehicles'
        elif any(keyword in title_lower for keyword in ['bike', 'motorcycle', 'scooter']):
            return 'Bikes'
        elif any(keyword in title_lower for keyword in ['furniture', 'sofa', 'chair', 'table']):
            return 'Furniture'
        elif any(keyword in title_lower for keyword in ['clothes', 'shirt', 'dress', 'fashion']):
            return 'Fashion'
        else:
            return 'Other'

    def _create_intelligent_fallback(self, url: str) -> Dict[str, Any]:
        """Create intelligent fallback when all scraping fails"""
        title = self._extract_title_from_url(url)
        estimated_price = self._estimate_price_from_context(url, title)
        domain = urlparse(url).netloc
        
        return {
            'title': title,
            'description': f'Product listing from {domain}. Full details available on the original page. AI will negotiate based on your preferences.',
            'price': estimated_price,
            'original_price': estimated_price,
            'location': 'India',
            'url': url,
            'platform': domain,
            'category': self._categorize_product(title),
            'condition': 'Used',
            'posted_date': datetime.now().isoformat(),
            'is_available': True,
            'scraped_successfully': False,
            'fallback_used': True,
            'seller_name': f'Seller on {domain}',
            'seller_contact': f'Contact via {domain}',
            'images': [],
            'features': ['Marketplace listing', 'AI-assisted negotiation'],
            'note': 'Product information estimated from URL. AI will negotiate based on your target price and budget.'
        }

    def _extract_title_from_url(self, url: str) -> str:
        """Extract product title from URL"""
        try:
            path = urlparse(url).path
            # Extract meaningful part from URL path
            parts = path.split('/')
            for part in reversed(parts):
                if part and len(part) > 5 and not part.isdigit():
                    # Clean up the part
                    title = part.replace('-', ' ').replace('_', ' ')
                    title = re.sub(r'[^\w\s]', ' ', title)
                    return ' '.join(word.capitalize() for word in title.split())
            
            # Fallback to domain-based title
            domain = urlparse(url).netloc.replace('www.', '')
            return f'Product from {domain.capitalize()}'
        except:
            return 'Marketplace Product'



# Helper function to install missing packages
async def install_missing_packages():
    """Install missing scraping packages"""
    packages = ['cloudscraper', 'fake-useragent', 'playwright']
    
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            logger.info(f"Installing {package}...")
            import subprocess
            subprocess.check_call(['pip', 'install', package])
            
            if package == 'playwright':
                subprocess.check_call(['playwright', 'install', 'chromium'])