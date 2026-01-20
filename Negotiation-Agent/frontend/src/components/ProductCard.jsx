import React from 'react'
import { motion } from 'framer-motion'
import { 
  Package, 
  MapPin, 
  Star, 
  Calendar,
  ExternalLink,
  Tag,
  DollarSign
} from 'lucide-react'

const ProductCard = ({ product }) => {
  if (!product) return null

  return (
    <motion.div
      className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="p-6">
        <div className="flex items-start gap-4">
          {/* Product Icon */}
          <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center flex-shrink-0">
            <Package className="w-8 h-8 text-white" />
          </div>

          {/* Product Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {product.title}
                </h3>
                <p className="text-gray-600 text-sm leading-relaxed mb-3 line-clamp-2">
                  {product.description}
                </p>
              </div>
              
              {/* Price Section */}
              <div className="text-right ml-4">
                <div className="text-2xl font-bold text-gray-900 flex items-center gap-1">
                  <DollarSign className="w-6 h-6" />
                  ₹{product.price?.toLocaleString()}
                </div>
                {product.original_price && product.original_price !== product.price && (
                  <div className="text-sm text-gray-500 line-through">
                    ₹{product.original_price.toLocaleString()}
                  </div>
                )}
              </div>
            </div>

            {/* Product Details */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <MapPin className="w-4 h-4 text-gray-400" />
                <span className="truncate">{product.location || 'Location not specified'}</span>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Star className="w-4 h-4 text-gray-400" />
                <span>{product.condition || 'Condition not specified'}</span>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Tag className="w-4 h-4 text-gray-400" />
                <span>{product.category || 'General'}</span>
              </div>
              
              {product.posted_date && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <span>{new Date(product.posted_date).toLocaleDateString()}</span>
                </div>
              )}
            </div>

            {/* Additional Details */}
            <div className="space-y-3">
              {/* Seller Info */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <span className="text-sm font-medium text-gray-900">
                    Seller: {product.seller_name || 'Unknown Seller'}
                  </span>
                  <div className="text-xs text-gray-600 mt-1">
                    Contact: {product.seller_contact || 'Contact via platform'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    product.is_available 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {product.is_available ? 'Available' : 'Unavailable'}
                  </span>
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {product.platform || 'Unknown Platform'}
                  </span>
                </div>
              </div>

              {/* Features */}
              {product.features && product.features.length > 0 && (
                <div className="p-3 bg-blue-50 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-900 mb-2">Key Features:</h4>
                  <div className="flex flex-wrap gap-2">
                    {product.features.slice(0, 6).map((feature, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-blue-100 text-blue-700"
                      >
                        {feature}
                      </span>
                    ))}
                    {product.features.length > 6 && (
                      <span className="text-xs text-blue-600">
                        +{product.features.length - 6} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* External Link */}
              {product.url && (
                <div className="flex items-center justify-between p-3 bg-primary-50 rounded-lg">
                  <span className="text-sm text-primary-900 font-medium">
                    View Original Listing
                  </span>
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-1 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Open
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default ProductCard