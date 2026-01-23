"""
Enhanced Appointment Routing System with Intelligent Doctor Allocation
Uses multiple factors to intelligently allocate patients to doctors
"""

from datetime import datetime, timedelta
from database import db
from models import StaffMember, Patient, AppointmentRequest, VitalSign, DoctorNote, Shift
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Language translations for appointment system
TRANSLATIONS = {
    'en': {
        'appointment_types': {
            'consultation': 'General Consultation',
            'follow-up': 'Follow-up Visit',
            'emergency': 'Emergency Appointment',
            'routine': 'Routine Checkup',
            'diagnostic': 'Diagnostic Test'
        },
        'departments': {
            'General': 'General Medicine',
            'Cardiology': 'Cardiology',
            'Neurology': 'Neurology',
            'Surgery': 'General Surgery',
            'ICU': 'Intensive Care Unit',
            'Emergency': 'Emergency Department',
            'Pediatrics': 'Pediatrics',
            'Orthopedics': 'Orthopedics',
            'Psychiatry': 'Psychiatry'
        },
        'urgency_levels': {
            'normal': 'Normal',
            'urgent': 'Urgent',
            'emergency': 'Emergency'
        }
    },
    'hi': {
        'appointment_types': {
            'consultation': 'सामान्य परामर्श',
            'follow-up': 'अनुवर्ती दौरा',
            'emergency': 'आपातकालीन नियुक्ति',
            'routine': 'नियमित जांच',
            'diagnostic': 'नैदानिक परीक्षण'
        },
        'departments': {
            'General': 'सामान्य चिकित्सा',
            'Cardiology': 'कार्डियोलॉजी',
            'Neurology': 'न्यूरोलॉजी',
            'Surgery': 'सामान्य सर्जरी',
            'ICU': 'गहन चिकित्सा इकाई',
            'Emergency': 'आपातकालीन विभाग',
            'Pediatrics': 'बाल रोग',
            'Orthopedics': 'हड्डी रोग',
            'Psychiatry': 'मनोचिकित्सा'
        },
        'urgency_levels': {
            'normal': 'सामान्य',
            'urgent': 'तत्काल',
            'emergency': 'आपातकालीन'
        }
    },
    'te': {
        'appointment_types': {
            'consultation': 'సాధారణ సలహా',
            'follow-up': 'ఫాలో-అప్ సందర్శన',
            'emergency': 'ఎమర్జెన్సీ నిర్ధారణ',
            'routine': 'రూటిన్ చెక్‌అప్',
            'diagnostic': 'రోగ నిర్ధారణ పరీక్ష'
        },
        'departments': {
            'General': 'సాధారణ వైద్యకం',
            'Cardiology': 'కార్డియోలజీ',
            'Neurology': 'నరాల రોగాల శాస్త్రం',
            'Surgery': 'సాధారణ శస్త్రచికిత్స',
            'ICU': 'ఇంటెన్సివ్ కేర్ యూనిట్',
            'Emergency': 'ఎమర్జెన్సీ డిపార్టుమెంట్',
            'Pediatrics': 'శిశువిహార శాస్త్రం',
            'Orthopedics': 'ఆర్థోపెడిక్‌లు',
            'Psychiatry': 'మానసిక రోగాల శాస్త్రం'
        },
        'urgency_levels': {
            'normal': 'సాధారణ',
            'urgent': 'తక్షణ',
            'emergency': 'ఎమర్జెన్సీ'
        }
    },
    'ta': {
        'appointment_types': {
            'consultation': 'பொதுவான ஆலோசனை',
            'follow-up': 'பின்தொடர்ந்து வரவு',
            'emergency': 'அவசர நியமனம்',
            'routine': 'வழக்கமான பரிசோதனை',
            'diagnostic': 'நோய் நির்ணய சோதனை'
        },
        'departments': {
            'General': 'பொதுவான மருத்துவம்',
            'Cardiology': 'இதய நோய் சிகிச்சையியல்',
            'Neurology': 'நரம்பு மண்டல நோய் சிகிச்சையியல்',
            'Surgery': 'பொதுவான அறுவை சிகிச்சை',
            'ICU': 'தீவிர சிகிச்சை பிரிவு',
            'Emergency': 'அவசர பிரிவு',
            'Pediatrics': 'குழந்தை மருத்துவம்',
            'Orthopedics': 'எலும்பு சிகிச்சையியல்',
            'Psychiatry': 'மনோ சிகிச்சையியல்'
        },
        'urgency_levels': {
            'normal': 'சாதாரணம்',
            'urgent': 'அவசரம்',
            'emergency': 'அவசர நிலை'
        }
    },
    'ml': {
        'appointment_types': {
            'consultation': 'പൊതുവായ ഉപദേശം',
            'follow-up': 'ഫോളോ-അപ്പ് സന്ദർശനം',
            'emergency': 'എമർജൻസി നിയമനം',
            'routine': 'നിയമിത പരിശോധന',
            'diagnostic': 'രോഗനിർണയ പരിശോധന'
        },
        'departments': {
            'General': 'പൊതുവായ ഔഷധം',
            'Cardiology': 'കാർഡിയോളജി',
            'Neurology': 'ന്യൂറോളജി',
            'Surgery': 'പൊതുവായ ശസ്ത്രക്രിയ',
            'ICU': 'ഗുരുതര പരിചരണ വിഭാഗം',
            'Emergency': 'എമർജൻസി വിഭാഗം',
            'Pediatrics': 'കുട്ടികളുടെ ഔഷധം',
            'Orthopedics': 'അസ്ഥിരോഗചികിത്സ',
            'Psychiatry': 'മനോരോഗചികിത്സ'
        },
        'urgency_levels': {
            'normal': 'സാധാരണ',
            'urgent': 'അത്യാവശ്യം',
            'emergency': 'എമർജൻസി'
        }
    }
}

class AppointmentRoutingEngine:
    """Intelligent appointment routing system"""
    
    def __init__(self):
        self.weights = {
            'specialization_match': 0.30,
            'workload': 0.25,
            'availability': 0.20,
            'patient_history': 0.15,
            'urgency_response': 0.10
        }
    
    def calculate_doctor_score(self, doctor, appointment_request):
        """
        Calculate routing score for a doctor
        Higher score = better match for patient
        """
        score = 0
        
        # 1. Specialization Match (0.30)
        specialization_score = self._calculate_specialization_match(
            doctor, 
            appointment_request.department,
            appointment_request.appointment_type
        )
        score += specialization_score * self.weights['specialization_match']
        
        # 2. Workload Assessment (0.25)
        workload_score = self._calculate_workload_score(doctor, appointment_request.preferred_date)
        score += workload_score * self.weights['workload']
        
        # 3. Availability (0.20)
        availability_score = self._calculate_availability_score(doctor, appointment_request.preferred_date)
        score += availability_score * self.weights['availability']
        
        # 4. Patient History (0.15)
        history_score = self._calculate_patient_history_score(doctor, appointment_request.patient)
        score += history_score * self.weights['patient_history']
        
        # 5. Urgency Response Capability (0.10)
        urgency_score = self._calculate_urgency_response_score(doctor, appointment_request.urgency)
        score += urgency_score * self.weights['urgency_response']
        
        return score
    
    def _calculate_specialization_match(self, doctor, department, appointment_type):
        """Match doctor specialization with appointment requirements"""
        if not doctor.specialization or not department:
            return 0.5  # Neutral if no specialization info
        
        specialization_lower = doctor.specialization.lower()
        department_lower = department.lower()
        
        # Exact match
        if specialization_lower == department_lower:
            return 1.0
        
        # Partial match
        if department_lower in specialization_lower or specialization_lower in department_lower:
            return 0.8
        
        # General practitioners can handle most appointments
        if 'general' in specialization_lower:
            if appointment_type in ['routine', 'consultation']:
                return 0.7
        
        return 0.3
    
    def _calculate_workload_score(self, doctor, preferred_date):
        """Calculate workload score (fewer appointments = higher score)"""
        if not preferred_date:
            return 0.5
        
        # Count appointments on that date
        appointment_count = AppointmentRequest.query.filter(
            AppointmentRequest.doctor_id == doctor.id,
            db.func.date(AppointmentRequest.preferred_date) == preferred_date.date(),
            AppointmentRequest.status.in_(['confirmed', 'pending'])
        ).count()
        
        # Max 10 appointments per day
        workload = appointment_count / 10.0
        score = max(0, 1 - workload)  # Inverse relationship
        
        return score
    
    def _calculate_availability_score(self, doctor, preferred_date):
        """Check doctor availability on preferred date"""
        if not preferred_date:
            return 0.5
        
        # Check shifts
        shift = Shift.query.filter(
            Shift.staff_id == doctor.id,
            db.func.date(Shift.start_time) == preferred_date.date()
        ).first()
        
        if shift and shift.is_active:
            return 1.0
        
        # Doctor might be available even without a shift
        return 0.6
    
    def _calculate_patient_history_score(self, doctor, patient):
        """Prefer doctors who have treated the patient before"""
        # Check if doctor has previous notes for patient
        previous_notes = DoctorNote.query.filter(
            DoctorNote.doctor_id == doctor.id,
            DoctorNote.patient_id == patient.id
        ).count()
        
        if previous_notes > 0:
            return 1.0  # Perfect match - doctor knows patient
        
        # Check if doctor is assigned to patient
        if patient.assigned_doctor_id == doctor.id:
            return 0.9
        
        return 0.4  # New doctor
    
    def _calculate_urgency_response_score(self, doctor, urgency):
        """Score doctor's capability to handle urgent cases"""
        if urgency == 'emergency':
            # Prefer doctors on duty
            return 1.0 if doctor.is_on_duty else 0.5
        elif urgency == 'urgent':
            # Prefer doctors with shorter availability
            return 0.9 if doctor.is_on_duty else 0.7
        else:
            return 0.8
    
    def allocate_doctor(self, appointment_request):
        """
        Intelligently allocate a doctor to the appointment request
        Returns the best matching doctor or None
        """
        try:
            # Get all available doctors for the department
            if appointment_request.department:
                doctors = StaffMember.query.filter(
                    StaffMember.role == 'doctor',
                    StaffMember.is_active == True,
                    (StaffMember.department == appointment_request.department) |
                    (StaffMember.specialization.ilike(f'%{appointment_request.department}%'))
                ).all()
            else:
                # Get all active doctors
                doctors = StaffMember.query.filter(
                    StaffMember.role == 'doctor',
                    StaffMember.is_active == True
                ).all()
            
            if not doctors:
                return None
            
            # Calculate scores for each doctor
            doctor_scores = {}
            for doctor in doctors:
                score = self.calculate_doctor_score(doctor, appointment_request)
                doctor_scores[doctor.id] = {
                    'doctor': doctor,
                    'score': score
                }
            
            # Select doctor with highest score
            best_doctor_id = max(doctor_scores, key=lambda x: doctor_scores[x]['score'])
            best_doctor = doctor_scores[best_doctor_id]['doctor']
            best_score = doctor_scores[best_doctor_id]['score']
            
            # Update appointment with routing info
            appointment_request.doctor_id = best_doctor.id
            appointment_request.routing_score = best_score
            appointment_request.allocated_by_system = True
            db.session.commit()
            
            logger.info(f"Appointment {appointment_request.id} allocated to Dr. {best_doctor.full_name} (score: {best_score:.2f})")
            return best_doctor
            
        except Exception as e:
            logger.error(f"Error in doctor allocation: {str(e)}")
            return None

def get_appointment_translations(language='en'):
    """Get appointment-related translations"""
    return TRANSLATIONS.get(language, TRANSLATIONS['en'])

def allocate_appointment(appointment_request):
    """Convenience function to allocate doctor to appointment"""
    router = AppointmentRoutingEngine()
    return router.allocate_doctor(appointment_request)
