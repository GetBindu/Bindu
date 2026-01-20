"""
Advanced Negotiation Strategy Engine
Implements sophisticated negotiation tactics and decision-making logic
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
import json
import random
from models import ChatMessage, Product, NegotiationApproach, PurchaseTimeline
import logging

logger = logging.getLogger(__name__)

class NegotiationPhase(Enum):
    OPENING = "opening"
    EXPLORATION = "exploration"
    BARGAINING = "bargaining"
    CLOSING = "closing"
    DEADLOCK = "deadlock"

class SellerPersonality(Enum):
    FLEXIBLE = "flexible"
    FIRM = "firm"
    EAGER = "eager"
    HESITANT = "hesitant"
    AGGRESSIVE = "aggressive"

class NegotiationTactic(Enum):
    ANCHORING = "anchoring"
    SCARCITY = "scarcity"
    BUNDLING = "bundling"
    RECIPROCITY = "reciprocity"
    AUTHORITY = "authority"
    SOCIAL_PROOF = "social_proof"
    COMMITMENT = "commitment"
    URGENCY = "urgency"

class AdvancedNegotiationEngine:
    def __init__(self):
        self.conversation_analyzer = ConversationAnalyzer()
        self.strategy_selector = StrategySelector()
        self.response_generator = ResponseGenerator()
        self.decision_engine = DecisionEngine()
    
    async def process_negotiation_turn(
        self,
        session_data: Dict[str, Any],
        seller_message: str,
        chat_history: List[ChatMessage],
        product: Product
    ) -> Dict[str, Any]:
        """
        Process a complete negotiation turn with advanced strategy
        """
        try:
            # Step 1: Analyze seller's message and behavior
            seller_analysis = await self.conversation_analyzer.analyze_seller_message(
                seller_message, chat_history, session_data
            )
            
            # Step 2: Determine current negotiation phase
            current_phase = self._determine_negotiation_phase(chat_history, seller_analysis)
            
            # Step 3: Make strategic decision
            decision = await self.decision_engine.make_decision(
                session_data, seller_analysis, current_phase, product
            )
            
            # Step 4: Select appropriate tactics
            tactics = await self.strategy_selector.select_tactics(
                decision, seller_analysis, current_phase, session_data
            )
            
            # Step 5: Generate response
            response = await self.response_generator.generate_strategic_response(
                decision, tactics, seller_analysis, session_data, product
            )
            
            return {
                'response': response,
                'decision': decision,
                'tactics_used': tactics,
                'seller_analysis': seller_analysis,
                'phase': current_phase.value,
                'confidence': decision.get('confidence', 0.7)
            }
            
        except Exception as e:
            logger.error(f"Error in negotiation turn processing: {e}")
            return {
                'response': "I understand. Let me think about your offer and get back to you.",
                'decision': {'action': 'pause', 'confidence': 0.5},
                'tactics_used': [],
                'seller_analysis': {},
                'phase': 'exploration',
                'confidence': 0.5
            }
    
    def _determine_negotiation_phase(
        self, 
        chat_history: List[ChatMessage], 
        seller_analysis: Dict[str, Any]
    ) -> NegotiationPhase:
        """Determine current negotiation phase"""
        
        message_count = len(chat_history)
        
        # Opening phase - first few exchanges
        if message_count <= 2:
            return NegotiationPhase.OPENING
        
        # Check for closing indicators
        closing_keywords = ['deal', 'final', 'accept', 'agree', 'done', 'sold']
        recent_messages = [msg.content.lower() for msg in chat_history[-3:]]
        
        if any(keyword in ' '.join(recent_messages) for keyword in closing_keywords):
            return NegotiationPhase.CLOSING
        
        # Check for deadlock
        if seller_analysis.get('flexibility_score', 0.5) < 0.2 and message_count > 6:
            return NegotiationPhase.DEADLOCK
        
        # Exploration vs Bargaining
        price_mentioned = any('price' in msg.content.lower() or '₹' in msg.content 
                            for msg in chat_history[-3:])
        
        if price_mentioned and message_count > 3:
            return NegotiationPhase.BARGAINING
        else:
            return NegotiationPhase.EXPLORATION


class ConversationAnalyzer:
    """Analyzes seller messages for behavioral patterns and negotiation cues"""
    
    def __init__(self):
        self.sentiment_keywords = {
            'positive': ['good', 'excellent', 'perfect', 'great', 'wonderful', 'yes', 'sure', 'okay'],
            'negative': ['no', 'cannot', 'impossible', 'never', 'refuse', 'reject'],
            'neutral': ['maybe', 'consider', 'think', 'possible', 'perhaps']
        }
        
        self.flexibility_indicators = {
            'high': ['negotiate', 'flexible', 'consider', 'discuss', 'maybe', 'perhaps'],
            'low': ['firm', 'fixed', 'final', 'non-negotiable', 'minimum', 'cannot']
        }
        
        self.urgency_indicators = {
            'high': ['urgent', 'immediately', 'today', 'asap', 'quick'],
            'low': ['whenever', 'no rush', 'flexible', 'anytime']
        }
    
    async def analyze_seller_message(
        self, 
        message: str, 
        chat_history: List[ChatMessage],
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Comprehensive analysis of seller's message and behavior"""
        
        message_lower = message.lower()
        
        # Sentiment Analysis
        sentiment = self._analyze_sentiment(message_lower)
        
        # Flexibility Assessment
        flexibility_score = self._assess_flexibility(message_lower, chat_history)
        
        # Urgency Detection
        urgency_level = self._detect_urgency(message_lower)
        
        # Personality Inference
        personality = self._infer_personality(message_lower, chat_history)
        
        # Price Movement Analysis
        price_analysis = self._analyze_price_movement(message, chat_history)
        
        # Objection Analysis
        objections = self._identify_objections(message_lower)
        
        # Buying Signals
        buying_signals = self._detect_buying_signals(message_lower)
        
        # Response Time Pattern
        response_pattern = self._analyze_response_pattern(chat_history)
        
        return {
            'sentiment': sentiment,
            'flexibility_score': flexibility_score,
            'urgency_level': urgency_level,
            'personality': personality.value,
            'price_analysis': price_analysis,
            'objections': objections,
            'buying_signals': buying_signals,
            'response_pattern': response_pattern,
            'message_length': len(message),
            'politeness_score': self._assess_politeness(message_lower)
        }
    
    def _analyze_sentiment(self, message: str) -> str:
        """Analyze sentiment of seller's message"""
        positive_count = sum(1 for word in self.sentiment_keywords['positive'] if word in message)
        negative_count = sum(1 for word in self.sentiment_keywords['negative'] if word in message)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _assess_flexibility(self, message: str, chat_history: List[ChatMessage]) -> float:
        """Assess seller's flexibility on a scale of 0-1"""
        
        high_flex_count = sum(1 for word in self.flexibility_indicators['high'] if word in message)
        low_flex_count = sum(1 for word in self.flexibility_indicators['low'] if word in message)
        
        # Base score
        base_score = 0.5
        
        # Adjust based on keywords
        if high_flex_count > 0:
            base_score += 0.2 * high_flex_count
        if low_flex_count > 0:
            base_score -= 0.3 * low_flex_count
        
        # Adjust based on price concessions in history
        price_concessions = self._count_price_concessions(chat_history)
        if price_concessions > 0:
            base_score += 0.1 * price_concessions
        
        return max(0, min(1, base_score))
    
    def _detect_urgency(self, message: str) -> str:
        """Detect seller's urgency level"""
        high_urgency = sum(1 for word in self.urgency_indicators['high'] if word in message)
        low_urgency = sum(1 for word in self.urgency_indicators['low'] if word in message)
        
        if high_urgency > 0:
            return 'high'
        elif low_urgency > 0:
            return 'low'
        else:
            return 'medium'
    
    def _infer_personality(self, message: str, chat_history: List[ChatMessage]) -> SellerPersonality:
        """Infer seller personality type"""
        
        # Analyze message patterns
        avg_response_length = sum(len(msg.content) for msg in chat_history if msg.sender == 'seller') / max(1, len([msg for msg in chat_history if msg.sender == 'seller']))
        
        if 'firm' in message or 'final' in message or 'non-negotiable' in message:
            return SellerPersonality.FIRM
        elif 'flexible' in message or 'negotiate' in message:
            return SellerPersonality.FLEXIBLE
        elif 'quick' in message or 'urgent' in message or avg_response_length < 50:
            return SellerPersonality.EAGER
        elif avg_response_length > 150:
            return SellerPersonality.HESITANT
        else:
            return SellerPersonality.FLEXIBLE  # Default
    
    def _analyze_price_movement(self, message: str, chat_history: List[ChatMessage]) -> Dict[str, Any]:
        """Analyze price-related information in message"""
        
        # Extract prices mentioned
        import re
        price_pattern = r'₹[\s,]*(\d+(?:,\d+)*)'
        prices = re.findall(price_pattern, message)
        
        if prices:
            current_price = int(prices[-1].replace(',', ''))
            
            # Compare with previous prices
            previous_prices = []
            for msg in chat_history:
                if msg.sender == 'seller':
                    msg_prices = re.findall(price_pattern, msg.content)
                    previous_prices.extend([int(p.replace(',', '')) for p in msg_prices])
            
            trend = 'stable'
            if previous_prices:
                last_price = previous_prices[-1] if previous_prices else current_price
                if current_price < last_price:
                    trend = 'decreasing'
                elif current_price > last_price:
                    trend = 'increasing'
            
            return {
                'current_price': current_price,
                'previous_prices': previous_prices,
                'trend': trend,
                'concession_amount': previous_prices[-1] - current_price if previous_prices else 0
            }
        
        return {'current_price': None, 'previous_prices': [], 'trend': 'stable', 'concession_amount': 0}
    
    def _identify_objections(self, message: str) -> List[str]:
        """Identify seller objections"""
        objections = []
        
        objection_patterns = {
            'price_too_low': ['too low', 'not enough', 'cannot accept', 'minimum'],
            'condition_concerns': ['condition', 'wear', 'damage', 'issue'],
            'timing_issues': ['time', 'when', 'schedule', 'availability'],
            'trust_concerns': ['trust', 'verify', 'proof', 'guarantee']
        }
        
        for objection_type, keywords in objection_patterns.items():
            if any(keyword in message for keyword in keywords):
                objections.append(objection_type)
        
        return objections
    
    def _detect_buying_signals(self, message: str) -> List[str]:
        """Detect positive buying signals"""
        signals = []
        
        signal_patterns = {
            'price_acceptance': ['okay', 'fine', 'accept', 'deal'],
            'logistics_discussion': ['when', 'where', 'pickup', 'delivery', 'meet'],
            'payment_discussion': ['payment', 'cash', 'transfer', 'money'],
            'urgency_to_sell': ['urgent', 'immediately', 'quick sale']
        }
        
        for signal_type, keywords in signal_patterns.items():
            if any(keyword in message for keyword in keywords):
                signals.append(signal_type)
        
        return signals
    
    def _count_price_concessions(self, chat_history: List[ChatMessage]) -> int:
        """Count number of price concessions made by seller"""
        # Implementation would track price decreases over time
        return 0  # Placeholder
    
    def _assess_politeness(self, message: str) -> float:
        """Assess politeness level of message"""
        polite_words = ['please', 'thank', 'sorry', 'appreciate', 'understand', 'respect']
        rude_words = ['no way', 'impossible', 'ridiculous', 'waste']
        
        polite_count = sum(1 for word in polite_words if word in message)
        rude_count = sum(1 for word in rude_words if word in message)
        
        base_score = 0.6
        base_score += 0.1 * polite_count
        base_score -= 0.2 * rude_count
        
        return max(0, min(1, base_score))
    
    def _analyze_response_pattern(self, chat_history: List[ChatMessage]) -> Dict[str, Any]:
        """Analyze seller's response patterns"""
        seller_messages = [msg for msg in chat_history if msg.sender == 'seller']
        
        if len(seller_messages) < 2:
            return {'avg_response_time': None, 'consistency': 'unknown'}
        
        # Calculate average message length
        avg_length = sum(len(msg.content) for msg in seller_messages) / len(seller_messages)
        
        # Analyze response times (if timestamps are available)
        response_times = []
        for i in range(1, len(seller_messages)):
            time_diff = (seller_messages[i].timestamp - seller_messages[i-1].timestamp).total_seconds()
            response_times.append(time_diff)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            'avg_response_time': avg_response_time,
            'avg_message_length': avg_length,
            'consistency': 'consistent' if avg_length > 30 else 'brief'
        }


class StrategySelector:
    """Selects appropriate negotiation tactics based on analysis"""
    
    def __init__(self):
        self.tactic_effectiveness = {
            NegotiationTactic.ANCHORING: {'flexible': 0.8, 'firm': 0.4, 'eager': 0.9},
            NegotiationTactic.SCARCITY: {'flexible': 0.6, 'firm': 0.3, 'eager': 0.9},
            NegotiationTactic.BUNDLING: {'flexible': 0.7, 'firm': 0.5, 'eager': 0.6},
            NegotiationTactic.URGENCY: {'flexible': 0.5, 'firm': 0.2, 'eager': 0.8}
        }
    
    async def select_tactics(
        self, 
        decision: Dict[str, Any], 
        seller_analysis: Dict[str, Any], 
        phase: NegotiationPhase,
        session_data: Dict[str, Any]
    ) -> List[NegotiationTactic]:
        """Select most effective tactics for current situation"""
        
        tactics = []
        personality = seller_analysis.get('personality', 'flexible')
        
        # Phase-specific tactics
        if phase == NegotiationPhase.OPENING:
            tactics.append(NegotiationTactic.ANCHORING)
            if seller_analysis.get('urgency_level') == 'high':
                tactics.append(NegotiationTactic.URGENCY)
        
        elif phase == NegotiationPhase.BARGAINING:
            if seller_analysis.get('flexibility_score', 0.5) > 0.6:
                tactics.append(NegotiationTactic.RECIPROCITY)
            
            if 'price_too_low' in seller_analysis.get('objections', []):
                tactics.append(NegotiationTactic.SOCIAL_PROOF)
        
        elif phase == NegotiationPhase.CLOSING:
            tactics.append(NegotiationTactic.COMMITMENT)
            if seller_analysis.get('urgency_level') == 'high':
                tactics.append(NegotiationTactic.SCARCITY)
        
        elif phase == NegotiationPhase.DEADLOCK:
            tactics.append(NegotiationTactic.BUNDLING)
            tactics.append(NegotiationTactic.AUTHORITY)
        
        # Filter tactics by effectiveness for this seller personality
        effective_tactics = []
        for tactic in tactics:
            effectiveness = self.tactic_effectiveness.get(tactic, {}).get(personality, 0.5)
            if effectiveness > 0.4:  # Only use tactics with >40% effectiveness
                effective_tactics.append(tactic)
        
        return effective_tactics[:3]  # Max 3 tactics per response


class DecisionEngine:
    """Makes strategic decisions about negotiation actions"""
    
    async def make_decision(
        self,
        session_data: Dict[str, Any],
        seller_analysis: Dict[str, Any],
        phase: NegotiationPhase,
        product: Product
    ) -> Dict[str, Any]:
        """Make strategic decision for next action"""
        
        target_price = session_data.get('target_price', 0)
        max_budget = session_data.get('max_budget', 0)
        current_price = seller_analysis.get('price_analysis', {}).get('current_price')
        
        if not current_price:
            current_price = product.price
        
        # Decision logic
        if current_price <= target_price:
            return {
                'action': 'accept',
                'confidence': 0.9,
                'reasoning': 'Price within target range'
            }
        
        elif current_price <= max_budget:
            # Calculate offer strategy
            if seller_analysis.get('flexibility_score', 0.5) > 0.6:
                # Seller is flexible, negotiate further
                new_offer = self._calculate_counter_offer(
                    current_price, target_price, seller_analysis, phase
                )
                return {
                    'action': 'counter_offer',
                    'offer': new_offer,
                    'confidence': 0.7,
                    'reasoning': 'Seller shows flexibility, room for negotiation'
                }
            else:
                # Seller is firm, consider accepting or walking away
                if current_price < max_budget * 0.95:  # Within 95% of budget
                    return {
                        'action': 'accept_with_conditions',
                        'confidence': 0.6,
                        'reasoning': 'Close to budget limit, try to add value'
                    }
        
        else:
            # Price exceeds budget
            if seller_analysis.get('flexibility_score', 0.5) > 0.7:
                # One last attempt
                final_offer = min(max_budget, int(target_price * 1.1))
                return {
                    'action': 'final_offer',
                    'offer': final_offer,
                    'confidence': 0.4,
                    'reasoning': 'Last attempt before walking away'
                }
            else:
                return {
                    'action': 'walk_away',
                    'confidence': 0.8,
                    'reasoning': 'Price too high, seller inflexible'
                }
        
        # Default: continue negotiating
        return {
            'action': 'continue',
            'confidence': 0.5,
            'reasoning': 'Gather more information'
        }
    
    def _calculate_counter_offer(
        self, 
        current_price: int, 
        target_price: int, 
        seller_analysis: Dict[str, Any], 
        phase: NegotiationPhase
    ) -> int:
        """Calculate strategic counter offer"""
        
        flexibility = seller_analysis.get('flexibility_score', 0.5)
        
        # Base increment calculation
        price_gap = current_price - target_price
        
        if phase == NegotiationPhase.OPENING:
            # Start low, room to move up
            increment = int(price_gap * 0.3 * flexibility)
        elif phase == NegotiationPhase.BARGAINING:
            # Moderate increments
            increment = int(price_gap * 0.4 * flexibility)
        else:
            # Smaller increments in later phases
            increment = int(price_gap * 0.6 * flexibility)
        
        new_offer = target_price + increment
        return min(new_offer, current_price - 1000)  # Always offer less than current


class ResponseGenerator:
    """Generates contextual negotiation responses using selected tactics"""
    
    def __init__(self):
        self.tactic_templates = {
            NegotiationTactic.ANCHORING: [
                "Based on current market rates for similar items, I was thinking around ₹{offer:,}. What do you think?",
                "I've seen similar products selling for ₹{offer:,}. Would that work for you?"
            ],
            NegotiationTactic.SCARCITY: [
                "I'm looking at a few similar listings. If we can agree on ₹{offer:,}, I can decide right away.",
                "I have another option, but I prefer yours. Can you consider ₹{offer:,}?"
            ],
            NegotiationTactic.URGENCY: [
                "I need to make a decision today. If ₹{offer:,} works, I can arrange pickup immediately.",
                "I can transfer the money right now if we agree on ₹{offer:,}."
            ],
            NegotiationTactic.RECIPROCITY: [
                "I appreciate your flexibility. Meeting me at ₹{offer:,} would really help my budget.",
                "Since you're being reasonable, I can stretch to ₹{offer:,}. That's really my best offer."
            ],
            NegotiationTactic.SOCIAL_PROOF: [
                "Similar items in this condition usually sell for around ₹{offer:,}. Market research shows this is fair.",
                "Based on what others are paying for similar products, ₹{offer:,} seems right."
            ],
            NegotiationTactic.BUNDLING: [
                "For ₹{offer:,}, could you include {additional_item}? That would make it worthwhile.",
                "I can do ₹{offer:,} if you can help with delivery/warranty/accessories."
            ],
            NegotiationTactic.AUTHORITY: [
                "My budget advisor suggested not going above ₹{offer:,} for items like this.",
                "Based on expert recommendations, ₹{offer:,} is the fair market value."
            ],
            NegotiationTactic.COMMITMENT: [
                "If you accept ₹{offer:,}, I'm ready to close the deal right now.",
                "₹{offer:,} and we have a deal. I'll bring cash for immediate pickup."
            ]
        }
    
    async def generate_strategic_response(
        self,
        decision: Dict[str, Any],
        tactics: List[NegotiationTactic],
        seller_analysis: Dict[str, Any],
        session_data: Dict[str, Any],
        product: Product
    ) -> str:
        """Generate enhanced response using comprehensive analysis and talking points"""
        
        action = decision.get('action', 'continue')
        strategy = session_data.get('strategy', {})
        talking_points = strategy.get('talking_points', {})
        
        if action == 'accept':
            return self._generate_acceptance_response(seller_analysis, session_data, talking_points)
        elif action == 'walk_away':
            return self._generate_walkaway_response(seller_analysis, session_data, talking_points)
        elif action in ['counter_offer', 'final_offer']:
            return self._generate_enhanced_tactical_response(
                decision, tactics, seller_analysis, session_data, product, talking_points
            )
        else:
            return self._generate_enhanced_exploratory_response(
                seller_analysis, session_data, talking_points
            )
    
    def _generate_enhanced_tactical_response(
        self, 
        decision: Dict[str, Any], 
        tactics: List[NegotiationTactic],
        seller_analysis: Dict[str, Any],
        session_data: Dict[str, Any],
        product: Product,
        talking_points: Dict[str, Any]
    ) -> str:
        """Generate enhanced tactical response using comprehensive analysis"""
        
        strategy = session_data.get('strategy', {})
        offer_amount = decision.get('offer_amount', 0)
        
        # Build response components
        response_parts = []
        
        # 1. Opening acknowledgment
        if seller_analysis.get('contains_offer'):
            response_parts.append("Thank you for your response.")
        else:
            response_parts.append("I appreciate you considering my interest.")
        
        # 2. Use market-based arguments from analysis
        price_arguments = talking_points.get('price_arguments', [])
        if price_arguments and NegotiationTactic.SOCIAL_PROOF in tactics:
            response_parts.append(random.choice(price_arguments))
        
        # 3. Address condition concerns if relevant
        condition_points = talking_points.get('condition_points', [])
        if condition_points and strategy.get('condition_factors', {}).get('concerns'):
            response_parts.append(random.choice(condition_points))
        
        # 4. Present the offer with appropriate tactic
        offer_statement = self._format_offer_with_tactic(
            offer_amount, tactics, strategy, talking_points
        )
        response_parts.append(offer_statement)
        
        # 5. Add urgency or closing element
        if decision.get('action') == 'final_offer':
            closing_args = talking_points.get('closing_arguments', [])
            if closing_args:
                response_parts.append(random.choice(closing_args))
            else:
                response_parts.append("This is my best offer. Please let me know if this works for you.")
        
        return " ".join(response_parts)
    
    def _generate_enhanced_exploratory_response(
        self, 
        seller_analysis: Dict[str, Any], 
        session_data: Dict[str, Any],
        talking_points: Dict[str, Any]
    ) -> str:
        """Generate enhanced exploratory response for opening or information gathering"""
        
        strategy = session_data.get('strategy', {})
        
        # Use opening points from comprehensive analysis
        opening_points = talking_points.get('opening_statements', [])
        if opening_points:
            main_message = random.choice(opening_points)
        else:
            main_message = f"I'm interested in your {session_data.get('product', {}).get('category', 'item')}."
        
        # Add market comparison if available
        market_comparisons = talking_points.get('market_comparisons', [])
        if market_comparisons:
            market_info = random.choice(market_comparisons)
            return f"{main_message} {market_info} What are your thoughts on the pricing?"
        
        return f"{main_message} Could you tell me more about its condition and if there's any flexibility in the price?"
    
    def _format_offer_with_tactic(
        self, 
        offer_amount: int, 
        tactics: List[NegotiationTactic],
        strategy: Dict[str, Any],
        talking_points: Dict[str, Any]
    ) -> str:
        """Format offer using the most appropriate tactic"""
        
        primary_tactic = tactics[0] if tactics else NegotiationTactic.ANCHORING
        
        # Use market-based justification for anchoring
        if primary_tactic == NegotiationTactic.ANCHORING:
            market_analysis = strategy.get('market_position', 'unknown')
            if market_analysis == 'above_market':
                return f"Based on market research, I can offer ₹{offer_amount:,}. This reflects the current market value for similar items."
            else:
                return f"Considering all factors, I can offer ₹{offer_amount:,}."
        
        # Use urgency from talking points
        elif primary_tactic == NegotiationTactic.URGENCY:
            return f"I'm ready to proceed immediately with ₹{offer_amount:,} if we can agree today."
        
        # Use condition-based reasoning
        elif primary_tactic == NegotiationTactic.AUTHORITY:
            condition_concerns = strategy.get('condition_factors', {}).get('concerns', [])
            if condition_concerns:
                return f"Given the condition factors, my budget allows for ₹{offer_amount:,}."
            else:
                return f"Based on my assessment, ₹{offer_amount:,} would be fair."
        
        # Default tactical approach
        else:
            templates = self.tactic_templates.get(primary_tactic, [
                "I can offer ₹{offer:,}. What do you think?"
            ])
            return random.choice(templates).format(offer=offer_amount)
    
    def _generate_acceptance_response(
        self, 
        seller_analysis: Dict[str, Any], 
        session_data: Dict[str, Any],
        talking_points: Dict[str, Any]
    ) -> str:
        """Generate acceptance response with next steps"""
        
        return ("Perfect! I accept your offer. I can arrange cash payment and pickup at your convenience. "
                "Please share your preferred time and location for the transaction.")
    
    def _generate_walkaway_response(
        self, 
        seller_analysis: Dict[str, Any], 
        session_data: Dict[str, Any],
        talking_points: Dict[str, Any]
    ) -> str:
        """Generate polite walkaway response"""
        
        strategy = session_data.get('strategy', {})
        max_budget = strategy.get('maximum_budget', 0)
        
        return (f"I understand your position, but ₹{max_budget:,} is really the maximum I can go. "
                f"If you change your mind, please let me know. Otherwise, I'll have to consider other options. "
                f"Thank you for your time.")
    
    def _generate_tactical_response(
        self, 
        decision: Dict[str, Any], 
        tactics: List[NegotiationTactic],
        seller_analysis: Dict[str, Any], 
        session_data: Dict[str, Any],
        product: Product
    ) -> str:
        """Generate response using negotiation tactics"""
        
        offer = decision.get('offer', session_data.get('target_price'))
        
        if not tactics:
            return f"I understand your position. Would ₹{offer:,} be acceptable?"
        
        # Select primary tactic
        primary_tactic = tactics[0]
        templates = self.tactic_templates.get(primary_tactic, [])
        
        if templates:
            template = random.choice(templates)
            
            # Handle bundling tactic
            if primary_tactic == NegotiationTactic.BUNDLING:
                additional_items = ['original accessories', 'delivery', 'warranty extension']
                additional_item = random.choice(additional_items)
                return template.format(offer=offer, additional_item=additional_item)
            else:
                return template.format(offer=offer)
        
        # Fallback
        return f"Considering everything, I think ₹{offer:,} would be fair. What do you say?"
    
    def _generate_acceptance_response(self, seller_analysis: Dict[str, Any], session_data: Dict[str, Any]) -> str:
        """Generate acceptance response"""
        responses = [
            "Perfect! That works for me. When would be a good time to meet?",
            "Excellent! I accept your offer. How should we proceed with the payment and pickup?",
            "Great! That's exactly what I was hoping for. Shall we exchange contact details?"
        ]
        return random.choice(responses)
    
    def _generate_exploratory_response(self, seller_analysis: Dict[str, Any], session_data: Dict[str, Any]) -> str:
        """Generate exploratory/information gathering response"""
        responses = [
            "I'm very interested in your listing. Could you tell me more about the condition?",
            "This looks perfect for what I need. Is there any flexibility on the pricing?",
            "I've been looking for exactly this item. What's the best price you can offer?"
        ]
        return random.choice(responses)