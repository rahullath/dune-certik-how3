/**
 * Table.js - Enhanced table functionality for How3.io
 * This file provides sorting, filtering, and other functionality for tables
 */

document.addEventListener('DOMContentLoaded', function() {
    // Format numbers in tables
    formatNumbersInTables();
    
    // Add sorting functionality to tables with 'sortable' class
    initSortableTables();
    
    // Add filter functionality to tables with 'filterable' class
    initFilterableTables();
    
    // Initialize performance comparison functionality
    initComparisonTables();
});

/**
 * Format large numbers in tables with appropriate suffixes (K, M, B)
 */
function formatNumbersInTables() {
    // Find all elements with the 'format-number' class
    const numberElements = document.querySelectorAll('.format-number');
    
    numberElements.forEach(element => {
        const value = parseFloat(element.textContent);
        if (!isNaN(value)) {
            if (value >= 1_000_000_000) {
                element.textContent = (value / 1_000_000_000).toFixed(2) + 'B';
            } else if (value >= 1_000_000) {
                element.textContent = (value / 1_000_000).toFixed(2) + 'M';
            } else if (value >= 1_000) {
                element.textContent = (value / 1_000).toFixed(2) + 'K';
            } else {
                element.textContent = value.toFixed(2);
            }
        }
    });
}

/**
 * Initialize sortable tables
 */
function initSortableTables() {
    const tables = document.querySelectorAll('table.sortable');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th');
        
        headers.forEach((header, index) => {
            // Skip headers with 'no-sort' class
            if (header.classList.contains('no-sort')) {
                return;
            }
            
            // Add sort indicator and click handler
            header.classList.add('sortable-header');
            header.innerHTML += '<span class="sort-indicator ms-1 opacity-50"><i class="fas fa-sort"></i></span>';
            
            header.addEventListener('click', function() {
                sortTable(table, index, header);
            });
        });
    });
}

/**
 * Sort a table by the specified column
 */
function sortTable(table, columnIndex, header) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAsc = !header.classList.contains('sort-asc');
    
    // Update sort direction indicators for all headers
    table.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        
        // Reset sort indicators
        const indicator = th.querySelector('.sort-indicator');
        if (indicator) {
            indicator.innerHTML = '<i class="fas fa-sort"></i>';
        }
    });
    
    // Update the clicked header
    header.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
    const indicator = header.querySelector('.sort-indicator');
    if (indicator) {
        indicator.innerHTML = isAsc ? 
            '<i class="fas fa-sort-up"></i>' : 
            '<i class="fas fa-sort-down"></i>';
    }
    
    // Determine sort type (numeric, date, or string)
    const sampleCell = rows[0]?.querySelectorAll('td')[columnIndex];
    const sampleContent = sampleCell?.textContent.trim();
    
    let sortType = 'string';
    
    if (!isNaN(parseFloat(sampleContent)) && isFinite(sampleContent)) {
        sortType = 'number';
    } else if (Date.parse(sampleContent)) {
        sortType = 'date';
    }
    
    // Sort the rows
    rows.sort((rowA, rowB) => {
        const cellA = rowA.querySelectorAll('td')[columnIndex];
        const cellB = rowB.querySelectorAll('td')[columnIndex];
        
        if (!cellA || !cellB) return 0;
        
        const valueA = cellA.textContent.trim();
        const valueB = cellB.textContent.trim();
        
        if (sortType === 'number') {
            // Handle K, M, B suffixes
            const numA = parseNumberWithSuffix(valueA);
            const numB = parseNumberWithSuffix(valueB);
            return isAsc ? numA - numB : numB - numA;
        } else if (sortType === 'date') {
            return isAsc ? 
                new Date(valueA) - new Date(valueB) : 
                new Date(valueB) - new Date(valueA);
        } else {
            return isAsc ? 
                valueA.localeCompare(valueB) : 
                valueB.localeCompare(valueA);
        }
    });
    
    // Reappend rows in the new order
    rows.forEach(row => {
        tbody.appendChild(row);
    });
    
    // Update row numbers/rankings if present
    updateRowNumbers(table);
}

/**
 * Parse numbers with K, M, B suffixes
 */
function parseNumberWithSuffix(value) {
    // Remove any currency symbols and commas
    let cleanValue = value.replace(/[$,]/g, '');
    
    // Extract numeric part and suffix
    const match = cleanValue.match(/^([\d.]+)\s*([KMB])?/i);
    if (!match) return 0;
    
    const num = parseFloat(match[1]);
    const suffix = match[2]?.toUpperCase();
    
    if (suffix === 'K') {
        return num * 1000;
    } else if (suffix === 'M') {
        return num * 1000000;
    } else if (suffix === 'B') {
        return num * 1000000000;
    } else {
        return num;
    }
}

/**
 * Update row numbers/rankings after sorting
 */
function updateRowNumbers(table) {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    // Check if first column might be a rank number
    let hasRankColumn = false;
    if (rows.length > 0) {
        const firstCell = rows[0].querySelector('td:first-child');
        if (firstCell && !isNaN(parseInt(firstCell.textContent.trim()))) {
            hasRankColumn = true;
        }
    }
    
    if (hasRankColumn) {
        rows.forEach((row, index) => {
            const rankCell = row.querySelector('td:first-child');
            if (rankCell) {
                rankCell.textContent = index + 1;
            }
        });
    }
}

/**
 * Initialize filterable tables
 */
function initFilterableTables() {
    const tables = document.querySelectorAll('table.filterable');
    
    tables.forEach(table => {
        // Check if there's already a filter input
        let filterInput = table.parentNode.querySelector('.table-filter-input');
        
        // If not, create one
        if (!filterInput) {
            const tableContainer = table.parentNode;
            filterInput = document.createElement('input');
            filterInput.type = 'text';
            filterInput.classList.add('form-control', 'form-control-sm', 'table-filter-input', 'mb-2');
            filterInput.placeholder = 'Filter table...';
            
            // Insert before the table
            tableContainer.insertBefore(filterInput, table);
        }
        
        // Add event listener
        filterInput.addEventListener('input', function() {
            filterTable(table, this.value);
        });
    });
}

/**
 * Filter table rows based on input
 */
function filterTable(table, query) {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    const searchTerm = query.toLowerCase();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

/**
 * Initialize protocol comparison functionality
 */
function initComparisonTables() {
    const tables = document.querySelectorAll('table.comparison-table');
    
    tables.forEach(table => {
        const checkboxes = table.querySelectorAll('input[type="checkbox"].compare-checkbox');
        
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                updateComparisonSelection(table);
            });
        });
        
        // Add comparison button if not present
        if (checkboxes.length > 0) {
            let compareButton = document.querySelector('.compare-selected-button');
            
            if (!compareButton) {
                compareButton = document.createElement('button');
                compareButton.classList.add('btn', 'btn-primary', 'compare-selected-button', 'mt-3');
                compareButton.textContent = 'Compare Selected (0)';
                compareButton.disabled = true;
                
                // Add the button after the table
                table.parentNode.appendChild(compareButton);
                
                // Add click handler
                compareButton.addEventListener('click', function() {
                    compareSelectedProtocols(table);
                });
            }
        }
    });
}

/**
 * Update the comparison selection count and button state
 */
function updateComparisonSelection(table) {
    const selected = table.querySelectorAll('input[type="checkbox"].compare-checkbox:checked');
    const button = document.querySelector('.compare-selected-button');
    
    if (button) {
        button.textContent = `Compare Selected (${selected.length})`;
        button.disabled = selected.length < 2;
    }
}

/**
 * Compare selected protocols - redirect to comparison page
 */
function compareSelectedProtocols(table) {
    const selected = table.querySelectorAll('input[type="checkbox"].compare-checkbox:checked');
    const protocolIds = Array.from(selected).map(checkbox => checkbox.value);
    
    if (protocolIds.length >= 2) {
        const url = `/compare?ids=${protocolIds.join(',')}`;
        window.location.href = url;
    }
}
