"""
Advanced Session Manager
Handles complete negotiation session lifecycle with analytics and learning
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import uuid
from enum import Enum
import logging
from models import NegotiationSession, ChatMessage, Product, NegotiationParams
from database import JSONDatabase
from scraper_service import MarketplaceScraper, MarketIntelligence
from enhanced_scraper import EnhancedMarketplaceScraper
from negotiation_engine import AdvancedNegotiationEngine, NegotiationPhase

logger = logging.getLogger(__name__)

class SessionStatus(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    HUMAN_HANDOFF = "human_handoff"

class SessionOutcome(Enum):
    SUCCESS = "success"
    FAILED_PRICE = "failed_price"
    FAILED_TERMS = "failed_terms"
    SELLER_UNRESPONSIVE = "seller_unresponsive"
    USER_CANCELLED = "user_cancelled"
    TECHNICAL_ERROR = "technical_error"

class InterventionTrigger(Enum):
    DEADLOCK = "deadlock"
    COMPLEX_TERMS = "complex_terms"
    SELLER_REQUEST = "seller_request"
    TECHNICAL_ISSUE = "technical_issue"
    USER_REQUEST = "user_request"

class AdvancedSessionManager:
    """Manages complete negotiation session lifecycle"""
    
    def __init__(self, db: JSONDatabase, enhanced_ai_service=None):
        self.db = db
        self.active_sessions: Dict[str, Dict] = {}
        self.negotiation_engine = AdvancedNegotiationEngine()
        self.market_intelligence = MarketIntelligence()
        self.session_analytics = SessionAnalytics()
        self.learning_engine = LearningEngine()
        self.enhanced_ai_service = enhanced_ai_service  # Enhanced AI service for intelligent negotiation
    
    async def create_session_from_url(self, product_url: str, params: NegotiationParams) -> Dict[str, Any]:
        """
        Phase 1: Create session from marketplace URL with full product discovery
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Step 1: Scrape product information
            logger.info(f"Scraping product from URL: {product_url}")
            
            # Use enhanced scraper for better success rate
            async with EnhancedMarketplaceScraper() as scraper:
                product_data = await scraper.scrape_product(product_url)
            
            if not product_data or not isinstance(product_data, dict):
                raise ValueError("Could not scrape product information from URL")
            
            # Step 2: Comprehensive market intelligence and product analysis
            logger.info("Performing comprehensive product analysis...")
            try:
                market_analysis = await self.market_intelligence.comprehensive_product_analysis(
                    product_data, params.target_price, params.max_budget
                )
            except Exception as e:
                logger.warning(f"Comprehensive analysis failed, using fallback: {e}")
                # Create basic market analysis if comprehensive fails
                market_analysis = {
                    'market_analysis': {'estimated_value': product_data.get('price', params.max_budget)},
                    'condition_analysis': {'score': 0.7},
                    'price_justification': {'is_reasonable': True},
                    'negotiation_points': {'key_points': ['Product condition', 'Market price']},
                    'strategy': {'approach': 'conservative', 'success_probability': 0.6},
                    'risk_assessment': {'level': 'medium'},
                    'confidence_score': 0.6,
                    'recommended_actions': ['Start with polite inquiry', 'Present reasonable offer']
                }
            
            # Step 3: Create Product object
            product = Product(
                id=f"scraped_{session_id}",
                **product_data
            )
            
            # Step 4: Save product to database
            await self.db.save_product(product)
            
            # Step 5: Strategy formulation based on market data
            strategy_data = await self._formulate_initial_strategy(
                product, params, market_analysis
            )
            
            # Step 5.5: Update params with correct product_id
            params.product_id = product.id
            
            # Step 6: Create negotiation session
            session = NegotiationSession(
                id=session_id,
                product_id=product.id,
                user_params=params,
                status=SessionStatus.INITIALIZING.value,
                created_at=datetime.now(),
                messages=[]
            )
            
            # Enhanced session data
            session_data = {
                'session': session,
                'product': product,
                'market_analysis': market_analysis,
                'strategy': strategy_data,
                'phase': NegotiationPhase.OPENING,
                'intervention_triggers': [],
                'performance_metrics': {
                    'messages_sent': 0,
                    'price_concessions_achieved': 0,
                    'negotiation_effectiveness': 0.0,
                    'time_to_first_response': None
                }
            }
            
            # Store active session
            self.active_sessions[session_id] = session_data
            await self.db.save_session(session)
            
            logger.info(f"Session {session_id} created successfully")
            
            return {
                'session_id': session_id,
                'product': product,
                'market_analysis': market_analysis,
                'strategy': strategy_data,
                'message': 'Session initialized successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating session from URL: {e}")
            raise
    
    async def start_negotiation(self, session_id: str) -> Dict[str, Any]:
        """
        Phase 3: Start active negotiation process with initial contact
        """
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session_data = self.active_sessions[session_id]
            session = session_data['session']
            product = session_data['product']
            strategy = session_data['strategy']
            
            # Update session status
            session.status = SessionStatus.ACTIVE.value
            session_data['start_time'] = datetime.now()
            
            # Generate opening message using negotiation engine
            opening_result = await self.negotiation_engine.process_negotiation_turn(
                session_data, "", [], product
            )
            
            # Create opening message
            opening_message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                sender="ai",
                content=opening_result['response'],
                timestamp=datetime.now(),
                sender_type="ai"
            )
            
            # Add to session
            session.messages.append(opening_message)
            session_data['performance_metrics']['messages_sent'] += 1
            
            # Save session
            await self.db.save_session(session)
            
            logger.info(f"Negotiation started for session {session_id}")
            
            return {
                'opening_message': opening_result['response'],
                'strategy_used': opening_result.get('tactics_used', []),
                'confidence': opening_result.get('confidence', 0.7),
                'phase': opening_result.get('phase', 'opening')
            }
            
        except Exception as e:
            logger.error(f"Error starting negotiation: {e}")
            raise
    
    async def process_seller_response(self, session_id: str, seller_message: str) -> Dict[str, Any]:
        """
        Phase 3: Process seller response and generate AI counter-response
        """
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session_data = self.active_sessions[session_id]
            session = session_data['session']
            product = session_data['product']
            
            # Record seller response time
            if session_data['performance_metrics']['time_to_first_response'] is None:
                session_data['performance_metrics']['time_to_first_response'] = (
                    datetime.now() - session_data['start_time']
                ).total_seconds()
            
            # Create seller message
            seller_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                sender="seller",
                content=seller_message,
                timestamp=datetime.now(),
                sender_type="human"
            )
            
            session.messages.append(seller_msg)
            
            # Check for intervention triggers
            intervention = await self._check_intervention_triggers(session_data, seller_message)
            if intervention:
                return await self._trigger_human_handoff(session_id, intervention)
            
            # Generate AI response using enhanced AI service (LangChain + MCP) or fallback to engine
            if self.enhanced_ai_service:
                negotiation_result = await self.enhanced_ai_service.make_negotiation_decision(
                    session_data, seller_message, session.messages, product
                )
                # Convert to expected format
                negotiation_result = {
                    'response': negotiation_result['response'],
                    'confidence': negotiation_result['confidence'],
                    'tactics_used': negotiation_result['tactics_used'],
                    'phase': session_data.get('phase', 'exploration'),
                    'decision': {
                        'action': negotiation_result.get('action_type', 'respond'),
                        'reasoning': negotiation_result.get('reasoning', ''),
                        'source': negotiation_result.get('source', 'enhanced_ai')
                    },
                    'seller_analysis': negotiation_result.get('mcp_insights', {}).get('seller_behavior', {})
                }
            else:
                # Fallback to original negotiation engine
                negotiation_result = await self.negotiation_engine.process_negotiation_turn(
                    session_data, seller_message, session.messages, product
                )
            
            # Create AI response message
            ai_message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                sender="ai",
                content=negotiation_result['response'],
                timestamp=datetime.now(),
                sender_type="ai"
            )
            
            session.messages.append(ai_message)
            session_data['performance_metrics']['messages_sent'] += 1
            
            # Update session phase and metrics
            session_data['phase'] = negotiation_result.get('phase', 'exploration')
            await self._update_performance_metrics(session_data, negotiation_result)
            
            # Check for completion conditions
            completion_check = await self._check_completion_conditions(session_data, negotiation_result)
            if completion_check:
                return await self._complete_session(session_id, completion_check)
            
            # Save session
            await self.db.save_session(session)
            
            return {
                'ai_response': negotiation_result['response'],
                'decision': negotiation_result.get('decision', {}),
                'tactics_used': negotiation_result.get('tactics_used', []),
                'phase': negotiation_result.get('phase'),
                'confidence': negotiation_result.get('confidence'),
                'seller_analysis': negotiation_result.get('seller_analysis', {}),
                'session_status': session.status
            }
            
        except Exception as e:
            logger.error(f"Error processing seller response: {e}")
            await self._handle_session_error(session_id, str(e))
            raise
    
    async def _formulate_initial_strategy(
        self, 
        product: Product, 
        params: NegotiationParams, 
        comprehensive_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 2: Enhanced strategy formulation using comprehensive analysis
        """
        
        # Extract analysis components
        market_analysis = comprehensive_analysis.get('market_analysis', {})
        condition_analysis = comprehensive_analysis.get('condition_analysis', {})
        price_justification = comprehensive_analysis.get('price_justification', {})
        negotiation_points = comprehensive_analysis.get('negotiation_points', {})
        ai_strategy = comprehensive_analysis.get('strategy', {})
        risk_assessment = comprehensive_analysis.get('risk_assessment', {})
        
        # Enhanced strategy using AI recommendations
        strategy = {
            'approach': ai_strategy.get('approach', 'data_driven'),
            'opening_offer': ai_strategy.get('opening_offer', params.target_price),
            'target_price': params.target_price,
            'maximum_budget': params.max_budget,
            'fallback_offer': ai_strategy.get('fallback_offer', params.max_budget),
            'negotiation_phases': ai_strategy.get('negotiation_phases', []),
            'key_tactics': ai_strategy.get('key_tactics', []),
            'success_probability': ai_strategy.get('success_probability', 60),
            'confidence_score': comprehensive_analysis.get('confidence_score', 0.7),
            
            # Market intelligence
            'market_position': market_analysis.get('market_position', 'unknown'),
            'negotiation_potential': market_analysis.get('negotiation_potential', 0.15),
            'estimated_fair_value': market_analysis.get('estimated_market_value', product.price),
            
            # Product insights
            'condition_factors': {
                'condition': condition_analysis.get('condition', 'Good'),
                'positive_points': condition_analysis.get('positive_indicators', []),
                'concerns': condition_analysis.get('negative_indicators', []),
                'condition_multiplier': condition_analysis.get('condition_multiplier', 0.85)
            },
            
            # Pricing strategy
            'price_strategy': {
                'is_overpriced': price_justification.get('is_overpriced', False),
                'negotiation_room': price_justification.get('negotiation_room', 0),
                'price_difference_pct': price_justification.get('price_difference_percentage', 0)
            },
            
            # Talking points for AI agent
            'talking_points': {
                'opening_statements': negotiation_points.get('opening_points', []),
                'price_arguments': negotiation_points.get('price_justification', []),
                'condition_points': negotiation_points.get('condition_concerns', []),
                'market_comparisons': negotiation_points.get('market_comparisons', []),
                'closing_arguments': negotiation_points.get('closing_arguments', [])
            },
            
            # Risk management
            'risks': {
                'level': risk_assessment.get('overall_risk_level', 'medium'),
                'concerns': risk_assessment.get('high_risks', []) + risk_assessment.get('medium_risks', []),
                'mitigation': risk_assessment.get('mitigation_strategies', [])
            },
            
            # Behavioral adjustments based on user preferences
            'user_approach': params.approach.value if hasattr(params.approach, 'value') else params.approach,
            'timeline': params.timeline.value if hasattr(params.timeline, 'value') else params.timeline
        }
        
        # Adjust AI behavior based on user approach
        approach_val = strategy['user_approach']
        if approach_val == 'assertive':
            strategy['confidence_multiplier'] = 1.2
            strategy['concession_rate'] = 0.05  # Smaller concessions
        elif approach_val == 'diplomatic':
            strategy['confidence_multiplier'] = 1.0
            strategy['concession_rate'] = 0.1   # Moderate concessions
        elif approach_val == 'considerate':
            strategy['confidence_multiplier'] = 0.8
            strategy['concession_rate'] = 0.15  # Larger concessions
        
        # Timeline adjustments
        timeline_val = strategy['timeline']
        if timeline_val == 'urgent':
            strategy['max_rounds'] = 5
            strategy['urgency_factor'] = 1.3
        elif timeline_val == 'flexible':
            strategy['max_rounds'] = 12
            strategy['urgency_factor'] = 0.8
        else:  # week
            strategy['max_rounds'] = 8
            strategy['urgency_factor'] = 1.0
        
        logger.info(f"Strategy formulated: {strategy['approach']} approach with {strategy['success_probability']:.0f}% success probability")
        
        return strategy
    
    async def _check_intervention_triggers(
        self, 
        session_data: Dict[str, Any], 
        seller_message: str
    ) -> Optional[InterventionTrigger]:
        """
        Phase 5: Check if human intervention is needed
        """
        
        message_lower = seller_message.lower()
        session = session_data['session']
        
        # Check for explicit seller requests
        if any(phrase in message_lower for phrase in [
            'speak to you directly', 'call you', 'talk to owner', 'real person'
        ]):
            return InterventionTrigger.SELLER_REQUEST
        
        # Check for complex terms discussion
        if any(phrase in message_lower for phrase in [
            'warranty', 'return policy', 'legal', 'contract', 'documentation'
        ]):
            return InterventionTrigger.COMPLEX_TERMS
        
        # Check for deadlock (too many back-and-forth without progress)
        if len(session.messages) > 12:
            recent_prices = self._extract_recent_prices(session.messages[-6:])
            if recent_prices and len(set(recent_prices)) == 1:  # No price movement
                return InterventionTrigger.DEADLOCK
        
        # Check for technical issues
        if any(phrase in message_lower for phrase in [
            'not working', 'error', 'problem with', 'technical issue'
        ]):
            return InterventionTrigger.TECHNICAL_ISSUE
        
        return None
    
    async def _check_completion_conditions(
        self, 
        session_data: Dict[str, Any], 
        negotiation_result: Dict[str, Any]
    ) -> Optional[SessionOutcome]:
        """
        Phase 5: Check if negotiation should be completed
        """
        
        decision = negotiation_result.get('decision', {})
        action = decision.get('action')
        
        if action == 'accept':
            return SessionOutcome.SUCCESS
        elif action == 'walk_away':
            return SessionOutcome.FAILED_PRICE
        elif action == 'final_offer' and decision.get('confidence', 0) < 0.3:
            return SessionOutcome.FAILED_PRICE
        
        # Check message limits
        session = session_data['session']
        if len(session.messages) > 20:  # Too many messages without resolution
            return SessionOutcome.SELLER_UNRESPONSIVE
        
        return None
    
    async def _complete_session(self, session_id: str, outcome: SessionOutcome) -> Dict[str, Any]:
        """
        Phase 5: Complete negotiation session with analytics
        """
        
        session_data = self.active_sessions[session_id]
        session = session_data['session']
        
        # Update session
        session.status = SessionStatus.COMPLETED.value
        session.outcome = outcome.value
        session.ended_at = datetime.now()
        
        # Calculate final metrics
        final_metrics = await self.session_analytics.calculate_final_metrics(session_data)
        
        # Extract final price if successful
        if outcome == SessionOutcome.SUCCESS:
            final_price = self._extract_final_agreed_price(session.messages)
            session.final_price = final_price
        
        # Learning update
        await self.learning_engine.update_from_session(session_data, outcome, final_metrics)
        
        # Save final session
        await self.db.save_session(session)
        
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        logger.info(f"Session {session_id} completed with outcome: {outcome.value}")
        
        return {
            'session_completed': True,
            'outcome': outcome.value,
            'final_price': session.final_price,
            'metrics': final_metrics,
            'session_summary': await self._generate_session_summary(session_data)
        }
    
    async def _trigger_human_handoff(self, session_id: str, trigger: InterventionTrigger) -> Dict[str, Any]:
        """
        Phase 5: Trigger human handoff when needed
        """
        
        session_data = self.active_sessions[session_id]
        session = session_data['session']
        
        session.status = SessionStatus.HUMAN_HANDOFF.value
        session_data['intervention_triggers'].append({
            'trigger': trigger.value,
            'timestamp': datetime.now(),
            'message_count': len(session.messages)
        })
        
        # Generate handoff message
        handoff_messages = {
            InterventionTrigger.SELLER_REQUEST: "I understand you'd like to speak directly. Let me connect you with my colleague who can assist you better.",
            InterventionTrigger.COMPLEX_TERMS: "These are important details that need careful consideration. Let me have someone with more expertise help us.",
            InterventionTrigger.DEADLOCK: "Let me bring in a colleague who might have a fresh perspective on this negotiation.",
            InterventionTrigger.TECHNICAL_ISSUE: "I want to make sure we address your concerns properly. Let me connect you with someone who can help."
        }
        
        handoff_message = handoff_messages.get(trigger, "Let me connect you with a human colleague for better assistance.")
        
        # Create handoff message
        handoff_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            sender="ai",
            content=handoff_message,
            timestamp=datetime.now(),
            sender_type="handoff"
        )
        
        session.messages.append(handoff_msg)
        await self.db.save_session(session)
        
        return {
            'handoff_triggered': True,
            'trigger': trigger.value,
            'handoff_message': handoff_message,
            'session_status': session.status,
            'contact_info': await self._get_user_contact_info(session_id)
        }
    
    def _extract_recent_prices(self, messages: List[ChatMessage]) -> List[int]:
        """Extract prices mentioned in recent messages"""
        import re
        prices = []
        
        for msg in messages:
            price_matches = re.findall(r'₹[\s,]*(\d+(?:,\d+)*)', msg.content)
            for price_str in price_matches:
                try:
                    price = int(price_str.replace(',', ''))
                    prices.append(price)
                except ValueError:
                    continue
        
        return prices
    
    def _extract_final_agreed_price(self, messages: List[ChatMessage]) -> Optional[int]:
        """Extract final agreed price from successful negotiation"""
        # Look for acceptance messages and extract price
        for msg in reversed(messages):
            if msg.sender == "ai" and any(word in msg.content.lower() 
                                         for word in ['accept', 'deal', 'agree']):
                prices = self._extract_recent_prices([msg])
                if prices:
                    return prices[-1]
        return None
    
    async def _update_performance_metrics(self, session_data: Dict[str, Any], negotiation_result: Dict[str, Any]):
        """Update real-time performance metrics"""
        
        metrics = session_data['performance_metrics']
        decision = negotiation_result.get('decision', {})
        
        # Track price concessions
        if 'offer' in decision:
            current_offer = decision['offer']
            target_price = session_data['session'].user_params.target_price
            original_price = session_data['product'].price
            
            # Calculate negotiation progress
            total_gap = original_price - target_price
            current_gap = original_price - current_offer
            
            if total_gap > 0:
                progress = current_gap / total_gap
                metrics['negotiation_effectiveness'] = min(1.0, max(0.0, progress))
        
        # Track confidence trends
        confidence = negotiation_result.get('confidence', 0.5)
        if 'confidence_history' not in metrics:
            metrics['confidence_history'] = []
        metrics['confidence_history'].append(confidence)
    
    async def _handle_session_error(self, session_id: str, error_message: str):
        """Handle session errors gracefully"""
        
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            session = session_data['session']
            
            session.status = SessionStatus.FAILED.value
            session.outcome = SessionOutcome.TECHNICAL_ERROR.value
            session.ended_at = datetime.now()
            
            # Log error message
            error_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                sender="system",
                content=f"Session error: {error_message}",
                timestamp=datetime.now(),
                sender_type="error"
            )
            
            session.messages.append(error_msg)
            await self.db.save_session(session)
    
    async def _generate_session_summary(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive session summary"""
        
        session = session_data['session']
        product = session_data['product']
        
        return {
            'session_id': session.id,
            'product_title': product.title,
            'original_price': product.price,
            'target_price': session.user_params.target_price,
            'final_price': session.final_price,
            'duration_minutes': self._calculate_session_duration(session),
            'message_count': len(session.messages),
            'outcome': session.outcome,
            'negotiation_approach': session.user_params.approach.value if hasattr(session.user_params.approach, 'value') else session.user_params.approach,
            'key_tactics_used': session_data.get('tactics_history', []),
            'seller_personality_detected': session_data.get('seller_personality'),
            'market_position': session_data.get('market_analysis', {}).get('average_price')
        }
    
    def _calculate_session_duration(self, session: NegotiationSession) -> Optional[float]:
        """Calculate session duration in minutes"""
        if session.ended_at and session.created_at:
            duration = session.ended_at - session.created_at
            return duration.total_seconds() / 60
        return None
    
    async def _get_user_contact_info(self, session_id: str) -> Dict[str, str]:
        """Get user contact information for handoff"""
        # This would retrieve user contact details for human handoff
        return {
            'phone': 'Contact available in user profile',
            'email': 'user@example.com',
            'preferred_contact': 'phone'
        }


class SessionAnalytics:
    """Analytics engine for session performance measurement"""
    
    async def calculate_final_metrics(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive session metrics"""
        
        session = session_data['session']
        product = session_data['product']
        
        # Basic metrics
        metrics = {
            'session_duration_minutes': self._calculate_duration(session),
            'message_count': len(session.messages),
            'ai_message_count': len([m for m in session.messages if m.sender == 'ai']),
            'seller_message_count': len([m for m in session.messages if m.sender == 'seller'])
        }
        
        # Price negotiation metrics
        if session.final_price:
            savings = product.price - session.final_price
            savings_percentage = (savings / product.price) * 100
            target_achievement = ((product.price - session.final_price) / 
                                (product.price - session.user_params.target_price)) * 100
            
            metrics.update({
                'price_savings': savings,
                'savings_percentage': savings_percentage,
                'target_achievement_percentage': min(100, max(0, target_achievement))
            })
        
        # Efficiency metrics
        if metrics['message_count'] > 0:
            metrics['messages_per_minute'] = metrics['message_count'] / max(1, metrics['session_duration_minutes'])
        
        # Strategy effectiveness
        performance_data = session_data.get('performance_metrics', {})
        metrics['negotiation_effectiveness'] = performance_data.get('negotiation_effectiveness', 0.0)
        
        return metrics
    
    def _calculate_duration(self, session: NegotiationSession) -> float:
        """Calculate session duration in minutes"""
        if session.ended_at and session.created_at:
            duration = session.ended_at - session.created_at
            return duration.total_seconds() / 60
        return 0


class LearningEngine:
    """Machine learning engine for continuous improvement"""
    
    def __init__(self):
        self.learning_data_file = "learning_data.json"
    
    async def update_from_session(
        self, 
        session_data: Dict[str, Any], 
        outcome: SessionOutcome, 
        metrics: Dict[str, Any]
    ):
        """Update learning models from completed session"""
        
        try:
            # Extract learning features
            learning_record = {
                'timestamp': datetime.now().isoformat(),
                'outcome': outcome.value,
                'product_category': session_data['product'].category,
                'negotiation_approach': session_data['session'].user_params.approach.value if hasattr(session_data['session'].user_params.approach, 'value') else session_data['session'].user_params.approach,
                'price_gap': session_data['product'].price - session_data['session'].user_params.target_price,
                'market_position': self._calculate_market_position(session_data),
                'tactics_used': session_data.get('tactics_history', []),
                'seller_personality': session_data.get('seller_personality'),
                'metrics': metrics
            }
            
            # Save learning record
            await self._save_learning_record(learning_record)
            
            # Update strategy effectiveness scores
            await self._update_strategy_scores(learning_record)
            
        except Exception as e:
            logger.error(f"Error updating learning engine: {e}")
    
    def _calculate_market_position(self, session_data: Dict[str, Any]) -> str:
        """Calculate market position of the product"""
        
        product_price = session_data['product'].price
        market_analysis = session_data.get('market_analysis', {})
        avg_market_price = market_analysis.get('average_price')
        
        if not avg_market_price:
            return 'unknown'
        
        ratio = product_price / avg_market_price
        
        if ratio > 1.2:
            return 'overpriced'
        elif ratio < 0.8:
            return 'underpriced'
        else:
            return 'market_rate'
    
    async def _save_learning_record(self, record: Dict[str, Any]):
        """Save learning record to persistent storage"""
        
        try:
            # Load existing data
            try:
                with open(self.learning_data_file, 'r') as f:
                    learning_data = json.load(f)
            except FileNotFoundError:
                learning_data = []
            
            # Add new record
            learning_data.append(record)
            
            # Keep only last 1000 records
            if len(learning_data) > 1000:
                learning_data = learning_data[-1000:]
            
            # Save back
            with open(self.learning_data_file, 'w') as f:
                json.dump(learning_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving learning record: {e}")
    
    async def _update_strategy_scores(self, record: Dict[str, Any]):
        """Update effectiveness scores for different strategies"""
        
        # This would update ML models or rule-based scoring systems
        # For now, just log the update
        logger.info(f"Learning update: {record['outcome']} for approach {record['negotiation_approach']}")
    
    async def get_strategy_recommendations(self, product: Product, params: NegotiationParams) -> Dict[str, Any]:
        """Get AI-powered strategy recommendations based on learning"""
        
        try:
            # Load historical data
            with open(self.learning_data_file, 'r') as f:
                learning_data = json.load(f)
            
            # Filter similar scenarios
            similar_scenarios = [
                record for record in learning_data
                if (record['product_category'] == product.category and 
                    record['negotiation_approach'] == (params.approach.value if hasattr(params.approach, 'value') else params.approach))
            ]
            
            if similar_scenarios:
                # Calculate success rate
                successful = len([r for r in similar_scenarios if r['outcome'] == 'success'])
                success_rate = successful / len(similar_scenarios)
                
                # Find best performing tactics
                successful_records = [r for r in similar_scenarios if r['outcome'] == 'success']
                if successful_records:
                    tactics_frequency = {}
                    for record in successful_records:
                        for tactic in record.get('tactics_used', []):
                            tactics_frequency[tactic] = tactics_frequency.get(tactic, 0) + 1
                    
                    recommended_tactics = sorted(tactics_frequency.items(), 
                                               key=lambda x: x[1], reverse=True)[:3]
                    
                    return {
                        'success_rate': success_rate,
                        'recommended_tactics': [tactic for tactic, count in recommended_tactics],
                        'confidence': min(1.0, len(similar_scenarios) / 10),  # More data = higher confidence
                        'similar_scenarios_count': len(similar_scenarios)
                    }
            
            # Default recommendations
            return {
                'success_rate': 0.6,  # Default assumption
                'recommended_tactics': ['anchoring', 'reciprocity'],
                'confidence': 0.3,  # Low confidence without historical data
                'similar_scenarios_count': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting strategy recommendations: {e}")
            return {
                'success_rate': 0.5,
                'recommended_tactics': [],
                'confidence': 0.2,
                'similar_scenarios_count': 0
            }