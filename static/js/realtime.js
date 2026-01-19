let eventSource = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

document.addEventListener('DOMContentLoaded', function() {
    if (typeof enableRealTimeUpdates !== 'undefined' && enableRealTimeUpdates) {
        startRealTimeUpdates();
    }
    
    fetchActiveAlerts();
});

function startRealTimeUpdates() {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource('/api/vitals/stream');
    
    eventSource.onopen = function() {
        console.log('SSE connection established');
        reconnectAttempts = 0;
        updateConnectionStatus(true);
    };
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            processRealTimeData(data);
        } catch (e) {
            console.error('Error parsing SSE data:', e);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('SSE error:', error);
        updateConnectionStatus(false);
        
        eventSource.close();
        
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay/1000} seconds... (attempt ${reconnectAttempts})`);
            setTimeout(startRealTimeUpdates, delay);
        }
    };
}

function processRealTimeData(data) {
    if (data.vitals && Array.isArray(data.vitals)) {
        data.vitals.forEach(vital => {
            updateVitalDisplay(vital.patient_id, vital);
        });
    }
    
    if (data.alerts && Array.isArray(data.alerts) && data.alerts.length > 0) {
        data.alerts.forEach(alert => {
            if (alert.severity === 'critical') {
                showEmergencyAlert(alert);
            } else {
                showAlertNotification(alert);
            }
        });
        
        updateAlertCount(data.alerts.length);
    }
}

function showAlertNotification(alert) {
    const container = document.getElementById('alertContainer');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${alert.severity === 'critical' ? 'danger' : 'warning'} alert-dismissible fade show`;
    notification.innerHTML = `
        <strong><i class="bi bi-exclamation-triangle-fill me-2"></i>${alert.title}</strong>
        <p class="mb-0 small">${alert.message}</p>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 150);
    }, 10000);
}

function updateAlertCount(newAlerts) {
    const badge = document.getElementById('alertCount');
    if (badge) {
        const current = parseInt(badge.textContent) || 0;
        const total = current + newAlerts;
        badge.textContent = total;
        badge.style.display = total > 0 ? 'inline' : 'none';
        
        if (newAlerts > 0) {
            const indicator = document.getElementById('alertIndicator');
            if (indicator) {
                indicator.classList.add('pulse-alert');
                setTimeout(() => indicator.classList.remove('pulse-alert'), 1000);
            }
        }
    }
}

function updateConnectionStatus(connected) {
    const indicator = document.getElementById('liveIndicator');
    if (indicator) {
        if (connected) {
            indicator.className = 'badge bg-success';
            indicator.innerHTML = '<i class="bi bi-circle-fill me-1"></i>LIVE';
        } else {
            indicator.className = 'badge bg-warning';
            indicator.innerHTML = '<i class="bi bi-circle me-1"></i>RECONNECTING...';
        }
    }
}

function fetchActiveAlerts() {
    fetch('/api/alerts/active')
        .then(response => response.json())
        .then(alerts => {
            const badge = document.getElementById('alertCount');
            if (badge) {
                const criticalCount = alerts.filter(a => a.severity === 'critical').length;
                badge.textContent = criticalCount;
                badge.style.display = criticalCount > 0 ? 'inline' : 'none';
            }
        })
        .catch(error => console.error('Error fetching alerts:', error));
}

window.addEventListener('beforeunload', function() {
    if (eventSource) {
        eventSource.close();
    }
});
