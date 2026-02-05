/**
 * UI Components and Utilities
 * Reusable UI components and helper functions
 */

// Utility functions
class Utils {
    static generateId() {
        return crypto.randomUUID();
    }
    
    static formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    static formatDate(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleDateString();
    }
    
    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    static copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            Toast.success('Copied to clipboard!');
        }).catch(() => {
            Toast.error('Failed to copy to clipboard');
        });
    }
}

// Message component
class MessageComponent {
    static create(message) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${message.role}`;
        messageEl.dataset.messageId = message.messageId;
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        if (message.parts && message.parts.length > 0) {
            message.parts.forEach(part => {
                if (part.kind === 'text') {
                    if (message.role === 'agent') {
                        // Check if marked is available, fallback to plain text
                        if (typeof window.marked !== 'undefined' && window.marked.parse) {
                            content.innerHTML = marked.parse(part.text);
                        } else {
                            // Fallback: escape HTML and use line breaks
                            content.textContent = part.text;
                            content.style.whiteSpace = 'pre-wrap';
                        }
                    } else {
                        content.textContent = part.text;
                    }
                }
            });
        } else {
            content.textContent = message.text || '';
        }
        
        const meta = document.createElement('div');
        meta.className = 'message-meta';
        
        const status = MessageComponent.createStatusIndicator(message.status);
        const timestamp = MessageComponent.createTimestamp(message.timestamp);
        
        meta.appendChild(status);
        meta.appendChild(timestamp);
        
        messageEl.appendChild(content);
        
        // Add feedback button INSIDE content for completed agent tasks (like old implementation)
        if (message.role === 'agent' && message.status && message.status.toLowerCase() === 'completed' && message.taskId) {
            const feedbackBtn = document.createElement('button');
            feedbackBtn.className = 'feedback-btn-corner';
            feedbackBtn.innerHTML = '👍 Feedback';
            feedbackBtn.onclick = (e) => {
                e.stopPropagation();
                console.log('Feedback button clicked!', { taskId: message.taskId });
                // Open feedback modal exactly like bindu\ui old implementation
                if (window.binduUI) {
                    console.log('Calling openFeedbackModal with taskId:', message.taskId);
                    window.binduUI.openFeedbackModal(message.taskId);
                } else {
                    console.error('window.binduUI not available!');
                }
            };
            content.appendChild(feedbackBtn);
        }
        
        // Add click handler for agent messages to set reply target (like old implementation)
        if (message.role === 'agent' && message.taskId) {
            messageEl.style.cursor = 'pointer';
            messageEl.addEventListener('click', (e) => {
                // Don't trigger if clicking on feedback button
                if (!e.target.closest('.feedback-btn-corner')) {
                    // Toggle reply target
                    if (window.binduUI) {
                        // Check if we're already replying to this message
                        if (window.binduUI.replyToTaskId === message.taskId) {
                            // If already replying, cancel the reply
                            window.binduUI.cancelReply();
                        } else {
                            // Set new reply target
                            window.binduUI.setReplyTo(message.taskId);
                        }
                    }
                }
            });
        }
        
        return messageEl;
    }
    
    static createFeedbackButtons(taskId) {
        const feedbackEl = document.createElement('div');
        feedbackEl.className = 'feedback-prompt';
        feedbackEl.innerHTML = `
            <p>Was this response helpful?</p>
            <div class="feedback-buttons">
                <button class="feedback-btn thumbs-up" onclick="window.binduUI.submitFeedback('${taskId}', 'helpful', 5)">👍</button>
                <button class="feedback-btn thumbs-down" onclick="window.binduUI.submitFeedback('${taskId}', 'not helpful', 1)">👎</button>
                <button class="feedback-btn detailed" onclick="window.binduUI.showDetailedFeedback('${taskId}')">💬</button>
            </div>
        `;
        return feedbackEl;
    }
    
    static createFeedbackSubmittedIndicator() {
        const feedbackEl = document.createElement('div');
        feedbackEl.className = 'feedback-submitted';
        feedbackEl.innerHTML = `
            <span class="feedback-indicator">✅ Feedback submitted</span>
        `;
        return feedbackEl;
    }
    
    static createStatusIndicator(status) {
        const statusEl = document.createElement('span');
        statusEl.className = 'message-status';
        
        if (status === 'sending') {
            statusEl.className += ' status-sending';
            statusEl.innerHTML = '⏳ Sending...';
        } else if (status === 'sent') {
            statusEl.className += ' status-sent';
            statusEl.innerHTML = '✓ Sent';
        } else if (status === 'error') {
            statusEl.className += ' status-error';
            statusEl.innerHTML = '✗ Failed';
        }
        
        return statusEl;
    }
    
    static createTimestamp(timestamp) {
        const timeEl = document.createElement('span');
        timeEl.className = 'message-time';
        timeEl.textContent = this.formatTime(timestamp);
        return timeEl;
    }
    
    static formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

// Typing indicator component
class TypingIndicator {
    static create() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        
        // Create simple dots container
        const dotsContainer = document.createElement('div');
        dotsContainer.className = 'typing-dots';
        
        // Create three simple dots
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            dotsContainer.appendChild(dot);
        }
        
        indicator.appendChild(dotsContainer);
        
        return indicator;
    }
}

// Conversation item component
class ConversationItem {
    static create(conversation, isActive = false) {
        const item = document.createElement('div');
        item.className = `conversation-item ${isActive ? 'active' : ''}`;
        item.dataset.conversationId = conversation.id;
        
        const content = document.createElement('div');
        content.className = 'conversation-content';
        
        const title = document.createElement('div');
        title.className = 'conversation-title';
        title.textContent = conversation.title;
        
        const meta = document.createElement('div');
        meta.className = 'conversation-meta';
        
        // Get actual message count from state manager
        let messageCount = conversation.messageCount || 0;
        if (window.stateManager) {
            const messages = window.stateManager.getMessages(conversation.id) || [];
            messageCount = messages.length;
        }
        
        meta.textContent = `${messageCount} message${messageCount !== 1 ? 's' : ''} • ${this.formatTime(conversation.updatedAt)}`;
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-conversation-btn';
        deleteBtn.innerHTML = '×';
        deleteBtn.title = 'Delete conversation';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent conversation selection
            if (confirm(`Delete conversation "${conversation.title}"?`)) {
                // Emit delete event
                item.dispatchEvent(new CustomEvent('deleteConversation', {
                    bubbles: true,
                    detail: { conversationId: conversation.id }
                }));
            }
        });
        
        content.appendChild(title);
        content.appendChild(meta);
        item.appendChild(content);
        item.appendChild(deleteBtn);
        
        return item;
    }
    
    static formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return date.toLocaleDateString([], { weekday: 'short' });
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    }
}

// Modal utility
class Modal {
    static show(modalId, content = null) {
        const modal = document.getElementById(modalId);
        if (modal) {
            // If content is provided, update the modal body
            if (content) {
                const modalBody = modal.querySelector('.modal-body');
                if (modalBody) {
                    modalBody.innerHTML = content;
                }
            }
            
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            
            // Focus first input
            const firstInput = modal.querySelector('input, textarea, button');
            if (firstInput) {
                firstInput.focus();
            }
        }
    }
    
    static hide(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }
    
    static hideAll() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
        document.body.style.overflow = '';
    }
}

// Toast notification utility
class Toast {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Add styles if not already present
        if (!document.querySelector('#toast-styles')) {
            const style = document.createElement('style');
            style.id = 'toast-styles';
            style.textContent = `
                .toast {
                    position: fixed;
                    bottom: 2rem;
                    right: 2rem;
                    padding: 0.75rem 1rem;
                    border-radius: 8px;
                    color: white;
                    font-weight: 500;
                    z-index: 1000;
                    animation: slideIn 0.3s ease-out;
                    max-width: 300px;
                }
                .toast-info { background-color: #3b82f6; }
                .toast-success { background-color: #10b981; }
                .toast-warning { background-color: #f59e0b; }
                .toast-error { background-color: #ef4444; }
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);
    }
    
    static success(message, duration) {
        this.show(message, 'success', duration);
    }
    
    static error(message, duration) {
        this.show(message, 'error', duration);
    }
    
    static warning(message, duration) {
        this.show(message, 'warning', duration);
    }
    
    static info(message, duration) {
        this.show(message, 'info', duration);
    }
}

// Loading overlay utility
class LoadingOverlay {
    static show(message = 'Loading...') {
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay hidden';
            overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <span class="loading-text">${message}</span>
            `;
            document.body.appendChild(overlay);
        } else {
            const textElement = overlay.querySelector('.loading-text');
            if (textElement) {
                textElement.textContent = message;
            }
        }
        
        overlay.classList.remove('hidden');
    }
    
    static hide() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }
}

// Auto-resize textarea utility
class AutoResizeTextarea {
    static init(textarea) {
        const resize = () => {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        };
        
        textarea.addEventListener('input', resize);
        textarea.addEventListener('focus', resize);
        resize();
    }
}

// Keyboard shortcuts
class KeyboardShortcuts {
    static init() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for new chat
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                window.binduUI.createNewConversation();
            }
            
            // Ctrl/Cmd + / for help
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                // Show help modal
            }
            
            // Escape to close modals
            if (e.key === 'Escape') {
                Modal.hideAll();
            }
        });
    }
}

// Export components
window.MessageComponent = MessageComponent;
window.TypingIndicator = TypingIndicator;
window.ConversationItem = ConversationItem;
window.Modal = Modal;
window.Toast = Toast;
window.LoadingOverlay = LoadingOverlay;
window.Utils = Utils;
window.AutoResizeTextarea = AutoResizeTextarea;
window.KeyboardShortcuts = KeyboardShortcuts;
