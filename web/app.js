const API_BASE = window.location.origin;

// State
let categories = [];
let notes = [];
let currentCategory = null;
let currentNote = null;
let isDirty = false;
let authToken = localStorage.getItem('auth_token');
let currentView = 'categories'; // 'categories', 'notes', 'chat'
let isOnline = navigator.onLine;

// Chat state
let chatMessages = [];
let conversationId = null;
let isChatLoading = false;
let mentionedNoteIds = new Set(); // Track notes mentioned in chat
let currentSaveMessageContent = ''; // Content to save from chat message

// Utility Functions
function debounce(func, wait) {
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Auth is disabled - skip login and initialize directly
    // Set a dummy token to satisfy API calls
    if (!authToken) {
        authToken = 'disabled';
        localStorage.setItem('auth_token', authToken);
    }
    initializeApp();
    setupEventListeners();
    setupOfflineDetection();
    setupPullToRefresh();
});

// Event Listeners
function setupEventListeners() {
    // Login/Signup
    document.getElementById('btnShowSignup')?.addEventListener('click', showSignupForm);
    document.getElementById('btnShowLogin')?.addEventListener('click', showLoginForm);
    document.getElementById('btnLogin')?.addEventListener('click', login);
    document.getElementById('btnSignup')?.addEventListener('click', signup);
    document.getElementById('btnLogout')?.addEventListener('click', logout);

    // Notes
    document.getElementById('btnNewNote')?.addEventListener('click', showNewNoteModal);
    document.getElementById('btnCancelNew')?.addEventListener('click', hideNewNoteModal);
    document.getElementById('btnCreateNote')?.addEventListener('click', createNote);
    document.getElementById('btnSave')?.addEventListener('click', saveNote);
    document.getElementById('btnDelete')?.addEventListener('click', deleteNote);

    // Debounced search (300ms delay)
    const debouncedSearch = debounce(handleSearch, 300);
    document.getElementById('searchBox')?.addEventListener('input', debouncedSearch);

    // Save message as note
    document.getElementById('btnCancelSaveMessage')?.addEventListener('click', hideSaveMessageModal);
    document.getElementById('btnSaveMessageAsNote')?.addEventListener('click', saveMessageAsNote);

    // Ask Claude about note
    document.getElementById('btnAskClaude')?.addEventListener('click', askClaudeAboutNote);
    document.getElementById('btnAskClaudeMobile')?.addEventListener('click', askClaudeAboutNote);


    // Close modals on background click
    document.getElementById('authModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'authModal') {
            // Don't allow closing auth modal if not logged in
            if (authToken) {
                hideAuthModal();
            }
        }
    });

    document.getElementById('newNoteModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'newNoteModal') {
            hideNewNoteModal();
        }
    });

    document.getElementById('saveMessageModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'saveMessageModal') {
            hideSaveMessageModal();
        }
    });

    // Mobile navigation
    document.querySelectorAll('.bottom-nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const view = tab.dataset.view;
            showView(view);
        });
    });

    // Mobile new note button
    document.getElementById('btnNewNoteMobile')?.addEventListener('click', showNewNoteModal);

    // Mobile back buttons
    document.getElementById('btnBackToCategories')?.addEventListener('click', () => showView('categories'));
    document.getElementById('btnBackToNotes')?.addEventListener('click', () => showView('notes'));

    // Desktop sidebar toggle
    document.getElementById('toggleSidebarBtn')?.addEventListener('click', toggleSidebar);
    document.getElementById('showSidebarBtn')?.addEventListener('click', showSidebar);
    document.getElementById('sidebarOverlay')?.addEventListener('click', toggleSidebar);

    // Mobile editor buttons
    document.getElementById('btnSaveMobile')?.addEventListener('click', saveNoteMobile);
    document.getElementById('btnDeleteMobile')?.addEventListener('click', deleteNoteMobile);

    // Track changes on mobile editor
    document.getElementById('noteTitleMobile')?.addEventListener('input', () => setDirty(true));
    document.getElementById('noteContentMobile')?.addEventListener('input', () => setDirty(true));
    document.getElementById('noteTagsMobile')?.addEventListener('input', () => setDirty(true));

    // Track changes on desktop editor
    document.getElementById('noteTitle')?.addEventListener('input', () => setDirty(true));
    document.getElementById('noteContent')?.addEventListener('input', () => setDirty(true));
    document.getElementById('noteTags')?.addEventListener('input', () => setDirty(true));

    // Chat event listeners
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');

    if (chatInput && chatSendBtn) {
        // Enable/disable send button based on input
        chatInput.addEventListener('input', () => {
            chatSendBtn.disabled = !chatInput.value.trim() || isChatLoading;
            // Auto-resize textarea
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 72) + 'px';
        });

        // Send on Enter (Shift+Enter for newline)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!chatSendBtn.disabled) {
                    sendChatMessage();
                }
            }
        });

        // Send button click
        chatSendBtn.addEventListener('click', sendChatMessage);
    }
}

// Set dirty state and update indicator
function setDirty(value) {
    isDirty = value;
    const indicator = document.getElementById('unsavedIndicator');
    if (indicator) {
        indicator.classList.toggle('show', value);
    }
}

// Sidebar Toggle Functions (Desktop)
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) {
        const isCollapsed = sidebar.classList.toggle('collapsed');
        // Toggle overlay on tablets
        if (overlay && window.innerWidth <= 1024 && window.innerWidth > 768) {
            overlay.classList.toggle('show', !isCollapsed);
        }
        // Save state to localStorage
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }
}

function showSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) {
        sidebar.classList.remove('collapsed');
        // Show overlay on tablets
        if (overlay && window.innerWidth <= 1024 && window.innerWidth > 768) {
            overlay.classList.add('show');
        }
        localStorage.setItem('sidebarCollapsed', 'false');
    }
}

// Restore sidebar state on load
function restoreSidebarState() {
    const sidebar = document.getElementById('sidebar');
    const width = window.innerWidth;

    // On tablets (769-1024px), start collapsed by default unless explicitly expanded
    if (width > 768 && width <= 1024) {
        const wasExpanded = localStorage.getItem('sidebarCollapsed') === 'false';
        if (!wasExpanded) {
            sidebar?.classList.add('collapsed');
        }
    }
    // On desktop (>1024px), respect saved state
    else if (width > 1024) {
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed && sidebar) {
            sidebar.classList.add('collapsed');
        }
    }
}

// Mobile View Switching
function showView(viewName) {
    currentView = viewName;

    // Update bottom nav tabs (editor doesn't have a tab, highlight notes)
    document.querySelectorAll('.bottom-nav-tab').forEach(tab => {
        const tabView = tab.dataset.view;
        tab.classList.toggle('active', tabView === viewName || (viewName === 'editor' && tabView === 'notes'));
    });

    // Update mobile views
    document.getElementById('mobileCategoriesView')?.classList.toggle('active', viewName === 'categories');
    document.getElementById('mobileNotesView')?.classList.toggle('active', viewName === 'notes');
    document.getElementById('mobileEditorView')?.classList.toggle('active', viewName === 'editor');
    document.getElementById('mobileChatView')?.classList.toggle('active', viewName === 'chat');

}

// Authentication
function showLoginModal() {
    showLoginForm();
    showModalAndPreventScroll('authModal');
}

function hideAuthModal() {
    hideModalAndRestoreScroll('authModal');
}

function showLoginForm() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('signupForm').style.display = 'none';
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPassword').value = '';
}

function showSignupForm() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('signupForm').style.display = 'block';
    document.getElementById('signupEmail').value = '';
    document.getElementById('signupPassword').value = '';
    document.getElementById('signupName').value = '';
}

async function login() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!email || !password) {
        showError('Email and password are required');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('auth_token', authToken);

        hideAuthModal();
        initializeApp();
    } catch (error) {
        showError(error.message);
    }
}

async function signup() {
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value;
    const fullName = document.getElementById('signupName').value.trim();

    if (!email || !password) {
        showError('Email and password are required');
        return;
    }

    if (password.length < 8) {
        showError('Password must be at least 8 characters');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email,
                password,
                full_name: fullName || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Signup failed');
        }

        showSuccess('Account created! Please login.');
        showLoginForm();
    } catch (error) {
        showError(error.message);
    }
}

function logout() {
    if (isDirty && !confirm('You have unsaved changes. Continue?')) {
        return;
    }

    authToken = null;
    localStorage.removeItem('auth_token');
    showLoginModal();

    // Clear app state
    categories = [];
    notes = [];
    currentCategory = null;
    currentNote = null;
    isDirty = false;
}

function initializeApp() {
    document.getElementById('app').style.display = 'flex';
    restoreSidebarState();
    loadCategories();
}

// API Calls
async function apiCall(endpoint, options = {}) {
    if (!authToken) {
        showLoginModal();
        throw new Error('Not authenticated');
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
                ...options.headers
            }
        });

        if (response.status === 401) {
            // Token expired or invalid
            authToken = null;
            localStorage.removeItem('auth_token');
            showLoginModal();
            throw new Error('Session expired. Please login again.');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }

        // Handle 204 No Content responses
        if (response.status === 204) {
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showError(error.message);
        throw error;
    }
}

async function loadCategories() {
    showCategoriesSkeleton();
    try {
        const data = await apiCall('/categories');
        categories = data.categories || [];
        renderCategories();
        loadAllNotes();
    } catch (error) {
        console.error('Failed to load categories:', error);
        categories = [];
        renderCategories(error);
    }
}

async function loadNotes(category = null) {
    showNotesSkeleton();
    try {
        const query = category ? `?category=${encodeURIComponent(category)}` : '';
        const data = await apiCall(`/notes${query}`);
        notes = data;
        renderNotes();
    } catch (error) {
        console.error('Failed to load notes:', error);
        notes = [];
        renderNotes(error);
    }
}

async function loadAllNotes() {
    showNotesSkeleton();
    try {
        const data = await apiCall('/notes');
        notes = data;
        renderNotes();
    } catch (error) {
        console.error('Failed to load notes:', error);
        notes = [];
        renderNotes(error);
    }
}

async function loadNote(noteId) {
    const data = await apiCall(`/notes/${noteId}`);
    displayNote(data);
}

async function saveNote() {
    if (!currentNote) return;

    const title = document.getElementById('noteTitle').value.trim();
    const content = document.getElementById('noteContent').value;
    const tagsInput = document.getElementById('noteTags').value;
    const tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);

    if (!title) {
        showError('Title is required');
        return;
    }

    await apiCall(`/notes/${currentNote.id}`, {
        method: 'PUT',
        body: JSON.stringify({
            title,
            content,
            tags,
            category: currentNote.category
        })
    });

    setDirty(false);
    currentNote.title = title;
    currentNote.content = content;
    currentNote.tags = tags;

    loadNotes(currentCategory);
    showSuccess('Note saved successfully');
}

async function deleteNote() {
    if (!currentNote) return;

    if (!confirm(`Are you sure you want to delete "${currentNote.title}"?`)) {
        return;
    }

    await apiCall(`/notes/${currentNote.id}`, {
        method: 'DELETE'
    });

    currentNote = null;
    hideEditor();
    loadNotes(currentCategory);
    showSuccess('Note deleted successfully');
}

// Mobile-specific save/delete that use mobile editor fields
async function saveNoteMobile() {
    if (!currentNote) return;

    const title = document.getElementById('noteTitleMobile').value.trim();
    const content = document.getElementById('noteContentMobile').value;
    const tagsInput = document.getElementById('noteTagsMobile').value;
    const tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);

    if (!title) {
        showError('Title is required');
        return;
    }

    await apiCall(`/notes/${currentNote.id}`, {
        method: 'PUT',
        body: JSON.stringify({
            title,
            content,
            tags,
            category: currentNote.category
        })
    });

    setDirty(false);
    currentNote.title = title;
    currentNote.content = content;
    currentNote.tags = tags;

    // Sync desktop editor
    document.getElementById('noteTitle').value = title;
    document.getElementById('noteContent').value = content;
    document.getElementById('noteTags').value = tags.join(', ');

    loadNotes(currentCategory);
    showSuccess('Note saved successfully');
}

async function deleteNoteMobile() {
    if (!currentNote) return;

    if (!confirm(`Are you sure you want to delete "${currentNote.title}"?`)) {
        return;
    }

    await apiCall(`/notes/${currentNote.id}`, {
        method: 'DELETE'
    });

    currentNote = null;
    hideEditor();
    showView('notes');
    loadNotes(currentCategory);
    showSuccess('Note deleted successfully');
}

async function createNote() {
    const title = document.getElementById('newNoteTitle').value.trim();
    const category = document.getElementById('newNoteCategory').value;
    const tagsInput = document.getElementById('newNoteTags').value;
    const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];

    if (!title || !category) {
        showError('Title and category are required');
        return;
    }

    await apiCall('/notes', {
        method: 'POST',
        body: JSON.stringify({
            title,
            category,
            content: '',
            tags,
            metadata: {}
        })
    });

    hideNewNoteModal();
    currentCategory = category;
    loadNotes(category);
    showSuccess('Note created successfully');
}

async function handleSearch(e) {
    const query = e.target.value.trim();

    if (!query) {
        loadAllNotes();
        return;
    }

    const data = await apiCall(`/search?q=${encodeURIComponent(query)}`);

    // Extract notes from search results
    notes = data.map(result => result.note);
    renderNotes();
}

// Render Functions
function renderCategories(error = null) {
    const container = document.getElementById('categoriesList');
    const mobileContainer = document.getElementById('mobileCategoriesList');

    console.log('renderCategories called, categories:', categories.length, 'mobileContainer:', !!mobileContainer);

    // Show error with retry button if there was an error
    if (error) {
        const errorHtml = `
            <div class="error">
                <div style="margin-bottom: 8px;">Failed to load categories</div>
                <div style="font-size: 12px; margin-bottom: 12px;">${error.message}</div>
                <button class="retry-btn" onclick="loadCategories()">
                    🔄 Retry
                </button>
            </div>
        `;
        if (container) container.innerHTML = errorHtml;
        if (mobileContainer) mobileContainer.innerHTML = errorHtml;
        return;
    }

    if (categories.length === 0) {
        const emptyHtml = '<div class="empty-state-text">No categories found</div>';
        if (container) container.innerHTML = emptyHtml;
        if (mobileContainer) mobileContainer.innerHTML = emptyHtml;
        return;
    }

    const totalNotes = notes.length;

    const categoriesHtml = `
        <div class="category ${currentCategory === null ? 'active' : ''}" data-category="">
            <span>📂 All Notes</span>
            <span class="category-count">${totalNotes}</span>
        </div>
        ${categories.map(cat => `
            <div class="category ${currentCategory === cat.name ? 'active' : ''}" data-category="${cat.name}">
                <span>📁 ${cat.name}</span>
                <span class="category-count">${cat.count}</span>
            </div>
        `).join('')}
    `;

    container.innerHTML = categoriesHtml;
    if (mobileContainer) mobileContainer.innerHTML = categoriesHtml;

    // Add click handlers to both containers
    const addCategoryHandlers = (cont) => {
        cont.querySelectorAll('.category').forEach(el => {
            el.addEventListener('click', () => {
                const category = el.dataset.category;
                currentCategory = category || null;

                // Update both desktop and mobile active states
                document.querySelectorAll('.category').forEach(c => c.classList.remove('active'));
                document.querySelectorAll(`.category[data-category="${category}"]`).forEach(c => c.classList.add('active'));

                if (category) {
                    loadNotes(category);
                } else {
                    loadAllNotes();
                }

                const title = category ? category.split('/').pop() : 'All Notes';
                document.getElementById('notesListTitle').textContent = title;
                const mobileTitle = document.getElementById('mobileNotesListTitle');
                if (mobileTitle) mobileTitle.textContent = title;

                // Switch to notes view on mobile
                showView('notes');
            });
        });
    };

    addCategoryHandlers(container);
    if (mobileContainer) addCategoryHandlers(mobileContainer);
}

function renderNotes(error = null) {
    const container = document.getElementById('notesList');
    const mobileContainer = document.getElementById('mobileNotesList');

    // Show error with retry button if there was an error
    if (error) {
        const errorHtml = `
            <div class="error">
                <div style="margin-bottom: 8px;">Failed to load notes</div>
                <div style="font-size: 12px; margin-bottom: 12px;">${error.message}</div>
                <button class="retry-btn" onclick="loadNotes(${currentCategory ? `'${currentCategory}'` : 'null'})">
                    🔄 Retry
                </button>
            </div>
        `;
        if (container) container.innerHTML = errorHtml;
        if (mobileContainer) mobileContainer.innerHTML = errorHtml;
        return;
    }

    if (notes.length === 0) {
        const emptyHtml = `
            <div class="empty-state">
                <div class="empty-state-icon">📝</div>
                <div class="empty-state-text">No notes found</div>
            </div>
        `;
        container.innerHTML = emptyHtml;
        if (mobileContainer) mobileContainer.innerHTML = emptyHtml;
        return;
    }

    const notesHtml = notes.map(note => {
        const isActive = currentNote?.id === note.id;
        const isMentioned = mentionedNoteIds.has(note.id);
        const classes = ['note-item'];
        if (isActive) classes.push('active');
        if (isMentioned) classes.push('mentioned-in-chat');

        return `
            <div class="${classes.join(' ')}" data-note-id="${note.id}">
                <div class="note-title">${note.title}</div>
                <div class="note-tags">
                    ${note.tags.map(tag => `<span class="note-tag">${tag}</span>`).join('')}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = notesHtml;
    if (mobileContainer) mobileContainer.innerHTML = notesHtml;

    // Add click handlers to both containers
    const addNoteHandlers = (cont) => {
        cont.querySelectorAll('.note-item').forEach(el => {
            el.addEventListener('click', () => {
                if (isDirty && !confirm('You have unsaved changes. Continue?')) {
                    return;
                }

                const noteId = el.dataset.noteId;

                // Update both desktop and mobile active states
                document.querySelectorAll('.note-item').forEach(n => n.classList.remove('active'));
                document.querySelectorAll(`.note-item[data-note-id="${noteId}"]`).forEach(n => n.classList.add('active'));

                loadNote(noteId);
            });
        });
    };

    addNoteHandlers(container);
    if (mobileContainer) addNoteHandlers(mobileContainer);
}

function displayNote(note) {
    currentNote = note;
    setDirty(false);

    // Desktop editor
    document.getElementById('editorEmpty').style.display = 'none';
    document.getElementById('editorContent').style.display = 'flex';

    document.getElementById('noteTitle').value = note.title;
    document.getElementById('noteCategory').textContent = note.category;
    document.getElementById('noteTags').value = note.tags.join(', ');
    document.getElementById('noteContent').value = note.content;

    // Mobile editor
    document.getElementById('noteTitleMobile').value = note.title;
    document.getElementById('noteCategoryMobile').textContent = note.category;
    document.getElementById('noteTagsMobile').value = note.tags.join(', ');
    document.getElementById('noteContentMobile').value = note.content;

    // Switch to editor view on mobile
    if (window.innerWidth <= 768) {
        showView('editor');
    }
}

function hideEditor() {
    document.getElementById('editorEmpty').style.display = 'flex';
    document.getElementById('editorContent').style.display = 'none';
    currentNote = null;
    setDirty(false);
}

// Modal Functions
function showNewNoteModal() {
    const select = document.getElementById('newNoteCategory');

    // Populate categories
    select.innerHTML = '<option value="">Select a category...</option>' +
        categories.map(cat => `<option value="${cat.name}">${cat.name}</option>`).join('');

    // Clear form
    document.getElementById('newNoteTitle').value = '';
    document.getElementById('newNoteTags').value = '';

    showModalAndPreventScroll('newNoteModal');
}

function hideNewNoteModal() {
    hideModalAndRestoreScroll('newNoteModal');
}

// Notifications
function showError(message) {
    // Simple alert for now - could be improved with toast notifications
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Simple alert for now - could be improved with toast notifications
    console.log('Success:', message);
}

// Warn before closing with unsaved changes
window.addEventListener('beforeunload', (e) => {
    if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
    }
});

// Chat Functions
async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const message = chatInput.value.trim();

    if (!message || isChatLoading) return;

    // Add user message
    const userMessage = {
        role: 'user',
        content: message,
        timestamp: new Date()
    };
    chatMessages.push(userMessage);
    renderChatMessages();

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatSendBtn.disabled = true;

    // Set loading state
    isChatLoading = true;

    // Add placeholder for assistant message
    const assistantMessage = {
        role: 'assistant',
        content: '',
        toolActivities: [],
        timestamp: new Date()
    };
    chatMessages.push(assistantMessage);
    renderChatMessages(true); // Show typing indicator

    try {
        // Build request body
        const body = {
            message: message,
            conversation_id: conversationId
        };

        // Call chat endpoint with SSE
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Chat request failed: ${response.status} ${errorText}`);
        }

        // Read SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');

            // Keep the last partial line in the buffer
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') {
                        continue;
                    }

                    try {
                        const parsed = JSON.parse(data);

                        if (parsed.conversation_id) {
                            conversationId = parsed.conversation_id;
                        }

                        // Handle different event types
                        if (parsed.type === 'text' || parsed.content) {
                            // Append content to the last assistant message
                            assistantMessage.content += parsed.content || '';
                            renderChatMessages(true);
                        } else if (parsed.type === 'tool_use') {
                            // Add tool activity indicator
                            const toolActivity = createToolActivity(parsed);
                            if (toolActivity) {
                                assistantMessage.toolActivities.push(toolActivity);
                                renderChatMessages(true);
                            }
                        } else if (parsed.type === 'tool_result') {
                            // Update existing tool activity with result
                            const toolActivity = assistantMessage.toolActivities.find(
                                t => t.id === parsed.tool_use_id
                            );
                            if (toolActivity) {
                                toolActivity.completed = true;
                            }
                            renderChatMessages(true);
                        }

                        if (parsed.error) {
                            assistantMessage.content = 'Error: ' + parsed.error;
                            assistantMessage.isError = true;
                            renderChatMessages();
                        }
                    } catch (e) {
                        console.warn('Failed to parse SSE data:', data, e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Chat error:', error);
        // Update the assistant message with error
        assistantMessage.content = `Sorry, an error occurred: ${error.message}`;
        assistantMessage.isError = true;
        renderChatMessages();
    } finally {
        isChatLoading = false;
        chatSendBtn.disabled = !chatInput.value.trim();
    }
}

// Create a tool activity indicator based on the tool being used
function createToolActivity(toolUseEvent) {
    if (!toolUseEvent.name) return null;

    const toolName = toolUseEvent.name;
    const toolInput = toolUseEvent.input || {};
    let icon = '🔧';
    let text = `Using ${toolName}`;

    // Map tool names to appropriate icons and messages
    if (toolName === 'search_notes' || toolName.includes('search')) {
        icon = '🔍';
        const query = toolInput.query || toolInput.q || '';
        text = query ? `Searching notes for: ${query}` : 'Searching notes';
    } else if (toolName === 'get_note' || toolName === 'read_note') {
        icon = '📄';
        const noteId = toolInput.note_id || toolInput.id || '';
        text = noteId ? `Reading note: ${noteId}` : 'Reading note';
    } else if (toolName === 'create_note') {
        icon = '✏️';
        const title = toolInput.title || '';
        text = title ? `Creating note: ${title}` : 'Creating note';
    } else if (toolName === 'update_note') {
        icon = '✏️';
        const title = toolInput.title || '';
        text = title ? `Updating note: ${title}` : 'Updating note';
    } else if (toolName === 'delete_note') {
        icon = '🗑️';
        text = 'Deleting note';
    } else if (toolName === 'list_notes') {
        icon = '📋';
        text = 'Listing notes';
    }

    return {
        id: toolUseEvent.id,
        icon,
        text,
        completed: false
    };
}

function renderChatMessages(showLoading = false) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    let html = '';

    // Performance optimization: limit initial render to last 50 messages
    const messagesToRender = chatMessages.length > 50 ? chatMessages.slice(-50) : chatMessages;

    for (const msg of messagesToRender) {
        const timeStr = formatChatTime(msg.timestamp);
        const content = msg.content || '';
        const toolActivities = msg.toolActivities || [];

        if (msg.role === 'user') {
            html += `
                <div class="chat-message user">
                    <div>${escapeHtml(content)}</div>
                    <div class="chat-message-time">${timeStr}</div>
                </div>
            `;
        } else {
            // Assistant message
            const hasContent = content.trim().length > 0;
            const hasTools = toolActivities.length > 0;

            if (hasTools || hasContent || !showLoading) {
                html += `<div class="chat-message assistant" data-message-index="${chatMessages.indexOf(msg)}">`;

                // Show tool activities first
                if (hasTools) {
                    html += '<div class="tool-activities">';
                    for (const activity of toolActivities) {
                        const completedClass = activity.completed ? 'completed' : '';
                        html += `
                            <div class="tool-activity ${completedClass}">
                                <span class="tool-icon">${activity.icon}</span>
                                <span class="tool-text">${escapeHtml(activity.text)}</span>
                            </div>
                        `;
                    }
                    html += '</div>';
                }

                // Show content if available (with linkified note titles)
                if (hasContent) {
                    html += `<div class="assistant-content">${linkifyNoteTitles(content)}</div>`;
                }

                // Add action buttons
                if (hasContent) {
                    html += `
                        <div class="message-actions">
                            <button class="message-action-btn save-as-note-btn" data-message-index="${chatMessages.indexOf(msg)}">
                                💾 Save as Note
                            </button>
                        </div>
                    `;
                }

                html += `
                        <div class="chat-message-time">${timeStr}</div>
                    </div>
                `;
            }
        }
    }

    // Show typing indicator
    if (showLoading && isChatLoading) {
        html += `
            <div class="chat-typing-indicator">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
    }

    container.innerHTML = html;

    // Add event listeners for note links
    container.querySelectorAll('.note-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const noteId = link.dataset.noteId;
            handleNoteLinkClick(noteId);
        });
    });

    // Add event listeners for "Save as Note" buttons
    container.querySelectorAll('.save-as-note-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const messageIndex = parseInt(btn.dataset.messageIndex);
            const message = chatMessages[messageIndex];
            if (message && message.content) {
                showSaveMessageModal(message.content);
            }
        });
    });

    // Auto-scroll to bottom with smooth animation
    requestAnimationFrame(() => {
        container.scrollTop = container.scrollHeight;
    });
}

function formatChatTime(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Chat-to-Notes Integration Functions

// Show save message modal
function showSaveMessageModal(messageContent) {
    currentSaveMessageContent = messageContent;
    const select = document.getElementById('saveMessageCategory');

    // Populate categories
    select.innerHTML = '<option value="">Select a category...</option>' +
        categories.map(cat => `<option value="${cat.name}">${cat.name}</option>`).join('');

    // Clear form fields
    document.getElementById('saveMessageTitle').value = '';
    document.getElementById('saveMessageTags').value = '';
    document.getElementById('saveMessageContent').value = messageContent;

    showModalAndPreventScroll('saveMessageModal');
}

// Hide save message modal
function hideSaveMessageModal() {
    hideModalAndRestoreScroll('saveMessageModal');
    currentSaveMessageContent = '';
}

// Save message as note
async function saveMessageAsNote() {
    const title = document.getElementById('saveMessageTitle').value.trim();
    const category = document.getElementById('saveMessageCategory').value;
    const tagsInput = document.getElementById('saveMessageTags').value;
    const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];

    if (!title || !category) {
        showError('Title and category are required');
        return;
    }

    try {
        await apiCall('/notes', {
            method: 'POST',
            body: JSON.stringify({
                title,
                category,
                content: currentSaveMessageContent,
                tags,
                metadata: {}
            })
        });

        hideSaveMessageModal();
        loadNotes(currentCategory);
        showSuccess('Message saved as note successfully');
    } catch (error) {
        console.error('Failed to save message as note:', error);
    }
}

// Ask Claude about the current note
function askClaudeAboutNote() {
    if (!currentNote) return;

    const noteTitle = currentNote.title;
    const chatInput = document.getElementById('chatInput');

    // Pre-fill chat input
    chatInput.value = `Tell me about this note: ${noteTitle}`;
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 72) + 'px';

    // Enable send button
    document.getElementById('chatSendBtn').disabled = false;

    // Switch to chat view
    showView('chat');

    // Focus on input
    chatInput.focus();
}

// Linkify note titles in text
function linkifyNoteTitles(text) {
    if (!text || !notes || notes.length === 0) return escapeHtml(text);

    // Escape HTML first
    let result = escapeHtml(text);

    // Sort notes by title length (longest first) to avoid partial matches
    const sortedNotes = [...notes].sort((a, b) => b.title.length - a.title.length);

    // Replace note titles with clickable links
    for (const note of sortedNotes) {
        const escapedTitle = escapeHtml(note.title);
        // Use word boundary to avoid partial matches
        const regex = new RegExp(`\\b(${escapedTitle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})\\b`, 'gi');
        result = result.replace(regex, `<span class="note-link" data-note-id="${note.id}">$1</span>`);

        // Track that this note was mentioned
        mentionedNoteIds.add(note.id);
    }

    return result;
}

// Handle note link click
function handleNoteLinkClick(noteId) {
    if (isDirty && !confirm('You have unsaved changes. Continue?')) {
        return;
    }

    // Update active states
    document.querySelectorAll('.note-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll(`.note-item[data-note-id="${noteId}"]`).forEach(n => n.classList.add('active'));

    // Load the note
    loadNote(noteId);

    // Switch to editor view on mobile
    if (window.innerWidth <= 768) {
        showView('editor');
    }
}

// Offline Detection
function setupOfflineDetection() {
    const offlineIndicator = document.getElementById('offlineIndicator');

    function updateOnlineStatus() {
        isOnline = navigator.onLine;
        offlineIndicator.classList.toggle('show', !isOnline);
    }

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    // Initial check
    updateOnlineStatus();
}

// Pull-to-Refresh
function setupPullToRefresh() {
    const views = [
        { view: document.getElementById('mobileCategoriesView'), indicator: document.getElementById('pullToRefreshCategories'), refresh: () => loadCategories() },
        { view: document.getElementById('mobileNotesView'), indicator: document.getElementById('pullToRefreshNotes'), refresh: () => loadNotes(currentCategory) }
    ];

    views.forEach(({ view, indicator, refresh }) => {
        if (!view || !indicator) return;

        let startY = 0;
        let isPulling = false;
        let currentY = 0;

        view.addEventListener('touchstart', (e) => {
            if (view.scrollTop === 0) {
                startY = e.touches[0].pageY;
                isPulling = true;
            }
        }, { passive: true });

        view.addEventListener('touchmove', (e) => {
            if (!isPulling) return;

            currentY = e.touches[0].pageY;
            const diff = currentY - startY;

            if (diff > 0 && view.scrollTop === 0) {
                if (diff > 60) {
                    indicator.classList.add('releasing');
                    indicator.querySelector('.refresh-text').textContent = 'Release to refresh';
                } else {
                    indicator.classList.remove('releasing');
                    indicator.querySelector('.refresh-text').textContent = 'Pull to refresh';
                }

                if (diff <= 100) {
                    indicator.classList.add('pulling');
                    indicator.style.transform = `translateY(${diff}px)`;
                }
            }
        }, { passive: true });

        view.addEventListener('touchend', () => {
            if (!isPulling) return;

            const diff = currentY - startY;

            if (diff > 60) {
                // Trigger refresh
                indicator.querySelector('.refresh-text').textContent = 'Refreshing...';
                refresh().finally(() => {
                    setTimeout(() => {
                        indicator.classList.remove('pulling', 'releasing');
                        indicator.style.transform = '';
                        indicator.querySelector('.refresh-text').textContent = 'Pull to refresh';
                    }, 500);
                });
            } else {
                indicator.classList.remove('pulling', 'releasing');
                indicator.style.transform = '';
            }

            isPulling = false;
            startY = 0;
            currentY = 0;
        }, { passive: true });
    });
}

// Modal Scroll Prevention
function showModalAndPreventScroll(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.classList.add('modal-open');
    }
}

function hideModalAndRestoreScroll(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.classList.remove('modal-open');
    }
}

// Loading Skeletons
function showCategoriesSkeleton() {
    const container = document.getElementById('categoriesList');
    const mobileContainer = document.getElementById('mobileCategoriesList');

    const skeletonHtml = Array(5).fill('').map(() =>
        '<div class="skeleton skeleton-category"></div>'
    ).join('');

    if (container) container.innerHTML = skeletonHtml;
    if (mobileContainer) mobileContainer.innerHTML = skeletonHtml;
}

function showNotesSkeleton() {
    const container = document.getElementById('notesList');
    const mobileContainer = document.getElementById('mobileNotesList');

    const skeletonHtml = Array(8).fill('').map(() =>
        '<div class="skeleton skeleton-note"></div>'
    ).join('');

    if (container) container.innerHTML = skeletonHtml;
    if (mobileContainer) mobileContainer.innerHTML = skeletonHtml;
}

// Enhanced API call with retry capability
async function apiCallWithRetry(endpoint, options = {}, retryCount = 0) {
    const maxRetries = 3;

    try {
        return await apiCall(endpoint, options);
    } catch (error) {
        if (!isOnline) {
            throw new Error('You are offline. Please check your connection.');
        }

        if (retryCount < maxRetries && error.message.includes('fetch')) {
            // Network error, offer retry
            return new Promise((resolve, reject) => {
                const retry = () => {
                    apiCallWithRetry(endpoint, options, retryCount + 1)
                        .then(resolve)
                        .catch(reject);
                };

                // For now, just reject with retry info
                // UI will show retry button
                reject({ ...error, canRetry: true, retryFn: retry });
            });
        }

        throw error;
    }
}
