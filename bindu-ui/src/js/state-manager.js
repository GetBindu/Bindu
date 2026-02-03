/**
 * State Manager for Bindu UI
 * Manages application state using a simple event-driven pattern
 */
class StateManager {
    constructor() {
        this.state = {
            // Agent information
            agentCard: null,
            didDocument: null,
            skills: [],
            
            // UI state
            currentTheme: 'light',
            sidebarOpen: true,
            activeTab: 'chat',
            
            // Conversations
            conversations: [],
            activeConversationId: null,
            
            // Messages
            messages: {}, // conversationId -> messages[]
            
            // Tasks
            tasks: {}, // taskId -> task
            
            // Settings
            settings: {
                agentUrl: 'http://localhost:3773',
                authToken: null,
                autoScroll: true,
            },
            
            // UI state
            loading: false,
            error: null,
            
            // Typing indicators
            typingIndicators: new Set(), // conversationIds
        };
        
        this.listeners = new Map();
        this.loadFromStorage();
    }

    // Subscribe to state changes
    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, new Set());
        }
        this.listeners.get(key).add(callback);
        
        // Return unsubscribe function
        return () => {
            const callbacks = this.listeners.get(key);
            if (callbacks) {
                callbacks.delete(callback);
            }
        };
    }

    // Notify listeners of state changes
    notify(key, oldValue, newValue) {
        const callbacks = this.listeners.get(key);
        if (callbacks) {
            callbacks.forEach(callback => callback(newValue, oldValue));
        }
    }

    // Get state
    get(key) {
        return key ? this.state[key] : this.state;
    }

    // Set state
    set(key, value) {
        const oldValue = this.state[key];
        this.state[key] = value;
        this.notify(key, oldValue, value);
        this.saveToStorage();
    }

    // Update state with object
    update(updates) {
        Object.entries(updates).forEach(([key, value]) => {
            const oldValue = this.state[key];
            this.state[key] = value;
            this.notify(key, oldValue, value);
        });
        this.saveToStorage();
    }

    // Conversation management
    addConversation(conversation) {
        const conversations = [...this.state.conversations];
        const existingIndex = conversations.findIndex(c => c.id === conversation.id);
        
        if (existingIndex >= 0) {
            conversations[existingIndex] = conversation;
        } else {
            conversations.unshift(conversation);
        }
        
        this.set('conversations', conversations);
    }

    setActiveConversation(conversationId) {
        this.set('activeConversationId', conversationId);
    }

    // Message management
    addMessage(conversationId, message) {
        const messages = this.state.messages[conversationId] || [];
        messages.push(message);
        this.state.messages[conversationId] = messages;
        
        // Update conversation message count
        const conversations = this.state.conversations;
        const conversationIndex = conversations.findIndex(c => c.id === conversationId);
        if (conversationIndex >= 0) {
            conversations[conversationIndex].messageCount = messages.length;
            conversations[conversationIndex].updatedAt = new Date().toISOString();
            
            // Update title from first user message if it's still "New Chat"
            if (conversations[conversationIndex].title === 'New Chat' && message.role === 'user') {
                if (message.parts && message.parts.length > 0) {
                    const textPart = message.parts.find(p => p.kind === 'text');
                    if (textPart) {
                        const title = textPart.text.length > 50 
                            ? textPart.text.substring(0, 50) + '...' 
                            : textPart.text;
                        conversations[conversationIndex].title = title;
                    }
                }
            }
        }
        
        this.notify('messages', {}, this.state.messages);
        this.notify('conversations', {}, this.state.conversations);
    }

    getMessages(conversationId) {
        return this.state.messages[conversationId] || [];
    }

    setMessages(conversationId, messages) {
        this.state.messages[conversationId] = messages;
        
        // Update conversation message count
        const conversations = this.state.conversations;
        const conversationIndex = conversations.findIndex(c => c.id === conversationId);
        if (conversationIndex >= 0) {
            conversations[conversationIndex].messageCount = messages.length;
            conversations[conversationIndex].updatedAt = new Date().toISOString();
        }
        
        this.notify('messages', {}, this.state.messages);
        this.notify('conversations', {}, this.state.conversations);
    }

    updateMessage(conversationId, messageId, updatedMessage) {
        const messages = this.state.messages[conversationId] || [];
        const index = messages.findIndex(msg => msg.messageId === messageId);
        if (index !== -1) {
            messages[index] = updatedMessage;
            this.state.messages[conversationId] = messages;
            this.notify('messages', {}, this.state.messages);
        }
    }

    // Task management
    addTask(task) {
        this.state.tasks[task.id] = task;
        this.notify('tasks', {}, this.state.tasks);
    }

    getTask(taskId) {
        return this.state.tasks[taskId];
    }

    // Settings management
    updateSettings(settings) {
        this.set('settings', { ...this.state.settings, ...settings });
    }

    // Theme management
    toggleTheme() {
        const newTheme = this.state.currentTheme === 'light' ? 'dark' : 'light';
        this.set('currentTheme', newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
    }

    // Typing indicators
    setTyping(conversationId, isTyping) {
        const typingIndicators = new Set(this.state.typingIndicators);
        if (isTyping) {
            typingIndicators.add(conversationId);
        } else {
            typingIndicators.delete(conversationId);
        }
        this.set('typingIndicators', typingIndicators);
    }

    isTyping(conversationId) {
        return this.state.typingIndicators.has(conversationId);
    }

    // Loading and error states
    setLoading(loading) {
        this.set('loading', loading);
    }

    setError(error) {
        this.set('error', error);
    }

    clearError() {
        this.set('error', null);
    }

    // Storage persistence
    saveToStorage() {
        try {
            const persistState = {
                currentTheme: this.state.currentTheme,
                sidebarOpen: this.state.sidebarOpen,
                settings: this.state.settings,
                conversations: this.state.conversations,
                activeConversationId: this.state.activeConversationId,
                messages: this.state.messages,
            };
            localStorage.setItem('bindu-ui-state', JSON.stringify(persistState));
        } catch (error) {
            console.warn('Failed to save state to localStorage:', error);
        }
    }

    loadFromStorage() {
        try {
            const stored = localStorage.getItem('bindu-ui-state');
            if (stored) {
                const persistState = JSON.parse(stored);
                Object.keys(persistState).forEach(key => {
                    if (key in this.state) {
                        this.state[key] = persistState[key];
                    }
                });
                
                // Apply theme
                document.documentElement.setAttribute('data-theme', this.state.currentTheme);
            }
        } catch (error) {
            console.warn('Failed to load state from localStorage:', error);
        }
    }

    // Reset state
    reset() {
        this.state = {
            ...this.state,
            conversations: [],
            activeConversationId: null,
            messages: {},
            tasks: {},
            error: null,
            typingIndicators: new Set(),
        };
        this.saveToStorage();
    }

    // Utility methods
    createConversation(title = 'New Chat') {
        const conversation = {
            id: crypto.randomUUID(),
            title,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            messageCount: 0,
        };
        
        this.addConversation(conversation);
        return conversation;
    }

    updateConversationTitle(conversationId, title) {
        const conversations = [...this.state.conversations];
        const index = conversations.findIndex(c => c.id === conversationId);
        if (index >= 0) {
            conversations[index].title = title;
            conversations[index].updatedAt = new Date().toISOString();
            this.state.conversations = conversations;
            this.notify('conversations', {}, this.state.conversations);
        }
    }

    deleteConversation(conversationId) {
        const conversations = this.state.conversations.filter(c => c.id !== conversationId);
        const messages = { ...this.state.messages };
        delete messages[conversationId];
        
        this.update({ conversations, messages });
        
        if (this.state.activeConversationId === conversationId) {
            this.setActiveConversation(null);
        }
    }
}

// Create global state manager instance
window.stateManager = new StateManager();
