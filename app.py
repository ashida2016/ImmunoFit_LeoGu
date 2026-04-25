from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from functools import wraps
from extensions import db
from models import User, Patient, Assessment, ExerciseSession
from translations import TRANSLATIONS
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-for-prototype'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///immunofit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ── Auth Helper ──────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# ── Before-request & Context Processors ──────────────────────
@app.before_request
def before_request():
    if 'lang' not in session:
        session['lang'] = 'en'

@app.context_processor
def inject_globals():
    lang = session.get('lang', 'en')
    def t(key):
        return TRANSLATIONS.get(key, {}).get(lang, key)

    current_user = get_current_user()

    # Resolve current patient
    current_patient = None
    if current_user:
        if current_user.role == 'patient' and current_user.linked_patient_id:
            session['patient_id'] = current_user.linked_patient_id
        if 'patient_id' not in session:
            session['patient_id'] = 1
        try:
            current_patient = Patient.query.get(session.get('patient_id', 1))
        except:
            pass

    return dict(t=t, current_lang=lang, current_patient=current_patient, current_user=current_user)

# ── Auth Routes ──────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            if user.linked_patient_id:
                session['patient_id'] = user.linked_patient_id
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Main Routes ──────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    user = get_current_user()
    if user.role == 'patient':
        return redirect(url_for('patient_mode'))
    else:
        return redirect(url_for('clinician_mode'))

@app.route('/patient_mode')
@login_required
def patient_mode():
    patient_id = session.get('patient_id', 1)
    patient = Patient.query.get_or_404(patient_id)
    latest_assessment = Assessment.query.filter_by(patient_id=patient.id).order_by(Assessment.timestamp.desc()).first()
    return render_template('patient.html', patient=patient, latest=latest_assessment)

@app.route('/clinician_mode')
@login_required
def clinician_mode():
    user = get_current_user()
    if user.role == 'patient':
        flash('Access denied. Patient accounts cannot access Research Mode.', 'warning')
        return redirect(url_for('patient_mode'))

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
@login_required
def set_patient(pid):
    session['patient_id'] = pid
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
