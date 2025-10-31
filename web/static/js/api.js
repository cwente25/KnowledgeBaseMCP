/**
 * API Client for Knowledge Base
 */

const API_BASE_URL = window.location.origin;

class APIClient {
    constructor() {
        this.baseURL = API_BASE_URL;
    }

    getToken() {
        return localStorage.getItem('jwt_token');
    }

    setToken(token) {
        localStorage.setItem('jwt_token', token);
    }

    removeToken() {
        localStorage.removeItem('jwt_token');
    }

    async request(endpoint, options = {}) {
        const token = this.getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, config);

            // Handle 401 Unauthorized
            if (response.status === 401) {
                this.removeToken();
                window.location.href = '/login.html';
                throw new Error('Session expired. Please login again.');
            }

            // Handle other errors
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Request failed' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            // Handle 204 No Content
            if (response.status === 204) {
                return null;
            }

            return await response.json();
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('Cannot connect to server. Is it running?');
            }
            throw error;
        }
    }

    // Auth endpoints
    async login(email, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    }

    async signup(email, password, full_name) {
        return this.request('/auth/signup', {
            method: 'POST',
            body: JSON.stringify({ email, password, full_name })
        });
    }

    async getCurrentUser() {
        return this.request('/auth/me');
    }

    // Notes endpoints
    async getNotes(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/notes${query ? '?' + query : ''}`);
    }

    async getNote(id) {
        return this.request(`/notes/${id}`);
    }

    async createNote(note) {
        return this.request('/notes', {
            method: 'POST',
            body: JSON.stringify(note)
        });
    }

    async updateNote(id, updates) {
        return this.request(`/notes/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
    }

    async deleteNote(id) {
        return this.request(`/notes/${id}`, {
            method: 'DELETE'
        });
    }

    // Search endpoint
    async search(query, params = {}) {
        const searchParams = new URLSearchParams({ q: query, ...params });
        return this.request(`/search?${searchParams}`);
    }

    // Categories endpoint
    async getCategories() {
        return this.request('/categories');
    }

    // Chat endpoint
    async chat(message, conversationId = null) {
        return this.request('/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId
            })
        });
    }

    async clearConversation(conversationId) {
        return this.request(`/chat/${conversationId}`, {
            method: 'DELETE'
        });
    }
}

// Export singleton instance
export const api = new APIClient();
