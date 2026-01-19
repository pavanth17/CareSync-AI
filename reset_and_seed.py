"""Reset patient and alert data and seed deterministic test patients.

Run this script from the project root:
  python reset_and_seed.py

It will:
- Delete existing `VitalSign`, `Alert`, `RiskAssessment`, `ChatMessage`, `AppointmentRequest`, `Medication`, `Patient` rows (in that safe order)
- Create three patients: stable, moderate risk, high/critical risk with vitals
- Run `analyze_all_patients()` to compute risks and create predictive alerts
"""
from datetime import datetime, timedelta
import random

from app import app, db, genai, gemini_model
from models import Patient, VitalSign, Alert, RiskAssessment, ChatMessage, Medication, StaffMember, LabReport
from predictive_analytics import analyze_all_patients

# Generate 25 doctors and 60 nurses
# Use Indian (Andhra Pradesh / Telugu) style sample names for realism
first_names = ['Suresh', 'Ravi', 'Satish', 'Lakshmi', 'Sita', 'Ramesh', 'Kavya', 'Priya', 'Manish', 'Anjali', 'Venkatesh', 'Sowmya', 'Harsha', 'Divya', 'Naveen', 'Shruti', 'Bhavya', 'Krishna', 'Rajesh', 'Meena', 'Chiranjeevi', 'Swathi', 'Teja', 'Aparna', 'Gowtham']
last_names = ['Reddy', 'Naidu', 'Prasad', 'Kumar', 'Rao', 'Chowdary', 'Raju', 'Murthy', 'Gowda', 'Sharma', 'Patel', 'Singh', 'Iyer', 'Nair', 'Desai']
spec_list = ['Cardiology', 'Neurology', 'General Medicine', 'Pediatrics', 'Emergency Medicine', 'Surgery', 'Oncology', 'Orthopedics']

SAMPLE_STAFF = []
# Create 25 doctors
for i in range(1, 26):
    fn = first_names[(i-1) % len(first_names)]
    ln = last_names[(i-1) % len(last_names)]
    spec = spec_list[(i-1) % len(spec_list)]
    SAMPLE_STAFF.append({
        'staff_id': f'DOC{i:04d}',
        'first_name': fn,
        'last_name': ln,
        'email': f'doc{i:02d}@example.com',
        'role': 'doctor',
        'specialization': spec
    })
# Create 60 nurses
for i in range(1, 61):
    fn = first_names[(i-1) % len(first_names)]
    ln = last_names[(i-1) % len(last_names)]
    SAMPLE_STAFF.append({
        'staff_id': f'NRS{i:04d}',
        'first_name': fn,
        'last_name': ln,
        'email': f'nrs{i:02d}@example.com',
        'role': 'nurse'
    })

def ensure_sample_staff():
    # Clear existing non-admin staff and recreate
    StaffMember.query.filter(StaffMember.role != 'admin').delete()
    db.session.commit()
    # Create all staff members
    for s in SAMPLE_STAFF:
        sm = StaffMember(
            staff_id=s['staff_id'],
            first_name=s['first_name'],
            last_name=s['last_name'],
            email=s['email'],
            role=s['role'],
            specialization=s.get('specialization'),
            is_active=True
        )
        sm.set_password('password')
        db.session.add(sm)
    db.session.commit()
    print(f'Seeded {len(SAMPLE_STAFF)} staff members')

SAMPLE_PATIENTS = [
    {
        'patient_id': 'PAT000001',
        'first_name': 'Stable',
        'last_name': 'Patient',
        'date_of_birth': datetime(1980,1,1).date(),
        'gender': 'female',
        'status': 'admitted'
    },
    {
        'patient_id': 'PAT000002',
        'first_name': 'Moderate',
        'last_name': 'Risk',
        'date_of_birth': datetime(1975,6,15).date(),
        'gender': 'male',
        'status': 'admitted'
    },
    {
        'patient_id': 'PAT000003',
        'first_name': 'Critical',
        'last_name': 'Patient',
        'date_of_birth': datetime(1950,3,20).date(),
        'gender': 'male',
        'status': 'icu'
    }
]

SAMPLE_ADDRESSES = [
    "12 Baker Street, Springfield",
    "45 Greenway Ave, Rivertown",
    "78 Sunset Blvd, Lakeview",
    "3 Elm St, Oldtown",
]

SAMPLE_DIAGNOSES = [
    "Community acquired pneumonia",
    "Uncontrolled hypertension",
    "Acute myocardial ischemia",
    "Sepsis",
    "Post-op monitoring",
    "Chronic obstructive pulmonary disease exacerbation",
    "Stroke - suspected",
]

SPECIALIZATIONS = [
    "General Medicine", "Cardiology", "Neurology",
    "Pediatrics", "Emergency Medicine", "Surgery",
    "Oncology", "Orthopedics"
]

def pick_staff_by_specialization(specialization):
    # Find active doctors with matching specialization; prefer least-loaded
    doctors = StaffMember.query.filter_by(role='doctor', is_active=True, specialization=specialization).all()
    if not doctors:
        doctors = StaffMember.query.filter_by(role='doctor', is_active=True).all()
    if not doctors:
        return None
    # pick doctor with fewest assigned patients
    best = None
    best_count = None
    for d in doctors:
        cnt = Patient.query.filter_by(assigned_doctor_id=d.id).count()
        if best is None or cnt < best_count:
            best = d
            best_count = cnt
    return best

def pick_nurse_for_patient():
    nurses = StaffMember.query.filter_by(role='nurse', is_active=True).all()
    if not nurses:
        return None
    best = None
    best_count = None
    for n in nurses:
        cnt = Patient.query.filter_by(assigned_nurse_id=n.id).count()
        if best is None or cnt < best_count:
            best = n
            best_count = cnt
    return best

def ai_recommend_specialization(patient_summary):
    if genai is None:
        return None
    try:
        prompt = (
            f"Given the following patient summary, recommend a single medical specialization best suited to manage this patient from the list: {SPECIALIZATIONS}. "
            f"Patient: {patient_summary}\nAnswer with the specialization name only."
        )
        if hasattr(genai, 'generate'):
            out = genai.generate(model='gemini-2.5-flash', input=prompt)
            # attempt to extract textual output
            if isinstance(out, dict):
                cand = out.get('candidates') or out.get('outputs')
                if cand:
                    text = cand[0].get('output') or cand[0].get('content') or str(cand[0])
                else:
                    text = str(out)
            else:
                text = str(out)
        elif gemini_model is not None and hasattr(gemini_model, 'generate'):
            out = gemini_model.generate(prompt)
            text = str(out)
        else:
            return None

        # Normalize and match to one of SPECIALIZATIONS
        text_low = text.lower()
        for s in SPECIALIZATIONS:
            if s.lower() in text_low:
                return s
        # try keywords
        if 'cardio' in text_low:
            return 'Cardiology'
        if 'neuro' in text_low:
            return 'Neurology'
        if 'emerg' in text_low or 'icu' in text_low:
            return 'Emergency Medicine'
    except Exception:
        return None
    return None

with app.app_context():
    print('Clearing existing patient-related data...')
    # Delete children first
    db.session.query(Alert).delete()
    db.session.query(RiskAssessment).delete()
    db.session.query(VitalSign).delete()
    db.session.query(ChatMessage).delete()
    db.session.query(Medication).delete()
    db.session.query(Patient).delete()
    db.session.commit()

    # Ensure sample staff exist for deterministic assignments
    ensure_sample_staff()

    print('Seeding sample patients and vitals...')
    now = datetime.now()
    for p in SAMPLE_PATIENTS:
        patient = Patient(
            patient_id=p['patient_id'],
            first_name=p['first_name'],
            last_name=p['last_name'],
            date_of_birth=p['date_of_birth'],
            gender=p['gender'],
            status=p['status']
        )
        db.session.add(patient)
        db.session.flush()

        # Enrich patient with realistic address and diagnosis
        patient.address = random.choice(SAMPLE_ADDRESSES)
        patient.diagnosis = random.choice(SAMPLE_DIAGNOSES)

        # Build a short patient summary for AI assignment
        try:
            age = patient.age
        except Exception:
            age = 'unknown age'
        patient_summary = f"{patient.full_name}, {age} years old, status: {patient.status}. Primary issue: {patient.diagnosis}."

        # Ask AI for recommended specialization (best-effort), fall back to simple heuristics
        specialization = ai_recommend_specialization(patient_summary)
        if specialization is None:
            # simple heuristic fallback based on diagnosis keywords
            diag_low = (patient.diagnosis or '').lower()
            if 'cardio' in diag_low or 'myocard' in diag_low or 'hypertension' in diag_low:
                specialization = 'Cardiology'
            elif 'neuro' in diag_low or 'stroke' in diag_low:
                specialization = 'Neurology'
            elif 'pneum' in diag_low or 'copd' in diag_low or 'sepsis' in diag_low:
                specialization = 'Emergency Medicine'
            elif 'post-op' in diag_low or 'surgery' in diag_low:
                specialization = 'Surgery'
            else:
                specialization = 'General Medicine'

        # Pick staff members
        doctor = pick_staff_by_specialization(specialization)
        nurse = pick_nurse_for_patient()
        if doctor:
            patient.assigned_doctor_id = doctor.id
        if nurse:
            patient.assigned_nurse_id = nurse.id

        # Persist enrichment to DB so assigned ids are saved with patient
        db.session.add(patient)
        db.session.flush()

        # Assign ward and bed numbers (wards A-E, beds 1-20)
        ward = random.choice(['A','B','C','D','E'])
        bed = random.randint(1,20)
        patient.room_number = f"{ward}-{random.randint(1,10)}"
        patient.bed_number = str(bed)
        db.session.add(patient)
        db.session.flush()

        # Create 0-2 sample lab reports per patient
        num_labs = random.choices([0,1,2], weights=[40,40,20])[0]
        labs = []
        sample_tests = ['CBC', 'BMP', 'Liver Function', 'CRP', 'D-Dimer', 'Troponin']
        for li in range(num_labs):
            test = random.choice(sample_tests)
            lr = LabReport(
                patient_id=patient.id,
                test_name=test,
                result=f"{random.uniform(0.5, 5.0):.2f}",
                units='mg/dL',
                normal_range='0.0-1.0',
                collected_at=now - timedelta(hours=random.randint(1,72)),
                reported_at=now - timedelta(hours=random.randint(1,48)),
                reported_by_id=(doctor.id if doctor else None)
            )
            labs.append(lr)
        if labs:
            db.session.add_all(labs)

        print(f"Seeded patient {patient.full_name} (id={patient.id}) assigned to: doctor={getattr(doctor, 'full_name', None)} nurse={getattr(nurse, 'full_name', None)} specialization={specialization}")

        # Add vitals: stable -> normal vitals; moderate -> slightly abnormal; critical -> dangerous values
        vitals = []
        if p['patient_id'] == 'PAT000001':
            # stable patient: normal vitals
            for i in range(8):
                vitals.append(VitalSign(
                    patient_id=patient.id,
                    heart_rate=random.randint(65,80),
                    blood_pressure_systolic=random.randint(110,125),
                    blood_pressure_diastolic=random.randint(70,80),
                    oxygen_saturation=random.uniform(96,99),
                    temperature=random.uniform(97.5,99.0),
                    respiratory_rate=random.randint(14,18),
                    recorded_at=now - timedelta(minutes=5*i)
                ))
        elif p['patient_id'] == 'PAT000002':
            # moderate risk: trending low oxygen and increasing HR
            for i in range(8):
                vitals.append(VitalSign(
                    patient_id=patient.id,
                    heart_rate=80 + i*2,
                    blood_pressure_systolic=115 + (i%3),
                    blood_pressure_diastolic=75 + (i%2),
                    oxygen_saturation=95 - i*0.5,
                    temperature=98.0 + (i%2)*0.2,
                    respiratory_rate=16 + (i%2),
                    recorded_at=now - timedelta(minutes=5*i)
                ))
        else:
            # critical patient: dangerous vitals
            for i in range(8):
                vitals.append(VitalSign(
                    patient_id=patient.id,
                    heart_rate=120 + i,
                    blood_pressure_systolic=170 - i,
                    blood_pressure_diastolic=100 - i,
                    oxygen_saturation=82 + i*0.5,
                    temperature=101 + (i%3)*0.6,
                    respiratory_rate=28 + (i%2)*2,
                    recorded_at=now - timedelta(minutes=5*i)
                ))

        db.session.add_all(vitals)
        # After seeded samples, ensure we have at least 55 patients
        existing_count = Patient.query.count()
        target = 55
        # Also ensure a few discharged patients exist for the discharged portal (with phone numbers)
        DISCHARGED_SAMPLE = [
            {'patient_id': 'PATDIS001', 'first_name': 'Grace', 'last_name': 'Recovered', 'phone': '555-0101'},
            {'patient_id': 'PATDIS002', 'first_name': 'Hank', 'last_name': 'Well', 'phone': '555-0102'},
            {'patient_id': 'PATDIS003', 'first_name': 'Ivy', 'last_name': 'Home', 'phone': '555-0103'},
        ]
        for dp in DISCHARGED_SAMPLE:
            if not Patient.query.filter_by(patient_id=dp['patient_id']).first():
                patient = Patient(
                    patient_id=dp['patient_id'],
                    first_name=dp['first_name'],
                    last_name=dp['last_name'],
                    date_of_birth=datetime(1985,1,1).date(),
                    gender='female',
                    status='discharged',
                    phone=dp['phone']
                )
                db.session.add(patient)
                db.session.flush()
                # add a few vitals and a diagnosis
                patient.address = random.choice(SAMPLE_ADDRESSES)
                patient.diagnosis = random.choice(SAMPLE_DIAGNOSES)
                db.session.add(patient)
                vitals = []
                for i in range(4):
                    vitals.append(VitalSign(
                        patient_id=patient.id,
                        heart_rate=random.randint(60,100),
                        blood_pressure_systolic=random.randint(110,140),
                        blood_pressure_diastolic=random.randint(70,90),
                        oxygen_saturation=random.uniform(94,99),
                        temperature=random.uniform(97.5,99.5),
                        respiratory_rate=random.randint(12,20),
                        recorded_at=now - timedelta(days=(i+1))
                    ))
                db.session.add_all(vitals)
        db.session.flush()
        next_idx = 4
        first_names = ['John','Jane','Sam','Sara','Liam','Noah','Olivia','Emma','Lucas','Mia','Ethan','Ava','Sophia','Isabella']
        last_names = ['Smith','Johnson','Lee','Brown','Garcia','Martinez','Davis','Lopez','Wilson','Anderson']
        while existing_count < target:
            pid = f"PAT{next_idx:06d}"
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            dob = datetime.now().date().replace(year=random.randint(1940,2005))
            status = random.choice(['admitted','admitted','admitted','icu','emergency'])
            patient = Patient(
                patient_id=pid,
                first_name=fn,
                last_name=ln,
                date_of_birth=dob,
                gender=random.choice(['male','female']),
                status=status
            )
            db.session.add(patient)
            db.session.flush()

            # enrich
            patient.address = random.choice(SAMPLE_ADDRESSES)
            patient.diagnosis = random.choice(SAMPLE_DIAGNOSES)
            try:
                age = patient.age
            except Exception:
                age = 'unknown age'
            patient_summary = f"{patient.full_name}, {age} years old, status: {patient.status}. Primary issue: {patient.diagnosis}."
            specialization = ai_recommend_specialization(patient_summary)
            if specialization is None:
                diag_low = (patient.diagnosis or '').lower()
                if 'cardio' in diag_low or 'myocard' in diag_low or 'hypertension' in diag_low:
                    specialization = 'Cardiology'
                elif 'neuro' in diag_low or 'stroke' in diag_low:
                    specialization = 'Neurology'
                elif 'pneum' in diag_low or 'copd' in diag_low or 'sepsis' in diag_low:
                    specialization = 'Emergency Medicine'
                elif 'post-op' in diag_low or 'surgery' in diag_low:
                    specialization = 'Surgery'
                else:
                    specialization = 'General Medicine'

            doctor = pick_staff_by_specialization(specialization)
            nurse = pick_nurse_for_patient()
            if doctor:
                patient.assigned_doctor_id = doctor.id
            if nurse:
                patient.assigned_nurse_id = nurse.id
            db.session.add(patient)
            db.session.flush()

            # add random vitals (8 entries)
            vitals = []
            base_hr = random.randint(60,120)
            for i in range(8):
                vitals.append(VitalSign(
                    patient_id=patient.id,
                    heart_rate=base_hr + random.randint(-5,5),
                    blood_pressure_systolic=random.randint(100,160),
                    blood_pressure_diastolic=random.randint(60,100),
                    oxygen_saturation=random.uniform(85,99),
                    temperature=98.0 + random.uniform(-1.5,3.0),
                    respiratory_rate=random.randint(12,30),
                    recorded_at=now - timedelta(minutes=5*i)
                ))
            db.session.add_all(vitals)
            # Assign ward/bed
            ward = random.choice(['A','B','C','D','E'])
            patient.room_number = f"{ward}-{random.randint(1,12)}"
            patient.bed_number = str(random.randint(1,20))
            db.session.add(patient)
            # occasional lab reports
            if random.random() < 0.4:
                test = random.choice(['CBC','BMP','CRP','LFT','Troponin'])
                lr = LabReport(
                    patient_id=patient.id,
                    test_name=test,
                    result=f"{random.uniform(0.5, 7.0):.2f}",
                    units='mg/dL',
                    normal_range='0.0-1.0',
                    collected_at=now - timedelta(hours=random.randint(1,120)),
                    reported_at=now - timedelta(hours=random.randint(1,72)),
                    reported_by_id=(doctor.id if doctor else None)
                )
                db.session.add(lr)
            existing_count += 1
            next_idx += 1
        db.session.commit()

    print('Running AI risk analysis for all patients...')
    results = analyze_all_patients()
    for r in results:
        print(f"Patient {r['patient_name']} -> {r['risk_level']} (score {r['risk_score']})")

    print('Done. Alerts created for high/critical patients.')
