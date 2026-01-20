import React from 'react'
import { motion } from 'framer-motion'
import { 
  Bot, 
  User, 
  CheckCircle, 
  XCircle, 
  DollarSign, 
  Clock, 
  MessageSquare,
  TrendingUp,
  AlertTriangle
} from 'lucide-react'

const MessageBubble = ({ message }) => {
  const getMessageIcon = () => {
    switch (message.type) {
      case 'ai':
        return <Bot className="w-4 h-4" />
      case 'seller':
        return <User className="w-4 h-4" />
      case 'system':
        return message.success ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />
      case 'price_update':
        return <DollarSign className="w-4 h-4" />
      default:
        return <MessageSquare className="w-4 h-4" />
    }
  }

  const getMessageStyles = () => {
    switch (message.type) {
      case 'ai':
        return {
          container: 'flex items-start gap-3 max-w-4xl',
          avatar: 'w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center text-white',
          bubble: 'bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm',
          text: 'text-gray-900'
        }
      case 'seller':
        return {
          container: 'flex items-start gap-3 max-w-4xl ml-auto flex-row-reverse',
          avatar: 'w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center text-white',
          bubble: 'bg-gray-100 border border-gray-200 rounded-2xl rounded-tr-sm px-4 py-3',
          text: 'text-gray-900'
        }
      case 'system':
        return {
          container: 'flex items-center justify-center max-w-4xl mx-auto',
          avatar: `w-8 h-8 ${message.success ? 'bg-green-500' : 'bg-red-500'} rounded-full flex items-center justify-center text-white`,
          bubble: `${message.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'} border rounded-lg px-4 py-3`,
          text: message.success ? 'text-green-900' : 'text-red-900'
        }
      case 'price_update':
        return {
          container: 'flex items-center justify-center max-w-4xl mx-auto',
          avatar: 'w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white',
          bubble: 'bg-blue-50 border-blue-200 border rounded-lg px-4 py-3',
          text: 'text-blue-900'
        }
      default:
        return {
          container: 'flex items-start gap-3 max-w-4xl',
          avatar: 'w-10 h-10 bg-gray-400 rounded-full flex items-center justify-center text-white',
          bubble: 'bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3',
          text: 'text-gray-900'
        }
    }
  }

  const styles = getMessageStyles()

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  return (
    <motion.div
      className={styles.container}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className={styles.avatar}>
        {getMessageIcon()}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className={styles.bubble}>
          {/* Message Header */}
          {(message.phase || message.strategy) && (
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-200">
              {message.phase && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                  Phase: {message.phase}
                </span>
              )}
              {message.strategy && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                  Strategy: {message.strategy}
                </span>
              )}
            </div>
          )}

          {/* Message Content */}
          <div className={styles.text}>
            {message.content}
          </div>

          {/* Price Information */}
          {message.finalPrice && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex items-center gap-2 text-lg font-semibold text-green-600">
                <DollarSign className="w-5 h-5" />
                Final Price: ₹{message.finalPrice.toLocaleString()}
              </div>
            </div>
          )}

          {message.price && message.type === 'price_update' && (
            <div className="mt-2 flex items-center gap-2 font-semibold">
              <TrendingUp className="w-4 h-4" />
              ₹{message.price.toLocaleString()}
            </div>
          )}

          {/* System Message Enhancements */}
          {message.type === 'system' && !message.success && (
            <div className="mt-2 flex items-center gap-2 text-sm text-red-700">
              <AlertTriangle className="w-4 h-4" />
              The negotiation did not reach a successful conclusion
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
          <Clock className="w-3 h-3" />
          {formatTime(message.timestamp)}
        </div>
      </div>
    </motion.div>
  )
}

export default MessageBubble