import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Bot, User, TrendingUp, Target, DollarSign, Brain, ShoppingCart, RefreshCw, Zap, Shield } from 'lucide-react';

// Utility functions
const formatNumber = (num) => {
  return new Intl.NumberFormat('en-IN').format(num || 0);
};

// Toast notifications
const showToast = (message, type = 'info') => {
  // Simple toast implementation
  const toast = document.createElement('div');
  toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 ${
    type === 'success' ? 'bg-green-500' :
    type === 'error' ? 'bg-red-500' :
    type === 'warning' ? 'bg-yellow-500' :
    'bg-blue-500'
  }`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 4000);
};

// Custom hook for app state management
const useAppState = () => {
  const [state, setState] = useState({
    // Connection state
    isConnected: false,
    connectionStatus: 'disconnected',
    
    // Session state
    sessionId: null,
    isNegotiating: false,
    
    // Product data
    product: null,
    marketAnalysis: null,
    
    // Messages
    messages: [],
    
    // Form data
    formData: {
      productUrl: '',
      targetPrice: '',
      maxBudget: '',
      approach: 'diplomatic',
      timeline: 'flexible',
      specialRequirements: ''
    },
    
    // Metrics
    metrics: {
      negotiationProgress: 0,
      currentOffer: 0,
      savingsPotential: 0,
      aiConfidence: 'Medium'
    }
  });

  const updateState = useCallback((updates) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  const updateFormData = useCallback((updates) => {
    setState(prev => ({
      ...prev,
      formData: { ...prev.formData, ...updates }
    }));
  }, []);

  const updateMetrics = useCallback((updates) => {
    setState(prev => ({
      ...prev,
      metrics: { ...prev.metrics, ...updates }
    }));
  }, []);

  const addMessage = useCallback((message) => {
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, { ...message, id: Date.now(), timestamp: new Date() }]
    }));
  }, []);

  const reset = useCallback(() => {
    setState(prev => ({
      ...prev,
      isConnected: false,
      connectionStatus: 'disconnected',
      sessionId: null,
      isNegotiating: false,
      product: null,
      marketAnalysis: null,
      messages: [],
      metrics: {
        negotiationProgress: 0,
        currentOffer: 0,
        savingsPotential: 0,
        aiConfidence: 'Medium'
      }
    }));
  }, []);

  return { state, updateState, updateFormData, updateMetrics, addMessage, reset };
};

// WebSocket Hook
const useWebSocket = (sessionId, onMessage) => {
  const wsRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!sessionId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/user/${sessionId}`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
        onMessage({ type: 'system', content: 'Connected to AI negotiation assistant' });
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
        onMessage({ type: 'system', content: 'Connection lost. Please refresh the page.' });
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        onMessage({ type: 'system', content: 'Connection error occurred' });
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setIsConnected(false);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId, onMessage]);

  return { isConnected };
};

// API Service
const apiService = {
  async startNegotiation(data) {
    const response = await fetch('/api/negotiate-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  async startDemo(data) {
    const response = await fetch('/api/demo-negotiate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  async sendMessage(sessionId, message) {
    const response = await fetch('/api/seller-response', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        message: message
      })
    });
    return response.json();
  }
};

// Message Bubble Component
const MessageBubble = ({ message }) => {
  const getMessageStyles = () => {
    switch (message.type) {
      case 'ai':
      case 'ai_message':
        return {
          container: 'flex items-start gap-3 max-w-4xl mb-4',
          avatar: 'w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white',
          bubble: 'bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm flex-1',
          text: 'text-gray-900'
        };
      case 'user':
      case 'seller':
        return {
          container: 'flex items-start gap-3 max-w-4xl ml-auto flex-row-reverse mb-4',
          avatar: 'w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center text-white',
          bubble: 'bg-gray-100 border border-gray-200 rounded-2xl rounded-tr-sm px-4 py-3 flex-1',
          text: 'text-gray-900'
        };
      case 'system':
        return {
          container: 'flex items-center justify-center max-w-4xl mx-auto mb-4',
          avatar: 'w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm',
          bubble: 'bg-blue-50 border-blue-200 border rounded-lg px-4 py-3',
          text: 'text-blue-900 text-sm'
        };
      default:
        return {
          container: 'flex items-start gap-3 max-w-4xl mb-4',
          avatar: 'w-10 h-10 bg-gray-400 rounded-full flex items-center justify-center text-white',
          bubble: 'bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3 flex-1',
          text: 'text-gray-900'
        };
    }
  };

  const styles = getMessageStyles();

  return (
    <div className={`${styles.container} message`}>
      <div className={styles.avatar}>
        {message.type === 'ai' || message.type === 'ai_message' ? 
          <Bot className="w-5 h-5" /> : 
          message.type === 'system' ? 
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
          </svg> : 
          <User className="w-5 h-5" />
        }
      </div>
      
      <div className={styles.bubble}>
        <div className={styles.text}>
          {message.content || message.message}
        </div>
        
        <div className="text-xs text-gray-500 mt-2">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};

// Product Info Component
const ProductInfo = ({ product, isVisible }) => {
  if (!isVisible || !product) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mx-6 mt-6">
      <div className="p-6">
        <div className="flex items-start gap-4 mb-4">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center flex-shrink-0 text-white text-2xl">
            <ShoppingCart className="w-8 h-8" />
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">{product.title}</h3>
            
            <div className="text-2xl font-bold text-green-600 mb-3">
              ₹{formatNumber(product.price)}
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Platform:</span>
                <span className="font-medium">{product.platform || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Location:</span>
                <span className="font-medium">{product.location || 'Not specified'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Metrics Panel Component
const MetricsPanel = ({ metrics, product }) => {
  const targetPrice = product?.price || 0;
  const savings = Math.max(0, targetPrice - (metrics.currentOffer || 0));
  
  return (
    <div className="space-y-4">
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-4 h-4 text-gray-600" />
          <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
            Negotiation Progress
          </span>
        </div>
        
        <div className="text-lg font-bold text-gray-900 mb-2">
          {metrics.negotiationProgress}%
        </div>
        
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-300"
            style={{ width: `${metrics.negotiationProgress}%` }}
          />
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-gray-600" />
          <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
            Current Offer
          </span>
        </div>
        
        <div className="text-lg font-bold text-gray-900">
          ₹{formatNumber(metrics.currentOffer)}
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="flex items-center gap-2 mb-2">
          <DollarSign className="w-4 h-4 text-gray-600" />
          <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
            Potential Savings
          </span>
        </div>
        
        <div className="text-lg font-bold text-green-600">
          ₹{formatNumber(savings)}
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-4 h-4 text-gray-600" />
          <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
            AI Confidence
          </span>
        </div>
        
        <div className="text-lg font-bold text-gray-900">
          {metrics.aiConfidence}
        </div>
      </div>
    </div>
  );
};

// Chat Interface Component
const ChatInterface = ({ messages, isNegotiating, onSendMessage, sessionId }) => {
  const [messageInput, setMessageInput] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!messageInput.trim() || !sessionId) return;
    
    const message = messageInput.trim();
    setMessageInput('');
    
    // Add user message immediately
    onSendMessage({ type: 'user', content: message });
    
    try {
      await apiService.sendMessage(sessionId, message);
    } catch (error) {
      console.error('Error sending message:', error);
      onSendMessage({ type: 'system', content: 'Failed to send message. Please try again.' });
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isNegotiating && messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-24 h-24 bg-gradient-to-br from-blue-100 to-blue-200 rounded-full flex items-center justify-center mx-auto mb-6">
            <Bot className="w-12 h-12 text-blue-600" />
          </div>
          
          <h3 className="text-xl font-semibold text-gray-900 mb-3">
            Ready to Start Negotiating
          </h3>
          
          <p className="text-gray-600 leading-relaxed">
            Configure your negotiation parameters in the sidebar and start your AI-powered marketplace negotiation session.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto scrollbar-hide p-6">
        {messages.map((message, index) => (
          <MessageBubble key={message.id || index} message={message} />
        ))}
        
        <div ref={messagesEndRef} />
      </div>
      
      {isNegotiating && (
        <div className="border-t border-gray-200 p-4 bg-white">
          <div className="flex gap-3">
            <textarea
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              placeholder="Type your message or let AI handle the negotiation..."
              rows={2}
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyPress={handleKeyPress}
            />
            
            <button
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              onClick={handleSendMessage}
              disabled={!messageInput.trim()}
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Sidebar Component
const Sidebar = ({ formData, onFormDataChange, onStartNegotiation, onStartDemo, onReset, isNegotiating, sessionId, onCopySessionId }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.productUrl || !formData.targetPrice || !formData.maxBudget) {
      showToast('Please fill in all required fields', 'error');
      return;
    }

    if (parseInt(formData.targetPrice) >= parseInt(formData.maxBudget)) {
      showToast('Target price must be less than maximum budget', 'error');
      return;
    }

    setIsLoading(true);
    try {
      await onStartNegotiation({
        product_url: formData.productUrl,
        target_price: parseInt(formData.targetPrice),
        max_budget: parseInt(formData.maxBudget),
        approach: formData.approach,
        timeline: formData.timeline,
        special_requirements: formData.specialRequirements || undefined
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemo = async () => {
    const targetPrice = parseInt(formData.targetPrice) || 40000;
    const maxBudget = parseInt(formData.maxBudget) || 60000;

    if (targetPrice >= maxBudget) {
      showToast('Target price must be less than maximum budget', 'error');
      return;
    }

    setIsLoading(true);
    try {
      await onStartDemo({
        product_url: 'demo://laptop-macbook-air-m2',
        target_price: targetPrice,
        max_budget: maxBudget,
        approach: formData.approach,
        timeline: formData.timeline,
        special_requirements: formData.specialRequirements || 'Demo negotiation'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-96 bg-gradient-to-b from-gray-800 to-gray-900 text-white flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-700">
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1 flex items-center gap-3">
            <Bot className="w-8 h-8 text-blue-400" />
            NegotiBot AI
          </h1>
          <p className="text-gray-400 text-sm">Professional Negotiation Assistant</p>
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto scrollbar-hide p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="text-lg font-semibold mb-4">New Negotiation</div>

          {/* Product URL */}
          <div>
            <label className="block text-sm font-medium mb-2">Marketplace URL</label>
            <input
              type="url"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400"
              placeholder="Paste product URL from OLX, Facebook Marketplace, etc."
              value={formData.productUrl}
              onChange={(e) => onFormDataChange({ productUrl: e.target.value })}
              disabled={isNegotiating || isLoading}
              required
            />
          </div>

          {/* Price fields */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Target Price (₹)</label>
              <input
                type="number"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400"
                placeholder="50,000"
                min="1"
                value={formData.targetPrice}
                onChange={(e) => onFormDataChange({ targetPrice: e.target.value })}
                disabled={isNegotiating || isLoading}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Budget (₹)</label>
              <input
                type="number"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400"
                placeholder="70,000"
                min="1"
                value={formData.maxBudget}
                onChange={(e) => onFormDataChange({ maxBudget: e.target.value })}
                disabled={isNegotiating || isLoading}
                required
              />
            </div>
          </div>

          {/* Negotiation Style */}
          <div>
            <label className="block text-sm font-medium mb-2">Negotiation Style</label>
            <select
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white"
              value={formData.approach}
              onChange={(e) => onFormDataChange({ approach: e.target.value })}
              disabled={isNegotiating || isLoading}
            >
              <option value="diplomatic">Diplomatic - Balanced & Professional</option>
              <option value="assertive">Assertive - Direct & Confident</option>
              <option value="considerate">Considerate - Empathetic & Budget-conscious</option>
            </select>
          </div>

          {/* Timeline */}
          <div>
            <label className="block text-sm font-medium mb-2">Purchase Timeline</label>
            <select
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white"
              value={formData.timeline}
              onChange={(e) => onFormDataChange({ timeline: e.target.value })}
              disabled={isNegotiating || isLoading}
            >
              <option value="flexible">Flexible - No specific timeline</option>
              <option value="week">Within a week</option>
              <option value="urgent">Urgent - ASAP</option>
            </select>
          </div>

          {/* Special Requirements */}
          <div>
            <label className="block text-sm font-medium mb-2">Additional Requirements</label>
            <input
              type="text"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400"
              placeholder="Warranty, delivery, accessories (optional)"
              value={formData.specialRequirements}
              onChange={(e) => onFormDataChange({ specialRequirements: e.target.value })}
              disabled={isNegotiating || isLoading}
            />
          </div>

          {/* Buttons */}
          <div className="space-y-3">
            <button
              type="submit"
              className={`w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center justify-center gap-2 ${(isNegotiating || isLoading) ? 'opacity-50 cursor-not-allowed' : ''}`}
              disabled={isNegotiating || isLoading}
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <span>Analyze Product & Start Negotiation</span>
              )}
            </button>

            <button
              type="button"
              className={`w-full px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 ${(isNegotiating || isLoading) ? 'opacity-50 cursor-not-allowed' : ''}`}
              onClick={handleDemo}
              disabled={isNegotiating || isLoading}
            >
              Try Demo Mode (No URL Required)
            </button>

            {isNegotiating && (
              <button
                type="button"
                className="w-full px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-all duration-200"
                onClick={onReset}
              >
                Reset Session
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Session Status */}
      {sessionId && (
        <div className="p-4 bg-gray-800 border-t border-gray-700">
          <div className="text-sm">
            <div className="font-medium text-blue-400 mb-1">Session Active</div>
            <div className="text-gray-300 mb-2 break-all">
              Session ID: {sessionId}
            </div>
            <button
              onClick={onCopySessionId}
              className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors duration-200"
            >
              Copy Session ID
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Main App Component
function AppSelfContained() {
  const { 
    state, 
    updateState, 
    updateFormData, 
    updateMetrics, 
    addMessage, 
    reset 
  } = useAppState();

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'ai_message':
      case 'negotiation_update':
        addMessage({
          type: 'ai',
          content: data.message,
          phase: data.phase,
          strategy: data.strategy
        });
        
        // Update metrics if available
        if (data.progress !== undefined || data.current_offer !== undefined) {
          updateMetrics({
            negotiationProgress: data.progress || state.metrics.negotiationProgress,
            currentOffer: data.current_offer || state.metrics.currentOffer,
            aiConfidence: data.confidence || state.metrics.aiConfidence
          });
        }
        break;

      case 'seller_message':
        addMessage({
          type: 'seller',
          content: data.message
        });
        break;

      case 'negotiation_complete':
        updateState({ isNegotiating: false });
        addMessage({
          type: 'system',
          content: data.message || 'Negotiation completed!',
          success: data.success,
          finalPrice: data.final_price
        });
        
        if (data.success) {
          showToast(`Negotiation successful! Final price: ₹${formatNumber(data.final_price)}`, 'success');
        } else {
          showToast('Negotiation was not successful', 'warning');
        }
        break;

      case 'system':
        addMessage(data);
        break;

      default:
        if (data.content || data.message) {
          addMessage(data);
        }
        console.log('Unknown message type:', data.type);
    }
  }, [addMessage, updateState, updateMetrics, state.metrics]);

  const { isConnected } = useWebSocket(state.sessionId, handleWebSocketMessage);

  useEffect(() => {
    updateState({ isConnected });
  }, [isConnected, updateState]);

  // Handle start negotiation
  const handleStartNegotiation = async (negotiationData) => {
    try {
      updateState({ connectionStatus: 'connecting' });
      
      const response = await apiService.startNegotiation(negotiationData);

      if (response.success) {
        updateState({
          sessionId: response.session.session_id,
          product: response.product_info,
          marketAnalysis: response.market_analysis,
          isNegotiating: true
        });

        // Initialize metrics
        const product = response.product_info;
        updateMetrics({
          currentOffer: product.price,
          savingsPotential: Math.max(0, product.price - negotiationData.target_price),
          aiConfidence: 'High'
        });
        
        showToast('Negotiation started successfully!', 'success');
      } else {
        showToast(response.message || 'Failed to start negotiation', 'error');
      }
    } catch (error) {
      console.error('Error starting negotiation:', error);
      showToast(error.message || 'Failed to start negotiation', 'error');
      updateState({ connectionStatus: 'error' });
    }
  };

  // Handle start demo
  const handleStartDemo = async (demoData) => {
    try {
      updateState({ connectionStatus: 'connecting' });
      
      const response = await apiService.startDemo(demoData);

      if (response.success) {
        updateState({
          sessionId: response.session.session_id,
          product: response.product_info,
          marketAnalysis: response.market_analysis,
          isNegotiating: true
        });

        // Initialize metrics
        const product = response.product_info;
        updateMetrics({
          currentOffer: product.price,
          savingsPotential: Math.max(0, product.price - demoData.target_price),
          aiConfidence: 'High'
        });
        
        showToast('Demo negotiation started successfully!', 'success');
      } else {
        showToast('Failed to start demo negotiation', 'error');
      }
    } catch (error) {
      console.error('Error starting demo:', error);
      showToast('Failed to start demo negotiation', 'error');
      updateState({ connectionStatus: 'error' });
    }
  };

  // Handle reset
  const handleReset = () => {
    if (window.confirm('Are you sure you want to reset the current session?')) {
      reset();
      showToast('Session reset successfully', 'success');
    }
  };

  const copySessionId = async () => {
    if (state.sessionId) {
      try {
        await navigator.clipboard.writeText(state.sessionId);
        showToast('Session ID copied to clipboard!', 'success');
      } catch (err) {
        showToast('Failed to copy session ID', 'error');
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="flex h-screen max-w-7xl mx-auto bg-white shadow-2xl">
        {/* Sidebar */}
        <Sidebar
          formData={state.formData}
          onFormDataChange={updateFormData}
          onStartNegotiation={handleStartNegotiation}
          onStartDemo={handleStartDemo}
          onReset={handleReset}
          isNegotiating={state.isNegotiating}
          sessionId={state.sessionId}
          onCopySessionId={copySessionId}
        />

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="bg-white border-b border-gray-200 px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                  <div className="p-2 bg-blue-600 rounded-lg text-white text-xl">
                    <Bot className="w-6 h-6" />
                  </div>
                  NegotiBot AI
                </h1>
                
                <p className="text-gray-600 mt-1">
                  {state.isNegotiating ? 
                    `Negotiating ${state.product?.title || 'product'}` : 
                    'Ready to start your next negotiation'
                  }
                </p>
              </div>
              
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-500" />
                  <span>AI-Powered</span>
                </div>
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-green-500" />
                  <span>Secure</span>
                </div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-blue-500" />
                  <span>Smart Analytics</span>
                </div>
              </div>
            </div>
          </header>

          {/* Content Area */}
          <div className="flex-1 flex overflow-hidden">
            {/* Chat Interface */}
            <div className="flex-1 flex flex-col">
              <ProductInfo
                product={state.product}
                isVisible={!!state.product}
              />
              
              <ChatInterface
                messages={state.messages}
                isNegotiating={state.isNegotiating}
                onSendMessage={addMessage}
                sessionId={state.sessionId}
              />
            </div>

            {/* Analytics Panel */}
            {state.isNegotiating && (
              <div className="w-80 border-l border-gray-200 bg-white overflow-y-auto">
                <div className="p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Product Analysis</h3>
                  <p className="text-sm text-gray-600">Market intelligence & insights</p>
                </div>

                <div className="p-6">
                  <MetricsPanel
                    metrics={state.metrics}
                    product={state.product}
                  />
                </div>
              </div>
            )}
          </div>
          
          {/* Footer */}
          <footer className="bg-gray-50 border-t border-gray-200 px-8 py-4">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <div>© 2025 NegotiBot AI. Professional marketplace negotiation assistant.</div>
              
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                <span>{isConnected ? 'Connected' : 'System Online'}</span>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default AppSelfContained;