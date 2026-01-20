"""
Enhanced AI Service - Now with LangChain Integration
Combines negotiation engine with LangChain AI agent, MCP integration and Gemini fallback
"""

import os
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from pydantic import BaseModel, Field

# Local imports
from models import NegotiationSession, ChatMessage
from negotiation_engine import AdvancedNegotiationEngine
from scraper_service import MarketplaceScraper
# from mcp_integration import JSONContextManager, NegotiationContext  # Temporarily disabled
from gemini_service import GeminiOnlyService
from langchain_agent import LangChainNegotiationAgent, NegotiationContext as LangChainContext

logger = logging.getLogger(__name__)

# Simple local NegotiationContext class
@dataclass
class NegotiationContext:
    """Simple context for negotiation decisions"""
    product: Dict[str, Any]
    target_price: int
    max_budget: int
    seller_messages: List[str]
    chat_history: List[Dict[str, Any]]
    market_data: Dict[str, Any]
    session_data: Dict[str, Any]
    negotiation_phase: str

class NegotiationResponse(BaseModel):
    """Structured response from the AI agent"""
    message: str = Field(description="Message to send to seller")
    action_type: str = Field(description="Type of action: offer, counter_offer, accept, reject, question")
    price_offer: Optional[int] = Field(description="Price offer if making an offer", default=None)
    confidence: float = Field(description="Confidence in this response (0-1)")
    reasoning: str = Field(description="Internal reasoning for this response")
    tactics_used: List[str] = Field(description="Negotiation tactics employed")
    next_steps: List[str] = Field(description="Recommended next steps")

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from pydantic import BaseModel, Field

# Local imports
from models import NegotiationSession, ChatMessage
from negotiation_engine import AdvancedNegotiationEngine
from scraper_service import MarketplaceScraper
# from mcp_integration import JSONContextManager, NegotiationContext  # Temporarily disabled
from gemini_service import GeminiOnlyService
from langchain_agent import LangChainNegotiationAgent, NegotiationContext as LangChainContext

logger = logging.getLogger(__name__)

# Simple local NegotiationContext class
@dataclass
class NegotiationContext:
    """Simple context for negotiation decisions"""
    product: Dict[str, Any]
    target_price: int
    max_budget: int
    seller_messages: List[str]
    chat_history: List[Dict[str, Any]]
    market_data: Dict[str, Any]
    session_data: Dict[str, Any]
    negotiation_phase: str

class NegotiationResponse(BaseModel):
    """Structured response from the AI agent"""
    message: str = Field(description="Message to send to seller")
    action_type: str = Field(description="Type of action: offer, counter_offer, accept, reject, question")
    price_offer: Optional[int] = Field(description="Price offer if making an offer", default=None)
    confidence: float = Field(description="Confidence in this response (0-1)")
    reasoning: str = Field(description="Internal reasoning for this response")
    tactics_used: List[str] = Field(description="Negotiation tactics employed")
    next_steps: List[str] = Field(description="Recommended next steps")


class EnhancedAIService:
    """Enhanced AI service combining traditional negotiation engine with MCP and Gemini"""
    
    def __init__(self, use_langchain: bool = True, use_mcp: bool = False):
        self.use_langchain = use_langchain  # Now enabled with proper integration
        self.use_mcp = use_mcp
        self.langchain_agent = None
        self.mcp_context_manager = None
        self.negotiation_engine = AdvancedNegotiationEngine()
        self.scraper_service = MarketplaceScraper()
        self.gemini_service = GeminiOnlyService()
        
        # Initialize services
        self.initialize_services()
    
    def initialize_services(self):
        """Initialize AI services"""
        try:
            # Initialize LangChain agent
            if self.use_langchain:
                try:
                    google_api_key = os.getenv("GOOGLE_API_KEY")
                    if google_api_key:
                        self.langchain_agent = LangChainNegotiationAgent(google_api_key)
                        logger.info("✅ LangChain negotiation agent initialized successfully")
                    else:
                        logger.warning("Google API key not found, disabling LangChain")
                        self.use_langchain = False
                        self.langchain_agent = None
                except Exception as e:
                    logger.error(f"LangChain initialization error: {e}")
                    logger.info("Falling back to Gemini-only service")
                    self.use_langchain = False
                    self.langchain_agent = None
            
            # MCP temporarily disabled
            self.use_mcp = False
            # if self.use_mcp:
            #     try:
            #         self.mcp_context_manager = JSONContextManager()
            #         logger.info("MCP context manager initialized")
            #     except Exception as e:
            #         logger.error(f"MCP initialization error: {e}")
            #         self.use_mcp = False
            
        except Exception as e:
            logger.error(f"Error initializing AI services: {e}")
            self.use_langchain = False
            self.use_mcp = False
    
    async def make_negotiation_decision(
        self,
        session_data: Dict[str, Any],
        seller_message: str,
        chat_history: List[Dict[str, Any]],
        product: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make an intelligent negotiation decision using all available AI systems
        """
        try:
            # Step 1: Prepare context for AI systems
            context = await self._prepare_negotiation_context(
                session_data, seller_message, chat_history, product
            )
            
            # Step 2: Try LangChain agent first (highest priority)
            if self.use_langchain and self.langchain_agent:
                try:
                    # Convert Pydantic models to dictionaries for LangChain compatibility
                    try:
                        product_dict = product.dict() if hasattr(product, 'dict') else dict(product.__dict__)
                    except Exception as e:
                        logger.warning(f"Product conversion error: {e}")
                        product_dict = {
                            "id": getattr(product, 'id', ''),
                            "title": getattr(product, 'title', ''),
                            "price": getattr(product, 'price', 0),
                            "description": getattr(product, 'description', '')
                        }
                    
                    # Convert chat_history to list of dictionaries
                    chat_history_dicts = []
                    for msg in context.chat_history:
                        try:
                            if hasattr(msg, 'dict'):
                                msg_dict = msg.dict()
                                # Ensure datetime objects are converted to strings
                                if 'timestamp' in msg_dict and hasattr(msg_dict['timestamp'], 'isoformat'):
                                    msg_dict['timestamp'] = msg_dict['timestamp'].isoformat()
                                chat_history_dicts.append(msg_dict)
                            else:
                                chat_history_dicts.append(dict(msg))
                        except Exception as e:
                            logger.warning(f"Chat message conversion error: {e}")
                            # Fallback with basic structure
                            chat_history_dicts.append({
                                "sender": getattr(msg, 'sender', 'unknown'),
                                "content": getattr(msg, 'content', ''),
                                "timestamp": getattr(msg, 'timestamp', datetime.now()).isoformat() if hasattr(getattr(msg, 'timestamp', None), 'isoformat') else str(getattr(msg, 'timestamp', ''))
                            })
                    
                    langchain_context = LangChainContext(
                        product=product_dict,
                        target_price=context.target_price,
                        max_budget=context.max_budget,
                        current_offer=session_data.get("last_offer"),
                        seller_messages=context.seller_messages,
                        chat_history=chat_history_dicts,
                        market_data=context.market_data,
                        session_data=context.session_data,
                        negotiation_phase=context.negotiation_phase
                    )
                    
                    langchain_decision = await self.langchain_agent.generate_negotiation_response(
                        langchain_context
                    )
                    
                    if langchain_decision and langchain_decision.get("confidence", 0) >= 0.4:
                        logger.info("🚀 Using LangChain agent decision")
                        # Transform LangChain response to match expected format
                        formatted_decision = {
                            'response': langchain_decision.get('message', ''),
                            'decision': {
                                'action': langchain_decision.get('action_type', 'respond'),
                                'confidence': langchain_decision.get('confidence', 0.75),
                                'reasoning': langchain_decision.get('reasoning', ''),
                                'price_offer': langchain_decision.get('price_offer')
                            },
                            'tactics_used': langchain_decision.get('tactics_used', []),
                            'phase': langchain_decision.get('negotiation_phase', 'exploration'),
                            'confidence': langchain_decision.get('confidence', 0.75),
                            'seller_analysis': langchain_decision.get('seller_analysis', {}),
                            'source': 'langchain_agent'
                        }
                        self._log_decision(formatted_decision, session_data)
                        return formatted_decision
                    else:
                        logger.info(f"LangChain confidence low ({langchain_decision.get('confidence', 0) if langchain_decision else 'None'}), falling back to engine")
                        
                except Exception as e:
                    logger.error(f"LangChain agent error: {e}")
                    logger.info("Falling back to traditional engine")
            
            # Step 3: Get MCP-enhanced insights - temporarily disabled
            mcp_insights = None
            # if self.use_mcp and self.mcp_context_manager:
            #     try:
            #         mcp_insights = await self._get_mcp_insights(context, session_data)
            #         logger.info("MCP insights obtained")
            #     except Exception as e:
            #         logger.error(f"MCP insights error: {e}")
            #         mcp_insights = None
            
            # Step 4: Get decision from traditional negotiation engine
            engine_decision = await self.negotiation_engine.process_negotiation_turn(
                session_data, seller_message, chat_history, product
            )
            
            # Step 5: Enhance with Gemini if available
            if os.getenv("GEMINI_API_KEY"):
                try:
                    gemini_enhancement = await self._get_gemini_enhancement(
                        context, engine_decision
                    )
                    if gemini_enhancement:
                        engine_decision = self._merge_gemini_enhancement(
                            engine_decision, gemini_enhancement
                        )
                except Exception as e:
                    logger.error(f"Gemini enhancement error: {e}")
            
            # Step 6: Combine with MCP insights
            final_decision = self._combine_with_mcp(engine_decision, mcp_insights)
            
            # Step 7: Log decision for learning
            self._log_decision(final_decision, session_data)
            
            return final_decision
            
        except Exception as e:
            logger.error(f"Error in AI decision making: {e}")
            return await self._fallback_decision(session_data, seller_message, chat_history, product)
    
    async def _prepare_negotiation_context(
        self,
        session_data: Dict[str, Any],
        seller_message: str,
        chat_history: List[Dict[str, Any]],
        product: Dict[str, Any]
    ) -> NegotiationContext:
        """Prepare comprehensive context for AI systems"""
        
        # Extract user parameters
        user_params = session_data.get("user_params", {})
        product_price = product.price if hasattr(product, 'price') else 0
        target_price = user_params.get("target_price", product_price * 0.8)
        max_budget = user_params.get("max_budget", product_price)
        
        # Get market data
        market_data = session_data.get("market_analysis", {})
        if not market_data:
            # Basic market data if not available
            market_data = {
                "average_price": product_price * 0.9,
                "price_range": {"min": product_price * 0.7, "max": product_price * 1.2},
                "market_trend": "stable"
            }
        
        # Determine negotiation phase
        negotiation_phase = self._determine_phase(chat_history, seller_message)
        
        # Analyze seller messages
        seller_messages = []
        for msg in chat_history:
            # Handle both object and dict formats
            if hasattr(msg, 'sender') and hasattr(msg, 'content'):
                if msg.sender == "seller":
                    seller_messages.append(msg.content)
            elif isinstance(msg, dict):
                if msg.get('sender') == "seller":
                    seller_messages.append(msg.get('content', ''))
        
        if seller_message:
            seller_messages.append(seller_message)
        
        return NegotiationContext(
            product=product,
            target_price=int(target_price),
            max_budget=int(max_budget),
            seller_messages=seller_messages,
            chat_history=chat_history,
            market_data=market_data,
            session_data=session_data,
            negotiation_phase=negotiation_phase
        )
    
    async def _get_mcp_insights(self, context: NegotiationContext, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get insights from MCP context manager"""
        
        try:
            # Update context with latest information
            session_id = session_data.get("session_id", "default")
            await self.mcp_context_manager.update_context(session_id, context)
            
            # Get analytical insights
            insights = await self.mcp_context_manager.get_insights(session_id)
            
            return {
                "market_insights": insights.get("market_analysis", {}),
                "negotiation_insights": insights.get("negotiation_patterns", {}),
                "recommendations": insights.get("recommendations", []),
                "confidence": insights.get("confidence", 0.7)
            }
            
        except Exception as e:
            logger.error(f"MCP insights error: {e}")
            return {}
    
    async def _get_gemini_enhancement(self, context: NegotiationContext, base_decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get enhancement suggestions from Gemini"""
        
        try:
            # Create prompt for Gemini
            product_name = context.product.title if hasattr(context.product, 'title') else 'Unknown'
            product_price = context.product.price if hasattr(context.product, 'price') else 0
            prompt = f"""
            You are a master negotiation strategist. Create a sophisticated, market-driven response for this negotiation:
            
            SITUATION ANALYSIS:
            - Product: {product_name}
            - Listed Price: ₹{product_price}
            - Target Price: ₹{context.target_price}
            - Max Budget: ₹{context.max_budget}
            - Phase: {context.negotiation_phase}
            
            SELLER'S RECENT BEHAVIOR:
            {context.seller_messages[-2:] if context.seller_messages else ['No messages yet']}
            
            CURRENT PROPOSAL TO ENHANCE:
            - Action: {base_decision.get('action_type', 'unknown')}
            - Message: {base_decision.get('message', '')}
            - Price Offer: ₹{base_decision.get('price_offer', 'None')}
            
            STRATEGIC ENHANCEMENT REQUIRED:
            1. **MARKET POSITIONING**: Use specific market data points and comparisons
            2. **PSYCHOLOGICAL TACTICS**: Apply anchoring, reciprocity, or scarcity as appropriate  
            3. **INCREMENTAL PROGRESSION**: Show strategic movement toward agreement
            4. **EVIDENCE-BASED ARGUMENTS**: Include reasons why the price is justified
            5. **PROFESSIONAL TONE**: Maintain respect while being firm and confident
            
            Create a response that:
            - Uses market intelligence to justify price points
            - Shows strategic thinking with specific reasoning
            - Applies appropriate negotiation tactics for the current phase
            - Maintains professional relationship while driving toward target
            
            JSON Response Required: {{"message_enhancement": "enhanced strategic message", "strategy_tips": "tactical reasoning", "confidence_adjustment": 0.1}}
            """
            
            # Get response from Gemini using strategic response method
            # Convert context.product to Product object if it's a dict
            if isinstance(context.product, dict):
                from models import Product
                from datetime import datetime
                product_obj = Product(
                    id=context.product.get('id', ''),
                    title=context.product.get('title', ''),
                    description=context.product.get('description', ''),
                    price=context.product.get('price', 0),
                    original_price=context.product.get('original_price', context.product.get('price', 0)),
                    seller_name=context.product.get('seller_name', ''),
                    seller_contact=context.product.get('seller_contact', ''),
                    location=context.product.get('location', ''),
                    url=context.product.get('url', ''),
                    platform=context.product.get('platform', ''),
                    category=context.product.get('category', ''),
                    condition=context.product.get('condition', ''),
                    images=context.product.get('images', []),
                    features=context.product.get('features', []),
                    posted_date=datetime.now(),
                    is_available=context.product.get('is_available', True)
                )
            else:
                product_obj = context.product

            response = await self.gemini_service.generate_strategic_response(
                session_data=context.session_data,
                seller_message=context.seller_messages[-1] if context.seller_messages else "",
                tactics=[],  # Will be determined by the method
                decision=base_decision,
                product=product_obj
            )
            
            if response:
                try:
                    # Handle both string and dict responses
                    content = response.get("content") if isinstance(response, dict) else response
                    if content:
                        # Try to parse as JSON
                        import re
                        json_match = re.search(r'\{.*\}', str(content), re.DOTALL)
                        if json_match:
                            enhancement = json.loads(json_match.group())
                            return enhancement
                except json.JSONDecodeError:
                    pass
                
                # If JSON parsing fails, return structured response
                content = response.get("content") if isinstance(response, dict) else str(response)
                return {
                    "message_enhancement": content[:200] if content else "Enhancement unavailable",
                    "strategy_tips": ["Use Gemini's advice"],
                    "confidence_adjustment": 0.1
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Gemini enhancement error: {e}")
            return None
    
    def _merge_gemini_enhancement(self, base_decision: Dict[str, Any], enhancement: Dict[str, Any]) -> Dict[str, Any]:
        """Merge Gemini enhancement with base decision"""
        
        enhanced_decision = base_decision.copy()
        
        # Enhance message if available
        if enhancement.get("message_enhancement"):
            # Keep base message but add enhancement note
            enhanced_decision["message"] = f"{base_decision.get('message', '')} {enhancement['message_enhancement'][:100]}"
        
        # Adjust confidence
        confidence_adj = enhancement.get("confidence_adjustment", 0)
        current_confidence = enhanced_decision.get("confidence", 0.7)
        enhanced_decision["confidence"] = min(1.0, max(0.0, current_confidence + confidence_adj))
        
        # Add strategy tips to tactics
        strategy_tips = enhancement.get("strategy_tips", [])
        current_tactics = enhanced_decision.get("tactics_used", [])
        enhanced_decision["tactics_used"] = current_tactics + strategy_tips[:2]  # Limit to 2 tips
        
        # Update reasoning
        enhanced_decision["reasoning"] = f"{base_decision.get('reasoning', '')} Enhanced with Gemini insights."
        
        return enhanced_decision
    
    def _combine_with_mcp(self, base_decision: Dict[str, Any], mcp_insights: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine base decision with MCP insights"""
        
        if not mcp_insights:
            return base_decision
        
        enhanced_decision = base_decision.copy()
        
        # Adjust confidence based on MCP insights
        mcp_confidence = mcp_insights.get("confidence", 0.7)
        current_confidence = enhanced_decision.get("confidence", 0.7)
        enhanced_decision["confidence"] = (current_confidence + mcp_confidence) / 2
        
        # Add MCP recommendations
        mcp_recommendations = mcp_insights.get("recommendations", [])
        if mcp_recommendations:
            current_next_steps = enhanced_decision.get("next_steps", [])
            enhanced_decision["next_steps"] = current_next_steps + mcp_recommendations[:2]
        
        # Update reasoning
        enhanced_decision["reasoning"] = f"{base_decision.get('reasoning', '')} Informed by MCP analysis."
        
        return enhanced_decision
    
    async def _fallback_decision(
        self,
        session_data: Dict[str, Any],
        seller_message: str,
        chat_history: List[Dict[str, Any]],
        product: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback decision using traditional negotiation engine"""
        
        try:
            # Use the traditional negotiation engine
            decision = await self.negotiation_engine.process_negotiation_turn(
                session_data, seller_message, chat_history, product
            )
            
            # Generate dynamic context-aware fallback messages
            user_params = session_data.get("user_params", {})
            target_price = getattr(user_params, 'target_price', None) if hasattr(user_params, 'target_price') else user_params.get("target_price")
            
            # Analyze recent conversation for context
            recent_messages = chat_history[-3:] if chat_history else []
            conversation_context = ""
            for msg in recent_messages:
                if hasattr(msg, 'content'):
                    conversation_context += f"{msg.sender}: {msg.content} "
            
            # Generate contextual responses based on seller's message
            contextual_responses = []
            
            if "price" in seller_message.lower() or any(digit.isdigit() for digit in seller_message):
                # Seller mentioned price - respond to their offer
                contextual_responses = [
                    f"I appreciate your offer, but I was hoping we could find a middle ground closer to ₹{target_price:,}. What do you think?",
                    f"That's higher than I was expecting. I've seen similar items for around ₹{target_price:,}. Can we work something out?",
                    f"I understand your position, but based on market rates, ₹{target_price:,} seems more reasonable. Would that work for you?"
                ]
            elif "no" in seller_message.lower() or "can't" in seller_message.lower():
                # Seller is resistant - be more persuasive
                contextual_responses = [
                    f"I completely understand your concerns. Perhaps we can find a compromise? What if we settle at ₹{target_price:,}?",
                    f"I respect that, but I'm really interested in this item. Could we possibly meet at ₹{target_price:,}?",
                    f"Fair enough. Let me ask - what's the lowest you'd be comfortable with? I was thinking around ₹{target_price:,}."
                ]
            elif "okay" in seller_message.lower() or "yes" in seller_message.lower():
                # Seller seems agreeable - be positive but still negotiate
                contextual_responses = [
                    f"Great! I'm glad we're on the same page. How does ₹{target_price:,} sound to you?",
                    f"Excellent! I think ₹{target_price:,} would be fair for both of us. What do you say?",
                    f"Perfect! Based on what I've researched, ₹{target_price:,} seems like a win-win. Agreed?"
                ]
            else:
                # Default strategic messages
                contextual_responses = [
                    f"Thanks for getting back to me! I've been looking at similar products, and ₹{target_price:,} seems like a fair market price.",
                    f"I appreciate you considering my interest. Based on my research, ₹{target_price:,} would be a reasonable price for this.",
                    f"I'm really interested in this item. From what I've seen in the market, ₹{target_price:,} would be a good deal for both of us."
                ]
            
            import random
            fallback_message = random.choice(contextual_responses) if target_price else "I'm interested in this product. Can we discuss the price based on current market conditions?"
            
            return {
                "message": decision.get("message", fallback_message),
                "action_type": decision.get("action_type", "counter_offer"),
                "price_offer": decision.get("price_offer", target_price),
                "confidence": decision.get("confidence", 0.7),
                "reasoning": "Fallback negotiation engine",
                "tactics_used": ["traditional_negotiation"],
                "next_steps": ["await_seller_response"]
            }
            
        except Exception as e:
            logger.error(f"Fallback decision error: {e}")
            
            # Ultimate fallback
            return {
                "message": "I'm interested in this product. What's your best price?",
                "action_type": "question",
                "price_offer": None,
                "confidence": 0.5,
                "reasoning": "Emergency fallback response",
                "tactics_used": ["basic_inquiry"],
                "next_steps": ["await_seller_response"]
            }
    
    def _determine_phase(self, chat_history: List[Any], current_message: str) -> str:
        """Determine the current phase of negotiation"""
        
        if not chat_history:
            return "opening"
        
        message_count = len(chat_history)
        
        # Look for key phrases in recent messages
        recent_messages = [msg.content.lower() if hasattr(msg, 'content') else str(msg).lower() for msg in chat_history[-3:]]
        recent_messages.append(current_message.lower() if current_message else "")
        
        combined_recent = " ".join(recent_messages)
        
        if "final" in combined_recent or "last" in combined_recent:
            return "closing"
        elif "counter" in combined_recent or message_count > 3:
            return "bargaining"
        elif message_count <= 2:
            return "opening"
        else:
            return "negotiation"
    
    def _log_decision(self, decision: Dict[str, Any], session_data: Dict[str, Any]):
        """Log decision for learning and analytics"""
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_data.get("session_id"),
                "decision": decision,
                "context_summary": {
                    "user_id": session_data.get("user_id"),
                    "product_id": self._get_product_id_safely(session_data),
                    "negotiation_round": len(session_data.get("chat_history", []))
                }
            }
            
            # In production, this would go to a proper logging system
            logger.info(f"Decision logged: {log_entry}")
            
        except Exception as e:
            logger.error(f"Error logging decision: {e}")

    def _get_product_id_safely(self, session_data: Dict[str, Any]) -> Optional[str]:
        """Safely extract product ID from session data"""
        try:
            product = session_data.get("product")
            if hasattr(product, 'id'):
                return product.id
            elif isinstance(product, dict):
                return product.get("id")
            return None
        except Exception:
            return None

    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all AI services"""
        try:
            status = {
                "enhanced_ai_service": "active",
                "langchain_agent": "active" if self.use_langchain and self.langchain_agent else "disabled",
                "mcp_integration": "active" if self.use_mcp else "disabled", 
                "gemini_fallback": "active",
                "negotiation_engine": "active",
                "scraper_service": "active",
                "services": {
                    "langchain": {
                        "enabled": self.use_langchain,
                        "initialized": self.langchain_agent is not None,
                        "tools": ["market_analysis", "price_calculator", "negotiation_strategy"] if self.langchain_agent else []
                    },
                    "mcp": {
                        "enabled": self.use_mcp,
                        "initialized": self.mcp_context_manager is not None
                    },
                    "gemini": {
                        "enabled": True,
                        "initialized": self.gemini_service is not None
                    },
                    "negotiation_engine": {
                        "enabled": True,
                        "initialized": self.negotiation_engine is not None
                    }
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "enhanced_ai_service": "error",
                "error": str(e)
            }


# Helper function for backwards compatibility
async def get_ai_decision(session_data: Dict[str, Any], seller_message: str, chat_history: List[Dict[str, Any]], product: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to get AI decision"""
    service = EnhancedAIService()
    return await service.make_negotiation_decision(session_data, seller_message, chat_history, product)