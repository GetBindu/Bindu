import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  MessageSquare, 
  Send, 
  Users, 
  Clock, 
  DollarSign,
  TrendingUp,
  Search,
  Filter,
  MoreVertical,
  CheckCircle,
  AlertCircle,
  User,
  Bot,
  Hash
} from 'lucide-react'
import toast from 'react-hot-toast'

const SellerPortal = ({ user, onLogout }) => {
  const [activeSessionId, setActiveSessionId] = useState('')
  const [sessions, setSessions] = useState([])
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [sessionDetails, setSessionDetails] = useState(null)
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)

  // Connect to session
  const connectToSession = async () => {
    if (!activeSessionId.trim()) {
      toast.error('Please enter a valid session ID')
      return
    }

    setIsLoading(true)
    try {
      // Validate session exists
      const response = await fetch(`/api/sessions/${activeSessionId}`)
      const data = await response.json()

      if (data.success) {
        // Debug: Log the entire response
        console.log('Session API response:', data)
        console.log('User params:', data.session?.user_params)
        
        // Connect to WebSocket
        const wsUrl = `ws://localhost:8000/ws/seller/${activeSessionId}`
        wsRef.current = new WebSocket(wsUrl)

        wsRef.current.onopen = () => {
          setIsConnected(true)
          const sessionData = {
            session: data.session,
            product: data.product,
            market_analysis: data.market_analysis,
            strategy: data.strategy
          }
          setSessionDetails(sessionData)
          
          // Debug logging
          console.log('Session Details Set:', sessionData)
          console.log('User Params:', data.session?.user_params)
          
          toast.success(`Connected to session ${activeSessionId}`)
        }

        wsRef.current.onmessage = (event) => {
          const data = JSON.parse(event.data)
          setMessages(prev => [...prev, {
            id: Date.now(),
            content: data.message,
            sender: data.sender || 'buyer',
            timestamp: new Date(),
            type: data.type || 'text'
          }])
        }

        wsRef.current.onclose = () => {
          setIsConnected(false)
          toast.info('Disconnected from session')
        }

        wsRef.current.onerror = () => {
          toast.error('Connection error')
          setIsConnected(false)
        }

        // Add to active sessions
        setSessions(prev => {
          const exists = prev.find(s => s.id === activeSessionId)
          if (!exists) {
            return [...prev, {
              id: activeSessionId,
              buyerName: data.session.buyer_name || 'Anonymous Buyer',
              productName: data.session.product_name || 'Product',
              status: 'active',
              lastActivity: new Date(),
              messageCount: 0
            }]
          }
          return prev
        })

      } else {
        toast.error('Invalid session ID')
      }
    } catch (error) {
      console.error('Connection error:', error)
      toast.error('Failed to connect to session')
    } finally {
      setIsLoading(false)
    }
  }

  // Send message
  const sendMessage = () => {
    if (!newMessage.trim() || !isConnected) return

    const message = {
      type: 'seller_message',
      message: newMessage,
      sender: 'seller',
      timestamp: new Date().toISOString()
    }

    wsRef.current.send(JSON.stringify(message))
    
    setMessages(prev => [...prev, {
      id: Date.now(),
      content: newMessage,
      sender: 'seller',
      timestamp: new Date(),
      type: 'text'
    }])

    setNewMessage('')
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return (
    <div className="h-screen bg-gradient-to-br from-dark-950 via-dark-900 to-primary-950 flex">
      {/* Sidebar */}
      <div className="w-80 bg-gradient-to-b from-dark-900 to-dark-800 border-r border-primary-800/30 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-primary-700/30">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-accent-500 to-primary-500 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-xl text-white">Seller Portal</h2>
              <p className="text-gray-400 text-sm">Welcome, {user?.name}</p>
            </div>
          </div>

          {/* Session Connection */}
          <div className="space-y-3">
            <div className="relative">
              <Hash className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                value={activeSessionId}
                onChange={(e) => setActiveSessionId(e.target.value)}
                placeholder="Enter session ID..."
                className="w-full pl-10 pr-4 py-3 bg-dark-800/50 border border-primary-600/30 rounded-lg focus:ring-2 focus:ring-primary-500 text-white placeholder-gray-400 text-sm"
              />
            </div>
            <motion.button
              onClick={connectToSession}
              disabled={isLoading || !activeSessionId.trim()}
              className={`w-full px-4 py-3 bg-gradient-to-r from-primary-600 to-accent-600 text-white font-medium rounded-lg transition-all duration-300 flex items-center justify-center gap-2 ${
                (isLoading || !activeSessionId.trim()) ? 'opacity-50 cursor-not-allowed' : 'hover:from-primary-500 hover:to-accent-500'
              }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <MessageSquare className="w-4 h-4" />
                  Connect to Session
                </>
              )}
            </motion.button>
          </div>
        </div>

        {/* Active Sessions */}
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Active Sessions ({sessions.length})
          </h3>
          
          <div className="space-y-2">
            {sessions.map((session) => (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3 bg-white/5 rounded-lg border border-primary-700/20 cursor-pointer hover:bg-white/10 transition-all ${
                  activeSessionId === session.id ? 'ring-2 ring-primary-500' : ''
                }`}
                onClick={() => setActiveSessionId(session.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white text-sm font-medium">{session.buyerName}</span>
                  <div className={`w-2 h-2 rounded-full ${
                    session.status === 'active' ? 'bg-green-500' : 'bg-gray-500'
                  }`} />
                </div>
                <p className="text-gray-400 text-xs truncate">{session.productName}</p>
                <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                  <span>#{session.id.slice(0, 8)}</span>
                  <span>{session.messageCount} messages</span>
                </div>
              </motion.div>
            ))}
            
            {sessions.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No active sessions</p>
                <p className="text-xs">Connect to a session to start chatting</p>
              </div>
            )}
          </div>
        </div>

        {/* Logout */}
        <div className="p-4 border-t border-primary-700/30">
          <button
            onClick={onLogout}
            className="w-full px-4 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-all text-sm"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex">
        {isConnected ? (
          <>
            {/* Session Details Panel */}
            <div className="w-80 bg-gradient-to-b from-dark-800 to-dark-700 border-r border-primary-700/30 flex flex-col">
              {/* Session Header */}
              <div className="p-4 border-b border-primary-700/30">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                    <User className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Session #{activeSessionId.slice(0, 8)}</h3>
                    <p className="text-gray-400 text-sm flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      Connected
                    </p>
                  </div>
                </div>
              </div>



              {/* Product Details */}
              {sessionDetails?.product && (
                <div className="p-4 border-b border-primary-700/30">
                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Product Details
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-400">Product Name</p>
                      <p className="text-white font-medium text-sm truncate" title={sessionDetails.product.title || 'No title available'}>
                        {sessionDetails.product.title || 'No title available'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Listed Price</p>
                      <p className="text-green-400 font-bold">
                        {sessionDetails.product.price ? 
                          `₹${sessionDetails.product.price.toLocaleString()}` : 
                          'Price not available'
                        }
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Condition</p>
                      <p className="text-white text-sm">{sessionDetails.product.condition || 'Not specified'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Location</p>
                      <p className="text-white text-sm">{sessionDetails.product.location || 'Not specified'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Platform</p>
                      <p className="text-white text-sm capitalize">{sessionDetails.product.platform || 'Not specified'}</p>
                    </div>
                  </div>
                </div>
              )}



              {/* Buyer Information */}
              {sessionDetails?.session && (
                <div className="p-4 border-b border-primary-700/30">
                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Buyer Information
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-400">Target Price</p>
                      <p className="text-primary-400 font-bold">
                        {(() => {
                          const userParams = sessionDetails.session.user_params;
                          const targetPrice = userParams?.target_price;
                          return targetPrice ? `₹${targetPrice.toLocaleString()}` : 'Not specified';
                        })()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Maximum Budget</p>
                      <p className="text-accent-400 font-bold">
                        {(() => {
                          const userParams = sessionDetails.session.user_params;
                          const maxBudget = userParams?.max_budget;
                          return maxBudget ? `₹${maxBudget.toLocaleString()}` : 'Not specified';
                        })()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Approach</p>
                      <p className="text-white text-sm capitalize">
                        {sessionDetails.session.user_params?.approach || 'Not specified'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Timeline</p>
                      <p className="text-white text-sm capitalize">
                        {sessionDetails.session.user_params?.timeline || 'Flexible'}
                      </p>
                    </div>
                    {sessionDetails.session.user_params?.special_requirements && (
                      <div>
                        <p className="text-sm text-gray-400">Special Requirements</p>
                        <p className="text-white text-xs leading-relaxed">
                          {sessionDetails.session.user_params.special_requirements}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Negotiation Insights */}
              {sessionDetails?.strategy && (
                <div className="p-4 flex-1 overflow-y-auto">
                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    AI Insights
                  </h4>
                  <div className="space-y-3">
                    {sessionDetails.strategy.approach && (
                      <div className="bg-white/5 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">Recommended Approach</p>
                        <p className="text-white text-sm capitalize">{sessionDetails.strategy.approach}</p>
                      </div>
                    )}
                    {sessionDetails.strategy.success_probability && (
                      <div className="bg-white/5 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">Success Probability</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-700 rounded-full h-2">
                            <div 
                              className="bg-gradient-to-r from-primary-500 to-accent-500 h-2 rounded-full"
                              style={{ width: `${(sessionDetails.strategy.success_probability * 100)}%` }}
                            />
                          </div>
                          <span className="text-white text-sm">
                            {Math.round(sessionDetails.strategy.success_probability * 100)}%
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Chat Section */}
            <div className="flex-1 flex flex-col">
              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                <AnimatePresence>
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex gap-3 ${message.sender === 'seller' ? 'justify-end' : 'justify-start'}`}
                    >
                      {message.sender !== 'seller' && (
                        <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center flex-shrink-0">
                          {message.sender === 'ai' ? (
                            <Bot className="w-4 h-4 text-white" />
                          ) : (
                            <User className="w-4 h-4 text-white" />
                          )}
                        </div>
                      )}
                      
                      <div className={`max-w-md ${message.sender === 'seller' ? 'order-first' : ''}`}>
                        <div className={`px-4 py-3 rounded-2xl ${
                          message.sender === 'seller'
                            ? 'bg-gradient-to-r from-primary-600 to-accent-600 text-white'
                            : message.sender === 'ai'
                            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                            : 'bg-white/10 text-white border border-white/20'
                        }`}>
                          <p className="text-sm leading-relaxed">{message.content}</p>
                        </div>
                        <p className="text-xs text-gray-500 mt-1 px-1">
                          {message.timestamp.toLocaleTimeString()}
                        </p>
                      </div>

                      {message.sender === 'seller' && (
                        <div className="w-8 h-8 bg-gradient-to-br from-accent-500 to-primary-500 rounded-full flex items-center justify-center flex-shrink-0">
                          <User className="w-4 h-4 text-white" />
                        </div>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="p-4 bg-gradient-to-r from-dark-800 to-dark-700 border-t border-primary-700/30">
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <textarea
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Type your message..."
                      className="w-full px-4 py-3 pr-12 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-primary-500 text-white placeholder-gray-400 resize-none backdrop-blur-sm"
                      rows={1}
                    />
                  </div>
                  <motion.button
                    onClick={sendMessage}
                    disabled={!newMessage.trim()}
                    className={`px-6 py-3 bg-gradient-to-r from-primary-600 to-accent-600 text-white rounded-xl transition-all duration-300 flex items-center gap-2 ${
                      !newMessage.trim() ? 'opacity-50 cursor-not-allowed' : 'hover:from-primary-500 hover:to-accent-500'
                    }`}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Send className="w-4 h-4" />
                  </motion.button>
                </div>
              </div>
            </div>
          </>
        ) : (
          // No Connection State
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl flex items-center justify-center mx-auto mb-6 opacity-50">
                <MessageSquare className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Ready to Connect</h3>
              <p className="text-gray-400 text-sm leading-relaxed mb-6">
                Enter a session ID from a buyer's negotiation to start chatting. 
                You'll be able to respond to their AI negotiation in real-time.
              </p>
              <div className="bg-white/5 rounded-lg p-4 text-left">
                <h4 className="font-medium text-primary-300 mb-2">How it works:</h4>
                <ul className="text-sm text-gray-300 space-y-2">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                    Buyer starts negotiation and gets session ID
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                    Enter the session ID to connect
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-primary-500 rounded-full" />
                    Chat directly with buyer in real-time
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default SellerPortal