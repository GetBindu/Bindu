import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Bot, User, TrendingUp, Target, DollarSign, Brain, ShoppingCart, RefreshCw, Zap, Shield, LogOut } from 'lucide-react';

// Theme configuration matching index.html
const theme = {
  colors: {
    primary: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
    },
    secondary: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
    accent: {
      50: '#ecfeff',
      100: '#cffafe',
      200: '#a5f3fc',
      300: '#67e8f9',
      400: '#22d3ee',
      500: '#06b6d4',
      600: '#0891b2',
      700: '#0e7490',
      800: '#155e75',
      900: '#164e63',
    },
    success: {
      50: '#f0fdf4',
      100: '#dcfce7',
      200: '#bbf7d0',
      300: '#86efac',
      400: '#4ade80',
      500: '#22c55e',
      600: '#16a34a',
      700: '#15803d',
      800: '#166534',
      900: '#14532d',
    }
  }
};

// Utility functions
const formatNumber = (num) => {
  return new Intl.NumberFormat('en-IN').format(num || 0);
};

// Toast notifications with theme
const showToast = (message, type = 'info') => {
  const toast = document.createElement('div');
  const colors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
  };
  
  toast.className = `fixed top-4 right-4 px-6 py-3 rounded-xl text-white z-50 ${colors[type]} shadow-2xl backdrop-blur-sm`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
    }
  }, 4000);
};

// Session management
const getStoredSession = () => {
  try {
    const session = localStorage.getItem('negotiation_session');
    return session ? JSON.parse(session) : null;
  } catch {
    return null;
  }
};

const storeSession = (sessionData) => {
  try {
    localStorage.setItem('negotiation_session', JSON.stringify(sessionData));
  } catch (e) {
    console.warn('Failed to store session:', e);
  }
};

const clearSession = () => {
  try {
    localStorage.removeItem('negotiation_session');
  } catch (e) {
    console.warn('Failed to clear session:', e);
  }
};

// Custom hook for app state management
const useAppState = () => {
  const [state, setState] = useState({
    // User session
    user: getStoredSession(),
    
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

  const logout = useCallback(() => {
    clearSession();
    setState(prev => ({
      ...prev,
      user: null,
      isConnected: false,
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
    // Redirect to landing page
    window.location.href = '/';
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

  return {
    state,
    updateState,
    updateFormData,
    updateMetrics,
    addMessage,
    logout,
    reset
  };
};

// Header component with consistent theme
const Header = ({ user, onLogout }) => {
  return (
    <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-blue-900 border-b border-blue-500/20 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                NegotiBot AI
              </h1>
              <p className="text-xs text-slate-400">Buyer Portal</p>
            </div>
          </div>

          {/* User info and logout */}
          {user && (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-white">{user.full_name || user.username}</p>
                <p className="text-xs text-slate-400">{user.email}</p>
              </div>
              <button
                onClick={onLogout}
                className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 text-slate-300 hover:text-white rounded-lg transition-all duration-200 border border-slate-600/50"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm">Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Main App Component
function AppSelfContained() {
  const { state, updateState, updateFormData, updateMetrics, addMessage, logout, reset } = useAppState();
  const wsRef = useRef(null);
  const chatContainerRef = useRef(null);

  // Check for user session on mount
  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      // Redirect to landing page if no session
      window.location.href = '/';
      return;
    }
    updateState({ user: storedSession });
  }, []);

  // WebSocket connection logic
  const connectWebSocket = useCallback((sessionId) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `ws://localhost:8000/ws/user/${sessionId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    wsRef.current = new WebSocket(wsUrl);
    
    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
      updateState({ isConnected: true, connectionStatus: 'connected' });
      showToast('Connected to negotiation session', 'success');
    };
    
    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        if (data.type === 'ai_response') {
          addMessage({
            sender: 'ai',
            content: data.message,
            timestamp: new Date(),
            confidence: data.confidence,
            tactics: data.tactics_used
          });
          
          if (data.metrics) {
            updateMetrics(data.metrics);
          }
        } else if (data.type === 'seller_message') {
          addMessage({
            sender: 'seller',
            content: data.message,
            timestamp: new Date()
          });
        } else if (data.type === 'status') {
          updateState({ connectionStatus: data.message });
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected');
      updateState({ isConnected: false, connectionStatus: 'disconnected' });
    };
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      updateState({ isConnected: false, connectionStatus: 'error' });
      showToast('Connection error occurred', 'error');
    };
  }, [updateState, addMessage, updateMetrics]);

  // Start negotiation
  const startNegotiation = async () => {
    if (!state.formData.productUrl || !state.formData.targetPrice || !state.formData.maxBudget) {
      showToast('Please fill in all required fields', 'warning');
      return;
    }

    if (parseInt(state.formData.targetPrice) >= parseInt(state.formData.maxBudget)) {
      showToast('Target price must be less than maximum budget', 'warning');
      return;
    }

    try {
      updateState({ isNegotiating: true });
      showToast('Starting negotiation session...', 'info');

      const response = await fetch('/api/negotiate-url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.user?.token || ''}`
        },
        body: JSON.stringify({
          product_url: state.formData.productUrl,
          target_price: parseInt(state.formData.targetPrice),
          max_budget: parseInt(state.formData.maxBudget),
          approach: state.formData.approach,
          timeline: state.formData.timeline,
          special_requirements: state.formData.specialRequirements
        })
      });

      const data = await response.json();

      if (response.ok && data.session_id) {
        updateState({
          sessionId: data.session_id,
          product: data.product,
          marketAnalysis: data.market_analysis,
          isNegotiating: true
        });

        // Connect WebSocket
        connectWebSocket(data.session_id);

        // Add initial message
        addMessage({
          sender: 'system',
          content: `Negotiation session started for ${data.product?.title || 'product'}. AI agent is analyzing the market and preparing initial strategy.`,
          timestamp: new Date()
        });

        showToast('Negotiation session started successfully!', 'success');
      } else {
        throw new Error(data.message || 'Failed to start negotiation');
      }
    } catch (error) {
      console.error('Error starting negotiation:', error);
      showToast('Failed to start negotiation: ' + error.message, 'error');
      updateState({ isNegotiating: false });
    }
  };

  // Auto-scroll chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [state.messages]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Render login redirect if no user
  if (!state.user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Authentication Required</h2>
          <p className="text-slate-400 mb-6">Please log in to access the buyer portal</p>
          <button
            onClick={() => window.location.href = '/'}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-xl hover:from-blue-700 hover:to-cyan-700 transition-all duration-200"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900">
      <Header user={state.user} onLogout={logout} />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Panel - Negotiation Setup */}
          <div className="lg:col-span-1">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-600/50 p-6 shadow-2xl">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
                  <ShoppingCart className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-xl font-bold text-white">Negotiation Setup</h2>
              </div>

              <div className="space-y-4">
                {/* Product URL */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Product URL *
                  </label>
                  <input
                    type="url"
                    value={state.formData.productUrl}
                    onChange={(e) => updateFormData({ productUrl: e.target.value })}
                    placeholder="https://www.olx.in/item/..."
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200"
                    disabled={state.isNegotiating}
                  />
                </div>

                {/* Target Price */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Target Price (₹) *
                  </label>
                  <input
                    type="number"
                    value={state.formData.targetPrice}
                    onChange={(e) => updateFormData({ targetPrice: e.target.value })}
                    placeholder="45000"
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200"
                    disabled={state.isNegotiating}
                  />
                </div>

                {/* Max Budget */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Maximum Budget (₹) *
                  </label>
                  <input
                    type="number"
                    value={state.formData.maxBudget}
                    onChange={(e) => updateFormData({ maxBudget: e.target.value })}
                    placeholder="55000"
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200"
                    disabled={state.isNegotiating}
                  />
                </div>

                {/* Approach */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Negotiation Approach
                  </label>
                  <select
                    value={state.formData.approach}
                    onChange={(e) => updateFormData({ approach: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200"
                    disabled={state.isNegotiating}
                  >
                    <option value="diplomatic">Diplomatic</option>
                    <option value="assertive">Assertive</option>
                    <option value="considerate">Considerate</option>
                  </select>
                </div>

                {/* Timeline */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Purchase Timeline
                  </label>
                  <select
                    value={state.formData.timeline}
                    onChange={(e) => updateFormData({ timeline: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200"
                    disabled={state.isNegotiating}
                  >
                    <option value="flexible">Flexible</option>
                    <option value="week">Within a week</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>

                {/* Special Requirements */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Special Requirements
                  </label>
                  <textarea
                    value={state.formData.specialRequirements}
                    onChange={(e) => updateFormData({ specialRequirements: e.target.value })}
                    placeholder="Any specific requirements or conditions..."
                    rows={3}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-200 resize-none"
                    disabled={state.isNegotiating}
                  />
                </div>

                {/* Start Button */}
                <button
                  onClick={startNegotiation}
                  disabled={state.isNegotiating}
                  className="w-full px-6 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 disabled:from-slate-600 disabled:to-slate-600 text-white rounded-xl font-semibold transition-all duration-200 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
                >
                  {state.isNegotiating ? (
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Negotiating...
                    </div>
                  ) : (
                    <div className="flex items-center justify-center gap-2">
                      <Zap className="w-5 h-5" />
                      Start AI Negotiation
                    </div>
                  )}
                </button>

                {/* Reset Button */}
                {state.sessionId && (
                  <button
                    onClick={reset}
                    className="w-full px-6 py-3 bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 hover:text-white rounded-xl font-medium transition-all duration-200 border border-slate-600/50"
                  >
                    Reset Session
                  </button>
                )}
              </div>
            </div>

            {/* Product Info */}
            {state.product && (
              <div className="mt-6 bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-600/50 p-6 shadow-2xl">
                <h3 className="text-lg font-bold text-white mb-4">Product Information</h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-slate-400">Title</p>
                    <p className="text-white font-medium">{state.product.title}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Listed Price</p>
                    <p className="text-xl font-bold text-green-400">₹{formatNumber(state.product.price)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Location</p>
                    <p className="text-white">{state.product.location}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Platform</p>
                    <p className="text-white">{state.product.platform}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel - Chat and Metrics */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Connection Status */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-600/50 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${
                    state.isConnected ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                  <span className="text-sm font-medium text-white">
                    {state.isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="text-sm text-slate-400">
                  {state.sessionId ? `Session: ${state.sessionId.slice(0, 8)}...` : 'No active session'}
                </div>
              </div>
            </div>

            {/* Metrics */}
            {state.sessionId && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-600/50 p-4 text-center">
                  <div className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <TrendingUp className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{state.metrics.negotiationProgress}%</div>
                  <div className="text-xs text-slate-400">Progress</div>
                </div>
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-600/50 p-4 text-center">
                  <div className="w-8 h-8 bg-green-500/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Target className="w-4 h-4 text-green-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">₹{formatNumber(state.metrics.currentOffer)}</div>
                  <div className="text-xs text-slate-400">Current Offer</div>
                </div>
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-600/50 p-4 text-center">
                  <div className="w-8 h-8 bg-yellow-500/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <DollarSign className="w-4 h-4 text-yellow-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">₹{formatNumber(state.metrics.savingsPotential)}</div>
                  <div className="text-xs text-slate-400">Savings</div>
                </div>
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-600/50 p-4 text-center">
                  <div className="w-8 h-8 bg-purple-500/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{state.metrics.aiConfidence}</div>
                  <div className="text-xs text-slate-400">AI Confidence</div>
                </div>
              </div>
            )}

            {/* Chat Interface */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-600/50 shadow-2xl">
              <div className="border-b border-slate-600/50 p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-blue-500 rounded-lg flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">AI Negotiation Chat</h3>
                    <p className="text-sm text-slate-400">Watch your AI agent negotiate in real-time</p>
                  </div>
                </div>
              </div>

              <div className="h-96 flex flex-col">
                {/* Messages */}
                <div 
                  ref={chatContainerRef}
                  className="flex-1 overflow-y-auto p-4 space-y-4"
                >
                  {state.messages.length === 0 ? (
                    <div className="text-center py-12">
                      <div className="w-16 h-16 bg-slate-700/50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <Bot className="w-8 h-8 text-slate-400" />
                      </div>
                      <p className="text-slate-400">Start a negotiation to see AI messages here</p>
                    </div>
                  ) : (
                    state.messages.map((message) => (
                      <div key={message.id} className={`flex gap-3 ${
                        message.sender === 'ai' ? 'justify-start' : 
                        message.sender === 'seller' ? 'justify-end' : 'justify-center'
                      }`}>
                        {message.sender === 'ai' && (
                          <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4 text-white" />
                          </div>
                        )}
                        {message.sender === 'seller' && (
                          <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-teal-500 rounded-lg flex items-center justify-center flex-shrink-0 order-2">
                            <User className="w-4 h-4 text-white" />
                          </div>
                        )}
                        <div className={`max-w-lg ${
                          message.sender === 'ai' ? 'bg-slate-700/50' :
                          message.sender === 'seller' ? 'bg-green-600/20 border border-green-500/30' :
                          'bg-blue-600/20 border border-blue-500/30'
                        } rounded-xl p-3 backdrop-blur-sm`}>
                          <p className="text-white text-sm leading-relaxed">{message.content}</p>
                          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-600/30">
                            <span className="text-xs text-slate-400">
                              {message.timestamp.toLocaleTimeString()}
                            </span>
                            {message.confidence && (
                              <span className="text-xs text-blue-400">
                                Confidence: {Math.round(message.confidence * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AppSelfContained;