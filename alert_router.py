import logging
import os
import json
import urllib.request
from datetime import datetime
from app import app, db
from models import Patient, StaffMember, Alert

logging.basicConfig(level=logging.DEBUG)


class AlertRouter:
    def __init__(self):
        self.routes = []
        self.load_distribution = {}
        
    def get_on_duty_doctors(self):
        """Get all on-duty doctors"""
        return StaffMember.query.filter(
            StaffMember.is_on_duty == True,
            StaffMember.is_active == True,
            StaffMember.role == 'doctor'
        ).all()
    
    def get_on_duty_nurses(self):
        """Get all on-duty nurses"""
        return StaffMember.query.filter(
            StaffMember.is_on_duty == True,
            StaffMember.is_active == True,
            StaffMember.role == 'nurse'
        ).all()
    
    def route_by_department(self, patient, alert_severity):
        """Route to staff in patient's department"""
        staff_list = StaffMember.query.filter(
            StaffMember.is_on_duty == True,
            StaffMember.is_active == True,
            StaffMember.department == patient.assigned_doctor.department if patient.assigned_doctor else None,
            StaffMember.role.in_(['doctor', 'nurse'])
        ).all()
        return staff_list if staff_list else self.route_by_availability()
    
    def route_by_availability(self):
        """Route to all available on-duty staff (broadcast)"""
        doctors = self.get_on_duty_doctors()
        nurses = self.get_on_duty_nurses()
        return doctors + nurses
    
    def route_by_specialty(self, patient, alert_severity):
        """Route to doctors with relevant specialization"""
        if not patient.diagnosis:
            return self.route_by_availability()
        
        relevant_roles = []
        diagnosis_lower = patient.diagnosis.lower()
        
        specialty_map = {
            'heart': 'Cardiology',
            'cardiac': 'Cardiology',
            'infarction': 'Cardiology',
            'neuro': 'Neurology',
            'stroke': 'Neurology',
            'brain': 'Neurology',
            'kidney': 'Nephrology',
            'renal': 'Nephrology',
            'cancer': 'Oncology',
            'tumor': 'Oncology',
            'fracture': 'Orthopedics',
            'bone': 'Orthopedics',
        }
        
        for keyword, spec in specialty_map.items():
            if keyword in diagnosis_lower:
                relevant_roles = StaffMember.query.filter(
                    StaffMember.is_on_duty == True,
                    StaffMember.is_active == True,
                    StaffMember.role == 'doctor',
                    StaffMember.specialization == spec
                ).all()
                if relevant_roles:
                    return relevant_roles
        
        return self.route_by_availability()
    
    def route_by_load_balance(self):
        """Route to least loaded on-duty staff"""
        staff = self.route_by_availability()
        if not staff:
            return []
        
        alert_counts = {}
        for member in staff:
            count = Alert.query.filter(
                Alert.acknowledged_by_id == member.id,
                Alert.is_acknowledged == False
            ).count()
            alert_counts[member.id] = count
        
        sorted_staff = sorted(staff, key=lambda x: alert_counts.get(x.id, 0))
        return sorted_staff[:max(1, len(sorted_staff) // 2)]
    
    def route_critical_alert(self, patient, alert_severity):
        """Route critical alerts to all available staff"""
        if alert_severity == 'critical':
            return self.route_by_availability()
        else:
            return self.route_by_load_balance()
    
    def route_warning_alert(self, patient, alert_severity):
        """Route warning alerts by specialty or load"""
        return self.route_by_specialty(patient, alert_severity)
    
    def get_routing_paths(self, patient, alert_severity):
        """Get multiple routing paths for an alert"""
        paths = {
            'primary': self.route_by_specialty(patient, alert_severity),
            'secondary': self.route_by_load_balance(),
            'broadcast': self.route_by_availability(),
            'critical': self.route_critical_alert(patient, alert_severity)
        }
        
        if alert_severity == 'critical':
            return paths['broadcast']
        elif alert_severity == 'warning':
            return paths['secondary'] or paths['broadcast']
        else:
            return paths['primary'] or paths['secondary'] or paths['broadcast']
    
    def distribute_alert(self, patient_id, alert_id, alert_severity):
        """Distribute alert to assigned doctor and nurses only when on-duty"""
        patient = Patient.query.get(patient_id)
        alert = Alert.query.get(alert_id)
        
        if not patient or not alert:
            return []
        
        recipients = []
        
        if patient.assigned_doctor_id and patient.assigned_doctor.is_on_duty and patient.assigned_doctor.is_active:
            recipients.append(patient.assigned_doctor)
        
        if patient.assigned_nurse_id and patient.assigned_nurse.is_on_duty and patient.assigned_nurse.is_active:
            recipients.append(patient.assigned_nurse)
        
        on_duty_nurses = StaffMember.query.filter(
            StaffMember.is_on_duty == True,
            StaffMember.is_active == True,
            StaffMember.role == 'nurse',
            StaffMember.id != patient.assigned_nurse_id
        ).all()
        
        for nurse in on_duty_nurses[:2]:
            if nurse not in recipients:
                recipients.append(nurse)
        
        logging.info(f"Alert {alert_id} routed to {len(recipients)} assigned staff members")
        return recipients


alert_router = AlertRouter()


def distribute_alerts_to_staff(patient_id, alert_severity, alert_id):
    """Distribute alert to multiple staff members via different paths"""
    try:
        recipients = alert_router.distribute_alert(patient_id, alert_severity, alert_id)
        logging.info(f"Distributed alert {alert_id} to {len(recipients)} recipients")
        return recipients
    except Exception as e:
        logging.error(f"Error distributing alerts: {e}")
        return []


def send_to_n8n_webhook(alert):
    """If `N8N_WEBHOOK_URL` is set in env, POST the alert payload to it.
    Uses stdlib to avoid adding new dependencies.
    """
    url = os.environ.get('N8N_WEBHOOK_URL')
    if not url:
        return False

    payload = {
        'alert_id': alert.id,
        'patient_id': alert.patient_id,
        'title': alert.title,
        'message': alert.message,
        'severity': alert.severity,
        'created_at': alert.created_at.isoformat() if getattr(alert, 'created_at', None) else None
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5) as resp:
            logging.info(f"Posted alert {alert.id} to n8n webhook, status {resp.status}")
        return True
    except Exception as e:
        logging.error(f"Failed to post to n8n webhook: {e}")
        return False
