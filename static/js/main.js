/**
 * Main.js - Main JavaScript functionality for How3.io
 * Contains global site functionality, interactivity and utilities
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltips.length > 0) {
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
    }
    
    // Initialize clickable table rows
    initClickableRows();
    
    // Initialize comparison functionality
    initComparisonFeature();
    
    // Check for flash messages and set timeout to fade them out
    const flashMessages = document.querySelectorAll('.alert');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(alert => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    }
});

/**
 * Initialize clickable table rows
 * Makes table rows with the 'clickable-row' class navigate to their data-href URL
 */
function initClickableRows() {
    const clickableRows = document.querySelectorAll('.clickable-row');
    if (clickableRows.length > 0) {
        clickableRows.forEach(row => {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function() {
                window.location = this.dataset.href;
            });
        });
    }
}

/**
 * Initialize protocol comparison feature
 * Handles the selection and comparison of protocols
 */
function initComparisonFeature() {
    const compareButtons = document.querySelectorAll('.add-to-compare');
    const compareBar = document.querySelector('.compare-bar');
    const selectedCountBadge = document.getElementById('selected-count');
    const compareBtn = document.getElementById('compare-btn');
    const resetCompareBtn = document.getElementById('reset-compare-btn');
    const addToCompareBtn = document.getElementById('add-to-compare-btn');
    
    // Load selected protocols from localStorage
    let selectedProtocols = [];
    const storedProtocols = localStorage.getItem('compareProtocols');
    
    if (storedProtocols) {
        selectedProtocols = JSON.parse(storedProtocols);
        updateCompareUI();
    }
    
    // Handle comparison buttons on protocol list
    if (compareButtons.length > 0) {
        compareButtons.forEach(button => {
            const protocolId = button.dataset.protocolId;
            
            // Mark buttons for already selected protocols
            if (selectedProtocols.includes(protocolId)) {
                button.classList.remove('btn-outline-light');
                button.classList.add('btn-success');
                button.textContent = 'Selected';
            }
            
            button.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent row click event if inside a clickable row
                
                const protocolId = this.dataset.protocolId;
                
                if (selectedProtocols.includes(protocolId)) {
                    // Remove from selection
                    selectedProtocols = selectedProtocols.filter(id => id !== protocolId);
                    this.classList.remove('btn-success');
                    this.classList.add('btn-outline-light');
                    this.textContent = 'Compare';
                } else {
                    // Add to selection (max 4)
                    if (selectedProtocols.length < 4) {
                        selectedProtocols.push(protocolId);
                        this.classList.remove('btn-outline-light');
                        this.classList.add('btn-success');
                        this.textContent = 'Selected';
                    } else {
                        showToast('You can select a maximum of 4 protocols for comparison.', 'warning');
                    }
                }
                
                updateCompareUI();
                
                // Save to localStorage
                localStorage.setItem('compareProtocols', JSON.stringify(selectedProtocols));
            });
        });
    }
    
    // Handle compare button
    if (compareBtn) {
        compareBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (selectedProtocols.length < 2) {
                showToast('Please select at least 2 protocols to compare.', 'warning');
                return;
            }
            
            const queryString = selectedProtocols.map(id => `ids[]=${id}`).join('&');
            window.location.href = `/compare?${queryString}`;
        });
    }
    
    // Handle reset compare button
    if (resetCompareBtn) {
        resetCompareBtn.addEventListener('click', function() {
            localStorage.removeItem('compareProtocols');
            window.location.href = '/protocols';
        });
    }
    
    // Handle add to compare button on protocol detail page
    if (addToCompareBtn) {
        const protocolId = addToCompareBtn.dataset.protocolId;
        
        // Update button state based on current selection
        if (selectedProtocols.includes(protocolId)) {
            addToCompareBtn.textContent = 'Remove from Compare';
            addToCompareBtn.classList.remove('btn-primary');
            addToCompareBtn.classList.add('btn-danger');
        }
        
        addToCompareBtn.addEventListener('click', function() {
            const protocolId = this.dataset.protocolId;
            
            if (selectedProtocols.includes(protocolId)) {
                // Remove from selection
                selectedProtocols = selectedProtocols.filter(id => id !== protocolId);
                this.textContent = 'Add to Compare';
                this.classList.remove('btn-danger');
                this.classList.add('btn-primary');
            } else {
                // Add to selection (max 4)
                if (selectedProtocols.length < 4) {
                    selectedProtocols.push(protocolId);
                    this.textContent = 'Remove from Compare';
                    this.classList.remove('btn-primary');
                    this.classList.add('btn-danger');
                } else {
                    showToast('You can select a maximum of 4 protocols for comparison.', 'warning');
                }
            }
            
            // Save to localStorage
            localStorage.setItem('compareProtocols', JSON.stringify(selectedProtocols));
        });
    }
    
    /**
     * Update the comparison UI elements
     */
    function updateCompareUI() {
        if (!selectedCountBadge || !compareBar) return;
        
        selectedCountBadge.textContent = selectedProtocols.length;
        
        if (selectedProtocols.length > 0) {
            compareBar.classList.remove('d-none');
        } else {
            compareBar.classList.add('d-none');
        }
    }
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, warning, danger, info)
 */
function showToast(message, type = 'info') {
    // Check if toast container exists, create if not
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    // Create toast content
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add toast to container
    toastContainer.appendChild(toastEl);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
    toast.show();
    
    // Remove toast element after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

/**
 * Format a number for display
 * @param {number} num - Number to format
 * @param {boolean} currency - Whether to include currency symbol
 * @returns {string} - Formatted number
 */
function formatNumber(num, currency = false) {
    if (num === null || num === undefined || isNaN(num)) {
        return 'N/A';
    }
    
    const prefix = currency ? '$' : '';
    
    if (num >= 1000000000) {
        return prefix + (num / 1000000000).toFixed(1) + 'B';
    }
    if (num >= 1000000) {
        return prefix + (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return prefix + (num / 1000).toFixed(1) + 'K';
    }
    return prefix + num.toFixed(0);
}

/**
 * Format a percentage for display
 * @param {number} percent - Percentage to format
 * @param {boolean} includeSign - Whether to include % sign
 * @returns {string} - Formatted percentage
 */
function formatPercent(percent, includeSign = true) {
    if (percent === null || percent === undefined || isNaN(percent)) {
        return 'N/A';
    }
    
    const sign = includeSign ? '%' : '';
    return percent.toFixed(1) + sign;
}

/**
 * Add a loading spinner to an element
 * @param {HTMLElement} element - Element to add spinner to
 * @param {string} size - Size of spinner (sm, md, lg)
 * @param {boolean} replace - Whether to replace element content
 */
function addSpinner(element, size = 'md', replace = true) {
    const spinner = document.createElement('div');
    spinner.className = `spinner-border spinner-border-${size} text-light`;
    spinner.setAttribute('role', 'status');
    spinner.innerHTML = '<span class="visually-hidden">Loading...</span>';
    
    if (replace) {
        // Save original content
        element.dataset.originalContent = element.innerHTML;
        element.innerHTML = '';
    }
    
    element.appendChild(spinner);
    element.disabled = true;
}

/**
 * Remove loading spinner from an element
 * @param {HTMLElement} element - Element to remove spinner from
 */
function removeSpinner(element) {
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.remove();
    }
    
    // Restore original content if it was saved
    if (element.dataset.originalContent) {
        element.innerHTML = element.dataset.originalContent;
        delete element.dataset.originalContent;
    }
    
    element.disabled = false;
}
