/* Dashboard-specific JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Load task statistics
    loadTaskStats();
    
    // Refresh stats every 30 seconds
    setInterval(loadTaskStats, 30000);
    
    // Initialize chart if available
    initializeCharts();
});

/**
 * Load task statistics
 */
function loadTaskStats() {
    makeRequest('/api/task-stats/')
        .then(response => response.json())
        .then(data => {
            updateTaskStatsUI(data);
        })
        .catch(error => console.error('Error loading task stats:', error));
}

/**
 * Update task stats in UI
 */
function updateTaskStatsUI(data) {
    // Update stat cards if they exist
    const totalTasksElem = document.querySelector('[data-stat="total-tasks"]');
    if (totalTasksElem) totalTasksElem.textContent = data.total;

    const completedElem = document.querySelector('[data-stat="completed-tasks"]');
    if (completedElem) completedElem.textContent = data.completed;

    const inProgressElem = document.querySelector('[data-stat="in-progress"]');
    if (inProgressElem) inProgressElem.textContent = data.in_progress;

    const overdueElem = document.querySelector('[data-stat="overdue"]');
    if (overdueElem) overdueElem.textContent = data.overdue;
}

/**
 * Initialize charts (if Chart.js is available)
 */
function initializeCharts() {
    const chartElements = document.querySelectorAll('[data-chart]');
    
    chartElements.forEach(element => {
        const chartType = element.getAttribute('data-chart');
        
        if (chartType === 'project-progress') {
            const projectId = element.getAttribute('data-project-id');
            loadProjectProgressChart(element, projectId);
        }
    });
}

/**
 * Load project progress chart
 */
function loadProjectProgressChart(element, projectId) {
    makeRequest(`/api/project-progress/${projectId}/`)
        .then(response => response.json())
        .then(data => {
            renderProgressChart(element, data);
        })
        .catch(error => console.error('Error loading project progress:', error));
}

/**
 * Render progress chart
 */
function renderProgressChart(element, data) {
    // Simple bar chart using HTML/CSS
    const chartContainer = document.createElement('div');
    chartContainer.className = 'chart-container';
    
    let html = `<div class="chart-title">${data.project_name}</div>`;
    html += `<div class="chart-main">
        <div class="chart-bar">
            <div class="bar-fill" style="width: ${data.overall_progress}%"></div>
        </div>
        <div class="chart-label">${data.overall_progress}% Complete</div>
    </div>`;
    
    if (data.milestones && data.milestones.length > 0) {
        html += '<div class="chart-milestones">';
        data.milestones.forEach(milestone => {
            html += `
                <div class="milestone-bar">
                    <div class="milestone-label">${milestone.name}</div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: ${milestone.progress}%"></div>
                    </div>
                    <div class="bar-progress">${milestone.progress}%</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    chartContainer.innerHTML = html;
    element.innerHTML = '';
    element.appendChild(chartContainer);
}

/* Chart Styles */
const chartStyles = document.createElement('style');
chartStyles.textContent = `
    .chart-container {
        padding: 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .chart-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 20px;
        color: #333;
    }

    .chart-main {
        margin-bottom: 30px;
    }

    .chart-bar {
        width: 100%;
        height: 30px;
        background: #f0f0f0;
        border-radius: 15px;
        overflow: hidden;
        margin-bottom: 10px;
    }

    .bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        transition: width 0.3s ease;
    }

    .chart-label {
        text-align: center;
        font-size: 14px;
        color: #666;
        font-weight: 500;
    }

    .chart-milestones {
        border-top: 1px solid #eee;
        padding-top: 20px;
    }

    .milestone-bar {
        margin-bottom: 15px;
    }

    .milestone-label {
        font-size: 12px;
        color: #666;
        margin-bottom: 5px;
        font-weight: 500;
    }

    .bar-container {
        width: 100%;
        height: 20px;
        background: #f0f0f0;
        border-radius: 10px;
        overflow: hidden;
    }

    .bar-progress {
        text-align: right;
        font-size: 12px;
        color: #666;
        margin-top: 3px;
    }
`;
document.head.appendChild(chartStyles);
