from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NegotiationApproach(str, Enum):
    ASSERTIVE = "assertive"
    DIPLOMATIC = "diplomatic"
    CONSIDERATE = "considerate"


class PurchaseTimeline(str, Enum):
    FLEXIBLE = "flexible"
    WEEK = "week"
    URGENT = "urgent"


class Product(BaseModel):
    id: str
    title: str
    description: str
    price: int
    original_price: int
    seller_name: str
    seller_contact: str
    location: str
    url: str
    platform: str  # olx, facebook, etc.
    category: str
    condition: str
    images: List[str] = []
    features: List[str] = []
    posted_date: datetime
    is_available: bool = True


class NegotiationParams(BaseModel):
    product_id: str
    target_price: int = Field(..., gt=0, description="Target price in INR")
    max_budget: int = Field(..., gt=0, description="Maximum budget in INR")
    approach: NegotiationApproach = Field(..., description="Negotiation approach")
    timeline: PurchaseTimeline = Field(default=PurchaseTimeline.FLEXIBLE)
    special_requirements: Optional[str] = Field(None, description="Special requirements")
    
    class Config:
        use_enum_values = True


class ChatMessage(BaseModel):
    id: str
    session_id: str
    sender: str  # "user", "seller", "ai"
    content: str
    timestamp: datetime
    sender_type: str  # "human", "ai", "override"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NegotiationSession(BaseModel):
    id: str
    product_id: str
    user_params: NegotiationParams
    status: str  # "active", "completed", "failed", "cancelled"
    created_at: datetime
    ended_at: Optional[datetime] = None
    messages: List[ChatMessage] = []
    final_price: Optional[int] = None
    outcome: Optional[str] = None  # "success", "failed", "cancelled"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebSocketMessage(BaseModel):
    type: str  # "message", "typing", "status", "error"
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AIResponse(BaseModel):
    content: str
    confidence: float
    strategy_used: str
    next_action: Optional[str] = None