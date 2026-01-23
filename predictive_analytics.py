import logging
import re
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.DEBUG)

class RiskPredictor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.risk_classifier = RandomForestClassifier(n_estimators=50, random_state=42)
        self.is_trained = False
        
    def prepare_vital_features(self, vitals):
        features = []
        for vital in vitals:
            feature_vector = [
                vital.heart_rate or 75,
                vital.blood_pressure_systolic or 120,
                vital.blood_pressure_diastolic or 80,
                vital.oxygen_saturation or 98,
                vital.temperature or 98.6,
                vital.respiratory_rate or 16
            ]
            features.append(feature_vector)
        return np.array(features) if features else np.array([])
    
    def calculate_trend(self, values, window=5):
        if len(values) < 2:
            return 0
        values = values[-window:]
        if len(values) < 2:
            return 0
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        return slope
    
    def analyze_patient_risk(self, patient_id):
        from models import VitalSign
        vitals = VitalSign.query.filter_by(patient_id=patient_id).order_by(
            VitalSign.recorded_at.desc()
        ).limit(20).all()
        
        if len(vitals) < 3:
            return {
                'risk_level': 'unknown',
                'risk_score': 0,
                'predictions': [],
                'message': 'Insufficient data for analysis'
            }
        
        latest = vitals[0]
        features = self.prepare_vital_features(vitals)
        
        if len(features) == 0:
            return {
                'risk_level': 'unknown',
                'risk_score': 0,
                'predictions': [],
                'message': 'No vital data available'
            }
        
        risk_factors = []
        risk_score = 0
        
        hr_values = [v.heart_rate for v in vitals if v.heart_rate]
        if hr_values:
            hr_trend = self.calculate_trend(hr_values)
            hr_avg = np.mean(hr_values)
            hr_std = np.std(hr_values)
            
            if hr_avg < 55 or hr_avg > 110:
                risk_score += 25
                risk_factors.append({
                    'type': 'heart_rate',
                    'severity': 'high',
                    'message': f'Average heart rate ({hr_avg:.0f} bpm) is outside normal range',
                    'trend': 'increasing' if hr_trend > 0.5 else 'decreasing' if hr_trend < -0.5 else 'stable'
                })
            elif hr_avg < 60 or hr_avg > 100:
                risk_score += 10
                risk_factors.append({
                    'type': 'heart_rate',
                    'severity': 'medium',
                    'message': f'Heart rate trending towards abnormal ({hr_avg:.0f} bpm)',
                    'trend': 'increasing' if hr_trend > 0.5 else 'decreasing' if hr_trend < -0.5 else 'stable'
                })
            
            if hr_std > 15:
                risk_score += 15
                risk_factors.append({
                    'type': 'heart_rate_variability',
                    'severity': 'medium',
                    'message': f'High heart rate variability detected (SD: {hr_std:.1f})',
                    'trend': 'unstable'
                })
        
        bp_systolic = [v.blood_pressure_systolic for v in vitals if v.blood_pressure_systolic]
        if bp_systolic:
            bp_trend = self.calculate_trend(bp_systolic)
            bp_avg = np.mean(bp_systolic)
            
            if bp_avg < 85 or bp_avg > 165:
                risk_score += 30
                risk_factors.append({
                    'type': 'blood_pressure',
                    'severity': 'high',
                    'message': f'Blood pressure ({bp_avg:.0f} mmHg systolic) critically abnormal',
                    'trend': 'increasing' if bp_trend > 1 else 'decreasing' if bp_trend < -1 else 'stable'
                })
            elif bp_avg < 95 or bp_avg > 145:
                risk_score += 15
                risk_factors.append({
                    'type': 'blood_pressure',
                    'severity': 'medium',
                    'message': f'Blood pressure trending towards abnormal range',
                    'trend': 'increasing' if bp_trend > 1 else 'decreasing' if bp_trend < -1 else 'stable'
                })
        
        oxygen_values = [v.oxygen_saturation for v in vitals if v.oxygen_saturation]
        if oxygen_values:
            o2_trend = self.calculate_trend(oxygen_values)
            o2_avg = np.mean(oxygen_values)
            
            if o2_avg < 90:
                risk_score += 35
                risk_factors.append({
                    'type': 'oxygen_saturation',
                    'severity': 'critical',
                    'message': f'Oxygen saturation critically low ({o2_avg:.0f}%)',
                    'trend': 'decreasing' if o2_trend < -0.2 else 'stable'
                })
            elif o2_avg < 94:
                risk_score += 20
                risk_factors.append({
                    'type': 'oxygen_saturation',
                    'severity': 'high',
                    'message': f'Low oxygen saturation ({o2_avg:.0f}%)',
                    'trend': 'decreasing' if o2_trend < -0.2 else 'stable'
                })
            
            if o2_trend < -0.5 and o2_avg < 96:
                risk_score += 10
                risk_factors.append({
                    'type': 'oxygen_trend',
                    'severity': 'medium',
                    'message': 'Oxygen saturation showing declining trend',
                    'trend': 'decreasing'
                })
        
        temp_values = [v.temperature for v in vitals if v.temperature]
        if temp_values:
            temp_avg = np.mean(temp_values)
            temp_trend = self.calculate_trend(temp_values)
            
            if temp_avg < 96 or temp_avg > 102:
                risk_score += 25
                risk_factors.append({
                    'type': 'temperature',
                    'severity': 'high',
                    'message': f'Temperature critically abnormal ({temp_avg:.1f}°F)',
                    'trend': 'increasing' if temp_trend > 0.1 else 'decreasing' if temp_trend < -0.1 else 'stable'
                })
            elif temp_avg < 97 or temp_avg > 100:
                risk_score += 10
                risk_factors.append({
                    'type': 'temperature',
                    'severity': 'medium',
                    'message': f'Temperature outside normal range ({temp_avg:.1f}°F)',
                    'trend': 'increasing' if temp_trend > 0.1 else 'decreasing' if temp_trend < -0.1 else 'stable'
                })
        
        resp_values = [v.respiratory_rate for v in vitals if v.respiratory_rate]
        if resp_values:
            resp_avg = np.mean(resp_values)
            
            if resp_avg < 10 or resp_avg > 28:
                risk_score += 25
                risk_factors.append({
                    'type': 'respiratory_rate',
                    'severity': 'high',
                    'message': f'Respiratory rate abnormal ({resp_avg:.0f}/min)',
                    'trend': 'abnormal'
                })
        
        if risk_score >= 70:
            risk_level = 'critical'
        elif risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 30:
            risk_level = 'moderate'
        elif risk_score > 0:
            risk_level = 'low'
        else:
            risk_level = 'stable'
        
        predictions = []
        for factor in risk_factors:
            if factor['trend'] in ['increasing', 'decreasing']:
                if factor['type'] == 'heart_rate' and factor['trend'] == 'increasing':
                    predictions.append('Heart rate may reach critical levels in next 1-2 hours')
                elif factor['type'] == 'oxygen_saturation' and factor['trend'] == 'decreasing':
                    predictions.append('Oxygen levels may require intervention within 30-60 minutes')
                elif factor['type'] == 'blood_pressure' and factor['trend'] == 'increasing':
                    predictions.append('Blood pressure trending upward - monitor closely')
                elif factor['type'] == 'temperature' and factor['trend'] == 'increasing':
                    predictions.append('Fever may worsen - consider intervention')
        
        # Optionally consult AI (Gemini) to refine/override assessment
        try:
            patient = Patient.query.get(patient_id)
            ai_advice = self.ai_consult(patient, vitals, risk_score, risk_factors)
            if ai_advice:
                # Apply suggested numeric score if provided
                if 'suggested_score' in ai_advice:
                    try:
                        risk_score = int(ai_advice['suggested_score'])
                    except Exception:
                        pass
                # Apply suggested level if provided
                if 'suggested_level' in ai_advice:
                    risk_level = ai_advice['suggested_level']

                # Attach AI note to predictions for visibility in UI
                note = ai_advice.get('note')
                if note:
                    predictions.insert(0, f"AI: {note}")
        except Exception as e:
            logging.debug(f"AI advice skipped due to error: {e}")

        return {
            'risk_level': risk_level,
            'risk_score': min(int(risk_score), 100),
            'risk_factors': risk_factors,
            'predictions': predictions,
            'analyzed_at': datetime.now().isoformat(),
            'vital_count': len(vitals)
        }

    def ai_consult(self, patient, vitals, current_score, risk_factors):
        """Optional: consult Gemini to get an AI opinion on risk.
        Returns a dict with optional 'suggested_level' and 'suggested_score' and a note.
        This call is best-effort and will not raise on error.
        """
        from app import genai, gemini_model
        if genai is None:
            return None

        try:
            # Build a concise prompt summarizing patient and recent vitals
            vitals_summary = []
            for v in vitals[:10]:
                t = v.recorded_at.isoformat() if v.recorded_at else ''
                vitals_summary.append(f"{t}: HR={v.heart_rate or 'n/a'}, BP={v.blood_pressure_systolic or 'n/a'}/{v.blood_pressure_diastolic or 'n/a'}, O2={v.oxygen_saturation or 'n/a'}%, Temp={v.temperature or 'n/a'}F, RR={v.respiratory_rate or 'n/a'}")

            prompt = (
                f"You are a clinical risk assistant. Evaluate the following patient vitals and the computed risk score {current_score}. "
                f"Patient: {patient.full_name} (ID: {patient.patient_id}), age={patient.age}, status={patient.status}.\n"
                f"Recent vitals (most recent first):\n" + "\n".join(vitals_summary) + "\n"
                f"Risk factors: {risk_factors}\n"
                "Provide a short recommendation in one line and optionally suggest a risk level (critical/high/moderate/low/stable) and a suggested numeric score (0-100)."
            )

            # Attempt to call Gemini; support both genai.generate and gemini_model.generate APIs
            resp_text = None
            try:
                if hasattr(genai, 'generate'):
                    out = genai.generate(model='gemini-2.5-flash', input=prompt)
                    # Attempt to extract text
                    if isinstance(out, dict):
                        # google generativeai may return candidates
                        cand = out.get('candidates') or out.get('outputs')
                        if cand:
                            first = cand[0]
                            resp_text = first.get('output') or first.get('content') or str(first)
                    else:
                        resp_text = str(out)
                elif gemini_model is not None and hasattr(gemini_model, 'generate'):
                    out = gemini_model.generate(prompt)
                    resp_text = str(out)
            except Exception:
                # If the higher-level generate fails, fallback to a safe str on object
                try:
                    resp_text = str(out)
                except Exception:
                    resp_text = None

            if not resp_text:
                return None

            # Parse suggested level and numeric score if present
            suggested = {}
            txt = resp_text.lower()
            if 'critical' in txt:
                suggested['suggested_level'] = 'critical'
            elif 'high' in txt:
                suggested['suggested_level'] = 'high'
            elif 'moderate' in txt:
                suggested['suggested_level'] = 'moderate'
            elif 'low' in txt:
                suggested['suggested_level'] = 'low'
            elif 'stable' in txt:
                suggested['suggested_level'] = 'stable'

            m = re.search(r"(score|score:?)\s*(\d{1,3})", txt)
            if m:
                try:
                    suggested['suggested_score'] = max(0, min(100, int(m.group(2))))
                except Exception:
                    pass

            suggested['note'] = resp_text.strip()[:1000]
            return suggested
        except Exception as e:
            logging.error(f"AI consult failed: {e}")
            return None
    
    def get_early_warning_score(self, vital):
        score = 0
        
        if vital.respiratory_rate:
            if vital.respiratory_rate <= 8:
                score += 3
            elif vital.respiratory_rate <= 11:
                score += 1
            elif vital.respiratory_rate >= 25:
                score += 3
            elif vital.respiratory_rate >= 21:
                score += 2
        
        if vital.oxygen_saturation:
            if vital.oxygen_saturation <= 91:
                score += 3
            elif vital.oxygen_saturation <= 93:
                score += 2
            elif vital.oxygen_saturation <= 95:
                score += 1
        
        if vital.heart_rate:
            if vital.heart_rate <= 40:
                score += 3
            elif vital.heart_rate <= 50:
                score += 1
            elif vital.heart_rate >= 131:
                score += 3
            elif vital.heart_rate >= 111:
                score += 2
            elif vital.heart_rate >= 91:
                score += 1
        
        if vital.blood_pressure_systolic:
            if vital.blood_pressure_systolic <= 90:
                score += 3
            elif vital.blood_pressure_systolic <= 100:
                score += 2
            elif vital.blood_pressure_systolic >= 220:
                score += 3
        
        if vital.temperature:
            if vital.temperature <= 95:
                score += 3
            elif vital.temperature >= 102.2:
                score += 2
            elif vital.temperature >= 100.4:
                score += 1
        
        return score


def create_predictive_alert(patient_id, risk_analysis):
    # Only create alerts for high or critical risk to reduce noise
    from app import db
    from models import Patient, Alert
    from alert_router import send_to_n8n_webhook
    if risk_analysis['risk_level'] not in ['critical', 'high']:
        return
    
    patient = Patient.query.get(patient_id)
    if not patient:
        return
    
    existing = Alert.query.filter_by(
        patient_id=patient_id,
        alert_type='predictive_warning',
        is_acknowledged=False
    ).first()
    
    if existing:
        existing.message = f"Risk Score: {risk_analysis['risk_score']}. " + "; ".join(risk_analysis.get('predictions', []))
        existing.severity = 'critical' if risk_analysis['risk_level'] == 'critical' else 'warning'
        existing.created_at = datetime.now()
        db.session.commit()
        try:
            send_to_n8n_webhook(existing)
        except Exception:
            pass
    else:
        alert = Alert(
            patient_id=patient_id,
            alert_type='predictive_warning',
            severity='critical' if risk_analysis['risk_level'] == 'critical' else 'warning',
            title=f"AI Risk Alert - {patient.full_name}",
            message=f"Risk Score: {risk_analysis['risk_score']}. " + "; ".join(risk_analysis.get('predictions', ['Early intervention recommended']))
        )
        db.session.add(alert)
        db.session.commit()
        try:
            send_to_n8n_webhook(alert)
        except Exception:
            pass


risk_predictor = RiskPredictor()


def analyze_all_patients():
    # Use a simple, non-transactional approach to avoid SQLAlchemy context issues
    from models import Patient
    try:
        patients = Patient.query.filter(Patient.status.in_(['admitted', 'icu', 'emergency'])).all()
    except Exception as e:
        logging.error(f"Error fetching patients: {e}")
        return []

    results = []
    for patient in patients:
        try:
            pid = patient.id
            pname = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
            room = patient.room_number or ''
            
            analysis = risk_predictor.analyze_patient_risk(pid)
            results.append({
                'patient_id': pid,
                'patient_name': pname,
                'room': room,
                **analysis
            })

            if analysis['risk_level'] in ['critical', 'high']:
                create_predictive_alert(pid, analysis)

        except Exception as e:
            logging.error(f"Error analyzing patient {pid}: {e}")

    return results
