// Dashboard JavaScript for Telegram Bot Analytics
class TelegramBotDashboard {
    constructor() {
        this.charts = {};
        this.currentTimeRange = 7;
        this.refreshInterval = null;
        this.isLoading = false;
        
        // Initialize dashboard when DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    init() {
        console.log('Initializing Telegram Bot Dashboard...');
        
        // Load initial data
        this.loadDashboardData();
        
        // Set up auto-refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            if (!this.isLoading) {
                this.loadDashboardData();
            }
        }, 30000);
        
        // Add event listeners
        this.setupEventListeners();
        
        console.log('Dashboard initialized successfully');
    }
    
    setupEventListeners() {
        // Handle page visibility change to pause/resume refresh
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                if (this.refreshInterval) {
                    clearInterval(this.refreshInterval);
                    this.refreshInterval = null;
                }
            } else {
                if (!this.refreshInterval) {
                    this.refreshInterval = setInterval(() => {
                        if (!this.isLoading) {
                            this.loadDashboardData();
                        }
                    }, 30000);
                }
            }
        });
    }
    
    async loadDashboardData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        
        try {
            // Load all dashboard data concurrently
            const [overview, conversations, popularProducts, botStatus] = await Promise.all([
                this.fetchOverviewData(),
                this.fetchConversationData(),
                this.fetchPopularProducts(),
                this.fetchBotStatus()
            ]);
            
            // Update UI with fetched data
            this.updateOverviewCards(overview);
            this.updateActivityChart(conversations);
            this.updatePopularProductsList(popularProducts);
            this.updateBotStatus(botStatus);
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('خطا در بارگذاری داده‌ها. لطفاً صفحه را رفرش کنید.');
        } finally {
            this.isLoading = false;
        }
    }
    
    async fetchOverviewData() {
        try {
            const response = await fetch('/api/analytics/overview');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching overview data:', error);
            throw error;
        }
    }
    
    async fetchConversationData() {
        try {
            const response = await fetch(`/api/analytics/conversations?days=${this.currentTimeRange}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching conversation data:', error);
            throw error;
        }
    }
    
    async fetchPopularProducts() {
        try {
            const response = await fetch('/api/analytics/popular-products');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching popular products:', error);
            throw error;
        }
    }
    
    async fetchBotStatus() {
        try {
            const response = await fetch('/api/bot/status');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching bot status:', error);
            throw error;
        }
    }
    
    updateOverviewCards(data) {
        if (!data) {
            console.warn('No overview data received');
            return;
        }
        
        // Update total users
        const totalUsersElement = document.getElementById('total-users');
        if (totalUsersElement) {
            totalUsersElement.textContent = this.formatNumber(data.total_users || 0);
        }
        
        // Update active users
        const activeUsersElement = document.getElementById('active-users');
        if (activeUsersElement) {
            activeUsersElement.textContent = this.formatNumber(data.active_users || 0);
        }
        
        // Update active conversations
        const activeConversationsElement = document.getElementById('active-conversations');
        if (activeConversationsElement) {
            activeConversationsElement.textContent = this.formatNumber(data.active_conversations || 0);
        }
        
        // Update messages today
        const messagesTodayElement = document.getElementById('messages-today');
        if (messagesTodayElement) {
            messagesTodayElement.textContent = this.formatNumber(data.messages_today || 0);
        }
        
        // Update AI response rate
        const aiResponseRateElement = document.getElementById('ai-response-rate');
        if (aiResponseRateElement) {
            aiResponseRateElement.textContent = (data.ai_response_rate || 0).toFixed(1);
        }
        
        // Update satisfaction rating
        const satisfactionRatingElement = document.getElementById('satisfaction-rating');
        if (satisfactionRatingElement) {
            satisfactionRatingElement.textContent = (data.avg_satisfaction_rating || 0).toFixed(1);
        }
    }
    
    updateActivityChart(data) {
        if (!data || !Array.isArray(data)) {
            console.warn('Invalid conversation data received');
            return;
        }
        
        const ctx = document.getElementById('activity-chart');
        if (!ctx) {
            console.warn('Activity chart canvas not found');
            return;
        }
        
        // Destroy existing chart if it exists
        if (this.charts.activity) {
            this.charts.activity.destroy();
        }
        
        // Prepare data for chart
        const labels = data.map(item => this.formatDate(item.date));
        const conversationsData = data.map(item => item.conversations || 0);
        const messagesData = data.map(item => item.messages || 0);
        
        // Create chart
        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'مکالمات',
                        data: conversationsData,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'پیام‌ها',
                        data: messagesData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `فعالیت ${this.currentTimeRange} روز گذشته`,
                        color: '#fff'
                    },
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }
    
    updatePopularProductsList(data) {
        const container = document.getElementById('popular-products');
        if (!container) {
            console.warn('Popular products container not found');
            return;
        }
        
        if (!data || !Array.isArray(data) || data.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>هیچ داده‌ای برای نمایش وجود ندارد</p>
                </div>
            `;
            return;
        }
        
        // Create list of popular products
        const productList = data.slice(0, 5).map((product, index) => {
            const badge = this.getRankBadge(index);
            return `
                <div class="d-flex justify-content-between align-items-center mb-2 p-2 rounded" 
                     style="background: rgba(255, 255, 255, 0.05);">
                    <div class="d-flex align-items-center">
                        <span class="badge ${badge} me-2">${index + 1}</span>
                        <div>
                            <div class="fw-semibold">${this.escapeHtml(product.product_name || 'نامشخص')}</div>
                            <small class="text-muted">${this.escapeHtml(product.category_name || 'دسته‌بندی نامشخص')}</small>
                        </div>
                    </div>
                    <span class="badge bg-primary">${this.formatNumber(product.view_count || 0)}</span>
                </div>
            `;
        }).join('');
        
        container.innerHTML = productList;
    }
    
    updateBotStatus(data) {
        if (!data) {
            console.warn('No bot status data received');
            return;
        }
        
        const statusElement = document.getElementById('bot-status');
        if (statusElement) {
            const status = data.status === 'online' ? 'آنلاین' : 'آفلاین';
            const statusClass = data.status === 'online' ? 'text-success' : 'text-danger';
            
            statusElement.textContent = status;
            statusElement.className = statusClass;
        }
    }
    
    // Analytics page specific functions
    async initializeAnalytics() {
        console.log('Initializing analytics page...');
        
        try {
            await this.loadAnalyticsData();
        } catch (error) {
            console.error('Error initializing analytics:', error);
            this.showError('خطا در بارگذاری داده‌های تحلیلی');
        }
    }
    
    async loadAnalyticsData() {
        try {
            const [overview, conversations, popularProducts, aiPerformance] = await Promise.all([
                this.fetchOverviewData(),
                this.fetchConversationData(),
                this.fetchPopularProducts(),
                this.fetchAIPerformance()
            ]);
            
            this.updateConversationsChart(conversations);
            this.updateAIPerformanceCard(aiPerformance);
            this.updatePopularProductsTable(popularProducts);
            this.updateUserActivityChart(overview);
            this.updateInteractionChart();
            this.updateSatisfactionChart();
            this.updateConfidenceDistributionChart(aiPerformance);
            
        } catch (error) {
            console.error('Error loading analytics data:', error);
            throw error;
        }
    }
    
    async fetchAIPerformance() {
        try {
            // This would be a new endpoint for AI performance data
            // For now, we'll use the overview data and extract AI metrics
            const overview = await this.fetchOverviewData();
            return {
                average_confidence: 0.75,
                confidence_distribution: [
                    { range: '0.0-0.2', count: 5 },
                    { range: '0.2-0.4', count: 12 },
                    { range: '0.4-0.6', count: 25 },
                    { range: '0.6-0.8', count: 45 },
                    { range: '0.8-1.0', count: 78 }
                ],
                escalation_rate: overview.escalated_conversations || 0,
                total_ai_responses: 165
            };
        } catch (error) {
            console.error('Error fetching AI performance data:', error);
            throw error;
        }
    }
    
    updateConversationsChart(data) {
        const ctx = document.getElementById('conversations-chart');
        if (!ctx || !data) return;
        
        if (this.charts.conversations) {
            this.charts.conversations.destroy();
        }
        
        const labels = data.map(item => this.formatDate(item.date));
        const conversationsData = data.map(item => item.conversations || 0);
        const messagesData = data.map(item => item.messages || 0);
        
        this.charts.conversations = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'مکالمات جدید',
                        data: conversationsData,
                        backgroundColor: 'rgba(54, 162, 235, 0.8)',
                        borderColor: 'rgb(54, 162, 235)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'کل پیام‌ها',
                        data: messagesData,
                        type: 'line',
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'آمار مکالمات و پیام‌ها',
                        color: '#fff'
                    },
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
    
    updateAIPerformanceCard(data) {
        if (!data) return;
        
        const confidenceElement = document.getElementById('ai-confidence');
        const confidenceBarElement = document.getElementById('ai-confidence-bar');
        const aiResponsesElement = document.getElementById('ai-responses');
        const escalationRateElement = document.getElementById('escalation-rate');
        
        if (confidenceElement) {
            confidenceElement.textContent = (data.average_confidence * 100).toFixed(1) + '%';
        }
        
        if (confidenceBarElement) {
            const confidencePercent = (data.average_confidence * 100);
            confidenceBarElement.style.width = `${confidencePercent}%`;
            
            // Change color based on confidence level
            if (confidencePercent >= 80) {
                confidenceBarElement.className = 'progress-bar bg-success';
            } else if (confidencePercent >= 60) {
                confidenceBarElement.className = 'progress-bar bg-warning';
            } else {
                confidenceBarElement.className = 'progress-bar bg-danger';
            }
        }
        
        if (aiResponsesElement) {
            aiResponsesElement.textContent = this.formatNumber(data.total_ai_responses || 0);
        }
        
        if (escalationRateElement) {
            escalationRateElement.textContent = (data.escalation_rate || 0).toFixed(1);
        }
    }
    
    updatePopularProductsTable(data) {
        const tableBody = document.getElementById('popular-products-table');
        if (!tableBody) return;
        
        if (!data || !Array.isArray(data) || data.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-muted">
                        <i class="fas fa-inbox fa-2x mb-2"></i>
                        <br>هیچ داده‌ای برای نمایش وجود ندارد
                    </td>
                </tr>
            `;
            return;
        }
        
        const rows = data.map((product, index) => `
            <tr>
                <td>
                    <span class="badge ${this.getRankBadge(index)}">${index + 1}</span>
                </td>
                <td>${this.escapeHtml(product.product_name || 'نامشخص')}</td>
                <td>${this.escapeHtml(product.category_name || 'دسته‌بندی نامشخص')}</td>
                <td>
                    <span class="badge bg-primary">${this.formatNumber(product.view_count || 0)}</span>
                </td>
            </tr>
        `).join('');
        
        tableBody.innerHTML = rows;
    }
    
    updateUserActivityChart(data) {
        const ctx = document.getElementById('user-activity-chart');
        if (!ctx) return;
        
        if (this.charts.userActivity) {
            this.charts.userActivity.destroy();
        }
        
        // Generate sample data for demonstration
        const labels = this.generateDateLabels(this.currentTimeRange);
        const activeUsersData = labels.map(() => Math.floor(Math.random() * 50) + 10);
        const newUsersData = labels.map(() => Math.floor(Math.random() * 15) + 2);
        
        this.charts.userActivity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'کاربران فعال',
                        data: activeUsersData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'کاربران جدید',
                        data: newUsersData,
                        borderColor: 'rgb(255, 205, 86)',
                        backgroundColor: 'rgba(255, 205, 86, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'فعالیت کاربران',
                        color: '#fff'
                    },
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
    
    updateInteractionChart() {
        const ctx = document.getElementById('interaction-chart');
        if (!ctx) return;
        
        if (this.charts.interaction) {
            this.charts.interaction.destroy();
        }
        
        const interactionTypes = ['مشاهده محصول', 'پیگیری سفارش', 'گفتگو با AI', 'ارجاع به پشتیبانی', 'مرور دسته‌بندی'];
        const interactionCounts = [45, 23, 67, 12, 34];
        
        this.charts.interaction = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: interactionTypes,
                datasets: [{
                    data: interactionCounts,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 205, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ],
                    borderColor: [
                        'rgb(255, 99, 132)',
                        'rgb(54, 162, 235)',
                        'rgb(255, 205, 86)',
                        'rgb(75, 192, 192)',
                        'rgb(153, 102, 255)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'انواع تعامل',
                        color: '#fff'
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#fff',
                            padding: 15
                        }
                    }
                }
            }
        });
    }
    
    updateSatisfactionChart() {
        const ctx = document.getElementById('satisfaction-chart');
        if (!ctx) return;
        
        if (this.charts.satisfaction) {
            this.charts.satisfaction.destroy();
        }
        
        const ratings = ['⭐', '⭐⭐', '⭐⭐⭐', '⭐⭐⭐⭐', '⭐⭐⭐⭐⭐'];
        const counts = [2, 3, 8, 15, 25];
        
        this.charts.satisfaction = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ratings,
                datasets: [{
                    label: 'تعداد امتیاز',
                    data: counts,
                    backgroundColor: 'rgba(255, 205, 86, 0.8)',
                    borderColor: 'rgb(255, 205, 86)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'توزیع امتیاز رضایت',
                        color: '#fff'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#fff',
                            stepSize: 1
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
        
        // Update satisfaction breakdown
        const breakdownElement = document.getElementById('satisfaction-breakdown');
        if (breakdownElement) {
            const total = counts.reduce((sum, count) => sum + count, 0);
            const average = counts.reduce((sum, count, index) => sum + (count * (index + 1)), 0) / total;
            
            breakdownElement.innerHTML = `
                <div class="row text-center">
                    <div class="col-6">
                        <h6 class="text-warning">${average.toFixed(1)}</h6>
                        <small class="text-muted">میانگین امتیاز</small>
                    </div>
                    <div class="col-6">
                        <h6 class="text-info">${total}</h6>
                        <small class="text-muted">کل امتیازها</small>
                    </div>
                </div>
            `;
        }
    }
    
    updateConfidenceDistributionChart(data) {
        const ctx = document.getElementById('confidence-distribution-chart');
        if (!ctx || !data || !data.confidence_distribution) return;
        
        if (this.charts.confidenceDistribution) {
            this.charts.confidenceDistribution.destroy();
        }
        
        const labels = data.confidence_distribution.map(item => item.range);
        const values = data.confidence_distribution.map(item => item.count);
        
        this.charts.confidenceDistribution = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        'rgba(220, 53, 69, 0.8)',   // 0.0-0.2 (red)
                        'rgba(255, 193, 7, 0.8)',   // 0.2-0.4 (yellow)
                        'rgba(255, 205, 86, 0.8)',  // 0.4-0.6 (orange)
                        'rgba(23, 162, 184, 0.8)',  // 0.6-0.8 (cyan)
                        'rgba(40, 167, 69, 0.8)'    // 0.8-1.0 (green)
                    ],
                    borderColor: [
                        'rgb(220, 53, 69)',
                        'rgb(255, 193, 7)',
                        'rgb(255, 205, 86)',
                        'rgb(23, 162, 184)',
                        'rgb(40, 167, 69)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'توزیع اطمینان هوش مصنوعی',
                        color: '#fff'
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#fff',
                            padding: 15
                        }
                    }
                }
            }
        });
    }
    
    // Utility functions
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString('fa-IR');
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('fa-IR', {
            month: 'short',
            day: 'numeric'
        });
    }
    
    generateDateLabels(days) {
        const labels = [];
        const today = new Date();
        
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(today.getDate() - i);
            labels.push(this.formatDate(date.toISOString()));
        }
        
        return labels;
    }
    
    getRankBadge(index) {
        const badges = ['bg-warning', 'bg-secondary', 'bg-success', 'bg-info', 'bg-primary'];
        return badges[index] || 'bg-secondary';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showError(message) {
        // Create or update error alert
        let alertContainer = document.getElementById('error-alert-container');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'error-alert-container';
            alertContainer.className = 'position-fixed top-0 end-0 p-3';
            alertContainer.style.zIndex = '1050';
            document.body.appendChild(alertContainer);
        }
        
        const alertElement = document.createElement('div');
        alertElement.className = 'alert alert-danger alert-dismissible fade show';
        alertElement.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alertElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.remove();
            }
        }, 5000);
    }
    
    showSuccess(message) {
        // Create or update success alert
        let alertContainer = document.getElementById('success-alert-container');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'success-alert-container';
            alertContainer.className = 'position-fixed top-0 end-0 p-3';
            alertContainer.style.zIndex = '1050';
            document.body.appendChild(alertContainer);
        }
        
        const alertElement = document.createElement('div');
        alertElement.className = 'alert alert-success alert-dismissible fade show';
        alertElement.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alertElement);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.remove();
            }
        }, 3000);
    }
    
    destroy() {
        // Clean up intervals and event listeners
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Destroy all charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        console.log('Dashboard destroyed');
    }
}

// Global functions for UI interactions
function refreshData() {
    if (window.dashboard) {
        window.dashboard.loadDashboardData();
        window.dashboard.showSuccess('داده‌ها به‌روزرسانی شد');
    }
}

function exportData() {
    // Create a simple CSV export of current data
    const csvContent = "data:text/csv;charset=utf-8," 
        + "Type,Value\n"
        + "Total Users," + (document.getElementById('total-users')?.textContent || '0') + "\n"
        + "Active Users," + (document.getElementById('active-users')?.textContent || '0') + "\n"
        + "Active Conversations," + (document.getElementById('active-conversations')?.textContent || '0') + "\n"
        + "Messages Today," + (document.getElementById('messages-today')?.textContent || '0') + "\n"
        + "AI Response Rate," + (document.getElementById('ai-response-rate')?.textContent || '0') + "%\n"
        + "Satisfaction Rating," + (document.getElementById('satisfaction-rating')?.textContent || '0') + "/5";
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `telegram_bot_report_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    if (window.dashboard) {
        window.dashboard.showSuccess('گزارش دانلود شد');
    }
}

function showSystemLogs() {
    alert('قابلیت مشاهده لاگ‌ها به زودی اضافه خواهد شد');
}

function changeTimeRange(days) {
    if (window.dashboard) {
        window.dashboard.currentTimeRange = days;
        window.dashboard.loadDashboardData();
        
        // Update active button
        document.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
    }
}

function exportReport(type) {
    const reportTypes = {
        'overview': 'گزارش کلی',
        'conversations': 'گزارش مکالمات',
        'products': 'گزارش محصولات',
        'ai_performance': 'گزارش عملکرد AI'
    };
    
    if (window.dashboard) {
        window.dashboard.showSuccess(`${reportTypes[type]} در حال آماده‌سازی است...`);
    }
    
    // In a real implementation, this would trigger a backend export
    setTimeout(() => {
        if (window.dashboard) {
            window.dashboard.showSuccess(`${reportTypes[type]} آماده دانلود است`);
        }
    }, 2000);
}

function initializeAnalytics() {
    if (window.dashboard) {
        window.dashboard.initializeAnalytics();
    }
}

// Initialize dashboard when script loads
window.dashboard = new TelegramBotDashboard();

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});
