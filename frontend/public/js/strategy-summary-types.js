/**
 * TypeScript-style type definitions for Strategy Summary feature
 * (Using JSDoc for type checking in vanilla JavaScript)
 */

/**
 * @typedef {Object} StrategySummary
 * @property {string} client_id - Client identifier
 * @property {string} start_date - Start date in YYYY-MM-DD format
 * @property {string} end_date - End date in YYYY-MM-DD format
 * @property {string[]} key_insights - Array of 3-5 strategic recommendations
 * @property {string} targeting_approach - Audience segmentation strategy
 * @property {string} timing_strategy - Send time optimization recommendations
 * @property {string} content_strategy - Content themes and messaging direction
 * @property {string} created_at - ISO timestamp
 * @property {string} updated_at - ISO timestamp
 * @property {string} generated_by - AI model identifier
 * @property {number} event_count - Number of events in this calendar period
 */

/**
 * @typedef {Object} StrategySummaryAPI
 * @property {function(string): Promise<StrategySummary|null>} fetch - Fetch strategy summary by client ID
 * @property {function(): boolean} isAvailable - Check if strategy summary exists
 * @property {function(): void} clear - Clear cached strategy summary
 */

/**
 * @typedef {Object} StrategySummaryState
 * @property {StrategySummary|null} data - Current strategy summary data
 * @property {boolean} loading - Loading state
 * @property {Error|null} error - Error state
 * @property {boolean} visible - UI visibility state
 */

// Export for module systems (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        // Types only - no runtime exports
    };
}
