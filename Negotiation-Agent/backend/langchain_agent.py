"""
LangChain Negotiation Agent
Advanced AI agent for intelligent negotiation using LangChain framework
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# LangChain imports
from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain.chains import LLMChain
from pydantic import BaseModel, Field

# Local imports
from models import NegotiationSession, ChatMessage

logger = logging.getLogger(__name__)

class NegotiationContext(BaseModel):
    """Context for negotiation decisions"""
    product: Dict[str, Any]
    target_price: int
    max_budget: int
    current_offer: Optional[int] = None
    seller_messages: List[str]
    chat_history: List[Dict[str, Any]]
    market_data: Dict[str, Any]
    session_data: Dict[str, Any]
    negotiation_phase: str

class MarketAnalysisTool(BaseTool):
    """Tool for analyzing market conditions"""
    name: str = "market_analysis"
    description: str = "Analyze market conditions and pricing for negotiation strategy"
    
    def _run(
        self, 
        product_name: str, 
        current_price: int,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Analyze market conditions"""
        try:
            # Simulate market analysis (you can integrate real market data here)
            analysis = {
                "market_trend": "stable",
                "suggested_price_range": {
                    "min": int(current_price * 0.7),
                    "max": int(current_price * 0.9)
                },
                "negotiation_leverage": "moderate",
                "competitive_prices": [
                    int(current_price * 0.8),
                    int(current_price * 0.85),
                    int(current_price * 0.9)
                ]
            }
            return json.dumps(analysis)
        except Exception as e:
            logger.error(f"Market analysis error: {e}")
            return "Market analysis unavailable"

class PriceCalculatorTool(BaseTool):
    """Tool for calculating optimal price offers"""
    name: str = "price_calculator"
    description: str = "Calculate optimal price offers based on negotiation strategy"
    
    def _run(
        self, 
        current_price: int, 
        target_price: int, 
        max_budget: int,
        negotiation_round: int,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Calculate optimal price offer"""
        try:
            # Progressive negotiation strategy
            if negotiation_round <= 2:
                # Start with aggressive offer
                offer = int(target_price * 1.1)
            elif negotiation_round <= 4:
                # Move towards middle ground
                offer = int((target_price + current_price) * 0.6)
            else:
                # Final offers closer to budget
                offer = int(min(max_budget * 0.95, (target_price + current_price) * 0.7))
            
            # Ensure offer is within bounds
            offer = max(target_price, min(offer, max_budget))
            
            result = {
                "suggested_offer": offer,
                "strategy": "progressive",
                "confidence": 0.8,
                "reasoning": f"Round {negotiation_round}: Strategic offer based on target ${target_price} and budget ${max_budget}"
            }
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Price calculation error: {e}")
            return "Price calculation failed"

class NegotiationStrategyTool(BaseTool):
    """Tool for determining negotiation strategy"""
    name: str = "negotiation_strategy"
    description: str = "Determine the best negotiation strategy and tactics to use"
    
    def _run(
        self, 
        seller_message: str,
        negotiation_phase: str,
        price_difference: int,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Determine negotiation strategy"""
        try:
            strategies = {
                "opening": ["anchoring", "information_gathering", "rapport_building"],
                "bargaining": ["reciprocal_concessions", "deadline_pressure", "alternative_options"],
                "closing": ["final_offer", "walk_away_threat", "compromise_seeking"]
            }
            
            # Analyze seller's tone and urgency
            seller_lower = seller_message.lower()
            urgency_indicators = ["final", "last", "deadline", "urgent", "today only"]
            flexibility_indicators = ["consider", "negotiate", "discuss", "flexible"]
            
            is_urgent = any(word in seller_lower for word in urgency_indicators)
            is_flexible = any(word in seller_lower for word in flexibility_indicators)
            
            # Determine strategy
            if price_difference > 30:  # Large gap
                strategy = "aggressive_negotiation"
                tactics = ["anchoring", "alternative_options", "market_comparison"]
            elif price_difference > 15:  # Moderate gap  
                strategy = "collaborative_negotiation"
                tactics = ["reciprocal_concessions", "value_proposition", "rapport_building"]
            else:  # Small gap
                strategy = "closing_negotiation"
                tactics = ["final_offer", "commitment_seeking", "minor_concessions"]
            
            # Adjust based on seller signals
            if is_urgent:
                tactics.append("deadline_leverage")
            if is_flexible:
                tactics.append("creative_solutions")
            
            result = {
                "strategy": strategy,
                "tactics": tactics,
                "seller_analysis": {
                    "urgency": is_urgent,
                    "flexibility": is_flexible
                },
                "recommended_approach": f"Use {strategy} with focus on {', '.join(tactics[:2])}"
            }
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Strategy analysis error: {e}")
            return "Strategy analysis failed"


class LangChainNegotiationAgent:
    """Advanced negotiation agent using LangChain"""
    
    def __init__(self, google_api_key: str = None):
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("Google API key is required for LangChain agent")
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=self.google_api_key,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize tools
        self.tools = [
            MarketAnalysisTool(),
            PriceCalculatorTool(),
            NegotiationStrategyTool()
        ]
        
        # Create negotiation prompt template
        self.negotiation_prompt = PromptTemplate(
            input_variables=[
                "product_name", "product_price", "target_price", "max_budget",
                "seller_message", "negotiation_phase", "conversation_flow", "price_mentions", 
                "seller_sentiment", "negotiation_stage", "seller_tactics", "market_data"
            ],
            template="""
You are an expert negotiation strategist helping a buyer negotiate the best deal. You must be strategic, methodical, and use market analysis to your advantage.

PRODUCT DETAILS:
- Product: {product_name}
- Listed Price: ₹{product_price}
- Target Price: ₹{target_price}
- Maximum Budget: ₹{max_budget}

CONVERSATION CONTEXT:
- Negotiation Phase: {negotiation_phase}
- Negotiation Stage: {negotiation_stage}
- Seller Sentiment: {seller_sentiment}
- Seller Tactics Detected: {seller_tactics}

- Full Conversation Flow:
{conversation_flow}

- Price-Related Discussions:
{price_mentions}

- Market Data: {market_data}

SELLER'S LATEST MESSAGE:
"{seller_message}"

CONTEXTUAL RESPONSE STRATEGY - Adapt based on seller behavior:

**SELLER SENTIMENT ANALYSIS**: {seller_sentiment}
- If RESISTANT: Use empathy, market data, alternatives, gentle pressure
- If AGREEABLE: Build on positivity, move closer to target price
- If OPEN: Test flexibility, provide compelling reasons, create urgency

**NEGOTIATION STAGE**: {negotiation_stage}  
- If OPENING: Establish rapport, anchor with target price, show serious interest
- If MIDDLE: Apply strategic pressure, use market comparisons, show flexibility
- If ADVANCED/CLOSING: Make final push, summarize value, create win-win scenario

**SELLER TACTICS DETECTED**: {seller_tactics}
- If "rejection": Counter with alternatives and market data
- If "acceptance": Confirm and close the deal
- If "counter_offer": Evaluate and respond strategically
- If "ultimatum": Test if it's real or negotiating tactic

**DYNAMIC RESPONSE RULES**:
1. NEVER use the same phrasing twice - always vary your language
2. Directly address what the seller just said - show you're listening
3. Adapt your tone to match the seller's energy level
4. Use different persuasion angles: logic, emotion, urgency, social proof
   - Vary your language and approach based on conversation history

4. **HUMAN-LIKE RESPONSE CRAFTING**:
   - Sound conversational and natural, not robotic
   - Reference specific points from the seller's message
   - Show emotional intelligence and adaptability
   - Use varied vocabulary and sentence structures
   - Include personal touches (but stay professional)

IMPORTANT: Your final answer must be ONLY the JSON response, nothing else. Do not include any explanatory text before or after the JSON.

RESPONSE FORMAT (return exactly this JSON structure as your final answer):
{{
    "message": "Your strategic response with specific reasoning and market-based arguments",
    "action_type": "offer|counter_offer|accept|reject|question|final_offer",
    "price_offer": price_amount_or_null,
    "confidence": confidence_score_0_to_1,
    "reasoning": "Step-by-step strategic analysis of your approach",
    "tactics_used": ["list", "of", "tactics"],
    "next_steps": ["recommended", "next", "steps"]
}}

Generate a strategic negotiation response (respond with JSON only):
"""
        )
        
        # Initialize agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
        
        logger.info("LangChain negotiation agent initialized successfully")
    
    async def generate_negotiation_response(
        self, 
        context: NegotiationContext
    ) -> Dict[str, Any]:
        """Generate intelligent negotiation response using LangChain with keyword fallback"""
        try:
            # First try to get a proper negotiation response using keyword-based system
            if context.seller_messages:
                keyword_response = self._get_keyword_based_response(context)
                if keyword_response and keyword_response.get("confidence", 0) >= 0.7:
                    logger.info("Using keyword-based response for reliable negotiation")
                    return keyword_response
            
            # Prepare input for the agent with dynamic conversation context
            recent_messages = context.chat_history[-6:] if context.chat_history else []
            conversation_flow = []
            
            for msg in recent_messages:
                if hasattr(msg, 'sender') and hasattr(msg, 'content'):
                    conversation_flow.append(f"{msg.sender}: {msg.content}")
                elif isinstance(msg, dict):
                    conversation_flow.append(f"{msg.get('sender', 'unknown')}: {msg.get('content', '')}")
            
            conversation_context = "\n".join(conversation_flow) if conversation_flow else "No previous conversation"
            
            # Analyze conversation context for better responses
            price_mentions = []
            seller_sentiment = "neutral"
            negotiation_stage = "initial"
            seller_tactics = []
            
            for i, msg in enumerate(conversation_flow):
                # Extract price mentions
                if any(price_word in msg.lower() for price_word in ['₹', 'rupees', 'price', 'cost', 'budget']):
                    price_mentions.append(msg)
                
                # Analyze seller behavior if it's a seller message
                if msg.startswith("Seller:"):
                    content_lower = msg.lower()
                    
                    # Determine seller sentiment
                    if any(word in content_lower for word in ["no", "can't", "impossible", "too low", "minimum", "sorry"]):
                        seller_sentiment = "resistant"
                        seller_tactics.append("rejection")
                    elif any(word in content_lower for word in ["okay", "yes", "agreed", "fine", "deal", "accept"]):
                        seller_sentiment = "agreeable"
                        seller_tactics.append("acceptance")
                    elif any(word in content_lower for word in ["maybe", "consider", "think", "possible", "let me"]):
                        seller_sentiment = "open"
                        seller_tactics.append("consideration")
                    elif any(word in content_lower for word in ["final", "last", "best", "lowest"]):
                        seller_tactics.append("ultimatum")
                        negotiation_stage = "closing"
                    elif any(word in content_lower for word in ["counter", "what about", "how about"]):
                        seller_tactics.append("counter_offer")
            
            # Determine negotiation stage based on message count
            seller_message_count = len([msg for msg in conversation_flow if msg.startswith("Seller:")])
            if seller_message_count == 1:
                negotiation_stage = "opening"
            elif seller_message_count > 3:
                negotiation_stage = "advanced"
            else:
                negotiation_stage = "middle"
            
            agent_input = {
                "product_name": context.product.get("name", "Unknown Product"),
                "product_price": context.product.get("price", 0),
                "target_price": context.target_price,
                "max_budget": context.max_budget,
                "seller_message": context.seller_messages[-1] if context.seller_messages else "",
                "negotiation_phase": context.negotiation_phase,
                "conversation_flow": conversation_context,
                "price_mentions": "\n".join(price_mentions) if price_mentions else "No price discussions yet",
                "seller_sentiment": seller_sentiment,
                "negotiation_stage": negotiation_stage,
                "seller_tactics": ", ".join(seller_tactics) if seller_tactics else "none detected",
                "market_data": json.dumps(context.market_data)
            }
            
            # Format the prompt
            formatted_prompt = self.negotiation_prompt.format(**agent_input)
            
            # Run the agent
            response = await self._run_agent_async(formatted_prompt)
            
            # Parse response
            parsed_response = self._parse_agent_response(response)
            
            # Add metadata
            parsed_response["source"] = "langchain_agent"
            parsed_response["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"LangChain agent generated response: {parsed_response.get('action_type', 'unknown')}")
            return parsed_response
            
        except Exception as e:
            logger.error(f"LangChain agent error: {e}")
            # Use keyword-based fallback instead of generic response
            fallback_response = self._get_keyword_based_response(context)
            if fallback_response:
                fallback_response["source"] = "langchain_agent_keyword_fallback"
                fallback_response["reasoning"] = f"Agent error, using keyword fallback: {str(e)}"
                return fallback_response
            
            # Final fallback if keyword system also fails
            return {
                "message": "I'm interested in this item and believe we can reach a fair agreement. What are your thoughts on my offer?",
                "action_type": "respond",
                "price_offer": context.target_price,
                "confidence": 0.6,
                "reasoning": f"Agent error, using basic fallback: {str(e)}",
                "tactics_used": ["collaborative_approach"],
                "next_steps": ["await_seller_response"],
                "source": "langchain_agent_fallback"
            }
    
    async def _run_agent_async(self, prompt: str) -> str:
        """Run agent asynchronously"""
        try:
            # Use the agent with the formatted prompt
            response = self.agent.run(prompt)
            logger.info(f"Agent raw response: {response[:200]}...")
            return response
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            # Return a valid JSON fallback
            fallback_response = {
                "message": "I need to review this further. Let me consider the best approach.",
                "action_type": "question",
                "price_offer": None,
                "confidence": 0.5,
                "reasoning": f"Agent error: {str(e)}",
                "tactics_used": ["fallback"],
                "next_steps": ["retry_with_fallback"]
            }
            return json.dumps(fallback_response)
    
    def _parse_agent_response(self, response: str) -> Dict[str, Any]:
        """Parse agent response into structured format"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["message", "action_type", "confidence", "reasoning"]
                for field in required_fields:
                    if field not in parsed:
                        parsed[field] = self._get_default_value(field)
                
                return parsed
            else:
                # Fallback parsing
                return self._create_fallback_response(response)
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, using fallback")
            return self._create_fallback_response(response)
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            "message": "I'm interested in moving forward with this negotiation. Let me know your thoughts on my offer.",
            "action_type": "respond",
            "price_offer": None,
            "confidence": 0.75,
            "reasoning": "Default response due to parsing issue",
            "tactics_used": ["analytical"],
            "next_steps": ["continue_negotiation"]
        }
        return defaults.get(field, "")
    
    def _create_fallback_response(self, raw_response: str) -> Dict[str, Any]:
        """Create fallback response from raw text"""
        # Avoid returning generic or unhelpful responses
        if len(raw_response) < 20 or "review" in raw_response.lower() or "consider" in raw_response.lower():
            return {
                "message": "I'm interested in reaching a fair agreement. Let me know your thoughts on my offer and we can work together.",
                "action_type": "respond",
                "price_offer": None,
                "confidence": 0.75,
                "reasoning": "Generated helpful fallback instead of generic response",
                "tactics_used": ["collaborative_approach"],
                "next_steps": ["await_seller_response"]
            }
        
        return {
            "message": raw_response[:500] if len(raw_response) > 500 else raw_response,
            "action_type": "respond",
            "price_offer": None,
            "confidence": 0.75,
            "reasoning": "Parsed from unstructured response",
            "tactics_used": ["analytical"],
            "next_steps": ["await_seller_response"]
        }
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
        logger.info("Agent memory cleared")
    
    def get_memory_summary(self) -> str:
        """Get summary of conversation memory"""
        try:
            messages = self.memory.chat_memory.messages
            return f"Memory contains {len(messages)} messages"
        except:
            return "Memory summary unavailable"
    
    def _get_keyword_based_response(self, context: NegotiationContext) -> Optional[Dict[str, Any]]:
        """Generate keyword-based response as fallback for LangChain agent"""
        try:
            if not context.seller_messages:
                return None
            
            latest_message = context.seller_messages[-1].lower()
            target_price = context.target_price
            product_name = context.product.get("title", "this item")
            
            # Determine approach (default to diplomatic for LangChain)
            approach = "diplomatic"
            
            # Enhanced keyword detection with more comprehensive responses
            keyword_responses = {
                # Price is too low keywords
                'price_low_keywords': ['low', 'too low', 'very low', 'not enough', 'insufficient', 'can\'t accept', 'won\'t work', 'minimum', 'higher'],
                'price_low_responses': {
                    "assertive": [
                        f"I understand your position, but ₹{target_price:,} is based on thorough market research. Let me increase to ₹{int(target_price * 1.1):,} as my best offer.",
                        f"I've analyzed comparable items and ₹{target_price:,} is competitive. I can stretch to ₹{int(target_price * 1.1):,} maximum.",
                        f"My research shows ₹{target_price:,} is fair market value. How about ₹{int(target_price * 1.1):,} as a compromise?"
                    ],
                    "diplomatic": [
                        f"I appreciate your perspective. I've researched similar {product_name} listings and ₹{target_price:,} seems reasonable. Could we perhaps meet at ₹{int(target_price * 1.1):,}?",
                        f"I understand your concern about the price. Based on market analysis, would ₹{int(target_price * 1.1):,} be more acceptable? I believe it's fair for both of us.",
                        f"Let's find a middle ground that works for both of us. I can go up to ₹{int(target_price * 1.1):,} - would this help bridge the gap?"
                    ],
                    "considerate": [
                        f"I really appreciate you considering my offer. I've done my research and ₹{int(target_price * 1.1):,} would really help my budget situation.",
                        f"I hope we can work something out. ₹{int(target_price * 1.1):,} would be perfect for me and I hope it works for you too.",
                        f"I understand it might seem low. ₹{int(target_price * 1.1):,} is really stretching my budget but I'd love to make this work."
                    ]
                },
                
                # Seller is okay/agreeable keywords
                'agreeable_keywords': ['ok', 'okay', 'fine', 'alright', 'sounds good', 'agreed', 'deal', 'accept', 'yes', 'sure'],
                'agreeable_responses': {
                    "assertive": [
                        "Excellent! I'm ready to finalize this deal immediately. How should we proceed with payment and pickup?",
                        "Perfect! Let's close this deal. I can arrange payment today - what's your preferred method?",
                        "Great decision! I'm prepared to complete the transaction right away. When can we arrange pickup?"
                    ],
                    "diplomatic": [
                        "Wonderful! I'm glad we could reach a mutually beneficial agreement. How would you like to handle the next steps?",
                        "That's fantastic! Thank you for being flexible and working with me. Shall we discuss pickup and payment details?",
                        "Excellent! I appreciate your cooperation in reaching this agreement. What's the best way to proceed?"
                    ],
                    "considerate": [
                        "Thank you so much! This really means a lot to me. I'm very grateful we could work this out. How should we arrange pickup?",
                        "I'm so happy we found a solution! Thank you for your understanding. When would be convenient for you to complete this?",
                        "Thank you for being so accommodating! I really appreciate your flexibility. How can we finalize everything?"
                    ]
                },
                
                # Negotiation/counter-offer keywords
                'negotiation_keywords': ['counter', 'negotiate', 'how about', 'what about', 'consider', 'think about', 'discuss', 'maybe'],
                'negotiation_responses': {
                    "assertive": [
                        f"I'm open to discussion. Based on market data, ₹{target_price:,} to ₹{int(target_price * 1.15):,} is where I need to be. What specific price did you have in mind?",
                        f"Let's talk numbers. My analysis shows ₹{target_price:,} is competitive, but I have some flexibility up to ₹{int(target_price * 1.15):,}.",
                        f"I appreciate the negotiation. Given market conditions, I can work within ₹{target_price:,} to ₹{int(target_price * 1.15):,} range."
                    ],
                    "diplomatic": [
                        f"Absolutely! I'm always open to finding a solution that benefits both parties. I'm thinking around ₹{target_price:,} to ₹{int(target_price * 1.15):,} - what are your thoughts?",
                        f"I'd love to work together on this. Could we explore the ₹{target_price:,} to ₹{int(target_price * 1.15):,} range? I believe that's fair for both of us.",
                        f"That's the spirit! Let's find common ground. I'm comfortable in the ₹{target_price:,} to ₹{int(target_price * 1.15):,} range - does that work?"
                    ],
                    "considerate": [
                        f"I really appreciate your willingness to negotiate. ₹{target_price:,} to ₹{int(target_price * 1.15):,} would be perfect for my situation.",
                        f"Thank you for being open to discussion. I hope we can find something around ₹{target_price:,} to ₹{int(target_price * 1.15):,} that works for both of us.",
                        f"I'm grateful for your flexibility. ₹{target_price:,} to ₹{int(target_price * 1.15):,} would really help me stay within my budget."
                    ]
                },
                
                # High price/expensive keywords
                'expensive_keywords': ['expensive', 'high', 'too much', 'costly', 'pricey', 'beyond budget', 'afford'],
                'expensive_responses': {
                    "assertive": [
                        f"I understand price is a concern. Based on market analysis, ₹{target_price:,} actually represents good value compared to similar listings.",
                        f"Let me provide perspective - at ₹{target_price:,}, this is below the average market price I've researched for {product_name}.",
                        f"I've done extensive price comparison and ₹{target_price:,} is competitive. I can show you similar listings if helpful."
                    ],
                    "diplomatic": [
                        f"I completely understand budget concerns. Could we look at ₹{target_price:,} as a fair middle ground that offers value for both of us?",
                        f"Price is important to me too. I believe ₹{target_price:,} strikes the right balance between fair value and affordability.",
                        f"Let's work together on this. ₹{target_price:,} would be reasonable given the current market - what do you think?"
                    ],
                    "considerate": [
                        f"I completely share your concern about prices these days. ₹{target_price:,} is really stretching my budget too, but I think it's fair.",
                        f"I understand the cost concern - that's exactly why I'm hoping ₹{target_price:,} could work for both of us.",
                        f"Budget is definitely important to me too. ₹{target_price:,} would really help me afford this while being fair to you."
                    ]
                },
                
                # Urgent/quick sale keywords
                'urgency_keywords': ['urgent', 'quick', 'asap', 'immediately', 'today', 'now', 'fast', 'hurry'],
                'urgency_responses': {
                    "assertive": [
                        f"Perfect timing! I can make an immediate decision at ₹{target_price:,} and complete the transaction today.",
                        f"I appreciate the urgency. ₹{target_price:,} and I can finalize everything within the hour - cash ready.",
                        f"Excellent! For ₹{target_price:,}, I'm prepared to close this deal right now. When can I pick up?"
                    ],
                    "diplomatic": [
                        f"I understand you need a quick sale. Would ₹{target_price:,} work for an immediate transaction? I can arrange everything today.",
                        f"If timing is important to you, I'm ready to proceed quickly at ₹{target_price:,}. We can finalize everything immediately.",
                        f"I can definitely help with your timeline. ₹{target_price:,} for a same-day completion - would this work?"
                    ],
                    "considerate": [
                        f"I'd love to help with your urgent sale! ₹{target_price:,} and I can be your immediate buyer if that helps your situation.",
                        f"I understand the urgency and would be happy to help. ₹{target_price:,} would allow me to decide and pay today.",
                        f"I can be your quick solution! ₹{target_price:,} and immediate pickup if that helps with your timing needs."
                    ]
                }
            }
            
            # Check for keyword matches and return appropriate response
            import random
            for category in ['price_low', 'agreeable', 'negotiation', 'expensive', 'urgency']:
                keywords = keyword_responses[f'{category}_keywords']
                if any(keyword in latest_message for keyword in keywords):
                    responses = keyword_responses[f'{category}_responses'][approach]
                    selected_response = random.choice(responses)
                    
                    # Determine action type and price offer based on category
                    if category == 'price_low':
                        action_type = "counter_offer"
                        price_offer = int(target_price * 1.1)
                    elif category == 'agreeable':
                        action_type = "accept"
                        price_offer = target_price
                    elif category == 'negotiation':
                        action_type = "counter_offer" 
                        price_offer = int(target_price * 1.1)
                    elif category == 'expensive':
                        action_type = "offer"
                        price_offer = target_price
                    elif category == 'urgency':
                        action_type = "offer"
                        price_offer = target_price
                    else:
                        action_type = "respond"
                        price_offer = None
                    
                    return {
                        "message": selected_response,
                        "action_type": action_type,
                        "price_offer": price_offer,
                        "confidence": 0.85,
                        "reasoning": f"Keyword-based response for '{category}' category detected in seller message",
                        "tactics_used": [f"keyword_{category}", "market_analysis", "strategic_pricing"],
                        "next_steps": ["await_seller_response", "prepare_next_move"],
                        "seller_analysis": {
                            "detected_sentiment": category,
                            "keywords_matched": [kw for kw in keywords if kw in latest_message]
                        }
                    }
            
            # Default greeting and general responses
            if any(greeting in latest_message for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'available']):
                greeting_responses = {
                    "diplomatic": [
                        f"Hello! I'm very interested in your {product_name}. Based on my research, ₹{target_price:,} would be a fair price. What do you think?",
                        f"Hi there! Your {product_name} looks perfect for my needs. Could we discuss ₹{target_price:,} as a starting point?",
                        f"Good to hear from you! I'm definitely interested. Would ₹{target_price:,} work as an initial offer?"
                    ]
                }
                
                return {
                    "message": random.choice(greeting_responses[approach]),
                    "action_type": "offer",
                    "price_offer": target_price,
                    "confidence": 0.8,
                    "reasoning": "Initial greeting response with market-based offer",
                    "tactics_used": ["rapport_building", "anchoring", "market_positioning"],
                    "next_steps": ["establish_interest", "gauge_flexibility"]
                }
            
            # Default response for unmatched messages
            default_responses = {
                "diplomatic": [
                    f"I'm interested in finding a solution that works for both of us. Based on market research, ₹{target_price:,} seems reasonable.",
                    f"Let me know your thoughts on ₹{target_price:,}. I believe it's a fair price given current market conditions.",
                    f"I'd like to move forward with this purchase. Could ₹{target_price:,} work for you?"
                ]
            }
            
            return {
                "message": random.choice(default_responses[approach]),
                "action_type": "offer",
                "price_offer": target_price,
                "confidence": 0.75,
                "reasoning": "Default market-based response when no specific keywords detected",
                "tactics_used": ["market_analysis", "collaborative_approach"],
                "next_steps": ["await_response", "analyze_seller_feedback"]
            }
            
        except Exception as e:
            logger.error(f"Keyword-based response error: {e}")
            return None