"""Run predictive analytics over admitted patients and print results.

Usage (PowerShell):
  python .\run_analysis.py

This script will:
 - ensure synthetic data exists (creates admin and sample staff/patients if missing)
 - run `analyze_all_patients()` from `predictive_analytics.py`
 - print JSON results to stdout
"""
from app import app
from synthetic_data import initialize_synthetic_data
from predictive_analytics import risk_predictor
from models import Patient
import json

if __name__ == "__main__":
    with app.app_context():
      # Initialize synthetic data if not present (safe: it skips existing entries)
      initialize_synthetic_data()

      patients = Patient.query.filter(Patient.status.in_(['admitted', 'icu', 'emergency'])).all()
      results = []

      for p in patients:
        analysis = risk_predictor.analyze_patient_risk(p.id)
        results.append({
          'patient_id': p.id,
          'patient_name': p.full_name,
          'room': p.room_number,
          **analysis
        })

      print(json.dumps(results, indent=2, default=str))
      print(f"Analyzed {len(results)} patients.")
