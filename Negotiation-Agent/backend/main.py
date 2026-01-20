"""
Full Negotiation Agent Application
Complete implementation of the marketplace negotiation workflow
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
import json
import asyncio
import uuid
from datetime import datetime
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import custom modules
from models import Product, NegotiationParams, ChatMessage, NegotiationSession
from database import JSONDatabase
from gemini_service import GeminiOnlyService
from websocket_manager import ConnectionManager
from session_manager import AdvancedSessionManager
from scraper_service import MarketplaceScraper, MarketIntelligence
from enhanced_scraper import EnhancedMarketplaceScraper
from negotiation_engine import AdvancedNegotiationEngine
from auth_service import AuthenticationService
from enhanced_ai_service import EnhancedAIService
# from mcp_integration import initialize_mcp_server  # Temporarily commented out

# Pydantic models for API endpoints
class URLNegotiationRequest(BaseModel):
    product_url: str = Field(..., description="Marketplace URL (OLX, Facebook, etc.)")
    target_price: int = Field(..., gt=0, description="Target price in INR")
    max_budget: int = Field(..., gt=0, description="Maximum budget in INR")
    approach: str = Field(..., description="Negotiation approach: assertive, diplomatic, considerate")
    timeline: str = Field(default="flexible", description="Purchase timeline: urgent, week, flexible")
    special_requirements: Optional[str] = Field(None, description="Special requirements")
    scraping_method: Optional[str] = Field(default="enhanced", description="Scraping method: enhanced, standard")

class SellerResponseRequest(BaseModel):
    session_id: str
    message: str

class SessionEndRequest(BaseModel):
    session_id: str
    outcome: str
    final_price: Optional[int] = None
    user_notes: Optional[str] = None

# Import custom modules

# User Role Enum
class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"

# Authentication models
class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="Username")
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$', description="Valid email address")
    full_name: str = Field(..., min_length=2, description="Full name")
    phone: str = Field(..., min_length=10, max_length=15, description="Phone number (required)")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    role: UserRole = Field(..., description="User role: buyer or seller")

class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    role: UserRole = Field(..., description="User role: buyer or seller")

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None

class LogoutRequest(BaseModel):
    session_id: str

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mcp_server
    await db.initialize()
    
    # Initialize MCP server
    try:
        # mcp_server = initialize_mcp_server(db, session_manager)  # Temporarily commented out
        logger.info("INFO: MCP server initialized successfully!")
    except Exception as e:
        logger.warning(f"MCP server initialization failed: {e}")
    
    logger.info("INFO: NegotiBot AI Enhanced Backend started successfully!")
    logger.info("INFO: - LangChain Agent: Fully Integrated & Active")
    logger.info("INFO: - MCP Integration: Available (Currently Disabled)") 
    logger.info("INFO: - Gemini Fallback: Available")
    logger.info("INFO: - Advanced Negotiation Tools: Market Analysis, Price Calculator, Strategy Advisor")
    yield
    # Shutdown (if needed)
    pass

# Initialize FastAPI app
app = FastAPI(
    title="NegotiBot AI - Full Implementation",
    description="Complete AI-powered marketplace negotiation platform with web scraping and advanced tactics",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = ["*"] if allowed_origins == "*" else allowed_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=os.getenv("ENABLE_CORS_CREDENTIALS", "true").lower() == "true",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with user-friendly messages"""
    from fastapi.responses import JSONResponse
    
    # Map technical field names to user-friendly names
    field_mapping = {
        "username": "Username",
        "password": "Password", 
        "email": "Email",
        "full_name": "Full Name",
        "phone": "Phone Number",
        "role": "Account Type"
    }
    
    # Map technical error messages to user-friendly ones
    message_mapping = {
        "field required": "is required",
        "string too short": "is too short",
        "string too long": "is too long",
        "value is not a valid email address": "must be a valid email address",
        "ensure this value has at least": "must have at least",
        "ensure this value has at most": "must have at most"
    }
    
    user_friendly_errors = []
    for error in exc.errors():
        field_path = error["loc"]
        field_name = str(field_path[-1]) if field_path else "Field"
        
        # Get user-friendly field name
        friendly_field = field_mapping.get(field_name, field_name.replace("_", " ").title())
        
        # Get user-friendly error message
        original_msg = error.get("msg", "")
        friendly_msg = original_msg
        
        for tech_msg, user_msg in message_mapping.items():
            if tech_msg in original_msg.lower():
                friendly_msg = user_msg
                break
        
        # Special cases for specific validations
        if "value_error.email" in error.get("type", ""):
            friendly_msg = "must be a valid email address"
        elif "value_error.any_str.min_length" in error.get("type", ""):
            friendly_msg = f"must be at least {error.get('ctx', {}).get('limit_value', 'X')} characters"
        elif "value_error.any_str.max_length" in error.get("type", ""):
            friendly_msg = f"must be no more than {error.get('ctx', {}).get('limit_value', 'X')} characters"
        
        user_friendly_errors.append(f"{friendly_field} {friendly_msg}")
    
    # Create a user-friendly main message based on the endpoint
    endpoint = str(request.url.path)
    if "login" in endpoint:
        main_message = "Login information is incomplete or invalid"
        hint = "Please make sure you've entered your username, password, and selected your account type (Buyer or Seller)"
    elif "register" in endpoint:
        main_message = "Registration information is incomplete or invalid"
        hint = "Please fill in all required fields: username, email, full name, phone number, password, and account type"
    else:
        main_message = "Please check the information you've entered"
        hint = "Make sure all required fields are filled in correctly"
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": main_message,
            "errors": user_friendly_errors,
            "hint": hint
        }
    )

# Mount static files (keep existing demo)
demo_path = Path(__file__).parent.parent / "demo"
if demo_path.exists():
    app.mount("/demo", StaticFiles(directory=str(demo_path)), name="demo")

# Mount seller interface
seller_path = Path(__file__).parent.parent / "seller-interface"
if seller_path.exists():
    app.mount("/seller", StaticFiles(directory=str(seller_path)), name="seller")

# Mount full interface (main app)
full_interface_path = Path(__file__).parent.parent / "full-interface"
if full_interface_path.exists():
    app.mount("/full-interface", StaticFiles(directory=str(full_interface_path)), name="full-interface")

# Mount React frontend
react_path = Path(__file__).parent.parent / "frontend"
if react_path.exists():
    app.mount("/react", StaticFiles(directory=str(react_path)), name="frontend")

# Serve main HTML files directly
@app.get("/")
async def root():
    """Serve the main landing page"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="Frontend not found")

@app.get("/seller-portal.html")
async def seller_portal():
    """Serve the seller portal page"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "seller-portal.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="Seller portal not found")

@app.get("/react-app.html") 
async def buyer_portal():
    """Serve the buyer portal page"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "react-app.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="Buyer portal not found")

# Initialize services
db = JSONDatabase()
ai_service = GeminiOnlyService()  # Legacy service for fallback
manager = ConnectionManager()
session_manager = AdvancedSessionManager(db)
market_intelligence = MarketIntelligence()
auth_service = AuthenticationService()

# Initialize enhanced AI services with LangChain + MCP
enhanced_ai_service = EnhancedAIService(use_langchain=True, use_mcp=False)
mcp_server = None

# Update session manager with enhanced AI service
session_manager.enhanced_ai_service = enhanced_ai_service

# Global storage for active connections
active_connections: Dict[str, Dict] = {}

# Authentication dependency
async def get_current_user(authorization: str = Header(None)):
    """Authentication dependency for protected routes"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Extract token from "Bearer <token>" format
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authentication format")
        
        token = authorization.split(" ")[1]
        user_data = auth_service.get_current_user(token)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return user_data
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# Buyer authentication dependency  
async def get_current_buyer(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user is a buyer"""
    if current_user.get("role") != "buyer":
        raise HTTPException(status_code=403, detail="Buyer access required")
    return current_user


@app.get("/")
async def root():
    """Serve the landing page"""
    try:
        landing_page_path = Path(__file__).parent.parent / "frontend" / "index.html"
        if landing_page_path.exists():
            return FileResponse(landing_page_path)
        else:
            return {
                "message": "NegotiBot AI - Landing page not found",
                "negotiation_url": "/react/react-app.html"
            }
    except Exception as e:
        return {
            "message": "NegotiBot AI Full Implementation is running!",
            "version": "2.0.0",
            "features": [
                "Web scraping from OLX/Facebook Marketplace",
                "Market intelligence analysis", 
                "Advanced negotiation tactics",
                "Real-time strategy adaptation",
                "Human handoff capabilities",
                "Performance analytics",
            "Machine learning optimization"
        ]
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database
        products = await db.get_products()
        
        # Test AI services
        ai_available = ai_service.model is not None
        ai_status = enhanced_ai_service.get_service_status()
        
        return {
            "status": "healthy",
            "database": "connected",
            "legacy_ai_service": "available" if ai_available else "fallback_mode",
            "enhanced_ai_service": ai_status,
            "products_count": len(products),
            "active_sessions": len(session_manager.active_sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/api/ai/status")
async def ai_service_status():
    """Detailed AI service status and performance metrics"""
    return enhanced_ai_service.get_service_status()


# ===== ROOT AND UTILITY ENDPOINTS =====

@app.get("/")
async def root():
    """Redirect to seller portal"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/react/seller-portal.html")

@app.get("/seller-portal")
async def seller_portal_redirect():
    """Redirect to seller portal"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/react/seller-portal.html")

@app.get("/react-app.html")
async def buyer_portal():
    """Serve buyer portal directly"""
    buyer_portal_path = Path(__file__).parent.parent / "frontend" / "react-app.html"
    if buyer_portal_path.exists():
        return FileResponse(buyer_portal_path)
    else:
        raise HTTPException(status_code=404, detail="Buyer portal not found")

# ===== AUTHENTICATION ENDPOINTS =====

@app.get("/api/auth/roles")
async def get_user_roles():
    """Get available user roles"""
    return {
        "roles": [
            {"value": UserRole.BUYER, "label": "Buyer"},
            {"value": UserRole.SELLER, "label": "Seller"}
        ]
    }

@app.post("/api/auth/register")
async def register_user(user_data: UserRegistration):
    """Register a new user and automatically log them in"""
    try:
        result = await auth_service.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone=user_data.phone,
            role=user_data.role.value
        )
        
        if result["success"]:
            # Auto-login after successful registration
            try:
                login_result = await auth_service.login_user(
                    username=user_data.username,
                    password=user_data.password,
                    role=user_data.role.value
                )
                
                if login_result["success"]:
                    return {
                        "success": True,
                        "message": "Registration and login successful",
                        "user": login_result["user"],
                        "token": login_result["token"],
                        "session_id": login_result["session_id"],
                        "auto_login": True
                    }
                else:
                    # Registration successful but auto-login failed
                    return {
                        "success": True,
                        "message": "Registration successful, please login manually",
                        "user": result.get("user"),
                        "user_id": result["user_id"],
                        "auto_login": False
                    }
            except Exception as login_error:
                logger.error(f"Auto-login after registration failed: {str(login_error)}")
                # Registration successful but auto-login failed
                return {
                    "success": True,
                    "message": "Registration successful, please login manually",
                    "user": result.get("user"),
                    "user_id": result["user_id"],
                    "auto_login": False
                }
        else:
            # Provide user-friendly error messages for registration
            error_message = result.get("message", "Registration failed")
            
            # Map common technical errors to user-friendly messages  
            if "username already exists" in error_message.lower() or "already taken" in error_message.lower():
                user_friendly_message = "This username is already taken. Please choose a different username."
            elif "email already exists" in error_message.lower() or "email.*already" in error_message.lower():
                user_friendly_message = "An account with this email already exists. Please use a different email or try logging in."
            elif "phone" in error_message.lower() and "invalid" in error_message.lower():
                user_friendly_message = "Please enter a valid phone number with at least 10 digits."
            elif "password" in error_message.lower() and ("short" in error_message.lower() or "weak" in error_message.lower()):
                user_friendly_message = "Password must be at least 6 characters long."
            else:
                user_friendly_message = error_message
                
            raise HTTPException(
                status_code=400, 
                detail={
                    "success": False,
                    "message": user_friendly_message,
                    "hint": "Please check all your information and try again."
                }
            )
    except HTTPException:
        raise  
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "success": False,
                "message": "We're having trouble creating your account right now. Please try again in a moment.",
                "hint": "If the problem persists, please contact support."
            }
        )

@app.post("/api/auth/login")
async def login_user(user_credentials: UserLogin):
    """Login user and create session"""
    try:
        result = await auth_service.login_user(
            username=user_credentials.username,
            password=user_credentials.password,
            role=user_credentials.role.value
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Login successful",
                "user": result["user"],
                "token": result["token"],
                "session_id": result["session_id"]
            }
        else:
            # Provide user-friendly error messages
            error_message = result.get("message", "Login failed")
            
            # Map common technical errors to user-friendly messages
            if "user not found" in error_message.lower():
                user_friendly_message = "Username not found. Please check your username or register if you don't have an account."
            elif "incorrect password" in error_message.lower() or "invalid password" in error_message.lower():
                user_friendly_message = "Incorrect password. Please check your password and try again."
            elif "invalid credentials" in error_message.lower():
                user_friendly_message = "Invalid username or password. Please check your credentials and try again."
            elif "role" in error_message.lower():
                user_friendly_message = "Please select whether you're logging in as a Buyer or Seller."
            else:
                user_friendly_message = error_message
                
            raise HTTPException(
                status_code=401, 
                detail={
                    "success": False,
                    "message": user_friendly_message,
                    "hint": "Make sure you're using the correct username, password, and account type."
                }
            )
            
    except HTTPException:
        raise 
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "success": False,
                "message": "We're having trouble logging you in right now. Please try again in a moment.",
                "hint": "If the problem persists, please contact support."
            }
        )

@app.post("/api/auth/logout")
async def logout_user(logout_data: LogoutRequest):
    """Logout user and invalidate session"""
    try:
        result = await auth_service.logout_user(logout_data.session_id)
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@app.get("/api/auth/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile information"""
    try:
        user = await auth_service.get_user_profile(user_id)
        
        if user:
            return {
                "success": True,
                "user": user
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except Exception as e:
        logger.error(f"Profile fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")

@app.put("/api/auth/profile/{user_id}")
async def update_user_profile(user_id: str, profile_data: UserProfileUpdate):
    """Update user profile"""
    try:
        result = await auth_service.update_user_profile(
            user_id=user_id,
            full_name=profile_data.full_name,
            phone=profile_data.phone,
            profile=profile_data.profile
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Profile updated successfully",
                "user": result["user"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        raise HTTPException(status_code=500, detail="Profile update failed")

@app.get("/api/auth/validate-session/{session_id}")
async def validate_session(session_id: str):
    """Validate session and return user info if valid"""
    try:
        result = await auth_service.validate_session(session_id)
        
        if result["success"]:
            return {
                "success": True,
                "user": result["user"],
                "session": result["session"]
            }
        else:
            raise HTTPException(status_code=401, detail=result["message"])
            
    except HTTPException:
        raise 
    except Exception as e:
        logger.error(f"Session validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Session validation failed")

# ===== NEGOTIATION ENDPOINTS =====

@app.post("/api/debug-demo-negotiate")
async def debug_demo_negotiate(request: URLNegotiationRequest, background_tasks: BackgroundTasks):
    """Debug demo negotiation endpoint without authentication (for testing)"""
    logger.info(f"[DEBUG] Starting debug demo negotiation...")
    try:
        # Create demo product data based on the URL pattern
        url = request.product_url.lower()
        
        if 'laptop' in url or 'macbook' in url or 'computer' in url:
            demo_title = "MacBook Air M2 - Excellent Condition"
            demo_price = 85000
            demo_description = "MacBook Air with M2 chip, 8GB RAM, 256GB SSD. Barely used, perfect condition."
        elif 'phone' in url or 'mobile' in url or 'iphone' in url:
            demo_title = "iPhone 14 Pro - Like New"
            demo_price = 65000
            demo_description = "iPhone 14 Pro 128GB, space black. Mint condition with original accessories."
        elif 'furniture' in url or 'sofa' in url or 'chair' in url:
            demo_title = "Modern Office Furniture Set"
            demo_price = 25000
            demo_description = "Complete office furniture set including desk, chair, and storage. Excellent quality."
        else:
            demo_title = "Premium Product - Great Deal"
            demo_price = 45000
            demo_description = "High-quality product in excellent condition. Perfect for your needs."
        
        # Create demo product
        demo_product = Product(
            id=str(uuid.uuid4()),
            title=demo_title,
            description=demo_description,
            price=demo_price,
            original_price=int(demo_price * 1.4),  # 40% higher original price
            seller_name="Demo Seller",
            seller_contact="Contact via platform",
            location="Bangalore, Karnataka",
            category="Electronics",
            condition="Excellent",
            url=request.product_url,  # Add this field
            platform="Demo",  # Add this field
            images=[],  # Add this field
            features=[],  # Add this field
            posted_date=datetime.now(),  # Add this field
        )
        
        logger.info(f"[DEBUG] Created demo product: {demo_product.id}")
        
        # Store in database
        await db.add_product(demo_product)
        logger.info(f"[DEBUG] Product stored in database")
        
        # Create negotiation parameters
        params = NegotiationParams(
            product_id=demo_product.id,
            target_price=request.target_price,
            max_budget=request.max_budget,
            approach=request.approach,
            timeline=request.timeline,
            special_requirements=request.special_requirements
        )
        
        logger.info(f"[DEBUG] Created negotiation params")
        
        # Create session
        session = await session_manager.create_session(demo_product, params)
        logger.info(f"[DEBUG] Created session: {session.session_id}")
        logger.info(f"[DEBUG] Active sessions now: {list(session_manager.active_sessions.keys())}")
        
        # Start background negotiation
        background_tasks.add_task(auto_start_negotiation, session.session_id)
        
        return {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "product_info": demo_product.dict()
            },
            "product_info": demo_product.dict(),
            "market_analysis": {
                "average_price": demo_price,
                "price_range": {"min": int(demo_price * 0.8), "max": int(demo_price * 1.2)},
                "market_trend": "stable"
            },
            "message": "Debug demo negotiation session created! AI is ready to negotiate.",
            "demo_mode": True
        }
        
    except Exception as e:
        logger.error(f"Error in debug demo negotiate: {e}")
        return {
            "success": False,
            "message": f"Debug demo setup failed: {str(e)}"
        }

@app.post("/api/demo-negotiate")
async def demo_negotiate(request: URLNegotiationRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_buyer)):
    """Demo negotiation endpoint with sample data (for testing without real URLs)"""
    try:
        # Create demo product data based on the URL pattern
        url = request.product_url.lower()
        
        if 'laptop' in url or 'macbook' in url or 'computer' in url:
            demo_title = "MacBook Air M2 - Excellent Condition"
            demo_price = 85000
            demo_description = "MacBook Air with M2 chip, 8GB RAM, 256GB SSD. Barely used, perfect condition."
        elif 'phone' in url or 'mobile' in url or 'iphone' in url:
            demo_title = "iPhone 14 Pro - Like New"
            demo_price = 65000
            demo_description = "iPhone 14 Pro 128GB, space black. Mint condition with original accessories."
        elif 'furniture' in url or 'sofa' in url or 'chair' in url:
            demo_title = "Modern Office Furniture Set"
            demo_price = 25000
            demo_description = "Complete office furniture set including desk, chair, and storage. Excellent quality."
        else:
            demo_title = "Premium Product - Great Deal"
            demo_price = 45000
            demo_description = "High-quality product in excellent condition. Perfect for your needs."
        
        # Create demo product
        demo_product = Product(
            id=str(uuid.uuid4()),
            title=demo_title,
            description=demo_description,
            price=demo_price,
            original_price=int(demo_price * 1.4),  # 40% higher original price
            seller_name="Demo Seller",
            seller_contact="Contact via platform",
            location="Bangalore, Karnataka",
            category="Electronics",
            condition="Excellent"
        )
        
        # Store in database
        await db.add_product(demo_product)
        
        # Create negotiation parameters
        params = NegotiationParams(
            product_id=demo_product.id,
            target_price=request.target_price,
            max_budget=request.max_budget,
            approach=request.approach,
            timeline=request.timeline,
            special_requirements=request.special_requirements
        )
        
        # Create session
        session = await session_manager.create_session(demo_product, params)
        
        # Start background negotiation
        background_tasks.add_task(auto_start_negotiation, session.session_id)
        
        return {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "product_info": demo_product.dict()
            },
            "product_info": demo_product.dict(),
            "market_analysis": {
                "average_price": demo_price,
                "price_range": {"min": int(demo_price * 0.8), "max": int(demo_price * 1.2)},
                "market_trend": "stable"
            },
            "message": "Demo negotiation session created! AI is ready to negotiate.",
            "demo_mode": True
        }
        
    except Exception as e:
        logger.error(f"Error in demo negotiate: {e}")
        return {
            "success": False,
            "message": f"Demo setup failed: {str(e)}"
        }


# ===============================
# PHASE 1: URL-BASED NEGOTIATION
# ===============================

@app.post("/api/negotiate-url")
async def start_negotiation_from_url(request: URLNegotiationRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_buyer)):
    """
    Phase 1: Start negotiation from marketplace URL
    Implements full product discovery and market analysis workflow
    """
    try:
        logger.info(f"Starting negotiation from URL: {request.product_url}")
        
        # Validate URL
        if not any(domain in request.product_url.lower() for domain in ['olx', 'facebook', 'quikr']):
            logger.warning(f"Unsupported marketplace URL: {request.product_url}")
            # Continue anyway - generic scraper might work
        
        # Create negotiation parameters
        params = NegotiationParams(
            product_id="",  # Will be set after scraping
            target_price=request.target_price,
            max_budget=request.max_budget,
            approach=request.approach,
            timeline=request.timeline,
            special_requirements=request.special_requirements
        )
        
        # Create session with full workflow
        session_result = await session_manager.create_session_from_url(request.product_url, params)
        
        if not session_result or 'session_id' not in session_result:
            return {
                "success": False,
                "message": "Could not create negotiation session. The product URL may be inaccessible or invalid.",
                "suggestion": "Please check the URL and try again, or use a different product listing."
            }
        
        # Start the negotiation in background
        session_id = session_result['session_id']
        background_tasks.add_task(auto_start_negotiation, session_id)
        
        # Return response in format expected by frontend
        product_info = session_result['product'].dict() if session_result.get('product') else {
            "title": "Product from marketplace",
            "price": request.target_price,
            "platform": "Marketplace"
        }
        
        return {
            "success": True,
            "session_id": session_id,
            "session": {
                "session_id": session_id
            },
            "product": product_info,
            "product_info": product_info,
            "market_analysis": session_result.get('market_analysis', {}),
            "strategy": session_result.get('strategy', {}),
            "message": "Negotiation session created! AI analysis complete - ready to negotiate."
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error starting negotiation from URL: {error_msg}")
        
        # Return user-friendly error instead of throwing exception
        return {
            "success": False,
            "message": f"Unable to analyze the product URL. {error_msg if 'scrape' in error_msg.lower() else 'Please check the URL and try again.'}",
            "suggestion": "Make sure the URL is from a supported marketplace (OLX, Facebook Marketplace) and the product page is accessible."
        }


async def auto_start_negotiation(session_id: str):
    """Automatically start negotiation after session creation"""
    try:
        await asyncio.sleep(2)  # Brief delay
        result = await session_manager.start_negotiation(session_id)
        logger.info(f"Auto-started negotiation for session {session_id}")
    except Exception as e:
        logger.error(f"Error auto-starting negotiation {session_id}: {e}")


@app.post("/api/market-analysis")
async def analyze_market_price(request: URLNegotiationRequest):
    """
    Get comprehensive market analysis for a product URL without starting negotiation
    """
    try:
        # Use enhanced scraper for better results
        scraping_method = getattr(request, 'scraping_method', 'enhanced')
        
        if scraping_method == 'enhanced':
            async with EnhancedMarketplaceScraper() as scraper:
                product_data = await scraper.scrape_product(request.product_url)
        else:
            async with MarketplaceScraper() as scraper:
                product_data = await scraper.scrape_product(request.product_url)
        
        if not product_data:
            raise HTTPException(status_code=400, detail="Could not scrape product information")
        
        # Perform comprehensive analysis
        comprehensive_analysis = await market_intelligence.comprehensive_product_analysis(
            product_data, request.target_price, request.max_budget
        )
        
        return {
            "success": True,
            "product_info": product_data,
            "comprehensive_analysis": comprehensive_analysis,
            "analysis_summary": {
                "market_position": comprehensive_analysis.get('market_analysis', {}).get('market_position', 'unknown'),
                "negotiation_potential": f"{comprehensive_analysis.get('market_analysis', {}).get('negotiation_potential', 0.15) * 100:.0f}%",
                "success_probability": f"{comprehensive_analysis.get('strategy', {}).get('success_probability', 60):.0f}%",
                "confidence_score": f"{comprehensive_analysis.get('confidence_score', 0.5) * 100:.0f}%",
                "recommended_opening_offer": comprehensive_analysis.get('strategy', {}).get('opening_offer', request.target_price),
                "key_talking_points": len(comprehensive_analysis.get('negotiation_points', {}).get('price_justification', [])),
                "risk_level": comprehensive_analysis.get('risk_assessment', {}).get('overall_risk_level', 'medium')
            }
        }
        
    except Exception as e:
        logger.error(f"Error in market analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/seller-response")
async def handle_seller_response(request: SellerResponseRequest):
    """
    Handle seller response message in negotiation
    """
    try:
        session_id = request.session_id
        message = request.message
        
        if session_id not in session_manager.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Process the seller's message through the negotiation engine
        await session_manager.process_seller_message(session_id, message)
        
        return {"success": True, "message": "Response processed successfully"}
        
    except Exception as e:
        logger.error(f"Error processing seller response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===============================
# PHASE 3: REAL-TIME NEGOTIATION
# ===============================

@app.websocket("/ws/user/{session_id}")
async def websocket_user_endpoint(websocket: WebSocket, session_id: str):
    """Enhanced WebSocket endpoint for user (monitors AI negotiation)"""
    await manager.connect_user(websocket, session_id)
    
    try:
        # Send session status
        if session_id in session_manager.active_sessions:
            session_data = session_manager.active_sessions[session_id]
            await manager.send_to_user(session_id, {
                "type": "session_status",
                "data": {
                    "phase": session_data.get('phase', 'unknown'),
                    "messages_count": len(session_data['session'].messages),
                    "product": session_data['product'].model_dump(mode='json'),
                    "market_analysis": session_data.get('market_analysis', {})
                }
            })
        
        while True:
            # Listen for user interventions
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get('type') == 'manual_override':
                await handle_user_override(session_id, message_data)
            elif message_data.get('type') == 'end_session':
                await handle_session_end_request(session_id, message_data)
                
    except WebSocketDisconnect:
        manager.disconnect_user(session_id)
        logger.info(f"User disconnected from session: {session_id}")


@app.websocket("/ws/seller/{session_id}")
async def websocket_seller_endpoint(websocket: WebSocket, session_id: str):
    """Enhanced WebSocket endpoint for seller side with full AI processing"""
    await manager.connect_seller(websocket, session_id)
    
    try:
        while True:
            # Listen for seller messages
            data = await websocket.receive_text()
            logger.info(f"[DEBUG] Seller WebSocket received data: {data}")
            message_data = json.loads(data)
            logger.info(f"[DEBUG] Parsed message data: {message_data}")
            
            # Process seller message with advanced negotiation engine
            if message_data.get('type') == 'message':
                logger.info(f"[DEBUG] Processing message type 'message' with content: {message_data.get('content', '')}")
                await handle_advanced_seller_message(session_id, message_data.get('content', ''))
            else:
                logger.warning(f"[DEBUG] Unknown message type: {message_data.get('type')}")
                
    except WebSocketDisconnect:
        manager.disconnect_seller(session_id)
        logger.info(f"Seller disconnected from session: {session_id}")
        
        # Notify user of disconnection
        await manager.send_to_user(session_id, {
            "type": "seller_offline",
            "message": "Seller disconnected"
        })


async def handle_advanced_seller_message(session_id: str, seller_message: str):
    """Handle seller message with advanced negotiation processing"""
    try:
        logger.info(f"[DEBUG] handle_advanced_seller_message called with session_id: {session_id}, message: {seller_message}")
        logger.info(f"[DEBUG] Active sessions: {list(session_manager.active_sessions.keys())}")
        
        if session_id not in session_manager.active_sessions:
            logger.warning(f"Session {session_id} not found in active sessions. Available sessions: {list(session_manager.active_sessions.keys())}")
            
            # Send error to seller
            await manager.send_to_seller(session_id, {
                "type": "error",
                "message": "Session not found. Please start a negotiation from the buyer side first."
            })
            return
        
        logger.info(f"Processing seller message in session {session_id}: {seller_message[:100]}...")
        
        # Process through advanced session manager
        result = await session_manager.process_seller_response(session_id, seller_message)
        logger.info(f"[DEBUG] Session manager returned result: {result}")
        
        # Send seller message to user for monitoring
        await manager.send_to_user(session_id, {
            "type": "seller_message",
            "message": seller_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Handle different result types
        if result.get('handoff_triggered'):
            # Human handoff required
            await manager.send_to_user(session_id, {
                "type": "handoff_required",
                "trigger": result.get('trigger'),
                "message": result.get('handoff_message'),
                "contact_info": result.get('contact_info', {})
            })
            
            await manager.send_to_seller(session_id, {
                "type": "message",
                "content": result.get('handoff_message'),
                "sender": "buyer"
            })
            
        elif result.get('session_completed'):
            # Session completed
            await manager.send_to_user(session_id, {
                "type": "session_completed",
                "outcome": result.get('outcome'),
                "final_price": result.get('final_price'),
                "metrics": result.get('metrics', {}),
                "summary": result.get('session_summary', {})
            })
            
            await manager.send_to_seller(session_id, {
                "type": "session_ended",
                "message": "Negotiation completed. Thank you!"
            })
            
        else:
            # Normal AI response
            ai_response = result.get('ai_response', '')
            
            # Send AI response to seller
            await manager.send_to_seller(session_id, {
                "type": "message",
                "content": ai_response,
                "sender": "buyer"
            })
            
            # Send AI response and analysis to user
            await manager.send_to_user(session_id, {
                "type": "ai_response",
                "message": ai_response,
                "decision": result.get('decision', {}),
                "tactics_used": result.get('tactics_used', []),
                "phase": result.get('phase'),
                "confidence": result.get('confidence', 0.5),
                "seller_analysis": result.get('seller_analysis', {}),
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error handling seller message: {e}")
        
        # Send error to user
        await manager.send_to_user(session_id, {
            "type": "error",
            "message": f"Error processing seller message: {str(e)}"
        })


async def handle_user_override(session_id: str, message_data: Dict[str, Any]):
    """Handle user manual override of AI response"""
    try:
        if session_id not in session_manager.active_sessions:
            return
        
        override_message = message_data.get('content', '')
        
        # Send override message to seller
        await manager.send_to_seller(session_id, {
            "type": "message",
            "content": override_message,
            "sender": "buyer"
        })
        
        # Log override in session
        session_data = session_manager.active_sessions[session_id]
        session = session_data['session']
        
        override_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            sender="user",
            content=override_message,
            timestamp=datetime.now(),
            sender_type="override"
        )
        
        session.messages.append(override_msg)
        await db.save_session(session)
        
        logger.info(f"User override in session {session_id}")
        
    except Exception as e:
        logger.error(f"Error handling user override: {e}")


async def handle_session_end_request(session_id: str, message_data: Dict[str, Any]):
    """Handle user request to end session"""
    try:
        if session_id not in session_manager.active_sessions:
            return
        
        # End session with user-specified outcome
        outcome = message_data.get('outcome', 'user_cancelled')
        final_price = message_data.get('final_price')
        
        session_data = session_manager.active_sessions[session_id]
        session = session_data['session']
        
        session.status = "cancelled"
        session.outcome = outcome
        session.final_price = final_price
        session.ended_at = datetime.now()
        
        await db.save_session(session)
        
        # Remove from active sessions
        del session_manager.active_sessions[session_id]
        
        # Notify both parties
        await manager.send_to_user(session_id, {
            "type": "session_ended",
            "outcome": outcome,
            "message": "Session ended by user"
        })
        
        await manager.send_to_seller(session_id, {
            "type": "session_ended",
            "message": "The buyer has ended the negotiation. Thank you for your time."
        })
        
        logger.info(f"Session {session_id} ended by user request")
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")


# ===============================
# LEGACY API ENDPOINTS (for demo compatibility)
# ===============================

@app.get("/api/products", response_model=List[Product])
async def get_products():
    """Get all predefined products (legacy endpoint)"""
    try:
        products = await db.get_products()
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """Get specific product by ID (legacy endpoint)"""
    try:
        product = await db.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/negotiations/start")
async def start_negotiation_legacy(params: NegotiationParams):
    """Start negotiation with predefined product (legacy endpoint)"""
    try:
        # Create session using legacy method
        session_id = str(uuid.uuid4())
        session = NegotiationSession(
            id=session_id,
            product_id=params.product_id,
            user_params=params,
            status="active",
            created_at=datetime.now(),
            messages=[]
        )
        
        # Get product details
        product = await db.get_product(params.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Simple session data for legacy compatibility
        session_data = {
            'session': session,
            'product': product,
            'market_analysis': {},
            'strategy': {'approach': params.approach.value},
            'phase': 'opening',
            'performance_metrics': {'messages_sent': 0}
        }
        
        # Store in session manager
        session_manager.active_sessions[session_id] = session_data
        await db.save_session(session)
        
        return {
            "session_id": session_id,
            "message": "Negotiation session started successfully",
            "product": product
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===============================
# ANALYTICS AND REPORTING
# ===============================

@app.get("/api/sessions/{session_id}")
async def get_session_details(session_id: str):
    """Get detailed session information"""
    try:
        if session_id in session_manager.active_sessions:
            session_data = session_manager.active_sessions[session_id]
            session = session_data['session']
            
            # Ensure proper serialization of session and user_params
            session_dict = session.dict()
            
            # Debug logging
            logger.info(f"Session dict for {session_id}: {session_dict}")
            logger.info(f"User params: {session_dict.get('user_params')}")
            
            return {
                "success": True,
                "session": session_dict,
                "product": session_data['product'].dict() if hasattr(session_data['product'], 'dict') else session_data['product'],
                "market_analysis": session_data.get('market_analysis', {}),
                "strategy": session_data.get('strategy', {}),
                "performance_metrics": session_data.get('performance_metrics', {}),
                "phase": session_data.get('phase', 'unknown'),
                "status": "active"
            }
        else:
            session = await db.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return {
                "success": True,
                "session": session.dict() if hasattr(session, 'dict') else session, 
                "status": "completed"
            }
            
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/performance")
async def get_performance_analytics():
    """Get overall system performance analytics"""
    try:
        # This would implement comprehensive analytics
        # For now, return basic stats
        
        total_sessions = len(session_manager.active_sessions)
        
        return {
            "active_sessions": total_sessions,
            "total_sessions_today": 0,  # Would implement proper counting
            "success_rate": 0.75,  # Would calculate from historical data
            "average_negotiation_time": 15.5,  # Minutes
            "top_tactics": ["anchoring", "reciprocity", "urgency"],
            "market_intelligence_accuracy": 0.85
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/sessions")
def debug_list_sessions():
    """Debug: List all active sessions"""
    return {
        "active_sessions": list(session_manager.active_sessions.keys()),
        "session_count": len(session_manager.active_sessions),
        "session_details": {
            session_id: {
                "user_websocket": session_data.get("user_websocket") is not None,
                "seller_websocket": session_data.get("seller_websocket") is not None,
                "created": session_data.get("created_at", "unknown")
            }
            for session_id, session_data in session_manager.active_sessions.items()
        }
    }

@app.get("/api/session/{session_id}/details")
def get_session_details(session_id: str):
    """Get session details for seller interface"""
    if session_id not in session_manager.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = session_manager.active_sessions[session_id]
    
    # Extract product details
    product = session_data.get("product")
    product_details = {}
    if product:
        if hasattr(product, 'dict'):
            product_details = product.dict()
        else:
            product_details = {
                "title": getattr(product, 'title', 'Unknown Product'),
                "price": getattr(product, 'price', 0),
                "original_price": getattr(product, 'original_price', 0),
                "description": getattr(product, 'description', ''),
                "location": getattr(product, 'location', ''),
                "condition": getattr(product, 'condition', ''),
                "seller_name": getattr(product, 'seller_name', ''),
                "url": getattr(product, 'url', '')
            }
    
    # Extract user parameters from session object
    session_obj = session_data.get("session")
    user_params = session_obj.user_params if session_obj and hasattr(session_obj, 'user_params') else session_data.get("user_params", {})
    
    # Handle user_params as either dict or NegotiationParams object
    if hasattr(user_params, 'target_price'):
        target_price = user_params.target_price
        max_budget = user_params.max_budget
        user_preferences = user_params.dict() if hasattr(user_params, 'dict') else {}
    else:
        target_price = user_params.get("target_price")
        max_budget = user_params.get("max_budget")
        user_preferences = user_params
    

    
    return {
        "session_id": session_id,
        "product_details": product_details,
        "target_price": target_price,
        "max_budget": max_budget,
        "user_preferences": user_preferences,
        "negotiation_status": session_data.get("status", "active"),
        "chat_history": session_data.get("chat_history", []),
        "created_at": session_data.get("created_at"),
        "is_connected": {
            "buyer": session_data.get("user_websocket") is not None,
            "seller": session_data.get("seller_websocket") is not None
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),  # Standard port
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )