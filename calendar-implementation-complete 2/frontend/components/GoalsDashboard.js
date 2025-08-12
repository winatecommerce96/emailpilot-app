// Goals Dashboard Component - Shows revenue goals and progress
const { useState, useEffect } = React;

function GoalsDashboard({ clientId, goals, campaigns = {}, currentDate = new Date() }) {
    const [currentMonthGoal, setCurrentMonthGoal] = useState(null);
    const [estimatedRevenue, setEstimatedRevenue] = useState(0);
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        if (!goals.length || !clientId) return;

        // Find goal for current viewing month
        const monthGoal = goals.find(g => 
            g.year === currentDate.getFullYear() && 
            g.month === currentDate.getMonth() + 1
        );

        setCurrentMonthGoal(monthGoal);

        // Calculate estimated revenue from current month campaigns
        const currentMonthCampaigns = getCampaignsForMonth(campaigns, currentDate.getFullYear(), currentDate.getMonth());
        const estimated = calculateEstimatedRevenue(currentMonthCampaigns);
        setEstimatedRevenue(estimated);

        // Calculate progress
        if (monthGoal && monthGoal.revenue_goal) {
            const progressPercent = (estimated / monthGoal.revenue_goal) * 100;
            setProgress(progressPercent);
        } else {
            setProgress(0);
        }
    }, [goals, campaigns, currentDate, clientId]);

    // Helper functions
    const getCampaignsForMonth = (campaigns, year, month) => {
        const monthCampaigns = {};
        const startDate = new Date(year, month, 1);
        const endDate = new Date(year, month + 1, 0);
        
        Object.entries(campaigns).forEach(([id, campaign]) => {
            const campaignDate = new Date(campaign.date);
            if (campaignDate >= startDate && campaignDate <= endDate) {
                monthCampaigns[id] = campaign;
            }
        });
        
        return monthCampaigns;
    };

    const detectCampaignType = (title, content) => {
        const text = `${title} ${content}`.toLowerCase();
        
        if (text.includes('rrb') || text.includes('promotion')) return 'RRB Promotion';
        if (text.includes('cheese club')) return 'Cheese Club';
        if (text.includes('nurturing') || text.includes('education')) return 'Nurturing/Education';
        if (text.includes('community') || text.includes('lifestyle')) return 'Community/Lifestyle';
        if (text.includes('re-engagement')) return 'Re-engagement';
        if (text.includes('sms')) return 'SMS Alert';
        
        return 'default';
    };

    const calculateEstimatedRevenue = (campaigns) => {
        let totalEstimated = 0;
        const baseRevenuePerCampaign = 500;
        const REVENUE_MULTIPLIERS = {
            'RRB Promotion': 1.5,
            'Cheese Club': 2.0,
            'Nurturing/Education': 0.8,
            'Community/Lifestyle': 0.7,
            'Re-engagement': 1.2,
            'SMS Alert': 1.3,
            'default': 1.0
        };
        
        Object.values(campaigns).forEach(campaign => {
            const campaignType = detectCampaignType(campaign.title || '', campaign.content || '');
            const multiplier = REVENUE_MULTIPLIERS[campaignType] || REVENUE_MULTIPLIERS.default;
            totalEstimated += baseRevenuePerCampaign * multiplier;
        });
        
        return totalEstimated;
    };

    if (!goals.length) {
        return null;
    }

    return (
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Revenue Goals & Progress</h2>
            
            {currentMonthGoal ? (
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <div className="flex justify-between items-start mb-3">
                        <div>
                            <h3 className="font-semibold text-gray-900">
                                {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })} Goal
                            </h3>
                            <p className="text-sm text-gray-600 mt-1">
                                Target: ${currentMonthGoal.revenue_goal?.toLocaleString() || '0'} | 
                                Estimated: ${estimatedRevenue.toLocaleString()}
                            </p>
                        </div>
                        <div className="text-right">
                            <span className={`text-2xl font-bold ${
                                progress >= 100 ? 'text-green-600' : 
                                progress >= 75 ? 'text-yellow-600' : 
                                'text-red-600'
                            }`}>
                                {Math.round(progress)}%
                            </span>
                        </div>
                    </div>
                    <div className="goal-progress-bar mb-3">
                        <div 
                            className="goal-progress-fill" 
                            style={{width: `${Math.min(progress, 100)}%`}}
                        ></div>
                    </div>
                    <div className="text-sm text-gray-600">
                        <p>Campaigns scheduled: {Object.keys(getCampaignsForMonth(campaigns, currentDate.getFullYear(), currentDate.getMonth())).length}</p>
                        {progress < 75 && (
                            <p className="text-orange-600 font-medium mt-1">⚠️ Consider adding more high-value campaigns</p>
                        )}
                        {progress >= 100 && (
                            <p className="text-green-600 font-medium mt-1">✅ On track to meet goal!</p>
                        )}
                    </div>
                </div>
            ) : (
                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <p className="text-gray-500">No goal set for {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}</p>
                </div>
            )}

            {/* Recent Goals */}
            <div>
                <h4 className="font-medium text-gray-700 mb-2">Recent Goals</h4>
                <div className="space-y-2">
                    {goals.slice(0, 3).map(goal => {
                        const monthName = new Date(goal.year, (goal.month || 1) - 1).toLocaleString('default', { 
                            month: 'short', 
                            year: 'numeric' 
                        });
                        return (
                            <div key={goal.id} className="flex justify-between items-center py-2 border-b border-gray-200">
                                <span className="text-sm text-gray-600">{monthName}</span>
                                <span className="text-sm font-medium">${(goal.revenue_goal || 0).toLocaleString()}</span>
                            </div>
                        );
                    })}
                </div>
            </div>

            <style jsx>{`
                .goal-progress-bar {
                    height: 8px;
                    background-color: #e5e7eb;
                    border-radius: 4px;
                    overflow: hidden;
                }
                .goal-progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #3b82f6, #10b981);
                    transition: width 0.5s ease;
                }
            `}</style>
        </div>
    );
}

// Make available globally
window.GoalsDashboard = GoalsDashboard;