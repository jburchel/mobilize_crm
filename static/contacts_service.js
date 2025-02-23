class ContactsService {
    constructor(auth) {
        this.auth = auth;
        this._handleError = this._handleError.bind(this);
    }

    _handleError(error) {
        console.error('ContactsService error:', error);
        let message = 'Failed to access contacts';
        
        if (error.code === 'permission-denied') {
            message = 'Please grant access to your Google contacts';
        } else if (error.code === 'unauthenticated') {
            message = 'Please sign in to access contacts';
        } else if (error.response) {
            message = `Error: ${error.response.status} - ${error.response.statusText}`;
        }
        
        throw new Error(message);
    }

    async fetchContacts(accessToken) {
        try {
            const user = this.auth.currentUser;
            if (!user) {
                throw new Error('User must be authenticated to fetch contacts');
            }

            // Use the provided access token from Google OAuth
            const response = await fetch('/api/contacts/sync', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${await user.getIdToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    access_token: accessToken
                })
            });

            if (!response.ok) {
                const error = await response.json();
                this._handleError(new Error(error.message || 'Failed to fetch contacts'));
                return [];
            }

            const contacts = await response.json();
            return contacts;
        } catch (error) {
            this._handleError(error);
            return [];
        }
    }

    async listContacts() {
        try {
            const user = this.auth.currentUser;
            if (!user) {
                throw new Error('User must be authenticated to fetch contacts');
            }
            
            // Get the Google OAuth token from the current user
            const googleProvider = user.providerData.find(provider => provider.providerId === 'google.com');
            if (!googleProvider) {
                throw new Error('Please sign in with Google to access contacts');
            }
            
            // Get fresh ID token with OAuth access token
            const idToken = await user.getIdToken(true);
            
            // Get stored access token
            const accessToken = sessionStorage.getItem('googleAccessToken');
            if (!accessToken) {
                throw new Error('Google authentication required');
            }

            const response = await fetch('/api/contacts/list', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    access_token: accessToken
                })
            });

            if (!response.ok) {
                const error = await response.json();
                this._handleError(new Error(error.message || 'Failed to list contacts'));
                return { contacts: [], groups: [] };
            }

            const result = await response.json();
            console.log('API Response:', result); // Add logging to debug
            return result;
        } catch (error) {
            this._handleError(error);
            return { contacts: [], groups: [] };
        }
    }

    async checkImportStatus(resourceName) {
        try {
            const user = this.auth.currentUser;
            if (!user) {
                throw new Error('User must be authenticated');
            }

            const token = await user.getIdToken();
            const response = await fetch(`/api/contacts/check-import/${encodeURIComponent(resourceName)}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to check import status');
            }

            return await response.json();
        } catch (error) {
            console.warn('Error checking import status:', error);
            return { imported: false }; // Fail gracefully
        }
    }

    async importContact(contact) {
        try {
            const user = this.auth.currentUser;
            if (!user) {
                throw new Error('User must be authenticated to import contact');
            }

            const token = await user.getIdToken();
            const response = await fetch('/api/contacts/import', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(contact)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to import contact');
            }

            return await response.json();
        } catch (error) {
            return this._handleError(error);
        }
    }
}

export { ContactsService };