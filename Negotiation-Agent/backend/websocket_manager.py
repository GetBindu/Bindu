from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional
import json
import asyncio
from enum import Enum
from datetime import datetime

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Enum and datetime objects"""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class ConnectionManager:
    def __init__(self):
        # Store WebSocket connections for users and sellers
        self.user_connections: Dict[str, WebSocket] = {}
        self.seller_connections: Dict[str, WebSocket] = {}
    
    async def connect_user(self, websocket: WebSocket, session_id: str):
        """Connect user (AI agent) to session"""
        await websocket.accept()
        self.user_connections[session_id] = websocket
        print(f"[INFO] User connected to session: {session_id}")
        
        # Send connection confirmation
        await self.send_to_user(session_id, {
            "type": "connected",
            "message": "Connected to negotiation session",
            "session_id": session_id
        })
    
    async def connect_seller(self, websocket: WebSocket, session_id: str):
        """Connect seller to session"""
        await websocket.accept()
        self.seller_connections[session_id] = websocket
        print(f"[INFO] Seller connected to session: {session_id}")
        
        # Send connection confirmation
        await self.send_to_seller(session_id, {
            "type": "connected",
            "message": "Connected to chat with buyer",
            "session_id": session_id
        })
        
        # Notify user that seller is online
        await self.send_to_user(session_id, {
            "type": "seller_online",
            "message": "Seller is now online"
        })
    
    def disconnect_user(self, session_id: str):
        """Disconnect user from session"""
        if session_id in self.user_connections:
            del self.user_connections[session_id]
            print(f"[INFO] User disconnected from session: {session_id}")
    
    def disconnect_seller(self, session_id: str):
        """Disconnect seller from session"""
        if session_id in self.seller_connections:
            del self.seller_connections[session_id]
            print(f"[INFO] Seller disconnected from session: {session_id}")
            
        # Notify user that seller went offline
        asyncio.create_task(self.send_to_user(session_id, {
            "type": "seller_offline",
            "message": "Seller went offline"
        }))
    
    async def send_to_user(self, session_id: str, message: dict):
        """Send message to user (AI agent side)"""
        if session_id in self.user_connections:
            try:
                websocket = self.user_connections[session_id]
                await websocket.send_text(json.dumps(message, cls=CustomJSONEncoder))
            except Exception as e:
                print(f"Error sending message to user {session_id}: {e}")
                self.disconnect_user(session_id)
    
    async def send_to_seller(self, session_id: str, message: dict):
        """Send message to seller"""
        if session_id in self.seller_connections:
            try:
                websocket = self.seller_connections[session_id]
                await websocket.send_text(json.dumps(message, cls=CustomJSONEncoder))
            except Exception as e:
                print(f"Error sending message to seller {session_id}: {e}")
                self.disconnect_seller(session_id)
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send message to both user and seller in a session"""
        await self.send_to_user(session_id, message)
        await self.send_to_seller(session_id, message)
    
    def is_user_connected(self, session_id: str) -> bool:
        """Check if user is connected to session"""
        return session_id in self.user_connections
    
    def is_seller_connected(self, session_id: str) -> bool:
        """Check if seller is connected to session"""
        return session_id in self.seller_connections
    
    def get_active_sessions(self) -> list:
        """Get list of active session IDs"""
        user_sessions = set(self.user_connections.keys())
        seller_sessions = set(self.seller_connections.keys())
        return list(user_sessions.union(seller_sessions))
    
    async def send_typing_indicator(self, session_id: str, sender: str, is_typing: bool):
        """Send typing indicator"""
        message = {
            "type": "typing",
            "sender": sender,
            "is_typing": is_typing
        }
        
        if sender == "user":
            await self.send_to_seller(session_id, message)
        elif sender == "seller":
            await self.send_to_user(session_id, message)
    
    async def send_status_update(self, session_id: str, status: str, details: dict = None):
        """Send status update to both parties"""
        message = {
            "type": "status_update",
            "status": status,
            "details": details or {}
        }
        await self.broadcast_to_session(session_id, message)