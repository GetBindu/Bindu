"""
Authentication service for the negotiation platform
Handles seller registration, login, and session management
"""

import hashlib
import secrets
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import json
import os

class AuthenticationService:
    def __init__(self):
        self.users_file = Path("data/users.json")
        self.sessions_file = Path("data/auth_sessions.json")
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440  # 24 hours
        
        # Ensure data directory exists
        self.users_file.parent.mkdir(exist_ok=True)
        
        # Initialize user storage
        if not self.users_file.exists():
            self._save_users({})
        
        # Initialize session storage
        if not self.sessions_file.exists():
            self._save_sessions({})
    
    def _load_users(self) -> Dict[str, Any]:
        """Load users from file"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_users(self, users: Dict[str, Any]):
        """Save users to file"""
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def _load_sessions(self) -> Dict[str, Any]:
        """Load sessions from file"""
        try:
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_sessions(self, sessions: Dict[str, Any]):
        """Save sessions to file"""
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_hex = hashed.split(':')
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_hex == password_hash.hex()
        except Exception:
            return False
    
    def _create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    async def register_user(self, username: str, email: str, password: str, 
                          full_name: str, phone: str, role: str = "buyer") -> Dict[str, Any]:
        """Register a new user (buyer or seller)"""
        users = self._load_users()
        
        # Validate role
        if role not in ["buyer", "seller"]:
            return {"success": False, "message": "Invalid role. Must be 'buyer' or 'seller'"}
        
        # Validate phone (now required)
        if not phone or len(phone.strip()) < 10:
            return {"success": False, "message": "Phone number is required and must be at least 10 digits"}
        
        # Check if username or email already exists
        for user_id, user_data in users.items():
            if user_data.get('username') == username:
                return {"success": False, "message": "Username already exists"}
            if user_data.get('email') == email:
                return {"success": False, "message": "Email already registered"}
        
        # Create new user
        user_id = secrets.token_urlsafe(16)
        hashed_password = self._hash_password(password)
        
        user_data = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'full_name': full_name,
            'phone': phone,
            'role': role,
            'created_at': datetime.now().isoformat(),
            'is_active': True,
            'profile': {}
        }
        
        users[user_id] = user_data
        self._save_users(users)
        
        return {
            "success": True, 
            "message": f"{role.capitalize()} registered successfully",
            "user_id": user_id
        }
    
    async def login_user(self, username: str, password: str, role: str = None) -> Dict[str, Any]:
        """Login user (buyer or seller)"""
        users = self._load_users()
        
        # Find user by username
        user_data = None
        for user_id, data in users.items():
            if data.get('username') == username:
                user_data = data
                break
        
        if not user_data:
            return {"success": False, "message": "Invalid username or password"}
        
        # Verify password
        if not self._verify_password(password, user_data['password_hash']):
            return {"success": False, "message": "Invalid username or password"}
        
        # Check if user is active
        if not user_data.get('is_active', True):
            return {"success": False, "message": "Account is disabled"}
        
        # If role is specified, verify it matches
        if role and user_data.get('role') != role:
            return {"success": False, "message": f"This account is not registered as a {role}"}
        
        # Create access token
        token_data = {
            "user_id": user_data['user_id'],
            "username": username,
            "role": user_data.get('role', 'buyer')
        }
        access_token = self._create_access_token(token_data)
        
        # Create session
        session_id = secrets.token_urlsafe(32)
        sessions = self._load_sessions()
        sessions[session_id] = {
            "user_id": user_data['user_id'],
            "username": username,
            "role": user_data.get('role', 'buyer'),
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "is_active": True
        }
        self._save_sessions(sessions)
        
        # Remove sensitive data
        safe_user_data = {k: v for k, v in user_data.items() if k != 'password_hash'}
        
        return {
            "success": True,
            "message": "Login successful",
            "user": safe_user_data,
            "token": access_token,
            "session_id": session_id
        }
    
    async def logout_user(self, session_id: str) -> Dict[str, Any]:
        """Logout user and invalidate session"""
        sessions = self._load_sessions()
        
        if session_id in sessions:
            sessions[session_id]['is_active'] = False
            sessions[session_id]['logged_out_at'] = datetime.now().isoformat()
            self._save_sessions(sessions)
        
        return {"success": True, "message": "Successfully logged out"}
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by user ID"""
        users = self._load_users()
        user_data = users.get(user_id)
        
        if user_data:
            # Remove sensitive data
            safe_user_data = {k: v for k, v in user_data.items() if k != 'password_hash'}
            return safe_user_data
        
        return None
    
    async def update_user_profile(self, user_id: str, full_name: str = None, 
                                phone: str = None, profile: Dict = None) -> Dict[str, Any]:
        """Update user profile"""
        users = self._load_users()
        
        if user_id not in users:
            return {"success": False, "message": "User not found"}
        
        user_data = users[user_id]
        
        # Update fields if provided
        if full_name:
            user_data['full_name'] = full_name
        if phone:
            user_data['phone'] = phone
        if profile:
            user_data['profile'].update(profile)
        
        user_data['updated_at'] = datetime.now().isoformat()
        users[user_id] = user_data
        self._save_users(users)
        
        # Remove sensitive data
        safe_user_data = {k: v for k, v in user_data.items() if k != 'password_hash'}
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": safe_user_data
        }
    
    def register_seller(self, username: str, email: str, password: str, 
                       full_name: str, phone: str = None) -> Dict[str, Any]:
        """Register a new seller"""
        users = self._load_users()
        
        # Check if username or email already exists
        for user_id, user_data in users.items():
            if user_data.get('username') == username:
                return {"success": False, "error": "Username already exists"}
            if user_data.get('email') == email:
                return {"success": False, "error": "Email already registered"}
        
        # Create new user
        user_id = secrets.token_urlsafe(16)
        user_data = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": self._hash_password(password),
            "full_name": full_name,
            "phone": phone,
            "role": "seller",
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "profile": {
                "total_products": 0,
                "successful_negotiations": 0,
                "average_rating": 0.0,
                "preferred_contact": "platform"
            }
        }
        
        users[user_id] = user_data
        self._save_users(users)
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "Seller registered successfully"
        }
    
    def login_seller(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate seller login"""
        users = self._load_users()
        
        # Find user by username or email
        user_data = None
        user_id = None
        for uid, data in users.items():
            if data.get('username') == username or data.get('email') == username:
                user_data = data
                user_id = uid
                break
        
        if not user_data:
            return {"success": False, "error": "Invalid credentials"}
        
        if not user_data.get('is_active'):
            return {"success": False, "error": "Account is deactivated"}
        
        # Verify password
        if not self._verify_password(password, user_data['password_hash']):
            return {"success": False, "error": "Invalid credentials"}
        
        # Create access token
        token_data = {
            "user_id": user_id,
            "username": user_data['username'],
            "role": user_data['role']
        }
        access_token = self._create_access_token(token_data)
        
        # Store session
        sessions = self._load_sessions()
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {
            "user_id": user_id,
            "username": user_data['username'],
            "login_time": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "access_token": access_token
        }
        self._save_sessions(sessions)
        
        # Remove sensitive data
        safe_user_data = {k: v for k, v in user_data.items() if k != 'password_hash'}
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "session_id": session_id,
            "user": safe_user_data
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Get current user from token"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        users = self._load_users()
        user_id = payload.get("user_id")
        
        if user_id and user_id in users:
            user_data = users[user_id].copy()
            user_data.pop('password_hash', None)  # Remove sensitive data
            return user_data
        
        return None
    
    def logout_seller(self, session_id: str) -> Dict[str, Any]:
        """Logout seller and invalidate session"""
        sessions = self._load_sessions()
        
        if session_id in sessions:
            del sessions[session_id]
            self._save_sessions(sessions)
            return {"success": True, "message": "Logged out successfully"}
        
        return {"success": False, "error": "Session not found"}
    
    def update_seller_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update seller profile"""
        users = self._load_users()
        
        if user_id not in users:
            return {"success": False, "error": "User not found"}
        
        # Update allowed fields
        allowed_fields = ['full_name', 'phone', 'profile']
        for field in allowed_fields:
            if field in profile_data:
                if field == 'profile':
                    users[user_id]['profile'].update(profile_data[field])
                else:
                    users[user_id][field] = profile_data[field]
        
        users[user_id]['updated_at'] = datetime.utcnow().isoformat()
        self._save_users(users)
        
        return {"success": True, "message": "Profile updated successfully"}
    
    def get_seller_stats(self, user_id: str) -> Dict[str, Any]:
        """Get seller statistics"""
        users = self._load_users()
        
        if user_id not in users:
            return {"success": False, "error": "User not found"}
        
        user_data = users[user_id]
        
        return {
            "success": True,
            "stats": {
                "total_products": user_data['profile'].get('total_products', 0),
                "successful_negotiations": user_data['profile'].get('successful_negotiations', 0),
                "average_rating": user_data['profile'].get('average_rating', 0.0),
                "member_since": user_data.get('created_at'),
                "last_login": user_data.get('last_login'),
                "account_status": "Active" if user_data.get('is_active') else "Inactive"
            }
        }
    
    async def validate_session(self, session_id: str) -> Dict[str, Any]:
        """Validate session and return user info if valid"""
        sessions = self._load_sessions()
        
        if session_id not in sessions:
            return {"success": False, "message": "Invalid session"}
        
        session_data = sessions[session_id]
        
        # Check if session is active
        if not session_data.get('is_active', False):
            return {"success": False, "message": "Session is not active"}
        
        # Check if session has expired (optional - could add expiration logic here)
        # For now, we'll just update last_activity
        session_data['last_activity'] = datetime.now().isoformat()
        self._save_sessions(sessions)
        
        # Get user data
        users = self._load_users()
        user_id = session_data.get('user_id')
        
        if user_id not in users:
            return {"success": False, "message": "User not found"}
        
        user_data = users[user_id]
        
        # Remove sensitive data
        safe_user_data = {k: v for k, v in user_data.items() if k != 'password_hash'}
        
        return {
            "success": True,
            "user": safe_user_data,
            "session": {
                "session_id": session_id,
                "username": session_data.get('username'),
                "role": session_data.get('role'),
                "created_at": session_data.get('created_at'),
                "last_activity": session_data.get('last_activity')
            }
        }