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
  Star,
  Zap,
  Target
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
        <h3 className="text-3xl font-bold bg-gradient-to-r from-primary-300 to-accent-300 bg-clip-text text-transparent mb-4">
          Ready to Negotiate Smarter
        </h3>
        <p className="text-gray-300 leading-relaxed mb-8 text-lg">
          Configure your AI negotiation assistant and start getting better deals with 
          intelligent market analysis and automated negotiation strategies.
        </p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <motion.div 
            className="bg-white/5 backdrop-blur-xl rounded-xl border border-white/10 p-4 hover:bg-white/10 transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <Bot className="w-6 h-6 text-primary-400 mx-auto mb-2" />
            <span className="text-gray-300 font-medium">AI Assistant</span>
          </motion.div>
          <motion.div 
            className="bg-white/5 backdrop-blur-xl rounded-xl border border-white/10 p-4 hover:bg-white/10 transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <TrendingUp className="w-6 h-6 text-accent-400 mx-auto mb-2" />
            <span className="text-gray-300 font-medium">Market Analysis</span>
          </motion.div>
          <motion.div 
            className="bg-white/5 backdrop-blur-xl rounded-xl border border-white/10 p-4 hover:bg-white/10 transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <CheckCircle className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
            <span className="text-gray-300 font-medium">Smart Strategies</span>
          </motion.div>
          <motion.div 
            className="bg-white/5 backdrop-blur-xl rounded-xl border border-white/10 p-4 hover:bg-white/10 transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <BarChart3 className="w-6 h-6 text-blue-400 mx-auto mb-2" />
            <span className="text-gray-300 font-medium">Real-time Analytics</span>
          </motion.div>
        </div>
      </div>
    </div>
  )

  const NegotiationHeader = () => {
    if (!product || !isNegotiating) return null

    return (
      <motion.div 
        className="border-b border-primary-700/30 bg-gradient-to-r from-dark-800 to-dark-700"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg">
                <Package className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-xl text-white mb-1">{product.title}</h3>
                <p className="text-gray-300 text-sm mb-2">{product.description}</p>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1 text-primary-300">
                    <DollarSign className="w-4 h-4" />
                    <span className="font-semibold">₹{product.price?.toLocaleString()}</span>
                  </div>
                  {product.location && (
                    <div className="flex items-center gap-1 text-gray-400">
                      <MapPin className="w-4 h-4" />
                      <span>{product.location}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-emerald-500' : 'bg-red-500'
              }`} />
              <span className="text-sm text-gray-300">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  const StatusIndicator = () => {
    if (!isNegotiating) return null

    return (
      <motion.div 
        className="px-6 py-3 bg-gradient-to-r from-primary-600/10 to-accent-600/10 border-b border-primary-700/30"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary-400" />
            <span className="text-gray-300">AI Negotiation Active</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 text-gray-400">
              <Target className="w-3 h-3" />
              <span>Session Active</span>
            </div>
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-gradient-to-br from-dark-950 via-dark-900 to-primary-950">
      <NegotiationHeader />
      <StatusIndicator />
      
      {messages.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="flex-1 overflow-y-auto">
          {product && (
            <motion.div 
              className="p-6 border-b border-primary-700/30"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <ProductCard product={product} />
            </motion.div>
          )}
          
          {marketAnalysis && (
            <motion.div 
              className="p-6 border-b border-primary-700/30"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <MarketAnalysis analysis={marketAnalysis} />
            </motion.div>
          )}

          <div className="p-6 space-y-4">
            <AnimatePresence>
              {messages.map((message, index) => (
                <motion.div
                  key={`${message.id}-${index}`}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -20, scale: 0.95 }}
                  transition={{ 
                    duration: 0.3,
                    delay: index * 0.05,
                    type: "spring",
                    stiffness: 300,
                    damping: 30
                  }}
                >
                  <MessageBubble message={message} />
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      {isNegotiating && (
        <motion.div 
          className="p-4 bg-gradient-to-r from-dark-800 to-dark-700 border-t border-primary-700/30"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center justify-center gap-3 text-sm text-gray-400">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
              <span>AI is analyzing and negotiating</span>
            </div>
            <div className="w-px h-4 bg-gray-600" />
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span>Real-time responses</span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default ChatInterface