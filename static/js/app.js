document.addEventListener('DOMContentLoaded', function() {
    initializeFlashMessages();
});

function initializeFlashMessages() {
    const alerts = document.querySelectorAll('.flash-messages .alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

// Expose the emergency alert handler globally for templates that call it
if (typeof window !== 'undefined') {
    window.showEmergencyAlert = showEmergencyAlert;
}

function showEmergencyAlert(alert) {
    const modal = document.getElementById('emergencyAlertModal');
    if (!modal) return;
    
    // Store alert ID on modal for potential use
    modal.dataset.currentAlertId = alert.id || '';
    
    // Update modal content with alert details
    const titleEl = document.getElementById('alertModalTitle');
    const patientEl = document.getElementById('alertPatientName');
    const locationEl = document.getElementById('alertLocation');
    const messageEl = document.getElementById('alertMessage');
    const timerEl = document.getElementById('countdownTimer');
    
    if (titleEl) titleEl.textContent = alert.severity === 'critical' ? 'CRITICAL ALERT' : 'Emergency Alert';
    if (patientEl) patientEl.textContent = alert.patient_name || 'Unknown Patient';
    if (locationEl) locationEl.textContent = `Room ${alert.room || '-'}, Bed ${alert.bed || '-'}`;
    if (messageEl) messageEl.textContent = alert.message || 'Patient requires immediate attention';
    if (timerEl) timerEl.textContent = '60';
    
    // Initialize and show the modal
    const bsModal = new bootstrap.Modal(modal, { backdrop: 'static', keyboard: false });
    bsModal.show();
    
    // Initialize countdown
    let countdown = 60;
    const countdownInterval = setInterval(() => {
        countdown = Math.max(0, countdown - 1);
        if (timerEl) timerEl.textContent = countdown;
        if (countdown <= 0) {
            clearInterval(countdownInterval);
            try { bsModal.hide(); } catch (e) {}
        }
    }, 1000);
    
    // Wire acknowledge button
    const ackBtn = document.getElementById('acknowledgeAlertBtn');
    if (ackBtn) {
        ackBtn.onclick = function(e) {
            e.preventDefault();
            clearInterval(countdownInterval);
            if (alert.id) {
                acknowledgeAlert(alert.id).then(() => {
                    try { bsModal.hide(); } catch (e) {}
                }).catch(() => {
                    try { bsModal.hide(); } catch (e) {}
                });
            } else {
                try { bsModal.hide(); } catch (e) {}
            }
        };
    }
    
    // Clean up interval when modal closes
    const modalCloseHandler = function() {
        clearInterval(countdownInterval);
        modal.removeEventListener('hidden.bs.modal', modalCloseHandler);
    };
    modal.addEventListener('hidden.bs.modal', modalCloseHandler);
    
    // Play alert sound
    playAlertSound();
}

function playAlertSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 880;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
        
        setTimeout(() => {
            const osc2 = audioContext.createOscillator();
            const gain2 = audioContext.createGain();
            osc2.connect(gain2);
            gain2.connect(audioContext.destination);
            osc2.frequency.value = 880;
            osc2.type = 'sine';
            gain2.gain.setValueAtTime(0.3, audioContext.currentTime);
            gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            osc2.start(audioContext.currentTime);
            osc2.stop(audioContext.currentTime + 0.5);
        }, 200);
    } catch (e) {
        console.log('Audio not supported');
    }
}

function acknowledgeAlert(alertId) {
    // Attempt AJAX POST acknowledgement. If it fails, fall back to form submit.
    return new Promise((resolve, reject) => {
        fetch(`/alert/${alertId}/acknowledge`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).then(resp => {
            if (resp.ok) {
                // update any alert item in the UI
                const el = document.querySelector(`.alert-item[data-alert-id="${alertId}"]`);
                if (el) {
                    el.classList.add('acknowledged');
                    // remove or mark acknowledged visually
                    el.style.opacity = '0.6';
                }
                resolve(true);
            } else {
                // fallback to form submit
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/alert/${alertId}/acknowledge`;
                document.body.appendChild(form);
                form.submit();
                resolve(false);
            }
        }).catch(err => {
            // network error, fallback to form
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/alert/${alertId}/acknowledge`;
            document.body.appendChild(form);
            form.submit();
            reject(err);
        });
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('alertContainer') || document.body;
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.role = 'alert';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
    }, 5000);
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}

function updateVitalDisplay(patientId, vitals) {
    const card = document.querySelector(`[data-patient-id="${patientId}"]`);
    if (!card) return;
    
    const heartRate = card.querySelector('[data-vital="heart_rate"]');
    const bp = card.querySelector('[data-vital="bp"]');
    const oxygen = card.querySelector('[data-vital="oxygen"]');
    const temperature = card.querySelector('[data-vital="temperature"]');
    const timestamp = card.querySelector('[data-vital="timestamp"]');
    
    if (heartRate) {
        heartRate.textContent = Math.round(vitals.heart_rate) || '--';
        updateVitalClass(heartRate.closest('.vital-item'), vitals.heart_rate, 50, 130, 60, 100);
    }
    
    if (bp && vitals.bp_systolic && vitals.bp_diastolic) {
        bp.textContent = `${Math.round(vitals.bp_systolic)}/${Math.round(vitals.bp_diastolic)}`;
        updateVitalClass(bp.closest('.vital-item'), vitals.bp_systolic, 90, 160, 100, 140);
    }
    
    if (oxygen) {
        oxygen.textContent = Math.round(vitals.oxygen) || '--';
        updateVitalClass(oxygen.closest('.vital-item'), vitals.oxygen, 90, 100, 95, 100, true);
    }
    
    if (temperature) {
        temperature.textContent = vitals.temperature ? vitals.temperature.toFixed(1) : '--';
        updateVitalClass(temperature.closest('.vital-item'), vitals.temperature, 96, 102, 97, 100);
    }
    
    if (timestamp) {
        timestamp.textContent = formatTime(vitals.recorded_at);
    }
    
    card.classList.remove('patient-normal', 'patient-warning', 'patient-critical');
    card.classList.add(`patient-${vitals.vital_status || 'normal'}`);
}

function updateVitalClass(element, value, critLow, critHigh, warnLow, warnHigh, invertLogic = false) {
    if (!element || value === null || value === undefined) return;
    
    element.classList.remove('vital-normal', 'vital-warning', 'vital-critical');
    
    if (invertLogic) {
        if (value < critLow) {
            element.classList.add('vital-critical');
        } else if (value < warnLow) {
            element.classList.add('vital-warning');
        } else {
            element.classList.add('vital-normal');
        }
    } else {
        if (value < critLow || value > critHigh) {
            element.classList.add('vital-critical');
        } else if (value < warnLow || value > warnHigh) {
            element.classList.add('vital-warning');
        } else {
            element.classList.add('vital-normal');
        }
    }
}
