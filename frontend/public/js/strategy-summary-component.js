/**
 * Strategy Summary UI Component
 *
 * Professional, collapsible panel that displays AI-generated strategy summaries.
 * Matches the existing EmailPilot calendar design system.
 */

class StrategySummaryComponent {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = null;
        this.state = {
            data: null,
            loading: false,
            error: null,
            expanded: false
        };
        this.options = {
            autoLoad: true,
            showToggle: true,
            animate: true,
            ...options
        };
    }

    /**
     * Initialize the component
     * @param {string} clientId - Client ID to load strategy for
     */
    async init(clientId) {
        this.clientId = clientId;
        this.container = document.getElementById(this.containerId);

        if (!this.container) {
            console.error('[StrategySummary] Container not found:', this.containerId);
            return;
        }

        // Initial render
        this.render();

        // Auto-load if enabled
        if (this.options.autoLoad && clientId) {
            await this.load(clientId);
        }
    }

    /**
     * Load strategy summary from API
     * @param {string} clientId - Client ID
     */
    async load(clientId) {
        this.setState({ loading: true, error: null });

        try {
            const data = await window.strategySummaryAPI.fetchStrategySummary(clientId);

            if (data) {
                this.setState({ data, loading: false });
            } else {
                // No strategy found - hide the component
                this.setState({ data: null, loading: false });
            }
        } catch (error) {
            console.error('[StrategySummary] Load error:', error);
            this.setState({
                loading: false,
                error: 'Failed to load strategy summary'
            });
        }
    }

    /**
     * Update component state and re-render
     * @param {Object} newState - State updates
     */
    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.render();
    }

    /**
     * Toggle expanded/collapsed state
     */
    toggle() {
        this.setState({ expanded: !this.state.expanded });
    }

    /**
     * Render the component
     */
    render() {
        if (!this.container) return;

        const { data, loading, error, expanded } = this.state;

        // Hide if no data and not loading
        if (!data && !loading && !error) {
            this.container.innerHTML = '';
            this.container.style.display = 'none';
            return;
        }

        this.container.style.display = 'block';

        // Loading state
        if (loading) {
            this.container.innerHTML = this._renderLoading();
            return;
        }

        // Error state
        if (error) {
            this.container.innerHTML = this._renderError(error);
            return;
        }

        // Render strategy summary
        if (data) {
            this.container.innerHTML = this._renderStrategy(data, expanded);
            this._attachEventListeners();
        }
    }

    /**
     * Render loading state
     * @private
     */
    _renderLoading() {
        return `
            <div class="strategy-summary-card animate-pulse">
                <div class="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
                <div class="h-4 bg-gray-700 rounded w-full mb-2"></div>
                <div class="h-4 bg-gray-700 rounded w-5/6"></div>
            </div>
        `;
    }

    /**
     * Render error state
     * @private
     */
    _renderError(error) {
        return `
            <div class="strategy-summary-card border-red-500">
                <div class="flex items-center gap-2 text-red-400">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>${error}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render strategy summary
     * @private
     */
    _renderStrategy(data, expanded) {
        const dateRange = this._formatDateRange(data.start_date, data.end_date);

        return `
            <div class="strategy-summary-card">
                <!-- Header -->
                <div class="strategy-summary-header" onclick="strategySummary.toggle()">
                    <div class="flex items-center justify-between w-full cursor-pointer">
                        <div class="flex items-center gap-3">
                            <div class="strategy-icon">
                                <i class="fas fa-lightbulb"></i>
                            </div>
                            <div>
                                <h3 class="strategy-title">AI Campaign Strategy</h3>
                                <p class="strategy-subtitle">${dateRange} • ${data.event_count} events</p>
                            </div>
                        </div>
                        <div class="strategy-toggle ${expanded ? 'expanded' : ''}">
                            <i class="fas fa-chevron-down"></i>
                        </div>
                    </div>
                </div>

                <!-- Content (Collapsible) -->
                <div class="strategy-summary-content ${expanded ? 'expanded' : ''}">
                    <!-- Key Insights -->
                    <div class="strategy-section">
                        <h4 class="strategy-section-title">
                            <i class="fas fa-star text-yellow-400"></i>
                            Key Insights
                        </h4>
                        <ul class="strategy-list">
                            ${data.key_insights.map(insight => `
                                <li class="strategy-list-item">
                                    <i class="fas fa-check-circle text-green-400"></i>
                                    <span>${insight}</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>

                    <!-- Targeting Approach -->
                    <div class="strategy-section">
                        <h4 class="strategy-section-title">
                            <i class="fas fa-bullseye text-blue-400"></i>
                            Targeting Approach
                        </h4>
                        <p class="strategy-text">${data.targeting_approach}</p>
                    </div>

                    <!-- Timing Strategy -->
                    <div class="strategy-section">
                        <h4 class="strategy-section-title">
                            <i class="fas fa-clock text-purple-400"></i>
                            Timing Strategy
                        </h4>
                        <p class="strategy-text">${data.timing_strategy}</p>
                    </div>

                    <!-- Content Strategy -->
                    <div class="strategy-section">
                        <h4 class="strategy-section-title">
                            <i class="fas fa-pen-fancy text-pink-400"></i>
                            Content Strategy
                        </h4>
                        <p class="strategy-text">${data.content_strategy}</p>
                    </div>

                    <!-- Footer -->
                    <div class="strategy-footer">
                        <div class="flex items-center gap-2 text-xs text-gray-400">
                            <i class="fas fa-robot"></i>
                            <span>Generated by ${this._formatModelName(data.generated_by)}</span>
                        </div>
                        <div class="text-xs text-gray-500">
                            ${this._formatTimestamp(data.created_at)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners after rendering
     * @private
     */
    _attachEventListeners() {
        // Event listeners are handled via onclick in template
        // Additional dynamic listeners can be added here if needed
    }

    /**
     * Format date range
     * @private
     */
    _formatDateRange(startDate, endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const options = { month: 'short', day: 'numeric', year: 'numeric' };

        return `${start.toLocaleDateString('en-US', options)} - ${end.toLocaleDateString('en-US', options)}`;
    }

    /**
     * Format AI model name
     * @private
     */
    _formatModelName(modelId) {
        const modelNames = {
            'claude-sonnet-4-5-20250929': 'Claude Sonnet 4.5',
            'claude-3-5-sonnet-20241022': 'Claude 3.5 Sonnet',
            'gpt-4': 'GPT-4'
        };

        return modelNames[modelId] || 'AI Assistant';
    }

    /**
     * Format timestamp
     * @private
     */
    _formatTimestamp(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 60) {
            return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        }

        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        }

        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    }

    /**
     * Destroy the component
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Create global instance for easy access
window.StrategySummaryComponent = StrategySummaryComponent;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StrategySummaryComponent;
}
