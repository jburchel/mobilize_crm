// Import the functions you need from the SDKs you need
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import { 
    getAuth, 
    GoogleAuthProvider, 
    browserLocalPersistence,
    inMemoryPersistence,
    setPersistence 
} from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js';

// Initialize Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyD-Ch-gB7HBoRFcO0mupDfVVEXbAJ9Yi8c",
    authDomain: "mobilize-crm.firebaseapp.com",
    projectId: "mobilize-crm",
    storageBucket: "mobilize-crm.appspot.com",
    messagingSenderId: "1069318103780",
    appId: "1:1069318103780:web:f0035b172d4cfcf6e182f1"
};

// Load OAuth configuration
async function loadOAuthConfig() {
    try {
        const response = await fetch('/api/auth/config');
        const config = await response.json();
        return config;
    } catch (error) {
        console.error('Failed to load OAuth configuration:', error);
        throw error;
    }
}

// Initialize Firebase and auth with async setup
async function initializeFirebase() {
    try {
        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);
        console.log("Firebase app initialized");
        
        // Try to set persistence
        try {
            await setPersistence(auth, browserLocalPersistence);
            console.log("Using browser persistence");
        } catch (error) {
            console.warn("Local persistence failed, falling back to in-memory:", error);
            try {
                await setPersistence(auth, inMemoryPersistence);
                console.log("Using in-memory persistence");
            } catch (fallbackError) {
                console.error("Failed to set any persistence:", fallbackError);
            }
        }
        
        // Configure GoogleAuthProvider
        const provider = new GoogleAuthProvider();
        
        // Configure provider with all required scopes
        provider.addScope('profile');
        provider.addScope('email');
        provider.addScope('https://www.googleapis.com/auth/contacts.readonly');
        provider.addScope('https://www.googleapis.com/auth/contacts.other.readonly');
        
        // Set custom parameters for Google sign-in
        provider.setCustomParameters({
            prompt: 'consent',  // Always show the Google consent screen
            access_type: 'offline'  // Request offline access to get refresh token
        });

        console.log("Google provider configured with scopes");
        
        // For debugging
        if (typeof window !== 'undefined') {
            window._firebaseAuthProvider = provider;
        }
        
        return { auth, provider };
    } catch (error) {
        console.error("Failed to initialize Firebase:", error);
        throw error;
    }
}

export { initializeFirebase };
