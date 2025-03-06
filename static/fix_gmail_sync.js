/**
 * Gmail Sync Fix for Mobilize CRM
 * 
 * This script fixes the JSON parsing error in the Gmail sync functionality.
 * It patches the fetch API to intercept calls to the problematic endpoints.
 */

(function() {
    // Wait for the DOM to be fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFix);
    } else {
        initFix();
    }

    function initFix() {
        console.log('Gmail Sync Fix loaded');
        
        // Apply the patches
        patchFetch();
        
        // Add the fix button
        setTimeout(addFixButton, 2000);
        
        // Add a status message to the page
        addStatusMessage();
        
        // Check if the fixed endpoints are available
        checkFixedEndpoints();
    }
    
    // Check if the fixed endpoints are available
    async function checkFixedEndpoints() {
        console.log('Checking if fixed endpoints are available...');
        
        try {
            const response = await fetch('/api/gmail/sync-status-fixed');
            
            if (response.status === 404) {
                console.error('Fixed endpoints are not available');
                window.GMAIL_SYNC_FIX_FALLBACK = true;
                
                // Try original endpoint as fallback
                const fallbackResponse = await fetch('/api/gmail/sync-status');
                if (!fallbackResponse.ok) {
                    throw new Error(`Fallback endpoint failed: ${fallbackResponse.status}`);
                }
            } else if (!response.ok) {
                throw new Error(`Fixed endpoint error: ${response.status}`);
            } else {
                console.log('Fixed endpoints are available');
                window.GMAIL_SYNC_FIX_FALLBACK = false;
            }
        } catch (error) {
            console.error('Error checking endpoints:', error);
            window.GMAIL_SYNC_FIX_FALLBACK = true;
        }
        
        updateStatusMessage(`Using ${window.GMAIL_SYNC_FIX_FALLBACK ? 'fallback' : 'fixed'} endpoints`);
    }

    function patchFetch() {
        const originalFetch = window.fetch;
        
        window.fetch = async function(url, options) {
            if (typeof url === 'string' && 
                (url.includes('/api/gmail/force-sync-emails') || 
                 url.includes('/api/gmail/sync-status'))) {
                
                try {
                    const response = await originalFetch(url, options);
                    
                    // Check if response is JSON
                    const contentType = response.headers.get('content-type');
                    if (!contentType || !contentType.includes('application/json')) {
                        console.error('Non-JSON response received:', await response.text());
                        return new Response(JSON.stringify({
                            success: false,
                            message: 'Invalid response format',
                            count: 0
                        }), {
                            status: 200,
                            headers: { 'Content-Type': 'application/json' }
                        });
                    }
                    
                    return response;
                } catch (error) {
                    console.error('Fetch error:', error);
                    return new Response(JSON.stringify({
                        success: false,
                        message: error.message,
                        count: 0
                    }), {
                        status: 200,
                        headers: { 'Content-Type': 'application/json' }
                    });
                }
            }
            
            return originalFetch(url, options);
        };
    }

    // Add a button to manually apply the fix
    function addFixButton() {
        const fixButton = document.createElement('button');
        fixButton.textContent = 'Fix Gmail Sync';
        fixButton.style.position = 'fixed';
        fixButton.style.bottom = '10px';
        fixButton.style.right = '10px';
        fixButton.style.zIndex = '9999';
        fixButton.style.padding = '8px 12px';
        fixButton.style.backgroundColor = '#4CAF50';
        fixButton.style.color = 'white';
        fixButton.style.border = 'none';
        fixButton.style.borderRadius = '4px';
        fixButton.style.cursor = 'pointer';
        
        fixButton.addEventListener('click', function() {
            patchFetch();
            
            // Manually trigger a sync
            console.log('Manually triggering Gmail sync...');
            updateStatusMessage('Manually triggering Gmail sync...');
            
            // Get the necessary tokens
            const googleAccessToken = sessionStorage.getItem('googleAccessToken');
            const userId = sessionStorage.getItem('userId');
            const firebaseToken = sessionStorage.getItem('authToken');
            
            if (!googleAccessToken || !userId || !firebaseToken) {
                console.error('Missing required tokens for sync');
                updateStatusMessage('Missing required tokens for sync');
                alert('Missing required tokens for sync. Please log in again.');
                return;
            }
            
            // Determine which endpoint to use
            const syncEndpoint = window.GMAIL_SYNC_FIX_FALLBACK ? 
                '/api/gmail/force-sync-emails' : 
                '/api/gmail/force-sync-emails-fixed';
                
            console.log(`Using endpoint: ${syncEndpoint}`);
            updateStatusMessage(`Using endpoint: ${syncEndpoint}`);
            
            // Call the endpoint
            fetch(syncEndpoint, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${firebaseToken}`,
                    'X-Google-Token': googleAccessToken,
                    'X-User-ID': userId
                }
            })
            .then(response => {
                // Handle potential non-JSON responses
                return response.text().then(text => {
                    try {
                        return JSON.parse(text);
                    } catch (e) {
                        console.error("Error parsing JSON:", e);
                        console.log("Raw response:", text);
                        return { 
                            success: false, 
                            message: "Error parsing server response",
                            count: 0
                        };
                    }
                });
            })
            .then(data => {
                console.log('Sync result:', data);
                updateStatusMessage(`Sync result: ${JSON.stringify(data)}`);
                alert(`Gmail sync fix applied! Result: ${data.message || 'Unknown'}`);
            })
            .catch(error => {
                console.error('Error syncing emails:', error);
                updateStatusMessage(`Error syncing emails: ${error.message}`);
                alert(`Error syncing emails: ${error.message}`);
            });
        });
        
        document.body.appendChild(fixButton);
    }
    
    // Add a status message to the page
    function addStatusMessage() {
        const statusDiv = document.createElement('div');
        statusDiv.id = 'gmail-sync-fix-status';
        statusDiv.style.position = 'fixed';
        statusDiv.style.bottom = '50px';
        statusDiv.style.right = '10px';
        statusDiv.style.zIndex = '9999';
        statusDiv.style.padding = '8px 12px';
        statusDiv.style.backgroundColor = '#f8f9fa';
        statusDiv.style.color = '#333';
        statusDiv.style.border = '1px solid #ddd';
        statusDiv.style.borderRadius = '4px';
        statusDiv.style.maxWidth = '300px';
        statusDiv.style.fontSize = '12px';
        statusDiv.style.display = 'none';
        
        statusDiv.textContent = 'Gmail Sync Fix Status';
        
        document.body.appendChild(statusDiv);
    }
    
    // Update the status message
    function updateStatusMessage(message) {
        const statusDiv = document.getElementById('gmail-sync-fix-status');
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.style.display = 'block';
            
            // Hide after 5 seconds
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }
    }
})(); 
