from datetime import datetime
from database import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)
    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)


class StaffMember(db.Model):
    __tablename__ = 'staff_members'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'doctor', 'nurse'
    department = db.Column(db.String(100), nullable=True)
    specialization = db.Column(db.String(100), nullable=True)
    is_on_duty = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    blood_type = db.Column(db.String(5), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    room_number = db.Column(db.String(20), nullable=True)
    bed_number = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), default='admitted')  # admitted, discharged, emergency, icu
    admission_date = db.Column(db.DateTime, default=datetime.now)
    discharge_date = db.Column(db.DateTime, nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=True)
    assigned_nurse_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    assigned_doctor = db.relationship('StaffMember', foreign_keys=[assigned_doctor_id], backref='patients_as_doctor')
    assigned_nurse = db.relationship('StaffMember', foreign_keys=[assigned_nurse_id], backref='patients_as_nurse')
    vitals = db.relationship('VitalSign', backref='patient', lazy='dynamic', order_by='desc(VitalSign.recorded_at)')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = datetime.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def latest_vitals(self):
        return self.vitals.first()


class VitalSign(db.Model):
    __tablename__ = 'vital_signs'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    heart_rate = db.Column(db.Float, nullable=True)  # bpm
    blood_pressure_systolic = db.Column(db.Integer, nullable=True)  # mmHg
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True)  # mmHg
    oxygen_saturation = db.Column(db.Float, nullable=True)  # %
    temperature = db.Column(db.Float, nullable=True)  # °F
    respiratory_rate = db.Column(db.Integer, nullable=True)  # breaths/min
    status = db.Column(db.String(20), default='normal')  # normal, warning, critical
    recorded_at = db.Column(db.DateTime, default=datetime.now)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=True)

    recorded_by = db.relationship('StaffMember', backref='recorded_vitals')


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    vital_sign_id = db.Column(db.Integer, db.ForeignKey('vital_signs.id'), nullable=True)
    alert_type = db.Column(db.String(50), nullable=False)  # critical_vitals, emergency, medication_due
    severity = db.Column(db.String(20), default='warning')  # warning, critical, emergency
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    patient = db.relationship('Patient', backref='alerts')
    vital_sign = db.relationship('VitalSign', backref='alerts')
    acknowledged_by = db.relationship('StaffMember', backref='acknowledged_alerts')


class Medication(db.Model):
    __tablename__ = 'medications'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    route = db.Column(db.String(50), nullable=True)  # oral, IV, injection, etc.
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    last_administered = db.Column(db.DateTime, nullable=True)
    next_due = db.Column(db.DateTime, nullable=True)
    prescribed_by_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    patient = db.relationship('Patient', backref='medications')
    prescribed_by = db.relationship('StaffMember', backref='prescribed_medications')


class LabReport(db.Model):
    __tablename__ = 'lab_reports'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    test_name = db.Column(db.String(200), nullable=False)
    result = db.Column(db.Text, nullable=False)
    units = db.Column(db.String(50), nullable=True)
    normal_range = db.Column(db.String(100), nullable=True)
    collected_at = db.Column(db.DateTime, nullable=True)
    reported_at = db.Column(db.DateTime, default=datetime.now)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=True)
    file_url = db.Column(db.String(300), nullable=True)

    patient = db.relationship('Patient', backref='lab_reports')
    reported_by = db.relationship('StaffMember', backref='reported_labs')


class TreatmentLog(db.Model):
    __tablename__ = 'treatment_logs'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=False)
    treatment_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    performed_at = db.Column(db.DateTime, default=datetime.now)

    patient = db.relationship('Patient', backref='treatment_logs')
    staff = db.relationship('StaffMember', backref='treatment_logs')


class MedicationAdministration(db.Model):
    __tablename__ = 'medication_administrations'
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medications.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    administered_by_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    administered_at = db.Column(db.DateTime, default=datetime.now)
    dosage_given = db.Column(db.String(100), nullable=False)
    route = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='administered')  # administered, skipped, refused, held
    notes = db.Column(db.Text, nullable=True)
    
    medication = db.relationship('Medication', backref='administrations')
    patient = db.relationship('Patient', backref='medication_administrations')
    administered_by = db.relationship('StaffMember', backref='administered_medications')


class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)  # morning, afternoon, night
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    checked_in_at = db.Column(db.DateTime, nullable=True)
    checked_out_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    staff = db.relationship('StaffMember', backref='shifts')


class ShiftHandoff(db.Model):
    __tablename__ = 'shift_handoffs'
    id = db.Column(db.Integer, primary_key=True)
    outgoing_staff_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=False)
    incoming_staff_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    handoff_time = db.Column(db.DateTime, default=datetime.now)
    summary = db.Column(db.Text, nullable=False)
    critical_notes = db.Column(db.Text, nullable=True)
    pending_tasks = db.Column(db.Text, nullable=True)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    
    outgoing_staff = db.relationship('StaffMember', foreign_keys=[outgoing_staff_id], backref='handoffs_given')
    incoming_staff = db.relationship('StaffMember', foreign_keys=[incoming_staff_id], backref='handoffs_received')
    patient = db.relationship('Patient', backref='handoffs')


class DoctorNote(db.Model):
    __tablename__ = 'doctor_notes'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=False)
    note_type = db.Column(db.String(50), nullable=False)  # progress, admission, discharge, consultation
    subjective = db.Column(db.Text, nullable=True)
    objective = db.Column(db.Text, nullable=True)
    assessment = db.Column(db.Text, nullable=True)
    plan = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    
    patient = db.relationship('Patient', backref='doctor_notes')
    doctor = db.relationship('StaffMember', backref='notes_written')


class RiskAssessment(db.Model):
    __tablename__ = 'risk_assessments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    risk_score = db.Column(db.Integer, nullable=False)
    risk_factors = db.Column(db.Text, nullable=True)
    predictions = db.Column(db.Text, nullable=True)
    assessed_at = db.Column(db.DateTime, default=datetime.now)
    
    patient = db.relationship('Patient', backref='risk_assessments')


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'patient' or 'assistant'
    message = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(5), default='en')  # 'en', 'es', 'fr', 'hi'
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    patient = db.relationship('Patient', backref='chat_messages')


class AppointmentRequest(db.Model):
    __tablename__ = 'appointment_requests'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.now)
    preferred_date = db.Column(db.DateTime, nullable=True)
    preferred_time = db.Column(db.String(20), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('staff_members.id'), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled
    notes = db.Column(db.Text, nullable=True)

    patient = db.relationship('Patient', backref='appointment_requests')
    doctor = db.relationship('StaffMember', backref='received_appointments')
