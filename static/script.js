class DepartureBoard {
    constructor() {
        this.refreshInterval = 30000; // 30 seconds
        this.isRefreshing = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDepartures();
        this.startAutoRefresh();
    }

    bindEvents() {
        // No refresh button, so no events to bind
    }

    async loadDepartures() {
        if (this.isRefreshing) return;
        
        this.isRefreshing = true;

        try {
            const response = await fetch('/api/departures');
            const data = await response.json();
            
            if (response.ok) {
                this.updateDisplay(data);
            } else {
                this.showError('Failed to fetch departure data');
            }
        } catch (error) {
            console.error('Error fetching departures:', error);
            this.showError('Network error - check connection');
        } finally {
            this.isRefreshing = false;
        }
    }

    updateDisplay(data) {
        // Update last updated time
        document.getElementById('update-time').textContent = data.last_updated;
        
        // Update platform 1
        this.updatePlatform('platform-1', data.platform_1);
        
        // Update platform 2
        this.updatePlatform('platform-2', data.platform_2);
    }

    updatePlatform(platformId, services) {
        const platformElement = document.getElementById(platformId);
        
        if (services.length === 0) {
            platformElement.innerHTML = '<div class="loading">No services</div>';
            return;
        }

        let html = '';
        services.forEach(service => {
            html += this.createServiceHTML(service);
        });
        
        platformElement.innerHTML = html;
    }


    createServiceHTML(service) {
        const estimatedTime = service.etd && service.etd !== service.std && service.etd !== 'On time' 
            ? `<div class="estimated-time">${this.escapeHtml(service.etd)}</div>` 
            : '';
        
        return `
            <div class="service-item">
                <div class="service-time">
                    <div class="scheduled-time">${this.escapeHtml(service.std)}</div>
                    ${estimatedTime}
                </div>
                <div class="service-details">
                    <div class="destination">${this.escapeHtml(service.destination)}</div>
                    <div class="operator">${this.escapeHtml(service.operator)}</div>
                </div>
                <div class="service-status status-${service.status_class}">
                    ${this.escapeHtml(service.status)}
                </div>
            </div>
        `;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        // Show error in all platforms
        const errorHTML = `<div class="loading" style="color: #ff6b6b;">${message}</div>`;
        document.getElementById('platform-1').innerHTML = errorHTML;
        document.getElementById('platform-2').innerHTML = errorHTML;
    }

    startAutoRefresh() {
        setInterval(() => {
            this.loadDepartures();
        }, this.refreshInterval);
    }
}

// Initialize the departure board when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new DepartureBoard();
});

// Handle page visibility changes to optimize refresh when tab is not visible
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Refresh immediately when tab becomes visible
        if (window.departureBoard) {
            window.departureBoard.loadDepartures();
        }
    }
});
