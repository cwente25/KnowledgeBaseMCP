const API_BASE = window.location.origin;

// State
let categories = [];
let notes = [];
let currentCategory = null;
let currentNote = null;
let isDirty = false;
let authToken = localStorage.getItem('auth_token');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        initializeApp();
    } else {
        showLoginModal();
    }
    setupEventListeners();
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
    document.getElementById('searchBox')?.addEventListener('input', handleSearch);

    // Track changes
    document.getElementById('noteTitle')?.addEventListener('input', () => isDirty = true);
    document.getElementById('noteContent')?.addEventListener('input', () => isDirty = true);
    document.getElementById('noteTags')?.addEventListener('input', () => isDirty = true);

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
}

// Authentication
function showLoginModal() {
    const modal = document.getElementById('authModal');
    showLoginForm();
    modal.classList.add('show');
}

function hideAuthModal() {
    document.getElementById('authModal').classList.remove('show');
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
    const data = await apiCall('/categories');
    categories = data.categories;
    renderCategories();
    loadAllNotes();
}

async function loadNotes(category = null) {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    const data = await apiCall(`/notes${query}`);
    notes = data;
    renderNotes();
}

async function loadAllNotes() {
    const data = await apiCall('/notes');
    notes = data;
    renderNotes();
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

    isDirty = false;
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
function renderCategories() {
    const container = document.getElementById('categoriesList');

    if (categories.length === 0) {
        container.innerHTML = '<div class="empty-state-text">No categories found</div>';
        return;
    }

    const totalNotes = notes.length;

    container.innerHTML = `
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

    // Add click handlers
    container.querySelectorAll('.category').forEach(el => {
        el.addEventListener('click', () => {
            const category = el.dataset.category;
            currentCategory = category || null;

            container.querySelectorAll('.category').forEach(c => c.classList.remove('active'));
            el.classList.add('active');

            if (category) {
                loadNotes(category);
            } else {
                loadAllNotes();
            }

            document.getElementById('notesListTitle').textContent =
                category ? category.split('/').pop() : 'All Notes';
        });
    });
}

function renderNotes() {
    const container = document.getElementById('notesList');

    if (notes.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📝</div>
                <div class="empty-state-text">No notes found</div>
            </div>
        `;
        return;
    }

    container.innerHTML = notes.map(note => `
        <div class="note-item ${currentNote?.id === note.id ? 'active' : ''}"
             data-note-id="${note.id}">
            <div class="note-title">${note.title}</div>
            <div class="note-tags">
                ${note.tags.map(tag => `<span class="note-tag">${tag}</span>`).join('')}
            </div>
        </div>
    `).join('');

    // Add click handlers
    container.querySelectorAll('.note-item').forEach(el => {
        el.addEventListener('click', () => {
            if (isDirty && !confirm('You have unsaved changes. Continue?')) {
                return;
            }

            const noteId = el.dataset.noteId;

            container.querySelectorAll('.note-item').forEach(n => n.classList.remove('active'));
            el.classList.add('active');

            loadNote(noteId);
        });
    });
}

function displayNote(note) {
    currentNote = note;
    isDirty = false;

    document.getElementById('editorEmpty').style.display = 'none';
    document.getElementById('editorContent').style.display = 'flex';

    document.getElementById('noteTitle').value = note.title;
    document.getElementById('noteCategory').textContent = note.category;
    document.getElementById('noteTags').value = note.tags.join(', ');
    document.getElementById('noteContent').value = note.content;
}

function hideEditor() {
    document.getElementById('editorEmpty').style.display = 'flex';
    document.getElementById('editorContent').style.display = 'none';
    currentNote = null;
    isDirty = false;
}

// Modal Functions
function showNewNoteModal() {
    const modal = document.getElementById('newNoteModal');
    const select = document.getElementById('newNoteCategory');

    // Populate categories
    select.innerHTML = '<option value="">Select a category...</option>' +
        categories.map(cat => `<option value="${cat.name}">${cat.name}</option>`).join('');

    // Clear form
    document.getElementById('newNoteTitle').value = '';
    document.getElementById('newNoteTags').value = '';

    modal.classList.add('show');
}

function hideNewNoteModal() {
    document.getElementById('newNoteModal').classList.remove('show');
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
