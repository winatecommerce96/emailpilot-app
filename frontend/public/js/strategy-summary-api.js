/**
 * Strategy Summary API Client
 *
 * Handles all API communications for strategy summary feature.
 * Provides caching and error handling.
 */

class StrategySummaryAPI {
    constructor(baseURL = '/api/calendar') {
        this.baseURL = baseURL;
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }

    /**
     * Fetch strategy summary for a client
     * @param {string} clientId - Client identifier
     * @param {Object} options - Fetch options
     * @param {string} [options.startDate] - Optional start date filter (YYYY-MM-DD)
     * @param {string} [options.endDate] - Optional end date filter (YYYY-MM-DD)
     * @param {boolean} [options.useCache=true] - Whether to use cached data
     * @returns {Promise<Object|null>} Strategy summary data or null if not found
     */
    async fetchStrategySummary(clientId, options = {}) {
        const { start_date, end_date, useCache = true } = options;

        // Check cache first
        const cacheKey = this._getCacheKey(clientId, start_date, end_date);
        if (useCache && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                console.log('[StrategyAPI] Using cached strategy summary');
                return cached.data;
            }
        }

        try {
            // Build query parameters
            const params = new URLSearchParams();
            if (start_date) params.append('start_date', start_date);
            if (end_date) params.append('end_date', end_date);

            const queryString = params.toString();
            const url = `${this.baseURL}/strategy-summary/${clientId}${queryString ? '?' + queryString : ''}`;

            console.log('[StrategyAPI] Fetching:', url);

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.status === 404) {
                // No strategy summary found - this is normal for calendars without strategy
                console.log('[StrategyAPI] No strategy summary found for client:', clientId);
                this._setCache(cacheKey, null);
                return null;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('[StrategyAPI] Strategy summary loaded:', data);

            // Cache the result
            this._setCache(cacheKey, data);

            return data;

        } catch (error) {
            console.error('[StrategyAPI] Error fetching strategy summary:', error);

            // Return cached data if available, even if expired
            if (this.cache.has(cacheKey)) {
                console.warn('[StrategyAPI] Using stale cache due to error');
                return this.cache.get(cacheKey).data;
            }

            throw error;
        }
    }

    /**
     * Check if a strategy summary exists for a client
     * @param {string} clientId - Client identifier
     * @returns {Promise<boolean>}
     */
    async hasStrategySummary(clientId) {
        try {
            const summary = await this.fetchStrategySummary(clientId);
            return summary !== null;
        } catch {
            return false;
        }
    }

    /**
     * Clear cache for a specific client or all clients
     * @param {string} [clientId] - Optional client ID to clear specific cache
     */
    clearCache(clientId = null) {
        if (clientId) {
            // Clear all cache entries for this client
            for (const [key, _] of this.cache) {
                if (key.startsWith(`${clientId}:`)) {
                    this.cache.delete(key);
                }
            }
            console.log('[StrategyAPI] Cache cleared for client:', clientId);
        } else {
            this.cache.clear();
            console.log('[StrategyAPI] All cache cleared');
        }
    }

    /**
     * Get cache statistics
     * @returns {Object} Cache stats
     */
    getCacheStats() {
        return {
            size: this.cache.size,
            entries: Array.from(this.cache.keys())
        };
    }

    /**
     * Generate cache key
     * @private
     */
    _getCacheKey(clientId, startDate, endDate) {
        return `${clientId}:${startDate || ''}:${endDate || ''}`;
    }

    /**
     * Set cache entry
     * @private
     */
    _setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }
}

// Create singleton instance
window.strategySummaryAPI = new StrategySummaryAPI();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StrategySummaryAPI;
}
