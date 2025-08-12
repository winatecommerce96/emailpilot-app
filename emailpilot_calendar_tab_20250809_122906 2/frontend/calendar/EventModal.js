// Event Modal Component for creating and editing calendar events
const { useState, useEffect } = React;

function EventModal({ 
    isOpen, 
    onClose, 
    event = null, 
    onSave, 
    onDelete, 
    onDuplicate,
    initialDate = null 
}) {
    const [formData, setFormData] = useState({
        title: '',
        event_date: '',
        event_type: '',
        content: '',
        segment: '',
        send_time: '',
        subject_a: '',
        subject_b: '',
        preview_text: '',
        main_cta: '',
        offer: '',
        ab_test: ''
    });
    
    const [mode, setMode] = useState('view'); // 'view', 'edit', 'create'
    const [loading, setLoading] = useState(false);

    // Initialize form data when modal opens
    useEffect(() => {
        if (isOpen) {
            if (event) {
                // Editing existing event
                setFormData({
                    title: event.title || '',
                    event_date: event.event_date || '',
                    event_type: event.event_type || '',
                    content: event.content || '',
                    segment: event.segment || '',
                    send_time: event.send_time || '',
                    subject_a: event.subject_a || '',
                    subject_b: event.subject_b || '',
                    preview_text: event.preview_text || '',
                    main_cta: event.main_cta || '',
                    offer: event.offer || '',
                    ab_test: event.ab_test || ''
                });
                setMode('view');
            } else {
                // Creating new event
                setFormData({
                    title: '',
                    event_date: initialDate || new Date().toISOString().split('T')[0],
                    event_type: '',
                    content: '<strong>Segment:</strong> <br><strong>Send Time:</strong> <br><strong>Subject A:</strong> <br><strong>Subject B:</strong> <br><strong>Preview Text:</strong> <br><strong>Main CTA:</strong> <br><strong>Offer:</strong> <br><strong>A/B Test:</strong> ',
                    segment: '',
                    send_time: '',
                    subject_a: '',
                    subject_b: '',
                    preview_text: '',
                    main_cta: '',
                    offer: '',
                    ab_test: ''
                });
                setMode('create');
            }
        }
    }, [isOpen, event, initialDate]);

    // Handle form input changes
    const handleInputChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
    };

    // Handle save
    const handleSave = async () => {
        if (!formData.title.trim()) {
            alert('Please enter a campaign title');
            return;
        }

        setLoading(true);
        try {
            const saveData = {
                ...formData,
                id: event?.id
            };
            
            const success = await onSave(saveData);
            if (success) {
                onClose();
            } else {
                alert('Failed to save event');
            }
        } catch (error) {
            alert('Error saving event: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    // Handle delete
    const handleDelete = async () => {
        if (!event?.id) return;
        
        if (confirm('Are you sure you want to delete this event?')) {
            setLoading(true);
            try {
                const success = await onDelete(event.id);
                if (success) {
                    onClose();
                } else {
                    alert('Failed to delete event');
                }
            } catch (error) {
                alert('Error deleting event: ' + error.message);
            } finally {
                setLoading(false);
            }
        }
    };

    // Handle duplicate
    const handleDuplicate = async () => {
        if (!event?.id) return;
        
        setLoading(true);
        try {
            const success = await onDuplicate(event.id);
            if (success) {
                onClose();
            } else {
                alert('Failed to duplicate event');
            }
        } catch (error) {
            alert('Error duplicating event: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
                {/* Modal Header */}
                <div className="flex justify-between items-center p-6 border-b">
                    <h2 className="text-xl font-bold text-gray-900">
                        {mode === 'create' ? 'Create New Campaign' : 
                         mode === 'edit' ? 'Edit Campaign' : formData.title}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* Modal Content */}
                <div className="max-h-[calc(90vh-140px)] overflow-y-auto">
                    {mode === 'view' ? (
                        <ViewMode 
                            event={event}
                            formData={formData}
                            onEdit={() => setMode('edit')}
                            onDuplicate={handleDuplicate}
                            loading={loading}
                        />
                    ) : (
                        <EditMode
                            formData={formData}
                            onChange={handleInputChange}
                            onSave={handleSave}
                            onCancel={() => {
                                if (mode === 'create') {
                                    onClose();
                                } else {
                                    setMode('view');
                                }
                            }}
                            onDelete={event ? handleDelete : null}
                            loading={loading}
                            isCreating={mode === 'create'}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}

// View Mode Component
function ViewMode({ event, formData, onEdit, onDuplicate, loading }) {
    const formatContent = (content) => {
        if (!content) return '';
        return content.replace(/<br>/g, '\n').replace(/<strong>(.*?)<\/strong>/g, '$1');
    };

    return (
        <div className="p-6">
            <div className="space-y-4 mb-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Campaign Type
                    </label>
                    <div className="text-sm text-gray-600">
                        {formData.event_type || 'Not specified'}
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Date
                    </label>
                    <div className="text-sm text-gray-600">
                        {new Date(formData.event_date).toLocaleDateString()}
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Campaign Details
                    </label>
                    <div className="text-sm text-gray-600 whitespace-pre-line bg-gray-50 p-3 rounded">
                        {formatContent(formData.content)}
                    </div>
                </div>

                {formData.segment && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Segment
                        </label>
                        <div className="text-sm text-gray-600">{formData.segment}</div>
                    </div>
                )}

                {formData.send_time && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Send Time
                        </label>
                        <div className="text-sm text-gray-600">{formData.send_time}</div>
                    </div>
                )}
            </div>

            <div className="flex justify-end space-x-3">
                <button
                    onClick={onDuplicate}
                    disabled={loading}
                    className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                >
                    {loading ? 'Processing...' : 'Duplicate'}
                </button>
                <button
                    onClick={onEdit}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                    Edit
                </button>
            </div>
        </div>
    );
}

// Edit Mode Component
function EditMode({ 
    formData, 
    onChange, 
    onSave, 
    onCancel, 
    onDelete, 
    loading, 
    isCreating 
}) {
    const eventTypes = [
        'RRB Promotion',
        'Cheese Club',
        'Nurturing/Education',
        'Community/Lifestyle',
        'Re-engagement',
        'SMS Alert'
    ];

    return (
        <div className="p-6">
            <div className="space-y-4 mb-6">
                {/* Title */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Campaign Title *
                    </label>
                    <input
                        type="text"
                        value={formData.title}
                        onChange={(e) => onChange('title', e.target.value)}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Enter campaign title"
                        required
                    />
                </div>

                {/* Date */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Campaign Date *
                    </label>
                    <input
                        type="date"
                        value={formData.event_date}
                        onChange={(e) => onChange('event_date', e.target.value)}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        required
                    />
                </div>

                {/* Event Type */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Campaign Type
                    </label>
                    <select
                        value={formData.event_type}
                        onChange={(e) => onChange('event_type', e.target.value)}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">Select campaign type...</option>
                        {eventTypes.map(type => (
                            <option key={type} value={type}>{type}</option>
                        ))}
                    </select>
                </div>

                {/* Campaign Details */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Campaign Details
                    </label>
                    <textarea
                        value={formData.content.replace(/<br>/g, '\n').replace(/<strong>(.*?)<\/strong>/g, '$1')}
                        onChange={(e) => onChange('content', e.target.value.replace(/\n/g, '<br>'))}
                        rows="8"
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Enter campaign details..."
                    />
                </div>

                {/* Additional Fields Row 1 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Segment
                        </label>
                        <input
                            type="text"
                            value={formData.segment}
                            onChange={(e) => onChange('segment', e.target.value)}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="Target segment"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Send Time
                        </label>
                        <input
                            type="text"
                            value={formData.send_time}
                            onChange={(e) => onChange('send_time', e.target.value)}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="e.g., 10:00 AM PST"
                        />
                    </div>
                </div>

                {/* Subject Lines */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Subject Line A
                        </label>
                        <input
                            type="text"
                            value={formData.subject_a}
                            onChange={(e) => onChange('subject_a', e.target.value)}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="First subject line option"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Subject Line B
                        </label>
                        <input
                            type="text"
                            value={formData.subject_b}
                            onChange={(e) => onChange('subject_b', e.target.value)}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="Second subject line option"
                        />
                    </div>
                </div>

                {/* Additional Fields Row 2 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Main CTA
                        </label>
                        <input
                            type="text"
                            value={formData.main_cta}
                            onChange={(e) => onChange('main_cta', e.target.value)}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="Call to action text"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            A/B Test
                        </label>
                        <input
                            type="text"
                            value={formData.ab_test}
                            onChange={(e) => onChange('ab_test', e.target.value)}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="A/B test details"
                        />
                    </div>
                </div>

                {/* Preview Text */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Preview Text
                    </label>
                    <textarea
                        value={formData.preview_text}
                        onChange={(e) => onChange('preview_text', e.target.value)}
                        rows="2"
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Email preview text"
                    />
                </div>

                {/* Offer */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Offer
                    </label>
                    <textarea
                        value={formData.offer}
                        onChange={(e) => onChange('offer', e.target.value)}
                        rows="2"
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Special offer or promotion details"
                    />
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-between">
                {onDelete && (
                    <button
                        onClick={onDelete}
                        disabled={loading}
                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                    >
                        {loading ? 'Processing...' : 'Delete'}
                    </button>
                )}
                
                <div className="flex justify-end space-x-3 ml-auto">
                    <button
                        onClick={onCancel}
                        disabled={loading}
                        className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onSave}
                        disabled={loading || !formData.title.trim()}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                    >
                        {loading ? 'Saving...' : 'Save'}
                    </button>
                </div>
            </div>
        </div>
    );
}