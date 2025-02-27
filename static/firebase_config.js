// Import the functions you need from the SDKs you need
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import { 
    getAuth, 
    GoogleAuthProvider, 
    browserLocalPersistence,
    setPersistence 
} from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js';

// Initialize Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyD-Ch-gB7HBoRFcO0mupDfVVEXbAJ9Yi8c",
    authDomain: "mobilize-crm.firebaseapp.com",
    projectId: "mobilize-crm",
    storageBucket: "mobilize-crm",
    messagingSenderId: "1069318103780",
    appId: "1:1069318103780:web:f0035b172d4cfcf6e182f1"
};

// Initialize Firebase and auth with async setup
async function initializeFirebase() {
    try {
        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);
        console.log("Firebase app initialized");
        
        // Set persistence to local storage
        await setPersistence(auth, browserLocalPersistence);
        console.log("Using browser persistence");
        
        // Configure GoogleAuthProvider with required scopes
        const provider = new GoogleAuthProvider();
        
        // Add required scopes directly
        provider.addScope('profile');
        provider.addScope('email');
        provider.addScope('https://www.googleapis.com/auth/contacts.readonly');
        provider.addScope('https://www.googleapis.com/auth/contacts.other.readonly');
        
        // Add Calendar and Gmail scopes
        provider.addScope('https://www.googleapis.com/auth/calendar');
        provider.addScope('https://www.googleapis.com/auth/gmail.send');
        provider.addScope('https://www.googleapis.com/auth/gmail.readonly');
        
        // Set custom parameters for Google sign-in
        provider.setCustomParameters({
            prompt: 'consent',  // Always show the Google consent screen
            access_type: 'offline'  // Request offline access to get refresh token
        });

        console.log("Google provider configured with scopes");
        return { auth, provider };
    } catch (error) {
        console.error("Failed to initialize Firebase:", error);
        throw error;
    }
}

export { initializeFirebase };
