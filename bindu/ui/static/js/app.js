import { ChatArea } from './components/chat/chat-area.js';
import { ContextSidebar } from './components/sidebar/context-sidebar.js';
import { AgentOverview } from './components/agent-info/agent-overview.js';
import { DIDIdentity } from './components/agent-info/did-identity.js';
import { SkillsPanel } from './components/agent-info/skills-panel.js';
import { JSONViewer } from './components/agent-info/json-viewer.js';
import { FeedbackModal } from './components/modals/feedback-modal.js';
import { SkillModal } from './components/modals/skill-modal.js';
import { Header } from './components/common/header.js';
import { Tabs } from './components/common/tabs.js';
import { CollapsibleSection } from './components/common/collapsible-section.js';

import { loadFullAgentInfo } from './api/agent.js';
import { createTask } from './api/tasks.js';
import { initializeAuth, setAuthToken } from './api/auth.js';
import { handlePaymentFlow } from './api/payment.js';
import { loadAndSetContexts, createContext, deleteContext, switchContext } from './api/contexts.js';
import { submitFeedback, cancelTask } from './tasks/tasks.js';

import { store } from './state/store.js';
import { on, emit } from './core/events.js';
import { UI_FLAGS, TASK_STATUS } from './core/constants.js';
import { parseTaskResponse } from './core/protocol.js';
import { ApiError } from './api/client.js';

export class BinduApp {
  constructor() {
    this.components = {};
    this.pollingTaskId = null;
    this.pollingInterval = null;
  }

  async initialize() {
    try {
      this.initializeComponents();
      this.setupEventListeners();
      this.subscribeToStore();
      
      initializeAuth();
      
      const agentInfo = await loadFullAgentInfo();
      store.setState({ agentInfo });
      this.renderAgentInfo(agentInfo);
      
      await loadAndSetContexts();
      
      console.log('Bindu App initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Bindu App:', error);
      store.setError('Failed to load agent information');
    }
  }

  initializeComponents() {
    this.components.chatArea = new ChatArea();
    this.components.contextSidebar = new ContextSidebar();
    this.components.agentOverview = new AgentOverview('agent-card-content');
    this.components.didIdentity = new DIDIdentity('did-summary-content');
    this.components.skillsPanel = new SkillsPanel('skills-summary-content');
    this.components.jsonViewer = new JSONViewer('agent-json-display', 'copy-json-btn');
    this.components.feedbackModal = new FeedbackModal('feedback-modal');
    this.components.skillModal = new SkillModal('skill-modal');
    this.components.header = new Header();
    this.components.tabs = new Tabs();
    this.components.collapsibleSection = new CollapsibleSection();
  }

  setupEventListeners() {
    document.addEventListener('chat-message-send', (e) => {
      this.handleMessageSend(e.detail.text, e.detail.replyToTaskId);
    });

    document.addEventListener('context-switch', (e) => {
      this.handleContextSwitch(e.detail.contextId);
    });

    document.addEventListener('context-new', () => {
      this.handleNewContext();
    });

    document.addEventListener('context-clear', (e) => {
      this.handleClearContext(e.detail.contextId);
    });

    document.addEventListener('feedback-submit', (e) => {
      this.handleFeedbackSubmit(e.detail.taskId, e.detail.rating, e.detail.feedback);
    });

    document.addEventListener('task-cancel-requested', (e) => {
      this.handleTaskCancel(e.detail.taskId);
    });

    document.addEventListener('auth-settings-requested', () => {
      this.handleAuthSettings();
    });

    on(UI_FLAGS.AUTH_REQUIRED, () => {
      this.handleAuthSettings();
    });

    on(UI_FLAGS.PAYMENT_REQUIRED, () => {
      this.handlePaymentRequired();
    });
  }

  subscribeToStore() {
    store.subscribe((state) => {
      if (state.contexts) {
        this.components.contextSidebar.update(state.contexts, state.contextId);
      }

      if (state.contextId) {
        this.components.chatArea.updateContextIndicator(state.contextId);
      }

      if (state.uiState.error) {
        this.components.chatArea.showError(state.uiState.error);
      }
    });
  }

  renderAgentInfo(agentInfo) {
    if (!agentInfo) return;

    this.components.header.updateAgentInfo(agentInfo.manifest);
    this.components.agentOverview.render(agentInfo.manifest);
    this.components.didIdentity.render(agentInfo.didDocument);
    this.components.skillsPanel.render(agentInfo.skills);
    this.components.jsonViewer.render(agentInfo.manifest);
  }

  async handleMessageSend(text, replyToTaskId = null) {
    const state = store.getState();
    
    this.components.chatArea.addThinkingIndicator(null);
    store.setIndicator('🤖 Agent is thinking...');

    try {
      const result = await createTask(text);
      const parsed = parseTaskResponse(result);

      if (parsed.uiFlag) {
        store.clearIndicator();
        this.components.chatArea.removeThinkingIndicator();
        
        if (parsed.uiFlag === UI_FLAGS.PAYMENT_REQUIRED) {
          await this.handlePaymentRequired();
          return await this.handleMessageSend(text, replyToTaskId);
        }
        
        emit(parsed.uiFlag);
        return;
      }

      if (parsed.error) {
        store.setError(parsed.error);
        this.components.chatArea.removeThinkingIndicator();
        return;
      }

      const task = parsed.task;
      
      if (!state.contextId && task.context_id) {
        store.setState({ contextId: task.context_id });
        await loadAndSetContexts();
      }

      const displayMessage = replyToTaskId
        ? `↩️ Replying to task ${replyToTaskId.substring(0, 8)}...\n\n${text}`
        : text;
      
      this.components.chatArea.addMessage(displayMessage, 'user', task.id);
      this.components.chatArea.clearReply();
      
      this.components.chatArea.removeThinkingIndicator();
      this.components.chatArea.addThinkingIndicator(task.id);
      
      store.updateTask(task);
      this.pollTaskStatus(task.id);

    } catch (error) {
      this.components.chatArea.removeThinkingIndicator();
      
      if (error instanceof ApiError) {
        if (error.status === 401) {
          emit(UI_FLAGS.AUTH_REQUIRED);
        } else if (error.status === 402) {
          emit(UI_FLAGS.PAYMENT_REQUIRED);
        } else {
          store.setError(error.message || 'Request failed');
        }
      } else {
        store.setError('Network error');
      }
    } finally {
      store.clearIndicator();
      this.components.chatArea.enableInput();
    }
  }

  async pollTaskStatus(taskId) {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }

    this.pollingTaskId = taskId;
    let attempts = 0;
    const maxAttempts = 300;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        this.components.chatArea.removeThinkingIndicator();
        this.components.chatArea.addMessage('⏱️ Timeout: Task did not complete', 'status');
        store.updateTask(null);
        return;
      }

      attempts++;

      try {
        const state = store.getState();
        const response = await fetch(`${window.location.origin}/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(state.authToken && { 'Authorization': `Bearer ${state.authToken}` }),
            ...(state.paymentToken && { 'X-PAYMENT': state.paymentToken })
          },
          body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'tasks/get',
            params: { taskId },
            id: crypto.randomUUID()
          })
        });

        if (!response.ok) throw new Error('Failed to get task status');

        const result = await response.json();
        if (result.error) throw new Error(result.error.message || 'Unknown error');

        const task = result.result;
        const taskState = task.status.state;

        if ([TASK_STATUS.COMPLETED, TASK_STATUS.FAILED, 'canceled'].includes(taskState)) {
          this.components.chatArea.removeThinkingIndicator();
          clearInterval(this.pollingInterval);
          this.pollingTaskId = null;

          store.updateTask(task);

          if (taskState === TASK_STATUS.COMPLETED) {
            const responseText = this.extractResponse(task);
            this.components.chatArea.addMessage(responseText, 'agent', taskId, taskState);
          } else if (taskState === TASK_STATUS.FAILED) {
            const error = task.metadata?.error || task.status?.error || 'Task failed';
            this.components.chatArea.addMessage(`❌ Task failed: ${error}`, 'status');
          } else {
            this.components.chatArea.addMessage('⚠️ Task was canceled', 'status');
          }

          store.setState({ paymentToken: null });
          await loadAndSetContexts();

        } else if ([TASK_STATUS.INPUT_REQUIRED, 'auth-required'].includes(taskState)) {
          this.components.chatArea.removeThinkingIndicator();
          clearInterval(this.pollingInterval);
          
          store.updateTask(task);
          
          const responseText = this.extractResponse(task);
          this.components.chatArea.addMessage(responseText, 'agent', taskId, taskState);
          
          await loadAndSetContexts();
        }

      } catch (error) {
        console.error('Error polling task status:', error);
        this.components.chatArea.removeThinkingIndicator();
        clearInterval(this.pollingInterval);
        this.pollingTaskId = null;
        store.setError('Error getting task status: ' + error.message);
      }
    };

    this.pollingInterval = setInterval(poll, 1000);
  }

  extractResponse(task) {
    const artifacts = task.artifacts || [];
    if (artifacts.length > 0) {
      const artifact = artifacts[artifacts.length - 1];
      const parts = artifact.parts || [];
      const textParts = parts
        .filter(part => part.kind === 'text')
        .map(part => part.text);
      if (textParts.length > 0) return textParts.join('\n');
    }

    const history = task.history || [];
    for (let i = history.length - 1; i >= 0; i--) {
      const msg = history[i];
      if (msg.role === 'assistant' || msg.role === 'agent') {
        const parts = msg.parts || [];
        const textParts = parts
          .filter(part => part.kind === 'text')
          .map(part => part.text);
        if (textParts.length > 0) return textParts.join('\n');
      }
    }

    return '✅ Task completed but no response found';
  }

  async handleContextSwitch(contextId) {
    const state = store.getState();
    if (contextId === state.contextId) return;

    try {
      this.components.chatArea.clearMessages();
      await switchContext(contextId);
      
      const response = await fetch(`${window.location.origin}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(state.authToken && { 'Authorization': `Bearer ${state.authToken}` }),
          ...(state.paymentToken && { 'X-PAYMENT': state.paymentToken })
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'tasks/list',
          params: { limit: 100, offset: 0 },
          id: crypto.randomUUID()
        })
      });

      if (!response.ok) throw new Error('Failed to load tasks');

      const result = await response.json();
      if (result.error) throw new Error(result.error.message);

      const allTasks = result.result || [];
      const contextTasks = allTasks
        .filter(task => task.context_id === contextId)
        .sort((a, b) => new Date(a.status.timestamp) - new Date(b.status.timestamp));

      for (const task of contextTasks) {
        const history = task.history || [];
        for (const msg of history) {
          const parts = msg.parts || [];
          const textParts = parts
            .filter(part => part.kind === 'text')
            .map(part => part.text);

          if (textParts.length > 0) {
            const text = textParts.join('\n');
            const sender = msg.role === 'user' ? 'user' : 'agent';
            const taskState = sender === 'agent' ? task.status.state : null;
            this.components.chatArea.addMessage(text, sender, task.id, taskState);
          }
        }
      }

      if (contextTasks.length > 0) {
        const lastTask = contextTasks[contextTasks.length - 1];
        store.updateTask(lastTask);
      }

    } catch (error) {
      console.error('Error switching context:', error);
      store.setError('Failed to load context: ' + error.message);
    }
  }

  handleNewContext() {
    store.setState({
      contextId: null,
      currentTaskId: null,
      currentTaskState: null
    });
    this.components.chatArea.clearMessages();
    this.components.chatArea.clearReply();
    this.components.chatArea.updateContextIndicator(null);
  }

  async handleClearContext(contextId) {
    try {
      await deleteContext(contextId);
      
      const state = store.getState();
      if (state.contextId === contextId) {
        this.handleNewContext();
      }
      
      await loadAndSetContexts();
      this.components.chatArea.addMessage('Context cleared successfully', 'status');
    } catch (error) {
      console.error('Error clearing context:', error);
      store.setError('Failed to clear context: ' + error.message);
    }
  }

  async handleFeedbackSubmit(taskId, rating, feedback) {
    try {
      await submitFeedback(taskId, rating, feedback);
      this.components.chatArea.addMessage('✅ Feedback submitted', 'status');
    } catch (error) {
      console.error('Error submitting feedback:', error);
      store.setError('Failed to submit feedback');
    }
  }

  async handleTaskCancel(taskId) {
    try {
      await cancelTask(taskId);
      this.components.chatArea.removeThinkingIndicator();
      this.components.chatArea.addMessage('⚠️ Task canceled successfully', 'status');
      
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval);
        this.pollingInterval = null;
      }
      
      await loadAndSetContexts();
    } catch (error) {
      console.error('Error canceling task:', error);
      store.setError('Failed to cancel task: ' + error.message);
    }
  }

  handleAuthSettings() {
    const token = prompt('Enter JWT token (leave empty to clear):');
    if (token !== null) {
      try {
        setAuthToken(token || null);
        if (token) {
          this.components.chatArea.addMessage('✅ Token saved', 'status');
        } else {
          this.components.chatArea.addMessage('Token cleared', 'status');
        }
        store.setError(null);
      } catch (error) {
        store.setError(error.message);
      }
    }
  }

  async handlePaymentRequired() {
    try {
      store.setIndicator('💰 Processing payment...');
      const paymentResult = await handlePaymentFlow();
      
      if (paymentResult.success) {
        this.components.chatArea.addMessage('💰 Payment approved!', 'status');
        return true;
      }
    } catch (error) {
      store.setError(`Payment failed: ${error.message}`);
      this.components.chatArea.addMessage(`❌ Payment failed: ${error.message}`, 'status');
      return false;
    } finally {
      store.clearIndicator();
    }
  }
}

export function initializeBinduApp() {
  const app = new BinduApp();
  app.initialize();
  
  window.BinduApp = app;
  window.Bindu = {
    app,
    store
  };
  
  return app;
}
