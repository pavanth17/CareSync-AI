import json
import logging
from datetime import datetime
from functools import wraps
from flask import render_template, redirect, url_for, request, flash, session, Response, jsonify
from flask_login import current_user
from app import app, db
from models import StaffMember, Patient, VitalSign, Alert, Medication, TreatmentLog, MedicationAdministration, Shift, ShiftHandoff, DoctorNote, RiskAssessment, ChatMessage, LabReport, AppointmentRequest
# Removed Replit-specific auth integration; using local session-based auth instead
from synthetic_data import initialize_synthetic_data
from vital_simulator import update_patient_vitals, get_and_clear_new_alerts, get_live_patient_vitals
from predictive_analytics import risk_predictor, analyze_all_patients

logging.basicConfig(level=logging.DEBUG)

# Replit auth blueprint removed for local hosting


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
            flash(f'Welcome back, {staff.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Staff ID / email or password.', 'danger')
    
    return render_template('index.html')


@app.route('/logout')
def staff_logout():
    session.pop('staff_id', None)
    session.pop('staff_role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


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
        critical_alerts=critical_alerts
    )


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


@app.route('/api/vitals/stream')
@staff_login_required
def vitals_stream():
    def generate():
        import time
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
    analysis = risk_predictor.analyze_patient_risk(patient_id)
    return jsonify(analysis)


@app.route('/api/risk-analysis/all')
@staff_login_required
def api_all_risk_analysis():
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


@app.route('/patient/<int:patient_id>/add-note', methods=['GET', 'POST'])
@staff_login_required
@role_required('doctor', 'admin')
def add_doctor_note(patient_id):
    staff = get_staff_user()
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        note_type = request.form.get('note_type', 'progress')
        subjective = request.form.get('subjective', '').strip()
        objective = request.form.get('objective', '').strip()
        assessment = request.form.get('assessment', '').strip()
        plan = request.form.get('plan', '').strip()
        
        note = DoctorNote(
            patient_id=patient_id,
            doctor_id=staff.id,
            note_type=note_type,
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan
        )
        db.session.add(note)
        db.session.commit()
        
        flash('Doctor note added successfully.', 'success')
        return redirect(url_for('patient_history', patient_id=patient_id))
    
    return render_template('add_note.html', staff=staff, patient=patient)


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


# ===== DISCHARGED PATIENT POST-CARE PORTAL =====

@app.route('/discharged-portal', methods=['GET', 'POST'])
def discharged_portal():
    """Discharged patient login portal"""
    if request.method == 'POST':
        patient_id_str = request.form.get('patient_id', '').strip().upper()
        phone = request.form.get('phone', '').strip()

        # Normalize phone by removing non-digit characters for matching
        def norm_phone(p):
            return ''.join([c for c in (p or '') if c.isdigit()])

        norm_input_phone = norm_phone(phone)

        # Query discharged patient by ID
        patient = Patient.query.filter_by(patient_id=patient_id_str, status='discharged').first()
        
        # Verify phone matches (normalized)
        if patient and patient.phone:
            if norm_phone(patient.phone) == norm_input_phone:
                session['discharged_patient_id'] = patient.id
                flash('Welcome! You can now chat with our AI assistant.', 'success')
                return redirect(url_for('discharged_dashboard'))
        
        # No valid match
        flash('Invalid Patient ID or phone number. Please check and try again.', 'danger')
    
    return render_template('discharged_portal.html')


@app.route('/discharged-dashboard')
def discharged_dashboard():
    """Discharged patient chat dashboard with CareSync AI Assistant"""
    patient_id = session.get('discharged_patient_id')
    if not patient_id:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('discharged_portal'))
    
    try:
        patient = Patient.query.get(patient_id)
        if not patient:
            flash('Patient record not found.', 'danger')
            return redirect(url_for('discharged_portal'))
        
        if patient.status != 'discharged':
            flash('This portal is only for discharged patients.', 'danger')
            return redirect(url_for('discharged_portal'))
        
        # Get chat history
        chat_history = ChatMessage.query.filter_by(patient_id=patient_id).order_by(ChatMessage.created_at.asc()).all()
        
        return render_template('discharged_dashboard.html',
            patient=patient,
            chat_history=chat_history
        )
    except Exception as e:
        logging.error(f"Error loading discharged dashboard for patient {patient_id}: {e}")
        flash('An error occurred while loading your dashboard.', 'danger')
        return redirect(url_for('discharged_portal'))



@app.route('/api/discharged/chat', methods=['POST'])
def discharged_chat():
    """Chat API for discharged patients with Gemini"""
    from app import gemini_model
    import json
    
    patient_id = session.get('discharged_patient_id')
    if not patient_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    new_chat_flag = data.get('new_chat', False)
    language = data.get('language', 'en').lower()
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # If Gemini isn't configured (no API key), provide a polite local fallback
    if not gemini_model:
        fallback_local = {
            'en': "Hi, I'm CareSync Assistant. I can't access the AI service right now, but please contact your healthcare provider for urgent medical advice.",
            'hi': "नमस्ते, मैं CareSync सहायक हूँ। वर्तमान में AI सेवा उपलब्ध नहीं है। तत्काल सहायता के लिए अपने स्वास्थ्य प्रदाता से संपर्क करें।",
            'ta': "வணக்கம், நான் CareSync உதவியாளர். தற்போது AI சேவை அணுக முடியவில்லை. உடனடி உதவிக்கு உங்கள் மருத்துவர்களை தொடர்பு கொள்ளுங்கள்.",
            'te': "హలో, నేను CareSync సహాయకుడు. ప్రస్తుతం AI సేవ అందుబాటులో లేదు. తక్షణ సహాయానికి మీ వైద్యుడిని సంప్రదించండి."
        }
        ai_response = fallback_local.get(language, fallback_local['en'])

        # Store assistant fallback for continuity
        try:
            ai_msg = ChatMessage(
                patient_id=patient_id,
                role='assistant',
                message=ai_response,
                language=language
            )
            db.session.add(ai_msg)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return jsonify({'role': 'assistant', 'message': ai_response, 'language': language}), 200
    
    patient = Patient.query.get_or_404(patient_id)
    
    # Store user message
    user_msg = ChatMessage(
        patient_id=patient_id,
        role='patient',
        message=user_message,
        language=language
    )
    db.session.add(user_msg)
    db.session.commit()
    
    # Build context and language prompt
    language_names = {
        'en': 'English',
        'hi': 'Hindi',
        'ta': 'Tamil',
        'te': 'Telugu'
    }
    lang_name = language_names.get(language, 'English')
    
    # Get recent chat history for context unless a fresh chat is requested
    recent_chat = []
    if not new_chat_flag:
        recent_chat = ChatMessage.query.filter_by(patient_id=patient_id).order_by(
            ChatMessage.created_at.desc()
        ).limit(6).all()
        recent_chat.reverse()
    
    context = f"You are CareSync AI Assistant, a helpful medical advisor for discharged patients. "
    context += f"Patient Name: {patient.full_name}, Patient ID: {patient.patient_id}. "
    context += f"Recent Diagnosis: {patient.diagnosis}. "
    
    # Get latest vitals for context
    latest_vital = patient.vitals.first()
    if latest_vital:
        vital_context = f"Latest vitals: HR {latest_vital.heart_rate} bpm, BP {latest_vital.blood_pressure_systolic}/{latest_vital.blood_pressure_diastolic} mmHg, O2 {latest_vital.oxygen_saturation}%, Temp {latest_vital.temperature}°F. "
        context += vital_context
    
    # Get active medications for context
    active_meds = Medication.query.filter_by(patient_id=patient_id, is_active=True).all()
    if active_meds:
        med_names = ', '.join([m.name for m in active_meds[:5]])
        context += f"Active medications: {med_names}. "
    
    context += f"Reply ONLY in {lang_name}. Keep responses concise and helpful. If describing urgent symptoms, suggest visiting a doctor and offer appointment booking."
    
    # Build conversation for Gemini
    messages = []
    for msg in recent_chat:
        if msg.role == 'patient':
            messages.append({'role': 'user', 'parts': [msg.message]})
        else:
            messages.append({'role': 'model', 'parts': [msg.message]})
    
    # Add current message
    messages.append({'role': 'user', 'parts': [f"{context}\n\nPatient: {user_message}"]})
    
    try:
        # Call Gemini API with safety settings
        response = gemini_model.generate_content(
            [msg['parts'][0] for msg in messages],
            generation_config={'temperature': 0.7, 'max_output_tokens': 500}
        )
        
        # Handle blocked responses or empty responses robustly
        ai_response = None
        try:
            # response.text accessor can raise if the model returned no valid Part
            ai_text = None
            try:
                ai_text = response.text
            except Exception as inner_e:
                logging.warning(f"Could not access response.text: {inner_e}")
                # Try alternative locations on the response object
                candidates = getattr(response, 'candidates', None)
                if candidates:
                    texts = [getattr(c, 'text', None) for c in candidates]
                    ai_text = ' '.join([t for t in texts if t]) if texts else None

            if not ai_text or not isinstance(ai_text, str) or not ai_text.strip():
                ai_response = (
                    "I appreciate your question. I'm working to provide you with the best response. "
                    "Please try again or contact your healthcare provider for immediate medical advice."
                )
            else:
                ai_response = ai_text
        except Exception as e:
            logging.error(f"Error processing Gemini response object: {e}")
            ai_response = (
                "I appreciate your question. I'm working to provide you with the best response. "
                "Please try again or contact your healthcare provider for immediate medical advice."
            )
        
        # Store AI response
        ai_msg = ChatMessage(
            patient_id=patient_id,
            role='assistant',
            message=ai_response,
            language=language
        )
        db.session.add(ai_msg)
        db.session.commit()
        
        return jsonify({
            'role': 'assistant',
            'message': ai_response,
            'language': language
        })
    
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        # Log and return a friendly assistant fallback (HTTP 200) so UI remains responsive
        fallback_msg = (
            "I appreciate your question. I'm currently unable to generate a full response. "
            "Please try again in a moment or contact your healthcare provider for urgent concerns."
        )
        logging.info(f"Returning assistant fallback for patient {patient_id}")

        # Store fallback as assistant message for continuity
        try:
            ai_msg = ChatMessage(
                patient_id=patient_id,
                role='assistant',
                message=fallback_msg,
                language=language
            )
            db.session.add(ai_msg)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return jsonify({'role': 'assistant', 'message': fallback_msg, 'language': language}), 200


@app.route('/api/discharged/clear-history', methods=['POST'])
def discharged_clear_history():
    """Clear chat history for the logged-in discharged patient."""
    patient_id = session.get('discharged_patient_id')
    if not patient_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        ChatMessage.query.filter_by(patient_id=patient_id).delete()
        db.session.commit()
        return jsonify({'ok': True}), 200
    except Exception as e:
        logging.error(f"Error clearing chat history for patient {patient_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Could not clear history'}), 500


@app.route('/api/discharged/book-appointment', methods=['POST'])
def discharged_book_appointment():
    """Allow discharged patient to request an appointment via the chat UI."""
    patient_id = session.get('discharged_patient_id')
    if not patient_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    preferred_date = data.get('preferred_date')  # ISO string expected
    preferred_time = data.get('preferred_time')
    doctor_id = data.get('doctor_id')
    notes = data.get('notes', '')

    try:
        preferred_dt = None
        if preferred_date:
            preferred_dt = datetime.fromisoformat(preferred_date)

        appt = AppointmentRequest(
            patient_id=patient_id,
            preferred_date=preferred_dt,
            preferred_time=preferred_time,
            doctor_id=doctor_id,
            notes=notes,
            status='pending'
        )
        db.session.add(appt)
        db.session.commit()

        return jsonify({'ok': True, 'appointment_id': appt.id, 'status': appt.status}), 201
    except Exception as e:
        logging.error(f"Error creating appointment request: {e}")
        db.session.rollback()
        return jsonify({'error': 'Could not create appointment request'}), 500


@app.route('/api/discharged/summary')
def discharged_summary():
    """Return a short AI-influenced risk summary for the logged-in discharged patient."""
    patient_id = session.get('discharged_patient_id')
    if not patient_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Basic risk analysis (may consult AI) - keep this first so heavy work is encapsulated
        analysis = risk_predictor.analyze_patient_risk(patient_id)

        # Normalize predictions to a friendly default when empty
        preds = analysis.get('predictions') or []
        if not preds:
            preds = ['No specific predictions at this time.']

        # Attach patient-level information so the frontend can render a full summary
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404

        # Lab results (most recent first, limit to 10)
        try:
            labs = [
                {
                    'test_name': lr.test_name,
                    'result': lr.result,
                    'units': lr.units,
                    'normal_range': lr.normal_range,
                    'reported_at': lr.reported_at.isoformat() if lr.reported_at else None,
                    'file_url': getattr(lr, 'file_url', None)
                }
                for lr in LabReport.query.filter_by(patient_id=patient_id).order_by(LabReport.reported_at.desc()).limit(10).all()
            ]
        except Exception:
            labs = []

        # Medications / prescriptions (active and recent)
        try:
            meds = [
                {
                    'name': m.name,
                    'dosage': m.dosage,
                    'frequency': m.frequency,
                    'route': m.route,
                    'start_date': m.start_date.isoformat() if m.start_date else None,
                    'end_date': m.end_date.isoformat() if m.end_date else None,
                    'notes': m.notes
                }
                for m in Medication.query.filter_by(patient_id=patient_id).order_by(Medication.start_date.desc()).limit(20).all()
            ]
        except Exception:
            meds = []

        payload = {
            'name': patient.full_name,
            'patient_id': patient.patient_id,
            'mobile': patient.phone or '',
            'age': patient.age,
            'admission_date': patient.admission_date.isoformat() if patient.admission_date else None,
            'discharge_date': patient.discharge_date.isoformat() if patient.discharge_date else None,
            'address': patient.address or '',
            'health_issue': patient.diagnosis or '',
            'lab_results': labs,
            'medical_prescription': meds,
            # Risk analysis fields
            'risk_level': (analysis.get('risk_level') or 'stable'),
            'risk_score': int(analysis.get('risk_score') or 0),
            'predictions': preds,
            'analyzed_at': analysis.get('analyzed_at'),
        }

        return jsonify(payload), 200
    except Exception as e:
        logging.error(f"Error computing summary for discharged patient {patient_id}: {e}")
        return jsonify({'error': 'Could not compute summary'}), 500


@app.route('/api/patient/<int:patient_id>/chat', methods=['POST'])
def patient_chat(patient_id):
    """Chat API accessible to logged-in staff or the discharged patient themselves."""
    from app import gemini_model

    # Authorization: allow if staff is logged in or the discharged patient session matches
    staff = get_staff_user()
    if not staff and session.get('discharged_patient_id') != patient_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    new_chat_flag = data.get('new_chat', False)
    language = data.get('language', 'en').lower()

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # Fallback if Gemini not configured
    if not getattr(gemini_model, '__call__', True) and not gemini_model:
        fallback_local = {
            'en': "Hi, I'm CareSync Assistant. I can't access the AI service right now, but please contact your healthcare provider for urgent medical advice.",
            'hi': "नमस्ते, मैं CareSync सहायक हूँ। वर्तमान में AI सेवा उपलब्ध नहीं है। तत्काल सहायता के लिए अपने स्वास्थ्य प्रदाता से संपर्क करें।",
            'ta': "வணக்கம், நான் CareSync உதவியாளர். தற்போது AI சேவை அணுக முடியவில்லை. உடனடி உதவிக்கு உங்கள் மருத்துவர்களை தொடர்பு கொள்ளுங்கள்.",
            'te': "హలో, నేను CareSync సహాయకుడు. ప్రస్తుతం AI సేవ అందుబాటులో లేదు. తక్షణ సహాయానికి మీ వైద్యుడిని సంప్రదించండి."
        }
        ai_response = fallback_local.get(language, fallback_local['en'])
        try:
            ai_msg = ChatMessage(patient_id=patient_id, role='assistant', message=ai_response, language=language)
            db.session.add(ai_msg)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return jsonify({'role': 'assistant', 'message': ai_response, 'language': language}), 200

    patient = Patient.query.get_or_404(patient_id)

    # Store message (from staff or patient) as 'patient' role so AI context treats it as user input
    user_msg = ChatMessage(patient_id=patient_id, role='patient', message=user_message, language=language)
    db.session.add(user_msg)
    db.session.commit()

    # Build context
    language_names = {'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil', 'te': 'Telugu'}
    lang_name = language_names.get(language, 'English')

    recent_chat = []
    if not new_chat_flag:
        recent_chat = ChatMessage.query.filter_by(patient_id=patient_id).order_by(ChatMessage.created_at.desc()).limit(6).all()
        recent_chat.reverse()

    context = f"You are CareSync AI Assistant, a helpful medical advisor for patients. Patient Name: {patient.full_name}, Patient ID: {patient.patient_id}. Recent Diagnosis: {patient.diagnosis}. "
    latest_vital = patient.vitals.first()
    if latest_vital:
        context += f"Latest vitals: HR {latest_vital.heart_rate} bpm, BP {latest_vital.blood_pressure_systolic}/{latest_vital.blood_pressure_diastolic} mmHg, O2 {latest_vital.oxygen_saturation}%, Temp {latest_vital.temperature}°F. "
    active_meds = Medication.query.filter_by(patient_id=patient_id, is_active=True).all()
    if active_meds:
        med_names = ', '.join([m.name for m in active_meds[:5]])
        context += f"Active medications: {med_names}. "

    context += f"Reply ONLY in {lang_name}. Keep responses concise and helpful. If describing urgent symptoms, suggest visiting a doctor and offer appointment booking."

    messages = []
    for msg in recent_chat:
        if msg.role == 'patient':
            messages.append({'role': 'user', 'parts': [msg.message]})
        else:
            messages.append({'role': 'model', 'parts': [msg.message]})

    messages.append({'role': 'user', 'parts': [f"{context}\n\nPatient: {user_message}"]})

    try:
        response = gemini_model.generate_content([m['parts'][0] for m in messages], generation_config={'temperature': 0.7, 'max_output_tokens': 500})
        ai_text = None
        try:
            ai_text = response.text
        except Exception:
            candidates = getattr(response, 'candidates', None)
            if candidates:
                texts = [getattr(c, 'text', None) for c in candidates]
                ai_text = ' '.join([t for t in texts if t]) if texts else None

        if not ai_text:
            ai_response = "I appreciate your question. I'm working to provide you with the best response. Please try again or contact your healthcare provider for immediate medical advice."
        else:
            ai_response = ai_text

        ai_msg = ChatMessage(patient_id=patient_id, role='assistant', message=ai_response, language=language)
        db.session.add(ai_msg)
        db.session.commit()

        return jsonify({'role': 'assistant', 'message': ai_response, 'language': language})
    except Exception as e:
        logging.error(f"Gemini API error for patient chat: {e}")
        fallback_msg = "I appreciate your question. I'm currently unable to generate a full response. Please try again in a moment or contact your healthcare provider for urgent concerns."
        try:
            ai_msg = ChatMessage(patient_id=patient_id, role='assistant', message=fallback_msg, language=language)
            db.session.add(ai_msg)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return jsonify({'role': 'assistant', 'message': fallback_msg, 'language': language}), 200


@app.route('/api/patient/<int:patient_id>/clear-history', methods=['POST'])
def patient_clear_history(patient_id):
    """Clear chat history for a specific patient (staff or patient action)."""
    staff = get_staff_user()
    if not staff and session.get('discharged_patient_id') != patient_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        ChatMessage.query.filter_by(patient_id=patient_id).delete()
        db.session.commit()
        return jsonify({'ok': True}), 200
    except Exception as e:
        logging.error(f"Error clearing chat history for patient {patient_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Could not clear history'}), 500


@app.route('/api/patient/<int:patient_id>/book-appointment', methods=['POST'])
def patient_book_appointment(patient_id):
    """Create an appointment request on behalf of a patient (staff or patient action)."""
    staff = get_staff_user()
    if not staff and session.get('discharged_patient_id') != patient_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    preferred_date = data.get('preferred_date')
    preferred_time = data.get('preferred_time')
    doctor_id = data.get('doctor_id')
    notes = data.get('notes', '')

    # If staff is a doctor and no doctor_id provided, default to them
    if not doctor_id and staff and staff.role == 'doctor':
        doctor_id = staff.id

    try:
        preferred_dt = None
        if preferred_date:
            try:
                preferred_dt = datetime.fromisoformat(preferred_date)
            except Exception:
                preferred_dt = None

        appt = AppointmentRequest(
            patient_id=patient_id,
            preferred_date=preferred_dt,
            preferred_time=preferred_time,
            doctor_id=doctor_id,
            notes=notes,
            status='pending'
        )
        db.session.add(appt)
        db.session.commit()
        return jsonify({'ok': True, 'appointment_id': appt.id, 'status': appt.status}), 201
    except Exception as e:
        logging.error(f"Error creating appointment request (patient/staff): {e}")
        db.session.rollback()
        return jsonify({'error': 'Could not create appointment request'}), 500


@app.route('/api/patient/<int:patient_id>/summary')
def patient_summary(patient_id):
    """Return a short AI-influenced risk summary for a given patient (staff or patient access)."""
    staff = get_staff_user()
    if not staff and session.get('discharged_patient_id') != patient_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        analysis = risk_predictor.analyze_patient_risk(patient_id)
        return jsonify(analysis), 200
    except Exception as e:
        logging.error(f"Error computing summary for patient {patient_id}: {e}")
        return jsonify({'error': 'Could not compute summary'}), 500


@app.route('/discharged-logout')
def discharged_logout():
    """Logout discharged patient"""
    session.pop('discharged_patient_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('discharged_portal'))


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403
