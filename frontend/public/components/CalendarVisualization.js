// Calendar Visualization Component - Advanced Calendar Display with Multiple Views
// Uses React for component structure and interactivity

const CalendarVisualization = () => {
    const [view, setView] = React.useState('month');
    const [selectedDate, setSelectedDate] = React.useState(new Date());
    const [campaigns, setCampaigns] = React.useState([]);
    const [selectedCampaign, setSelectedCampaign] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [draggedItem, setDraggedItem] = React.useState(null);

    // Campaign type colors
    const campaignColors = {
        promotional: '#a855f7', // purple
        content: '#3b82f6',     // blue
        engagement: '#10b981',  // green
        seasonal: '#f97316',    // orange
        automated: '#ec4899'    // pink
    };

    // Generate calendar days for month view
    const generateMonthDays = () => {
        const year = selectedDate.getFullYear();
        const month = selectedDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - firstDay.getDay());
        
        const days = [];
        const current = new Date(startDate);
        
        while (current <= lastDay || current.getDay() !== 0) {
            days.push(new Date(current));
            current.setDate(current.getDate() + 1);
        }
        
        return days;
    };

    // Get campaigns for a specific day
    const getCampaignsForDay = (date) => {
        return campaigns.filter(campaign => {
            const campaignDate = new Date(campaign.date);
            return campaignDate.toDateString() === date.toDateString();
        });
    };

    // Handle drag and drop
    const handleDragStart = (e, campaign) => {
        setDraggedItem(campaign);
        e.dataTransfer.effectAllowed = 'move';
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDrop = (e, date) => {
        e.preventDefault();
        if (draggedItem) {
            const updatedCampaigns = campaigns.map(c => 
                c.id === draggedItem.id 
                    ? { ...c, date: date.toISOString() }
                    : c
            );
            setCampaigns(updatedCampaigns);
            setDraggedItem(null);
            
            // Show success animation
            showNotification('Campaign moved successfully');
        }
    };

    // Month View Component
    const MonthView = () => {
        const days = generateMonthDays();
        const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        
        return React.createElement('div', { className: 'calendar-month-view' },
            // Week day headers
            React.createElement('div', { className: 'grid grid-cols-7 gap-1 mb-2' },
                weekDays.map(day => 
                    React.createElement('div', {
                        key: day,
                        className: 'text-center text-white/60 text-sm font-semibold p-2'
                    }, day)
                )
            ),
            // Calendar grid
            React.createElement('div', { className: 'grid grid-cols-7 gap-1' },
                days.map((day, index) => {
                    const isCurrentMonth = day.getMonth() === selectedDate.getMonth();
                    const isToday = day.toDateString() === new Date().toDateString();
                    const dayCampaigns = getCampaignsForDay(day);
                    
                    return React.createElement('div', {
                        key: index,
                        className: `calendar-day min-h-[100px] p-2 rounded-lg border ${
                            isCurrentMonth 
                                ? 'border-white/20 bg-white/5' 
                                : 'border-white/10 bg-white/[0.02] opacity-50'
                        } ${isToday ? 'ring-2 ring-blue-400' : ''} 
                        hover:bg-white/10 transition-all cursor-pointer`,
                        onDragOver: handleDragOver,
                        onDrop: (e) => handleDrop(e, day)
                    },
                        React.createElement('div', { className: 'flex justify-between items-start mb-2' },
                            React.createElement('span', {
                                className: `text-sm ${isToday ? 'text-blue-400 font-bold' : 'text-white/60'}`
                            }, day.getDate()),
                            dayCampaigns.length > 0 && 
                            React.createElement('span', {
                                className: 'text-xs bg-white/20 px-1.5 py-0.5 rounded-full text-white/80'
                            }, dayCampaigns.length)
                        ),
                        React.createElement('div', { className: 'space-y-1' },
                            dayCampaigns.slice(0, 3).map(campaign =>
                                React.createElement('div', {
                                    key: campaign.id,
                                    className: 'campaign-chip text-xs p-1 rounded cursor-move hover:scale-105 transition-transform',
                                    style: { backgroundColor: `${campaignColors[campaign.type]}40` },
                                    draggable: true,
                                    onDragStart: (e) => handleDragStart(e, campaign),
                                    onClick: () => setSelectedCampaign(campaign)
                                },
                                    React.createElement('div', { className: 'text-white truncate' }, campaign.name)
                                )
                            ),
                            dayCampaigns.length > 3 &&
                            React.createElement('div', {
                                className: 'text-xs text-white/40 text-center'
                            }, `+${dayCampaigns.length - 3} more`)
                        )
                    );
                })
            )
        );
    };

    // Week View Component
    const WeekView = () => {
        const startOfWeek = new Date(selectedDate);
        startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay());
        
        const weekDays = [];
        for (let i = 0; i < 7; i++) {
            const day = new Date(startOfWeek);
            day.setDate(day.getDate() + i);
            weekDays.push(day);
        }
        
        const hours = Array.from({ length: 24 }, (_, i) => i);
        
        return React.createElement('div', { className: 'calendar-week-view' },
            React.createElement('div', { className: 'grid grid-cols-8 gap-1' },
                // Time column
                React.createElement('div', { className: 'sticky left-0' },
                    React.createElement('div', { className: 'h-12' }), // Header spacer
                    hours.map(hour =>
                        React.createElement('div', {
                            key: hour,
                            className: 'h-16 text-white/40 text-xs p-1'
                        }, `${hour}:00`)
                    )
                ),
                // Day columns
                weekDays.map(day => 
                    React.createElement('div', { key: day.toDateString() },
                        React.createElement('div', {
                            className: 'h-12 text-center text-white/80 font-semibold p-2 border-b border-white/20'
                        },
                            React.createElement('div', null, day.toLocaleDateString('en', { weekday: 'short' })),
                            React.createElement('div', { className: 'text-lg' }, day.getDate())
                        ),
                        hours.map(hour => {
                            const hourCampaigns = getCampaignsForDay(day).filter(c => {
                                const campaignHour = new Date(c.date).getHours();
                                return campaignHour === hour;
                            });
                            
                            return React.createElement('div', {
                                key: `${day}-${hour}`,
                                className: 'h-16 border border-white/10 hover:bg-white/5 p-1',
                                onDragOver: handleDragOver,
                                onDrop: (e) => {
                                    const dropDate = new Date(day);
                                    dropDate.setHours(hour);
                                    handleDrop(e, dropDate);
                                }
                            },
                                hourCampaigns.map(campaign =>
                                    React.createElement('div', {
                                        key: campaign.id,
                                        className: 'text-xs p-1 rounded mb-1',
                                        style: { backgroundColor: `${campaignColors[campaign.type]}60` },
                                        draggable: true,
                                        onDragStart: (e) => handleDragStart(e, campaign)
                                    }, campaign.name)
                                )
                            );
                        })
                    )
                )
            )
        );
    };

    // Timeline View Component
    const TimelineView = () => {
        const sortedCampaigns = [...campaigns].sort((a, b) => 
            new Date(a.date) - new Date(b.date)
        );
        
        return React.createElement('div', { className: 'calendar-timeline-view' },
            React.createElement('div', { className: 'space-y-4' },
                sortedCampaigns.map((campaign, index) => {
                    const date = new Date(campaign.date);
                    const isUpcoming = date > new Date();
                    
                    return React.createElement('div', {
                        key: campaign.id,
                        className: 'timeline-item flex items-start space-x-4',
                        style: { animationDelay: `${index * 0.05}s` }
                    },
                        // Timeline line and dot
                        React.createElement('div', { className: 'flex flex-col items-center' },
                            React.createElement('div', {
                                className: `w-4 h-4 rounded-full ${isUpcoming ? 'bg-blue-400' : 'bg-gray-400'}`
                            }),
                            index < sortedCampaigns.length - 1 &&
                            React.createElement('div', {
                                className: 'w-0.5 h-20 bg-white/20 mt-2'
                            })
                        ),
                        // Campaign card
                        React.createElement('div', {
                            className: 'flex-1 glass-card rounded-lg p-4 hover:scale-[1.02] transition-transform cursor-pointer',
                            onClick: () => setSelectedCampaign(campaign)
                        },
                            React.createElement('div', { className: 'flex justify-between items-start mb-2' },
                                React.createElement('h3', { className: 'text-white font-semibold' }, campaign.name),
                                React.createElement('span', {
                                    className: 'text-xs px-2 py-1 rounded-full',
                                    style: { backgroundColor: `${campaignColors[campaign.type]}40` }
                                }, campaign.type)
                            ),
                            React.createElement('div', { className: 'text-white/60 text-sm mb-2' },
                                date.toLocaleDateString('en', { 
                                    weekday: 'long', 
                                    year: 'numeric', 
                                    month: 'long', 
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                })
                            ),
                            campaign.metrics &&
                            React.createElement('div', { className: 'flex space-x-4 text-xs text-white/50' },
                                React.createElement('span', null, `Open: ${(campaign.metrics.openRate * 100).toFixed(1)}%`),
                                React.createElement('span', null, `Click: ${(campaign.metrics.clickRate * 100).toFixed(1)}%`),
                                React.createElement('span', null, `Revenue: $${campaign.metrics.revenue.toLocaleString()}`)
                            )
                        )
                    );
                })
            )
        );
    };

    // Analytics View Component
    const AnalyticsView = () => {
        const days = generateMonthDays();
        const maxCampaigns = Math.max(...days.map(d => getCampaignsForDay(d).length), 1);
        
        return React.createElement('div', { className: 'calendar-analytics-view' },
            React.createElement('h3', { className: 'text-white text-lg font-semibold mb-4' }, 'Campaign Density Heatmap'),
            React.createElement('div', { className: 'grid grid-cols-7 gap-1' },
                days.map((day, index) => {
                    const dayCampaigns = getCampaignsForDay(day);
                    const intensity = dayCampaigns.length / maxCampaigns;
                    const isCurrentMonth = day.getMonth() === selectedDate.getMonth();
                    
                    return React.createElement('div', {
                        key: index,
                        className: `aspect-square rounded flex items-center justify-center text-white/80 text-sm cursor-pointer hover:ring-2 hover:ring-white/50 transition-all`,
                        style: {
                            backgroundColor: isCurrentMonth 
                                ? `rgba(99, 102, 241, ${intensity * 0.8})`
                                : 'rgba(255, 255, 255, 0.05)',
                            opacity: isCurrentMonth ? 1 : 0.3
                        },
                        title: `${day.toLocaleDateString()}: ${dayCampaigns.length} campaigns`
                    }, day.getDate());
                })
            ),
            React.createElement('div', { className: 'mt-6' },
                React.createElement('h4', { className: 'text-white/80 text-sm mb-2' }, 'Legend'),
                React.createElement('div', { className: 'flex items-center space-x-4' },
                    [0, 0.25, 0.5, 0.75, 1].map(val =>
                        React.createElement('div', {
                            key: val,
                            className: 'flex items-center space-x-1'
                        },
                            React.createElement('div', {
                                className: 'w-6 h-6 rounded',
                                style: { backgroundColor: `rgba(99, 102, 241, ${val * 0.8})` }
                            }),
                            React.createElement('span', { className: 'text-xs text-white/60' }, 
                                val === 0 ? '0' : val === 1 ? 'Max' : `${val * 100}%`
                            )
                        )
                    )
                )
            )
        );
    };

    // Render the appropriate view
    const renderView = () => {
        switch (view) {
            case 'week':
                return React.createElement(WeekView);
            case 'timeline':
                return React.createElement(TimelineView);
            case 'analytics':
                return React.createElement(AnalyticsView);
            default:
                return React.createElement(MonthView);
        }
    };

    // Show notification helper
    const showNotification = (message) => {
        // This would integrate with the toast system in the main app
        console.log('Notification:', message);
    };

    // Main render
    return React.createElement('div', { className: 'calendar-visualization' },
        // View selector
        React.createElement('div', { className: 'flex space-x-2 mb-4' },
            ['month', 'week', 'timeline', 'analytics'].map(v =>
                React.createElement('button', {
                    key: v,
                    className: `px-4 py-2 rounded-lg transition-all ${
                        view === v 
                            ? 'bg-blue-500 text-white' 
                            : 'bg-white/10 text-white/70 hover:bg-white/20'
                    }`,
                    onClick: () => setView(v)
                }, v.charAt(0).toUpperCase() + v.slice(1))
            )
        ),
        
        // Calendar content
        React.createElement('div', { className: 'calendar-content' },
            renderView()
        ),
        
        // Selected campaign details
        selectedCampaign && React.createElement('div', {
            className: 'fixed bottom-4 right-4 glass-card rounded-xl p-4 max-w-sm animate-slide-in'
        },
            React.createElement('div', { className: 'flex justify-between items-start mb-2' },
                React.createElement('h3', { className: 'text-white font-semibold' }, selectedCampaign.name),
                React.createElement('button', {
                    className: 'text-white/60 hover:text-white',
                    onClick: () => setSelectedCampaign(null)
                }, '×')
            ),
            React.createElement('div', { className: 'space-y-2 text-sm text-white/70' },
                React.createElement('div', null, `Type: ${selectedCampaign.type}`),
                React.createElement('div', null, `Date: ${new Date(selectedCampaign.date).toLocaleDateString()}`),
                selectedCampaign.segment && React.createElement('div', null, `Segment: ${selectedCampaign.segment}`),
                selectedCampaign.metrics && React.createElement('div', { className: 'pt-2 border-t border-white/20' },
                    React.createElement('div', null, `Expected Open Rate: ${(selectedCampaign.metrics.openRate * 100).toFixed(1)}%`),
                    React.createElement('div', null, `Expected Revenue: $${selectedCampaign.metrics.revenue.toLocaleString()}`)
                )
            )
        )
    );
};

// Export for use in other components
window.CalendarVisualization = CalendarVisualization;