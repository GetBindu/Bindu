# Multi-stage Dockerfile for Bindu UI
# Stage 1: Build stage
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Production stage
FROM nginx:alpine AS production

# Install additional utilities if needed
RUN apk add --no-cache \
    curl \
    && rm -rf /var/cache/apk/*

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user for security
RUN addgroup -g 1001 -S bindu && \
    adduser -S bindu -u 1001 -G bindu

# Set proper permissions
RUN chown -R bindu:bindu /usr/share/nginx/html && \
    chown -R bindu:bindu /var/cache/nginx && \
    chown -R bindu:bindu /var/log/nginx && \
    chown -R bindu:bindu /etc/nginx/conf.d

# Create nginx pid directory
RUN touch /var/run/nginx.pid && \
    chown -R bindu:bindu /var/run/nginx.pid

# Switch to non-root user
USER bindu

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
