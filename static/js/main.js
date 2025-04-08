/**
 * Main.js - Main JavaScript functionality for How3.io
 * Contains global site functionality, interactivity and utilities
 */

// Initialize all interactive elements when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initClickableRows();
    initTooltips();
});

/**
 * Initialize clickable table rows
 * Makes table rows with the 'clickable-row' class navigate to their data-href URL
 */
function initClickableRows() {
    const clickableRows = document.querySelectorAll('.clickable-row');
    clickableRows.forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function() {
            window.location.href = this.dataset.href;
        });
    });
}

/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, warning, danger, info)
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <span class="rounded me-2 bg-${type}" style="width: 20px; height: 20px;"></span>
                <strong class="me-auto">How3.io</strong>
                <small>Just now</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Format a number for display
 * @param {number} num - Number to format
 * @param {boolean} currency - Whether to include currency symbol
 * @returns {string} - Formatted number
 */
function formatNumber(num, currency = false) {
    if (typeof num !== 'number') return 'N/A';
    
    const formatter = new Intl.NumberFormat('en-US', {
        style: currency ? 'currency' : 'decimal',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
    
    return formatter.format(num);
}

/**
 * Format a percentage for display
 * @param {number} percent - Percentage to format
 * @param {boolean} includeSign - Whether to include % sign
 * @returns {string} - Formatted percentage
 */
function formatPercent(percent, includeSign = true) {
    if (typeof percent !== 'number') return 'N/A';
    
    const formatter = new Intl.NumberFormat('en-US', {
        style: includeSign ? 'percent' : 'decimal',
        minimumFractionDigits: 1,
        maximumFractionDigits: 2
    });
    
    return formatter.format(includeSign ? percent / 100 : percent);
}

/**
 * Add a loading spinner to an element
 * @param {HTMLElement} element - Element to add spinner to
 * @param {string} size - Size of spinner (sm, md, lg)
 * @param {boolean} replace - Whether to replace element content
 */
function addSpinner(element, size = 'md', replace = true) {
    const spinner = document.createElement('div');
    spinner.className = `spinner-border text-primary spinner-border-${size}`;
    spinner.setAttribute('role', 'status');
    spinner.innerHTML = '<span class="visually-hidden">Loading...</span>';
    
    if (replace) {
        element.innerHTML = '';
    }
    element.appendChild(spinner);
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
}