/**
 * API Test functionality for LBDesign
 */

document.addEventListener('DOMContentLoaded', function() {
    const testButton = document.getElementById('testButton');
    const responseBox = document.getElementById('response');
    
    if (testButton) {
        testButton.addEventListener('click', async function() {
            // Disable button during request
            testButton.disabled = true;
            testButton.textContent = 'Loading...';
            
            try {
                // Call the API endpoint
                const response = await fetch('/api/v1/hello');
                const data = await response.json();
                
                // Display response
                responseBox.classList.add('show', 'success');
                responseBox.classList.remove('error');
                responseBox.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                
            } catch (error) {
                // Display error
                responseBox.classList.add('show', 'error');
                responseBox.classList.remove('success');
                responseBox.innerHTML = `<pre>Error: ${error.message}</pre>`;
                
            } finally {
                // Re-enable button
                testButton.disabled = false;
                testButton.textContent = 'Test Hello World API';
            }
        });
    }
});
