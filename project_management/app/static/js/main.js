/* Main JavaScript for Network Project Management */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dropdowns
    initializeDropdowns();
    
    // Initialize alerts
    initializeAlerts();
    
    // Initialize tooltips if needed
    initializeTooltips();
    
    // Initialize mobile menu toggle
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const navbarMenu = document.getElementById('navbar-menu');
    const navbarRight = document.getElementById('navbar-right');
    
    if (mobileBtn && navbarMenu && navbarRight) {
        mobileBtn.addEventListener('click', function() {
            navbarMenu.classList.toggle('active');
            navbarRight.classList.toggle('active');
        });
    }
});

/**
 * Initialize dropdown functionality
 */
function initializeDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const trigger = dropdown.querySelector('.dropdown-toggle');
        if (trigger) {
            trigger.addEventListener('click', function(e) {
                e.preventDefault();
                dropdown.classList.toggle('open');
            });
        }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('open');
            }
        });
    });
}

/**
 * Initialize alert functionality
 */
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                alert.style.display = 'none';
            });
        }
    });
}

/**
 * Initialize tooltips (if needed)
 */
function initializeTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseover', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.getAttribute('data-tooltip');
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
            tooltip.style.left = (rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)) + 'px';
        });
    });
}

/**
 * Format date to readable format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

/**
 * Show loading indicator
 */
function showLoading(message = 'Loading...') {
    const loader = document.createElement('div');
    loader.className = 'loader';
    loader.innerHTML = `<p>${message}</p>`;
    document.body.appendChild(loader);
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    const loader = document.querySelector('.loader');
    if (loader) {
        loader.remove();
    }
}

/**
 * Make AJAX request with CSRF token
 */
function makeRequest(url, options = {}) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }

    return fetch(url, {
        ...options,
        headers
    });
}

/**
 * Get task statistics
 */
function getTaskStats() {
    makeRequest('/api/task-stats/')
        .then(response => response.json())
        .then(data => {
            // Update task stats if stats container exists
            const statsContainer = document.getElementById('task-stats');
            if (statsContainer) {
                statsContainer.innerHTML = `
                    <div class="stat">
                        <span class="label">Total Tasks:</span>
                        <span class="value">${data.total}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Completed:</span>
                        <span class="value">${data.completed}</span>
                    </div>
                    <div class="stat">
                        <span class="label">In Progress:</span>
                        <span class="value">${data.in_progress}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Overdue:</span>
                        <span class="value text-danger">${data.overdue}</span>
                    </div>
                `;
            }
        })
        .catch(error => console.error('Error fetching task stats:', error));
}

/**
 * Get project progress
 */
function getProjectProgress(projectId) {
    makeRequest(`/api/project-progress/${projectId}/`)
        .then(response => response.json())
        .then(data => {
            console.log('Project Progress:', data);
        })
        .catch(error => console.error('Error fetching project progress:', error));
}

/**
 * Confirm action before proceeding
 */
function confirmAction(message = 'Are you sure?') {
    return confirm(message);
}

/**
 * Show notification
 */
function showNotification(message, type = 'success') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span>${message}</span>
        <button class="alert-close">&times;</button>
    `;
    
    const container = document.querySelector('.alerts') || document.body;
    container.insertBefore(alert, container.firstChild);
    
    const closeBtn = alert.querySelector('.alert-close');
    closeBtn.addEventListener('click', function() {
        alert.remove();
    });

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

/**
 * Validate form before submission
 */
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = '#d32f2f';
            isValid = false;
        } else {
            input.style.borderColor = '';
        }
    });

    return isValid;
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

/**
 * Calculate days remaining
 */
function daysRemaining(dueDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const due = new Date(dueDate);
    due.setHours(0, 0, 0, 0);
    
    const diffTime = due - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return diffDays;
}

/**
 * Check if task is overdue
 */
function isOverdue(dueDate) {
    return daysRemaining(dueDate) < 0;
}

/**
 * Export table to CSV
 */
function exportTableToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;

    let csv = [];
    const rows = table.querySelectorAll('tr');

    rows.forEach(row => {
        let csvRow = [];
        const cols = row.querySelectorAll('td, th');

        cols.forEach(col => {
            csvRow.push(col.innerText);
        });

        csv.push(csvRow.join(','));
    });

    downloadCSV(csv.join('\n'), filename);
}

/**
 * Download CSV file
 */
function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(csvFile);
    downloadLink.download = filename;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

/**
 * Print page or element
 */
function printElement(elementId) {
    const element = document.getElementById(elementId) || document.body;
    const printWindow = window.open('', '', 'height=400,width=800');
    printWindow.document.write('<html><head><title>Print</title>');
    printWindow.document.write('<link rel="stylesheet" href="/static/css/style.css">');
    printWindow.document.write('</head><body>');
    printWindow.document.write(element.innerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
}

/* CSS for Loader */
const loaderStyle = document.createElement('style');
loaderStyle.textContent = `
    .loader {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    }

    .loader p {
        background: white;
        padding: 30px 50px;
        border-radius: 8px;
        color: #333;
        font-weight: 500;
    }

    .tooltip {
        position: fixed;
        background: #333;
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 999;
        pointer-events: none;
    }

    .tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 5px solid transparent;
        border-top-color: #333;
    }
`;
document.head.appendChild(loaderStyle);
