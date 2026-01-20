"""
Model Context Protocol (MCP) Integration
Provides intelligent context management for the negotiation agent
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
# import aioredis  # Commented out due to Python 3.13 compatibility issues
from database import JSONDatabase
from session_manager import AdvancedSessionManager

logger = logging.getLogger(__name__)

@dataclass
class NegotiationContext:
    """Rich context for negotiation decisions"""
    session_id: str
    product_info: Dict
    buyer_profile: Dict
    seller_info: Dict
    market_data: Dict
    conversation_history: List[Dict]
    negotiation_phase: str
    current_strategy: Dict
    sentiment_analysis: Dict
    price_history: List[Dict]
    success_metrics: Dict
    context_updated_at: datetime

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['context_updated_at'] = self.context_updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'NegotiationContext':
        """Create from dictionary"""
        data['context_updated_at'] = datetime.fromisoformat(data['context_updated_at'])
        return cls(**data)

logger = logging.getLogger(__name__)

class JSONContextManager:
    """
    JSON-based context manager for negotiation sessions
    Stores all context data in JSON files for persistence
    """
    
    def __init__(self, data_path: str = "./data"):
        self.data_path = data_path
        self.context_file = f"{data_path}/negotiation_contexts.json"
        self.session_file = f"{data_path}/negotiation_sessions.json"
        self.analytics_file = f"{data_path}/negotiation_analytics.json"
        
        # Ensure data directory exists
        import os
        os.makedirs(data_path, exist_ok=True)
        
        # Initialize files if they don't exist
        self._initialize_files()
        
        # In-memory cache for quick access
        self.context_cache: Dict[str, NegotiationContext] = {}
        
    def _initialize_files(self):
        """Initialize JSON files if they don't exist"""
        files = [
            (self.context_file, {}),
            (self.session_file, {}),
            (self.analytics_file, {})
        ]
        
        import os
        for file_path, default_data in files:
            if not os.path.exists(file_path):
                self._save_json(file_path, default_data)
    
    def _load_json(self, file_path: str) -> Dict:
        """Load data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, file_path: str, data: Dict):
        """Save data to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save JSON to {file_path}: {e}")

    async def create_negotiation_context(self, 
                                       session_id: str,
                                       product_info: Dict,
                                       buyer_profile: Dict,
                                       seller_info: Dict) -> NegotiationContext:
        """Create a new negotiation context"""
        
        context = NegotiationContext(
            session_id=session_id,
            product_info=product_info,
            buyer_profile=buyer_profile,
            seller_info=seller_info,
            market_data={},
            conversation_history=[],
            negotiation_phase="initialization",
            current_strategy={},
            sentiment_analysis={},
            price_history=[],
            success_metrics={
                "messages_exchanged": 0,
                "offers_made": 0,
                "counteroffers_received": 0,
                "price_concessions": 0,
                "negotiation_start": datetime.now().isoformat()
            },
            context_updated_at=datetime.now()
        )
        
        # Store in JSON file
        await self._store_context(context)
        
        # Cache locally for quick access
        self.context_cache[session_id] = context
        
        logger.info(f"Created negotiation context for session {session_id}")
        return context

    async def update_context(self, 
                           session_id: str, 
                           updates: Dict[str, Any]) -> NegotiationContext:
        """Update negotiation context with new information"""
        
        context = await self.get_context(session_id)
        if not context:
            raise ValueError(f"No context found for session {session_id}")
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(context, key):
                if key == "conversation_history" and isinstance(value, dict):
                    # Append to conversation history
                    context.conversation_history.append(value)
                elif key == "price_history" and isinstance(value, dict):
                    # Append to price history
                    context.price_history.append(value)
                elif key == "success_metrics" and isinstance(value, dict):
                    # Update metrics
                    context.success_metrics.update(value)
                else:
                    # Direct update
                    setattr(context, key, value)
        
        # Update timestamp
        context.context_updated_at = datetime.now()
        
        # Persist changes
        await self._store_context(context)
        self.context_cache[session_id] = context
        
        logger.debug(f"Updated context for session {session_id}")
        return context

    async def get_context(self, session_id: str) -> Optional[NegotiationContext]:
        """Retrieve negotiation context"""
        
        # Check local cache first
        if session_id in self.context_cache:
            return self.context_cache[session_id]
        
        # Load from JSON file
        contexts = self._load_json(self.context_file)
        if session_id in contexts:
            context = NegotiationContext.from_dict(contexts[session_id])
            self.context_cache[session_id] = context
            return context
            
        return None

    async def _store_context(self, context: NegotiationContext):
        """Store context in JSON file"""
        try:
            contexts = self._load_json(self.context_file)
            contexts[context.session_id] = context.to_dict()
            self._save_json(self.context_file, contexts)
        except Exception as e:
            logger.error(f"Failed to store context: {e}")

    async def add_message_to_context(self, 
                                   session_id: str,
                                   message: str,
                                   sender: str,
                                   metadata: Optional[Dict] = None) -> NegotiationContext:
        """Add a message to the conversation context"""
        
        message_data = {
            "content": message,
            "sender": sender,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Analyze message sentiment and intent
        analysis = await self._analyze_message(message, sender)
        message_data["analysis"] = analysis
        
        # Update context
        updates = {
            "conversation_history": message_data,
            "success_metrics": {
                "messages_exchanged": 1  # Will be added to existing count
            }
        }
        
        # Update negotiation phase based on message content
        phase_update = await self._determine_negotiation_phase(session_id, message, sender)
        if phase_update:
            updates["negotiation_phase"] = phase_update
        
        return await self.update_context(session_id, updates)

    async def _analyze_message(self, message: str, sender: str) -> Dict:
        """Analyze message for sentiment, intent, and negotiation signals"""
        
        # Simple sentiment analysis (in production, use proper NLP)
        positive_words = ["great", "excellent", "perfect", "good", "yes", "agree", "deal"]
        negative_words = ["no", "bad", "terrible", "refuse", "reject", "impossible"]
        negotiation_words = ["maybe", "consider", "think", "possible", "negotiate"]
        
        message_lower = message.lower()
        
        sentiment_score = 0
        for word in positive_words:
            if word in message_lower:
                sentiment_score += 1
        for word in negative_words:
            if word in message_lower:
                sentiment_score -= 1
        
        # Determine intent
        intent = "neutral"
        if any(word in message_lower for word in ["buy", "purchase", "take", "deal"]):
            intent = "purchase"
        elif any(word in message_lower for word in ["sell", "offer", "price"]):
            intent = "selling"
        elif any(word in message_lower for word in negotiation_words):
            intent = "negotiate"
        
        return {
            "sentiment_score": sentiment_score,
            "sentiment": "positive" if sentiment_score > 0 else "negative" if sentiment_score < 0 else "neutral",
            "intent": intent,
            "urgency": "high" if "urgent" in message_lower or "quickly" in message_lower else "normal",
            "flexibility": "high" if any(word in message_lower for word in negotiation_words) else "low"
        }

    async def _determine_negotiation_phase(self, session_id: str, message: str, sender: str) -> Optional[str]:
        """Determine current negotiation phase based on message content"""
        
        context = await self.get_context(session_id)
        if not context:
            return None
        
        message_lower = message.lower()
        current_phase = context.negotiation_phase
        
        # Phase progression logic
        if current_phase == "initialization":
            if sender == "agent" and any(word in message_lower for word in ["interested", "price", "offer"]):
                return "opening_offer"
        elif current_phase == "opening_offer":
            if sender == "seller" and any(word in message_lower for word in ["counter", "offer", "price"]):
                return "active_negotiation"
        elif current_phase == "active_negotiation":
            if any(word in message_lower for word in ["accept", "deal", "agreed"]):
                return "closing"
            elif any(word in message_lower for word in ["final", "last", "best"]):
                return "final_offer"
        elif current_phase == "final_offer":
            if any(word in message_lower for word in ["accept", "deal"]):
                return "agreement"
            elif any(word in message_lower for word in ["no", "reject", "impossible"]):
                return "deadlock"
        
        return None

    def get_all_sessions(self) -> Dict[str, Dict]:
        """Get all negotiation sessions"""
        return self._load_json(self.session_file)

    def save_session_analytics(self, session_id: str, analytics: Dict):
        """Save analytics for a session"""
        all_analytics = self._load_json(self.analytics_file)
        all_analytics[session_id] = {
            **analytics,
            "saved_at": datetime.now().isoformat()
        }
        self._save_json(self.analytics_file, all_analytics)

    def get_session_analytics(self, session_id: str) -> Optional[Dict]:
        """Get analytics for a specific session"""
        all_analytics = self._load_json(self.analytics_file)
        return all_analytics.get(session_id)

    async def cleanup_old_contexts(self, max_age_hours: int = 24):
        """Clean up old contexts to save storage"""
        try:
            contexts = self._load_json(self.context_file)
            cleaned_contexts = {}
            cleaned_count = 0
            
            for session_id, context_data in contexts.items():
                try:
                    updated_at = datetime.fromisoformat(context_data["context_updated_at"])
                    if (datetime.now() - updated_at).total_seconds() / 3600 < max_age_hours:
                        cleaned_contexts[session_id] = context_data
                    else:
                        cleaned_count += 1
                        # Remove from cache too
                        if session_id in self.context_cache:
                            del self.context_cache[session_id]
                except (KeyError, ValueError):
                    # Keep context if we can't parse the date
                    cleaned_contexts[session_id] = context_data
            
            self._save_json(self.context_file, cleaned_contexts)
            logger.info(f"Cleaned up {cleaned_count} old negotiation contexts")
            
        except Exception as e:
            logger.error(f"Context cleanup failed: {e}")
    
    def __init__(self, db: JSONDatabase, session_manager: AdvancedSessionManager):
        self.db = db
        self.session_manager = session_manager
        self.market_intelligence = MarketIntelligence()
        self.server = Server("negotiation-agent")
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools for the negotiation agent"""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="get_market_intelligence",
                        description="Get comprehensive market analysis for a product",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "product_title": {"type": "string"},
                                "product_price": {"type": "number"},
                                "product_category": {"type": "string"}
                            },
                            "required": ["product_title", "product_price"]
                        }
                    ),
                    Tool(
                        name="analyze_seller_behavior",
                        description="Analyze seller's communication pattern and flexibility",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "messages": {"type": "array", "items": {"type": "string"}},
                                "response_times": {"type": "array", "items": {"type": "number"}},
                                "price_movements": {"type": "array", "items": {"type": "number"}}
                            },
                            "required": ["messages"]
                        }
                    ),
                    Tool(
                        name="calculate_negotiation_strategy",
                        description="Calculate optimal negotiation strategy based on context",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "current_price": {"type": "number"},
                                "target_price": {"type": "number"},
                                "max_budget": {"type": "number"},
                                "seller_flexibility": {"type": "string"},
                                "negotiation_phase": {"type": "string"}
                            },
                            "required": ["current_price", "target_price", "max_budget"]
                        }
                    ),
                    Tool(
                        name="generate_tactical_response",
                        description="Generate a tactical negotiation response",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "tactic": {"type": "string"},
                                "context": {"type": "object"},
                                "seller_message": {"type": "string"},
                                "target_outcome": {"type": "string"}
                            },
                            "required": ["tactic", "context", "seller_message"]
                        }
                    ),
                    Tool(
                        name="assess_deal_quality",
                        description="Assess the quality of a deal offer",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "offer_price": {"type": "number"},
                                "original_price": {"type": "number"},
                                "market_average": {"type": "number"},
                                "product_condition": {"type": "string"}
                            },
                            "required": ["offer_price", "original_price"]
                        }
                    ),
                    Tool(
                        name="predict_negotiation_outcome",
                        description="Predict likely outcomes of different negotiation approaches",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "session_context": {"type": "object"},
                                "proposed_actions": {"type": "array", "items": {"type": "object"}}
                            },
                            "required": ["session_context"]
                        }
                    )
                ]
            )
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls from the negotiation agent"""
            
            try:
                if name == "get_market_intelligence":
                    result = await self._get_market_intelligence(arguments)
                elif name == "analyze_seller_behavior":
                    result = await self._analyze_seller_behavior(arguments)
                elif name == "calculate_negotiation_strategy":
                    result = await self._calculate_negotiation_strategy(arguments)
                elif name == "generate_tactical_response":
                    result = await self._generate_tactical_response(arguments)
                elif name == "assess_deal_quality":
                    result = await self._assess_deal_quality(arguments)
                elif name == "predict_negotiation_outcome":
                    result = await self._predict_negotiation_outcome(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result))]
                )
                
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "error": str(e),
                        "tool": name
                    }))]
                )
        
        @self.server.list_resources()
        async def list_resources() -> ListResourcesResult:
            """List available resources"""
            return ListResourcesResult(
                resources=[
                    Resource(
                        uri="negotiation://context/current",
                        name="Current Negotiation Context",
                        mimeType="application/json",
                        description="Current state of all active negotiations"
                    ),
                    Resource(
                        uri="negotiation://history/sessions",
                        name="Session History",
                        mimeType="application/json", 
                        description="Historical negotiation session data"
                    ),
                    Resource(
                        uri="negotiation://market/intelligence",
                        name="Market Intelligence",
                        mimeType="application/json",
                        description="Real-time market data and trends"
                    )
                ]
            )
    
    async def _get_market_intelligence(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get market intelligence for a product"""
        try:
            analysis = await self.market_intelligence.comprehensive_product_analysis(
                {
                    "title": args["product_title"],
                    "price": args["product_price"],
                    "category": args.get("product_category", "general")
                },
                target_price=args["product_price"] * 0.8,
                max_budget=args["product_price"] * 1.2
            )
            return analysis
        except Exception as e:
            return {"error": str(e), "fallback_data": {
                "average_price": args["product_price"] * 0.9,
                "price_range": {
                    "min": args["product_price"] * 0.7,
                    "max": args["product_price"] * 1.3
                },
                "market_trend": "stable"
            }}
    
    async def _analyze_seller_behavior(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze seller behavior patterns"""
        messages = args["messages"]
        response_times = args.get("response_times", [])
        price_movements = args.get("price_movements", [])
        
        # Sentiment analysis
        sentiment_scores = []
        flexibility_indicators = []
        urgency_indicators = []
        
        for msg in messages:
            msg_lower = msg.lower()
            
            # Sentiment (simplified)
            if any(word in msg_lower for word in ["great", "excellent", "perfect", "love"]):
                sentiment_scores.append(1)
            elif any(word in msg_lower for word in ["sorry", "can't", "no", "impossible"]):
                sentiment_scores.append(-1)
            else:
                sentiment_scores.append(0)
            
            # Flexibility indicators
            if any(phrase in msg_lower for phrase in ["maybe", "could", "might", "let me think"]):
                flexibility_indicators.append(1)
            elif any(phrase in msg_lower for phrase in ["final", "firm", "non-negotiable"]):
                flexibility_indicators.append(-1)
            else:
                flexibility_indicators.append(0)
            
            # Urgency indicators
            if any(word in msg_lower for word in ["quick", "urgent", "asap", "soon"]):
                urgency_indicators.append(1)
            else:
                urgency_indicators.append(0)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        avg_flexibility = sum(flexibility_indicators) / len(flexibility_indicators) if flexibility_indicators else 0
        avg_urgency = sum(urgency_indicators) / len(urgency_indicators) if urgency_indicators else 0
        
        return {
            "sentiment": "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "neutral",
            "flexibility": "high" if avg_flexibility > 0.3 else "low" if avg_flexibility < -0.3 else "medium",
            "urgency": "high" if avg_urgency > 0.5 else "low",
            "response_pattern": "quick" if response_times and sum(response_times)/len(response_times) < 300 else "slow",
            "price_trend": "declining" if price_movements and price_movements[-1] < price_movements[0] else "stable",
            "recommended_approach": self._recommend_approach(avg_sentiment, avg_flexibility, avg_urgency)
        }
    
    def _recommend_approach(self, sentiment: float, flexibility: float, urgency: float) -> str:
        """Recommend negotiation approach based on seller analysis"""
        if flexibility > 0.3 and sentiment > 0:
            return "collaborative"
        elif urgency > 0.5:
            return "patient_opportunistic"
        elif sentiment < -0.2:
            return "diplomatic_persistent"
        else:
            return "balanced_professional"
    
    async def _calculate_negotiation_strategy(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal negotiation strategy"""
        current_price = args["current_price"]
        target_price = args["target_price"]
        max_budget = args["max_budget"]
        seller_flexibility = args.get("seller_flexibility", "medium")
        phase = args.get("negotiation_phase", "exploration")
        
        gap = current_price - target_price
        budget_room = max_budget - target_price
        
        # Calculate recommended counter-offer
        if seller_flexibility == "high":
            counter_ratio = 0.4
        elif seller_flexibility == "low":
            counter_ratio = 0.7
        else:
            counter_ratio = 0.6
        
        counter_offer = max(target_price, current_price - (gap * counter_ratio))
        
        # Select tactics based on phase and seller type
        tactics = []
        if phase == "opening":
            tactics = ["anchoring", "market_research"]
        elif phase == "exploration":
            tactics = ["information_gathering", "value_demonstration"]
        elif phase == "bargaining":
            if seller_flexibility == "high":
                tactics = ["reciprocity", "bundling"]
            else:
                tactics = ["authority", "social_proof"]
        elif phase == "closing":
            tactics = ["urgency", "commitment"]
        
        return {
            "recommended_counter_offer": int(counter_offer),
            "tactics": tactics,
            "confidence": 0.8 if seller_flexibility == "high" else 0.6,
            "approach": "aggressive" if gap > budget_room else "conservative",
            "next_steps": self._get_next_steps(phase, seller_flexibility),
            "risk_assessment": "low" if counter_offer <= max_budget else "high"
        }
    
    def _get_next_steps(self, phase: str, flexibility: str) -> List[str]:
        """Get recommended next steps"""
        if phase == "opening":
            return ["establish_rapport", "gather_product_details", "set_initial_anchor"]
        elif phase == "exploration":
            return ["probe_seller_motivation", "share_market_data", "test_flexibility"]
        elif phase == "bargaining":
            if flexibility == "high":
                return ["make_progressive_offers", "bundle_additional_value"]
            else:
                return ["use_external_pressure", "create_scarcity"]
        else:
            return ["finalize_terms", "arrange_transaction"]
    
    async def _generate_tactical_response(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a tactical response"""
        # This would integrate with your existing response generation
        tactic = args["tactic"]
        context = args["context"]
        seller_message = args["seller_message"]
        target_outcome = args.get("target_outcome", "price_reduction")
        
        # Simplified tactical response generation
        responses = {
            "anchoring": f"Based on similar products I've seen, I was thinking more around ₹{int(context.get('target_price', 0)):,}. What do you think?",
            "market_research": f"I've been researching similar items and found they typically sell for ₹{int(context.get('market_average', 0)):,}. Can we work with that?",
            "scarcity": "I'm really interested in this item and ready to make a decision today if we can find the right price.",
            "reciprocity": "I appreciate your flexibility on this. To meet you halfway, what if we settled on ₹{int(context.get('counter_offer', 0)):,}?",
            "urgency": "I need to make a decision by tomorrow. If we can agree on ₹{int(context.get('final_offer', 0)):,}, I can transfer the amount immediately."
        }
        
        return {
            "message": responses.get(tactic, "Let me think about your offer and get back to you."),
            "tactic_used": tactic,
            "expected_outcome": target_outcome,
            "follow_up_actions": ["wait_for_response", "assess_reaction"]
        }
    
    async def _assess_deal_quality(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Assess deal quality"""
        offer_price = args["offer_price"]
        original_price = args["original_price"]
        market_average = args.get("market_average", original_price)
        
        savings_from_original = original_price - offer_price
        savings_percent = (savings_from_original / original_price) * 100
        
        market_savings = market_average - offer_price
        market_savings_percent = (market_savings / market_average) * 100 if market_average > 0 else 0
        
        if savings_percent >= 20:
            quality = "excellent"
        elif savings_percent >= 10:
            quality = "good"
        elif savings_percent >= 5:
            quality = "fair"
        else:
            quality = "poor"
        
        return {
            "deal_quality": quality,
            "savings_amount": int(savings_from_original),
            "savings_percent": round(savings_percent, 2),
            "market_comparison": "above_average" if market_savings_percent > 5 else "below_average" if market_savings_percent < -5 else "average",
            "recommendation": "accept" if quality in ["excellent", "good"] else "negotiate",
            "confidence": 0.9 if quality == "excellent" else 0.7 if quality == "good" else 0.5
        }
    
    async def _predict_negotiation_outcome(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Predict negotiation outcomes"""
        session_context = args["session_context"]
        
        # Simplified outcome prediction based on context
        current_gap = session_context.get("price_gap", 0)
        seller_flexibility = session_context.get("seller_flexibility", "medium")
        negotiation_rounds = session_context.get("rounds", 0)
        
        if seller_flexibility == "high" and current_gap < 0.2:
            success_probability = 0.85
            predicted_final_price = session_context.get("target_price", 0) * 1.05
        elif seller_flexibility == "medium":
            success_probability = 0.65
            predicted_final_price = session_context.get("target_price", 0) * 1.15
        else:  # low flexibility
            success_probability = 0.35
            predicted_final_price = session_context.get("current_price", 0) * 0.95
        
        return {
            "success_probability": success_probability,
            "predicted_final_price": int(predicted_final_price),
            "estimated_rounds_remaining": max(1, 5 - negotiation_rounds),
            "key_factors": ["seller_flexibility", "price_gap", "negotiation_history"],
            "recommendations": [
                "continue_negotiating" if success_probability > 0.5 else "consider_walking_away",
                "use_urgency_tactics" if negotiation_rounds > 3 else "gather_more_information"
            ]
        }

    async def get_negotiation_context(self, session_id: str) -> NegotiationContext:
        """Get complete negotiation context for a session"""
        try:
            session_data = self.session_manager.active_sessions.get(session_id, {})
            if not session_data:
                raise ValueError(f"Session {session_id} not found")
            
            return NegotiationContext(
                session_id=session_id,
                product=session_data.get("product", {}).dict() if session_data.get("product") else {},
                market_analysis=session_data.get("market_analysis", {}),
                chat_history=[msg.dict() for msg in session_data.get("session", {}).messages or []],
                seller_analysis=session_data.get("seller_analysis", {}),
                negotiation_state=session_data.get("strategy", {}),
                user_preferences=session_data.get("user_params", {}).dict() if session_data.get("user_params") else {},
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error getting negotiation context: {e}")
            raise

# Global MCP server instance
mcp_server = None

# def initialize_mcp_server(db: JSONDatabase, session_manager: AdvancedSessionManager) -> NegotiationMCPServer:
#     """Initialize the global MCP server"""
#     global mcp_server
#     mcp_server = NegotiationMCPServer(db, session_manager)
#     return mcp_server

# def get_mcp_server() -> Optional[NegotiationMCPServer]:
#     """Get the global MCP server instance"""
#     return mcp_server