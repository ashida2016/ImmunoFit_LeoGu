from extensions import db
from datetime import datetime

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    bmi = db.Column(db.Float)
    comorbidities = db.Column(db.String(255))
    medication_history = db.Column(db.String(255))
    
    # relations
    assessments = db.relationship('Assessment', backref='patient', lazy=True)
    sessions = db.relationship('ExerciseSession', backref='patient', lazy=True)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Clinical physiological markers
    lymphocytes = db.Column(db.Float)
    neutrophils = db.Column(db.Float)
    nlr = db.Column(db.Float) # neutrophils to lymphocytes ratio
    crp = db.Column(db.Float)
    
    # Molecular & Gene expression
    dcn = db.Column(db.Float) # Decorin
    ifng = db.Column(db.Float)
    cd8a = db.Column(db.Float)
    gzmb = db.Column(db.Float)
    pdcd1 = db.Column(db.Float)
    ctla4 = db.Column(db.Float)
    mki67 = db.Column(db.Float)
    chek1 = db.Column(db.Float)
    wee1 = db.Column(db.Float)
    
    # Advanced 3D Space Metrics (derived or inputted)
    activation = db.Column(db.Float)
    exhaustion = db.Column(db.Float)
    proliferation = db.Column(db.Float)
    
    # Calculated metrics
    baseline_irs = db.Column(db.Float)
    delta_irs = db.Column(db.Float)
    predicted_response = db.Column(db.Float) # Probability

class ExerciseSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    exercise_type = db.Column(db.String(50)) # Aerobic, Resistance
    duration = db.Column(db.Integer) # in minutes
    intensity = db.Column(db.String(50)) # Low, Moderate, High
