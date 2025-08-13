// Plan Campaign Dialog Component for AI-generated campaign planning
const { useState, useEffect } = React;

function PlanCampaignDialog({ 
    isOpen, 
    onClose, 
    clientId,
    clientName,
    onEventsGenerated = () => {}
}) {
    const [formData, setFormData] = useState({
        campaignType: '',
        startDate: '',
        endDate: '',
        promotionDetails: ''
    });
    
    const [loading, setLoading] = useState(false);
    const [generatedPlan, setGeneratedPlan] = useState(null);
    const [showPreview, setShowPreview] = useState(false);
    const [errors, setErrors] = useState({});

    // Campaign type options
    const campaignTypes = [
        'New Product Launch',
        'Limited Time Offer',
        'Flash Sale',
        'Seasonal Campaign',
        'Re-engagement Campaign',
        'Welcome Series',
        'Nurturing/Education',
        'Community/Lifestyle',
        'Other'
    ];

    // Reset form when dialog opens/closes
    useEffect(() => {
        if (isOpen) {
            setFormData({
                campaignType: '',
                startDate: '',
                endDate: '',
                promotionDetails: ''
            });
            setGeneratedPlan(null);
            setShowPreview(false);
            setErrors({});
        }
    }, [isOpen]);

    // Handle form input changes
    const handleInputChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
        
        // Clear error when user starts typing
        if (errors[field]) {
            setErrors(prev => ({
                ...prev,
                [field]: null
            }));
        }
    };

    // Validate form
    const validateForm = () => {
        const newErrors = {};
        
        if (!formData.campaignType) {
            newErrors.campaignType = 'Campaign type is required';
        }
        
        if (!formData.startDate) {
            newErrors.startDate = 'Start date is required';
        }
        
        if (!formData.endDate) {
            newErrors.endDate = 'End date is required';
        }
        
        if (formData.startDate && formData.endDate && formData.startDate > formData.endDate) {
            newErrors.endDate = 'End date must be after start date';
        }
        
        if (!formData.promotionDetails.trim()) {
            newErrors.promotionDetails = 'Promotion details are required';
        }
        
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    // Generate campaign plan using AI
    const handleGeneratePlan = async () => {
        if (!validateForm()) return;
        
        setLoading(true);
        try {
            const response = await axios.post(
                `${API_BASE_URL}/api/calendar/plan-campaign`,
                {
                    client_id: clientId,
                    campaign_type: formData.campaignType,
                    start_date: formData.startDate,
                    end_date: formData.endDate,
                    promotion_details: formData.promotionDetails
                },
                { withCredentials: true }
            );
            
            // Transform the response to match our component's expected format
            const transformedPlan = {
                summary: `${response.data.total_events} events planned for your ${formData.campaignType} campaign`,
                strategy: response.data.campaign_plan,
                events: response.data.events_created || [],
                recommendations: [
                    "Review each event and adjust timing as needed",
                    "Customize content for your brand voice",
                    "Set up tracking for campaign performance"
                ]
            };
            
            setGeneratedPlan(transformedPlan);
            setShowPreview(true);
        } catch (error) {
            console.error('Error generating campaign plan:', error);
            alert('Failed to generate campaign plan: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoading(false);
        }
    };

    // Confirm and accept the generated plan
    const handleConfirmPlan = async () => {
        if (!generatedPlan?.events) return;
        
        // The events were already created by the /plan-campaign endpoint
        // Just notify parent to refresh calendar and close dialog
        onEventsGenerated(generatedPlan.events);
        onClose();
        
        alert(`Campaign plan accepted! ${generatedPlan.events.length} events have been added to your calendar.`);
    };

    // Go back to form from preview
    const handleBackToForm = () => {
        setShowPreview(false);
        setGeneratedPlan(null);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
                {/* Modal Header */}
                <div className="flex justify-between items-center p-6 border-b bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
                    <div>
                        <h2 className="text-xl font-bold">
                            {showPreview ? 'Campaign Plan Preview' : 'Plan New Campaign'}
                        </h2>
                        <p className="text-indigo-100 text-sm mt-1">
                            {clientName ? `for ${clientName}` : 'AI-Generated Campaign Planning'}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-white hover:text-indigo-200 text-2xl"
                        disabled={loading}
                    >
                        ×
                    </button>
                </div>

                {/* Modal Content */}
                <div className="max-h-[calc(90vh-140px)] overflow-y-auto">
                    {showPreview ? (
                        <PlanPreview 
                            plan={generatedPlan}
                            onConfirm={handleConfirmPlan}
                            onBack={handleBackToForm}
                            loading={loading}
                        />
                    ) : (
                        <PlanForm 
                            formData={formData}
                            errors={errors}
                            campaignTypes={campaignTypes}
                            onChange={handleInputChange}
                            onGenerate={handleGeneratePlan}
                            onCancel={onClose}
                            loading={loading}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}

// Plan Form Component
function PlanForm({ 
    formData, 
    errors, 
    campaignTypes, 
    onChange, 
    onGenerate, 
    onCancel, 
    loading 
}) {
    return (
        <div className="p-6">
            <div className="space-y-6">
                {/* Campaign Type */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Campaign Type *
                    </label>
                    <select
                        value={formData.campaignType}
                        onChange={(e) => onChange('campaignType', e.target.value)}
                        className={`w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                            errors.campaignType ? 'border-red-500' : 'border-gray-300'
                        }`}
                    >
                        <option value="">Select campaign type...</option>
                        {campaignTypes.map(type => (
                            <option key={type} value={type}>{type}</option>
                        ))}
                    </select>
                    {errors.campaignType && (
                        <p className="text-red-500 text-sm mt-1">{errors.campaignType}</p>
                    )}
                </div>

                {/* Date Range */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Start Date *
                        </label>
                        <input
                            type="date"
                            value={formData.startDate}
                            onChange={(e) => onChange('startDate', e.target.value)}
                            min={new Date().toISOString().split('T')[0]}
                            className={`w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                                errors.startDate ? 'border-red-500' : 'border-gray-300'
                            }`}
                        />
                        {errors.startDate && (
                            <p className="text-red-500 text-sm mt-1">{errors.startDate}</p>
                        )}
                    </div>
                    
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            End Date *
                        </label>
                        <input
                            type="date"
                            value={formData.endDate}
                            onChange={(e) => onChange('endDate', e.target.value)}
                            min={formData.startDate || new Date().toISOString().split('T')[0]}
                            className={`w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                                errors.endDate ? 'border-red-500' : 'border-gray-300'
                            }`}
                        />
                        {errors.endDate && (
                            <p className="text-red-500 text-sm mt-1">{errors.endDate}</p>
                        )}
                    </div>
                </div>

                {/* Promotion Details */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Promotion Details *
                    </label>
                    <textarea
                        value={formData.promotionDetails}
                        onChange={(e) => onChange('promotionDetails', e.target.value)}
                        rows="6"
                        className={`w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                            errors.promotionDetails ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="Describe your promotion in detail:&#10;• Product or service being promoted&#10;• Target audience&#10;• Key benefits or offers&#10;• Special pricing or discounts&#10;• Any specific requirements or constraints"
                    />
                    {errors.promotionDetails && (
                        <p className="text-red-500 text-sm mt-1">{errors.promotionDetails}</p>
                    )}
                    <p className="text-gray-500 text-sm mt-1">
                        The more details you provide, the better the AI can plan your campaign.
                    </p>
                </div>

                {/* Info Box */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex">
                        <div className="text-blue-600 mr-3">💡</div>
                        <div>
                            <h4 className="text-blue-800 font-medium mb-1">AI Campaign Planning</h4>
                            <p className="text-blue-700 text-sm">
                                Our AI will analyze your inputs and generate a comprehensive campaign plan 
                                including email sequences, timing recommendations, subject lines, and content suggestions.
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3 mt-8 pt-6 border-t">
                <button
                    onClick={onCancel}
                    disabled={loading}
                    className="px-6 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 disabled:opacity-50 transition-colors"
                >
                    Cancel
                </button>
                <button
                    onClick={onGenerate}
                    disabled={loading}
                    className="px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 transition-colors flex items-center"
                >
                    {loading ? (
                        <>
                            <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Generating Plan...
                        </>
                    ) : (
                        <>
                            <span className="mr-2">🤖</span>
                            Generate Campaign Plan
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}

// Plan Preview Component
function PlanPreview({ plan, onConfirm, onBack, loading }) {
    if (!plan) return null;

    return (
        <div className="p-6">
            {/* Plan Summary */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                <h3 className="text-green-800 font-medium mb-2">✅ Campaign Plan Generated</h3>
                <p className="text-green-700 text-sm">{plan.summary}</p>
            </div>

            {/* Campaign Strategy */}
            {plan.strategy && (
                <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">Campaign Strategy</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-gray-700 whitespace-pre-line">{plan.strategy}</p>
                    </div>
                </div>
            )}

            {/* Generated Events */}
            {plan.events && plan.events.length > 0 && (
                <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">
                        Planned Events ({plan.events.length})
                    </h3>
                    <div className="space-y-3">
                        {plan.events.map((event, index) => (
                            <EventPreviewCard key={index} event={event} index={index} />
                        ))}
                    </div>
                </div>
            )}

            {/* Recommendations */}
            {plan.recommendations && plan.recommendations.length > 0 && (
                <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">Recommendations</h3>
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                        <ul className="space-y-2">
                            {plan.recommendations.map((rec, index) => (
                                <li key={index} className="flex items-start">
                                    <span className="text-amber-600 mr-2">📌</span>
                                    <span className="text-amber-800 text-sm">{rec}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-between pt-6 border-t">
                <button
                    onClick={onBack}
                    disabled={loading}
                    className="px-6 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 disabled:opacity-50 transition-colors"
                >
                    ← Back to Form
                </button>
                
                <div className="flex space-x-3">
                    <button
                        onClick={onConfirm}
                        disabled={loading || !plan.events || plan.events.length === 0}
                        className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors flex items-center"
                    >
                        {loading ? (
                            <>
                                <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                Creating Events...
                            </>
                        ) : (
                            <>
                                <span className="mr-2">✨</span>
                                Create Campaign Events
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}

// Event Preview Card Component
function EventPreviewCard({ event, index }) {
    const getEventTypeColor = (type) => {
        const colors = {
            'email': 'bg-blue-100 text-blue-800',
            'sms': 'bg-purple-100 text-purple-800',
            'social': 'bg-pink-100 text-pink-800',
            'preparation': 'bg-gray-100 text-gray-800',
            'launch': 'bg-green-100 text-green-800',
            'follow-up': 'bg-orange-100 text-orange-800'
        };
        return colors[type?.toLowerCase()] || 'bg-gray-100 text-gray-800';
    };

    return (
        <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                    <div className="flex items-center mb-2">
                        <span className="text-sm font-medium text-gray-500 mr-2">
                            Day {index + 1}
                        </span>
                        {event.event_type && (
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEventTypeColor(event.event_type)}`}>
                                {event.event_type}
                            </span>
                        )}
                    </div>
                    <h4 className="font-medium text-gray-900 mb-1">{event.title}</h4>
                    <p className="text-sm text-gray-600">
                        {new Date(event.date || event.event_date).toLocaleDateString('en-US', { 
                            weekday: 'long', 
                            year: 'numeric', 
                            month: 'long', 
                            day: 'numeric' 
                        })}
                    </p>
                </div>
            </div>
            
            {event.content && (
                <div className="bg-gray-50 rounded p-3 text-sm text-gray-700">
                    <p className="whitespace-pre-line">{event.content}</p>
                </div>
            )}
            
            {/* Additional event details */}
            <div className="mt-3 grid grid-cols-2 gap-4 text-xs text-gray-500">
                {event.segment && (
                    <div>
                        <strong>Segment:</strong> {event.segment}
                    </div>
                )}
                {event.send_time && (
                    <div>
                        <strong>Send Time:</strong> {event.send_time}
                    </div>
                )}
            </div>
        </div>
    );
}

// Make PlanCampaignDialog available globally
window.PlanCampaignDialog = PlanCampaignDialog;