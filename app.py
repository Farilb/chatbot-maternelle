from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from datetime import datetime, timedelta
import json
from bson import ObjectId
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'sante_maternelle_secret_key')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Import des modules MongoDB
from nlp.processor import process_question
from services.database import init_db, save_consultation, get_user_consultations, db_manager
from services.notification import send_sms_alert
from services.vaccine_tracker import VaccineTracker
from models.pregnancy import Pregnancy
from models.user import User

print("✅ Tous les modules MongoDB chargés avec succès")

# Initialisation au démarrage
with app.app_context():
    try:
        init_db()
        print("✅ Application initialisée avec succès")
    except Exception as e:
        print(f"❌ Erreur initialisation: {e}")

# Middleware pour gérer l'utilisateur
@app.before_request
def before_request():
    """Vérifie et initialise la session utilisateur"""
    if 'user_id' not in session:
        session['user_id'] = str(ObjectId())
        session['user_type'] = 'guest'
        session.permanent = True
    
    app.jinja_env.globals['user_type'] = session.get('user_type', 'guest')

# Routes principales
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    user_id = session.get('user_id')
    consultations = get_user_consultations(user_id, 10)
    return render_template('chat.html', consultations=consultations)

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    
    if not user_id or session.get('user_type') == 'guest':
        return redirect(url_for('profile_setup'))
    
    pregnancy_data = db_manager.get_user_pregnancy(user_id)
    consultations = get_user_consultations(user_id, 5)
    user_data = db_manager.get_user_by_id(user_id)
    
    vaccine_reminders = []
    if user_data and 'children' in user_data:
        tracker = VaccineTracker()
        for child in user_data.get('children', []):
            if 'birth_date' in child:
                birth_date = child['birth_date']
                reminders = tracker.get_upcoming_vaccines(birth_date)
                for rem in reminders:
                    rem['child_name'] = child.get('name', 'Bébé')
                vaccine_reminders.extend(reminders)
    
    return render_template('dashboard.html', 
                         pregnancy=pregnancy_data,
                         consultations=consultations,
                         user=user_data,
                         vaccine_reminders=vaccine_reminders[:5])

@app.route('/pregnancy-tracker')
def pregnancy_tracker():
    user_id = session.get('user_id')
    pregnancy_data = db_manager.get_user_pregnancy(user_id)
    
    baby_development = "Aucune grossesse enregistrée"
    if pregnancy_data:
        pregnancy = Pregnancy(pregnancy_data)
        baby_development = pregnancy.get_baby_development()
    
    return render_template('pregnancy_tracker.html', 
                         pregnancy=pregnancy_data,
                         baby_development=baby_development)

@app.route('/profile-setup')
def profile_setup():
    return render_template('profile_setup.html')

@app.route('/emergency')
def emergency_info():
    return render_template('emergency.html')

# API Routes
@app.route('/api/chat', methods=['POST'])
def chat_api():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        user_message = data.get('message', '').strip()
        user_id = session.get('user_id', 'anonymous')
        
        if not user_message:
            return jsonify({'error': 'Message vide'}), 400
        
        result = process_question(user_message)
        
        consultation_id = save_consultation(
            user_id=user_id,
            question=user_message,
            response=result['response'],
            urgency=result.get('urgency', 'low')
        )
        
        if result.get('urgency') == 'high':
            user_data = db_manager.get_user_by_id(user_id)
            if user_data and 'phone' in user_data:
                send_sms_alert(
                    user_data['phone'], 
                    f"🔔 Alerte Santé: {user_message[:50]}..."
                )
        
        return jsonify({
            'response': result['response'],
            'urgency': result.get('urgency', 'low'),
            'category': result.get('category', 'general'),
            'consultation_id': consultation_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        print(f"❌ Erreur chat API: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500

@app.route('/api/profile', methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        if not user_id:
            user_id = str(ObjectId())
            session['user_id'] = user_id
        
        user_data = {
            'nom': data.get('nom', ''),
            'prenom': data.get('prenom', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'date_naissance': data.get('date_naissance'),
            'statut': data.get('statut', 'enceinte'),
            'groupe_sanguin': data.get('groupe_sanguin', ''),
            'allergies': data.get('allergies', ''),
            'traitements': data.get('traitements', ''),
            'children': data.get('children', [])
        }
        
        user_id = db_manager.save_user(user_data)
        session['user_type'] = 'registered'
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'message': 'Profil mis à jour avec succès'
        })
    
    except Exception as e:
        print(f"❌ Erreur profil: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pregnancy', methods=['POST'])
def update_pregnancy():
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Utilisateur non identifié'}), 401
        
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        due_date = start_date + timedelta(days=280)
        
        pregnancy_data = {
            'user_id': user_id,
            'start_date': start_date,
            'due_date': due_date,
            'medical_history': data.get('medical_history', {}),
            'appointments': data.get('appointments', [])
        }
        
        pregnancy_id = db_manager.save_pregnancy(pregnancy_data)
        
        return jsonify({
            'status': 'success', 
            'pregnancy_id': pregnancy_id,
            'due_date': due_date.strftime('%d/%m/%Y'),
            'current_week': Pregnancy(pregnancy_data).calculate_week()
        })
    
    except Exception as e:
        print(f"❌ Erreur grossesse: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/baby-development')
def baby_development():
    try:
        user_id = session.get('user_id')
        pregnancy_data = db_manager.get_user_pregnancy(user_id)
        
        if pregnancy_data:
            pregnancy = Pregnancy(pregnancy_data)
            development = pregnancy.get_baby_development()
            return jsonify({
                'development': development, 
                'week': pregnancy.week_current,
                'trimester': pregnancy.trimester
            })
        
        return jsonify({'error': 'Aucune grossesse enregistrée'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/child', methods=['POST'])
def add_child():
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        child_data = {
            'name': data.get('name', ''),
            'birth_date': datetime.strptime(data['birth_date'], '%Y-%m-%d'),
            'gender': data.get('gender', ''),
            'birth_weight': data.get('birth_weight')
        }
        
        success = db_manager.save_child_info(user_id, child_data)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Enfant ajouté avec succès'})
        else:
            return jsonify({'error': 'Erreur sauvegarde enfant'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vaccine-reminders')
def get_vaccine_reminders():
    try:
        user_id = session.get('user_id')
        user_data = db_manager.get_user_by_id(user_id)
        
        reminders = []
        if user_data and 'children' in user_data:
            tracker = VaccineTracker()
            for child in user_data['children']:
                if 'birth_date' in child:
                    birth_date = child['birth_date']
                    child_reminders = tracker.get_upcoming_vaccines(birth_date)
                    for rem in child_reminders:
                        rem['child_name'] = child.get('name', 'Bébé')
                    reminders.extend(child_reminders)
        
        return jsonify({'reminders': reminders})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/consultations')
def get_consultations():
    try:
        user_id = session.get('user_id')
        limit = request.args.get('limit', 10, type=int)
        
        consultations = get_user_consultations(user_id, limit)
        return jsonify({'consultations': consultations})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'MongoDB',
        'version': '1.0.0'
    })

# Gestion des erreurs
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Lancement du Chatbot Santé Maternelle avec MongoDB...")
    print(f"📍 URL: http://localhost:{port}")
    print(f"🔧 Mode debug: {debug}")
    print(f"🗄️ Base de données: MongoDB")
    
    app.run(debug=debug, host='0.0.0.0', port=port)