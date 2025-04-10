document.addEventListener('DOMContentLoaded', () => {
    const navButtons = {
        chat: document.getElementById('nav-chat'),
        upload: document.getElementById('nav-upload'),
        wallet: document.getElementById('nav-wallet'),
    };

    const views = {
        chat: document.getElementById('chat-view'),
        upload: document.getElementById('upload-view'),
        wallet: document.getElementById('wallet-view'),
    };

    // Function to switch views
    function switchView(targetViewId) {
        // Hide all views and remove active class from buttons
        Object.values(views).forEach(view => {
            if (view) view.classList.remove('active-view');
        });
        Object.values(navButtons).forEach(button => {
            if (button) button.classList.remove('active');
        });

        // Show the target view and set button active
        const targetView = views[targetViewId];
        const targetButton = navButtons[targetViewId];

        if (targetView) {
            targetView.classList.add('active-view');
        }
        if (targetButton) {
            targetButton.classList.add('active');
        }
        console.log(`Switched to ${targetViewId} view`);
    }

    // Add event listeners to navigation buttons
    if (navButtons.chat) {
        navButtons.chat.addEventListener('click', () => switchView('chat'));
    }
    if (navButtons.upload) {
        navButtons.upload.addEventListener('click', () => switchView('upload'));
    }
    if (navButtons.wallet) {
        navButtons.wallet.addEventListener('click', () => switchView('wallet'));
    }

    // --- Placeholder for Chat Interaction Logic ---
    const promptInput = document.getElementById('prompt-input');
    const submitButton = document.getElementById('submit-prompt');
    const chatHistory = document.querySelector('#chat-view .chat-history');
    const estimatedCostEl = document.getElementById('estimated-cost');

    if (submitButton && promptInput && chatHistory) {
        submitButton.addEventListener('click', () => {
            const prompt = promptInput.value.trim();
            if (prompt) {
                console.log("Sending prompt:", prompt);
                // Add user message to history
                const userMsgDiv = document.createElement('div');
                userMsgDiv.classList.add('message', 'user-message');
                userMsgDiv.innerHTML = `<p>${prompt}</p>`; // Basic escaping needed for real use
                chatHistory.appendChild(userMsgDiv);

                // Add status message
                const statusMsgDiv = document.createElement('div');
                statusMsgDiv.classList.add('message', 'status-message');
                statusMsgDiv.innerHTML = `<p><i>Processing prompt...</i></p>`;
                chatHistory.appendChild(statusMsgDiv);
                chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll down

                // Clear input
                promptInput.value = '';

                // TODO: Implement actual API call to backend (/core/prompt)
                // fetch('/core/prompt', { method: 'POST', ... })
                // .then(response => response.json())
                // .then(data => { ... handle response ... })
                // .catch(error => { ... handle error ... });

                // Simulate AI response after a delay
                setTimeout(() => {
                    // Remove status message
                    chatHistory.removeChild(statusMsgDiv);

                    // Add AI message
                    const aiMsgDiv = document.createElement('div');
                    aiMsgDiv.classList.add('message', 'ai-message');
                    aiMsgDiv.innerHTML = `<p>Simulated AI response for: "${prompt.substring(0, 30)}..."</p>`;
                    chatHistory.appendChild(aiMsgDiv);
                    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll down
                }, 1500);
            }
        });
    }

    // --- Placeholder for Upload Interaction Logic ---
    const uploadButton = document.getElementById('submit-upload');
    const fileInput = document.getElementById('file-upload');
    const descriptionInput = document.getElementById('description');
    const tagsInput = document.getElementById('tags');
    const uploadStatusDiv = document.querySelector('#upload-view .upload-status p');

    if (uploadButton && fileInput && descriptionInput && tagsInput && uploadStatusDiv) {
        uploadButton.addEventListener('click', () => {
            const file = fileInput.files[0];
            const description = descriptionInput.value.trim();
            const tags = tagsInput.value.split(',').map(tag => tag.trim()).filter(tag => tag); // Basic tag parsing

            if (!file) {
                uploadStatusDiv.textContent = 'Error: Please select a file.';
                return;
            }
            if (!description || tags.length === 0) {
                 uploadStatusDiv.textContent = 'Error: Description and at least one tag are required.';
                 return;
            }

            uploadStatusDiv.textContent = 'Uploading...';

            // TODO: Implement actual API call to backend (/upload) using FormData
            // const formData = new FormData();
            // formData.append('file', file);
            // formData.append('user_id', 'test_user_123'); // Get actual user ID
            // formData.append('description', description);
            // formData.append('tags_json', JSON.stringify(tags));
            // fetch('/upload', { method: 'POST', body: formData }) ...

            // Simulate upload response
            setTimeout(() => {
                const fakeCid = `FAKE_CID_${file.name.substring(0,5)}`;
                const fakeReward = (file.size / 1000000 * 0.01).toFixed(4); // Simulate reward
                uploadStatusDiv.textContent = `Success! File uploaded. CID: ${fakeCid}. Reward: ${fakeReward} COLAB.`;
                // Clear form?
                // fileInput.value = '';
                // descriptionInput.value = '';
                // tagsInput.value = '';
            }, 2000);
        });
    }

    // Initial setup: Ensure only the default view is shown
    switchView('chat'); // Start on chat view
});