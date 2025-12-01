from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
from datetime import datetime, timedelta
import json
from bson import ObjectId
from dotenv import load_dotenv
from functools import wraps

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

# 🔐 DECORATEUR D'AUTHENTIFICATION
def login_required(f):
    """Décorateur pour vérifier si l'utilisateur est connecté"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'registered':
            flash("🔒 Vous devez créer votre profil pour accéder à cette fonctionnalité", "warning")
            return redirect(url_for('profile_setup'))
        return f(*args, **kwargs)
    return decorated_function

def guest_allowed(f):
    """Décorateur pour les pages accessibles aux invités"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Initialiser une session guest si nécessaire
        if 'user_id' not in session:
            session['user_id'] = str(ObjectId())
            session['user_type'] = 'guest'
            session.permanent = True
        return f(*args, **kwargs)
    return decorated_function

# Middleware pour gérer l'utilisateur
@app.before_request
def before_request():
    """Vérifie et initialise la session utilisateur"""
    if 'user_id' not in session:
        session['user_id'] = str(ObjectId())
        session['user_type'] = 'guest'
        session.permanent = True
    
    app.jinja_env.globals['user_type'] = session.get('user_type', 'guest')
    app.jinja_env.globals['is_authenticated'] = session.get('user_type') == 'registered'

# Routes principales
@app.route('/')
@guest_allowed
def index():
    """Page d'accueil - Accessible à tous"""
    return render_template('index.html')

@app.route('/chat')
@login_required
def chat():
    """Interface de chat - Réservée aux utilisateurs inscrits"""
    user_id = session.get('user_id')
    consultations = get_user_consultations(user_id, 10)
    return render_template('chat.html', consultations=consultations)

@app.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord - Réservé aux utilisateurs inscrits"""
    try:
        user_id = session.get('user_id')
        
        pregnancy_data = db_manager.get_user_pregnancy(user_id)
        consultations = get_user_consultations(user_id, 5)
        user_data = db_manager.get_user_by_id(user_id)
        
        # 🔥 CORRECTION : Calculer week_current et trimester pour le dashboard
        week_current = 0
        trimester = 1
        if pregnancy_data:
            pregnancy_obj = Pregnancy(pregnancy_data)
            week_current = pregnancy_obj.calculate_week()
            trimester = pregnancy_obj.trimester
            
            # Mettre à jour les données pour le template
            pregnancy_data['week_current'] = week_current
            pregnancy_data['trimester'] = trimester
        
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
                             vaccine_reminders=vaccine_reminders[:5],
                             week_current=week_current,  # 🔥 AJOUT
                             trimester=trimester)        # 🔥 AJOUT
    
    except Exception as e:
        print(f"❌ Erreur dashboard: {e}")
        flash("Erreur lors du chargement du tableau de bord", "error")
        return redirect(url_for('index'))

@app.route('/pregnancy-tracker')
@login_required
def pregnancy_tracker():
    """Suivi de grossesse - Réservé aux utilisateurs inscrits"""
    try:
        user_id = session.get('user_id')
        pregnancy_data = db_manager.get_user_pregnancy(user_id)
        
        baby_development = "Aucune grossesse enregistrée"
        week_current = 0
        trimester = 1
        
        if pregnancy_data:
            # 🔥 CORRECTION : Créer un objet Pregnancy pour avoir les méthodes
            pregnancy_obj = Pregnancy(pregnancy_data)
            week_current = pregnancy_obj.calculate_week()
            trimester = pregnancy_obj.trimester
            baby_development = pregnancy_obj.get_baby_development()
            
            # 🔥 Mettre à jour les données pour le template
            pregnancy_data['week_current'] = week_current
            pregnancy_data['trimester'] = trimester
        
        return render_template('pregnancy_tracker.html', 
                             pregnancy=pregnancy_data,
                             baby_development=baby_development,
                             week_current=week_current,
                             trimester=trimester)
    
    except Exception as e:
        print(f"❌ Erreur pregnancy_tracker: {e}")
        flash("Erreur lors du chargement du suivi de grossesse", "error")
        return redirect(url_for('dashboard'))

@app.route('/profile-setup')
@guest_allowed
def profile_setup():
    """Configuration du profil utilisateur - Accessible à tous"""
    return render_template('profile_setup.html')

@app.route('/emergency')
@guest_allowed
def emergency_info():
    """Page d'information d'urgence - Accessible à tous"""
    return render_template('emergency.html')

@app.route('/logout')
def logout():
    """Déconnexion de l'utilisateur"""
    session.clear()
    flash("👋 Vous avez été déconnecté avec succès", "info")
    return redirect(url_for('index'))

# 🔒 PROTECTION DES API
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """Endpoint pour le chat - Réservé aux utilisateurs inscrits"""
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
@guest_allowed
def update_profile():
    """Mise à jour du profil utilisateur - Accessible à tous"""
    try:
        data = request.get_json()
        print(f"📥 Données reçues du frontend: {data}")
        
        user_id = session.get('user_id')
        
        if not user_id:
            user_id = str(ObjectId())
            session['user_id'] = user_id
        
        # Validation des données requises
        required_fields = ['prenom', 'phone']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Le champ {field} est obligatoire'}), 400
        
        # Préparation des données pour MongoDB
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
        
        print(f"💾 Tentative de sauvegarde...")
        
        # Sauvegarde dans MongoDB
        user_mongo_id = db_manager.save_user(user_data)
        
        if not user_mongo_id:
            return jsonify({'error': 'Échec de la création du profil'}), 500
        
        # 🔥 CORRECTION : Bien mettre à jour la session
        session['user_type'] = 'registered'
        session['user_profile'] = {
            'prenom': user_data['prenom'],
            'nom': user_data['nom'],
            'email': user_data.get('email', ''),
            'phone': user_data['phone']
        }
        session['user_mongo_id'] = str(user_mongo_id)
        
        # 🔥 FORCER la sauvegarde de la session
        session.modified = True
        
        print(f"✅ Profil créé avec succès! User ID: {user_mongo_id}")
        print(f"🔐 Session mise à jour: user_type={session.get('user_type')}")
        
        return jsonify({
            'status': 'success',
            'user_id': str(user_mongo_id),
            'message': 'Profil créé avec succès ! Vous pouvez maintenant utiliser toutes les fonctionnalités.'
        })
    
    except ValueError as e:
        print(f"❌ Erreur de doublon: {e}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        print(f"❌ Erreur serveur: {e}")
        import traceback
        print(f"📋 Stack trace: {traceback.format_exc()}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# Les autres routes API protégées
@app.route('/api/pregnancy', methods=['POST'])
@login_required
def update_pregnancy():
    """Crée ou met à jour une grossesse pour l'utilisateur connecté"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Utilisateur non identifié'}), 401
        
        if 'start_date' not in data:
            return jsonify({'error': 'Date de début requise'}), 400
        
        # Conversion et calcul des dates
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        due_date = start_date + timedelta(days=280)  # 40 semaines
        
        pregnancy_data = {
            'user_id': user_id,
            'start_date': start_date,
            'due_date': due_date,
            'medical_history': data.get('medical_history', {}),
            'appointments': data.get('appointments', []),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Sauvegarde dans MongoDB
        pregnancy_id = db_manager.save_pregnancy(pregnancy_data)
        
        if not pregnancy_id:
            return jsonify({'error': 'Erreur sauvegarde grossesse'}), 500
        
        # Calcul des informations de grossesse
        pregnancy_obj = Pregnancy(pregnancy_data)
        current_week = pregnancy_obj.calculate_week()
        trimester = pregnancy_obj.trimester
        
        return jsonify({
            'status': 'success', 
            'pregnancy_id': pregnancy_id,
            'due_date': due_date.strftime('%d/%m/%Y'),
            'current_week': current_week,
            'trimester': trimester,
            'message': 'Grossesse enregistrée avec succès !'
        })
    
    except ValueError as e:
        print(f"❌ Erreur format date: {e}")
        return jsonify({'error': 'Format de date invalide. Utilisez YYYY-MM-DD'}), 400
    except Exception as e:
        print(f"❌ Erreur grossesse: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/baby-development')
@login_required
def baby_development():
    """Retourne le développement du bébé selon la semaine"""
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
@login_required
def add_child():
    """Ajoute un enfant au profil utilisateur"""
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
@login_required
def get_vaccine_reminders():
    """Retourne les rappels de vaccins pour l'utilisateur connecté"""
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
@login_required
def get_consultations():
    """Retourne l'historique des consultations de l'utilisateur connecté"""
    try:
        user_id = session.get('user_id')
        limit = request.args.get('limit', 10, type=int)
        
        consultations = get_user_consultations(user_id, limit)
        return jsonify({'consultations': consultations})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Routes utilitaires (accessibles à tous)
@app.route('/health')
def health_check():
    """Endpoint de santé de l'application - Accessible à tous"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'MongoDB',
        'version': '1.0.0'
    })


@app.route('/debug-session')
def debug_session():
    """Route de debug pour vérifier la session"""
    return jsonify({
        'user_id': session.get('user_id'),
        'user_type': session.get('user_type'),
        'is_authenticated': session.get('user_type') == 'registered',
        'user_profile': session.get('user_profile')
    })
# Gestion des erreurs
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(error):
    flash("🔒 Accès refusé - Authentification requise", "error")
    return redirect(url_for('profile_setup'))

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Lancement du Chatbot Santé Maternelle avec Authentification...")
    print(f"📍 URL: http://localhost:{port}")
    print(f"🔧 Mode debug: {debug}")
    print(f"🔒 Authentification: OBLIGATOIRE pour le chat")
    print(f"🗄️ Base de données: MongoDB")
    
    app.run(debug=debug, host='0.0.0.0', port=port)