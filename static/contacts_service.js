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

    async listContacts() {
        try {
            const user = this.auth.currentUser;
            if (!user) {
                throw new Error('User must be authenticated to fetch contacts');
            }

            // Get access token directly from session storage
            const accessToken = sessionStorage.getItem('googleAccessToken');
            if (!accessToken) {
                throw new Error('Google access token not found. Please sign in again.');
            }

            // Get Firebase ID token for backend authentication
            const idToken = await user.getIdToken();

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

    async importContact(contact, type) {
        try {
            const user = this.auth.currentUser;
            if (!user) {
                throw new Error('User must be authenticated');
            }

            const token = await user.getIdToken();
            const response = await fetch('/api/contacts/import', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...contact,
                    import_type: type
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to import contact');
            }

            return await response.json();
        } catch (error) {
            this._handleError(error);
        }
    }
}

export { ContactsService };