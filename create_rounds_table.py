from app import app, db
from models import Round

def create_rounds_table():
    with app.app_context():
        try:
            Round.__table__.create(db.engine)
            print("Table 'rounds' created successfully.")
        except Exception as e:
            print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_rounds_table()
