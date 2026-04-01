from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from extensions import db
from models import Patient, Assessment, ExerciseSession
from translations import TRANSLATIONS
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-for-prototype'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///immunofit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.before_request
def before_request():
    if 'lang' not in session:
        session['lang'] = 'en'
    if 'patient_id' not in session:
        # Default to the first patient if it exists
        session['patient_id'] = 1
 
@app.context_processor
def inject_globals():
    lang = session.get('lang', 'en')
    def t(key):
        return TRANSLATIONS.get(key, {}).get(lang, key)
    
    # Try fetching current patient
    current_patient = None
    try:
        current_patient = Patient.query.get(session.get('patient_id', 1))
    except:
        pass
        
    return dict(t=t, current_lang=lang, current_patient=current_patient)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/patient_mode')
def patient_mode():
    patient_id = session.get('patient_id', 1)
    patient = Patient.query.get_or_404(patient_id)
    # Get latest assessment
    latest_assessment = Assessment.query.filter_by(patient_id=patient.id).order_by(Assessment.timestamp.desc()).first()
    return render_template('patient.html', patient=patient, latest=latest_assessment)

@app.route('/clinician_mode')
def clinician_mode():
    patient_id = session.get('patient_id', 1)
    patient = Patient.query.get_or_404(patient_id)
    assessments = Assessment.query.filter_by(patient_id=patient.id).order_by(Assessment.timestamp.asc()).all()
    latest_assessment = assessments[-1] if assessments else None
    all_patients = Patient.query.all()
    
    # Prepare data for Google Charts
    irs_data = [['Time', 'Baseline IRS', 'Delta IRS']]
    activation_data = [['Time', 'Activation', 'Exhaustion', 'Proliferation']]
    
    for a in assessments:
        t_str = a.timestamp.strftime('%m-%d')
        irs_data.append([t_str, a.baseline_irs or 0, a.delta_irs or 0])
        activation_data.append([t_str, a.activation or 0, a.exhaustion or 0, a.proliferation or 0])
        
    return render_template('clinician.html', 
                           patient=patient, 
                           latest=latest_assessment, 
                           all_patients=all_patients,
                           irs_data=irs_data,
                           activation_data=activation_data)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ['en', 'zh']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/set_patient/<int:pid>')
def set_patient(pid):
    session['patient_id'] = pid
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        # automatically create schema
        db.create_all()
    app.run(debug=True, port=5000)
