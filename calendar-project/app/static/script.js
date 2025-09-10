/**
 * EmailPilot Campaign Calendar - Frontend JavaScript
 * Refactored to work with FastAPI backend instead of Firebase/Google APIs
 */

// --- UTILITY FUNCTIONS ---
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// --- STATE MANAGEMENT ---
let currentDate = new Date(2025, 8, 1);
let campaignData = {};
let originalCampaignDataAfterImport = null;
let draggedEventId = null;
let clients = [];
let currentClientId = null;
let undoStack = [];
let chatHistory = [];
let currentGoals = [];

// --- CAMPAIGN TYPE REVENUE MULTIPLIERS ---
const REVENUE_MULTIPLIERS = {
    'RRB Promotion': 1.5,
    'Cheese Club': 2.0,
    'Nurturing/Education': 0.8,
    'Community/Lifestyle': 0.7,
    'Re-engagement': 1.2,
    'SMS Alert': 1.3,
    'default': 1.0
};

// --- DOM ELEMENTS ---
const modal = document.getElementById('modal');
const modalTransformContainer = document.getElementById('modal-transform-container');
const modalContentArea = document.getElementById('modal-content-area');
const confirmationModal = document.getElementById('confirmation-modal');
const calendarGrid = document.getElementById('calendar-grid');
const calendarTitle = document.getElementById('calendar-title');
const prevMonthBtn = document.getElementById('prev-month-btn');
const nextMonthBtn = document.getElementById('next-month-btn');
const importPlanBtn = document.getElementById('import-plan-btn');
const importBtnText = document.getElementById('import-btn-text');
const importLoader = document.getElementById('import-loader');
const saveChangesBtn = document.getElementById('save-changes-btn');
const undoBtn = document.getElementById('undo-btn');
const commitCalendarBtn = document.getElementById('commit-calendar-btn');
const importLogSection = document.getElementById('import-log-section');
const importLogContent = document.getElementById('import-log-content');
const commitLogSection = document.getElementById('commit-log-section');
const commitLogContent = document.getElementById('commit-log-content');
const clientSelector = document.getElementById('client-selector');
const addClientBtn = document.getElementById('add-client-btn');
const deleteClientBtn = document.getElementById('delete-client-btn');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send-btn');
const goalsDashboard = document.getElementById('goals-dashboard');
const goalsContent = document.getElementById('goals-content');

// --- API HELPER FUNCTIONS ---
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Request failed:', error);
        throw error;
    }
}

// --- CORE FUNCTIONS ---
function log(message, type = 'import') {
    console.log(message);
    const logSection = type === 'commit' ? commitLogSection : importLogSection;
    const logContent = type === 'commit' ? commitLogContent : importLogContent;
    if (logSection.classList.contains('hidden')) {
        logSection.classList.remove('hidden');
    }
    logContent.textContent += `\n${new Date().toLocaleTimeString()} - ${message}`;
    logContent.scrollTop = logContent.scrollHeight;
}

function pushToUndoStack() {
    undoStack.push(JSON.parse(JSON.stringify(campaignData)));
    if (undoStack.length > 20) undoStack.shift();
    undoBtn.disabled = false;
}

// --- CLIENT MANAGEMENT FUNCTIONS ---
async function loadClients() {
    try {
        log('Fetching client list from backend...');
        const response = await apiRequest('/api/clients');
        clients = response.clients || [];
        
        if (clients.length > 0) {
            log(`Successfully fetched ${clients.length} clients.`);
            updateClientSelector();
            await loadClientData(clients[0].id);
        } else {
            log('No clients found. Please add one.');
            generateCalendar();
        }
    } catch (error) {
        log(`Error loading clients: ${error.message}`);
        clients = [];
        updateClientSelector();
    }
}

async function addClient(clientName) {
    try {
        const response = await apiRequest('/api/clients', {
            method: 'POST',
            body: JSON.stringify({ name: clientName })
        });
        
        const newClient = response.client;
        clients.push(newClient);
        updateClientSelector();
        clientSelector.value = newClient.id;
        await loadClientData(newClient.id);
        log(`Added new client: ${newClient.name}`);
        
        return newClient;
    } catch (error) {
        log(`Error adding client: ${error.message}`);
        throw error;
    }
}

async function deleteClient(clientId) {
    try {
        await apiRequest(`/api/clients/${clientId}`, {
            method: 'DELETE'
        });
        
        const deletedClient = clients.find(c => c.id === clientId);
        clients = clients.filter(c => c.id !== clientId);
        campaignData = {};
        originalCampaignDataAfterImport = null;
        currentClientId = null;
        updateClientSelector();
        
        log(`Deleted client: ${deletedClient?.name}`);
        
        // Load first remaining client or disable buttons
        if (clients.length > 0) {
            clientSelector.value = clients[0].id;
            await loadClientData(clients[0].id);
        } else {
            saveChangesBtn.disabled = true;
            importPlanBtn.disabled = true;
        }
    } catch (error) {
        log(`Error deleting client: ${error.message}`);
        throw error;
    }
}

async function loadClientData(clientId) {
    if (currentClientId === clientId) return;
    
    currentClientId = clientId;
    undoStack = [];
    chatHistory = [];
    chatMessages.innerHTML = '';
    undoBtn.disabled = true;
    saveChangesBtn.disabled = false;
    importPlanBtn.disabled = false;
    
    try {
        const response = await apiRequest(`/api/clients/${clientId}/campaigns`);
        campaignData = response.campaignData || {};
        originalCampaignDataAfterImport = response.originalCampaignDataAfterImport || null;
        
        const clientName = clients.find(c => c.id === clientId)?.name;
        log(`Loaded data for client: ${clientName}`);
        
        generateCalendar();
        await loadClientGoals(clientId);
    } catch (error) {
        console.error('Load error:', error);
        log(`Error loading client data: ${error.message}`);
        campaignData = {};
        originalCampaignDataAfterImport = null;
        saveChangesBtn.disabled = true;
        generateCalendar();
    }
}

async function saveClientData() {
    if (!currentClientId) return;
    
    const originalText = saveChangesBtn.textContent;
    saveChangesBtn.textContent = 'Saving...';
    saveChangesBtn.disabled = true;

    try {
        const clientName = clients.find(c => c.id === currentClientId)?.name;
        await apiRequest(`/api/clients/${currentClientId}/campaigns`, {
            method: 'POST',
            body: JSON.stringify({
                campaignData: campaignData,
                originalCampaignDataAfterImport: originalCampaignDataAfterImport
            })
        });
        
        log(`Saved changes for client: ${clientName}`);
        saveChangesBtn.textContent = 'Saved!';
        renderGoals(); // Update goals display after save
    } catch (error) {
        console.error('Save error:', error);
        log(`Error saving client data: ${error.message}`);
        saveChangesBtn.textContent = 'Save Failed';
    } finally {
        setTimeout(() => {
            saveChangesBtn.textContent = originalText;
            saveChangesBtn.disabled = false;
        }, 2000);
    }
}

const autoSaveClientData = debounce(saveClientData, 2000);

// --- GOALS FUNCTIONS ---
async function loadClientGoals(clientId) {
    try {
        // Goals would be loaded via FastAPI endpoint
        const response = await apiRequest(`/api/clients/${clientId}/goals`);
        currentGoals = response.goals || [];
        
        if (currentGoals.length > 0) {
            goalsDashboard.classList.remove('hidden');
            renderGoals();
        } else {
            goalsDashboard.classList.add('hidden');
        }
        
        log(`Loaded ${currentGoals.length} goals for client`);
    } catch (error) {
        console.error('Error loading goals:', error);
        log(`Error loading goals: ${error.message}`);
        currentGoals = [];
        goalsDashboard.classList.add('hidden');
    }
}

function calculateEstimatedRevenue(events) {
    let totalEstimated = 0;
    const baseRevenuePerCampaign = 500; // Base estimate
    
    Object.values(events).forEach(event => {
        const campaignType = detectCampaignType(event.title, event.content);
        const multiplier = REVENUE_MULTIPLIERS[campaignType] || REVENUE_MULTIPLIERS.default;
        totalEstimated += baseRevenuePerCampaign * multiplier;
    });
    
    return totalEstimated;
}

function detectCampaignType(title, content) {
    const text = `${title} ${content}`.toLowerCase();
    
    if (text.includes('rrb') || text.includes('promotion')) return 'RRB Promotion';
    if (text.includes('cheese club')) return 'Cheese Club';
    if (text.includes('nurturing') || text.includes('education')) return 'Nurturing/Education';
    if (text.includes('community') || text.includes('lifestyle')) return 'Community/Lifestyle';
    if (text.includes('re-engagement')) return 'Re-engagement';
    if (text.includes('sms')) return 'SMS Alert';
    
    return 'default';
}

function getEventsForMonth(year, month) {
    const monthEvents = {};
    Object.keys(campaignData).forEach(eventId => {
        const event = campaignData[eventId];
        const eventDate = new Date(event.date);
        if (eventDate.getFullYear() === year && eventDate.getMonth() === month) {
            monthEvents[eventId] = event;
        }
    });
    return monthEvents;
}

function renderGoals() {
    if (currentGoals.length === 0) {
        goalsContent.innerHTML = '<p class="text-gray-500">No goals set for this client</p>';
        return;
    }
    
    // Get current month's campaigns
    const currentMonthEvents = getEventsForMonth(currentDate.getFullYear(), currentDate.getMonth());
    const estimatedRevenue = calculateEstimatedRevenue(currentMonthEvents);
    
    // Find goal for current viewing month
    const currentMonthGoal = currentGoals.find(g => 
        g.year === currentDate.getFullYear() && 
        g.month === currentDate.getMonth() + 1
    );
    
    let goalsHTML = '';
    
    if (currentMonthGoal) {
        const targetRevenue = currentMonthGoal.revenue_goal || 0;
        const progress = targetRevenue > 0 ? (estimatedRevenue / targetRevenue) * 100 : 0;
        
        goalsHTML += `
            <div class="bg-gray-50 rounded-lg p-4">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="font-semibold text-gray-900">
                            ${currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })} Goal
                        </h3>
                        <p class="text-sm text-gray-600 mt-1">
                            Target: $${targetRevenue.toLocaleString()} | 
                            Estimated: $${estimatedRevenue.toLocaleString()}
                        </p>
                    </div>
                    <div class="text-right">
                        <span class="text-2xl font-bold ${progress >= 100 ? 'text-green-600' : progress >= 75 ? 'text-yellow-600' : 'text-red-600'}">
                            ${Math.round(progress)}%
                        </span>
                    </div>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: ${Math.min(progress, 100)}%"></div>
                </div>
            </div>
        `;
    }
    
    goalsContent.innerHTML = goalsHTML || '<p class="text-gray-500">No goals for current month</p>';
}

// --- CALENDAR FUNCTIONS ---
function generateCalendar() {
    const fragment = document.createDocumentFragment();
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    calendarTitle.textContent = `${currentDate.toLocaleString('default', { month: 'long' })} ${year}`;

    const firstDay = new Date(year, month, 1);
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const startDayOfWeek = firstDay.getDay();
    const prevDays = new Date(year, month, 0).getDate();
    
    // Previous month days
    for (let i = startDayOfWeek; i > 0; i--) {
        fragment.appendChild(createDayElement(prevDays - i + 1, new Date(year, month - 1, prevDays - i + 1), true));
    }
    
    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
        fragment.appendChild(createDayElement(day, new Date(year, month, day)));
    }
    
    // Next month days
    const nextDays = 42 - (startDayOfWeek + daysInMonth);
    for (let day = 1; day <= nextDays; day++) {
        fragment.appendChild(createDayElement(day, new Date(year, month + 1, day), true));
    }
    
    calendarGrid.innerHTML = '';
    calendarGrid.appendChild(fragment);
    
    renderAllEvents();
    renderGoals(); // Update goals when calendar changes
}

function createDayElement(dayNumber, date, isOtherMonth = false) {
    const dayEl = document.createElement('div');
    const dateString = date.toISOString().split('T')[0];
    dayEl.className = `day ${isOtherMonth ? 'text-gray-400 bg-gray-50' : ''}`;
    dayEl.dataset.date = dateString;

    const dayNumberEl = document.createElement('div');
    dayNumberEl.className = 'day-number';
    dayNumberEl.textContent = dayNumber;
    dayEl.appendChild(dayNumberEl);

    const addBtn = document.createElement('button');
    addBtn.className = 'add-event-btn text-gray-400 hover:text-indigo-600';
    addBtn.innerHTML = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd"></path></svg>';
    addBtn.addEventListener('click', () => { renderModalContent(null, dateString); openModal(); });
    dayEl.appendChild(addBtn);

    // Drag and drop event handlers
    dayEl.addEventListener('dragover', e => e.preventDefault());
    dayEl.addEventListener('drop', e => {
        e.preventDefault();
        if (draggedEventId) {
            pushToUndoStack();
            const dayEl = e.currentTarget;
            const draggedEl = document.getElementById(draggedEventId);
            dayEl.appendChild(draggedEl);
            campaignData[draggedEventId].date = dayEl.dataset.date;
            draggedEventId = null;
            autoSaveClientData();
        }
    });
    
    return dayEl;
}

function renderAllEvents() {
    const existingEvents = document.querySelectorAll('.event');
    existingEvents.forEach(el => el.remove());
    
    const fragment = document.createDocumentFragment();
    const eventsByDate = {};
    
    Object.keys(campaignData).forEach(eventId => {
        const event = campaignData[eventId];
        if (!eventsByDate[event.date]) {
            eventsByDate[event.date] = [];
        }
        eventsByDate[event.date].push({ id: eventId, data: event });
    });
    
    Object.keys(eventsByDate).forEach(date => {
        const dayEl = document.querySelector(`.day[data-date="${date}"]`);
        if (dayEl) {
            const dayFragment = document.createDocumentFragment();
            eventsByDate[date].forEach(({ id, data }) => {
                dayFragment.appendChild(createEventElement(id, data));
            });
            dayEl.appendChild(dayFragment);
        }
    });
}

function createEventElement(eventId, eventData) {
    const eventEl = document.createElement('div');
    eventEl.id = eventId;
    eventEl.className = `event ${eventData.color || 'bg-gray-200 text-gray-800'}`;
    eventEl.draggable = true;
    eventEl.textContent = eventData.title;
    addEventListenersToEvent(eventEl);
    return eventEl;
}

function addEventListenersToEvent(eventEl) {
    eventEl.addEventListener('click', (e) => { 
        e.stopPropagation(); 
        renderModalContent(eventEl.id); 
        openModal(); 
    });
    eventEl.addEventListener('dragstart', (e) => { 
        draggedEventId = e.target.id; 
        setTimeout(() => e.target.classList.add('dragging'), 0); 
    });
    eventEl.addEventListener('dragend', (e) => e.target.classList.remove('dragging'));
}

function saveEvent(eventId, date) {
    pushToUndoStack();
    const newTitle = document.getElementById('edit-title').value;
    const newContent = document.getElementById('edit-content').value.replace(/\n/g, '<br>');
    const campaignType = detectCampaignType(newTitle, newContent);
    const colorMap = {
        'RRB Promotion': 'bg-red-300 text-red-800',
        'Cheese Club': 'bg-green-200 text-green-800',
        'Nurturing/Education': 'bg-blue-200 text-blue-800',
        'Community/Lifestyle': 'bg-purple-200 text-purple-800',
        'Re-engagement': 'bg-yellow-200 text-yellow-800',
        'SMS Alert': 'bg-orange-300 text-orange-800',
        'default': 'bg-gray-200 text-gray-800'
    };
    
    if (eventId) {
        campaignData[eventId].title = newTitle;
        campaignData[eventId].content = newContent;
        campaignData[eventId].color = colorMap[campaignType] || colorMap.default;
    } else {
        const newId = 'event-' + Date.now();
        campaignData[newId] = { 
            date, 
            title: newTitle, 
            content: newContent,
            color: colorMap[campaignType] || colorMap.default
        };
    }
    
    generateCalendar();
    autoSaveClientData();
    closeModal();
}

function deleteEvent(eventId) {
    pushToUndoStack();
    delete campaignData[eventId];
    generateCalendar();
    autoSaveClientData();
    closeModal();
}

// --- AI CHAT FUNCTIONS ---
async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addChatMessage('user', message);
    chatInput.value = '';
    chatSendBtn.disabled = true;
    
    try {
        const response = await apiRequest('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                client_id: currentClientId,
                campaign_data: campaignData,
                goals: currentGoals,
                chat_history: chatHistory
            })
        });
        
        const aiResponse = response.response;
        addChatMessage('assistant', aiResponse);
        
        // Handle AI actions if present
        if (response.action) {
            await handleAiAction(response.action);
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage('assistant', 'Sorry, I encountered an error processing your request.');
        log(`Chat error: ${error.message}`);
    } finally {
        chatSendBtn.disabled = false;
    }
}

function addChatMessage(role, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `chat-bubble ${role === 'user' ? 'bg-blue-600 text-white ml-auto' : 'bg-gray-200 text-gray-800'}`;
    messageEl.textContent = content;
    chatMessages.appendChild(messageEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Update chat history
    chatHistory.push({ role, content });
    if (chatHistory.length > 20) chatHistory.shift(); // Keep last 20 messages
}

async function handleAiAction(action) {
    try {
        switch (action.type) {
            case 'create':
                if (action.event) {
                    pushToUndoStack();
                    const newId = 'event-' + Date.now();
                    campaignData[newId] = action.event;
                    generateCalendar();
                    autoSaveClientData();
                    log(`AI created campaign: ${action.event.title}`);
                }
                break;
                
            case 'update':
                if (action.eventId && campaignData[action.eventId]) {
                    pushToUndoStack();
                    Object.assign(campaignData[action.eventId], action.updates);
                    generateCalendar();
                    autoSaveClientData();
                    log(`AI updated campaign: ${action.eventId}`);
                }
                break;
                
            case 'delete':
                if (action.eventId && campaignData[action.eventId]) {
                    pushToUndoStack();
                    delete campaignData[action.eventId];
                    generateCalendar();
                    autoSaveClientData();
                    log(`AI deleted campaign: ${action.eventId}`);
                }
                break;
        }
    } catch (error) {
        console.error('Error handling AI action:', error);
        log(`Error handling AI action: ${error.message}`);
    }
}

// --- DOCUMENT IMPORT FUNCTIONS ---
async function importDocument() {
    const docUrl = prompt('Enter Google Doc URL or ID:');
    if (!docUrl) return;
    
    resetImportButton();
    setImportButtonLoading(true);
    
    try {
        log('Starting document import...');
        
        const response = await apiRequest('/api/import-doc', {
            method: 'POST',
            body: JSON.stringify({
                doc_url: docUrl,
                client_id: currentClientId
            })
        });
        
        if (response.campaigns && response.campaigns.length > 0) {
            originalCampaignDataAfterImport = JSON.parse(JSON.stringify(campaignData));
            
            // Apply imported campaigns to calendar
            response.campaigns.forEach(campaign => {
                const eventId = 'event-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                campaignData[eventId] = campaign;
            });
            
            generateCalendar();
            autoSaveClientData();
            log(`Successfully imported ${response.campaigns.length} campaigns`);
        } else {
            log('No campaigns found in document');
        }
        
    } catch (error) {
        console.error('Import error:', error);
        log(`Import error: ${error.message}`);
    } finally {
        setImportButtonLoading(false);
    }
}

async function commitToSheet() {
    if (!currentClientId) {
        log('Please select a client first');
        return;
    }
    
    try {
        log('Committing calendar to sheet...', 'commit');
        
        const response = await apiRequest('/api/commit-sheet', {
            method: 'POST',
            body: JSON.stringify({
                client_id: currentClientId,
                campaign_data: campaignData
            })
        });
        
        log(`Successfully committed calendar to sheet: ${response.sheet_url}`, 'commit');
        
    } catch (error) {
        console.error('Commit error:', error);
        log(`Commit error: ${error.message}`, 'commit');
    }
}

// --- UI HELPER FUNCTIONS ---
function updateClientSelector() {
    clientSelector.innerHTML = '';
    
    if (clients.length === 0) {
        const option = document.createElement('option');
        option.textContent = 'No clients available';
        option.disabled = true;
        clientSelector.appendChild(option);
        return;
    }
    
    clients.forEach(client => {
        const option = document.createElement('option');
        option.value = client.id;
        option.textContent = client.name;
        if (client.id === currentClientId) {
            option.selected = true;
        }
        clientSelector.appendChild(option);
    });
}

function setImportButtonLoading(isLoading) {
    if (isLoading) {
        importBtnText.textContent = 'Importing...';
        importLoader.classList.remove('hidden');
        importPlanBtn.disabled = true;
    } else {
        importBtnText.textContent = 'Import Plan';
        importLoader.classList.add('hidden');
        importPlanBtn.disabled = false;
    }
}

function resetImportButton() {
    setImportButtonLoading(false);
}

function openModal() {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.style.overflow = 'auto';
}

function renderModalContent(eventId, date) {
    const event = eventId ? campaignData[eventId] : null;
    const isEdit = !!eventId;
    
    modalContentArea.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div class="px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-medium text-gray-900">
                    ${isEdit ? 'Edit Campaign' : 'New Campaign'}
                </h3>
            </div>
            <div class="px-6 py-4">
                <div class="space-y-4">
                    <div>
                        <label for="edit-title" class="block text-sm font-medium text-gray-700">Title</label>
                        <input type="text" id="edit-title" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm" 
                               value="${event?.title || ''}" placeholder="Campaign title">
                    </div>
                    <div>
                        <label for="edit-content" class="block text-sm font-medium text-gray-700">Content</label>
                        <textarea id="edit-content" rows="4" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm" 
                                  placeholder="Campaign details, segments, send time, etc.">${event?.content?.replace(/<br>/g, '\n') || ''}</textarea>
                    </div>
                    <div class="text-sm text-gray-500">
                        Date: ${event?.date || date}
                    </div>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
                ${isEdit ? '<button onclick="deleteEvent(\'' + eventId + '\')" class="px-4 py-2 text-sm text-red-600 hover:text-red-800">Delete</button>' : ''}
                <button onclick="closeModal()" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
                <button onclick="saveEvent(${isEdit ? '\'' + eventId + '\'' : 'null'}, '${event?.date || date}')" 
                        class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
                    ${isEdit ? 'Update' : 'Create'}
                </button>
            </div>
        </div>
    `;
}

function showPromptModal(promptText, callback) {
    const userInput = prompt(promptText);
    if (userInput && userInput.trim()) {
        callback(userInput.trim());
    }
}

function showConfirmationModal(message, callback) {
    const confirmed = confirm(message);
    if (confirmed) {
        callback();
    }
}

// --- EVENT LISTENERS ---
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize the application
    try {
        await loadClients();
        log('Application initialized successfully');
    } catch (error) {
        log(`Initialization error: ${error.message}`);
    }
});

// Navigation buttons
prevMonthBtn?.addEventListener('click', () => {
    currentDate.setMonth(currentDate.getMonth() - 1);
    generateCalendar();
});

nextMonthBtn?.addEventListener('click', () => {
    currentDate.setMonth(currentDate.getMonth() + 1);
    generateCalendar();
});

// Client management
clientSelector?.addEventListener('change', (e) => {
    if (e.target.value && e.target.value !== currentClientId) {
        loadClientData(e.target.value);
    }
});

addClientBtn?.addEventListener('click', () => {
    showPromptModal("Enter the new client's name:", async (clientName) => {
        try {
            await addClient(clientName);
        } catch (error) {
            alert('Failed to add client. Please try again.');
        }
    });
});

deleteClientBtn?.addEventListener('click', () => {
    if (!currentClientId) {
        alert('Please select a client to delete.');
        return;
    }
    
    const currentClient = clients.find(c => c.id === currentClientId);
    if (!currentClient) {
        alert('Selected client not found.');
        return;
    }
    
    showConfirmationModal(
        `Are you sure you want to delete the client "${currentClient.name}" and all their campaigns?`,
        () => deleteClient(currentClientId)
    );
});

// Campaign management
saveChangesBtn?.addEventListener('click', saveClientData);

undoBtn?.addEventListener('click', () => {
    if (undoStack.length > 0) {
        campaignData = undoStack.pop();
        generateCalendar();
        autoSaveClientData();
        if (undoStack.length === 0) {
            undoBtn.disabled = true;
        }
    }
});

// Import and export
importPlanBtn?.addEventListener('click', importDocument);
commitCalendarBtn?.addEventListener('click', commitToSheet);

// Chat functionality
chatSendBtn?.addEventListener('click', sendChatMessage);
chatInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
});

// Modal close on background click
modal?.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

// Prevent form submission on enter key in modal inputs
document.addEventListener('keypress', (e) => {
    if (e.target.tagName === 'INPUT' && e.key === 'Enter') {
        e.preventDefault();
    }
});