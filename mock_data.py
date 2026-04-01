import random
from datetime import datetime, timedelta
from extensions import db
from models import Patient, Assessment, ExerciseSession
from app import app

def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Patients
        p1 = Patient(name="John Doe", age=58, gender="Male", bmi=27.5, comorbidities="Hypertension", medication_history="Amlodipine")
        p2 = Patient(name="Jane Smith", age=62, gender="Female", bmi=24.1, comorbidities="None", medication_history="None")
        db.session.add_all([p1, p2])
        db.session.commit()
        
        # Base timestamp
        base_time = datetime.utcnow() - timedelta(days=30)
        
        # Generate temporal progression for Patient 1 (improving trajectory)
        for i in range(5):
            eval_time = base_time + timedelta(days=i*7)
            # IRS starts low, increases
            baseline_irs = 30 + i * 12 + random.uniform(-2, 2)
            delta_irs = 5 + i * 3 + random.uniform(-1, 1)
            
            # molecular data (DCN going up, exhaust going down)
            dcn = 1.2 + i * 0.4 + random.uniform(-0.1, 0.1)
            ifng = 3.0 + i * 0.6 + random.uniform(-0.2, 0.2)
            
            # 3D Space Metrics
            activation = 40 + i * 10 + random.uniform(-5, 5)
            exhaustion = 80 - i * 10 + random.uniform(-5, 5)
            proliferation = 50 + i * 8 + random.uniform(-5, 5)
            
            predicted_response = min(95.0, baseline_irs * 0.6 + delta_irs * 1.5)
            
            assessment = Assessment(
                patient_id=p1.id, timestamp=eval_time,
                lymphocytes=2.1 + i*0.1, neutrophils=4.0 - i*0.2, nlr=(4.0 - i*0.2)/(2.1 + i*0.1),
                crp=5.0 - i*0.5,
                dcn=dcn, ifng=ifng, cd8a=4.0+i*0.5, gzmb=3.5+i*0.4,
                pdcd1=6.0-i*0.5, ctla4=4.5-i*0.3, mki67=2.0+i*0.3, chek1=1.5+i*0.2, wee1=2.0+i*0.1,
                activation=activation, exhaustion=exhaustion, proliferation=proliferation,
                baseline_irs=baseline_irs, delta_irs=delta_irs, predicted_response=predicted_response
            )
            db.session.add(assessment)
            
            # Exercise sessions
            if i > 0:
                ex_time = eval_time - timedelta(days=2)
                session = ExerciseSession(patient_id=p1.id, timestamp=ex_time, exercise_type="Aerobic", duration=30, intensity="Moderate")
                db.session.add(session)

        # Generate temporal progression for Patient 2 (stable/slow trajectory)
        for i in range(3):
            eval_time = base_time + timedelta(days=i*7)
            baseline_irs = 45 + random.uniform(-3, 3)
            delta_irs = 2 + random.uniform(-1, 1)
            
            dcn = 0.9 + random.uniform(-0.1, 0.1)
            ifng = 2.5 + random.uniform(-0.2, 0.2)
            
            activation = 35 + random.uniform(-2, 2)
            exhaustion = 60 + random.uniform(-2, 2)
            proliferation = 40 + random.uniform(-2, 2)
            predicted_response = 40.0 + random.uniform(-2, 2)
            
            assessment = Assessment(
                patient_id=p2.id, timestamp=eval_time,
                lymphocytes=1.8, neutrophils=4.5, nlr=4.5/1.8, crp=6.2,
                dcn=dcn, ifng=ifng, cd8a=3.2, gzmb=2.8,
                pdcd1=5.5, ctla4=5.0, mki67=1.8, chek1=1.2, wee1=1.5,
                activation=activation, exhaustion=exhaustion, proliferation=proliferation,
                baseline_irs=baseline_irs, delta_irs=delta_irs, predicted_response=predicted_response
            )
            db.session.add(assessment)
            
        db.session.commit()
        print("Mock data generated successfully!")

if __name__ == '__main__':
    init_db()
