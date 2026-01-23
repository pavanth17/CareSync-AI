import random
from datetime import datetime, timedelta
from app import db
from models import StaffMember, Patient, VitalSign, Medication, Alert
from alert_router import send_to_n8n_webhook

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Rohan", "Rahul", "Vikas",
    "Amit", "Siddharth", "Priya", "Sanya", "Ananya", "Sneha", "Pooja", "Kavya",
    "Suman", "Deepa", "Lakshmi", "Meera", "Suresh", "Ramesh", "Rajesh", "Sunil",
    "Kumar", "Venkatesh", "Manish", "Pavan", "Nisha", "Divya", "Bhavya", "Keerthi",
    "Shreya", "Ishaan", "Tara", "Kiran", "Ila", "Nitin", "Siddhi", "Ritika"
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Khan", "Mehta",
    "Nair", "Iyer", "Joshi", "Desai", "Bose", "Kapoor", "Chaudhary", "Saxena",
    "Malhotra", "Mishra", "Verma", "Shah", "Rao", "Ghosh", "Pillai", "Chowdhury",
    "Tripathi", "Prasad", "Naik", "Dutta", "Bhandari", "Nambiar"
]

DEPARTMENTS = ["Emergency", "ICU", "Cardiology", "Neurology", "Pediatrics", "Oncology", "Orthopedics", "Surgery"]
SPECIALIZATIONS = ["General Medicine", "Cardiology", "Neurology", "Pediatrics", "Emergency Medicine", "Surgery", "Oncology", "Orthopedics"]

DIAGNOSES = [
    "Acute myocardial infarction", "Pneumonia", "Stroke", "Diabetes mellitus",
    "Chronic kidney disease", "Heart failure", "COPD exacerbation", "Sepsis",
    "Acute appendicitis", "Fracture", "Hypertension crisis", "Asthma exacerbation",
    "Gastrointestinal bleeding", "Deep vein thrombosis", "Pulmonary embolism"
]

MEDICATIONS_LIST = [
    ("Aspirin", "81mg", "Once daily", "oral"),
    ("Metoprolol", "50mg", "Twice daily", "oral"),
    ("Lisinopril", "10mg", "Once daily", "oral"),
    ("Metformin", "500mg", "A tablet only afternoon after meals", "oral"),
    ("Atorvastatin", "40mg", "Once daily", "oral"),
    ("Omeprazole", "20mg", "A tablet before breakfast at mrng", "oral"),
    ("Amlodipine", "5mg", "Once daily", "oral"),
    ("Ceftriaxone", "1g", "Twice daily", "IV"),
    ("Vancomycin", "1g", "Twice daily", "IV"),
    ("Morphine", "2mg", "As needed", "IV"),
    ("Heparin", "5000 units", "A tablet 3 times a day after food", "subcutaneous"),
    ("Insulin Regular", "10 units", "A tablet before breakfast at mrng", "subcutaneous"),
]


def generate_staff_id(role, index):
    prefix = {"admin": "ADM", "doctor": "DOC", "nurse": "NRS"}
    return f"{prefix.get(role, 'STF')}{str(index).zfill(4)}"


def generate_patient_id(index):
    return f"PAT{str(index).zfill(6)}"


def create_admin():
    existing = StaffMember.query.filter_by(role='admin').first()
    if existing:
        return existing
    
    admin = StaffMember(
        staff_id="ADM0001",
        first_name="Pavanth",
        last_name="Kumar",
        email="admin@caresync.hospital",
        phone="9700443157",
        role="admin",
        department="Administration",
        is_on_duty=True,
        is_active=True
    )
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()
    return admin


def create_synthetic_staff(num_doctors=2, num_nurses=3):
    staff_created = []
    
    existing_doctors = StaffMember.query.filter_by(role='doctor').count()
    existing_nurses = StaffMember.query.filter_by(role='nurse').count()
    
    for i in range(existing_doctors + 1, existing_doctors + num_doctors + 1):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        staff_id = generate_staff_id('doctor', i)
        
        if StaffMember.query.filter_by(staff_id=staff_id).first():
            continue
            
        doctor = StaffMember(
            staff_id=staff_id,
            first_name=first_name,
            last_name=last_name,
            email=f"{first_name.lower()}.{last_name.lower()}.doc{i}@caresync.hospital",
            phone=f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            role="doctor",
            department=random.choice(DEPARTMENTS),
            specialization=random.choice(SPECIALIZATIONS),
            is_on_duty=random.choice([True, True, False]),
            is_active=True
        )
        doctor.set_password(f"doctor{i}")
        db.session.add(doctor)
        staff_created.append(doctor)
    
    for i in range(existing_nurses + 1, existing_nurses + num_nurses + 1):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        staff_id = generate_staff_id('nurse', i)
        
        if StaffMember.query.filter_by(staff_id=staff_id).first():
            continue
            
        nurse = StaffMember(
            staff_id=staff_id,
            first_name=first_name,
            last_name=last_name,
            email=f"{first_name.lower()}.{last_name.lower()}.nrs{i}@caresync.hospital",
            phone=f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            role="nurse",
            department=random.choice(DEPARTMENTS),
            is_on_duty=random.choice([True, True, False]),
            is_active=True
        )
        nurse.set_password(f"nurse{i}")
        db.session.add(nurse)
        staff_created.append(nurse)
    
    db.session.commit()
    return staff_created


def create_ward_staff():
    """Create specific staff for ward login demos"""
    ward_staff = []
    
    # ICU Nurse
    if not StaffMember.query.filter_by(staff_id="NRS_ICU").first():
        icu_nurse = StaffMember(
            staff_id="NRS_ICU",
            first_name="Priya",
            last_name="ICU",
            email="icu.nurse@caresync.hospital",
            phone="555-000-0001",
            role="nurse",
            department="ICU",
            is_on_duty=True,
            is_active=True
        )
        icu_nurse.set_password("nurse123")
        db.session.add(icu_nurse)
        ward_staff.append(icu_nurse)

    # Emergency Nurse
    if not StaffMember.query.filter_by(staff_id="NRS_ER").first():
        er_nurse = StaffMember(
            staff_id="NRS_ER",
            first_name="Rahul",
            last_name="Emergency",
            email="er.nurse@caresync.hospital",
            phone="555-000-0002",
            role="nurse",
            department="Emergency",
            is_on_duty=True,
            is_active=True
        )
        er_nurse.set_password("nurse123")
        db.session.add(er_nurse)
        ward_staff.append(er_nurse)

    db.session.commit()
    return ward_staff


def create_synthetic_patients(num_patients=5, num_discharged=0):
    patients_created = []
    existing_count = Patient.query.count()

    doctors = StaffMember.query.filter_by(role='doctor', is_active=True).all()
    nurses = StaffMember.query.filter_by(role='nurse', is_active=True).all()

    if not doctors or not nurses:
        return []

    for i in range(existing_count + 1, existing_count + num_patients + 1):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        patient_id = generate_patient_id(i)
        
        if Patient.query.filter_by(patient_id=patient_id).first():
            continue
        
        birth_year = datetime.now().year - random.randint(18, 85)
        dob = datetime(birth_year, random.randint(1, 12), random.randint(1, 28))
        
        admission_days_ago = random.randint(0, 14)
        
        status = random.choices(
            ['admitted', 'admitted', 'icu', 'emergency', 'discharged'],
            weights=[40, 30, 15, 10, 5]
        )[0]
        
        patient = Patient(
            patient_id=patient_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob.date(),
            gender=random.choice(['Male', 'Female']),
            blood_type=random.choice(['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']),
            phone=f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            email=f"{first_name.lower()}.{last_name.lower()}{i}@email.com",
            address=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Cedar', 'Pine'])} Street, City, State {random.randint(10000, 99999)}",
            emergency_contact_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            emergency_contact_phone=f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            room_number=f"{random.choice(['A', 'B', 'C', 'D'])}{random.randint(101, 450)}",
            bed_number=str(random.randint(1, 4)),
            status=status,
            admission_date=datetime.now() - timedelta(days=admission_days_ago),
            diagnosis=random.choice(DIAGNOSES),
            notes=f"Patient admitted for {random.choice(DIAGNOSES).lower()}. Regular monitoring required.",
            assigned_doctor_id=random.choice(doctors).id if doctors else None,
            assigned_nurse_id=random.choice(nurses).id if nurses else None,
            department=random.choice(DEPARTMENTS) if status != 'discharged' else None
        )
        db.session.add(patient)
        patients_created.append(patient)
    
    db.session.commit()
    # Mark a subset as discharged if requested
    try:
        if num_discharged and len(patients_created) > 0:
            num_to_discharge = min(num_discharged, len(patients_created))
            discharged_sample = random.sample(patients_created, num_to_discharge)
            for p in discharged_sample:
                p.status = 'discharged'
                p.discharge_date = datetime.now()
            db.session.commit()
    except Exception:
        db.session.rollback()

    return patients_created


def generate_vital_sign(patient, status_bias=None):
    if status_bias == 'critical' or (patient.status in ['icu', 'emergency'] and random.random() < 0.3):
        heart_rate = random.choice([random.randint(35, 50), random.randint(120, 160)])
        systolic = random.choice([random.randint(70, 85), random.randint(180, 210)])
        diastolic = random.choice([random.randint(40, 55), random.randint(110, 130)])
        oxygen = random.randint(80, 89)
        temperature = random.choice([random.uniform(95.0, 96.5), random.uniform(102.5, 105.0)])
        respiratory = random.choice([random.randint(6, 10), random.randint(28, 40)])
        status = 'critical'
    elif status_bias == 'warning' or random.random() < 0.15:
        heart_rate = random.choice([random.randint(50, 60), random.randint(100, 120)])
        systolic = random.choice([random.randint(90, 100), random.randint(140, 160)])
        diastolic = random.choice([random.randint(55, 65), random.randint(90, 100)])
        oxygen = random.randint(90, 93)
        temperature = random.choice([random.uniform(96.5, 97.5), random.uniform(99.5, 101.5)])
        respiratory = random.choice([random.randint(10, 12), random.randint(20, 25)])
        status = 'warning'
    else:
        heart_rate = random.randint(60, 100)
        systolic = random.randint(110, 130)
        diastolic = random.randint(70, 85)
        oxygen = random.randint(95, 100)
        temperature = random.uniform(97.5, 99.0)
        respiratory = random.randint(12, 20)
        status = 'normal'
    
    vital = VitalSign(
        patient_id=patient.id,
        heart_rate=round(heart_rate, 1),
        blood_pressure_systolic=systolic,
        blood_pressure_diastolic=diastolic,
        oxygen_saturation=round(oxygen, 1),
        temperature=round(temperature, 1),
        respiratory_rate=respiratory,
        status=status,
        recorded_at=datetime.now()
    )
    
    return vital


def create_initial_vitals(patients):
    for patient in patients:
        for i in range(5):
            vital = generate_vital_sign(patient)
            vital.recorded_at = datetime.now() - timedelta(minutes=i*15)
            db.session.add(vital)
    db.session.commit()


def create_medications_for_patients(patients):
    for patient in patients:
        num_meds = random.randint(1, 4)
        selected_meds = random.sample(MEDICATIONS_LIST, num_meds)
        
        for med in selected_meds:
            start_date = patient.admission_date
            next_due = datetime.now() + timedelta(hours=random.randint(1, 8))
            
            medication = Medication(
                patient_id=patient.id,
                name=med[0],
                dosage=med[1],
                frequency=med[2],
                route=med[3],
                start_date=start_date,
                next_due=next_due,
                prescribed_by_id=patient.assigned_doctor_id,
                is_active=True
            )
            db.session.add(medication)
    
    db.session.commit()


def check_vital_thresholds(vital):
    alerts = []
    patient = Patient.query.get(vital.patient_id)
    
    if vital.heart_rate and (vital.heart_rate < 50 or vital.heart_rate > 130):
        severity = 'critical' if (vital.heart_rate < 40 or vital.heart_rate > 150) else 'warning'
        alerts.append({
            'type': 'critical_vitals',
            'severity': severity,
            'title': f"Abnormal Heart Rate - {patient.full_name}",
            'message': f"Heart rate is {vital.heart_rate} bpm. Room {patient.room_number}, Bed {patient.bed_number}."
        })
    
    if vital.blood_pressure_systolic and (vital.blood_pressure_systolic < 90 or vital.blood_pressure_systolic > 160):
        severity = 'critical' if (vital.blood_pressure_systolic < 80 or vital.blood_pressure_systolic > 180) else 'warning'
        alerts.append({
            'type': 'critical_vitals',
            'severity': severity,
            'title': f"Abnormal Blood Pressure - {patient.full_name}",
            'message': f"Blood pressure is {vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic} mmHg. Room {patient.room_number}, Bed {patient.bed_number}."
        })
    
    if vital.oxygen_saturation and vital.oxygen_saturation < 92:
        severity = 'critical' if vital.oxygen_saturation < 88 else 'warning'
        alerts.append({
            'type': 'critical_vitals',
            'severity': severity,
            'title': f"Low Oxygen Saturation - {patient.full_name}",
            'message': f"SpO2 is {vital.oxygen_saturation}%. Room {patient.room_number}, Bed {patient.bed_number}."
        })
    
    if vital.temperature and (vital.temperature < 96.5 or vital.temperature > 101.5):
        severity = 'critical' if (vital.temperature < 95 or vital.temperature > 103) else 'warning'
        alerts.append({
            'type': 'critical_vitals',
            'severity': severity,
            'title': f"Abnormal Temperature - {patient.full_name}",
            'message': f"Temperature is {vital.temperature}°F. Room {patient.room_number}, Bed {patient.bed_number}."
        })
    
    if vital.respiratory_rate and (vital.respiratory_rate < 10 or vital.respiratory_rate > 25):
        severity = 'critical' if (vital.respiratory_rate < 8 or vital.respiratory_rate > 30) else 'warning'
        alerts.append({
            'type': 'critical_vitals',
            'severity': severity,
            'title': f"Abnormal Respiratory Rate - {patient.full_name}",
            'message': f"Respiratory rate is {vital.respiratory_rate} breaths/min. Room {patient.room_number}, Bed {patient.bed_number}."
        })
    
    return alerts


def create_alert(patient_id, vital_id, alert_type, severity, title, message):
    existing = Alert.query.filter_by(
        patient_id=patient_id,
        alert_type=alert_type,
        is_acknowledged=False
    ).first()
    
    if existing:
        existing.message = message
        existing.severity = severity
        existing.vital_sign_id = vital_id
        existing.created_at = datetime.now()
        db.session.commit()
        # notify n8n if configured
        try:
            send_to_n8n_webhook(existing)
        except Exception:
            pass
    else:
        alert = Alert(
            patient_id=patient_id,
            vital_sign_id=vital_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message
        )
        db.session.add(alert)
    
    db.session.commit()
    # notify n8n if configured
    try:
        send_to_n8n_webhook(alert)
    except Exception:
        pass


def initialize_synthetic_data(num_doctors=2, num_nurses=3, num_patients=5, num_discharged=0):
    admin = create_admin()
    print(f"Admin created: {admin.staff_id}")

    staff = create_synthetic_staff(num_doctors=num_doctors, num_nurses=num_nurses)
    print(f"Created {len(staff)} staff members")

    ward_staff = create_ward_staff()
    print(f"Created {len(ward_staff)} ward staff members")

    patients = create_synthetic_patients(num_patients=num_patients, num_discharged=num_discharged)
    print(f"Created {len(patients)} patients ({num_discharged} requested discharged)")

    if patients:
        create_initial_vitals(patients)
        print("Created initial vitals")

        create_medications_for_patients(patients)
        print("Created medications")

    return True
