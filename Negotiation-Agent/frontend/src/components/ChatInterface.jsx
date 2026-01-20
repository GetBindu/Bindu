import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  MessageCircle, 
  Bot, 
  User, 
  Clock, 
  TrendingUp, 
  CheckCircle, 
  AlertCircle,
  DollarSign,
  BarChart3,
  Package,
  MapPin,
  Star
} from 'lucide-react'
import useNegotiationStore from '../hooks/useNegotiationStore'
import MessageBubble from './MessageBubble'
import ProductCard from './ProductCard'
import MarketAnalysis from './MarketAnalysis'

const ChatInterface = () => {
  const { messages, isNegotiating, product, marketAnalysis, isConnected } = useNegotiationStore()
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const EmptyState = () => (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-lg">
        <motion.div 
          className="w-28 h-28 bg-gradient-to-br from-primary-500 to-accent-500 rounded-3xl flex items-center justify-center mx-auto mb-8 shadow-2xl"
          whileHover={{ rotate: 5, scale: 1.05 }}
          transition={{ type: "spring", stiffness: 300 }}
        >
          <MessageCircle className="w-14 h-14 text-white" />
        </motion.div>
        <h3 className="text-3xl font-bold text-gradient-violet mb-4">
          Ready to Negotiate Smarter
        </h3>
        <p className="text-gray-300 leading-relaxed mb-8 text-lg">
          Configure your AI negotiation assistant and start getting better deals with 
          intelligent market analysis and automated negotiation strategies.
        </p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="glass-card p-4">
            <Bot className="w-6 h-6 text-primary-400 mx-auto mb-2" />
            <span className="text-gray-300 font-medium">AI Assistant</span>
          </div>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-green-500" />
            <span>Market Analysis</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-purple-500" />
            <span>Real-time Updates</span>
          </div>
        </div>
      </div>
    </div>
  )

  const NegotiationHeader = () => {
    if (!product || !isNegotiating) return null

    return (
      <motion.div 
        className="border-b border-gray-200 bg-white"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center">
                <Package className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 text-lg">{product.title}</h3>
                <p className="text-gray-600 text-sm mt-1 line-clamp-2">{product.description}</p>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {product.location}
                  </span>
                  <span className="flex items-center gap-1">
                    <Star className="w-3 h-3" />
                    {product.condition}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-900">₹{product.price?.toLocaleString()}</div>
              {product.original_price && product.original_price !== product.price && (
                <div className="text-sm text-gray-500 line-through">
                  ₹{product.original_price.toLocaleString()}
                </div>
              )}
            </div>
          </div>

          {/* Connection Status */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-600">
                {isConnected ? 'Live Negotiation Active' : 'Connection Lost'}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Started {new Date().toLocaleTimeString()}
              </span>
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
      {/* Header */}
      <NegotiationHeader />

      {/* Messages Container */}
      <div className="flex-1 overflow-hidden">
        {!isNegotiating && messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="h-full flex">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto scrollbar-hide">
              <div className="p-6 space-y-6">
                {/* Product Card */}
                {product && <ProductCard product={product} />}
                
                {/* Market Analysis */}
                {marketAnalysis && <MarketAnalysis analysis={marketAnalysis} />}
                
                {/* Messages */}
                <AnimatePresence initial={false}>
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}
                </AnimatePresence>
                
                {/* Connection Lost Indicator */}
                {isNegotiating && !isConnected && (
                  <motion.div
                    className="flex items-center justify-center p-4 bg-red-50 rounded-lg border border-red-200"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                  >
                    <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
                    <span className="text-red-700 font-medium">Connection lost. Attempting to reconnect...</span>
                  </motion.div>
                )}
                
                {/* Typing Indicator */}
                {isNegotiating && isConnected && (
                  <motion.div
                    className="flex items-center gap-3 px-4 py-3 bg-white rounded-lg shadow-sm border border-gray-200 max-w-xs"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                      <Bot className="w-4 h-4 text-primary-600" />
                    </div>
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm text-gray-600">AI is thinking...</span>
                  </motion.div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Sidebar Info */}
            {isNegotiating && (
              <div className="w-80 border-l border-gray-200 bg-white p-6 overflow-y-auto">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-primary-600" />
                  Session Insights
                </h3>
                
                <div className="space-y-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Negotiation Progress</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Messages Exchanged</span>
                        <span className="font-medium">{messages.length}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Current Strategy</span>
                        <span className="font-medium">Diplomatic</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Success Rate</span>
                        <span className="font-medium text-green-600">87%</span>
                      </div>
                    </div>
                  </div>

                  {marketAnalysis && (
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h4 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
                        <BarChart3 className="w-4 h-4" />
                        Market Data
                      </h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-blue-700">Average Price</span>
                          <span className="font-medium">₹{marketAnalysis.average_price?.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-blue-700">Market Trend</span>
                          <span className="font-medium capitalize">{marketAnalysis.market_trend}</span>
                        </div>
                        {marketAnalysis.price_range && (
                          <div className="flex justify-between">
                            <span className="text-blue-700">Price Range</span>
                            <span className="font-medium">
                              ₹{marketAnalysis.price_range.min?.toLocaleString()} - ₹{marketAnalysis.price_range.max?.toLocaleString()}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="bg-green-50 rounded-lg p-4">
                    <h4 className="font-medium text-green-900 mb-2">AI Recommendations</h4>
                    <ul className="space-y-1 text-sm text-green-700">
                      <li>• Stay patient and polite</li>
                      <li>• Highlight product value</li>
                      <li>• Use market data as leverage</li>
                      <li>• Consider seasonal trends</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatInterface