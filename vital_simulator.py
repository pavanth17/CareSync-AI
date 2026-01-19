import random
import logging
from datetime import datetime
from app import app, db
from models import Patient, VitalSign, Alert, StaffMember
from synthetic_data import generate_vital_sign, check_vital_thresholds, create_alert
from alert_router import alert_router, distribute_alerts_to_staff

logging.basicConfig(level=logging.DEBUG)

new_alerts = []
alert_paths = {}

def update_patient_vitals():
    global new_alerts
    
    with app.app_context():
        try:
            patients = Patient.query.filter(Patient.status.in_(['admitted', 'icu', 'emergency'])).all()
            
            if not patients:
                logging.info("No active patients to update vitals for")
                return
            
            patients_to_update = random.sample(patients, min(len(patients), max(3, len(patients) // 2)))
            
            for patient in patients_to_update:
                status_bias = None
                if patient.status == 'icu':
                    status_bias = random.choices(['critical', 'warning', None], weights=[20, 30, 50])[0]
                elif patient.status == 'emergency':
                    status_bias = random.choices(['critical', 'warning', None], weights=[30, 40, 30])[0]
                else:
                    status_bias = random.choices(['critical', 'warning', None], weights=[5, 10, 85])[0]
                
                vital = generate_vital_sign(patient, status_bias)
                db.session.add(vital)
                db.session.commit()
                
                alert_data = check_vital_thresholds(vital)
                for alert in alert_data:
                    alert_obj = Alert(
                        patient_id=patient.id,
                        vital_sign_id=vital.id,
                        alert_type=alert['type'],
                        severity=alert['severity'],
                        title=alert['title'],
                        message=alert['message']
                    )
                    db.session.add(alert_obj)
                    db.session.commit()
                    
                    recipients = distribute_alerts_to_staff(
                        patient.id,
                        alert['severity'],
                        alert_obj.id
                    )
                    
                    routing_path = []
                    if recipients:
                        routing_path = [staff.staff_id for staff in recipients]
                    
                    for staff in recipients:
                        new_alerts.append({
                            'staff_id': staff.id,
                            'staff_name': staff.full_name,
                            'patient_id': patient.id,
                            'patient_name': patient.full_name,
                            'room': patient.room_number,
                            'bed': patient.bed_number,
                            'type': alert['type'],
                            'severity': alert['severity'],
                            'title': alert['title'],
                            'message': alert['message'],
                            'routing_path': routing_path,
                            'timestamp': datetime.now().isoformat()
                        })
                    
            logging.info(f"Updated vitals for {len(patients_to_update)} patients")
            
        except Exception as e:
            logging.error(f"Error updating vitals: {e}")
            db.session.rollback()


def get_and_clear_new_alerts():
    global new_alerts
    alerts = new_alerts.copy()
    new_alerts = []
    return alerts


def get_live_patient_vitals():
    with app.app_context():
        patients = Patient.query.filter(Patient.status.in_(['admitted', 'icu', 'emergency'])).all()
        
        vitals_data = []
        for patient in patients:
            latest_vital = patient.latest_vitals
            if latest_vital:
                vitals_data.append({
                    'patient_id': patient.id,
                    'patient_name': patient.full_name,
                    'room': patient.room_number,
                    'bed': patient.bed_number,
                    'status': patient.status,
                    'vital_status': latest_vital.status,
                    'heart_rate': latest_vital.heart_rate,
                    'bp_systolic': latest_vital.blood_pressure_systolic,
                    'bp_diastolic': latest_vital.blood_pressure_diastolic,
                    'oxygen': latest_vital.oxygen_saturation,
                    'temperature': latest_vital.temperature,
                    'respiratory_rate': latest_vital.respiratory_rate,
                    'recorded_at': latest_vital.recorded_at.isoformat()
                })
        
        return vitals_data
