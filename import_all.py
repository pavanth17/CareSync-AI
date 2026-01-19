"""Import all application modules to catch import/runtime errors quickly.
Run: python import_all.py
"""
import traceback

modules = [
    'app',
    'models',
    'routes',
    'synthetic_data',
    'vital_simulator',
    'predictive_analytics',
    'alert_router'
]

errors = []
for m in modules:
    try:
        __import__(m)
        print(f"Imported {m} OK")
    except Exception as e:
        print(f"Error importing {m}: {e}")
        traceback.print_exc()
        errors.append((m, e))

if errors:
    print(f"\nImport errors detected: {len(errors)} modules failed")
    for m, e in errors:
        print(f" - {m}: {e}")
else:
    print("\nAll modules imported successfully.")
