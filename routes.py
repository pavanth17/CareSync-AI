import json
import logging
from datetime import datetime
from functools import wraps
from flask import render_template, redirect, url_for, request, flash, session, Response, jsonify
from flask_login import current_user
from app import app, db
from models import StaffMember, Patient, VitalSign, Alert, Medication, TreatmentLog, MedicationAdministration, Shift, ShiftHandoff, DoctorNote, RiskAssessment, ChatMessage, LabReport, AppointmentRequest, AuditLog, Round, Ward
# Removed Replit-specific auth integration; using local session-based auth instead
from synthetic_data import initialize_synthetic_data

logging.basicConfig(level=logging.DEBUG)

# Replit auth blueprint removed for local hosting

def generate_fallback_response(patient, user_message, language='en'):
    """Generate intelligent fallback responses based on patient data"""
    msg_lower = user_message.lower()
    
    # Get patient data
    active_meds = Medication.query.filter_by(patient_id=patient.id, is_active=True).all()
    latest_vital = patient.vitals.order_by(VitalSign.recorded_at.desc()).first()
    
    if language == 'hi':
        if any(word in msg_lower for word in ['medicine', 'medication', 'दवा']):
            if active_meds:
                meds_text = ', '.join([f"{m.name} ({m.dosage})" for m in active_meds])
                return f"आपकी वर्तमान दवाएं: {meds_text}। कृपया अपने डॉक्टर से परामर्श करें।"
            return "आपके पास वर्तमान में कोई सक्रिय दवा नहीं है।"
        elif any(word in msg_lower for word in ['blood pressure', 'bp', 'ब्लड प्रेशर']):
            if latest_vital:
                return f"आपका नवीनतम रक्तचाप: {latest_vital.blood_pressure_systolic}/{latest_vital.blood_pressure_diastolic} mmHg है।"
            return "रक्तचाप डेटा उपलब्ध नहीं है।"
        elif any(word in msg_lower for word in ['diagnosis', 'बीमारी', 'रोग']):
            return f"आपका निदान: {patient.diagnosis}। अधिक जानकारी के लिए अपने डॉक्टर से बात करें।"
        return "नमस्ते, मैं CareSync सहायक हूँ। कृपया अपने डॉक्टर से परामर्श करें।"
    
    # English fallback
    if any(word in msg_lower for word in ['medicine', 'medication', 'drug', 'pills']):
        if active_meds:
            meds_text = ', '.join([f"{m.name} ({m.dosage})" for m in active_meds])
            return f"Your current medications: {meds_text}. Please consult your doctor for more details."
        return "You currently have no active medications on record."
    
    elif any(word in msg_lower for word in ['blood pressure', 'bp', 'vitals', 'vital signs']):
        if latest_vital:
            return f"Your latest blood pressure: {latest_vital.blood_pressure_systolic}/{latest_vital.blood_pressure_diastolic} mmHg. Heart rate: {latest_vital.heart_rate} bpm. SpO2: {latest_vital.oxygen_saturation}%."
        return "Vital signs data not available."
    
    elif any(word in msg_lower for word in ['diagnosis', 'condition', 'disease']):
        return f"Your diagnosis: {patient.diagnosis}. For detailed information, please consult your doctor."
    
    elif any(word in msg_lower for word in ['appointment', 'schedule', 'book']):
        appointments = AppointmentRequest.query.filter_by(patient_id=patient.id, status='confirmed').count()
        return f"You have {appointments} confirmed appointments. To book a new appointment, use the Appointments tab."
    
    elif any(word in msg_lower for word in ['emergency', 'urgent', 'help', 'pain']):
        return "If you're experiencing an emergency, please call 911 or visit your nearest emergency room immediately."
    
    # Default response
    return "Hello! I'm CareSync Assistant. I can help with information about your medications, vitals, and health records. Please contact your healthcare provider for medical advice."

@app.before_request
def make_session_permanent():
    session.permanent = True


def get_staff_user():
    if 'staff_id' in session:
        return StaffMember.query.filter_by(id=session['staff_id']).first()
    return None


def staff_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        staff = get_staff_user()
        if not staff:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        staff = get_staff_user()
        if not staff or staff.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            staff = get_staff_user()
            if not staff or staff.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Server is running'}), 200


@app.route('/')
def index():
    staff = get_staff_user()
    if staff:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def staff_login():
    if get_staff_user():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        identifier = request.form.get('staff_id', '').strip()
        password = request.form.get('password', '')

        # Allow login using either staff ID (e.g. DOC0001) or email address
        staff = None
        try:
            if '@' in identifier:
                staff = StaffMember.query.filter_by(email=identifier.lower(), is_active=True).first()
            else:
                staff = StaffMember.query.filter_by(staff_id=identifier.upper(), is_active=True).first()
        except Exception:
            staff = None

        if staff and staff.check_password(password):
            session['staff_id'] = staff.id
            session['staff_role'] = staff.role
            
            # Audit Login
            try:
                log = AuditLog(
                    action='LOGIN',
                    table_name='auth',
                    record_id=staff.id,
                    field_name='session',
                    old_value=None,
                    new_value='active',
                    changed_by_id=staff.id
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                logging.error(f"Failed to log login audit: {e}")
                
            flash(f'Welcome back, {staff.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Staff ID / email or password.', 'danger')
            # Optional: Log failed attempts if needed (careful with spam)
    
    return render_template('index.html')

@app.route('/logout')
def logout():
    staff = get_staff_user()
    if staff:
        try:
            log = AuditLog(
                action='LOGOUT',
                table_name='auth',
                record_id=staff.id,
                field_name='session',
                old_value='active',
                new_value='terminated',
                changed_by_id=staff.id
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
            
    session.pop('staff_id', None)
    session.pop('staff_role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('staff_login'))





@app.route('/dashboard')
@staff_login_required
def dashboard():
    staff = get_staff_user()
    
    if staff.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif staff.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif staff.role == 'nurse':
        return redirect(url_for('nurse_dashboard'))
    
    return redirect(url_for('index'))


@app.route('/ward/<department_name>')
@staff_login_required
def ward_dashboard(department_name):
    """Specific dashboard for a department/ward"""
    staff = get_staff_user()
    
    # Fetch patients in this department, exclude discharged
    patients = Patient.query.filter(
        Patient.department == department_name, 
        Patient.status != 'discharged'
    ).order_by(Patient.room_number).all()
    
    # Quick stats
    critical_count = 0
    stable_count = 0
    for p in patients:
        lv = p.latest_vitals
        if lv and lv.status == 'critical':
            critical_count += 1
        elif lv and lv.status == 'normal':
            stable_count += 1
            
    # Staff on duty in this department
    staff_on_duty_count = StaffMember.query.filter_by(
        department=department_name, 
        is_on_duty=True
    ).count()
    
    return render_template('ward_dashboard.html', 
        staff=staff,
        department=department_name,
        patients=patients,
        critical_count=critical_count,
        stable_count=stable_count,
        staff_on_duty_count=staff_on_duty_count
    )


@app.route('/admin')
@staff_login_required
@admin_required
def admin_dashboard():
    staff = get_staff_user()
    
    total_patients = Patient.query.filter(Patient.status != 'discharged').count()
    total_doctors = StaffMember.query.filter_by(role='doctor', is_active=True).count()
    total_nurses = StaffMember.query.filter_by(role='nurse', is_active=True).count()
    on_duty_doctors = StaffMember.query.filter_by(role='doctor', is_on_duty=True, is_active=True).count()
    on_duty_nurses = StaffMember.query.filter_by(role='nurse', is_on_duty=True, is_active=True).count()
    critical_alerts = Alert.query.filter_by(is_acknowledged=False, severity='critical').count()
    
    icu_patients = Patient.query.filter_by(status='icu').count()
    emergency_patients = Patient.query.filter_by(status='emergency').count()
    
    doctors = StaffMember.query.filter_by(role='doctor', is_active=True).all()
    nurses = StaffMember.query.filter_by(role='nurse', is_active=True).all()
    
    recent_alerts = Alert.query.filter_by(is_acknowledged=False).order_by(Alert.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
        staff=staff,
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_nurses=total_nurses,
        on_duty_doctors=on_duty_doctors,
        on_duty_nurses=on_duty_nurses,
        critical_alerts=critical_alerts,
        icu_patients=icu_patients,
        emergency_patients=emergency_patients,
        doctors=doctors,
        nurses=nurses,
        recent_alerts=recent_alerts
    )


@app.route('/admin/users')
@staff_login_required
@admin_required
def admin_users():
    staff = get_staff_user()
    all_staff = StaffMember.query.filter(StaffMember.role != 'admin').order_by(StaffMember.role, StaffMember.last_name).all()
    return render_template('admin/users.html', staff=staff, all_staff=all_staff)


@app.route('/admin/register', methods=['GET', 'POST'])
@staff_login_required
@admin_required
def admin_register():
    staff = get_staff_user()
    
    if request.method == 'POST':
        role = request.form.get('role')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        specialization = request.form.get('specialization', '').strip()
        password = request.form.get('password', '')
        
        if not all([role, first_name, last_name, email, password]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('admin/register.html', staff=staff)
        
        if StaffMember.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/register.html', staff=staff)
        
        prefix = {'doctor': 'DOC', 'nurse': 'NRS'}
        count = StaffMember.query.filter_by(role=role).count() + 1
        staff_id = f"{prefix.get(role, 'STF')}{str(count).zfill(4)}"
        
        while StaffMember.query.filter_by(staff_id=staff_id).first():
            count += 1
            staff_id = f"{prefix.get(role, 'STF')}{str(count).zfill(4)}"
        
        new_staff = StaffMember(
            staff_id=staff_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            role=role,
            department=department,
            specialization=specialization if role == 'doctor' else None,
            is_on_duty=False,
            is_active=True
        )
        new_staff.set_password(password)
        
        db.session.add(new_staff)
        db.session.commit()
        
        flash(f'{role.title()} registered successfully. Staff ID: {staff_id}', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/register.html', staff=staff)


@app.route('/admin/staff/<int:staff_id>/toggle-duty', methods=['POST'])
@staff_login_required
@admin_required
def toggle_duty(staff_id):
    target_staff = StaffMember.query.get_or_404(staff_id)
    target_staff.is_on_duty = not target_staff.is_on_duty
    db.session.commit()
    return redirect(url_for('admin_users'))


@app.route('/admin/staff/<int:staff_id>/toggle-active', methods=['POST'])
@staff_login_required
@admin_required
def toggle_active(staff_id):
    target_staff = StaffMember.query.get_or_404(staff_id)
    target_staff.is_active = not target_staff.is_active
    db.session.commit()
    return redirect(url_for('admin_users'))


@app.route('/admin/patients')
@staff_login_required
@admin_required
def admin_patients():
    staff = get_staff_user()
    patients = Patient.query.order_by(Patient.admission_date.desc()).all()
    return render_template('admin/patients.html', staff=staff, patients=patients)


@app.route('/admin/appointments')
@staff_login_required
@admin_required
def admin_appointments():
    staff = get_staff_user()
    appointments = AppointmentRequest.query.order_by(AppointmentRequest.requested_at.desc()).all()
    return render_template('admin/appointments.html', staff=staff, appointments=appointments)


@app.route('/admin/appointment/<int:appt_id>/confirm', methods=['POST'])
@staff_login_required
def confirm_appointment(appt_id):
    # Depending on requirements, maybe only admin or doctors can confirm
    staff = get_staff_user()
    if staff.role not in ['admin', 'doctor']:
        flash('Permission denied.', 'danger')
        return redirect(url_for('dashboard'))
        
    appt = AppointmentRequest.query.get_or_404(appt_id)
    appt.status = 'confirmed'
    db.session.commit()
    flash('Appointment confirmed.', 'success')
    return redirect(request.referrer or url_for('admin_appointments'))



@app.route('/doctor')
@staff_login_required
@role_required('doctor', 'admin')
def doctor_dashboard():
    staff = get_staff_user()
    
    if staff.role == 'admin':
        patients = Patient.query.filter(Patient.status != 'discharged').all()
        active_alerts = []
        critical_alerts = []
    else:
        patients = Patient.query.filter_by(assigned_doctor_id=staff.id).filter(Patient.status != 'discharged').all()
        
        if staff.is_on_duty:
            patient_ids = [p.id for p in patients]
            active_alerts = Alert.query.filter(
                Alert.patient_id.in_(patient_ids),
                Alert.is_acknowledged == False
            ).order_by(Alert.severity.desc(), Alert.created_at.desc()).all()
            critical_alerts = [a for a in active_alerts if a.severity == 'critical']
        else:
            active_alerts = []
            critical_alerts = []
    
    return render_template('doctor/dashboard.html',
        staff=staff,
        patients=patients,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        todays_rounds=Round.query.filter(
            Round.doctor_id == staff.id, 
            Round.scheduled_time >= datetime.now().replace(hour=0, minute=0, second=0),
            Round.scheduled_time < datetime.now().replace(hour=0, minute=0, second=0) + __import__('datetime').timedelta(days=1)
        ).order_by(Round.scheduled_time).all()
    )


@app.route('/doctor/schedule-round', methods=['POST'])
@staff_login_required
@role_required('doctor')
def schedule_round():
    staff = get_staff_user()
    patient_id = request.form.get('patient_id')
    scheduled_time_str = request.form.get('scheduled_time')
    notes = request.form.get('notes')

    if not patient_id or not scheduled_time_str:
        flash('Missing required fields', 'danger')
        return redirect(url_for('doctor_dashboard'))

    try:
        # Combine today's date with the time
        time_obj = datetime.strptime(scheduled_time_str, '%H:%M').time()
        scheduled_datetime = datetime.combine(datetime.now().date(), time_obj)
        
        round_entry = Round(
            doctor_id=staff.id,
            patient_id=patient_id,
            scheduled_time=scheduled_datetime,
            notes=notes,
            status='pending'
        )
        db.session.add(round_entry)
        db.session.commit()
        flash('Round scheduled successfully', 'success')
    except Exception as e:
        flash(f'Error scheduling round: {e}', 'danger')

    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/round/<int:round_id>/complete', methods=['POST'])
@staff_login_required
@role_required('doctor')
def complete_round(round_id):
    round_entry = Round.query.get_or_404(round_id)
    if round_entry.doctor_id != session.get('staff_id'):
         flash('Unauthorized', 'danger')
         return redirect(url_for('doctor_dashboard'))
    
    round_entry.status = 'completed'
    db.session.commit()
    flash('Round marked as completed', 'success')
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/note/<int:patient_id>/add', methods=['GET', 'POST'])
@staff_login_required
@role_required('doctor')
def add_doctor_note(patient_id):
    staff = get_staff_user()
    patient = Patient.query.get_or_404(patient_id)

    if request.method == 'POST':
        note_type = request.form.get('note_type')
        subjective = request.form.get('subjective')
        objective = request.form.get('objective')
        assessment = request.form.get('assessment')
        plan = request.form.get('plan')

        note = DoctorNote(
            patient_id=patient.id,
            doctor_id=staff.id,
            note_type=note_type,
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan
        )
        db.session.add(note)
        db.session.commit()
        flash('Note added successfully', 'success')
        return redirect(url_for('patient_detail', patient_id=patient.id))

    return render_template('doctor/add_note.html', staff=staff, patient=patient)



@app.route('/nurse')
@staff_login_required
@role_required('nurse', 'admin')
def nurse_dashboard():
    staff = get_staff_user()
    
    if staff.role == 'admin':
        patients = Patient.query.filter(Patient.status != 'discharged').all()
        active_alerts = []
    else:
        patients = Patient.query.filter_by(assigned_nurse_id=staff.id).filter(Patient.status != 'discharged').all()
        
        if staff.is_on_duty:
            patient_ids = [p.id for p in patients]
            active_alerts = Alert.query.filter(
                Alert.patient_id.in_(patient_ids),
                Alert.is_acknowledged == False
            ).order_by(Alert.severity.desc(), Alert.created_at.desc()).all()
        else:
            active_alerts = []
    
    medications_due = Medication.query.filter(
        Medication.is_active == True,
        Medication.next_due <= datetime.now()
    ).all()
    
    return render_template('nurse/dashboard.html',
        staff=staff,
        patients=patients,
        active_alerts=active_alerts,
        medications_due=medications_due
    )


@app.route('/patient/<int:patient_id>')
@staff_login_required
def patient_detail(patient_id):
    try:
        staff = get_staff_user()
        patient = Patient.query.get_or_404(patient_id)
        
        # Audit View (Full Record Access)
        try:
            log = AuditLog(
                action='VIEW',
                table_name='patients',
                record_id=patient.id,
                field_name='all',
                old_value=None,
                new_value='full_detail_access',
                changed_by_id=staff.id
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logging.error(f"Audit Log Error: {e}")
        
        vitals = VitalSign.query.filter_by(patient_id=patient_id).order_by(VitalSign.recorded_at.desc()).limit(50).all()
        medications = Medication.query.filter_by(patient_id=patient_id, is_active=True).all()
        # load lab reports for the patient
        lab_reports = LabReport.query.filter_by(patient_id=patient_id).order_by(LabReport.reported_at.desc()).limit(20).all()
        alerts = Alert.query.filter_by(patient_id=patient_id).order_by(Alert.created_at.desc()).limit(20).all()
        treatment_logs = TreatmentLog.query.filter_by(patient_id=patient_id).order_by(TreatmentLog.performed_at.desc()).limit(20).all()
        
        # Serialize vitals for use in client-side charts (JSON-serializable)
        vitals_json = []
        for v in vitals:
            vitals_json.append({
                'id': v.id,
                'heart_rate': v.heart_rate,
                'blood_pressure_systolic': v.blood_pressure_systolic,
                'blood_pressure_diastolic': v.blood_pressure_diastolic,
                'oxygen_saturation': v.oxygen_saturation,
                'temperature': v.temperature,
                'respiratory_rate': v.respiratory_rate,
                'status': v.status,
                'recorded_at': v.recorded_at.isoformat()
            })

        return render_template('patient_detail.html',
            staff=staff,
            patient=patient,
            vitals=vitals,
            vitals_json=vitals_json,
            medications=medications,
            lab_reports=lab_reports,
            alerts=alerts,
            treatment_logs=treatment_logs
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        app.logger.error('Error rendering patient_detail: %s', tb)
        return Response(tb, status=500, mimetype='text/plain')


@app.route('/alert/<int:alert_id>/acknowledge', methods=['POST'])
@staff_login_required
def acknowledge_alert(alert_id):
    staff = get_staff_user()
    alert = Alert.query.get_or_404(alert_id)
    
    alert.is_acknowledged = True
    alert.acknowledged_by_id = staff.id
    alert.acknowledged_at = datetime.now()
    db.session.commit()
    # If this was an AJAX request, return a JSON response so the client can update UI without reload
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'ok': True, 'alert_id': alert_id}), 200

    return redirect(request.referrer or url_for('dashboard'))


@app.route('/api/trigger-emergency-alert', methods=['POST'])
@staff_login_required
def trigger_emergency_alert():
    """Trigger a random patient emergency alert for demo/testing purposes"""
    try:
        staff = get_staff_user()
        
        # Get admitted patients
        patients = Patient.query.filter(Patient.status.in_(['admitted', 'icu', 'emergency'])).all()
        
        if not patients:
            return jsonify({'success': False, 'message': 'No patients available'}), 400
        
        # Pick a random patient
        import random
        patient = random.choice(patients)
        
        # Create emergency alert
        alert = Alert(
            patient_id=patient.id,
            alert_type='oxygen_critical',
            severity='critical',
            message=f'EMERGENCY: {patient.full_name} - Oxygen saturation critically low (88%)',
            details={'reason': 'Demo emergency alert - oxygen saturation critical'},
            created_by_id=staff.id,
            is_acknowledged=False
        )
        
        db.session.add(alert)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'alert_id': alert.id,
            'patient_id': patient.id,
            'patient_name': patient.full_name,
            'severity': alert.severity,
            'message': alert.message
        }), 200
        
    except Exception as e:
        logging.error(f"Error triggering emergency alert: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/vitals/stream')
@staff_login_required
def vitals_stream():
    def generate():
        import time
        from vital_simulator import update_patient_vitals, get_and_clear_new_alerts, get_live_patient_vitals
        while True:
            update_patient_vitals()
            
            vitals = get_live_patient_vitals()
            alerts = get_and_clear_new_alerts()
            
            data = {
                'vitals': vitals,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(5)
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/alerts/active')
@staff_login_required
def get_active_alerts():
    staff = get_staff_user()
    
    if staff.role == 'admin':
        return jsonify([])
    
    if not staff.is_on_duty:
        return jsonify([])
    
    alerts = Alert.query.filter_by(is_acknowledged=False).order_by(
        Alert.severity.desc(),
        Alert.created_at.desc()
    ).all()
    
    alerts_data = []
    for alert in alerts:
        patient = Patient.query.get(alert.patient_id)
        alerts_data.append({
            'id': alert.id,
            'patient_id': alert.patient_id,
            'patient_name': patient.full_name if patient else 'Unknown',
            'room': patient.room_number if patient else '',
            'bed': patient.bed_number if patient else '',
            'type': alert.alert_type,
            'severity': alert.severity,
            'title': alert.title,
            'message': alert.message,
            'created_at': alert.created_at.isoformat()
        })
    
    return jsonify(alerts_data)


@app.route('/api/patient/<int:patient_id>/vitals')
@staff_login_required
def get_patient_vitals(patient_id):
    vitals = VitalSign.query.filter_by(patient_id=patient_id).order_by(VitalSign.recorded_at.desc()).limit(20).all()
    
    vitals_data = []
    for vital in vitals:
        vitals_data.append({
            'id': vital.id,
            'heart_rate': vital.heart_rate,
            'bp_systolic': vital.blood_pressure_systolic,
            'bp_diastolic': vital.blood_pressure_diastolic,
            'oxygen': vital.oxygen_saturation,
            'temperature': vital.temperature,
            'respiratory_rate': vital.respiratory_rate,
            'status': vital.status,
            'recorded_at': vital.recorded_at.isoformat()
        })
    
    return jsonify(vitals_data)


@app.route('/init-data')
def init_data():
    try:
        initialize_synthetic_data()
        flash('Synthetic data initialized successfully!', 'success')
    except Exception as e:
        flash(f'Error initializing data: {str(e)}', 'danger')
        logging.error(f"Error initializing data: {e}")
    return redirect(url_for('index'))


@app.route('/credentials')
def view_credentials():
    admins = StaffMember.query.filter_by(role='admin', is_active=True).all()
    doctors = StaffMember.query.filter_by(role='doctor', is_active=True).all()
    nurses = StaffMember.query.filter_by(role='nurse', is_active=True).all()
    
    credentials = {
        'admins': [{'staff_id': a.staff_id, 'name': a.full_name} for a in admins],
        'doctors': [{'staff_id': d.staff_id, 'name': d.full_name} for d in doctors],
        'nurses': [{'staff_id': n.staff_id, 'name': n.full_name} for n in nurses]
    }
    
    return render_template('credentials.html', credentials=credentials)


@app.context_processor
def utility_processor():
    return {
        'now': datetime.now(),
        'get_staff_user': get_staff_user
    }


@app.route('/patient/<int:patient_id>/risk-analysis')
@staff_login_required
def patient_risk_analysis(patient_id):
    from predictive_analytics import risk_predictor
    staff = get_staff_user()
    patient = Patient.query.get_or_404(patient_id)
    
    analysis = risk_predictor.analyze_patient_risk(patient_id)
    
    risk_assessment = RiskAssessment(
        patient_id=patient_id,
        risk_level=analysis['risk_level'],
        risk_score=analysis['risk_score'],
        risk_factors=json.dumps(analysis.get('risk_factors', [])),
        predictions=json.dumps(analysis.get('predictions', []))
    )
    db.session.add(risk_assessment)
    db.session.commit()
    
    past_assessments = RiskAssessment.query.filter_by(patient_id=patient_id).order_by(
        RiskAssessment.assessed_at.desc()
    ).limit(10).all()
    
    return render_template('risk_analysis.html',
        staff=staff,
        patient=patient,
        analysis=analysis,
        past_assessments=past_assessments
    )


@app.route('/api/risk-analysis/<int:patient_id>')
@staff_login_required
def api_risk_analysis(patient_id):
    from predictive_analytics import risk_predictor
    analysis = risk_predictor.analyze_patient_risk(patient_id)
    return jsonify(analysis)


@app.route('/api/risk-analysis/all')
@staff_login_required
def api_all_risk_analysis():
    from predictive_analytics import analyze_all_patients
    results = analyze_all_patients()
    return jsonify(results)


@app.route('/medication/<int:patient_id>/schedule', methods=['GET', 'POST'])
@staff_login_required
@role_required('doctor', 'nurse', 'admin')
def medication_schedule(patient_id):
    staff = get_staff_user()
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dosage = request.form.get('dosage', '').strip()
        frequency = request.form.get('frequency', '').strip()
        route = request.form.get('route', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if name and dosage and frequency:
            freq_hours = {
                'Once daily': 24,
                'Twice daily': 12,
                'Three times daily': 8,
                'Four times daily': 6,
                'Every 4 hours': 4,
                'Every 6 hours': 6,
                'Every 8 hours': 8,
                'Every 12 hours': 12,
                'As needed': 0
            }.get(frequency, 24)
            
            from datetime import timedelta
            next_due = datetime.now() + timedelta(hours=freq_hours) if freq_hours > 0 else None
            
            medication = Medication(
                patient_id=patient_id,
                name=name,
                dosage=dosage,
                frequency=frequency,
                route=route,
                start_date=datetime.now(),
                next_due=next_due,
                prescribed_by_id=staff.id if staff.role == 'doctor' else None,
                notes=notes,
                is_active=True
            )
            db.session.add(medication)
            db.session.commit()
            
            flash(f'Medication "{name}" scheduled successfully.', 'success')
            return redirect(url_for('patient_medications', patient_id=patient_id))
        else:
            flash('Please fill in all required fields.', 'danger')
    
    return render_template('medication_schedule.html', staff=staff, patient=patient)


@app.route('/patient/<int:patient_id>/medications')
@staff_login_required
def patient_medications(patient_id):
    staff = get_staff_user()
    patient = Patient.query.get_or_404(patient_id)
    
    medications = Medication.query.filter_by(patient_id=patient_id, is_active=True).all()
    past_medications = Medication.query.filter_by(patient_id=patient_id, is_active=False).limit(10).all()
    
    administrations = MedicationAdministration.query.filter_by(patient_id=patient_id).order_by(
        MedicationAdministration.administered_at.desc()
    ).limit(30).all()
    
    return render_template('patient_medications.html',
        staff=staff,
        patient=patient,
        medications=medications,
        past_medications=past_medications,
        administrations=administrations
    )


@app.route('/medication/<int:medication_id>/administer', methods=['POST'])
@staff_login_required
@role_required('nurse', 'admin')
def administer_medication(medication_id):
    staff = get_staff_user()
    medication = Medication.query.get_or_404(medication_id)
    
    notes = request.form.get('notes', '').strip()
    status = request.form.get('status', 'administered')
    
    administration = MedicationAdministration(
        medication_id=medication_id,
        patient_id=medication.patient_id,
        administered_by_id=staff.id,
        scheduled_time=medication.next_due or datetime.now(),
        dosage_given=medication.dosage,
        route=medication.route,
        status=status,
        notes=notes
    )
    db.session.add(administration)
    
    medication.last_administered = datetime.now()
    
    freq_hours = {
        'Once daily': 24,
        'Twice daily': 12,
        'Three times daily': 8,
        'Four times daily': 6,
        'Every 4 hours': 4,
        'Every 6 hours': 6,
        'Every 8 hours': 8,
        'Every 12 hours': 12,
        'As needed': 0
    }.get(medication.frequency, 24)
    
    from datetime import timedelta
    if freq_hours > 0:
        medication.next_due = datetime.now() + timedelta(hours=freq_hours)
    
    db.session.commit()
    
    flash(f'Medication administration recorded.', 'success')
    return redirect(url_for('patient_medications', patient_id=medication.patient_id))


@app.route('/shifts')
@staff_login_required
def shift_management():
    staff = get_staff_user()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    tomorrow = today + timedelta(days=1)
    
    todays_shifts = Shift.query.filter(
        Shift.start_time >= today,
        Shift.start_time < tomorrow
    ).order_by(Shift.start_time).all()
    
    on_duty_staff = StaffMember.query.filter_by(is_on_duty=True, is_active=True).all()
    all_staff = StaffMember.query.filter(StaffMember.role.in_(['doctor', 'nurse']), StaffMember.is_active == True).all()
    
    pending_handoffs = ShiftHandoff.query.filter_by(acknowledged=False).order_by(
        ShiftHandoff.handoff_time.desc()
    ).all()
    
    return render_template('shifts.html',
        staff=staff,
        todays_shifts=todays_shifts,
        on_duty_staff=on_duty_staff,
        all_staff=all_staff,
        pending_handoffs=pending_handoffs
    )


@app.route('/shifts/create', methods=['POST'])
@staff_login_required
@role_required('admin')
def create_shift():
    staff_member_id = request.form.get('staff_id', type=int)
    shift_type = request.form.get('shift_type', '')
    department = request.form.get('department', '')
    date_str = request.form.get('date', '')
    
    if not staff_member_id or not shift_type or not date_str:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('shift_management'))
    
    shift_times = {
        'morning': (7, 15),
        'afternoon': (15, 23),
        'night': (23, 7)
    }
    
    from datetime import timedelta
    date = datetime.strptime(date_str, '%Y-%m-%d')
    start_hour, end_hour = shift_times.get(shift_type, (7, 15))
    
    start_time = date.replace(hour=start_hour, minute=0, second=0)
    if end_hour < start_hour:
        end_time = (date + timedelta(days=1)).replace(hour=end_hour, minute=0, second=0)
    else:
        end_time = date.replace(hour=end_hour, minute=0, second=0)
    
    shift = Shift(
        staff_id=staff_member_id,
        shift_type=shift_type,
        start_time=start_time,
        end_time=end_time,
        department=department,
        is_active=True
    )
    db.session.add(shift)
    db.session.commit()
    
    flash('Shift created successfully.', 'success')
    return redirect(url_for('shift_management'))


@app.route('/shifts/<int:shift_id>/check-in', methods=['POST'])
@staff_login_required
def shift_check_in(shift_id):
    staff = get_staff_user()
    shift = Shift.query.get_or_404(shift_id)
    
    if shift.staff_id != staff.id and staff.role != 'admin':
        flash('You can only check in to your own shift.', 'danger')
        return redirect(url_for('shift_management'))
    
    shift.checked_in_at = datetime.now()
    
    staff_member = StaffMember.query.get(shift.staff_id)
    if staff_member:
        staff_member.is_on_duty = True
    
    db.session.commit()
    
    flash('Checked in successfully.', 'success')
    return redirect(url_for('shift_management'))


@app.route('/shifts/<int:shift_id>/check-out', methods=['POST'])
@staff_login_required
def shift_check_out(shift_id):
    staff = get_staff_user()
    shift = Shift.query.get_or_404(shift_id)
    
    if shift.staff_id != staff.id and staff.role != 'admin':
        flash('You can only check out from your own shift.', 'danger')
        return redirect(url_for('shift_management'))
    
    shift.checked_out_at = datetime.now()
    shift.is_active = False
    
    staff_member = StaffMember.query.get(shift.staff_id)
    if staff_member:
        staff_member.is_on_duty = False
    
    db.session.commit()
    
    flash('Checked out successfully.', 'success')
    return redirect(url_for('shift_management'))


@app.route('/handoff/create', methods=['GET', 'POST'])
@staff_login_required
def create_handoff():
    staff = get_staff_user()
    
    if request.method == 'POST':
        incoming_staff_id = request.form.get('incoming_staff_id', type=int)
        patient_id = request.form.get('patient_id', type=int) or None
        summary = request.form.get('summary', '').strip()
        critical_notes = request.form.get('critical_notes', '').strip()
        pending_tasks = request.form.get('pending_tasks', '').strip()
        
        if not incoming_staff_id or not summary:
            flash('Please provide incoming staff and summary.', 'danger')
            return redirect(url_for('create_handoff'))
        
        handoff = ShiftHandoff(
            outgoing_staff_id=staff.id,
            incoming_staff_id=incoming_staff_id,
            patient_id=patient_id,
            summary=summary,
            critical_notes=critical_notes,
            pending_tasks=pending_tasks
        )
        db.session.add(handoff)
        db.session.commit()
        
        flash('Handoff report created successfully.', 'success')
        return redirect(url_for('shift_management'))
    
    incoming_staff_list = StaffMember.query.filter(
        StaffMember.role == staff.role,
        StaffMember.id != staff.id,
        StaffMember.is_active == True
    ).all()
    
    if staff.role == 'doctor':
        patients = Patient.query.filter_by(assigned_doctor_id=staff.id).filter(Patient.status != 'discharged').all()
    elif staff.role == 'nurse':
        patients = Patient.query.filter_by(assigned_nurse_id=staff.id).filter(Patient.status != 'discharged').all()
    else:
        patients = Patient.query.filter(Patient.status != 'discharged').all()
    
    return render_template('handoff_create.html',
        staff=staff,
        incoming_staff_list=incoming_staff_list,
        patients=patients
    )


@app.route('/handoff/<int:handoff_id>/acknowledge', methods=['POST'])
@staff_login_required
def acknowledge_handoff(handoff_id):
    staff = get_staff_user()
    handoff = ShiftHandoff.query.get_or_404(handoff_id)
    
    if handoff.incoming_staff_id != staff.id:
        flash('You can only acknowledge handoffs addressed to you.', 'danger')
        return redirect(url_for('shift_management'))
    
    handoff.acknowledged = True
    handoff.acknowledged_at = datetime.now()
    db.session.commit()
    
    flash('Handoff acknowledged.', 'success')
    return redirect(url_for('shift_management'))


@app.route('/patient/<int:patient_id>/history')
@staff_login_required
def patient_history(patient_id):
    staff = get_staff_user()
    if not staff:
        flash('You must be logged in as staff to access this page.', 'danger')
        return redirect(url_for('staff_login'))
    patient = Patient.query.get_or_404(patient_id)
    
    vitals = VitalSign.query.filter_by(patient_id=patient_id).order_by(VitalSign.recorded_at.desc()).limit(100).all()
    treatments = TreatmentLog.query.filter_by(patient_id=patient_id).order_by(TreatmentLog.performed_at.desc()).all()
    notes = DoctorNote.query.filter_by(patient_id=patient_id).order_by(DoctorNote.created_at.desc()).all()
    medications = MedicationAdministration.query.filter_by(patient_id=patient_id).order_by(
        MedicationAdministration.administered_at.desc()
    ).all()
    alerts = Alert.query.filter_by(patient_id=patient_id).order_by(Alert.created_at.desc()).limit(50).all()
    risk_assessments = RiskAssessment.query.filter_by(patient_id=patient_id).order_by(
        RiskAssessment.assessed_at.desc()
    ).limit(20).all()
    
    return render_template('patient_history.html',
        staff=staff,
        patient=patient,
        vitals=vitals,
        treatments=treatments,
        notes=notes,
        medications=medications,
        alerts=alerts,
        risk_assessments=risk_assessments
    )





@app.route('/patient/<int:patient_id>/add-treatment', methods=['GET', 'POST'])
@staff_login_required
def add_treatment(patient_id):
    staff = get_staff_user()
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        treatment_type = request.form.get('treatment_type', '').strip()
        description = request.form.get('description', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if treatment_type and description:
            treatment = TreatmentLog(
                patient_id=patient_id,
                staff_id=staff.id,
                treatment_type=treatment_type,
                description=description,
                notes=notes
            )
            db.session.add(treatment)
            db.session.commit()
            
            flash('Treatment logged successfully.', 'success')
            return redirect(url_for('patient_history', patient_id=patient_id))
        else:
            flash('Please fill in all required fields.', 'danger')
    
    return render_template('add_treatment.html', staff=staff, patient=patient)


# ===== UNIVERSAL PATIENT PORTAL =====

def get_logged_in_patient():
    if 'patient_id' in session:
        return Patient.query.get(session['patient_id'])
    return None

def patient_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'patient_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('patient_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/patient-login', methods=['GET', 'POST'])
def patient_login():
    """Universal patient login portal (Current & Discharged)"""
    if request.method == 'POST':
        patient_id_str = request.form.get('patient_id', '').strip().upper()
        phone = request.form.get('phone', '').strip()

        # Normalize phone by removing non-digit characters for matching
        def norm_phone(p):
            return ''.join([c for c in (p or '') if c.isdigit()])

        norm_input_phone = norm_phone(phone)

        # Query patient by ID (any status)
        patient = Patient.query.filter_by(patient_id=patient_id_str).first()
        
        # Verify phone matches (normalized)
        if patient and patient.phone:
            if norm_phone(patient.phone) == norm_input_phone:
                session['patient_id'] = patient.id
                flash(f'Welcome back, {patient.first_name}!', 'success')
                return redirect(url_for('patient_portal_dashboard'))
        
        # No valid match
        flash('Invalid Patient ID or phone number. Please check and try again.', 'danger')
    
    return render_template('patient_login.html')


@app.route('/discharged-portal', methods=['GET', 'POST'])
def discharged_portal():
    """Discharged patient portal - redirects to patient login"""
    return redirect(url_for('patient_login'))


@app.route('/patient-portal/dashboard')
@patient_login_required
def patient_portal_dashboard():
    """Main dashboard for the patient portal"""
    patient = get_logged_in_patient()
    if not patient:
        session.pop('patient_id', None)
        return redirect(url_for('patient_login'))
    
    # helper for upcoming appointments
    upcoming_appointments_count = AppointmentRequest.query.filter(
        AppointmentRequest.patient_id == patient.id,
        AppointmentRequest.status.in_(['pending', 'confirmed']),
        AppointmentRequest.preferred_date >= datetime.now().date()
    ).count()

    # helper for active meds
    active_meds_count = Medication.query.filter_by(patient_id=patient.id, is_active=True).count()

    # helper for lab reports (assuming LabReport model exists, if not catch error)
    lab_reports_count = 0
    try:
        lab_reports_count = LabReport.query.filter_by(patient_id=patient.id).count()
    except Exception:
        pass # LabReport might not exist yet

    # latest vital
    latest_vital = patient.vitals.order_by(VitalSign.recorded_at.desc()).first()

    # Recent Activity (Mockup aggregation)
    recent_activity = []
    
    # 1. Recent Meds
    recent_meds = Medication.query.filter_by(patient_id=patient.id).order_by(Medication.start_date.desc()).limit(3).all()
    for m in recent_meds:
        recent_activity.append({
            'type': 'medication',
            'title': f'Started {m.name}',
            'description': f'Dosage: {m.dosage}',
            'time': m.start_date.strftime('%Y-%m-%d'),
            'timestamp': datetime.combine(m.start_date, datetime.min.time())
        })

    # 2. Recent Vitals
    recent_vitals = patient.vitals.order_by(VitalSign.recorded_at.desc()).limit(3).all()
    for v in recent_vitals:
        recent_activity.append({
            'type': 'vital',
            'title': 'Vitals Recorded',
            'description': f'BP: {v.blood_pressure_systolic}/{v.blood_pressure_diastolic}',
            'time': v.recorded_at.strftime('%Y-%m-%d %H:%M'),
            'timestamp': v.recorded_at
        })
    
    # Sort by timestamp desc
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:5]

    return render_template('patient_portal_dashboard.html',
        patient=patient,
        active_meds_count=active_meds_count,
        upcoming_appointments_count=upcoming_appointments_count,
        latest_vital=latest_vital,
        lab_reports_count=lab_reports_count,
        recent_activity=recent_activity
    )

@app.route('/patient-portal/history')
@patient_login_required
def patient_portal_history():
    patient = get_logged_in_patient()
    notes = DoctorNote.query.filter_by(patient_id=patient.id).order_by(DoctorNote.created_at.desc()).all()
    # treatments could be added if we create a model, for now just notes
    return render_template('patient_portal_history.html', patient=patient, notes=notes, treatments=[])

@app.route('/patient-portal/medications')
@patient_login_required
def patient_portal_medications():
    patient = get_logged_in_patient()
    medications = Medication.query.filter_by(patient_id=patient.id).order_by(Medication.start_date.desc()).all()
    return render_template('patient_portal_medications.html', patient=patient, medications=medications)

@app.route('/patient-portal/appointments')
@patient_login_required
def patient_portal_appointments():
    patient = get_logged_in_patient()
    appointments = AppointmentRequest.query.filter_by(patient_id=patient.id).order_by(AppointmentRequest.created_at.desc()).all()
    doctors = StaffMember.query.filter_by(role='doctor').all()
    return render_template('patient_portal_appointments.html', patient=patient, appointments=appointments, doctors=doctors)

@app.route('/patient-portal/chat')
@patient_login_required
def patient_portal_chat():
    patient = get_logged_in_patient()
    chat_history = ChatMessage.query.filter_by(patient_id=patient.id).order_by(ChatMessage.created_at.asc()).all()
    return render_template('patient_portal_chat.html', patient=patient, chat_history=chat_history)

@app.route('/patient-logout')
def patient_logout():
    session.pop('patient_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('patient_login'))


# ===== PATIENT API ENDPOINTS =====

@app.route('/api/patient/<int:patient_id>/chat', methods=['POST'])
def patient_chat(patient_id):
    """Chat API with multi-language support"""
    from app import gemini_model
    import json
    
    # Authorization
    staff = get_staff_user()
    if not staff and session.get('patient_id') != patient_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    new_chat_flag = data.get('new_chat', False)
    language = data.get('language', 'en').lower()
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    patient = Patient.query.get_or_404(patient_id)
    
    # Store user message
    user_msg = ChatMessage(patient_id=patient_id, role='patient', message=user_message, language=language)
    db.session.add(user_msg)
    db.session.commit()
    
    # Try Gemini first if available
    ai_response = None
    if gemini_model:
        try:
            recent_chat = ChatMessage.query.filter_by(patient_id=patient_id).order_by(ChatMessage.created_at.desc()).limit(6).all()
            recent_chat.reverse()
            
            lang_name = {'en':'English', 'hi':'Hindi', 'ta':'Tamil', 'te':'Telugu', 'ml':'Malayalam'}.get(language, 'English')
            
            context = f"Patient: {patient.full_name}. Diagnosis: {patient.diagnosis}. "
            lv = patient.vitals.order_by(VitalSign.recorded_at.desc()).first()
            if lv:
                context += f"Latest Vitals: HR {lv.heart_rate}, BP {lv.blood_pressure_systolic}/{lv.blood_pressure_diastolic}, SpO2 {lv.oxygen_saturation}%. "
            
            active_meds = Medication.query.filter_by(patient_id=patient_id, is_active=True).all()
            if active_meds:
                med_list = [f"{m.name} ({m.dosage}, {m.frequency})" for m in active_meds]
                context += f"Active Meds: {', '.join(med_list)}. "
                
            context += f"Reply in {lang_name}. Be concise, empathetic. If emergency suspected, advise ER immediately."
            
            messages = [m.message for m in recent_chat]
            messages.append(f"{context} Patient: {user_message}")
            
            response = gemini_model.generate_content(messages)
            if hasattr(response, 'text') and response.text:
                ai_response = response.text
        except Exception as e:
            logging.debug(f"Gemini unavailable, using fallback: {str(e)[:80]}")
    
    # Use fallback if Gemini not available or failed
    if not ai_response:
        ai_response = generate_fallback_response(patient, user_message, language)
    
    try:
        ai_msg = ChatMessage(patient_id=patient_id, role='assistant', message=ai_response, language=language)
        db.session.add(ai_msg)
        db.session.commit()
        return jsonify({'role': 'assistant', 'message': ai_response, 'language': language, 'message_id': ai_msg.id})
    except:
        db.session.rollback()
        return jsonify({'role': 'assistant', 'message': ai_response, 'language': language})

@app.route('/api/chat/feedback/<int:message_id>', methods=['POST'])
def chat_feedback(message_id):
    """Record helpfulness feedback for a chat message"""
    # Auth check (staff or patient owner)
    staff = get_staff_user()
    data = request.get_json() or {}
    
    msg = ChatMessage.query.get_or_404(message_id)
    
    # Simple ownership check
    if not staff and session.get('patient_id') != msg.patient_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    is_helpful = data.get('is_helpful')
    if is_helpful is not None:
        msg.is_helpful = bool(is_helpful)
        
    feedback_text = data.get('feedback_text')
    if feedback_text:
        msg.feedback_text = feedback_text
        
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/patient/<int:patient_id>/clear-history', methods=['POST'])
def patient_clear_history(patient_id):
    staff = get_staff_user()
    if not staff and session.get('patient_id') != patient_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    ChatMessage.query.filter_by(patient_id=patient_id).delete()
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/patient/<int:patient_id>/book-appointment', methods=['POST'])
def patient_book_appointment(patient_id):
    """Book appointment with intelligent doctor allocation"""
    from appointment_routing import allocate_appointment
    
    staff = get_staff_user()
    patient_in_session = session.get('patient_id')
    if not staff and patient_in_session != patient_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json() or {}
    try:
        pref_date = datetime.fromisoformat(data.get('preferred_date')) if data.get('preferred_date') else None
    except:
        pref_date = None
    
    # Create appointment with all new fields
    appt = AppointmentRequest(
        patient_id=patient_id,
        preferred_date=pref_date,
        preferred_time=data.get('preferred_time'),
        doctor_id=data.get('doctor_id'),
        notes=data.get('notes', ''),
        appointment_type=data.get('appointment_type', 'routine'),
        department=data.get('department', ''),
        language_preference=data.get('language', 'en'),
        urgency=data.get('urgency', 'normal'),
        source=data.get('source', 'patient_portal'),
        status='pending'
    )
    db.session.add(appt)
    db.session.commit()
    
    # Try intelligent doctor allocation if no doctor specified
    if not appt.doctor_id and appt.appointment_type != 'emergency':
        allocated_doctor = allocate_appointment(appt)
        if allocated_doctor:
            appt.status = 'confirmed'
            db.session.commit()
    
    return jsonify({
        'ok': True, 
        'appointment_id': appt.id,
        'status': appt.status,
        'allocated_by_system': appt.allocated_by_system,
        'routing_score': float(appt.routing_score) if appt.routing_score else None
    })


# ===== NEW APPOINTMENT SYSTEM ENDPOINTS =====

@app.route('/api/appointment/translations/<language>', methods=['GET'])
def get_appointment_translations(language='en'):
    """Get appointment form translations"""
    from appointment_routing import get_appointment_translations
    
    translations = get_appointment_translations(language)
    return jsonify(translations)


@app.route('/api/patient/<int:patient_id>/medical-records', methods=['GET'])
@patient_login_required
def get_patient_medical_records(patient_id):
    """Get comprehensive medical records including notes, treatments, vitals, medications, alerts"""
    
    # Verify authorization
    patient = Patient.query.get_or_404(patient_id)
    if session.get('patient_id') != patient_id:
        staff = get_staff_user()
        if not staff or (staff.id != patient.assigned_doctor_id and staff.id != patient.assigned_nurse_id):
            return jsonify({'error': 'Unauthorized'}), 401
    
    # Get doctor notes
    doctor_notes = DoctorNote.query.filter_by(patient_id=patient_id).order_by(
        DoctorNote.created_at.desc()
    ).all()
    
    notes_data = [{
        'id': note.id,
        'type': note.note_type,
        'doctor': note.doctor.full_name if note.doctor else 'Unknown',
        'subjective': note.subjective,
        'objective': note.objective,
        'assessment': note.assessment,
        'plan': note.plan,
        'date': note.created_at.isoformat()
    } for note in doctor_notes]
    
    # Get treatment logs
    treatments = TreatmentLog.query.filter_by(patient_id=patient_id).order_by(
        TreatmentLog.performed_at.desc()
    ).all()
    
    treatments_data = [{
        'id': treatment.id,
        'type': treatment.treatment_type,
        'description': treatment.description,
        'notes': treatment.notes,
        'staff': treatment.staff.full_name if treatment.staff else 'Unknown',
        'date': treatment.performed_at.isoformat()
    } for treatment in treatments]
    
    # Get vitals history (last 30)
    vitals = VitalSign.query.filter_by(patient_id=patient_id).order_by(
        VitalSign.recorded_at.desc()
    ).limit(30).all()
    
    vitals_data = [{
        'id': vital.id,
        'heart_rate': vital.heart_rate,
        'blood_pressure_systolic': vital.blood_pressure_systolic,
        'blood_pressure_diastolic': vital.blood_pressure_diastolic,
        'oxygen_saturation': vital.oxygen_saturation,
        'temperature': vital.temperature,
        'respiratory_rate': vital.respiratory_rate,
        'status': vital.status,
        'date': vital.recorded_at.isoformat()
    } for vital in vitals]
    
    # Get medications
    medications = Medication.query.filter_by(patient_id=patient_id).all()
    
    meds_data = [{
        'id': med.id,
        'name': med.name,
        'dosage': med.dosage,
        'frequency': med.frequency,
        'route': med.route,
        'is_active': med.is_active,
        'start_date': med.start_date.isoformat() if med.start_date else None,
        'end_date': med.end_date.isoformat() if med.end_date else None,
        'prescribed_by': med.prescribed_by.full_name if med.prescribed_by else 'Unknown',
        'notes': med.notes
    } for med in medications]
    
    # Get alerts
    alerts = Alert.query.filter_by(patient_id=patient_id).order_by(
        Alert.created_at.desc()
    ).limit(20).all()
    
    alerts_data = [{
        'id': alert.id,
        'type': alert.alert_type,
        'severity': alert.severity,
        'title': alert.title,
        'message': alert.message,
        'is_acknowledged': alert.is_acknowledged,
        'date': alert.created_at.isoformat()
    } for alert in alerts]
    
    return jsonify({
        'patient': {
            'id': patient.id,
            'name': patient.full_name,
            'diagnosis': patient.diagnosis,
            'status': patient.status,
            'room': patient.room_number,
            'bed': patient.bed_number
        },
        'doctor_notes': notes_data,
        'treatments': treatments_data,
        'vitals_history': vitals_data,
        'medications': meds_data,
        'alerts': alerts_data
    })


@app.route('/api/landing-page/book-appointment', methods=['POST'])
def landing_page_book_appointment():
    """Book appointment directly from landing page (for new/guest patients)"""
    from appointment_routing import allocate_appointment
    
    data = request.get_json() or {}
    
    # For landing page bookings, we might not have a patient ID yet
    # Try to find or create patient
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    
    if not (phone or email) or not (first_name and last_name):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Try to find existing patient
    patient = None
    if phone:
        patient = Patient.query.filter_by(phone=phone).first()
    if not patient and email:
        patient = Patient.query.filter_by(email=email).first()
    
    # If patient doesn't exist, create new patient record
    if not patient:
        try:
            # Generate patient ID
            last_patient = Patient.query.order_by(Patient.patient_id.desc()).first()
            if last_patient:
                patient_num = int(last_patient.patient_id.replace('PAT', '')) + 1
            else:
                patient_num = 1
            
            patient = Patient(
                patient_id=f'PAT{patient_num:06d}',
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                date_of_birth=datetime.strptime(data.get('dob', '2000-01-01'), '%Y-%m-%d').date() if data.get('dob') else datetime(2000, 1, 1).date(),
                gender=data.get('gender', 'Other'),
                status='inquiry',
                department=data.get('department', 'General')
            )
            db.session.add(patient)
            db.session.commit()
        except Exception as e:
            logging.error(f"Error creating patient: {str(e)}")
            return jsonify({'error': 'Could not create patient record'}), 400
    
    # Create appointment request
    try:
        pref_date = datetime.fromisoformat(data.get('preferred_date')) if data.get('preferred_date') else None
    except:
        pref_date = None
    
    appt = AppointmentRequest(
        patient_id=patient.id,
        preferred_date=pref_date,
        preferred_time=data.get('preferred_time'),
        notes=data.get('reason', ''),
        appointment_type=data.get('appointment_type', 'consultation'),
        department=data.get('department', 'General'),
        language_preference=data.get('language', 'en'),
        urgency=data.get('urgency', 'normal'),
        source='landing_page',
        status='pending'
    )
    db.session.add(appt)
    db.session.commit()
    
    # Try intelligent doctor allocation
    allocated_doctor = allocate_appointment(appt)
    if allocated_doctor:
        appt.status = 'confirmed'
        db.session.commit()
    
    return jsonify({
        'ok': True,
        'appointment_id': appt.id,
        'patient_id': patient.id,
        'patient_code': patient.patient_id,
        'status': appt.status,
        'message': 'Appointment request submitted. You will receive a confirmation.'
    })


@app.route('/patient-portal/medical-records')
@patient_login_required
def patient_medical_records_page():
    """Medical records page for patient portal"""
    patient = get_logged_in_patient()
    
    # Get all records
    doctor_notes = DoctorNote.query.filter_by(patient_id=patient.id).order_by(DoctorNote.created_at.desc()).all()
    treatments = TreatmentLog.query.filter_by(patient_id=patient.id).order_by(TreatmentLog.performed_at.desc()).all()
    vitals = VitalSign.query.filter_by(patient_id=patient.id).order_by(VitalSign.recorded_at.desc()).limit(50).all()
    medications = Medication.query.filter_by(patient_id=patient.id).all()
    alerts = Alert.query.filter_by(patient_id=patient.id).order_by(Alert.created_at.desc()).limit(20).all()
    
    return render_template('patient_portal_medical_records.html',
                         patient=patient,
                         doctor_notes=doctor_notes,
                         treatments=treatments,
                         vitals=vitals,
                         medications=medications,
                         alerts=alerts)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


# ===== NURSE DASHBOARD MODIFICATIONS =====

@app.route('/admin/wards', methods=['GET', 'POST'])
@staff_login_required
@admin_required
def admin_wards():
    staff = get_staff_user()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name')
            capacity = request.form.get('capacity')
            floor = request.form.get('floor')
            
            if Ward.query.filter_by(name=name).first():
                flash('Ward with this name already exists.', 'danger')
            else:
                new_ward = Ward(name=name, capacity=capacity, floor=floor)
                db.session.add(new_ward)
                db.session.commit()
                flash('Ward created successfully.', 'success')
                
        elif action == 'edit':
            ward_id = request.form.get('ward_id')
            ward = Ward.query.get_or_404(ward_id)
            ward.name = request.form.get('name')
            ward.capacity = request.form.get('capacity')
            ward.floor = request.form.get('floor')
            head_nurse_id = request.form.get('head_nurse_id')
            if head_nurse_id:
                ward.head_nurse_id = head_nurse_id
            db.session.commit()
            flash('Ward updated successfully.', 'success')
            
        return redirect(url_for('admin_wards'))

    wards = Ward.query.order_by(Ward.name).all()
    
    # Calculate occupancy for each ward
    ward_stats = []
    for w in wards:
        occupancy = Patient.query.filter_by(department=w.name, status='admitted').count()
        ward_stats.append({
            'ward': w,
            'occupancy': occupancy,
            'percent': int((occupancy / w.capacity) * 100) if w.capacity > 0 else 0
        })
        
    nurses = StaffMember.query.filter_by(role='nurse').all()
    return render_template('admin/wards.html', staff=staff, ward_stats=ward_stats, nurses=nurses)


@app.route('/admin/assign-staff', methods=['GET', 'POST'])
@staff_login_required
@admin_required
def admin_assign_staff():
    staff_user = get_staff_user()
    
    if request.method == 'POST':
        staff_id = request.form.get('staff_id')
        new_dept = request.form.get('department')
        
        target_staff = StaffMember.query.get(staff_id)
        if target_staff:
            target_staff.department = new_dept
            db.session.commit()
            flash(f'Updated {target_staff.full_name} to {new_dept}.', 'success')
        else:
            flash('Staff member not found.', 'danger')
            
        return redirect(url_for('admin_assign_staff'))

    all_staff = StaffMember.query.filter(StaffMember.role != 'admin').order_by(StaffMember.role, StaffMember.last_name).all()
    wards = Ward.query.order_by(Ward.name).all()
    
    return render_template('admin/staff_assignment.html', staff=staff_user, all_staff=all_staff, wards=wards)
    """Look up patient by ID for modification (returns partial HTML)"""
    staff = get_staff_user()
    patient_id_str = request.args.get('patient_id', '').strip()
    
    # Try exact match first, then case-insensitive
    patient = Patient.query.filter_by(patient_id=patient_id_str).first()
    if not patient:
         patient = Patient.query.filter(Patient.patient_id.ilike(patient_id_str)).first()
            
    if not patient:
        return jsonify({'error': 'Patient ID not found.'}), 404
        
    # Audit View (Nurse Lookup)
    try:
        log = AuditLog(
            action='VIEW',
            table_name='patients',
            record_id=patient.id,
            field_name='all',
            old_value=None,
            new_value='lookup_for_edit',
            changed_by_id=staff.id
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logging.error(f"Audit Log Error: {e}")
        
    return render_template('nurse/edit_patient_partial.html', staff=staff, patient=patient)


@app.route('/nurse/patient-lookup', methods=['GET'])
@staff_login_required
@role_required('nurse', 'admin')
def nurse_patient_lookup():
    """AJAX endpoint to lookup patient and return edit form"""
    patient_id = request.args.get('patient_id', '').strip()
    
    if not patient_id:
        return jsonify({'error': 'Patient ID required'}), 400
    
    patient = Patient.query.filter_by(patient_id=patient_id).first()
    
    if not patient:
        return jsonify({'error': f'Patient {patient_id} not found'}), 404
    
    # Get existing medications
    current_meds = Medication.query.filter_by(patient_id=patient.id, is_active=True).all()
    
    # Return HTML for edit form
    html = f'''
    <div class="alert alert-info">
        <strong>{patient.full_name}</strong> - {patient.patient_id} | Room {patient.room_number or '-'} | Status: <span class="badge bg-primary">{patient.status.upper()}</span>
    </div>
    
    <form class="row g-3" id="patientEditForm" data-patient-id="{patient.id}">
        <div class="col-md-6">
            <label for="diagnosis" class="form-label">Diagnosis</label>
            <textarea class="form-control" id="diagnosis" name="diagnosis" rows="2">{patient.diagnosis or ''}</textarea>
        </div>
        
        <div class="col-md-6">
            <label for="notes" class="form-label">Medical Notes</label>
            <textarea class="form-control" id="notes" name="notes" rows="2">{patient.notes or ''}</textarea>
        </div>
        
        <div class="col-md-3">
            <label for="room_number" class="form-label">Room Number</label>
            <input type="text" class="form-control" id="room_number" name="room_number" value="{patient.room_number or ''}">
        </div>
        
        <div class="col-md-3">
            <label for="bed_number" class="form-label">Bed Number</label>
            <input type="text" class="form-control" id="bed_number" name="bed_number" value="{patient.bed_number or ''}">
        </div>
        
        <div class="col-md-6">
            <label for="status" class="form-label">Status</label>
            <select class="form-select" id="status" name="status">
                <option value="admitted" {'selected' if patient.status == 'admitted' else ''}>Admitted</option>
                <option value="icu" {'selected' if patient.status == 'icu' else ''}>ICU</option>
                <option value="emergency" {'selected' if patient.status == 'emergency' else ''}>Emergency</option>
                <option value="discharged" {'selected' if patient.status == 'discharged' else ''}>Discharged</option>
            </select>
        </div>
        
        <hr class="col-12">
        
        <!-- Medication Management Section -->
        <div class="col-12">
            <h6 class="mb-3"><i class="bi bi-capsule me-2"></i>Medication Management</h6>
        </div>
        
        <div class="col-md-4">
            <label for="medication_name" class="form-label">Medicine Name</label>
            <input type="text" class="form-control" id="medication_name" placeholder="e.g., Aspirin, Ibuprofen">
        </div>
        
        <div class="col-md-4">
            <label for="medication_dosage" class="form-label">Dosage</label>
            <select class="form-select" id="medication_dosage">
                <option value="">-- Select Dosage --</option>
                <option value="5mg">5 mg</option>
                <option value="10mg">10 mg</option>
                <option value="25mg">25 mg</option>
                <option value="50mg">50 mg</option>
                <option value="100mg">100 mg</option>
                <option value="250mg">250 mg</option>
                <option value="500mg">500 mg</option>
                <option value="1000mg">1000 mg</option>
                <option value="250ml">250 ml</option>
                <option value="500ml">500 ml</option>
                <option value="1 unit">1 unit</option>
                <option value="2 units">2 units</option>
                <option value="5 units">5 units</option>
                <option value="10 units">10 units</option>
                <option value="1 tablet">1 tablet</option>
                <option value="2 tablets">2 tablets</option>
                <option value="0.5 tablet">0.5 tablet</option>
            </select>
        </div>
        
        <div class="col-md-4">
            <label for="medication_timing" class="form-label">Timing / Frequency</label>
            <select class="form-select" id="medication_timing">
                <option value="">-- Select Timing --</option>
                <option value="Once daily">Once daily</option>
                <option value="Twice daily">Twice daily (Morning & Evening)</option>
                <option value="Three times daily">Three times daily (Morning, Afternoon, Evening)</option>
                <option value="Four times daily">Four times daily</option>
                <option value="Every 4 hours">Every 4 hours</option>
                <option value="Every 6 hours">Every 6 hours</option>
                <option value="Every 8 hours">Every 8 hours</option>
                <option value="Every 12 hours">Every 12 hours</option>
                <option value="As needed">As needed</option>
            </select>
        </div>
        
        <div class="col-md-4">
            <label for="medication_route" class="form-label">Route</label>
            <select class="form-select" id="medication_route">
                <option value="oral" selected>Oral</option>
                <option value="intravenous">Intravenous (IV)</option>
                <option value="intramuscular">Intramuscular (IM)</option>
                <option value="topical">Topical</option>
                <option value="sublingual">Sublingual</option>
                <option value="inhalation">Inhalation</option>
            </select>
        </div>
        
        <div class="col-md-8">
            <label for="medication_notes" class="form-label">Notes</label>
            <input type="text" class="form-control" id="medication_notes" placeholder="e.g., with food, after meals">
        </div>
        
        <div class="col-12">
            <button type="button" class="btn btn-info" id="addMedicationBtn">
                <i class="bi bi-plus-circle me-2"></i>Add Medication
            </button>
        </div>
        
        <!-- Current Medications List -->
        <div class="col-12" id="currentMedsSection" style="display: {'block' if current_meds else 'none'};">
            <h6 class="mt-3 mb-3"><i class="bi bi-list-check me-2"></i>Current Medications</h6>
            <div class="table-responsive">
                <table class="table table-sm table-hover" id="currentMedicationsTable">
                    <thead class="table-light">
                        <tr>
                            <th>Medicine</th>
                            <th>Dosage</th>
                            <th>Frequency</th>
                            <th>Route</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="currentMedsBody">
    '''
    
    for med in current_meds:
        html += f'''
                        <tr data-med-id="{med.id}">
                            <td><strong>{med.name}</strong></td>
                            <td>{med.dosage}</td>
                            <td>{med.frequency}</td>
                            <td>{med.route or 'oral'}</td>
                            <td>
                                <button type="button" class="btn btn-sm btn-danger remove-med-btn" data-med-id="{med.id}">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>
        '''
    
    html += f'''
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="col-12">
            <button type="submit" class="btn btn-success">
                <i class="bi bi-check-circle me-2"></i>Save Changes
            </button>
            <button type="reset" class="btn btn-secondary ms-2">
                <i class="bi bi-x-circle me-2"></i>Reset
            </button>
        </div>
    </form>
    
    <script>
        // Store medications being added in session
        let newMedications = [];
        
        document.getElementById('patientEditForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            const patientId = this.getAttribute('data-patient-id');
            const formData = new FormData(this);
            
            // Add new medications to form data
            formData.append('new_medications', JSON.stringify(newMedications));
            
            fetch(`/nurse/update-patient/${{patientId}}`, {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert('Patient record and medications updated successfully!');
                    location.reload();
                }} else {{
                    alert('Error: ' + (data.error || 'Unknown error'));
                }}
            }})
            .catch(error => {{
                alert('Error updating patient: ' + error.message);
            }});
        }});
        
        // Add medication button handler
        document.getElementById('addMedicationBtn').addEventListener('click', function() {{
            const medName = document.getElementById('medication_name').value.trim();
            const medDosage = document.getElementById('medication_dosage').value;
            const medTiming = document.getElementById('medication_timing').value;
            const medRoute = document.getElementById('medication_route').value;
            const medNotes = document.getElementById('medication_notes').value.trim();
            
            if (!medName) {{
                alert('Please enter medicine name');
                return;
            }}
            if (!medDosage) {{
                alert('Please select dosage');
                return;
            }}
            if (!medTiming) {{
                alert('Please select timing/frequency');
                return;
            }}
            
            // Add to list
            newMedications.push({{
                name: medName,
                dosage: medDosage,
                frequency: medTiming,
                route: medRoute,
                notes: medNotes
            }});
            
            // Add row to table
            const tbody = document.getElementById('currentMedsBody');
            const tr = document.createElement('tr');
            tr.classList.add('table-success');
            tr.innerHTML = `
                <td><strong>${{medName}}</strong> <span class="badge bg-success ms-2">NEW</span></td>
                <td>${{medDosage}}</td>
                <td>${{medTiming}}</td>
                <td>${{medRoute}}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-danger remove-new-med-btn">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            
            // Remove button handler
            tr.querySelector('.remove-new-med-btn').addEventListener('click', function() {{
                tr.remove();
                const idx = newMedications.findIndex(m => m.name === medName && m.dosage === medDosage);
                if (idx > -1) newMedications.splice(idx, 1);
                if (newMedications.length === 0 && document.querySelectorAll('#currentMedsBody tr').length === 0) {{
                    document.getElementById('currentMedsSection').style.display = 'none';
                }}
            }});
            
            tbody.appendChild(tr);
            document.getElementById('currentMedsSection').style.display = 'block';
            
            // Clear form
            document.getElementById('medication_name').value = '';
            document.getElementById('medication_dosage').value = '';
            document.getElementById('medication_timing').value = '';
            document.getElementById('medication_route').value = 'oral';
            document.getElementById('medication_notes').value = '';
            document.getElementById('medication_name').focus();
        }});
        
        // Remove existing medications
        document.querySelectorAll('.remove-med-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                const medId = this.getAttribute('data-med-id');
                fetch(`/api/medication/${{medId}}/deactivate`, {{
                    method: 'POST',
                    headers: {{'X-Requested-With': 'XMLHttpRequest'}}
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        this.closest('tr').remove();
                        if (document.querySelectorAll('#currentMedsBody tr').length === 0 && newMedications.length === 0) {{
                            document.getElementById('currentMedsSection').style.display = 'none';
                        }}
                    }} else {{
                        alert('Error removing medication');
                    }}
                }});
    </script>
    '''
    
    return html


@app.route('/nurse/update-patient/<int:patient_id>', methods=['POST'])
@staff_login_required
@role_required('nurse', 'admin')
def update_patient_record(patient_id):
    """Update patient record with audit trail and medications"""
    staff = get_staff_user()
    patient = Patient.query.get_or_404(patient_id)
    
    # Fields allowed to edit
    editable_fields = ['diagnosis', 'notes', 'room_number', 'bed_number', 'status']
    
    changes_made = False
    
    try:
        # Update existing fields
        for field in editable_fields:
            new_value = request.form.get(field)
            if new_value is not None:
                new_value = new_value.strip()
                old_value = getattr(patient, field) or ''
                
                # Check if changed (handling None vs empty string)
                if str(old_value) != str(new_value):
                    # Record change
                    setattr(patient, field, new_value)
                    
                    # Create Audit Log
                    audit = AuditLog(
                        action='UPDATE',
                        table_name='patients',
                        record_id=patient.id,
                        field_name=field,
                        old_value=str(old_value),
                        new_value=new_value,
                        changed_by_id=staff.id
                    )
                    db.session.add(audit)
                    changes_made = True
        
        # Handle new medications
        new_meds_json = request.form.get('new_medications', '[]')
        try:
            new_meds = json.loads(new_meds_json)
            for med_data in new_meds:
                if med_data.get('name') and med_data.get('dosage') and med_data.get('frequency'):
                    # Calculate next_due based on frequency
                    freq_hours = {
                        'Once daily': 24,
                        'Twice daily': 12,
                        'Three times daily': 8,
                        'Four times daily': 6,
                        'Every 4 hours': 4,
                        'Every 6 hours': 6,
                        'Every 8 hours': 8,
                        'Every 12 hours': 12,
                        'As needed': 0
                    }.get(med_data.get('frequency'), 24)
                    
                    from datetime import timedelta
                    next_due = datetime.now() + timedelta(hours=freq_hours) if freq_hours > 0 else None
                    
                    medication = Medication(
                        patient_id=patient_id,
                        name=med_data.get('name'),
                        dosage=med_data.get('dosage'),
                        frequency=med_data.get('frequency'),
                        route=med_data.get('route', 'oral'),
                        start_date=datetime.now(),
                        next_due=next_due,
                        notes=med_data.get('notes', ''),
                        is_active=True
                    )
                    db.session.add(medication)
                    changes_made = True
        except (json.JSONDecodeError, AttributeError):
            logging.warning(f"Invalid medications JSON for patient {patient_id}")
        
        if changes_made:
            patient.updated_at = datetime.now()
            db.session.commit()
            
            # Create notification for assigned nurse if exists
            if patient.assigned_nurse_id and patient.assigned_nurse_id != staff.id:
                from models import Notification
                notification = Notification(
                    recipient_id=patient.assigned_nurse_id,
                    notification_type='patient_update',
                    title=f'Patient Record Updated: {patient.full_name}',
                    message=f'{staff.full_name} updated patient record for {patient.full_name} (Room {patient.room_number}). New status: {patient.status.upper()}',
                    patient_id=patient.id,
                    is_read=False,
                    is_acknowledged=False
                )
                db.session.add(notification)
                db.session.commit()
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': True, 'message': 'No changes detected'})
            
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating patient {patient_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/medication/<int:medication_id>/deactivate', methods=['POST'])
@staff_login_required
def deactivate_medication(medication_id):
    """Deactivate a medication"""
    try:
        medication = Medication.query.get_or_404(medication_id)
        medication.is_active = False
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deactivating medication {medication_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/nurse/notifications')
@staff_login_required
@role_required('nurse', 'admin')
def get_nurse_notifications():
    """Fetch unacknowledged notifications for the current nurse"""
    staff = get_staff_user()
    
    # Get unacknowledged notifications for this nurse
    from models import Notification
    notifications = Notification.query.filter(
        Notification.recipient_id == staff.id,
        Notification.is_acknowledged == False
    ).order_by(Notification.created_at.desc()).all()
    
    notification_list = []
    for notif in notifications:
        notification_list.append({
            'id': notif.id,
            'type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'patient_id': notif.patient_id,
            'patient_name': notif.patient.full_name if notif.patient else 'N/A',
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'count': len(notification_list),
        'notifications': notification_list
    }), 200


@app.route('/api/notification/<int:notification_id>/acknowledge', methods=['POST'])
@staff_login_required
def acknowledge_notification(notification_id):
    """Mark notification as acknowledged"""
    try:
        from models import Notification
        notification = Notification.query.get_or_404(notification_id)
        notification.is_acknowledged = True
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error acknowledging notification {notification_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/notification/<int:notification_id>/read', methods=['POST'])
@staff_login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        from models import Notification
        notification = Notification.query.get_or_404(notification_id)
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error marking notification read {notification_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/book-appointment-public', methods=['POST'])
def book_appointment_public():
    """Handle public appointment requests from landing page"""
    try:
        # 1. Extract form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        dob_str = request.form.get('date_of_birth')
        gender = request.form.get('gender')
        pref_date_str = request.form.get('preferred_date')
        pref_time = request.form.get('preferred_time')
        problem = request.form.get('problem_description', '')

        if not all([first_name, last_name, dob_str, gender, pref_date_str, pref_time]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        # 2. Find or Create Patient
        # Simple matching logic: email or phone
        patient = None
        if email:
            patient = Patient.query.filter_by(email=email).first()
        if not patient and phone:
            patient = Patient.query.filter_by(phone=phone).first()
            
        if not patient:
            # Generate new Patient ID
            last_patient = Patient.query.order_by(Patient.id.desc()).first()
            next_num = 1
            if last_patient and last_patient.patient_id and last_patient.patient_id.startswith('PAT'):
                try:
                    next_num = int(last_patient.patient_id[3:]) + 1
                except ValueError:
                    pass
            
            new_patient_id = f"PAT{str(next_num).zfill(4)}"
            
            # Create new patient
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for Date of Birth.', 'danger')
                return redirect(url_for('index'))

            patient = Patient(
                patient_id=new_patient_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                date_of_birth=dob,
                gender=gender,
                status='outpatient', # New status for these patients
                diagnosis=problem # Initial diagnosis/complaint
            )
            db.session.add(patient)
            db.session.commit()
            logging.info(f"Created new patient {new_patient_id} for appointment request.")

        # 3. Create Appointment Request
        try:
            pref_date = datetime.strptime(pref_date_str, '%Y-%m-%d')
            # Combine if strictly needed, but model has separate fields
        except ValueError:
            flash('Invalid date format for Appointment Date.', 'danger')
            return redirect(url_for('index'))

        appt = AppointmentRequest(
            patient_id=patient.id,
            preferred_date=pref_date,
            preferred_time=pref_time,
            notes=problem,
            status='pending',
            source='landing_page',
            appointment_type='consultation'
        )
        db.session.add(appt)
        db.session.commit()

        flash('Your appointment request has been submitted successfully! We will contact you shortly.', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in book_appointment_public: {e}")
        flash('An error occurred while processing your request. Please try again.', 'danger')
        return redirect(url_for('index'))
