/**
 * Stock Notification System JavaScript
 * Handles real-time updates and interactions for stock alerts
 */

class StockNotificationManager {
    constructor() {
        this.updateInterval = 30000; // Update every 30 seconds
        this.notificationWidget = document.getElementById('stockNotificationWidget');
        this.init();
    }
    
    init() {
        // Start periodic updates
        this.startPeriodicUpdates();
        
        // Bind event listeners
        this.bindEventListeners();
        
        // Initial update
        this.updateNotifications();
    }
    
    startPeriodicUpdates() {
        setInterval(() => {
            this.updateNotifications();
        }, this.updateInterval);
    }
    
    bindEventListeners() {
        // Listen for alert dismissals
        if (this.notificationWidget) {
            this.notificationWidget.addEventListener('click', (e) => {
                if (e.target.classList.contains('btn-close')) {
                    this.handleAlertDismissal(e);
                }
            });
        }
    }
    
    async updateNotifications() {
        try {
            const response = await fetch('/inventory/alerts/json/');
            if (response.ok) {
                const data = await response.json();
                this.updateNotificationDisplay(data);
            }
        } catch (error) {
            console.error('Error updating notifications:', error);
        }
    }
    
    updateNotificationDisplay(data) {
        if (!this.notificationWidget) return;
        
        if (data.count > 0) {
            this.renderNotifications(data.alerts);
        } else {
            this.renderNoAlerts();
        }
    }
    
    renderNotifications(alerts) {
        const notificationList = this.notificationWidget.querySelector('.notification-list');
        if (!notificationList) return;
        
        notificationList.innerHTML = alerts.map(alert => this.createAlertHTML(alert)).join('');
    }
    
    createAlertHTML(alert) {
        const priorityClass = this.getPriorityClass(alert.priority);
        const alertTypeIcon = alert.type === 'Out of Stock' ? 'times-circle' : 'exclamation-triangle';
        
        return `
            <div class="notification-item alert alert-${priorityClass} alert-dismissible fade show" role="alert" data-alert-id="${alert.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="alert-heading mb-1">
                            <i class="fas fa-${alertTypeIcon} me-2"></i>
                            ${alert.type}
                        </h6>
                        <p class="mb-1"><strong>${alert.product.name}</strong></p>
                        <small class="text-muted">
                            Current Stock: ${alert.current_value} | 
                            ${alert.threshold_value ? `Threshold: ${alert.threshold_value} | ` : ''}
                            Priority: ${alert.priority}
                        </small>
                        ${alert.message ? `<p class="mb-0 mt-2">${alert.message}</p>` : ''}
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
                
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="stockNotifications.acknowledgeAlert('${alert.id}')">
                        <i class="fas fa-check me-1"></i>Acknowledge
                    </button>
                    <button class="btn btn-sm btn-outline-success me-1" onclick="stockNotifications.resolveAlert('${alert.id}')">
                        <i class="fas fa-check-double me-1"></i>Resolve
                    </button>
                    <a href="/admin/catalog/product/${alert.product.id}/change/" class="btn btn-sm btn-outline-secondary">
                        <i class="fas fa-edit me-1"></i>Manage
                    </a>
                </div>
            </div>
        `;
    }
    
    renderNoAlerts() {
        const notificationList = this.notificationWidget.querySelector('.notification-list');
        if (!notificationList) return;
        
        notificationList.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-check-circle text-success fa-2x mb-2"></i>
                <p class="mb-0">No active stock alerts</p>
                <small>All products have sufficient stock levels</small>
            </div>
        `;
    }
    
    getPriorityClass(priority) {
        switch (priority.toLowerCase()) {
            case 'critical': return 'danger';
            case 'high': return 'warning';
            case 'medium': return 'info';
            case 'low': return 'success';
            default: return 'info';
        }
    }
    
    async acknowledgeAlert(alertId) {
        try {
            const response = await fetch(`/inventory/alerts/${alertId}/acknowledge/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.showToast('Success', data.message, 'success');
                this.updateNotifications();
            } else {
                throw new Error('Failed to acknowledge alert');
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            this.showToast('Error', 'Failed to acknowledge alert', 'error');
        }
    }
    
    async resolveAlert(alertId) {
        try {
            const response = await fetch(`/inventory/alerts/${alertId}/resolve/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.showToast('Success', data.message, 'success');
                this.updateNotifications();
            } else {
                throw new Error('Failed to resolve alert');
            }
        } catch (error) {
            console.error('Error resolving alert:', error);
            this.showToast('Error', 'Failed to resolve alert', 'error');
        }
    }
    
    handleAlertDismissal(event) {
        const alertItem = event.target.closest('.notification-item');
        if (alertItem) {
            alertItem.remove();
        }
    }
    
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
    
    showToast(title, message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <div class="toast-header">
                <strong>${title}</strong>
                <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('stockNotificationWidget')) {
        window.stockNotifications = new StockNotificationManager();
    }
});

// Add toast notification styles
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        min-width: 300px;
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    }
    
    .toast-success {
        border-left: 4px solid #28a745;
    }
    
    .toast-error {
        border-left: 4px solid #dc3545;
    }
    
    .toast-info {
        border-left: 4px solid #17a2b8;
    }
    
    .toast-warning {
        border-left: 4px solid #ffc107;
    }
    
    .toast-header {
        padding: 10px 15px;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .toast-body {
        padding: 10px 15px;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;

document.head.appendChild(toastStyles);
