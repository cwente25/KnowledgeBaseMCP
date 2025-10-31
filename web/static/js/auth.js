/**
 * Authentication utilities
 */

import { api } from './api.js';

export async function login(email, password) {
    const response = await api.login(email, password);
    api.setToken(response.access_token);
    return response;
}

export async function signup(email, password, fullName) {
    const response = await api.signup(email, password, fullName);
    return response;
}

export function logout() {
    api.removeToken();
    window.location.href = '/login.html';
}

export function isAuthenticated() {
    return !!api.getToken();
}

export async function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login.html';
        return false;
    }

    try {
        await api.getCurrentUser();
        return true;
    } catch (error) {
        window.location.href = '/login.html';
        return false;
    }
}
