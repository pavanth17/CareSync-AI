document.addEventListener('DOMContentLoaded', function() {
    // Only connect if realtime updates are enabled (set in dashboard_base.html)
    if (typeof enableRealTimeUpdates !== 'undefined' && enableRealTimeUpdates) {
        console.log('Initializing Real-Time Socket.IO connection...');
        
        const socket = io();

        socket.on('connect', function() {
            console.log('Socket.IO Connected!');
        });

        socket.on('vital_update', function(data) {
            console.log('Vital Update:', data);
            updatePatientCard(data);
        });

        socket.on('new_alert', function(data) {
            console.log('New Alert:', data);
            handleNewAlert(data);
        });
    }
});

function updatePatientCard(data) {
    // Find the patient card
    const card = document.querySelector(`.patient-card[data-patient-id="${data.patient_id}"]`);
    if (!card) return;

    // Update Vitals
    updateVitalValue(card, 'heart_rate', data.heart_rate);
    updateVitalValue(card, 'bp', `${data.bp_systolic}/${data.bp_diastolic}`);
    updateVitalValue(card, 'oxygen', data.oxygen);
    updateVitalValue(card, 'temperature', data.temperature);
    
    // Update Timestamp
    const timestampElem = card.querySelector('[data-vital="timestamp"]');
    if (timestampElem) timestampElem.textContent = data.timestamp;

    // Update Status Color
    card.classList.remove('patient-normal', 'patient-warning', 'patient-critical');
    card.classList.add(`patient-${data.status}`);
}

function updateVitalValue(card, type, value) {
    const elem = card.querySelector(`[data-vital="${type}"]`);
    if (elem) {
        // Add a highlight animation
        elem.classList.add('vital-update-flash');
        elem.textContent = value || '--';
        setTimeout(() => elem.classList.remove('vital-update-flash'), 1000);
    }
}

function handleNewAlert(data) {
    // Check if user is admin - specific request to disable alerts for admins
    if (typeof staffRole !== 'undefined' && staffRole === 'admin') {
        console.log('Suppressing alert for admin role');
        return;
    }

    // Play sound
    if (typeof playAlertSound === 'function') {
        playAlertSound();
    }

    // Show popup
    if (typeof showEmergencyAlert === 'function') {
        showEmergencyAlert({
            id: data.id,
            patient_name: data.patient_name,
            room: data.room,
            bed: data.bed,
            message: data.message,
            severity: data.severity
        });
    }
}

// Add CSS for update flash
const style = document.createElement('style');
style.textContent = `
    @keyframes flashHighlight {
        0% { background-color: rgba(255, 255, 0, 0.5); }
        100% { background-color: transparent; }
    }
    .vital-update-flash {
        animation: flashHighlight 1s ease-out;
        border-radius: 4px;
    }
`;
document.head.appendChild(style);
