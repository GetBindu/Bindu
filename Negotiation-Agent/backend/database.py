import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from models import Product, NegotiationSession


class JSONDatabase:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Use path relative to backend directory
            backend_dir = Path(__file__).parent
            data_dir = backend_dir.parent / "data"
        self.data_dir = Path(data_dir)
        self.products_file = self.data_dir / "products.json"
        self.sessions_file = self.data_dir / "sessions.json"
        
    async def initialize(self):
        """Initialize database with predefined data"""
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize products if file doesn't exist
        if not self.products_file.exists():
            await self._create_initial_products()
            
        # Initialize sessions file if it doesn't exist
        if not self.sessions_file.exists():
            await self._create_initial_sessions()
    
    async def _create_initial_products(self):
        """Create initial predefined products"""
        initial_products = [
            {
                "id": "prod_001",
                "title": "iPhone 13 - 128GB Blue",
                "description": "Excellent condition iPhone 13 with original box, charger, and all accessories. No scratches, battery health 95%. Used for 6 months only.",
                "price": 45000,
                "original_price": 65000,
                "seller_name": "Rajesh Kumar",
                "seller_contact": "9876543210",
                "location": "Sector 18, Noida",
                "url": "https://olx.in/ad/iphone-13-128gb-blue-excellent-condition-ID1234567",
                "platform": "OLX",
                "category": "Mobile Phones",
                "condition": "Excellent",
                "images": [
                    "https://example.com/images/iphone13_1.jpg",
                    "https://example.com/images/iphone13_2.jpg"
                ],
                "features": [
                    "128GB Storage",
                    "Blue Color", 
                    "Original Box",
                    "95% Battery Health",
                    "No Physical Damage"
                ],
                "posted_date": "2025-09-20T10:30:00Z",
                "is_available": True
            },
            {
                "id": "prod_002", 
                "title": "Samsung Galaxy S23 Ultra - 256GB Black",
                "description": "Like new Samsung Galaxy S23 Ultra with S Pen. Purchased 3 months ago, rarely used. All original accessories included.",
                "price": 75000,
                "original_price": 95000,
                "seller_name": "Priya Sharma",
                "seller_contact": "9123456789",
                "location": "Koramangala, Bangalore",
                "url": "https://olx.in/ad/samsung-s23-ultra-256gb-black-ID2345678",
                "platform": "OLX",
                "category": "Mobile Phones",
                "condition": "Like New",
                "images": [
                    "https://example.com/images/s23ultra_1.jpg",
                    "https://example.com/images/s23ultra_2.jpg"
                ],
                "features": [
                    "256GB Storage",
                    "Phantom Black",
                    "S Pen Included",
                    "Original Packaging",
                    "Warranty Valid"
                ],
                "posted_date": "2025-09-21T14:15:00Z",
                "is_available": True
            },
            {
                "id": "prod_003",
                "title": "MacBook Air M2 - 13 inch Silver",
                "description": "MacBook Air M2 chip, 8GB RAM, 256GB SSD. Perfect for students and professionals. Barely used, pristine condition.",
                "price": 85000,
                "original_price": 115000,
                "seller_name": "Amit Patel",
                "seller_contact": "9234567890",
                "location": "Andheri West, Mumbai",
                "url": "https://facebook.com/marketplace/macbook-air-m2-silver-ID3456789",
                "platform": "Facebook Marketplace",
                "category": "Laptops",
                "condition": "Excellent",
                "images": [
                    "https://example.com/images/macbook_1.jpg",
                    "https://example.com/images/macbook_2.jpg"
                ],
                "features": [
                    "M2 Chip",
                    "8GB RAM",
                    "256GB SSD",
                    "13-inch Display",
                    "Silver Color"
                ],
                "posted_date": "2025-09-19T09:45:00Z",
                "is_available": True
            },
            {
                "id": "prod_004",
                "title": "Sony PlayStation 5 Console",
                "description": "PlayStation 5 console with extra DualSense controller. Includes popular games: Spider-Man, God of War. Excellent condition.",
                "price": 42000,
                "original_price": 50000,
                "seller_name": "Rohit Singh",
                "seller_contact": "9345678901",
                "location": "CP, New Delhi",
                "url": "https://olx.in/ad/playstation-5-console-extra-controller-ID4567890",
                "platform": "OLX",
                "category": "Gaming",
                "condition": "Good",
                "images": [
                    "https://example.com/images/ps5_1.jpg",
                    "https://example.com/images/ps5_2.jpg"
                ],
                "features": [
                    "PS5 Console",
                    "Extra Controller",
                    "2 Games Included",
                    "All Cables",
                    "Original Box"
                ],
                "posted_date": "2025-09-22T11:20:00Z",
                "is_available": True
            },
            {
                "id": "prod_005",
                "title": "Honda Activa 6G - 2023 Model",
                "description": "Well-maintained Honda Activa 6G, 2023 model. Only 2500 KM driven. Single owner, all papers clear.",
                "price": 65000,
                "original_price": 75000,
                "seller_name": "Sunita Devi",
                "seller_contact": "9456789012",
                "location": "Vaishali, Ghaziabad",
                "url": "https://olx.in/ad/honda-activa-6g-2023-excellent-ID5678901",
                "platform": "OLX",
                "category": "Vehicles",
                "condition": "Excellent",
                "images": [
                    "https://example.com/images/activa_1.jpg",
                    "https://example.com/images/activa_2.jpg"
                ],
                "features": [
                    "2023 Model",
                    "2500 KM Only",
                    "Single Owner",
                    "All Papers Clear",
                    "Well Maintained"
                ],
                "posted_date": "2025-09-18T16:30:00Z",
                "is_available": True
            }
        ]
        
        with open(self.products_file, 'w', encoding='utf-8') as f:
            json.dump(initial_products, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] Created initial products database with {len(initial_products)} products")
    
    async def _create_initial_sessions(self):
        """Create initial sessions file"""
        initial_sessions = []
        
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(initial_sessions, f, indent=2, ensure_ascii=False)
        
        print("[INFO] Created initial sessions database")
    
    async def get_products(self) -> List[Product]:
        """Get all products"""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                products_data = json.loads(content)
            
            products = []
            for product_data in products_data:
                # Convert datetime string to datetime object
                product_data['posted_date'] = datetime.fromisoformat(product_data['posted_date'].replace('Z', '+00:00'))
                products.append(Product(**product_data))
            
            return products
        except Exception as e:
            print(f"Error loading products: {e}")
            return []
    
    async def save_product(self, product: Product) -> bool:
        """Save a product to the database"""
        try:
            products = await self.get_products()
            
            # Check if product exists
            existing_index = None
            for i, existing_product in enumerate(products):
                if existing_product.id == product.id:
                    existing_index = i
                    break
            
            # Convert product to dict for JSON serialization
            product_dict = product.dict()
            product_dict['posted_date'] = product.posted_date.isoformat()
            
            # Load current products data
            try:
                with open(self.products_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        products_data = json.loads(content)
                    else:
                        products_data = []
            except (FileNotFoundError, json.JSONDecodeError, ValueError):
                products_data = []
            
            if existing_index is not None:
                # Update existing product
                products_data[existing_index] = product_dict
            else:
                # Add new product
                products_data.append(product_dict)
            
            # Save back to file
            with open(self.products_file, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving product: {e}")
            return False
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get specific product by ID"""
        products = await self.get_products()
        for product in products:
            if product.id == product_id:
                return product
        return None
    
    async def save_session(self, session: NegotiationSession):
        """Save negotiation session"""
        try:
            # Load existing sessions
            sessions_data = []
            if self.sessions_file.exists():
                try:
                    with open(self.sessions_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # Only parse if file has content
                            sessions_data = json.loads(content)
                        else:
                            sessions_data = []
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Warning: Could not load sessions file, starting fresh: {e}")
                    sessions_data = []
            
            # Convert session to dict and handle datetime serialization
            session_dict = session.dict()
            session_dict['created_at'] = session.created_at.isoformat()
            if session.ended_at:
                session_dict['ended_at'] = session.ended_at.isoformat()
            
            # Convert message timestamps
            for message in session_dict['messages']:
                if isinstance(message['timestamp'], datetime):
                    message['timestamp'] = message['timestamp'].isoformat()
            
            # Update or add session
            session_exists = False
            for i, existing_session in enumerate(sessions_data):
                if existing_session['id'] == session.id:
                    sessions_data[i] = session_dict
                    session_exists = True
                    break
            
            if not session_exists:
                sessions_data.append(session_dict)
            
            # Save to file
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving session: {e}")
    
    async def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get specific session by ID"""
        try:
            if not self.sessions_file.exists():
                return None
                
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return None
                    sessions_data = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                return None
            
            for session_data in sessions_data:
                if session_data['id'] == session_id:
                    # Convert datetime strings back to datetime objects
                    session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                    if session_data.get('ended_at'):
                        session_data['ended_at'] = datetime.fromisoformat(session_data['ended_at'])
                    
                    # Convert message timestamps
                    for message in session_data['messages']:
                        message['timestamp'] = datetime.fromisoformat(message['timestamp'])
                    
                    return NegotiationSession(**session_data)
            
            return None
        except Exception as e:
            print(f"Error loading session: {e}")
            return None