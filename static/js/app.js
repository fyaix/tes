// Global variables
let socket;
let currentSection = 'setup';
let isGitHubConfigured = false;
let testResults = [];
let totalAccounts = 0;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Initialize the application
function initializeApp() {
    // Show loading screen briefly for better UX
    setTimeout(() => {
        hideLoadingScreen();
    }, 1000);
    
    // Initialize Socket.IO
    initializeSocket();
    
    // Setup navigation
    setupNavigation();
    
    // Setup event listeners
    setupEventListeners();
    
    // Setup form handlers
    setupFormHandlers();
    
    // Load saved GitHub configuration
    loadSavedGitHubConfig();
    
    // Auto-load template configuration
    autoLoadConfiguration();
    
    // Update status
    updateStatus('Ready', 'success');
}

// Hide loading screen and show app
function hideLoadingScreen() {
    const loadingScreen = document.getElementById('loading-screen');
    const app = document.getElementById('app');
    
    loadingScreen.style.opacity = '0';
    loadingScreen.style.visibility = 'hidden';
    
    app.classList.remove('hidden');
}

// Initialize Socket.IO connection
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        updateStatus('Connected', 'success');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateStatus('Disconnected', 'error');
    });
    
    socket.on('testing_update', function(data) {
        updateTestingProgress(data);
    });
    
    socket.on('testing_complete', function(data) {
        handleTestingComplete(data);
    });
    
    socket.on('config_generated', function(data) {
        handleConfigGenerated(data);
    });
    
    socket.on('testing_error', function(data) {
        showToast('Testing Error', data.message, 'error');
        hideTestingProgress();
    });
}

// Setup navigation
function setupNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    
    navButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetSection = this.dataset.section;
            switchSection(targetSection);
        });
    });
}

// Switch between sections
function switchSection(sectionName) {
    // Update navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');
    
    // Update sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionName).classList.add('active');
    
    currentSection = sectionName;
    
    // Scroll to top
    window.scrollTo(0, 0);
    
    // Section-specific actions
    if (sectionName === 'results') {
        loadResults();
    }
}

// Setup all event listeners
function setupEventListeners() {
    // GitHub configuration source radio buttons
    const configSourceRadios = document.querySelectorAll('input[name="config-source"]');
    configSourceRadios.forEach(radio => {
        radio.addEventListener('change', handleConfigSourceChange);
    });
    
    // Filter controls
    const filterStatus = document.getElementById('filter-status');
    if (filterStatus) {
        filterStatus.addEventListener('change', filterResults);
    }
}

// Setup form handlers
function setupFormHandlers() {
    // GitHub setup
    document.getElementById('setup-github-btn').addEventListener('click', setupGitHub);
    
    // Load configuration
    document.getElementById('load-config-btn').addEventListener('click', loadConfiguration);
    
    // Add links and test
    document.getElementById('add-and-test-btn').addEventListener('click', addLinksAndTest);
    
    // Download configuration
    document.getElementById('download-config-btn').addEventListener('click', downloadConfiguration);
    
    // Upload to GitHub
    document.getElementById('upload-github-btn').addEventListener('click', uploadToGitHub);
}

// Handle configuration source change
function handleConfigSourceChange(event) {
    const githubFileSelection = document.getElementById('github-file-selection');
    
    if (event.target.value === 'github') {
        if (isGitHubConfigured) {
            githubFileSelection.classList.remove('hidden');
            loadGitHubFiles();
        } else {
            showToast('GitHub Required', 'Please configure GitHub integration first', 'warning');
            document.querySelector('input[name="config-source"][value="local"]').checked = true;
        }
    } else {
        githubFileSelection.classList.add('hidden');
    }
}

// Update status indicator
function updateStatus(text, type = 'info') {
    const statusText = document.getElementById('status-text');
    const statusDot = document.querySelector('.status-dot');
    
    statusText.textContent = text;
    
    // Remove existing status classes
    statusDot.classList.remove('success', 'error', 'warning', 'info');
    
    // Add new status class
    statusDot.classList.add(type);
    
    // Update CSS custom property for status color
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };
    
    statusDot.style.background = colors[type] || colors.info;
}

// Show toast notification
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon"></div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        removeToast(toast);
    }, 5000);
    
    // Click to dismiss
    toast.addEventListener('click', () => {
        removeToast(toast);
    });
}

// Remove toast notification
function removeToast(toast) {
    toast.classList.remove('show');
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

// Set button loading state
function setButtonLoading(buttonId, loading = true) {
    const button = document.getElementById(buttonId);
    const btnText = button.querySelector('.btn-text');
    const btnLoader = button.querySelector('.btn-loader');
    
    if (loading) {
        button.disabled = true;
        btnText.style.opacity = '0';
        btnLoader.classList.remove('hidden');
    } else {
        button.disabled = false;
        btnText.style.opacity = '1';
        btnLoader.classList.add('hidden');
    }
}

// GitHub Integration Functions
async function setupGitHub() {
    const token = document.getElementById('github-token').value.trim();
    const owner = document.getElementById('github-owner').value.trim();
    const repo = document.getElementById('github-repo').value.trim();
    
    if (!token || !owner || !repo) {
        showToast('Missing Information', 'Please fill in all GitHub fields', 'warning');
        return;
    }
    
    setButtonLoading('setup-github-btn', true);
    updateStatus('Configuring GitHub...', 'info');
    
    try {
        const response = await fetch('/api/setup-github', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token, owner, repo }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            isGitHubConfigured = true;
            updateGitHubStatus('success');
            showToast('Success', data.message, 'success');
            updateStatus('GitHub configured', 'success');
        } else {
            updateGitHubStatus('error');
            showToast('Configuration Failed', data.message, 'error');
            updateStatus('GitHub configuration failed', 'error');
        }
    } catch (error) {
        console.error('GitHub setup error:', error);
        updateGitHubStatus('error');
        showToast('Network Error', 'Failed to connect to server', 'error');
        updateStatus('Network error', 'error');
    } finally {
        setButtonLoading('setup-github-btn', false);
    }
}

// Update GitHub status badge
function updateGitHubStatus(status) {
    const badge = document.getElementById('github-status');
    
    badge.classList.remove('success', 'error');
    
    if (status === 'success') {
        badge.textContent = 'Configured';
        badge.classList.add('success');
    } else if (status === 'error') {
        badge.textContent = 'Error';
        badge.classList.add('error');
    } else {
        badge.textContent = 'Not Configured';
    }
}

// Load GitHub files
async function loadGitHubFiles() {
    if (!isGitHubConfigured) return;
    
    const select = document.getElementById('github-files');
    select.innerHTML = '<option value="">Loading...</option>';
    
    try {
        const response = await fetch('/api/list-github-files');
        const data = await response.json();
        
        if (data.success) {
            select.innerHTML = '<option value="">Select a file...</option>';
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file.path;
                option.textContent = file.name;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option value="">Error loading files</option>';
            showToast('Load Error', data.message, 'error');
        }
    } catch (error) {
        console.error('Load GitHub files error:', error);
        select.innerHTML = '<option value="">Network error</option>';
        showToast('Network Error', 'Failed to load GitHub files', 'error');
    }
}

// Load saved GitHub configuration
async function loadSavedGitHubConfig() {
    try {
        const response = await fetch('/api/get-github-config');
        const data = await response.json();
        
        if (data.success && data.config.configured) {
            document.getElementById('github-owner').value = data.config.owner;
            document.getElementById('github-repo').value = data.config.repo;
            isGitHubConfigured = true;
            updateGitHubStatus('success');
        }
    } catch (error) {
        console.error('Load GitHub config error:', error);
    }
}

// Auto-load configuration on startup
async function autoLoadConfiguration() {
    const requestData = { source: 'local' };
    
    try {
        const response = await fetch('/api/load-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateStatus('Template loaded', 'success');
            showSetupStatus('Local template loaded successfully', 'success');
        } else {
            updateStatus('Template load failed', 'warning');
            showSetupStatus('Failed to load local template', 'error');
        }
    } catch (error) {
        console.error('Auto-load configuration error:', error);
        updateStatus('Template unavailable', 'warning');
        showSetupStatus('Template file not found', 'error');
    }
}

// Manual configuration loading
async function loadConfiguration() {
    const configSource = document.querySelector('input[name="config-source"]:checked').value;
    let requestData = { source: configSource };
    
    if (configSource === 'github') {
        const filePath = document.getElementById('github-files').value;
        if (!filePath) {
            showToast('File Required', 'Please select a GitHub file', 'warning');
            return;
        }
        requestData.file_path = filePath;
    }
    
    setButtonLoading('load-config-btn', true);
    updateStatus('Loading configuration...', 'info');
    
    try {
        const response = await fetch('/api/load-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Success', data.message, 'success');
            updateStatus('Configuration loaded', 'success');
            showSetupStatus(data.message, 'success');
        } else {
            showToast('Load Failed', data.message, 'error');
            updateStatus('Load failed', 'error');
            showSetupStatus(data.message, 'error');
        }
    } catch (error) {
        console.error('Load configuration error:', error);
        showToast('Network Error', 'Failed to load configuration', 'error');
        updateStatus('Network error', 'error');
        showSetupStatus('Network error occurred', 'error');
    } finally {
        setButtonLoading('load-config-btn', false);
    }
}

// Show setup status message
function showSetupStatus(message, type) {
    const statusCard = document.getElementById('setup-status');
    const statusMessage = document.getElementById('setup-status-message');
    
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusCard.style.display = 'block';
}

// Add links and start testing
async function addLinksAndTest() {
    const linksText = document.getElementById('vpn-links').value.trim();
    
    if (!linksText) {
        showToast('No Links', 'Please paste some VPN links', 'warning');
        return;
    }
    
    setButtonLoading('add-and-test-btn', true);
    updateStatus('Adding links...', 'info');
    
    try {
        const response = await fetch('/api/add-links-and-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ links: linksText }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Success', data.message, 'success');
            updateStatus('Starting tests...', 'info');
            
            // Update account counts
            totalAccounts = data.total_accounts;
            document.getElementById('total-accounts').textContent = totalAccounts;
            document.getElementById('test-status').textContent = '🔄';
            
            // Show quick stats
            document.getElementById('quick-stats').style.display = 'block';
            
            // Clear the textarea
            document.getElementById('vpn-links').value = '';
            
            if (data.invalid_links.length > 0) {
                showToast('Some Invalid Links', `${data.invalid_links.length} links could not be parsed`, 'warning');
            }
            
            // Switch to testing section and start testing
            switchSection('testing');
            startTesting();
            
        } else {
            showToast('Add Failed', data.message, 'error');
            updateStatus('Add failed', 'error');
        }
    } catch (error) {
        console.error('Add links error:', error);
        showToast('Network Error', 'Failed to add links', 'error');
        updateStatus('Network error', 'error');
    } finally {
        setButtonLoading('add-and-test-btn', false);
    }
}

// Update account counts and statistics
async function updateAccountCounts() {
    try {
        const response = await fetch('/api/get-results');
        const data = await response.json();
        
        totalAccounts = data.total_accounts;
        
        // Update UI
        document.getElementById('total-accounts').textContent = totalAccounts;
        document.getElementById('test-total').textContent = totalAccounts;
        
        // Count by type (this would need to be implemented in the backend)
        // For now, we'll just show the total
        document.getElementById('vless-count').textContent = '—';
        document.getElementById('trojan-count').textContent = '—';
        document.getElementById('ss-count').textContent = '—';
        
    } catch (error) {
        console.error('Update account counts error:', error);
    }
}

// Log activity
function logActivity(message) {
    const activityCard = document.getElementById('recent-activity');
    const activityLog = document.getElementById('activity-log');
    
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = 'activity-entry';
    logEntry.innerHTML = `
        <span class="activity-time">${timestamp}</span>
        <span class="activity-message">${message}</span>
    `;
    
    activityLog.insertBefore(logEntry, activityLog.firstChild);
    activityCard.style.display = 'block';
    
    // Keep only last 10 entries
    while (activityLog.children.length > 10) {
        activityLog.removeChild(activityLog.lastChild);
    }
}

// Testing Functions
function startTesting() {
    if (totalAccounts === 0) {
        showToast('No Accounts', 'Please add some VPN accounts first', 'warning');
        return;
    }
    
    updateStatus('Starting tests...', 'info');
    
    showTestingProgress();
    
    // Start testing via Socket.IO
    socket.emit('start_testing');
}

// Show testing progress UI
function showTestingProgress() {
    document.getElementById('testing-progress').style.display = 'block';
    document.getElementById('live-results').style.display = 'block';
    
    // Reset progress
    updateProgressBar(0);
    updateTestStats(0, 0, 0);
}

// Hide testing progress UI
function hideTestingProgress() {
    updateStatus('Testing stopped', 'warning');
}

// Update testing progress
function updateTestingProgress(data) {
    const completed = data.results.filter(r => r.Status !== 'WAIT' && !r.Status.startsWith('Testing') && !r.Status.startsWith('Retry')).length;
    const total = data.total;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    updateProgressBar(percentage);
    
    // Update progress text
    document.getElementById('progress-text').textContent = `${completed} / ${total} accounts tested`;
    document.getElementById('progress-percent').textContent = `${percentage}%`;
    
    // Count stats
    const successful = data.results.filter(r => r.Status === '●').length;
    const failed = data.results.filter(r => r.Status.startsWith('✖')).length;
    const testing = data.results.filter(r => r.Status.startsWith('Testing') || r.Status.startsWith('Retry')).length;
    
    updateTestStats(successful, failed, testing);
    
    // Update live results
    updateLiveResults(data.results);
    
    updateStatus(`Testing... ${completed}/${total}`, 'info');
}

// Handle testing completion
function handleTestingComplete(data) {
    updateStatus(`Testing complete: ${data.successful}/${data.total} successful`, 'success');
    
    showToast('Testing Complete', `${data.successful} out of ${data.total} accounts passed`, 'success');
    
    testResults = data.results;
    
    // Update results section
    updateResultsSummary(data);
    
    // Update test status
    document.getElementById('test-status').textContent = data.successful > 0 ? '✅' : '❌';
    
    // Show notification for auto-generated config
    if (data.successful > 0) {
        document.getElementById('config-notification').style.display = 'block';
    }
}

// Handle auto-generated configuration
function handleConfigGenerated(data) {
    if (data.success) {
        showToast('Config Generated', `Configuration auto-generated with ${data.account_count} accounts`, 'success');
        
        // Update export section
        document.getElementById('config-account-count').textContent = data.account_count;
        document.getElementById('config-timestamp').textContent = new Date().toLocaleTimeString();
        document.getElementById('config-badge').textContent = 'Auto-Generated';
        
        // Enable GitHub upload if configured
        if (isGitHubConfigured) {
            document.getElementById('github-upload-status').textContent = 'Ready';
            document.getElementById('github-upload-status').classList.add('success');
        }
    } else {
        showToast('Config Generation Failed', data.error, 'error');
    }
}

// Update progress bar
function updateProgressBar(percentage) {
    document.getElementById('progress-fill').style.width = `${percentage}%`;
}

// Update test statistics
function updateTestStats(successful, failed, testing) {
    document.getElementById('successful-count').textContent = successful;
    document.getElementById('failed-count').textContent = failed;
    document.getElementById('testing-count').textContent = testing;
}

// Update live results display
function updateLiveResults(results) {
    const tableBody = document.getElementById('testing-table-body');
    tableBody.innerHTML = '';
    
    results.forEach((result, index) => {
        const row = createTestingTableRow(result, index);
        tableBody.appendChild(row);
    });
}

// Create testing table row
function createTestingTableRow(result, index) {
    const row = document.createElement('tr');
    
    const statusText = getStatusText(result.Status);
    const statusClass = getStatusClass(result.Status);
    const latencyText = result.Latency !== -1 ? `${result.Latency}ms` : '—';
    const jitterText = result.Jitter !== -1 ? `${result.Jitter}ms` : '—';
    
    row.innerHTML = `
        <td>${index + 1}</td>
        <td class="type-cell">${result.VpnType}</td>
        <td>${result.Country}</td>
        <td>${result.Provider}</td>
        <td>${result['Tested IP']}</td>
        <td class="latency-cell">${latencyText}</td>
        <td class="latency-cell">${jitterText}</td>
        <td class="status-cell">${result.ICMP}</td>
        <td class="status-cell ${statusClass}">${statusText}</td>
    `;
    
    return row;
}

// Get CSS class for status
function getStatusClass(status) {
    if (status === '●') return 'status-success';
    if (status.startsWith('✖')) return 'status-failed';
    if (status.startsWith('Testing') || status.startsWith('Retry')) return 'status-testing';
    return 'status-waiting';
}

// Get status text for display
function getStatusText(status) {
    if (status === '●') return '✅';
    if (status.startsWith('✖')) return '❌';
    if (status.startsWith('Testing')) return '🔄';
    if (status.startsWith('Retry')) return '🔁';
    if (status === 'WAIT') return '⏳';
    return status;
}

// Results Functions
async function loadResults() {
    try {
        const response = await fetch('/api/get-results');
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            testResults = data.results;
            displayDetailedResults(data.results);
            updateResultsSummary(data);
            
            if (data.has_config) {
                showExportOptions();
            }
        }
    } catch (error) {
        console.error('Load results error:', error);
    }
}

// Update results summary
function updateResultsSummary(data) {
    const successful = data.results.filter(r => r.Status === '●').length;
    const failed = data.results.filter(r => r.Status.startsWith('✖')).length;
    
    // Calculate average latency
    const successfulResults = data.results.filter(r => r.Status === '●' && r.Latency !== -1);
    const avgLatency = successfulResults.length > 0 
        ? Math.round(successfulResults.reduce((sum, r) => sum + r.Latency, 0) / successfulResults.length)
        : 0;
    
    document.getElementById('summary-successful').textContent = successful;
    document.getElementById('summary-failed').textContent = failed;
    document.getElementById('summary-avg-latency').textContent = `${avgLatency}ms`;
    
    document.getElementById('results-summary').style.display = 'block';
    document.getElementById('detailed-results').style.display = 'block';
}

// Display detailed results
function displayDetailedResults(results) {
    const container = document.getElementById('results-table');
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = '<p>No results available</p>';
        return;
    }
    
    // Create table
    const table = document.createElement('div');
    table.className = 'results-table';
    
    // Create header
    const header = document.createElement('div');
    header.className = 'result-header';
    header.innerHTML = `
        <div>Status</div>
        <div>Location</div>
        <div>Type</div>
        <div>Latency</div>
        <div>IP</div>
    `;
    table.appendChild(header);
    
    // Add results
    results.forEach(result => {
        const row = createDetailedResultRow(result);
        table.appendChild(row);
    });
    
    container.appendChild(table);
}

// Create detailed result row
function createDetailedResultRow(result) {
    const row = document.createElement('div');
    row.className = 'result-row';
    
    const statusClass = getStatusClass(result.Status);
    const latencyText = result.Latency !== -1 ? `${result.Latency}ms` : '—';
    
    row.innerHTML = `
        <div class="result-status ${statusClass}"></div>
        <div>${result.Country} ${result.Provider}</div>
        <div>${result.VpnType.toUpperCase()}</div>
        <div>${latencyText}</div>
        <div>${result['Tested IP']}</div>
    `;
    
    return row;
}

// Filter results
function filterResults() {
    const filterValue = document.getElementById('filter-status').value;
    let filteredResults = testResults;
    
    if (filterValue === 'successful') {
        filteredResults = testResults.filter(r => r.Status === '●');
    } else if (filterValue === 'failed') {
        filteredResults = testResults.filter(r => r.Status.startsWith('✖'));
    }
    
    displayDetailedResults(filteredResults);
}

// Export Functions (Auto-generated, so no manual generation needed)

async function downloadConfiguration() {
    updateStatus('Downloading configuration...', 'info');
    
    try {
        const response = await fetch('/api/download-config');
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'VortexVpn-config.json';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('Success', 'Configuration downloaded', 'success');
            updateStatus('Download complete', 'success');
            logActivity('Configuration downloaded');
        } else {
            const data = await response.json();
            showToast('Download Failed', data.message, 'error');
        }
    } catch (error) {
        console.error('Download error:', error);
        showToast('Network Error', 'Failed to download configuration', 'error');
        updateStatus('Download error', 'error');
    }
}

async function uploadToGitHub() {
    const commitMessage = document.getElementById('commit-message').value.trim();
    
    if (!commitMessage) {
        showToast('Commit Message Required', 'Please enter a commit message', 'warning');
        return;
    }
    
    setButtonLoading('upload-github-btn', true);
    updateStatus('Uploading to GitHub...', 'info');
    
    try {
        const response = await fetch('/api/upload-to-github', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ commit_message: commitMessage }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Success', data.message, 'success');
            updateStatus('Upload complete', 'success');
            logActivity('Configuration uploaded to GitHub');
        } else {
            showToast('Upload Failed', data.message, 'error');
            updateStatus('Upload failed', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Network Error', 'Failed to upload to GitHub', 'error');
        updateStatus('Upload error', 'error');
    } finally {
        setButtonLoading('upload-github-btn', false);
    }
}

// Mobile-specific enhancements
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed');
            });
    });
}

// Handle mobile back button
window.addEventListener('popstate', function(event) {
    // Handle navigation history
});

// Handle orientation change
window.addEventListener('orientationchange', function() {
    setTimeout(() => {
        // Refresh layout if needed
    }, 100);
});

// Touch gestures for better mobile UX
let touchStartY = 0;
let touchEndY = 0;

document.addEventListener('touchstart', function(event) {
    touchStartY = event.changedTouches[0].screenY;
}, { passive: true });

document.addEventListener('touchend', function(event) {
    touchEndY = event.changedTouches[0].screenY;
    handleGesture();
}, { passive: true });

function handleGesture() {
    const threshold = 50;
    const diff = touchStartY - touchEndY;
    
    if (Math.abs(diff) > threshold) {
        // Handle swipe gestures if needed
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Add CSS for dynamic elements
const dynamicStyles = document.createElement('style');
dynamicStyles.textContent = `
    .activity-entry {
        display: flex;
        justify-content: space-between;
        padding: var(--space-sm);
        border-bottom: 1px solid var(--border-primary);
        font-size: var(--font-size-sm);
    }
    
    .activity-time {
        color: var(--text-muted);
        font-size: var(--font-size-xs);
    }
    
    .activity-message {
        color: var(--text-secondary);
    }
    
    .results-table {
        display: flex;
        flex-direction: column;
    }
    
    .result-header,
    .result-row {
        display: grid;
        grid-template-columns: auto 2fr 1fr 1fr 1.5fr;
        gap: var(--space-sm);
        padding: var(--space-sm) var(--space-md);
        align-items: center;
        border-bottom: 1px solid var(--border-primary);
    }
    
    .result-header {
        background: var(--bg-primary);
        font-weight: 600;
        font-size: var(--font-size-sm);
        color: var(--text-primary);
    }
    
    .result-row {
        font-size: var(--font-size-sm);
        color: var(--text-secondary);
    }
    
    .result-row:hover {
        background: var(--bg-primary);
    }
    
    .status-message {
        padding: var(--space-md);
        border-radius: var(--radius-md);
        border-left: 4px solid;
    }
    
    .status-message.success {
        background: rgba(16, 185, 129, 0.1);
        border-color: var(--success);
        color: var(--success);
    }
    
    .status-message.error {
        background: rgba(239, 68, 68, 0.1);
        border-color: var(--error);
        color: var(--error);
    }
    
    @media (max-width: 768px) {
        .result-header,
        .result-row {
            grid-template-columns: auto 1fr auto;
        }
        
        .result-header div:nth-child(3),
        .result-header div:nth-child(5),
        .result-row div:nth-child(3),
        .result-row div:nth-child(5) {
            display: none;
        }
    }
`;

document.head.appendChild(dynamicStyles);