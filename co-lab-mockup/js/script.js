document.addEventListener('DOMContentLoaded', () => {
    // --- DOM References ---
    const leftPanel = document.getElementById('left-panel');
    const rightPanel = document.getElementById('right-panel');
    const resizer = document.getElementById('drag-handle');
    const leftPanelToggleBtn = document.getElementById('left-panel-toggle');
    const logoImage = document.getElementById('logo-img'); // Logo in right header
    const rightPanelTabs = document.querySelectorAll('.right-panel-nav .nav-tab-btn');
    const rightPanelContentSections = document.querySelectorAll('.right-panel-content-area .content-section');

    // Profile Dropdown Elements
    const profileButton = document.getElementById('profile-button');
    const profileDropdown = document.getElementById('profile-dropdown');
    const dropdownThemeToggle = document.getElementById('dropdown-theme-toggle');
    const dropdownSettings = document.getElementById('dropdown-settings');
    const dropdownSignOut = document.getElementById('dropdown-sign-out');

    // Upload Button Elements
    const uploadButton = document.getElementById('upload-button');
    const uploadDropdown = document.getElementById('upload-dropdown');
    const uploadComputer = document.getElementById('upload-computer');
    const uploadMyFiles = document.getElementById('upload-my-files');

    // Conversation History Elements
    const historyToggleBtn = document.getElementById('history-toggle-btn');
    const historySidebar = document.getElementById('conversation-history-sidebar');


    // Settings Elements
    const settingsContent = document.getElementById('settings-content');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    let apiSettingFields = []; // Will populate later
    let hasUnsavedChanges = false;
    // --- Local Storage Keys ---
    const themeKey = 'coLabThemePreference';
    const leftPanelWidthKey = 'coLabLeftPanelWidth';
    const leftPanelCollapsedKey = 'coLabLeftPanelCollapsed';
    const historySidebarHiddenKey = 'coLabHistorySidebarHidden'; // New key

    // --- Helper: Get CSS Variable ---
    const getCssVariable = (variableName) => getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();

    // --- Theme Management ---
    const applyTheme = (theme) => {
        const themeToggleLink = document.getElementById('dropdown-theme-toggle');
        if (themeToggleLink) {
            if (theme === 'light') {
                document.body.classList.add('light-theme');
                themeToggleLink.innerHTML = '<i class="fas fa-moon fa-fw"></i> Toggle Dark Mode';
            } else { // Dark theme
                document.body.classList.remove('light-theme');
                themeToggleLink.innerHTML = '<i class="fas fa-sun fa-fw"></i> Toggle Light Mode';
            }
        }
        if (logoImage) {
            logoImage.src = theme === 'light' ? 'assets/Co-Lab_Logo_Light.png' : 'assets/Co-Lab_Logo_Dark.png';
        }
    };

    const toggleTheme = () => {
        const isLight = document.body.classList.contains('light-theme');
        const newTheme = isLight ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem(themeKey, newTheme);
    };

    // Apply saved theme on initial load
    const savedTheme = localStorage.getItem(themeKey) || 'dark';
    applyTheme(savedTheme);


    // --- Profile Dropdown Logic ---
    const toggleProfileDropdown = (show) => {
        if (!profileDropdown) return;
        const shouldShow = show ?? !profileDropdown.classList.contains('show');
        profileDropdown.classList.toggle('show', shouldShow);
    };

    if (profileButton) {
        profileButton.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleProfileDropdown();
        });
    }

    document.addEventListener('click', (e) => {
        if (profileDropdown && profileDropdown.classList.contains('show')) {
            if (!profileButton.contains(e.target) && !profileDropdown.contains(e.target)) {
                toggleProfileDropdown(false);
            }
        }
    });

    if (dropdownThemeToggle) {
        dropdownThemeToggle.addEventListener('click', (e) => {
            e.preventDefault();
            toggleTheme();
            toggleProfileDropdown(false);
        });
    }

    if (dropdownSettings) {
        dropdownSettings.addEventListener('click', (e) => {
            e.preventDefault();
            // console.log("Settings dropdown item clicked"); // Log click - Removed
            showRightPanelSection('settings-content');
            toggleProfileDropdown(false);
            // queryApiSettingFields(); // This is already called by showRightPanelSection logic if target is settings
        });
            // Activate the settings tab - THIS WAS LIKELY THE ISSUE FOR SETTINGS ACCESS
            // showRightPanelSection('settings-content'); // Keep commented out
            // Ensure setting fields are queried after potential dynamic loading
            // queryApiSettingFields(); // This is handled elsewhere now
    }

    if (dropdownSignOut) {
        dropdownSignOut.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Sign Out clicked");
            toggleProfileDropdown(false);
        });
    }

    // --- Upload Button Dropdown Logic ---
    const toggleUploadDropdown = (show) => {
        if (!uploadDropdown) return;
        const shouldShow = show ?? !uploadDropdown.classList.contains('show');
        uploadDropdown.classList.toggle('show', shouldShow);
    };

    if (uploadButton) {
        uploadButton.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleUploadDropdown();
        });
    }

    // Handle upload options clicks
    if (uploadComputer) {
        uploadComputer.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Upload from Computer clicked");
            // Implement file upload from computer functionality here
            toggleUploadDropdown(false);
        });
    }

    if (uploadMyFiles) {
        uploadMyFiles.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Upload from My Files clicked");
            // Implement file selection from My Files functionality here
            toggleUploadDropdown(false);
            // Optionally show the My Files tab
            showRightPanelSection('my-files-content');
        });
    }

    // Close upload dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (uploadDropdown && uploadDropdown.classList.contains('show')) {
            if (!uploadButton.contains(e.target) && !uploadDropdown.contains(e.target)) {
                toggleUploadDropdown(false);
            }
        }
    });

    // --- Conversation History Sidebar Toggle ---
    const toggleHistorySidebar = (hide) => {
        if (!historySidebar) return;
        const shouldHide = hide ?? !historySidebar.classList.contains('hidden');
        
        // Toggle the hidden class
        // console.log(`Toggling history sidebar. Should hide: ${shouldHide}`); // Removed log
        historySidebar.classList.toggle('hidden', shouldHide);
        
        // Update the toggle button icon/title
        if (historyToggleBtn) {
            historyToggleBtn.title = shouldHide ? "Show History" : "Hide History";
        }
        
        // Save state to localStorage
        localStorage.setItem(historySidebarHiddenKey, shouldHide ? 'true' : 'false');
    };

    if (historyToggleBtn) {
        historyToggleBtn.addEventListener('click', () => toggleHistorySidebar());
    }

    // Apply saved history state on load, defaulting to visible
    const savedHistoryHidden = localStorage.getItem(historySidebarHiddenKey) === 'true';
    if (historySidebar) {
        // Explicitly set the class based on the saved state or default (visible)
        historySidebar.classList.toggle('hidden', savedHistoryHidden);
    }


    // --- Left Panel Toggle (UPDATED to handle history) ---
    const toggleLeftPanel = (collapse) => {
        if (!leftPanel || !rightPanel || !resizer) return;

        const shouldCollapse = collapse ?? !leftPanel.classList.contains('collapsed');
        const collapsedWidth = getCssVariable('--left-panel-collapsed-width') || '50px'; // Fallback
        const resizerWidth = resizer.offsetWidth;

        // console.log(`Toggling left panel. Should collapse: ${shouldCollapse}`); // Removed log
        if (shouldCollapse) {
            // Store current width before collapsing (if not already collapsed)
            if (!leftPanel.classList.contains('collapsed')) {
                 const currentWidth = leftPanel.offsetWidth > 0 ? `${leftPanel.offsetWidth}px` : (localStorage.getItem(leftPanelWidthKey) || '50%');
                 localStorage.setItem(leftPanelWidthKey, currentWidth);
            }

            leftPanel.classList.add('collapsed');
            leftPanel.style.width = collapsedWidth;
            rightPanel.style.width = `calc(100% - ${collapsedWidth})`;
            resizer.style.display = 'none';
            localStorage.setItem(leftPanelCollapsedKey, 'true');
            // Ensure history is hidden when main panel collapses
            if (historySidebar) historySidebar.classList.add('hidden');

        } else {
            leftPanel.classList.remove('collapsed');
            const restoredWidth = localStorage.getItem(leftPanelWidthKey) || '50%';
            leftPanel.style.width = restoredWidth;
            rightPanel.style.width = `calc(100% - ${restoredWidth} - ${resizerWidth}px)`;
            resizer.style.display = 'block';
            localStorage.setItem(leftPanelCollapsedKey, 'false');
            // Restore history sidebar state (it might have been open before collapsing)
             if (historySidebar && localStorage.getItem(historySidebarHiddenKey) !== 'true') {
                 historySidebar.classList.remove('hidden');
             }
        }
    };

    if (leftPanelToggleBtn) {
        leftPanelToggleBtn.addEventListener('click', () => toggleLeftPanel());
    }

     // Apply saved collapsed state on load (UPDATED)
     const savedCollapsed = localStorage.getItem(leftPanelCollapsedKey) === 'true';
     if (savedCollapsed && leftPanel && rightPanel && resizer) {
         const collapsedWidth = getCssVariable('--left-panel-collapsed-width') || '50px';
         leftPanel.classList.add('collapsed');
         leftPanel.style.width = collapsedWidth;
         rightPanel.style.width = `calc(100% - ${collapsedWidth})`;
         resizer.style.display = 'none';
         // Ensure history is hidden if main panel starts collapsed
         if (historySidebar) historySidebar.classList.add('hidden');
     }


    // --- Right Panel Tab Switching ---
    const showRightPanelSection = (targetId) => {
        rightPanelTabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.target === targetId);
        });
        rightPanelContentSections.forEach(section => {
            section.classList.toggle('active', section.id === targetId);
        });
        if (rightPanel) {
            const contentArea = rightPanel.querySelector('.right-panel-content-area');
            if (contentArea) contentArea.scrollTop = 0;
        }
    };

    rightPanelTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetId = tab.dataset.target; // Get targetId here
            // console.log(`Tab clicked: ${targetId}`); // Removed log
            // --- Unsaved Changes Check ---
            // Updated check: Only prompt if leaving settings with unsaved changes
            if (hasUnsavedChanges && settingsContent.classList.contains('active') && targetId !== 'settings-content') {
                const proceed = confirm("You have unsaved changes in Settings. Do you want to discard them and switch tabs?");
                if (!proceed) {
                    // console.log("Tab switch cancelled due to unsaved changes."); // Removed log
                    return; // Stop the tab switch if user cancels
                }
                // If user proceeds (discards changes)
                resetUnsavedChangesState();
                // console.log("Unsaved changes discarded."); // Removed log
            }
            // --- End Unsaved Changes Check ---

            // console.log(`Showing section: ${targetId}`); // Removed log
            showRightPanelSection(targetId); // Keep only ONE call
            // If switching *to* settings, ensure fields are queried
            if (targetId === 'settings-content') {
                queryApiSettingFields();
            }
        });
    });

    if (!document.querySelector('.right-panel-content-area .content-section.active')) {
        showRightPanelSection('tasks-content');
    }


    // --- Panel Resizing ---
    let isResizing = false;
    let startX, startWidthLeft;

    if (resizer && leftPanel && rightPanel) {
        // Apply saved width on load (only if not collapsed)
        if (!savedCollapsed) {
            const savedWidth = localStorage.getItem(leftPanelWidthKey);
            if (savedWidth) {
                leftPanel.style.width = savedWidth;
                rightPanel.style.width = `calc(100% - ${savedWidth} - ${resizer.offsetWidth}px)`;
            }
        }

        resizer.addEventListener('mousedown', (e) => {
            if (leftPanel.classList.contains('collapsed')) return; // Prevent dragging when collapsed

            isResizing = true;
            startX = e.clientX;
            startWidthLeft = leftPanel.offsetWidth;

            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        const handleMouseMove = (e) => {
            if (!isResizing) return;

            const currentX = e.clientX;
            const deltaX = currentX - startX;
            let newLeftWidth = startWidthLeft + deltaX;

            const minLeftWidth = parseInt(getCssVariable('--left-panel-min-width') || '250'); // Use CSS var or fallback
            const minRightWidth = parseInt(getCssVariable('--right-panel-min-width') || '350');
            const containerWidth = leftPanel.parentElement.offsetWidth;
            const resizerWidth = resizer.offsetWidth;
            const collapsedWidthThreshold = parseInt(getCssVariable('--left-panel-collapsed-width') || '50');

            // Prevent making left panel smaller than its collapsed width during resize
            if (newLeftWidth < collapsedWidthThreshold + 20) { // Add a small buffer
                 newLeftWidth = collapsedWidthThreshold + 20;
            }
            // Clamp based on min widths
            if (newLeftWidth < minLeftWidth) {
                newLeftWidth = minLeftWidth;
            }
            if (containerWidth - newLeftWidth - resizerWidth < minRightWidth) {
                newLeftWidth = containerWidth - minRightWidth - resizerWidth;
            }

            leftPanel.style.width = `${newLeftWidth}px`;
            rightPanel.style.width = `calc(100% - ${newLeftWidth}px - ${resizerWidth}px)`;
        };

        const handleMouseUp = () => {
            if (isResizing) {
                isResizing = false;
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
                document.body.style.cursor = '';
                document.body.style.userSelect = '';

                if (!leftPanel.classList.contains('collapsed')) {
                    localStorage.setItem(leftPanelWidthKey, leftPanel.style.width);
                }
            }
        };
    }



    // --- API Settings Save Logic ---
    const queryApiSettingFields = () => {
        if (settingsContent) {
            // Query fields only when settings tab is potentially visible
            apiSettingFields = settingsContent.querySelectorAll('.api-setting-field');
            // Add listeners only if they haven't been added before or if fields changed
            // Simple approach: remove and re-add listeners
            apiSettingFields.forEach(field => {
                field.removeEventListener('input', handleSettingChange);
                field.removeEventListener('change', handleSettingChange);
                field.addEventListener('input', handleSettingChange);
                field.addEventListener('change', handleSettingChange); // For select elements
            });
        }
    };

    const handleSettingChange = () => {
        if (!hasUnsavedChanges) {
            hasUnsavedChanges = true;
            if (saveSettingsBtn) {
                saveSettingsBtn.classList.add('unsaved-changes');
                // Optional: Update button text or add an indicator
                // saveSettingsBtn.textContent = "Save API Settings*"; 
            }
        }
    };

    const resetUnsavedChangesState = () => {
        hasUnsavedChanges = false;
        if (saveSettingsBtn) {
            saveSettingsBtn.classList.remove('unsaved-changes');
            // Optional: Reset button text if changed
            // saveSettingsBtn.textContent = "Save API Settings"; 
        }
    };

    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            console.log("Saving API Settings..."); // Placeholder for actual save logic
            // Simulate save
            resetUnsavedChangesState();
            alert("API Settings Saved (mock)!"); // User feedback
        });
    }

    // Initial query in case settings tab is active on load
    if (document.querySelector('#settings-content.active')) {
        queryApiSettingFields();
    }

    // Add listener to the settings dropdown item to ensure fields are queried when tab is shown - REDUNDANT LISTENER REMOVED
    // if (dropdownSettings) {
    //     dropdownSettings.addEventListener('click', queryApiSettingFields); // Keep commented out
    // }
});