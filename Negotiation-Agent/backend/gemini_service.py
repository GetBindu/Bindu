"""
ENHANCED KEYWORD-BASED STATIC RESPONSE SYSTEM

This module implements a sophisticated keyword-based static response system for negotiations.
When Gemini API is unavailable or fails, the system uses intelligent keyword detection to 
generate dynamic, context-aware responses.

KEYWORD CATEGORIES AND RESPONSES:
1. PRICE_LOW_KEYWORDS: ['low', 'too low', 'very low', 'not enough', 'insufficient', 'can\'t accept', 'won\'t work']
   - Responses: Market-based justifications, slight price increases, persistence

2. AGREEABLE_KEYWORDS: ['ok', 'okay', 'fine', 'alright', 'sounds good', 'agreed', 'deal', 'accept', 'yes'] 
   - Responses: Deal closure, logistics coordination, contact exchange

3. NEGOTIATION_KEYWORDS: ['counter', 'negotiate', 'how about', 'what about', 'consider', 'think about']
   - Responses: Open to discussion while maintaining target price

4. EXPENSIVE_KEYWORDS: ['expensive', 'high', 'too much', 'costly', 'pricey', 'beyond budget']
   - Responses: Value justification, market comparisons, finding middle ground

5. URGENCY_KEYWORDS: ['urgent', 'quick', 'asap', 'immediately', 'today', 'now', 'fast']
   - Responses: Quick decision offers, immediate purchase readiness

6. GREETING_KEYWORDS: ['hi', 'hello', 'hey', 'good morning', 'good afternoon']
   - Responses: Professional introductions with immediate price offers

NEGOTIATION APPROACHES:
- ASSERTIVE: Direct, confident, market-research backed responses
- DIPLOMATIC: Balanced, collaborative, solution-focused responses  
- CONSIDERATE: Polite, budget-conscious, appreciation-focused responses

Each response is dynamically selected based on:
- Seller's keywords
- Negotiation approach preference
- Target price and budget constraints
- Product information
- Conversation context
"""

import google.generativeai as genai
import os
import random
from typing import List, Optional, Dict, Any
from models import ChatMessage, Product, NegotiationApproach
from negotiation_engine import NegotiationTactic, NegotiationPhase
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class GeminiOnlyService:
    """Gemini-only AI service for negotiation responses"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("WARNING: GEMINI_API_KEY not configured. Using fallback responses only.")
            self.model = None
        else:
            self.setup_client()
        
    def setup_client(self):
        """Setup Gemini AI client"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("INFO: Gemini AI service initialized successfully")
        except Exception as e:
            logger.error(f"ERROR: Failed to initialize Gemini AI: {e}")
            self.model = None
    
    async def generate_strategic_response(
        self,
        session_data: Dict[str, Any],
        seller_message: str,
        tactics: List[NegotiationTactic],
        decision: Dict[str, Any],
        product: Product
    ) -> str:
        """Generate strategic response using advanced context and tactics"""
        
        if not self.model:
            return self._get_enhanced_fallback_response(session_data, seller_message, tactics, decision, product)
        
        try:
            # Build enhanced context for AI
            context = self._build_strategic_context(
                session_data, seller_message, tactics, decision, product
            )
            
            # Generate response using Gemini
            response = await self._call_gemini_api(context)
            return response
            
        except Exception as e:
            logger.error(f"Error generating strategic AI response: {e}")
            return self._get_enhanced_fallback_response(session_data, seller_message, tactics, decision, product)
    
    async def generate_response(
        self,
        approach,  # Can be string or NegotiationApproach enum
        target_price: int,
        max_budget: int,
        chat_history: List[ChatMessage],
        product: Product
    ) -> str:
        """Legacy method for backward compatibility"""
        
        # Convert string to enum if needed
        if isinstance(approach, str):
            try:
                approach = NegotiationApproach(approach.lower())
            except ValueError:
                approach = NegotiationApproach.DIPLOMATIC  # Default fallback
        
        if not self.model:
            return self._get_fallback_response(approach, target_price, chat_history, product)
        
        try:
            # Build context for AI
            context = self._build_negotiation_context(
                approach, target_price, max_budget, chat_history, product
            )
            
            # Generate response using Gemini
            response = await self._call_gemini_api(context)
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._get_fallback_response(approach, target_price, chat_history, product)
    
    def _build_negotiation_context(
        self,
        approach: NegotiationApproach,
        target_price: int,
        max_budget: int,
        chat_history: List[ChatMessage],
        product: Product
    ) -> str:
        """Build context prompt for Gemini AI"""
        
        # Get the latest seller message
        seller_messages = [msg for msg in chat_history if msg.sender == "seller"]
        last_seller_message = seller_messages[-1].content if seller_messages else ""
        
        # Build conversation history
        conversation_history = ""
        for msg in chat_history[-6:]:  # Last 6 messages for context
            sender_label = "Seller" if msg.sender == "seller" else "You (Buyer)"
            conversation_history += f"{sender_label}: {msg.content}\n"
        
        # Define approach strategies
        approach_strategies = {
            NegotiationApproach.ASSERTIVE: {
                "style": "direct and confident",
                "tactics": "Make firm offers, emphasize market research, be persistent but polite",
                "personality": "business-like and decisive"
            },
            NegotiationApproach.DIPLOMATIC: {
                "style": "balanced and respectful",
                "tactics": "Find mutual benefits, acknowledge seller's position, propose win-win solutions",
                "personality": "professional and understanding"
            },
            NegotiationApproach.CONSIDERATE: {
                "style": "empathetic and budget-conscious",
                "tactics": "Explain budget constraints, show genuine interest, be patient",
                "personality": "humble and appreciative"
            }
        }
        
        strategy = approach_strategies.get(approach, approach_strategies[NegotiationApproach.DIPLOMATIC])
        
        prompt = f"""
You are an AI negotiation agent representing a buyer who wants to purchase: {product.title}

PRODUCT DETAILS:
- Current asking price: ₹{product.price:,}
- Your target price: ₹{target_price:,}
- Your maximum budget: ₹{max_budget:,}
- Product condition: {product.condition}
- Seller: {product.seller_name}
- Location: {product.location}

NEGOTIATION APPROACH: {approach.value.upper() if hasattr(approach, 'value') else str(approach).upper()}
- Style: {strategy["style"]}
- Tactics: {strategy["tactics"]}
- Personality: {strategy["personality"]}

CONVERSATION HISTORY:
{conversation_history}

LATEST SELLER MESSAGE: "{last_seller_message}"

INSTRUCTIONS:
1. Respond as a human buyer (never mention you're an AI)
2. Use the {approach.value if hasattr(approach, 'value') else str(approach)} negotiation approach consistently
3. Stay within your budget constraints (max ₹{max_budget:,})
4. Work towards your target price of ₹{target_price:,}
5. Keep responses conversational and natural (50-80 words)
6. Include relevant details about pickup/payment when appropriate
7. Be respectful but persistent in negotiations
8. If the seller's price is too high, explain your position clearly
9. If a good deal is reached, move towards closing (exchange contact details)

CURRENT SITUATION ANALYSIS:
- Current offer/price being discussed: Look at the conversation
- Progress towards target: Calculate if you're getting closer
- Seller's flexibility: Assess from their responses

Generate your next response as the buyer:
"""
        
        return prompt
    
    def _build_strategic_context(
        self,
        session_data: Dict[str, Any],
        seller_message: str,
        tactics: List[NegotiationTactic],
        decision: Dict[str, Any],
        product: Product
    ) -> str:
        """Build enhanced strategic context for Gemini AI with advanced tactics"""
        
        session = session_data['session']
        strategy = session_data.get('strategy', {})
        market_analysis = session_data.get('market_analysis', {})
        performance_metrics = session_data.get('performance_metrics', {})
        
        # Get conversation history
        conversation_history = ""
        for msg in session.messages[-8:]:  # Last 8 messages for context
            sender_label = "Seller" if msg.sender == "seller" else "You (Buyer)"
            conversation_history += f"{sender_label}: {msg.content}\n"
        
        # Build tactics description
        tactics_description = self._build_tactics_description(tactics)
        
        # Market intelligence context
        market_context = ""
        if market_analysis:
            avg_price = market_analysis.get('average_price')
            price_range = market_analysis.get('price_range', {})
            if avg_price:
                market_context = f"""
MARKET INTELLIGENCE:
- Average market price: ₹{avg_price:,}
- Price range: ₹{price_range.get('min', 0):,} - ₹{price_range.get('max', 0):,}
- Market trend: {market_analysis.get('market_trend', 'stable')}
- Similar listings: {market_analysis.get('similar_listings_count', 0)}
"""
        
        # Performance context
        performance_context = ""
        if performance_metrics:
            messages_sent = performance_metrics.get('messages_sent', 0)
            effectiveness = performance_metrics.get('negotiation_effectiveness', 0)
            performance_context = f"""
NEGOTIATION PROGRESS:
- Messages exchanged: {messages_sent}
- Negotiation effectiveness: {effectiveness:.1%}
- Time to first response: {performance_metrics.get('time_to_first_response', 'N/A')}
"""
        
        # Decision context
        decision_context = f"""
CURRENT DECISION: {decision.get('action', 'continue')}
- Confidence level: {decision.get('confidence', 0.5):.1%}
- Reasoning: {decision.get('reasoning', 'Continue negotiation')}
"""
        
        if 'offer' in decision:
            decision_context += f"- Recommended offer: ₹{decision['offer']:,}\n"
        
        prompt = f"""
You are an advanced AI negotiation agent representing a buyer for: {product.title}

PRODUCT DETAILS:
- Current asking price: ₹{product.price:,}
- Your target price: ₹{session.user_params.target_price:,}
- Your maximum budget: ₹{session.user_params.max_budget:,}
- Product condition: {product.condition}
- Seller: {product.seller_name}
- Location: {product.location}
- Platform: {product.platform}

NEGOTIATION APPROACH: {session.user_params.approach.value.upper() if hasattr(session.user_params.approach, 'value') else str(session.user_params.approach).upper()}
{market_context}
{performance_context}
{decision_context}

CONVERSATION HISTORY:
{conversation_history}

LATEST SELLER MESSAGE: "{seller_message}"

STRATEGIC TACTICS TO USE:
{tactics_description}

ADVANCED INSTRUCTIONS:
1. You are a sophisticated AI agent (never mention being AI to seller)
2. Use the specified tactics naturally in your response
3. Follow the decision guidance while maintaining conversational flow
4. Incorporate market intelligence to support your position
5. Keep responses human-like and conversational (60-100 words)
6. Show empathy while being strategic
7. Use specific numbers and facts to build credibility
8. Maintain the negotiation approach consistently
9. If price is discussed, use market data to justify your position
10. Always work towards your target price while respecting maximum budget

CURRENT NEGOTIATION PHASE: {session_data.get('phase', NegotiationPhase.EXPLORATION).value if hasattr(session_data.get('phase', NegotiationPhase.EXPLORATION), 'value') else str(session_data.get('phase', 'exploration'))}

Generate your strategic response as the buyer:
"""
        
        return prompt
    
    def _build_tactics_description(self, tactics: List[NegotiationTactic]) -> str:
        """Build description of tactics to use"""
        
        tactic_descriptions = {
            NegotiationTactic.ANCHORING: "Anchor with market research and comparable prices",
            NegotiationTactic.SCARCITY: "Mention time constraints or alternative options",
            NegotiationTactic.BUNDLING: "Request additional value (accessories, delivery, warranty)",
            NegotiationTactic.RECIPROCITY: "Show appreciation for seller's flexibility and respond in kind",
            NegotiationTactic.SOCIAL_PROOF: "Reference what others are paying for similar items",
            NegotiationTactic.URGENCY: "Express time sensitivity or immediate purchase capability",
            NegotiationTactic.AUTHORITY: "Reference expert advice or professional recommendations",
            NegotiationTactic.COMMITMENT: "Show readiness to close the deal immediately"
        }
        
        if not tactics:
            return "No specific tactics - focus on natural conversation and relationship building"
        
        descriptions = []
        for tactic in tactics:
            desc = tactic_descriptions.get(tactic, f"Use {tactic.value} approach")
            descriptions.append(f"- {desc}")
        
        return "\n".join(descriptions)
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API asynchronously"""
        try:
            # Run the synchronous Gemini call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            raise
    
    def _get_fallback_response(
        self, 
        approach,  # Can be string or NegotiationApproach enum
        target_price: int, 
        chat_history: List[ChatMessage],
        product: Product
    ) -> str:
        """Enhanced fallback responses using keyword-based static responses"""
        
        # Convert string to enum if needed
        if isinstance(approach, str):
            try:
                approach = NegotiationApproach(approach.lower())
            except ValueError:
                approach = NegotiationApproach.DIPLOMATIC  # Default fallback
        
        # Get last seller message
        seller_messages = [msg for msg in chat_history if msg.sender == "seller"]
        
        if not seller_messages:
            # Opening message
            if approach == NegotiationApproach.ASSERTIVE:
                return f"Hello {product.seller_name}! I'm interested in your listing. Based on current market rates, I'd like to offer ₹{target_price:,}. Is this acceptable?"
            elif approach == NegotiationApproach.DIPLOMATIC:
                return f"Good day {product.seller_name}! I'm very interested in your product. Would you consider an offer of ₹{target_price:,}? I believe it's a fair price given the current market."
            else:  # CONSIDERATE
                return f"Hi {product.seller_name}! I'm really interested in your listing. My budget is a bit tight at ₹{target_price:,}. Would this work for you?"
        
        # Use enhanced keyword-based response system
        last_seller_message = seller_messages[-1].content
        return self._get_keyword_based_response_simple(last_seller_message, approach, target_price, product)
    
    def _get_keyword_based_response_simple(
        self, 
        seller_message: str, 
        approach: NegotiationApproach, 
        target_price: int, 
        product: Product
    ) -> str:
        """Simplified keyword-based response system for fallback responses"""
        
        message_lower = seller_message.lower()
        
        # Define keyword-based response mappings (simplified version)
        keyword_responses = {
            # Price is too low keywords
            'price_low_keywords': ['low', 'too low', 'very low', 'not enough', 'insufficient', 'can\'t accept', 'won\'t work', 'no', 'cannot', 'firm', 'minimum'],
            'price_low_responses': {
                NegotiationApproach.ASSERTIVE: [
                    f"I understand, but ₹{target_price:,} is based on market research. Let me stretch to ₹{int(target_price * 1.1):,} maximum.",
                    f"Based on similar listings, ₹{target_price:,} is competitive. I can go up to ₹{int(target_price * 1.1):,} if needed.",
                    f"Market data supports ₹{target_price:,}. My absolute maximum would be ₹{int(target_price * 1.1):,}."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"I appreciate your position. Could we perhaps meet at ₹{int(target_price * 1.1):,}? That would work for both of us.",
                    f"Let's find middle ground. Would ₹{int(target_price * 1.1):,} be more acceptable?",
                    f"I understand your concern. Could ₹{int(target_price * 1.1):,} bridge the gap between us?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"I really want this item. Could you please consider ₹{int(target_price * 1.1):,}? It would mean a lot to me.",
                    f"I understand it might seem low. ₹{int(target_price * 1.1):,} is really stretching my budget.",
                    f"Please help me out. ₹{int(target_price * 1.1):,} would be perfect if you could consider it."
                ]
            },
            
            # Seller is okay/agreeable keywords
            'agreeable_keywords': ['ok', 'okay', 'fine', 'alright', 'sounds good', 'agreed', 'deal', 'accept', 'yes'],
            'agreeable_responses': {
                NegotiationApproach.ASSERTIVE: [
                    "Excellent! Let's finalize this deal. When can we arrange pickup?",
                    "Perfect! I'm ready to proceed. How should we handle payment?",
                    "Great decision! Let's exchange contact details and complete this transaction."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    "Wonderful! I'm glad we could reach an agreement. How would you like to proceed?",
                    "That's fantastic! Thank you for being flexible. What's the next step?",
                    "Excellent! I appreciate your cooperation. Shall we arrange the pickup details?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    "Thank you so much! This really means a lot to me. How can we arrange the pickup?",
                    "I'm so grateful we could work this out! When would be convenient for you?",
                    "Thank you for understanding! I really appreciate your flexibility."
                ]
            },
            
            # Greeting keywords
            'greeting_keywords': ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'available'],
            'greeting_responses': {
                NegotiationApproach.ASSERTIVE: [
                    f"Hello {product.seller_name}! Yes, I'm very interested. I can offer ₹{target_price:,} for immediate purchase.",
                    f"Hi there! I'm interested in your {product.title}. ₹{target_price:,} would work for me."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"Hello {product.seller_name}! Yes, I'm interested in your listing. Would ₹{target_price:,} work for you?",
                    f"Hi! Your {product.title} looks great. Could we discuss ₹{target_price:,}?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"Hello {product.seller_name}! Yes, I'm interested. I hope ₹{target_price:,} might work?",
                    f"Hi! I really love your {product.title}. Could ₹{target_price:,} be possible?"
                ]
            },
            
            # Price discussion keywords
            'price_keywords': ['price', 'cost', 'amount', 'offer', 'budget'],
            'price_responses': {
                NegotiationApproach.ASSERTIVE: [
                    f"Based on market research, ₹{target_price:,} is what I can offer. It's competitive and fair.",
                    f"I've analyzed similar items - ₹{target_price:,} is a solid market price."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"I've been looking at similar items, and ₹{target_price:,} seems reasonable. What do you think?",
                    f"Based on my research, ₹{target_price:,} appears fair for both of us."
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"I understand the value, but my budget is limited to ₹{target_price:,}. Is there any flexibility?",
                    f"₹{target_price:,} is really what I can afford. I hope that might work?"
                ]
            },
            
            # Logistics keywords
            'logistics_keywords': ['meet', 'pickup', 'delivery', 'when', 'where', 'payment'],
            'logistics_responses': {
                NegotiationApproach.ASSERTIVE: [
                    "Perfect! I'm flexible with timing. I can arrange pickup today or tomorrow. Cash or online transfer?",
                    "Excellent! I can come whenever convenient for you. What payment method do you prefer?"
                ],
                NegotiationApproach.DIPLOMATIC: [
                    "Great! I'm available most times. When would work best for you? I can do cash or digital payment.",
                    "Wonderful! I'm flexible with both timing and payment method. What works for you?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    "Thank you! I can work around your schedule. Whatever time and payment method you prefer.",
                    "I appreciate it! I'm very flexible with pickup time and can pay however you'd like."
                ]
            }
        }
        
        # Check for keyword matches and return appropriate response
        for category in ['price_low', 'agreeable', 'greeting', 'price', 'logistics']:
            keywords = keyword_responses[f'{category}_keywords']
            if any(keyword in message_lower for keyword in keywords):
                responses = keyword_responses[f'{category}_responses'][approach]
                return random.choice(responses)
        
        # Default fallback response when no keywords match
        default_responses = {
            NegotiationApproach.ASSERTIVE: [
                f"Based on my research, ₹{target_price:,} is a fair market price for this item.",
                f"I'm prepared to offer ₹{target_price:,} which aligns with current market values."
            ],
            NegotiationApproach.DIPLOMATIC: [
                f"I'm hoping we can find a price that works for both of us, around ₹{target_price:,}.",
                f"Could we explore ₹{target_price:,} as a fair solution?"
            ],
            NegotiationApproach.CONSIDERATE: [
                f"I really hope we can work something out around ₹{target_price:,}.",
                f"₹{target_price:,} would really fit my budget perfectly. I hope that might work?"
            ]
        }
        return random.choice(default_responses[approach])
    
    def _get_enhanced_fallback_response(
        self, 
        session_data: Dict[str, Any],
        seller_message: str,
        tactics: List[NegotiationTactic],
        decision: Dict[str, Any],
        product: Product
    ) -> str:
        """Enhanced fallback responses using keyword-based static responses"""
        
        session = session_data['session']
        approach = session.user_params.approach
        target_price = session.user_params.target_price
        max_budget = session.user_params.max_budget
        
        action = decision.get('action', 'continue')
        
        # Handle specific decisions
        if action == 'accept':
            return random.choice([
                "Perfect! That works for me. When can we arrange the pickup?",
                "Excellent! I accept your offer. How should we proceed with payment?",
                "Great! That's exactly what I was hoping for. Let's finalize this deal."
            ])
        
        elif action == 'walk_away':
            return random.choice([
                "I appreciate your time, but that's beyond my budget. Thank you for considering my offers.",
                "Thank you for the negotiation. Unfortunately, we couldn't reach a mutually beneficial agreement.",
                "I understand your position, but I'll need to explore other options. Best of luck with your sale!"
            ])
        
        elif action in ['counter_offer', 'final_offer']:
            offer = decision.get('offer', target_price)
            
            # Use tactics in fallback responses
            if NegotiationTactic.ANCHORING in tactics:
                return f"Based on current market rates, I think ₹{offer:,} is a fair price. Similar items are selling in this range."
            
            elif NegotiationTactic.URGENCY in tactics:
                return f"I can make a quick decision if we can agree on ₹{offer:,}. I'm ready to complete the purchase today."
            
            elif NegotiationTactic.SCARCITY in tactics:
                return f"I'm considering a few options, but yours is my preference. Would ₹{offer:,} work? I can decide immediately."
            
            elif NegotiationTactic.BUNDLING in tactics:
                return f"For ₹{offer:,}, could you include original accessories or help with delivery? That would seal the deal."
            
            elif NegotiationTactic.RECIPROCITY in tactics:
                return f"I appreciate your flexibility on this. Meeting me at ₹{offer:,} would really help within my budget."
            
            else:
                # Default counter offer
                if approach == NegotiationApproach.ASSERTIVE:
                    return f"Let me be direct - ₹{offer:,} is my best offer based on market research. Can we make this work?"
                elif approach == NegotiationApproach.DIPLOMATIC:
                    return f"I've done some research and ₹{offer:,} seems fair for both of us. What do you think?"
                else:  # CONSIDERATE
                    return f"I really want this item. Could you please consider ₹{offer:,}? It would mean a lot to me."
        
        # KEYWORD-BASED STATIC RESPONSES - Dynamic responses based on seller's keywords
        return self._get_keyword_based_response(seller_message, session_data, product)
    
    def _get_keyword_based_response(
        self, 
        seller_message: str, 
        session_data: Dict[str, Any], 
        product: Product
    ) -> str:
        """Generate dynamic responses based on keywords in seller's message"""
        
        session = session_data['session']
        approach = session.user_params.approach
        target_price = session.user_params.target_price
        max_budget = session.user_params.max_budget
        message_lower = seller_message.lower()
        
        # Define keyword-based response mappings
        keyword_responses = {
            # Price is too low keywords
            'price_low_keywords': ['low', 'too low', 'very low', 'not enough', 'insufficient', 'can\'t accept', 'won\'t work'],
            'price_low_responses': {
                NegotiationApproach.ASSERTIVE: [
                    f"I understand, but ₹{target_price:,} is based on market research. Similar items are selling at this price range.",
                    f"Let me be clear - ₹{target_price:,} is a fair market price. I've seen comparable items at this rate.",
                    f"I've done my homework on pricing. ₹{target_price:,} is what the market supports for this item."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"I appreciate your perspective. Could we perhaps meet somewhere around ₹{target_price:,}? I believe it's fair for both parties.",
                    f"I understand your position. Based on my research, ₹{target_price:,} seems reasonable. What are your thoughts?",
                    f"Let's find a middle ground. I think ₹{target_price:,} could work well for both of us."
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"I really appreciate you considering my offer. ₹{target_price:,} would really help with my budget constraints.",
                    f"I hope we can work something out around ₹{target_price:,}. This would mean a lot to me.",
                    f"I understand it might seem low, but ₹{target_price:,} is what I can comfortably afford right now."
                ]
            },
            
            # Seller is okay/agreeable keywords
            'agreeable_keywords': ['ok', 'okay', 'fine', 'alright', 'sounds good', 'agreed', 'deal', 'accept', 'yes'],
            'agreeable_responses': {
                NegotiationApproach.ASSERTIVE: [
                    "Excellent! Let's finalize this deal. When can we arrange pickup?",
                    "Perfect! I'm ready to proceed. How should we handle payment?",
                    "Great decision! Let's exchange contact details and complete this transaction."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    "Wonderful! I'm glad we could reach an agreement. How would you like to proceed?",
                    "That's fantastic! Thank you for being flexible. What's the next step?",
                    "Excellent! I appreciate your cooperation. Shall we arrange the pickup details?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    "Thank you so much! This really means a lot to me. How can we arrange the pickup?",
                    "I'm so grateful we could work this out! When would be convenient for you?",
                    "Thank you for understanding! I really appreciate your flexibility."
                ]
            },
            
            # Negotiation/counter-offer keywords
            'negotiation_keywords': ['counter', 'negotiate', 'how about', 'what about', 'consider', 'think about'],
            'negotiation_responses': {
                NegotiationApproach.ASSERTIVE: [
                    f"I'm open to discussion, but ₹{target_price:,} is really where I need to be for this to work.",
                    f"Let's talk numbers. My research shows ₹{target_price:,} is fair market value.",
                    f"I can negotiate, but ₹{target_price:,} is based on solid market analysis."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"I'm definitely open to finding a solution that works for both of us around ₹{target_price:,}.",
                    f"Absolutely, let's see if we can find common ground near ₹{target_price:,}.",
                    f"I appreciate your willingness to negotiate. Could ₹{target_price:,} work for you?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"I'd really appreciate any flexibility you could show. ₹{target_price:,} would be perfect for me.",
                    f"I hope we can find something that works. ₹{target_price:,} would really help my situation.",
                    f"Thank you for being open to negotiation. ₹{target_price:,} would be wonderful."
                ]
            },
            
            # High price/expensive keywords
            'expensive_keywords': ['expensive', 'high', 'too much', 'costly', 'pricey', 'beyond budget'],
            'expensive_responses': {
                NegotiationApproach.ASSERTIVE: [
                    f"I understand it might seem high, but I've researched the market and ₹{target_price:,} is competitive.",
                    f"Let me show you the value - at ₹{target_price:,}, this is actually below market average.",
                    f"I've compared prices extensively. ₹{target_price:,} is fair considering the market rates."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"I see your concern about the price. Could we explore ₹{target_price:,} as a middle ground?",
                    f"Price is important to me too. I think ₹{target_price:,} offers good value for both of us.",
                    f"Let's find a balance. Would ₹{target_price:,} be more reasonable?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"I understand budget concerns completely. ₹{target_price:,} is really stretching my budget too.",
                    f"I share your concern about price. ₹{target_price:,} would really help me stay within budget.",
                    f"I feel the same way about high prices. ₹{target_price:,} would be perfect for me."
                ]
            },
            
            # Urgent/quick sale keywords
            'urgency_keywords': ['urgent', 'quick', 'asap', 'immediately', 'today', 'now', 'fast'],
            'urgency_responses': {
                NegotiationApproach.ASSERTIVE: [
                    f"Perfect! I can make a quick decision at ₹{target_price:,}. Let's close this deal today.",
                    f"Excellent timing! I'm ready to purchase immediately at ₹{target_price:,}.",
                    f"I appreciate the urgency. ₹{target_price:,} and we can complete this transaction right now."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"I understand you need a quick sale. Could ₹{target_price:,} work for an immediate purchase?",
                    f"If timing is important, I'm ready to proceed quickly at ₹{target_price:,}.",
                    f"I can help with your timeline. Would ₹{target_price:,} work for a same-day deal?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"I'd love to help with your urgent sale! ₹{target_price:,} would let me decide immediately.",
                    f"I understand you need this sold quickly. ₹{target_price:,} would allow me to buy today.",
                    f"I can be your quick buyer at ₹{target_price:,} if that helps your timeline."
                ]
            }
        }
        
        # Check for keyword matches and return appropriate response
        for category in ['price_low', 'agreeable', 'negotiation', 'expensive', 'urgency']:
            keywords = keyword_responses[f'{category}_keywords']
            if any(keyword in message_lower for keyword in keywords):
                responses = keyword_responses[f'{category}_responses'][approach]
                return random.choice(responses)
        
        # Default greeting and general responses
        if any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
            greeting_responses = {
                NegotiationApproach.ASSERTIVE: [
                    f"Hello! I'm interested in your {product.title}. I can offer ₹{target_price:,} based on current market rates.",
                    f"Hi there! I've researched similar items and ₹{target_price:,} seems like a fair price for your {product.title}."
                ],
                NegotiationApproach.DIPLOMATIC: [
                    f"Hello {product.seller_name}! I'm very interested in your {product.title}. Could we discuss ₹{target_price:,}?",
                    f"Hi! Your {product.title} caught my attention. Would ₹{target_price:,} be something we could work with?"
                ],
                NegotiationApproach.CONSIDERATE: [
                    f"Hello! I really love your {product.title}. I hope ₹{target_price:,} might work for both of us.",
                    f"Hi {product.seller_name}! Your {product.title} is exactly what I'm looking for. Could ₹{target_price:,} work?"
                ]
            }
            return random.choice(greeting_responses[approach])
        
        # Default fallback response when no keywords match
        default_responses = {
            NegotiationApproach.ASSERTIVE: [
                f"Based on my research, ₹{target_price:,} is a fair market price for this item.",
                f"I'm prepared to offer ₹{target_price:,} which aligns with current market values.",
                f"My analysis shows ₹{target_price:,} is competitive for this type of item."
            ],
            NegotiationApproach.DIPLOMATIC: [
                f"I'm interested in finding a price that works for both of us, around ₹{target_price:,}.",
                f"Could we explore ₹{target_price:,} as a fair middle ground?",
                f"I'm hoping we can reach an agreement near ₹{target_price:,}."
            ],
            NegotiationApproach.CONSIDERATE: [
                f"I really hope we can work something out around ₹{target_price:,}.",
                f"₹{target_price:,} would really fit my budget perfectly. I hope that might work?",
                f"I'm really interested and ₹{target_price:,} would be ideal for me."
            ]
        }
        return random.choice(default_responses[approach])


# Utility function to test Gemini API connection
async def test_gemini_connection():
    """Test function to verify Gemini API is working"""
    service = GeminiAIService()
    
    if not service.model:
        print("[ERROR] Gemini API not configured properly")
        return False
    
    try:
        test_prompt = "Say 'Hello from Gemini AI!' in a friendly way."
        response = await service._call_gemini_api(test_prompt)
        print(f"[INFO] Gemini API test successful: {response}")
        return True
    except Exception as e:
        print(f"[ERROR] Gemini API test failed: {e}")
        return False