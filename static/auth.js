import { initializeFirebase } from './firebase_config.js';
import { signInWithPopup, signOut, GoogleAuthProvider } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js';
import { ContactsService } from './contacts_service.js';

class AuthManager {
    constructor() {
        console.log("Starting AuthManager initialization...");
        this._initializeElements();
        
        // Check if AuthManager is already initialized
        if (window.AuthManagerInstance) {
            console.log("AuthManager already initialized, reusing instance");
            return window.AuthManagerInstance;
        }
        
        this.initialize().catch(error => {
            console.error('Failed to initialize AuthManager:', error);
            this.handleError(error);
        });

        // Store instance globally
        window.AuthManagerInstance = this;
    }

    _initializeElements() {
        // Get UI elements with error handling
        const getElement = (id, optional = false) => {
            const element = document.getElementById(id);
            if (!element && !optional) {
                console.error(`Required element #${id} not found`);
            }
            return element;
        };

        this.authContainer = document.querySelector('.auth-container');
        this.signInButton = getElement('sign-in');
        this.signOutButton = getElement('sign-out');
        this.authStatus = getElement('auth-status');
        this.authError = getElement('auth-error');
        this.loadingOverlay = getElement('loading-overlay');
        this.syncStatus = getElement('sync-status', true) || this._createSyncStatus();
        this.navbar = document.querySelector('.navbar.auth-required');
        this.mobileMenuButton = document.querySelector('.mobile-menu-toggle');
        this.navList = document.querySelector('.nav-list');

        if (!this.authContainer) {
            console.error('Auth container not found');
        }

        // Set up mobile menu toggle
        if (this.mobileMenuButton && this.navList) {
            this.mobileMenuButton.addEventListener('click', () => {
                const isExpanded = this.mobileMenuButton.getAttribute('aria-expanded') === 'true';
                this.mobileMenuButton.setAttribute('aria-expanded', !isExpanded);
                this.navList.classList.toggle('active');
                this.authContainer.classList.toggle('active');
            });
        }
    }

    _createSyncStatus() {
        const status = document.createElement('div');
        status.id = 'sync-status';
        status.style.display = 'none';
        status.className = 'sync-status';
        this.authContainer?.appendChild(status);
        return status;
    }

    async initialize() {
        console.log("Initializing Firebase auth...");
        this.loadingOverlay.style.display = 'flex';
        
        try {
            const { auth, provider } = await initializeFirebase();
            this.auth = auth;
            this.provider = provider;
            
            // Set auth on window and dispatch event
            window.auth = auth;
            console.log("Auth object set on window");
            
            this.contactsService = new ContactsService(auth);
            this.setupListeners();
            console.log("Firebase auth initialization complete");
            
            // Emit event for other components
            window.dispatchEvent(new CustomEvent('firebaseAuthReady', { 
                detail: { auth },
                bubbles: true,
                composed: true 
            }));
        } catch (error) {
            console.error("Failed to initialize Firebase:", error);
            throw error; // Re-throw to be caught by the constructor
        } finally {
            this.loadingOverlay.style.display = 'none';
        }
    }

    setupListeners() {
        this.auth.onAuthStateChanged(this.handleAuthStateChange.bind(this));
        this.signInButton.addEventListener('click', this.signIn.bind(this));
        this.signOutButton.addEventListener('click', this.signOut.bind(this));
    }

    async signIn() {
        this.loadingOverlay.style.display = 'flex';
        try {
            console.log("Starting sign-in process...");
            const result = await signInWithPopup(this.auth, this.provider);
            console.log("Sign-in popup completed");
            
            // Get the OAuth access token from the credential
            const credential = GoogleAuthProvider.credentialFromResult(result);
            const token = credential?.accessToken;
            console.log("OAuth token obtained:", token ? "Yes" : "No");
            
            if (!token) {
                throw new Error('No access token received from Google authentication');
            }

            // Store access token in session storage for reuse
            sessionStorage.setItem('googleAccessToken', token);
            
            // After successful sign-in, sync contacts
            if (this.contactsService) {
                try {
                    this.syncStatus.textContent = 'Syncing contacts...';
                    this.syncStatus.style.display = 'block';
                    const contacts = await this.contactsService.fetchContacts(token);
                    console.log("Contacts synchronized:", contacts.length);
                } catch (error) {
                    console.error("Error syncing contacts:", error);
                    this.handleError(error);
                }
            }
        } catch (error) {
            console.error("Authentication error:", error);
            // Handle specific error cases
            if (error.code === 'auth/popup-closed-by-user') {
                this.handleError(new Error('Sign-in was cancelled'));
            } else if (error.code === 'auth/popup-blocked') {
                this.handleError(new Error('Sign-in popup was blocked. Please allow popups for this site.'));
            } else if (error.code === 'auth/unauthorized-domain') {
                this.handleError(new Error('This domain is not authorized for OAuth operations'));
            } else {
                this.handleError(new Error(`Authentication failed: ${error.message}`));
            }
        } finally {
            this.loadingOverlay.style.display = 'none';
        }
    }

    async signOut() {
        this.loadingOverlay.style.display = 'flex';
        
        try {
            await signOut(this.auth);
            console.log("Sign out successful");
        } catch (error) {
            console.error("Sign-out error:", error);
            this.handleError(error);
        } finally {
            this.loadingOverlay.style.display = 'none';
        }
    }

    handleAuthStateChange(user) {
        console.log("Auth state changed:", user ? "User logged in" : "User logged out");
        
        try {
            if (user) {
                // Update auth status
                this.authStatus.textContent = `Welcome, ${user.displayName}`;
                this.signInButton.style.display = 'none';
                this.signOutButton.style.display = 'block';
                
                // Show navigation menu with animation
                if (this.navbar) {
                    this.navbar.style.display = 'block';
                    // Force a reflow to trigger the transition
                    this.navbar.offsetHeight;
                }

                // Get the user's ID token
                user.getIdToken().then(token => {
                    // Store the token for API calls
                    sessionStorage.setItem('authToken', token);
                    
                    // If on landing page, redirect to dashboard
                    if (window.location.pathname === '/') {
                        window.location.href = '/dashboard';
                    }
                });
            } else {
                // Update auth status
                this.authStatus.textContent = 'Please sign in';
                this.signInButton.style.display = 'block';
                this.signOutButton.style.display = 'none';
                
                // Hide navigation menu
                if (this.navbar) {
                    this.navbar.style.display = 'none';
                }
                
                // Reset mobile menu state
                if (this.mobileMenuButton && this.navList) {
                    this.mobileMenuButton.setAttribute('aria-expanded', 'false');
                    this.navList.classList.remove('active');
                    this.authContainer.classList.remove('active');
                }
                
                // Clear stored tokens
                sessionStorage.removeItem('authToken');
                sessionStorage.removeItem('googleAccessToken');

                // If not on landing page, redirect to root
                if (window.location.pathname !== '/') {
                    window.location.href = '/';
                }
            }
        } catch (error) {
            console.error("Error updating UI:", error);
            this.handleError(error);
        }
    }

    handleError(error) {
        console.error('Auth error:', error);
        let errorMessage = 'An error occurred during authentication.';
        
        if (error.code === 'auth/failed-persistence') {
            errorMessage = 'Unable to persist login state. You may need to sign in again after refreshing.';
        } else if (error.message?.includes('storage')) {
            errorMessage = 'Storage access is limited in this context. Some features may be unavailable.';
        } else if (error.message?.includes('contacts')) {
            errorMessage = error.message;
        } else if (error.message?.includes('popup')) {
            errorMessage = error.message;
        } else if (error.message?.includes('OAuth')) {
            errorMessage = 'Google authentication failed. Please try again.';
        }
        
        // Show error in UI
        if (this.authError) {
            this.authError.textContent = errorMessage;
            this.authError.style.display = 'block';
            
            // Remove error after 5 seconds
            setTimeout(() => {
                if (this.authError.textContent === errorMessage) {
                    this.authError.style.display = 'none';
                }
            }, 5000);
        }

        // Dispatch error event for other components
        window.dispatchEvent(new CustomEvent('authError', {
            detail: { error: errorMessage },
            bubbles: true
        }));
    }
}

// Initialize authentication when the DOM is fully loaded
function initAuth() {
    console.log("Preparing to initialize AuthManager...");
    try {
        new AuthManager();
        console.log("AuthManager initialized successfully");
    } catch (error) {
        console.error("Failed to create AuthManager:", error);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
} else {
    initAuth();
}
