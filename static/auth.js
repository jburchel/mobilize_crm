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
        this.signInButton = getElement('sign-in', true);
        this.landingSignInButton = getElement('landing-sign-in', true);
        this.signOutButton = getElement('sign-out', true);
        this.authStatus = getElement('auth-status', true);
        this.authError = getElement('auth-error');
        this.landingAuthError = getElement('landing-auth-error', true);
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

        // Add sidebar toggle functionality
        const sidebar = document.getElementById('sidebar');
        const mobileMenuButton = document.querySelector('.mobile-menu-toggle');

        if (mobileMenuButton && sidebar) {
            mobileMenuButton.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
                const isCollapsed = sidebar.classList.contains('collapsed');
                mobileMenuButton.setAttribute('aria-expanded', !isCollapsed);
                
                // For mobile devices
                if (window.innerWidth <= 768) {
                    sidebar.classList.toggle('active');
                }
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
        this.signInButton?.addEventListener('click', this.signIn.bind(this));
        this.landingSignInButton?.addEventListener('click', this.signIn.bind(this));
        this.signOutButton?.addEventListener('click', this.signOut.bind(this));
    }

    async signIn() {
        this.loadingOverlay.style.display = 'flex';
        try {
            console.log("Starting sign-in process...");
            // Force refresh token to ensure we get a fresh one with the right scopes
            await this.auth.signOut();
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
            console.log("Access token stored in session storage");

            // Get the ID token and store it
            const idToken = await result.user.getIdToken();
            document.cookie = `firebase_token=${idToken}; path=/; SameSite=Strict`;

            // Redirect to dashboard after successful login
            if (window.location.pathname === '/' || window.location.pathname === '/landing') {
                console.log("Redirecting to dashboard...");
                window.location.href = '/dashboard';
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
            // Clear all stored tokens
            sessionStorage.removeItem('googleAccessToken');
            sessionStorage.removeItem('authToken');
            document.cookie = 'firebase_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
            
            await signOut(this.auth);
            console.log("Sign out successful");
            
            // Redirect to landing page
            window.location.href = '/';
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
                this.signInButton.classList.add('hidden');
                this.signOutButton.classList.remove('hidden');
                
                // Show navigation menu and adjust sidebar
                if (this.navbar) {
                    this.navbar.classList.remove('hidden');
                }
                
                // Ensure sidebar is visible and active
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    sidebar.classList.remove('hidden');
                    if (window.innerWidth > 768) {
                        sidebar.classList.remove('collapsed');
                    }
                }

                // Get the user's ID token and set up auth
                user.getIdToken().then(token => {
                    // Store the token for API calls
                    sessionStorage.setItem('authToken', token);
                    
                    // Store token in cookie for server-side auth
                    document.cookie = `firebase_token=${token}; path=/; SameSite=Strict`;
                    
                    // Add Authorization header to all requests
                    this._setupRequestInterceptor(token);
                });
            } else {
                // Update auth status
                this.authStatus.textContent = 'Please sign in';
                this.signInButton.classList.remove('hidden');
                this.signOutButton.classList.add('hidden');
                
                // Hide navigation menu
                if (this.navbar) {
                    this.navbar.classList.add('hidden');
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
                document.cookie = 'firebase_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
            }
        } catch (error) {
            console.error("Error updating UI:", error);
            this.handleError(error);
        }
    }

    _setupRequestInterceptor(token) {
        // Intercept all fetch requests to add the auth token
        const originalFetch = window.fetch;
        window.fetch = function() {
            let [resource, config] = arguments;
            if (!config) {
                config = {};
            }
            if (!config.headers) {
                config.headers = {};
            }
            // Add Authorization header if it's not already present
            if (!config.headers.Authorization) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return originalFetch(resource, config);
        };
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
        const showError = (element) => {
            if (element) {
                element.textContent = errorMessage;
                element.style.display = 'block';
                
                // Remove error after 5 seconds
                setTimeout(() => {
                    if (element.textContent === errorMessage) {
                        element.style.display = 'none';
                    }
                }, 5000);
            }
        };

        // Show error in both places if they exist
        showError(this.authError);
        showError(this.landingAuthError);

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
