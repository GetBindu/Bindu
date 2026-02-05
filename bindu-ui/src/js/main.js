/**
 * Main Application Entry Point
 * Initializes the Bindu UI application
 */

// Import modules
import './api-client.js';
import './state-manager.js';
import './ui-components.js';
import { marked } from 'marked';

// Make marked available globally for ui-components
window.marked = marked;

// Main application class
class BinduUI {
    constructor() {
        this.stateManager = stateManager;
        this.apiClient = null; // Will be initialized in initializeApiClient
        
        // Use state manager for all state - CONSOLIDATED APPROACH
        // Initialize state manager with required properties if not present
        if (!this.stateManager.get('currentTaskId')) {
            this.stateManager.set('currentTaskId', null);
        }
        if (!this.stateManager.get('currentTaskState')) {
            this.stateManager.set('currentTaskState', null);
        }
        if (!this.stateManager.get('contextId')) {
            this.stateManager.set('contextId', null);
        }
        if (!this.stateManager.get('replyToTaskId')) {
            this.stateManager.set('replyToTaskId', null);
        }
        if (!this.stateManager.get('taskHistory')) {
            this.stateManager.set('taskHistory', []);
        }
        if (!this.stateManager.get('contexts')) {
            this.stateManager.set('contexts', []);
        }
        
        // Authentication State - use state manager
        const storedToken = localStorage.getItem('bindu_auth_token');
        if (storedToken && !this.stateManager.get('authToken')) {
            this.stateManager.set('authToken', storedToken);
        }
        
        // Payment State - use state manager
        if (!this.stateManager.get('paymentToken')) {
            this.stateManager.set('paymentToken', null);
        }
        if (!this.stateManager.get('pendingPaymentRequest')) {
            this.stateManager.set('pendingPaymentRequest', null);
        }
        
        // UI State - use state manager
        if (!this.stateManager.get('currentConversationId')) {
            this.stateManager.set('currentConversationId', null);
        }
        if (!this.stateManager.get('isTyping')) {
            this.stateManager.set('isTyping', false);
        }
        if (!this.stateManager.get('processingConversations')) {
            this.stateManager.set('processingConversations', new Set());
        }
        if (!this.stateManager.get('eventListenersSetup')) {
            this.stateManager.set('eventListenersSetup', false);
        }
        if (!this.stateManager.get('isSending')) {
            this.stateManager.set('isSending', false);
        }
        if (!this.stateManager.get('lastSendTime')) {
            this.stateManager.set('lastSendTime', 0);
        }
        if (!this.stateManager.get('eventInProgress')) {
            this.stateManager.set('eventInProgress', false);
        }
        if (!this.stateManager.get('conversationTaskIds')) {
            this.stateManager.set('conversationTaskIds', new Map());
        }
        if (!this.stateManager.get('typingIndicators')) {
            this.stateManager.set('typingIndicators', new Set());
        }
        
        this.init();
    }

    // Getter methods for cleaner access to state manager
    get currentTaskId() { return this.stateManager.get('currentTaskId'); }
    set currentTaskId(value) { this.stateManager.set('currentTaskId', value); }
    
    get currentTaskState() { return this.stateManager.get('currentTaskState'); }
    set currentTaskState(value) { this.stateManager.set('currentTaskState', value); }
    
    get contextId() { return this.stateManager.get('contextId'); }
    set contextId(value) { this.stateManager.set('contextId', value); }
    
    get replyToTaskId() { return this.stateManager.get('replyToTaskId'); }
    set replyToTaskId(value) { this.stateManager.set('replyToTaskId', value); }
    
    get taskHistory() { return this.stateManager.get('taskHistory'); }
    set taskHistory(value) { this.stateManager.set('taskHistory', value); }
    
    get contexts() { return this.stateManager.get('contexts'); }
    set contexts(value) { this.stateManager.set('contexts', value); }
    
    get authToken() { return this.stateManager.get('authToken'); }
    set authToken(value) { 
        this.stateManager.set('authToken', value);
        if (value) {
            localStorage.setItem('bindu_auth_token', value);
        } else {
            localStorage.removeItem('bindu_auth_token');
        }
    }
    
    get paymentToken() { return this.stateManager.get('paymentToken'); }
    set paymentToken(value) { this.stateManager.set('paymentToken', value); }
    
    get currentConversationId() { return this.stateManager.get('currentConversationId'); }
    set currentConversationId(value) { this.stateManager.set('currentConversationId', value); }
    
    get isTyping() { return this.stateManager.get('isTyping'); }
    set isTyping(value) { this.stateManager.set('isTyping', value); }
    
    get processingConversations() { return this.stateManager.get('processingConversations'); }
    set processingConversations(value) { this.stateManager.set('processingConversations', value); }
    
    get eventListenersSetup() { return this.stateManager.get('eventListenersSetup'); }
    set eventListenersSetup(value) { this.stateManager.set('eventListenersSetup', value); }
    
    get isSending() { return this.stateManager.get('isSending'); }
    set isSending(value) { this.stateManager.set('isSending', value); }
    
    get lastSendTime() { return this.stateManager.get('lastSendTime'); }
    set lastSendTime(value) { this.stateManager.set('lastSendTime', value); }
    
    get eventInProgress() { return this.stateManager.get('eventInProgress'); }
    set eventInProgress(value) { this.stateManager.set('eventInProgress', value); }
    
    get conversationTaskIds() { return this.stateManager.get('conversationTaskIds'); }
    set conversationTaskIds(value) { this.stateManager.set('conversationTaskIds', value); }
    
    get typingIndicators() { return this.stateManager.get('typingIndicators'); }
    set typingIndicators(value) { this.stateManager.set('typingIndicators', value); }

    async init() {
        try {
            console.log('🚀 Starting Bindu UI initialization...');
            
            // Wait a bit for modules to load
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Check if required dependencies are available
            if (!window.stateManager) {
                throw new Error('StateManager not loaded');
            }
            if (!window.BinduApiClient) {
                throw new Error('BinduApiClient not loaded');
            }
            if (!window.Utils) {
                throw new Error('Utils not loaded');
            }
            if (!window.Modal) {
                throw new Error('Modal not loaded');
            }
            if (!window.ApiError) {
                throw new Error('ApiError not loaded');
            }
            
            console.log('✅ Dependencies loaded successfully');
            
            // Initialize API client
            this.initializeApiClient();
            console.log('✅ API client initialized');
            
            // Setup UI event listeners
            this.setupEventListeners();
            console.log('✅ Event listeners setup');
            
            // Setup keyboard shortcuts
            KeyboardShortcuts.init();
            console.log('✅ Keyboard shortcuts initialized');
            
            // Load initial data
            await this.loadInitialData();
            console.log('✅ Initial data loaded');
            
            // Setup state subscriptions
            this.setupStateSubscriptions();
            console.log('✅ State subscriptions setup');
            
            // Auto-resize message input
            const messageInput = document.getElementById('message-input');
            if (messageInput) {
                AutoResizeTextarea.init(messageInput);
                console.log('✅ Auto-resize textarea initialized');
            } else {
                console.warn('⚠️ Message input not found');
            }
            
            // Modal event listeners (exactly like bindu\ui old implementation)
            const feedbackModal = document.getElementById('feedback-modal');
            const skillModal = document.getElementById('skill-modal');

            if (feedbackModal) {
                feedbackModal.addEventListener('click', (e) => {
                    if (e.target === feedbackModal) {
                        this.closeFeedbackModal();
                    }
                });
            }

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    // Check feedback modal
                    const feedbackModal = document.getElementById('feedback-modal');
                    if (feedbackModal && !feedbackModal.classList.contains('hidden')) {
                        this.closeFeedbackModal();
                    }
                    
                    // Check skill modal
                    const skillModal = document.getElementById('skill-modal');
                    if (skillModal && !skillModal.classList.contains('hidden')) {
                        Modal.hide('skill-modal');
                    }
                }
            });

            // Initialize other components
            this.addSmoothAnimations();
            console.log('✅ Animations initialized');
            
            // Load skills
            await this.loadSkills();
            console.log('✅ Skills loaded');
            
            // Hide any visible modals on initialization
            this.hideAllModals();
            console.log('✅ Modals hidden');
            
            console.log('🎉 Bindu UI initialized successfully');
        } catch (error) {
            console.error('❌ Failed to initialize Bindu UI:', error);
            Toast.error('Failed to initialize application');
        }
    }

    initializeApiClient() {
        const settings = stateManager.get('settings');
        this.apiClient = new BinduApiClient(settings.agentUrl);
        this.apiClient.setAuthToken(settings.authToken);
    }

    setupEventListeners() {
        // Mobile menu toggle
        document.getElementById('menu-toggle').addEventListener('click', () => {
            this.toggleSidebar();
        });

        // Theme toggle
        document.getElementById('theme-toggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        // Settings
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.showSettingsModal();
        });

        // New chat
        document.getElementById('new-chat-btn').addEventListener('click', () => {
            this.createNewConversation();
        });

        // Message input
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');

        messageInput.addEventListener('input', () => {
            this.updateCharCount();
            this.updateSendButton();
        });

        sendBtn.addEventListener('click', (e) => {
            console.log('Send button clicked - event:', e.type, e.target);
            // Immediate event lock to prevent any duplicate processing
            if (this.eventInProgress) {
                console.log('Event already in progress, ignoring');
                return;
            }
            this.eventInProgress = true;
            this.sendMessage();
        });

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                console.log('Enter key pressed - event:', e.type, e.key);
                e.preventDefault();
                // Immediate event lock to prevent any duplicate processing
                if (this.eventInProgress) {
                    console.log('Event already in progress, ignoring');
                    return;
                }
                this.eventInProgress = true;
                this.sendMessage();
            }
        });

        // Example prompts - REMOVED to prevent duplicate listeners
        // Prompt card listeners are now set up in renderMessages function

        // Settings modal
        document.getElementById('close-settings').addEventListener('click', () => {
            Modal.hide('settings-modal');
        });

        document.getElementById('cancel-settings').addEventListener('click', () => {
            Modal.hide('settings-modal');
        });

        document.getElementById('save-settings').addEventListener('click', () => {
            this.saveSettings();
        });

        // Info modal
        document.getElementById('close-info').addEventListener('click', () => {
            Modal.hide('info-modal');
        });

        // Cancel reply button
        const cancelReplyBtn = document.getElementById('cancel-reply');
        if (cancelReplyBtn) {
            cancelReplyBtn.addEventListener('click', () => {
                this.cancelReply();
            });
        }

        // Modal backdrop clicks
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    Modal.hide(modal.id);
                }
            });
        });
    }

    setupStateSubscriptions() {
        // Listen for conversation changes
        stateManager.subscribe('conversations', () => {
            this.renderConversationsList();
        });

        stateManager.subscribe('activeConversationId', (conversationId) => {
            this.switchToConversation(conversationId);
        });

        stateManager.subscribe('messages', () => {
            this.renderMessages();
        });

        stateManager.subscribe('loading', (loading) => {
            if (loading) {
                LoadingOverlay.show('Connecting to agent...');
            } else {
                LoadingOverlay.hide();
            }
        });

        stateManager.subscribe('error', (error) => {
            if (error) {
                Toast.error(error.message || 'An error occurred');
            }
        });

        // Note: Skills subscription removed since skills tab is removed
        // Skills are now accessible from Info tab only
    }

    async loadInitialData() {
        try {
            stateManager.setLoading(true);
            
            // Try to load agent card with error recovery
            let agentCard = null;
            try {
                agentCard = await this.apiClient.getAgentCard();
                stateManager.set('agentCard', agentCard);
                this.updateAgentInfo(agentCard);
                console.log('✅ Agent card loaded successfully');
            } catch (error) {
                console.warn('⚠️ Agent not available, using demo mode:', error.message);
                // Create demo agent card with skills
                agentCard = {
                    id: 'demo-agent',
                    name: 'Demo Agent',
                    description: 'A demo agent for testing purposes',
                    version: '1.0.0',
                    skills: [
                        {
                            id: 'demo-skill-1',
                            name: 'Research',
                            description: 'Conduct research and gather information',
                            tags: ['research', 'information']
                        },
                        {
                            id: 'demo-skill-2',
                            name: 'Analysis',
                            description: 'Analyze data and provide insights',
                            tags: ['analysis', 'data']
                        },
                        {
                            id: 'demo-skill-3',
                            name: 'Writing',
                            description: 'Generate written content and reports',
                            tags: ['writing', 'content']
                        }
                    ]
                };
                stateManager.set('agentCard', agentCard);
                this.updateAgentInfo(agentCard);
            }
            
            // Load conversations/contexts with error recovery
            let conversations = [];
            try {
                const contexts = await this.apiClient.getConversations();
                
                // Get existing local conversations first
                const localConversations = stateManager.get('conversations') || [];
                
                // Convert contexts to conversation format
                const contextConversations = contexts.map(ctx => {
                    // Get actual message count from state manager if available
                    const existingMessages = stateManager.getMessages(ctx.id) || [];
                    
                    // Get first message for title
                    let title = 'New Chat';
                    if (existingMessages.length > 0) {
                        const firstMessage = existingMessages.find(m => m.role === 'user');
                        if (firstMessage && firstMessage.parts && firstMessage.parts.length > 0) {
                            const textPart = firstMessage.parts.find(p => p.kind === 'text');
                            if (textPart) {
                                title = textPart.text.length > 50 
                                    ? textPart.text.substring(0, 50) + '...' 
                                    : textPart.text;
                            }
                        }
                    }
                    
                    return {
                        id: ctx.id,
                        title: title || ctx.firstMessage || 'New Chat',
                        createdAt: ctx.timestamp ? new Date(ctx.timestamp).toISOString() : new Date().toISOString(),
                        updatedAt: ctx.timestamp ? new Date(ctx.timestamp).toISOString() : new Date().toISOString(),
                        messageCount: existingMessages.length, // Use actual message count
                        taskCount: ctx.task_count || 0,
                        isContext: true
                    };
                });
                
                // Merge local conversations with server contexts
                // Server contexts take priority for matching IDs
                const mergedConversations = [...localConversations];
                contextConversations.forEach(ctxConv => {
                    const existingIndex = mergedConversations.findIndex(c => c.id === ctxConv.id);
                    if (existingIndex >= 0) {
                        // Update existing conversation with server data
                        mergedConversations[existingIndex] = { ...mergedConversations[existingIndex], ...ctxConv };
                    } else {
                        // Add new context conversation
                        mergedConversations.push(ctxConv);
                    }
                });
                
                // If no conversations at all, create default conversation
                if (mergedConversations.length === 0) {
                    const defaultConversation = stateManager.createConversation();
                    mergedConversations.push(defaultConversation);
                }
                
                conversations = mergedConversations;
                stateManager.set('conversations', conversations);
                console.log(`✅ Loaded ${conversations.length} conversations (merged local + server)`);
            } catch (error) {
                console.warn('⚠️ Failed to load conversations:', error.message);
                // Use existing local conversations or create default
                conversations = stateManager.get('conversations') || [];
                if (conversations.length === 0) {
                    const defaultConversation = stateManager.createConversation();
                    conversations = [defaultConversation];
                    stateManager.set('conversations', conversations);
                }
                console.log('🆕 Using local conversations or created default');
            }
            
            // Auto-select or create conversation with better error handling
            const activeConversationId = this.currentConversationId;
            console.log('📍 Active conversation ID from state:', activeConversationId);
            console.log('📋 Available conversations:', conversations);
            
            if (activeConversationId && conversations.find(c => c.id === activeConversationId)) {
                // Load history for the active conversation
                console.log('🔄 Using existing active conversation:', activeConversationId);
                try {
                    // Check if messages already exist in localStorage first
                    const existingMessages = stateManager.getMessages(activeConversationId);
                    if (existingMessages.length === 0) {
                        console.log('📜 No local messages found, loading from server...');
                        await this.loadConversationHistory(activeConversationId);
                    } else {
                        console.log(`📋 Found ${existingMessages.length} messages in localStorage`);
                    }
                    stateManager.setActiveConversation(activeConversationId);
                    this.currentConversationId = activeConversationId;
                } catch (error) {
                    console.warn('⚠️ Failed to load conversation history:', error.message);
                    // Continue anyway, will show empty conversation
                }
            } else if (conversations.length > 0) {
                // Load history for the first conversation
                console.log('🔄 Using first available conversation:', conversations[0].id);
                try {
                    // Check if messages already exist in localStorage first
                    const existingMessages = stateManager.getMessages(conversations[0].id);
                    if (existingMessages.length === 0) {
                        console.log('📜 No local messages found, loading from server...');
                        await this.loadConversationHistory(conversations[0].id);
                    } else {
                        console.log(`📋 Found ${existingMessages.length} messages in localStorage`);
                    }
                    stateManager.setActiveConversation(conversations[0].id);
                    this.currentConversationId = conversations[0].id;
                } catch (error) {
                    console.warn('⚠️ Failed to load conversation history:', error.message);
                    // Continue anyway
                }
            } else {
                // Only create new conversation if absolutely no conversations exist
                console.log('🆕 No conversations found, creating new one');
                const newConversation = stateManager.createConversation();
                stateManager.setActiveConversation(newConversation.id);
                this.currentConversationId = newConversation.id;
                console.log('✅ Created initial conversation:', newConversation.id);
            }
            
            // Update UI after conversation is set
            this.renderConversationsList();
            this.renderMessages();
            this.updateSendButton();
            
            console.log('✅ Final currentConversationId:', this.currentConversationId);
            
            stateManager.setLoading(false);
            
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            stateManager.setLoading(false);
            stateManager.setError(error.message);
            Toast.error('Failed to load initial data: ' + error.message);
            
            // Try to recover by creating minimal state
            try {
                const fallbackConversation = stateManager.createConversation();
                stateManager.setActiveConversation(fallbackConversation.id);
                this.currentConversationId = fallbackConversation.id;
                this.renderConversationsList();
                this.renderMessages();
                Toast.info('Recovered with minimal functionality');
            } catch (recoveryError) {
                console.error('❌ Even recovery failed:', recoveryError);
                Toast.error('Application failed to initialize properly');
            }
        }
    }

    async loadSkills() {
        try {
            const skills = await this.apiClient.getSkills();
            // Ensure skills is always an array
            const skillsArray = Array.isArray(skills) ? skills : [];
            stateManager.set('skills', skillsArray);
            console.log(`✅ Loaded ${skillsArray.length} skills`);
        } catch (error) {
            console.warn('⚠️ Failed to load skills:', error.message);
            // Use demo skills from agent card
            const agentCard = stateManager.get('agentCard');
            const demoSkills = agentCard?.skills || [];
            // Ensure demo skills is also an array
            const skillsArray = Array.isArray(demoSkills) ? demoSkills : [];
            stateManager.set('skills', skillsArray);
            console.log(`📋 Using ${skillsArray.length} demo skills`);
        }
    }

    async loadConversationHistory(conversationId) {
        try {
            console.log(`📜 Loading history for conversation: ${conversationId}`);
            
            // Load task history for this conversation
            const tasks = await this.apiClient.getConversationTasks(conversationId);
            console.log(`📋 Found ${tasks.length} tasks for conversation`);
            
            // Convert tasks to messages and add to state
            const messages = [];
            tasks.forEach(task => {
                try {
                    // Add user message from task input
                    if (task.input && task.input.message) {
                        messages.push({
                            messageId: task.id + '-user',
                            role: 'user',
                            parts: task.input.message.parts || [{ kind: 'text', text: task.input.message }],
                            timestamp: task.created_at,
                            status: 'sent'
                        });
                    }
                    
                    // Add agent messages from task artifacts
                    if (task.artifacts && task.artifacts.length > 0) {
                        task.artifacts.forEach(artifact => {
                            if (artifact.parts && artifact.parts.length > 0) {
                                artifact.parts.forEach(part => {
                                    if (part.kind === 'text') {
                                        messages.push({
                                            messageId: task.id + '-agent-' + Math.random(),
                                            role: 'agent',
                                            parts: [part],
                                            timestamp: task.updated_at || task.created_at,
                                            status: 'sent'
                                        });
                                    }
                                });
                            }
                        });
                    }
                    
                    // Check if task is in input-required state
                    if (task.status && task.status.state === 'input-required') {
                        // Store task ID for continuity
                        this.conversationTaskIds.set(conversationId, task.id);
                        
                        // Add input-required message
                        if (task.history && task.history.length > 0) {
                            const lastMessage = task.history[task.history.length - 1];
                            if (lastMessage && lastMessage.parts) {
                                const inputRequest = lastMessage.parts.find(part => part.kind === 'text');
                                if (inputRequest) {
                                    messages.push({
                                        messageId: task.id + '-input-required',
                                        role: 'agent',
                                        parts: [{
                                            kind: 'text',
                                            text: `⚠️ **Input Required**: ${inputRequest.text}\n\nPlease provide the required information and try again.`
                                        }],
                                        timestamp: task.status.timestamp,
                                        status: 'sent'
                                    });
                                }
                            }
                        }
                    }
                } catch (taskError) {
                    console.warn(`⚠️ Failed to process task ${task.id}:`, taskError.message);
                    // Continue with other tasks
                }
            });
            
            // Sort messages by timestamp with safe date parsing
            messages.sort((a, b) => {
                try {
                    const dateA = new Date(a.timestamp);
                    const dateB = new Date(b.timestamp);
                    return dateA.getTime() - dateB.getTime();
                } catch (error) {
                    console.warn('Invalid timestamp in message sorting:', error);
                    return 0; // Keep original order if dates are invalid
                }
            });
            
            // Get existing messages and merge with server messages
            const existingMessages = stateManager.getMessages(conversationId) || [];
            
            // Create a map of existing messages by messageId to avoid duplicates
            const existingMessageMap = new Map();
            existingMessages.forEach(msg => {
                existingMessageMap.set(msg.messageId, msg);
            });
            
            // Add server messages that don't already exist
            const mergedMessages = [...existingMessages];
            messages.forEach(serverMsg => {
                if (!existingMessageMap.has(serverMsg.messageId)) {
                    mergedMessages.push(serverMsg);
                }
            });
            
            // Sort all messages by timestamp with safe date parsing
            mergedMessages.sort((a, b) => {
                try {
                    const dateA = new Date(a.timestamp);
                    const dateB = new Date(b.timestamp);
                    return dateA.getTime() - dateB.getTime();
                } catch (error) {
                    console.warn('Invalid timestamp in merged message sorting:', error);
                    return 0; // Keep original order if dates are invalid
                }
            });
            
            // Add merged messages to state
            stateManager.setMessages(conversationId, mergedMessages);
            console.log(`✅ Loaded ${mergedMessages.length} total messages for conversation ${conversationId} (${existingMessages.length} local + ${messages.length} server)`);
            
        } catch (error) {
            console.warn('⚠️ Failed to load conversation history:', error.message);
            // Don't throw error, just continue without history
            stateManager.setMessages(conversationId, []);
        }
    }

    toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('open');
        }
    }

    updateAgentInfo(agentCard) {
        const agentName = document.getElementById('agent-name');
        const agentStatus = document.getElementById('agent-status');
        
        if (agentName) {
            agentName.textContent = agentCard ? (agentCard.name || 'Unknown Agent') : 'Agent Offline';
        }
        
        if (agentStatus) {
            agentStatus.className = agentCard ? 'status-dot online' : 'status-dot offline';
        }
    }

    renderConversationsList() {
        const conversationsList = document.getElementById('conversations-list');
        const conversations = stateManager.get('conversations');
        const activeId = stateManager.get('activeConversationId');
        
        if (conversations.length === 0) {
            conversationsList.innerHTML = '<div class="no-conversations">No conversations yet</div>';
            return;
        }
        
        conversationsList.innerHTML = '';
        conversations.forEach(conversation => {
            const item = ConversationItem.create(conversation, conversation.id === activeId);
            item.addEventListener('click', () => {
                stateManager.setActiveConversation(conversation.id);
            });
            
            // Add delete conversation event listener
            item.addEventListener('deleteConversation', (e) => {
                this.deleteConversation(e.detail.conversationId);
            });
            
            conversationsList.appendChild(item);
        });
    }

    async switchToConversation(conversationId) {
        this.currentConversationId = conversationId; // Set current conversation ID first
        
        // Update active state in sidebar
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', item.dataset.conversationId === conversationId);
        });
        
        // Check if messages already exist in localStorage first
        const currentMessages = stateManager.getMessages(conversationId);
        if (currentMessages.length === 0) {
            console.log('📜 No local messages found, loading from server...');
            await this.loadConversationHistory(conversationId);
        } else {
            console.log(`📋 Found ${currentMessages.length} messages in localStorage`);
        }
        
        this.renderMessages();
        console.log('Switched to conversation:', conversationId);
    }

    setupPromptCardListeners() {
        const promptCards = document.querySelectorAll('.prompt-card');
        promptCards.forEach(card => {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                const prompt = card.dataset.prompt;
                if (prompt) {
                    const messageInput = document.getElementById('message-input');
                    if (messageInput) {
                        messageInput.value = prompt;
                        messageInput.focus();
                        this.updateCharCount();
                        this.updateSendButton();
                        
                        // Auto-send the prompt
                        this.sendMessage();
                    }
                }
            });
        });
    }

    renderSkills() {
        // Skills tab has been removed - skills are now accessible from Info tab only
        // This function is kept for backward compatibility but won't render anything
        console.log('renderSkills() called but skills tab has been removed - skills are accessible from Info tab');
        
        // Don't render anything since skills tab is removed
        // Skills are now displayed in the Info tab via loadAgentInfo()
    }

    async showSkillDetails(skillId) {
        try {
            console.log('🔍 Loading skill details for ID:', skillId);
            
            const skill = await this.apiClient.getSkill(skillId);
            console.log('✅ Skill data received:', skill);
            
            const documentation = await this.apiClient.getSkillDocumentation(skillId);
            console.log('📚 Documentation received:', documentation ? 'success' : 'failed');
            
            // Parse and format the YAML documentation
            const formattedDocumentation = this.formatSkillDocumentation(documentation);
            
            const modalContent = `
                <div class="skill-modal-content">
                    <div class="skill-modal-header">
                        <h2>${skill.name || 'Unknown Skill'}</h2>
                        <span class="skill-id">${skill.id || skillId}</span>
                    </div>
                    <div class="skill-modal-description">
                        <p>${skill.description || 'No description available'}</p>
                    </div>
                    ${skill.tags ? `
                        <div class="skill-tags">
                            <strong>Tags:</strong>
                            ${skill.tags.map(tag => `<span class="skill-tag">${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                    <div class="skill-documentation">
                        <h3>Skill Documentation</h3>
                        ${formattedDocumentation}
                    </div>
                </div>
            `;
            
            console.log('🎯 Showing modal with content length:', modalContent.length);
            Modal.show('skill-modal', modalContent);
            
        } catch (error) {
            console.error('❌ Failed to load skill details:', error);
            console.error('❌ Skill ID was:', skillId);
            console.error('❌ Error details:', error.message);
            
            Toast.error(`Failed to load skill details: ${error.message}`);
            
            // Show error in modal
            const errorContent = `
                <div class="skill-modal-content">
                    <div class="skill-modal-header">
                        <h2>Error Loading Skill</h2>
                    </div>
                    <div class="skill-modal-description">
                        <p>Could not load details for skill ID: <code>${skillId}</code></p>
                        <p><strong>Error:</strong> ${error.message}</p>
                    </div>
                </div>
            `;
            
            console.log('🚨 Showing error modal');
            Modal.show('skill-modal', errorContent);
        }
    }

    formatSkillDocumentation(documentation) {
        if (!documentation) return '<p class="no-docs">No documentation available</p>';
        
        try {
            // Parse YAML-like structure and format it
            const sections = this.parseYamlSections(documentation);
            
            let html = '<div class="skill-docs-container">';
            
            // Basic Metadata Section
            if (sections.id || sections.name || sections.version || sections.author) {
                html += '<div class="doc-section">';
                html += '<h4><span class="section-icon">📋</span>Basic Metadata</h4>';
                html += '<div class="doc-grid">';
                if (sections.id) html += `<div class="doc-item"><strong>ID:</strong> <code>${sections.id}</code></div>`;
                if (sections.name) html += `<div class="doc-item"><strong>Name:</strong> <span>${sections.name}</span></div>`;
                if (sections.version) html += `<div class="doc-item"><strong>Version:</strong> <span>${sections.version}</span></div>`;
                if (sections.author) html += `<div class="doc-item"><strong>Author:</strong> <span>${sections.author}</span></div>`;
                html += '</div></div>';
            }
            
            // Description Section
            if (sections.description) {
                html += '<div class="doc-section">';
                html += '<h4><span class="section-icon">📝</span>Description</h4>';
                html += `<div class="doc-description">${sections.description.replace(/\n/g, '<br>')}</div>`;
                html += '</div>';
            }
            
            // Tags Section
            if (sections.tags && Array.isArray(sections.tags)) {
                html += '<div class="doc-section">';
                html += '<h4><span class="section-icon">🏷️</span>Tags</h4>';
                html += '<div class="doc-tags">';
                sections.tags.forEach(tag => {
                    html += `<span class="doc-tag">${tag}</span>`;
                });
                html += '</div></div>';
            }
            
            // Examples Section
            if (sections.examples && Array.isArray(sections.examples)) {
                html += '<div class="doc-section">';
                html += '<h4><span class="section-icon">💡</span>Example Queries</h4>';
                html += '<div class="doc-examples">';
                sections.examples.forEach(example => {
                    html += `<div class="doc-example">"${example}"</div>`;
                });
                html += '</div></div>';
            }
            
            // Capabilities Section
            if (sections.capabilities_detail) {
                html += '<div class="doc-section">';
                html += '<h4><span class="section-icon">⚡</span>Capabilities</h4>';
                html += '<div class="doc-capabilities">';
                
                if (sections.capabilities_detail.research_depth) {
                    const research = sections.capabilities_detail.research_depth;
                    html += '<div class="capability-subsection">';
                    html += '<h5>Research Depth</h5>';
                    if (research.supported) html += '<div class="capability-item">✅ Multi-level research supported</div>';
                    if (research.levels) html += `<div class="capability-item">📊 Levels: ${research.levels.join(', ')}</div>`;
                    if (research.sources) html += `<div class="capability-item">🔍 Sources: ${research.sources.join(', ')}</div>`;
                    html += '</div>';
                }
                
                if (sections.capabilities_detail.report_generation) {
                    const reports = sections.capabilities_detail.report_generation;
                    html += '<div class="capability-subsection">';
                    html += '<h5>Report Generation</h5>';
                    if (reports.supported) html += '<div class="capability-item">✅ Multiple report styles</div>';
                    if (reports.styles) html += `<div class="capability-item">📄 Styles: ${reports.styles.join(', ')}</div>`;
                    html += '</div>';
                }
                
                html += '</div></div>';
            }
            
            // Performance Section
            if (sections.performance) {
                html += '<div class="doc-section">';
                html += '<h4><span class="section-icon">📈</span>Performance Metrics</h4>';
                html += '<div class="doc-grid">';
                
                // Handle all performance metrics dynamically
                Object.keys(sections.performance).forEach(key => {
                    const value = sections.performance[key];
                    const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    let formattedValue = value;
                    
                    // Format specific keys
                    if (key.includes('time_ms')) {
                        formattedValue = `${value}ms`;
                    } else if (key.includes('seconds')) {
                        formattedValue = `${value}s`;
                    } else if (key.includes('mb')) {
                        formattedValue = `${value}MB`;
                    }
                    
                    html += `<div class="doc-item"><strong>${formattedKey}:</strong> <span>${formattedValue}</span></div>`;
                });
                
                html += '</div></div>';
            }
            
            // Use Cases Section
            if (sections.documentation && sections.documentation.use_cases) {
                const useCases = sections.documentation.use_cases;
                html += '<div class="doc-section">';
                html += '<h4><span class="section-icon">🎯</span>When to Use</h4>';
                
                if (useCases.when_to_use && Array.isArray(useCases.when_to_use)) {
                    html += '<div class="use-cases"><h5>✅ Ideal for:</h5><ul>';
                    useCases.when_to_use.forEach(useCase => {
                        html += `<li>${useCase}</li>`;
                    });
                    html += '</ul></div>';
                }
                
                if (useCases.when_not_to_use && Array.isArray(useCases.when_not_to_use)) {
                    html += '<div class="use-cases"><h5>❌ Avoid for:</h5><ul>';
                    useCases.when_not_to_use.forEach(useCase => {
                        html += `<li>${useCase}</li>`;
                    });
                    html += '</ul></div>';
                }
                
                html += '</div>';
            }
            
            // Raw Documentation (collapsible)
            html += '<div class="doc-section">';
            html += '<details class="raw-docs">';
            html += '<summary><span class="section-icon">🔧</span>View Raw Documentation</summary>';
            html += `<pre><code>${this.escapeHtml(documentation)}</code></pre>`;
            html += '</details>';
            html += '</div>';
            
            html += '</div>';
            return html;
            
        } catch (error) {
            console.warn('Failed to parse documentation, showing raw:', error);
            return `<div class="raw-docs-fallback">
                <h4>Documentation</h4>
                <pre><code>${this.escapeHtml(documentation)}</code></pre>
            </div>`;
        }
    }

    parseYamlSections(yamlText) {
        const sections = {};
        const lines = yamlText.split('\n');
        let currentSection = null;
        let currentList = null;
        let multilineValue = null;
        let multilineKey = null;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();
            
            // Skip empty lines and comments
            if (!trimmed || trimmed.startsWith('#')) continue;
            
            // Handle multiline values (| syntax)
            if (multilineKey && line.startsWith('  ')) {
                // Continuation of multiline value
                multilineValue += (multilineValue ? '\n' : '') + line.substring(2);
                continue;
            } else if (multilineKey) {
                // End of multiline value
                sections[multilineKey] = multilineValue;
                multilineKey = null;
                multilineValue = null;
            }
            
            // Check for multiline indicator (|)
            if (line.match(/^[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*\|$/)) {
                const key = line.split(':')[0].trim();
                multilineKey = key;
                multilineValue = '';
                continue;
            }
            
            // Check for top-level keys (no indentation)
            if (line.match(/^[a-zA-Z_][a-zA-Z0-9_]*\s*:/)) {
                const [key, ...valueParts] = line.split(':');
                const value = valueParts.join(':').trim();
                
                if (value) {
                    // Simple key-value pair
                    sections[key.trim()] = value.replace(/^["']|["']$/g, '');
                } else {
                    // Start of a section
                    currentSection = key.trim();
                    sections[currentSection] = {};
                }
                currentList = null;
                continue;
            }
            
            // Check for list items
            if (trimmed.startsWith('-')) {
                const item = trimmed.substring(1).trim();
                
                if (currentSection) {
                    if (!Array.isArray(sections[currentSection])) {
                        sections[currentSection] = [];
                    }
                    sections[currentSection].push(item.replace(/^["']|["']$/g, ''));
                }
                continue;
            }
            
            // Check for nested key-value pairs
            if (currentSection && line.match(/^\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:/)) {
                const [key, ...valueParts] = line.split(':');
                const value = valueParts.join(':').trim();
                
                if (typeof sections[currentSection] !== 'object' || Array.isArray(sections[currentSection])) {
                    sections[currentSection] = {};
                }
                
                sections[currentSection][key.trim()] = value.replace(/^["']|["']$/g, '');
            }
        }
        
        // Handle final multiline value if file ends with it
        if (multilineKey && multilineValue) {
            sections[multilineKey] = multilineValue;
        }
        
        return sections;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderMessages() {
        const messagesContainer = document.getElementById('chat-messages');
        const messages = stateManager.getMessages(this.currentConversationId);
        const isTyping = stateManager.isTyping(this.currentConversationId);
        
        // Clear existing messages
        messagesContainer.innerHTML = '';
        
        if (!this.currentConversationId) {
            // Show welcome message
            messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Welcome to Bindu Agent Chat</h2>
                    <p>Start a conversation with your AI agent. Select an existing conversation from the sidebar or create a new one.</p>
                    <div class="example-prompts">
                        <h3>Try these examples:</h3>
                        <div class="prompt-card" data-prompt="Hello! Can you introduce yourself?">
                            <h4>👋 Introduction</h4>
                            <p>Hello! Can you introduce yourself?</p>
                        </div>
                        <div class="prompt-card" data-prompt="What can you help me with?">
                            <h4>🔍 Capabilities</h4>
                            <p>What can you help me with?</p>
                        </div>
                        <div class="prompt-card" data-prompt="Show me your skills and abilities">
                            <h4>⚡ Skills</h4>
                            <p>Show me your skills and abilities</p>
                        </div>
                    </div>
                </div>
            `;
            
        } else if (messages.length === 0) {
            // Show welcome message with prompts for active but empty conversation
            messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <h2>Welcome to Bindu Agent Chat</h2>
                    <p>Start a conversation with your AI agent. Try these example prompts:</p>
                    <div class="example-prompts">
                        <h3>Try these examples:</h3>
                        <div class="prompt-card" data-prompt="Hello! Can you introduce yourself?">
                            <h4>👋 Introduction</h4>
                            <p>Hello! Can you introduce yourself?</p>
                        </div>
                        <div class="prompt-card" data-prompt="What can you help me with?">
                            <h4>🔍 Capabilities</h4>
                            <p>What can you help me with?</p>
                        </div>
                        <div class="prompt-card" data-prompt="Show me your skills and abilities">
                            <h4>⚡ Skills</h4>
                            <p>Show me your skills and abilities</p>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Re-attach prompt card listeners for both welcome scenarios
        if (!this.currentConversationId || messages.length === 0) {
            // Add fresh listeners with proper cleanup
            const promptCards = messagesContainer.querySelectorAll('.prompt-card');
            promptCards.forEach(card => {
                // Clone and replace to remove existing listeners
                const newCard = card.cloneNode(true);
                card.parentNode.replaceChild(newCard, card);
                
                // Add fresh listener
                newCard.addEventListener('click', (e) => {
                    e.preventDefault();
                    const prompt = newCard.dataset.prompt;
                    if (prompt) {
                        const messageInput = document.getElementById('message-input');
                        if (messageInput) {
                            messageInput.value = prompt;
                            this.updateCharCount();
                            this.updateSendButton();
                            messageInput.focus();
                            
                            // Auto-send the prompt
                            this.sendMessage();
                        }
                    }
                });
            });
            
            return;
        }
        
        // Render messages
        messages.forEach(message => {
            const messageEl = MessageComponent.create(message);
            messagesContainer.appendChild(messageEl);
        });
        
        // Add typing indicator if needed (only if no messages or last message is from user)
        const lastMessage = messages[messages.length - 1];
        const shouldShowTyping = isTyping && (!lastMessage || lastMessage.role === 'user');
        
        if (shouldShowTyping) {
            const typingIndicator = TypingIndicator.create();
            typingIndicator.id = 'typing-indicator';
            messagesContainer.appendChild(typingIndicator);
        }
        
        // Auto-scroll to bottom
        this.scrollToBottom();
    }

    getAgentBaseUrl() {
        // Get agent URL from settings (defaults to /api)
        const settings = stateManager.get('settings');
        return settings.agentUrl || '/api'; // <--- Changed this
    }

    // ============================================================================
    // Payment Management (from old app.js)
    // ============================================================================
    
    async handlePaymentRequired(originalRequest) {
        try {
            Toast.info('Time to pay the piper!');

            // Start payment session (no auth required - public endpoint)
            const sessionResponse = await fetch(`${this.getAgentBaseUrl()}/api/start-payment-session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!sessionResponse.ok) {
                throw new Error('Failed to start payment session');
            }

            const sessionData = await sessionResponse.json();
            const { session_id, browser_url } = sessionData;

            Toast.info('🌐 Opening payment page...');

            // Open payment page in new window
            const paymentWindow = window.open(browser_url, '_blank', 'width=600,height=800');

            if (!paymentWindow) {
                Toast.error('❌ Please allow popups to complete payment');
                return false;
            }

            Toast.info('Waiting for your wallet to wake up...');

            // Poll for payment completion
            const maxAttempts = 60; // 5 minutes (5 second intervals)
            let attempts = 0;

            while (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
                attempts++;

                const statusResponse = await fetch(`${this.getAgentBaseUrl()}/api/payment-status/${session_id}`);

                if (!statusResponse.ok) continue;

                const statusData = await statusResponse.json();

                if (statusData.status === 'completed' && statusData.payment_token) {
                    this.paymentToken = statusData.payment_token;
                    Toast.success('💰 Payment approved! Your agent is now caffeinated.');

                    // Close payment window if still open
                    if (paymentWindow && !paymentWindow.closed) {
                        paymentWindow.close();
                    }

                    return true;
                }

                if (statusData.status === 'failed') {
                    Toast.error('❌ Payment failed: ' + (statusData.error || 'Unknown error'));
                    return false;
                }
            }

            Toast.error('⏱️ Payment timeout. Please try again.');
            return false;

        } catch (error) {
            console.error('Payment error:', error);
            Toast.error('❌ Payment error: ' + error.message);
            return false;
        }
    }

    getPaymentHeaders() {
        if (!this.paymentToken) return {};

        // Ensure payment token is properly encoded
        const cleanToken = this.paymentToken.trim();

        // Check for non-ASCII characters
        if (!/^[\x00-\x7F]*$/.test(cleanToken)) {
            console.error('Payment token contains non-ASCII characters');
            this.paymentToken = null;
            return {};
        }

        return { 'X-PAYMENT': cleanToken };
    }

    // ============================================================================
    // Authentication Management (from old app.js) - UPDATED FOR STATE MANAGER
    // ============================================================================
    
    getAuthHeaders() {
        if (!this.authToken) return {};

        // Ensure token is properly encoded (trim and validate ASCII)
        const cleanToken = this.authToken.trim();

        // Check for non-ASCII characters that would cause ISO-8859-1 errors
        if (!/^[\x00-\x7F]*$/.test(cleanToken)) {
            console.error('Auth token contains non-ASCII characters');
            Toast.warning('⚠️ Invalid auth token format. Please re-enter your token.');
            this.authToken = null;
            return {};
        }

        return { 'Authorization': `Bearer ${cleanToken}` };
    }

    openAuthSettings() {
        const token = prompt('Enter JWT token (leave empty to clear):');
        if (token !== null) {
            this.authToken = token || null;
            // Update API client token to maintain sync
            this.apiClient.setAuthToken(this.authToken);
            if (this.authToken) {
                Toast.success('✅ Token saved');
            } else {
                Toast.info('Token cleared');
            }
        }
    }

    // ============================================================================
    // A2A Protocol Compliant Task Management (from old app.js)
    // ============================================================================

    generateTaskId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();

        if (!message) return;

        input.value = '';
        const sendButton = document.getElementById('send-btn');
        sendButton.disabled = true;
        
        // Show sending state
        this.setSendButtonSending(true);

        try {
            // Task ID logic based on A2A protocol:
            // - Non-terminal states (input-required, auth-required): REUSE task ID
            // - Terminal states (completed, failed, canceled): CREATE new task
            // - No current task: CREATE new task
            let taskId;
            const referenceTaskIds = [];

            const isNonTerminalState = this.currentTaskState &&
                (this.currentTaskState === 'input-required' || this.currentTaskState === 'auth-required');

            if (this.replyToTaskId) {
                // Explicit reply to a specific task - always create new task
                taskId = this.generateTaskId();
                referenceTaskIds.push(this.replyToTaskId);
            } else if (isNonTerminalState && this.currentTaskId) {
                // Continue same task for non-terminal states
                taskId = this.currentTaskId;
                console.log('🔄 Continuing non-terminal task:', taskId);
            } else if (this.currentTaskId) {
                // Terminal state or no state - create new task, reference previous
                taskId = this.generateTaskId();
                referenceTaskIds.push(this.currentTaskId);
                console.log('🆕 Creating new task, referencing previous:', this.currentTaskId);
            } else {
                // First message in conversation
                taskId = this.generateTaskId();
                console.log('🌟 Creating first task:', taskId);
            }

            const messageId = this.generateTaskId();
            const newContextId = this.contextId || this.generateTaskId();

            console.log('📤 Sending message with A2A protocol:', {
                taskId,
                contextId: newContextId,
                existingContextId: this.contextId,
                isNewContext: !this.contextId,
                currentState: this.currentTaskState,
                isNonTerminalState,
                referenceTaskIds
            });

            // Show typing indicator immediately for better UX
            this.showTypingIndicator();

            const requestBody = {
                jsonrpc: '2.0',
                method: 'message/send',
                params: {
                    message: {
                        role: 'user',
                        parts: [{ kind: 'text', text: message }],
                        kind: 'message',
                        messageId: messageId,
                        contextId: newContextId,
                        taskId: taskId,
                        ...(referenceTaskIds.length > 0 && { referenceTaskIds })
                    },
                    configuration: {
                        acceptedOutputModes: ['application/json']
                    }
                },
                id: this.generateTaskId()
            };

            const response = await fetch(`${this.getAgentBaseUrl()}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders(),
                    ...this.getPaymentHeaders()
                },
                body: JSON.stringify(requestBody)
            });

            // Handle 401 Unauthorized (Auth Required)
            if (response.status === 401) {
                Toast.error('🔒 Authentication required. Please provide your JWT token.');
                this.openAuthSettings();
                throw new Error('Authentication required');
            }

            // Handle 402 Payment Required
            if (response.status === 402) {
                const paymentSuccess = await this.handlePaymentRequired(requestBody);
                if (paymentSuccess) {
                    // Retry the exact same request with payment token
                    const retryResponse = await fetch(`${this.getAgentBaseUrl()}/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...this.getAuthHeaders(),
                            ...this.getPaymentHeaders()
                        },
                        body: JSON.stringify(requestBody)
                    });

                    if (!retryResponse.ok) throw new Error('Failed to send message after payment');

                    const result = await retryResponse.json();
                    if (result.error) throw new Error(result.error.message || 'Unknown error');

                    const task = result.result;
                    const taskContextId = task.context_id || task.contextId;

                    console.log('💳 Payment retry successful, received task:', {
                        taskId: task.id,
                        contextId: taskContextId
                    });

                    // Update state with new task
                    this.currentTaskId = task.id;
                    this.currentTaskState = null; // Will be updated by polling

                    if (taskContextId) {
                        const isNewContext = !this.contextId;
                        this.contextId = taskContextId;

                        if (isNewContext) {
                            await this.loadContexts();
                        }
                    }

                    const displayMessage = this.replyToTaskId
                        ? `↩️ Replying to previous message...\n\n${message}` 
                        : message;
                    this.addMessage(displayMessage, 'user', task.id);

                    this.clearReply();
                    this.addThinkingIndicator('thinking-indicator', task.id);
                    this.pollTaskStatus(task.id);

                    return;
                } else {
                    throw new Error('Payment required but not completed');
                }
            }

            if (!response.ok) throw new Error('Failed to send message');

            const result = await response.json();
            if (result.error) throw new Error(result.error.message || 'Unknown error');

            const task = result.result;
            const taskContextId = task.context_id || task.contextId;

            console.log('✅ Message sent successfully, received task:', {
                taskId: task.id,
                contextId: taskContextId,
                context_id: task.context_id,
                previousContextId: this.contextId
            });

            // Update currentTaskId to the NEW task
            this.currentTaskId = task.id;
            this.currentTaskState = null; // Will be determined by polling

            // Check if this is a new context
            const isNewContext = taskContextId && !this.contextId;

            if (taskContextId) {
                this.contextId = taskContextId;
            }

            console.log('🔄 State updated:', {
                currentTaskId: this.currentTaskId,
                contextId: this.contextId,
                isNewContext
            });

            // Reload contexts if new context was created
            if (isNewContext) {
                await this.loadContexts();
            }

            const displayMessage = this.replyToTaskId
                ? `↩️ Replying to previous message...\n\n${message}` 
                : message;
            this.addMessage(displayMessage, 'user', task.id);

            this.clearReply();

            // Add thinking indicator immediately
            this.addThinkingIndicator('thinking-indicator', task.id);

            this.pollTaskStatus(task.id);

        } catch (error) {
            console.error('❌ Error sending message:', error);
            Toast.error('Failed to send message: ' + error.message);
            // Re-enable send button on error
            sendButton.disabled = false;
            this.eventInProgress = false;
            this.setSendButtonSending(false);
        }
    }

    async loadContexts() {
        try {
            console.log('Loading contexts...');
            const response = await fetch(`${this.getAgentBaseUrl()}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders(),
                    ...this.getPaymentHeaders()
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'contexts/list',
                    params: { length: 50 },
                    id: this.generateTaskId()
                })
            });

            if (response.status === 401) {
                console.warn('Authentication required for contexts');
                Toast.warning('🔒 Authentication required to load contexts. Please provide your JWT token.');
                return;
            }

            if (!response.ok) throw new Error('Failed to load contexts');

            const result = await response.json();
            if (result.error) throw new Error(result.error.message || 'Unknown error');

            const serverContexts = result.result || [];
            this.contexts = serverContexts.map(ctx => ({
                id: ctx.context_id,
                taskCount: ctx.task_count || 0,
                taskIds: ctx.task_ids || [],
                timestamp: Date.now(),
                firstMessage: 'Loading...'
            }));

            for (const ctx of this.contexts) {
                if (ctx.taskIds.length > 0) {
                    await this.loadContextPreview(ctx);
                }
            }

            this.renderConversationsList();
        } catch (error) {
            console.error('Error loading contexts:', error);
            this.renderConversationsList();
        }
    }

    createNewConversation() {
        const conversation = stateManager.createConversation();
        stateManager.setActiveConversation(conversation.id);
        this.currentConversationId = conversation.id;
        console.log('Created new conversation:', conversation.id);
    }

    async loadContextPreview(ctx) {
        try {
            const response = await fetch(`${this.getAgentBaseUrl()}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders(),
                    ...this.getPaymentHeaders()
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'tasks/get',
                    params: { taskId: ctx.taskIds[0] },
                    id: this.generateTaskId()
                })
            });

            if (!response.ok) return;

            const result = await response.json();
            if (result.error) return;

            const task = result.result;
            const history = task.history || [];

            for (const msg of history) {
                if (msg.role === 'user') {
                    const parts = msg.parts || [];
                    const textParts = parts
                        .filter(part => part.kind === 'text')
                        .map(part => part.text);
                    if (textParts.length > 0) {
                        ctx.firstMessage = textParts[0].substring(0, 50);
                        break;
                    }
                }
            }

            if (task.status && task.status.timestamp) {
                try {
                    const timestamp = new Date(task.status.timestamp);
                    // Check if the date is valid
                    if (isNaN(timestamp.getTime())) {
                        console.warn('Invalid timestamp format:', task.status.timestamp);
                        // Keep the current timestamp (set earlier)
                    } else {
                        ctx.timestamp = timestamp.getTime();
                    }
                } catch (error) {
                    console.warn('Error parsing timestamp:', error, task.status.timestamp);
                    // Keep the current timestamp (set earlier)
                }
            }
        } catch (error) {
            console.error('Error loading context preview:', error);
        }
    }

    updateContextList() {
        const container = document.getElementById('conversations-list');
        if (!container) return;

        if (this.contexts.length === 0) {
            container.innerHTML = '<div class="loading">No conversations yet</div>';
            return;
        }

        const sortedContexts = [...this.contexts].sort((a, b) => b.timestamp - a.timestamp);
        const colors = ['color-blue', 'color-green', 'color-purple', 'color-orange', 'color-pink', 'color-teal'];

        let html = sortedContexts.map((ctx, index) => {
            const isActive = ctx.id === this.contextId;
            const time = this.formatTime(ctx.timestamp);
            const preview = ctx.firstMessage || 'New conversation';
            
            // Get actual message count from state manager
            const messages = stateManager.getMessages(ctx.id) || [];
            const messageCount = messages.length;
            
            const contextShortId = ctx.id.substring(0, 8);
            const colorClass = colors[index % colors.length];

            return `
                <div class="conversation-item ${isActive ? 'active' : ''}" onclick="window.binduUI.switchToContext('${ctx.id}')">
                    <div class="conversation-content">
                        <div class="conversation-title">
                            <div class="context-badge ${colorClass}">${contextShortId}</div>
                            <span>${preview}</span>
                        </div>
                        <div class="conversation-meta">
                            <span>${messageCount} message${messageCount !== 1 ? 's' : ''}</span>
                            <span>${time}</span>
                        </div>
                    </div>
                    <button class="delete-conversation-btn" onclick="event.stopPropagation(); window.binduUI.confirmClearContext('${ctx.id}')" title="Clear context">×</button>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    // Add missing methods referenced in HTML
    async switchToContext(contextId) {
        this.contextId = contextId;
        
        // Update active state in UI
        document.querySelectorAll('.context-item').forEach(item => {
            item.classList.toggle('active', item.dataset.contextId === contextId);
        });

        // Update context indicator
        this.updateContextIndicator();

        // Load conversation history for this context
        await this.loadConversationHistory(contextId);
        
        console.log('Switched to context:', contextId);
    }

    async confirmClearContext(contextId) {
        if (!confirm(`Clear all tasks in context ${contextId.substring(0, 8)}...?`)) {
            return;
        }
        await this.clearContext(contextId);
    }

    async clearContext(contextId) {
        try {
            await this.apiClient.clearContext(contextId);
            Toast.success('Context cleared successfully');
            
            // Reload contexts
            await this.loadContexts();
            
            // If we cleared the active context, create a new one
            if (contextId === this.contextId) {
                this.contextId = null;
                this.currentTaskId = null;
                this.currentTaskState = null;
                this.updateContextIndicator();
            }
        } catch (error) {
            console.error('Failed to clear context:', error);
            Toast.error('Failed to clear context');
        }
    }

    updateContextIndicator() {
        const indicator = document.getElementById('context-indicator-text');
        if (indicator) {
            if (this.contextId) {
                const shortId = this.contextId.substring(0, 8);
                indicator.textContent = `Active Context: ${shortId}`;
            } else {
                indicator.textContent = 'No active context - Start a new conversation';
            }
        }
    }

    formatTime(timestamp) {
        try {
            const date = new Date(timestamp);
            // Check if the date is valid
            if (isNaN(date.getTime())) {
                console.warn('Invalid timestamp in formatTime:', timestamp);
                return 'Unknown time';
            }
            
            const now = new Date();
            const diff = now - date;
            const hours = Math.floor(diff / (1000 * 60 * 60));

            if (hours < 24) {
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            } else {
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }
        } catch (error) {
            console.warn('Error formatting time:', error, timestamp);
            return 'Unknown time';
        }
    }

    setReplyTo(taskId) {
        this.replyToTaskId = taskId;
        const indicator = document.getElementById('reply-indicator');
        if (indicator) {
            const text = document.getElementById('reply-text');
            if (text) {
                text.textContent = `💬 Replying to previous message`;
            }
            indicator.classList.add('visible');
        }
        document.getElementById('message-input').focus();
    }

    cancelReply() {
        this.replyToTaskId = null;
        const indicator = document.getElementById('reply-indicator');
        if (indicator) {
            indicator.classList.remove('visible');
        }
        document.getElementById('message-input').focus();
    }

    setSendButtonSending(isSending) {
        const sendButton = document.getElementById('send-btn');
        if (!sendButton) return;

        if (isSending) {
            // Change to loading/spinning icon
            sendButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                    <style>
                        @keyframes spin {
                            to { transform: rotate(360deg); }
                        }
                        .spin {
                            animation: spin 1s linear infinite;
                            transform-origin: center;
                        }
                    </style>
                    <path class="spin" d="M12 2v4c0 1.1.9 2 2 2h4c0-3.31-2.69-6-6-6zm0 16v4c3.31 0 6-2.69 6-6h-4c-1.1 0-2 .9-2 2zm-6-6H2c0 3.31 2.69 6 6 6v-4c-1.1 0-2-.9-2-2zm0-4c-1.1 0-2 .9-2 2h4c0-1.1.9-2 2-2V2c-3.31 0-6 2.69-6 6z"/>
                </svg>
            `;
            sendButton.classList.add('sending');
        } else {
            // Reset to normal send icon
            sendButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            `;
            sendButton.classList.remove('sending');
        }
    }

    enableSendButton() {
        const sendButton = document.getElementById('send-btn');
        if (sendButton) {
            sendButton.disabled = false;
            this.eventInProgress = false;
            this.setSendButtonSending(false);
        }
        this.updateSendButton();
    }

    openFeedbackModal(taskId) {
        // Use Modal class for consistency
        const modal = document.getElementById('feedback-modal');
        const previewElement = document.getElementById('feedback-message-preview');
        const feedbackRating = document.getElementById('feedback-rating');
        const feedbackText = document.getElementById('feedback-text');
        
        // Find the user message that prompted this AI response
        if (previewElement && this.currentConversationId) {
            const messages = stateManager.getMessages(this.currentConversationId);
            let userMessage = "Previous conversation";
            
            // Look for the most recent user message before an agent message with this taskId
            for (let i = messages.length - 1; i >= 0; i--) {
                const message = messages[i];
                if (message.role === 'user') {
                    // Get the first 50 characters of the user message
                    const messageText = message.parts && message.parts[0] ? message.parts[0].text : message.text || '';
                    userMessage = messageText.length > 50 ? messageText.substring(0, 50) + '...' : messageText;
                    break;
                }
            }
            
            previewElement.textContent = `"${userMessage}"`;
        }
        
        // Reset form to default values like old UI
        if (feedbackRating) {
            feedbackRating.value = '5';  // Default to 5 stars
        }
        if (feedbackText) {
            feedbackText.value = '';  // Clear text
        }
        
        if (modal) {
            modal.dataset.taskId = taskId;  // Store task ID internally for submission
            Modal.show('feedback-modal');  // Use Modal class
        }
    }

    closeFeedbackModal() {
        // Use Modal class for consistency
        const modal = document.getElementById('feedback-modal');
        if (modal) {
            Modal.hide('feedback-modal');  // Use Modal class
            
            // Reset form fields
            const feedbackText = document.getElementById('feedback-text');
            const feedbackRating = document.getElementById('feedback-rating');
            if (feedbackText) feedbackText.value = '';
            if (feedbackRating) feedbackRating.value = '5';
        }
    }

    async submitFeedback() {
        // Exactly like bindu\ui old implementation
        const modal = document.getElementById('feedback-modal');
        if (!modal) return;
        
        const taskId = modal.dataset.taskId;
        const feedbackText = document.getElementById('feedback-text');
        const feedbackRating = document.getElementById('feedback-rating');
        
        const feedback = feedbackText ? feedbackText.value.trim() : '';
        const rating = feedbackRating ? parseInt(feedbackRating.value) : 5;

        try {
            await this.apiClient.submitFeedback(taskId, feedback, rating);
            Toast.success('Thank you for your feedback!');
            this.closeFeedbackModal();  // Use correct method
        } catch (error) {
            console.error('Failed to submit feedback:', error);
            Toast.error('Failed to submit feedback');
        }
    }

    showDetailedFeedback(taskId) {
        // For backward compatibility
        this.openFeedbackModal(taskId);
    }

    clearReply() {
        this.replyToTaskId = null;
        const indicator = document.getElementById('reply-indicator');
        if (indicator) {
            indicator.classList.remove('visible');
        }
    }

    updateCharCount() {
        const messageInput = document.getElementById('message-input');
        const charCount = document.getElementById('char-count');
        const count = messageInput.value.length;
        charCount.textContent = `${count} / 4000`;
    }

    // ============================================================================
    // Task Polling (from old app.js) - CRITICAL MISSING METHOD
    // ============================================================================
    
    async pollTaskStatus(taskId) {
        let attempts = 0;
        const maxAttempts = 300;
        const thinkingId = 'thinking-indicator';

        const poll = async () => {
            if (attempts >= maxAttempts) {
                this.removeThinkingIndicator(thinkingId);
                this.addMessage('⏱️ Timeout: Task did not complete', 'status');
                this.currentTaskId = null;
                this.currentTaskState = null;
                // Re-enable send button on timeout
                this.enableSendButton();
                return;
            }

            attempts++;

            try {
                const task = await this.apiClient.getTask(taskId);
                const state = task.status.state;

                // Terminal states - task is now IMMUTABLE
                if (state === 'completed' || state === 'failed' || state === 'canceled') {
                    this.removeThinkingIndicator(thinkingId);
                    // Keep currentTaskId and mark as terminal
                    this.currentTaskId = taskId;
                    this.currentTaskState = state;  // Terminal state
                    if (!this.taskHistory.includes(taskId)) {
                        this.taskHistory.push(taskId);
                    }
                    console.log('Task status update:', task);
                    
                    // Re-enable send button when agent responds
                    this.enableSendButton();
                    
                    if (state === 'completed') {
                        const responseText = this.extractResponse(task);
                        this.addMessage(responseText, 'agent', taskId, state);
                        this.showFeedbackOption(taskId);
                    }
                    else if (state === 'failed') {
                        const error =
                            task.metadata?.error ||
                            task.metadata?.error_message ||
                            task.status?.error ||
                            task.error ||
                            'Task failed';

                        this.addMessage(`❌ Task failed: ${error}`, 'status');
                        const responseText = this.extractResponse(task);
                        this.addMessage(responseText, 'agent', taskId, state);
                    }
                    else {
                        this.addMessage('⚠️ Task was canceled', 'status');
                    }

                    // Clear payment token when task reaches terminal state
                    // Next message will create NEW task and require NEW payment
                    if (this.paymentToken) {
                        console.log('Task completed - clearing payment token for next task');
                        this.paymentToken = null;
                    }

                    // Reload contexts to update task counts
                    await this.loadContexts();
                }
                // Non-terminal states - task still MUTABLE, waiting for input
                else if (state === 'input-required' || state === 'auth-required') {
                    this.removeThinkingIndicator(thinkingId);
                    // Keep currentTaskId and mark as non-terminal
                    this.currentTaskId = taskId;
                    this.currentTaskState = state;  // Non-terminal state
                    if (!this.taskHistory.includes(taskId)) {
                        this.taskHistory.push(taskId);
                    }
                    const responseText = this.extractResponse(task);
                    this.addMessage(responseText, 'agent', taskId, state);

                    // Reload contexts to update task counts
                    await this.loadContexts();
                }
                // Working states - continue polling
                else {
                    setTimeout(poll, 1000); // Poll every 1 second
                }
            } catch (error) {
                console.error('Error polling task status:', error);
                this.removeThinkingIndicator(thinkingId);
                this.addMessage('❌ Failed to get task status', 'status');
                this.currentTaskId = null;
                this.currentTaskState = null;
            }
        };

        poll();
    }

    // ============================================================================
    // Message Display Functions (from old app.js) - CRITICAL MISSING METHODS
    // ============================================================================

    addMessage(content, role, taskId = null, status = null) {
        const message = {
            messageId: crypto.randomUUID(),
            role: role,
            parts: [{ kind: 'text', text: content }],
            timestamp: new Date().toISOString(),
            taskId: taskId,
            status: status || 'sent',
            // Add feedback state for persistence
            feedbackEnabled: role === 'agent' && status === 'completed'
        };

        // Remove typing indicator when agent message is added
        if (role === 'agent') {
            this.removeTypingIndicator();
        }

        // Add to state manager
        if (this.currentConversationId) {
            stateManager.addMessage(this.currentConversationId, message);
        }

        // Also add to local task history for compatibility
        if (taskId && role === 'agent') {
            if (!this.taskHistory.includes(taskId)) {
                this.taskHistory.push(taskId);
            }
        }

        // Update UI
        this.renderMessages();
        this.scrollToBottom();
    }

    addThinkingIndicator(elementId, taskId = null) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;

        // Remove existing thinking indicator
        this.removeThinkingIndicator(elementId);

        const indicator = TypingIndicator.create();
        indicator.id = elementId;
        if (taskId) {
            indicator.dataset.taskId = taskId;
        }
        
        messagesContainer.appendChild(indicator);
        this.scrollToBottom();
    }

    removeThinkingIndicator(elementId) {
        const indicator = document.getElementById(elementId);
        if (indicator) {
            indicator.remove();
        }
    }

    extractResponse(task) {
        // Extract response text from task artifacts (same as old implementation)
        const artifacts = task.artifacts || [];
        if (artifacts.length > 0) {
            const artifact = artifacts[artifacts.length - 1]; // Use LAST artifact only
            const parts = artifact.parts || [];
            const textParts = parts
                .filter(part => part.kind === 'text')
                .map(part => part.text);
            if (textParts.length > 0) return textParts.join('\n'); // Single \n like old
        }

        // Fallback to history if no artifacts (same as old implementation)
        const history = task.history || [];
        for (let i = history.length - 1; i >= 0; i--) {
            const msg = history[i];
            if (msg.role === 'assistant' || msg.role === 'agent') { // Check both roles
                const parts = msg.parts || [];
                const textParts = parts
                    .filter(part => part.kind === 'text')
                    .map(part => part.text);
                if (textParts.length > 0) return textParts.join('\n'); // Single \n like old
            }
        }

        return '✅ Task completed but no response found'; // Same as old
    }

    updateSendButton() {
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const hasText = messageInput.value.trim().length > 0;
        
        // Debug logging
        console.log('updateSendButton:', {
            hasText,
            currentConversationId: this.currentConversationId,
            isProcessing: this.processingConversations.has(this.currentConversationId),
            sendBtnDisabled: sendBtn.disabled
        });
        
        // Reset button content if not processing
        if (!this.processingConversations.has(this.currentConversationId)) {
            sendBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
            `;
        }
        
        sendBtn.disabled = !hasText || !this.currentConversationId || this.processingConversations.has(this.currentConversationId);
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chat-messages');
        if (stateManager.get('settings').autoScroll) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        // Remove any existing typing indicators
        this.removeTypingIndicator();
        
        // Create and add new typing indicator
        const typingIndicator = TypingIndicator.create();
        typingIndicator.id = 'typing-indicator';
        messagesContainer.appendChild(typingIndicator);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const existingIndicator = document.getElementById('typing-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
    }

    showSettingsModal() {
        const settings = stateManager.get('settings');
        
        // Populate form
        document.getElementById('agent-url').value = settings.agentUrl;
        document.getElementById('auth-token').value = settings.authToken || '';
        document.getElementById('auto-scroll').checked = settings.autoScroll;
        
        Modal.show('settings-modal');
    }

    async saveSettings() {
        const agentUrl = document.getElementById('agent-url').value;
        const authToken = document.getElementById('auth-token').value;
        const autoScroll = document.getElementById('auto-scroll').checked;
        
        // Update settings
        stateManager.updateSettings({
            agentUrl,
            authToken,
            autoScroll,
        });
        
        // Reinitialize API client
        this.initializeApiClient();
        
        // Reload data
        await this.loadInitialData();
        
        Modal.hide('settings-modal');
        Toast.success('Settings saved successfully');
    }
    
    async deleteConversation(conversationId) {
        try {
            // Check if this is a server context before trying to clear it
            const conversations = stateManager.get('conversations');
            const conversation = conversations.find(c => c.id === conversationId);
            
            if (conversation && conversation.isContext) {
                // Clear context on server first
                await this.apiClient.clearContext(conversationId);
            }
            
            // Remove conversation from state
            stateManager.deleteConversation(conversationId);
            
            // Clear task ID for deleted conversation
            this.conversationTaskIds.delete(conversationId);
            
            // If deleted conversation was active, switch to another or create new one
            if (this.currentConversationId === conversationId) {
                const remainingConversations = stateManager.get('conversations');
                if (remainingConversations.length > 0) {
                    this.switchToConversation(remainingConversations[0].id);
                } else {
                    this.createNewConversation();
                }
            }
            
            Toast.success('Conversation deleted');
        } catch (error) {
            console.error('Failed to delete conversation:', error);
            // Still remove from local state even if server call fails
            stateManager.deleteConversation(conversationId);
            this.conversationTaskIds.delete(conversationId);
            
            if (this.currentConversationId === conversationId) {
                const remainingConversations = stateManager.get('conversations');
                if (remainingConversations.length > 0) {
                    this.switchToConversation(remainingConversations[0].id);
                } else {
                    this.createNewConversation();
                }
            }
            
            Toast.warning('Conversation deleted locally (server cleanup failed)');
        }
    }

    showFeedbackOption(taskId) {
        // Enable feedback on the last agent message with this taskId
        if (!this.currentConversationId) {
            console.warn('Cannot show feedback: No active conversation');
            return;
        }
        
        const messages = stateManager.getMessages(this.currentConversationId);
        const targetMessage = messages.filter(m => m.role === 'agent' && m.taskId === taskId).pop();
        
        if (targetMessage) {
            // Update message to enable feedback
            targetMessage.feedbackEnabled = true;
            stateManager.updateMessage(this.currentConversationId, targetMessage.messageId, targetMessage);
            
            // Re-render to show feedback buttons
            this.renderMessages();
        }
    }

    async submitFeedback(taskId, feedback, rating) {
        try {
            // Add fallback logic from old implementation
            const feedbackText = feedback || `Rating: ${rating}/5`;
            await this.apiClient.submitFeedback(taskId, feedbackText, rating);
            Toast.success('Thank you for your feedback!');
            
            // Remove feedback option by updating message state
            if (this.currentConversationId) {
                const messages = stateManager.getMessages(this.currentConversationId);
                const targetMessage = messages.find(m => m.role === 'agent' && m.taskId === taskId);
                
                if (targetMessage) {
                    targetMessage.feedbackEnabled = false;
                    targetMessage.feedbackSubmitted = true;
                    stateManager.updateMessage(this.currentConversationId, targetMessage.messageId, targetMessage);
                    this.renderMessages();
                }
            }
        } catch (error) {
            console.error('Failed to submit feedback:', error);
            Toast.error('Failed to submit feedback');
        }
    }

    showDetailedFeedback(taskId) {
        // Set task ID in the modal (stored internally, not displayed)
        const modal = document.getElementById('feedback-modal');
        const previewElement = document.getElementById('feedback-message-preview');
        
        if (modal) {
            modal.dataset.taskId = taskId;
        }
        
        // Find the user message that prompted this AI response
        if (previewElement && this.currentConversationId) {
            const messages = stateManager.getMessages(this.currentConversationId);
            let userMessage = "Previous conversation";
            
            // Look for the most recent user message
            for (let i = messages.length - 1; i >= 0; i--) {
                const message = messages[i];
                if (message.role === 'user') {
                    // Get the first 50 characters of the user message
                    const messageText = message.parts && message.parts[0] ? message.parts[0].text : message.text || '';
                    userMessage = messageText.length > 50 ? messageText.substring(0, 50) + '...' : messageText;
                    break;
                }
            }
            
            previewElement.textContent = `"${userMessage}"`;
        }
        
        // Reset form
        const ratingElement = document.getElementById('feedback-rating');
        const textElement = document.getElementById('feedback-text');
        if (ratingElement) ratingElement.value = '5';
        if (textElement) textElement.value = '';
        
        Modal.show('feedback-modal');
    }

    async submitDetailedFeedbackFromModal() {
        const modal = document.getElementById('feedback-modal');
        const taskId = modal.dataset.taskId;
        const rating = document.getElementById('feedback-rating').value;
        const feedbackText = document.getElementById('feedback-text').value;
        
        try {
            await this.apiClient.submitFeedback(taskId, feedbackText, parseInt(rating));
            Toast.success('Thank you for your detailed feedback!');
            Modal.hide('feedback-modal');
        } catch (error) {
            console.error('Failed to submit feedback:', error);
            Toast.error('Failed to submit feedback');
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        stateManager.set('currentTheme', newTheme);
        
        // Add transition effect
        document.body.style.transition = 'background-color 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }

    showLoadingSkeleton(container) {
        container.innerHTML = `
            <div class="skeleton-loader">
                <div class="skeleton-message"></div>
                <div class="skeleton-message"></div>
                <div class="skeleton-message skeleton-short"></div>
            </div>
        `;
    }

    // Note: switchTab function removed since no tabs exist
// Chat is always visible

    extractAuthorFromAgentCard(agentCard) {
        // Extract author from DID extension like old code
        const didExtension = agentCard.capabilities?.extensions?.find(ext => ext.uri?.startsWith('did:'));
        return didExtension?.params?.author || null;
    }

    extractPublicKeyFromAgentCard(agentCard, didDocument) {
        // Extract public key from DID document like old code
        if (didDocument && didDocument.authentication && didDocument.authentication[0]) {
            return didDocument.authentication[0].publicKeyBase58;
        }
        return null;
    }

    showInfoModal() {
        // Show modal first, then load content with small delay for DOM readiness
        Modal.show('info-modal');
        setTimeout(() => this.loadAgentInfo(), 50);  // Small delay for DOM readiness
    }

    async loadAgentInfo() {
        const infoModalContent = document.getElementById('info-modal-content');
        const agentCard = stateManager.get('agentCard');
        const skills = stateManager.get('skills');
        
        if (!infoModalContent) {
            console.error('Info modal content element not found');
            return;
        }
        
        if (agentCard) {
            // Try to load DID document
            let didDocument = null;
            let agentDid = agentCard.did;
            
            // If DID is not in agent card, try to get it from capabilities like old app.js
            if (!agentDid && agentCard.id) {
                // Check if capabilities provide DID information (like old implementation)
                const didExtension = agentCard.capabilities?.extensions?.find(ext => ext.uri?.startsWith('did:'));
                if (didExtension && didExtension.uri) {
                    agentDid = didExtension.uri;
                    console.log('DID Extension found:', didExtension);
                    console.log('Resolving DID:', agentDid);
                } else {
                    // Don't construct hardcoded DID - rely on extensions or skip
                    console.log('DID not available in agent card capabilities, skipping DID resolution');
                }
            }
            
            try {
                if (agentDid) {
                    // Use proper DID resolution like old app.js
                    const didResponse = await fetch(`${this.getAgentBaseUrl()}/did/resolve`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ did: agentDid })
                    });
                    
                    if (didResponse.ok) {
                        didDocument = await didResponse.json();
                        console.log('DID Document loaded:', didDocument);
                    } else {
                        const errorText = await didResponse.text();
                        console.error('DID resolution failed:', errorText);
                    }
                }
            } catch (error) {
                console.warn('Failed to resolve DID:', error);
            }
            
            infoModalContent.innerHTML = `
                <div class="agent-card-balanced">
                    <!-- Agent Header -->
                    <div class="agent-header-balanced">
                        <div class="agent-avatar-balanced">
                            <div class="avatar-circle-balanced">
                                <span class="avatar-initial-balanced">${(agentCard.name || 'Agent').charAt(0).toUpperCase()}</span>
                            </div>
                            <div class="status-dot-balanced online"></div>
                        </div>
                        <div class="agent-info-balanced">
                            <h1 class="agent-name-balanced">${agentCard.name || 'Unknown Agent'}</h1>
                            <p class="agent-description-balanced">${agentCard.description || 'Advanced AI Assistant'}</p>
                            <div class="agent-meta-balanced">
                                <span class="version-pill-balanced">v${agentCard.version || '1.0.0'}</span>
                                <span class="status-pill-balanced">Online</span>
                                <span class="protocol-badge">Protocol: ${agentCard.protocolVersion || '2026.1.12'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Quick Stats -->
                    <div class="stats-section-balanced">
                        <div class="stat-card-balanced">
                            <div class="stat-icon">🛠️</div>
                            <div class="stat-info">
                                <span class="stat-number-balanced">${skills ? skills.length : 0}</span>
                                <span class="stat-label-balanced">Skills</span>
                            </div>
                        </div>
                        <div class="stat-card-balanced">
                            <div class="stat-icon">⚡</div>
                            <div class="stat-info">
                                <span class="stat-number-balanced">${agentCard.capabilities ? Object.keys(agentCard.capabilities).length : 0}</span>
                                <span class="stat-label-balanced">Capabilities</span>
                            </div>
                        </div>
                        <div class="stat-card-balanced">
                            <div class="stat-icon">🔗</div>
                            <div class="stat-info">
                                <span class="stat-number-balanced">${agentDid ? 'DID' : 'None'}</span>
                                <span class="stat-label-balanced">Identity</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Skills Section -->
                    ${skills && skills.length > 0 ? `
                        <div class="skills-section-balanced">
                            <h3 class="section-title-balanced">Available Skills (${skills.length})</h3>
                            <div class="skills-grid-balanced">
                                ${skills.map(skill => `
                                    <div class="skill-card-balanced" onclick="window.binduUI.showSkillDetails('${skill.id || 'unknown'}')">
                                        <div class="skill-header-balanced">
                                            <div class="skill-icon-balanced">🛠️</div>
                                            <div class="skill-name-balanced">${skill.name || skill.id}</div>
                                        </div>
                                        <p class="skill-description-balanced">${skill.description || 'No description available'}</p>
                                        <div class="skill-action-balanced">
                                            <span>View Details →</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <!-- Capabilities Section -->
                    <div class="capabilities-section-balanced">
                        <h3 class="section-title-balanced">Core Capabilities</h3>
                        <div class="capabilities-grid-balanced">
                            ${agentCard.capabilities ? Object.keys(agentCard.capabilities).map(cap => 
                                `<div class="capability-card-balanced">
                                    <div class="capability-icon-balanced">⚡</div>
                                    <div class="capability-name-balanced">${cap}</div>
                                </div>`
                            ).join('') : '<div class="no-capabilities-balanced">No capabilities specified</div>'}
                        </div>
                    </div>
                    
                    <!-- Technical Details -->
                    <div class="technical-section-balanced">
                        <h3 class="section-title-balanced">Technical Information</h3>
                        <div class="technical-grid-balanced">
                            <div class="technical-item-balanced">
                                <div class="tech-label-balanced">Agent ID</div>
                                <div class="tech-value-balanced">
                                    <code>${agentCard.id || 'Unknown'}</code>
                                    <button class="copy-btn-balanced" onclick="navigator.clipboard.writeText('${agentCard.id || ''}')" title="Copy Agent ID">📋</button>
                                </div>
                            </div>
                            <div class="technical-item-balanced">
                                <div class="tech-label-balanced">Connection URL</div>
                                <div class="tech-value-balanced">
                                    <code>${agentCard.url || 'http://localhost'}</code>
                                    <button class="copy-btn-balanced" onclick="navigator.clipboard.writeText('${agentCard.url || ''}')" title="Copy URL">📋</button>
                                </div>
                            </div>
                            ${agentDid ? `
                                <div class="technical-item-balanced">
                                    <div class="tech-label-balanced">Decentralized ID</div>
                                    <div class="tech-value-balanced">
                                        <code>${agentDid}</code>
                                        <button class="copy-btn-balanced" onclick="navigator.clipboard.writeText('${agentDid}')" title="Copy DID">📋</button>
                                    </div>
                                </div>
                            ` : ''}
                            ${this.extractPublicKeyFromAgentCard(agentCard, didDocument) ? `
                                <div class="technical-item-balanced">
                                    <div class="tech-label-balanced">Public Key</div>
                                    <div class="tech-value-balanced">
                                        <code class="public-key-balanced">${this.extractPublicKeyFromAgentCard(agentCard, didDocument).substring(0, 20)}...</code>
                                        <button class="copy-btn-balanced" onclick="navigator.clipboard.writeText('${this.extractPublicKeyFromAgentCard(agentCard, didDocument)}')" title="Copy Public Key">📋</button>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    
                    <!-- Trust & Security -->
                    <div class="trust-section-balanced">
                        <h3 class="section-title-balanced">Trust & Security</h3>
                        <div class="trust-badges-balanced">
                            <div class="trust-badge-balanced ${agentCard.agent_trust?.verified ? 'verified' : 'unverified'}">
                                <div class="trust-icon-balanced">${agentCard.agent_trust?.verified ? '✅' : '⚠️'}</div>
                                <div class="trust-info-balanced">
                                    <div class="trust-title-balanced">${agentCard.agent_trust?.verified ? 'Verified Agent' : 'Unverified Agent'}</div>
                                    <div class="trust-desc-balanced">${agentCard.agent_trust?.verified ? 'This agent has been verified and is trusted' : 'This agent has not been verified'}</div>
                                </div>
                            </div>
                            ${agentCard.agent_trust?.level ? `
                                <div class="trust-level-balanced">
                                    <div class="trust-label-balanced">Trust Level</div>
                                    <div class="trust-value-balanced">${agentCard.agent_trust.level}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        } else {
            infoModalContent.innerHTML = '<div class="loading">Loading agent information...</div>';
        }
    }

addSmoothAnimations() {
    // Enhanced animations for better UX
    const style = document.createElement('style');
    style.textContent = `
        /* Enhanced message animations */
        .message {
            animation: messageSlideIn 0.3s ease-out;
            transition: all 0.2s ease;
        }
        
        .message:hover {
            transform: translateX(2px);
        }
        
        .message.agent:hover::before {
            content: "Click to reply";
            position: absolute;
            top: -25px;
            right: 10px;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            opacity: 0;
            animation: fadeIn 0.2s ease-out forwards;
            animation-delay: 0.5s;
            white-space: nowrap;
            border: 1px solid var(--border-secondary);
            z-index: 10;
        }
        
        @keyframes messageSlideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        /* Enhanced button interactions */
        .icon-btn {
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        
        .icon-btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(99, 102, 241, 0.1);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: width 0.3s ease, height 0.3s ease;
        }
        
        .icon-btn:hover::before {
            width: 100%;
            height: 100%;
        }
        
        .icon-btn:hover {
            transform: scale(1.05);
            background: var(--bg-secondary);
        }
        
        .icon-btn:active {
            transform: scale(0.95);
        }
        
        /* Enhanced send button */
        #send-btn {
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        
        #send-btn:not(:disabled):hover {
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        
        #send-btn:not(:disabled):active {
            transform: scale(0.95);
        }
        
        #send-btn::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: width 0.4s ease, height 0.4s ease;
        }
        
        #send-btn:not(:disabled):active::after {
            width: 200%;
            height: 200%;
        }
        
        /* Enhanced input field */
        #message-input {
            transition: all 0.2s ease;
        }
        
        #message-input:focus {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
        }
        
        /* Enhanced conversation items */
        .conversation-item {
            transition: all 0.2s ease;
            position: relative;
        }
        
        .conversation-item:hover {
            transform: translateX(4px);
            background: var(--bg-secondary);
        }
        
        .conversation-item.active {
            transform: translateX(8px);
            background: linear-gradient(90deg, var(--bg-secondary), transparent);
        }
        
        /* Enhanced modal animations */
        .modal-content {
            animation: modalSlideIn 0.3s ease-out;
            transition: all 0.2s ease;
        }
        
        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: scale(0.9) translateY(-20px);
            }
            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }
        
        .modal-close {
            transition: all 0.2s ease;
        }
        
        .modal-close:hover {
            transform: scale(1.1) rotate(90deg);
            background: var(--bg-secondary);
            border-radius: 50%;
        }
        
        /* Enhanced form controls */
        .form-control {
            transition: all 0.2s ease;
        }
        
        .form-control:focus {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
        }
        
        /* Enhanced feedback buttons */
        .feedback-btn-corner {
            transition: all 0.2s ease;
        }
        
        .feedback-btn-corner:hover {
            transform: scale(1.1) rotate(5deg);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        
        /* Enhanced typing indicator */
        .typing-indicator {
            animation: typingSlideIn 0.3s ease-out;
        }
        
        @keyframes typingSlideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        `;
        document.head.appendChild(style);
    }

    hideAllModals() {
        // Hide all modals on page load
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.add('hidden');
        });
        
        // Clear any modal content that might have been populated
        const modalBodies = document.querySelectorAll('.modal-body');
        modalBodies.forEach(body => {
            // Keep settings, feedback, and info modal content
            if (body.id !== 'settings-modal-body' && 
                body.closest('#feedback-modal') === null && 
                body.closest('#info-modal') === null) {
                body.innerHTML = '';
            }
        });
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.binduUI = new BinduUI();
});
