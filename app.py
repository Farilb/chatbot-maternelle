from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
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
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configuration de l'authentification Flask-Login
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "🔒 Vous devez vous connecter pour accéder à cette page"
login_manager.login_message_category = "warning"

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

# 🔐 Configuration Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Charge l'utilisateur pour Flask-Login"""
    try:
        user_data = db_manager.get_user_by_id(user_id)
        if user_data:
            user = User(user_data)
            return user
    except Exception as e:
        print(f"❌ Erreur chargement utilisateur: {e}")
    return None

# 🔐 DECORATEURS D'AUTHENTIFICATION
def guest_allowed(f):
    """Décorateur pour les pages accessibles aux invités"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Cette fonction permet l'accès sans login
        return f(*args, **kwargs)
    return decorated_function

# Middleware pour gérer l'utilisateur
@app.before_request
def before_request():
    """Vérifie et initialise la session utilisateur"""
    # Variables globales pour les templates
    app.jinja_env.globals['current_user'] = current_user
    app.jinja_env.globals['is_authenticated'] = current_user.is_authenticated

# ============ ROUTES D'AUTHENTIFICATION ============

@app.route('/register', methods=['GET', 'POST'])
@guest_allowed
def register():
    """Page d'inscription"""
    if request.method == 'POST':
        return handle_registration(request.form)
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@guest_allowed
def login():
    """Page de connexion"""
    if request.method == 'POST':
        return handle_login(request.form)
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Déconnexion de l'utilisateur"""
    logout_user()
    flash("👋 Vous avez été déconnecté avec succès", "info")
    return redirect(url_for('index'))

# ============ HANDLERS D'AUTHENTIFICATION ============

def handle_registration(form_data):
    """Gère l'inscription d'un nouvel utilisateur"""
    try:
        # Validation des champs requis
        required_fields = ['prenom', 'email', 'password', 'phone']
        for field in required_fields:
            if not form_data.get(field):
                flash(f"Le champ {field} est obligatoire", "error")
                return render_template('register.html')
        
        email = form_data['email'].strip().lower()
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = db_manager.get_user_by_email(email)
        if existing_user:
            flash("Cet email est déjà utilisé", "error")
            return render_template('register.html')
        
        # Vérifier la confirmation du mot de passe
        if form_data.get('password') != form_data.get('confirm_password'):
            flash("Les mots de passe ne correspondent pas", "error")
            return render_template('register.html')
        
        # Récupérer les données des enfants
        children = []
        child_index = 1
        while True:
            child_name = form_data.get(f'children[{child_index}][name]')
            if not child_name:
                break
            
            child_data = {
                'name': child_name,
                'birth_date': form_data.get(f'children[{child_index}][birth_date]'),
                'gender': form_data.get(f'children[{child_index}][gender]', ''),
                'birth_weight': form_data.get(f'children[{child_index}][birth_weight]')
            }
            
            if child_data['birth_date']:
                children.append(child_data)
            
            child_index += 1
        
        # Créer un nouvel utilisateur avec toutes les informations
        user_data = {
            'prenom': form_data['prenom'].strip(),
            'nom': form_data.get('nom', '').strip(),
            'email': email,
            'phone': form_data['phone'].strip(),
            'date_naissance': form_data.get('date_naissance'),
            'statut': form_data.get('statut', 'enceinte'),
            'groupe_sanguin': form_data.get('groupe_sanguin', ''),
            'allergies': form_data.get('allergies', ''),
            'traitements': form_data.get('traitements', ''),
            'children': children,
            'role': 'user',
            'is_active': True,
            'date_creation': datetime.utcnow()
        }
        
        # Utiliser Bcrypt pour le hash du mot de passe
        user = User(user_data)
        user.password_hash = bcrypt.generate_password_hash(form_data['password']).decode('utf-8')
        
        # Sauvegarder l'utilisateur
        user_id = db_manager.save_user(user.to_dict())
        
        if not user_id:
            flash("Erreur lors de la création du compte", "error")
            return render_template('register.html')
        
        # Si l'utilisateur est enceinte, enregistrer la grossesse
        if form_data.get('statut') in ['enceinte', 'les_deux'] and form_data.get('start_date'):
            try:
                start_date = datetime.strptime(form_data['start_date'], '%Y-%m-%d')
                due_date = start_date + timedelta(days=280)  # 40 semaines
                
                pregnancy_data = {
                    'user_id': user_id,
                    'start_date': start_date,
                    'due_date': due_date,
                    'current_week': int(form_data.get('current_week', 12)),
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                db_manager.save_pregnancy(pregnancy_data)
            except Exception as e:
                print(f"⚠️ Erreur sauvegarde grossesse: {e}")
                # Ne pas bloquer l'inscription si la grossesse échoue
        
        # Connecter l'utilisateur automatiquement
        saved_user_data = db_manager.get_user_by_id(user_id)
        if saved_user_data:
            user_obj = User(saved_user_data)
            login_user(user_obj)
            flash(f"✅ Compte créé avec succès ! Bienvenue {user_obj.prenom}", "success")
            return redirect(url_for('dashboard'))
        
        flash("Erreur lors de la création du compte", "error")
        return render_template('register.html')
        
    except Exception as e:
        print(f"❌ Erreur inscription: {e}")
        flash("Une erreur est survenue lors de l'inscription", "error")
        return render_template('register.html')

def handle_login(form_data):
    """Gère la connexion d'un utilisateur"""
    try:
        email = form_data.get('email', '').strip().lower()
        password = form_data.get('password', '')
        remember = form_data.get('remember') == 'on'
        
        if not email or not password:
            flash("Email et mot de passe requis", "error")
            return render_template('login.html')
        
        # Récupérer l'utilisateur
        user_data = db_manager.get_user_by_email(email)
        
        if not user_data:
            flash("Email ou mot de passe incorrect", "error")
            return render_template('login.html')
        
        # Vérifier le mot de passe
        user = User(user_data)
        
        # Vérifier avec Bcrypt d'abord (si le hash est bcrypt)
        if user.password_hash and user.password_hash.startswith('$2b$'):
            if bcrypt.check_password_hash(user.password_hash, password):
                login_user(user, remember=remember)
                flash(f"👋 Bienvenue {user.prenom} !", "success")
                return redirect(url_for('dashboard'))
        # Sinon vérifier avec l'ancienne méthode SHA256
        elif user.check_password(password):
            # Mettre à jour le hash vers Bcrypt
            user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            db_manager.update_user(user.id, {'password_hash': user.password_hash})
            login_user(user, remember=remember)
            flash(f"👋 Bienvenue {user.prenom} ! (Votre mot de passe a été mis à jour)", "success")
            return redirect(url_for('dashboard'))
        
        flash("Email ou mot de passe incorrect", "error")
        return render_template('login.html')
        
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        flash("Une erreur est survenue lors de la connexion", "error")
        return render_template('login.html')

# ============ ROUTES PRINCIPALES ============

@app.route('/')
@guest_allowed
def index():
    """Page d'accueil - Accessible à tous"""
    return render_template('index.html')

@app.route('/chat')
@login_required
def chat():
    """Interface de chat - Réservée aux utilisateurs connectés"""
    user_id = current_user.id
    consultations = get_user_consultations(user_id, 10)
    return render_template('chat.html', consultations=consultations)

@app.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord - Réservé aux utilisateurs connectés"""
    try:
        user_id = current_user.id
        
        pregnancy_data = db_manager.get_user_pregnancy(user_id)
        consultations = get_user_consultations(user_id, 5)
        user_data = db_manager.get_user_by_id(user_id)
        
        # Calculer week_current et trimester pour le dashboard
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
                             week_current=week_current,
                             trimester=trimester)
    
    except Exception as e:
        print(f"❌ Erreur dashboard: {e}")
        flash("Erreur lors du chargement du tableau de bord", "error")
        # Rediriger vers le profil si erreur
        return redirect(url_for('profile'))

@app.route('/pregnancy_tracker')
@login_required
def pregnancy_tracker():
    """Suivi de grossesse - Réservé aux utilisateurs connectés"""
    try:
        user_id = current_user.id
        pregnancy_data = db_manager.get_user_pregnancy(user_id)
        
        baby_development = "Aucune grossesse enregistrée"
        week_current = 0
        trimester = 1
        
        if pregnancy_data:
            # Créer un objet Pregnancy pour avoir les méthodes
            pregnancy_obj = Pregnancy(pregnancy_data)
            week_current = pregnancy_obj.calculate_week()
            trimester = pregnancy_obj.trimester
            baby_development = pregnancy_obj.get_baby_development()
            
            # Mettre à jour les données pour le template
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

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Page de profil utilisateur"""
    if request.method == 'POST':
        return update_profile(request.form)
    
    try:
        user_data = db_manager.get_user_by_id(current_user.id)
        pregnancy_data = db_manager.get_user_pregnancy(current_user.id)
        
        return render_template('profile_setup.html', 
                             user_data=user_data, 
                             pregnancy=pregnancy_data)
    except Exception as e:
        print(f"❌ Erreur profil: {e}")
        flash("Erreur lors du chargement du profil", "error")
        return redirect(url_for('dashboard'))

def update_profile(form_data):
    """Met à jour le profil utilisateur"""
    try:
        update_data = {
            'prenom': form_data.get('prenom', current_user.prenom),
            'nom': form_data.get('nom', current_user.nom),
            'phone': form_data.get('phone', current_user.phone),
            'date_naissance': form_data.get('date_naissance'),
            'statut': form_data.get('statut', current_user.statut),
            'groupe_sanguin': form_data.get('groupe_sanguin', ''),
            'allergies': form_data.get('allergies', ''),
            'traitements': form_data.get('traitements', ''),
            'date_modification': datetime.utcnow()
        }
        
        # Mise à jour du mot de passe si fourni
        new_password = form_data.get('new_password')
        if new_password:
            if new_password != form_data.get('confirm_password'):
                flash("Les mots de passe ne correspondent pas", "error")
                return redirect(url_for('profile'))
            
            update_data['password_hash'] = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Mettre à jour dans la base de données
        success = db_manager.update_user(current_user.id, update_data)
        
        if success:
            flash("✅ Profil mis à jour avec succès", "success")
        else:
            flash("❌ Erreur lors de la mise à jour du profil", "error")
        
        return redirect(url_for('profile'))
        
    except Exception as e:
        print(f"❌ Erreur mise à jour profil: {e}")
        flash("Erreur lors de la mise à jour du profil", "error")
        return redirect(url_for('profile'))

@app.route('/profile-setup')
@guest_allowed
def profile_setup():
    """Configuration du profil utilisateur - Accessible à tous"""
    # Si l'utilisateur est connecté, rediriger vers le profil
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    # Sinon, rediriger vers l'inscription
    flash("Veuillez d'abord créer un compte pour configurer votre profil", "info")
    return redirect(url_for('register'))

@app.route('/emergency')
@guest_allowed
def emergency_info():
    """Page d'information d'urgence - Accessible à tous"""
    return render_template('emergency.html')

# ============ API ROUTES ============

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """Endpoint pour le chat - Réservé aux utilisateurs connectés"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        user_message = data.get('message', '').strip()
        user_id = current_user.id
        
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

@app.route('/api/profile', methods=['POST', 'PUT'])
@login_required
def api_update_profile():
    """API de mise à jour du profil (pour compatibilité)"""
    try:
        data = request.get_json()
        
        update_data = {
            'prenom': data.get('prenom', current_user.prenom),
            'nom': data.get('nom', current_user.nom),
            'email': data.get('email', current_user.email),
            'phone': data.get('phone', current_user.phone),
            'statut': data.get('statut', current_user.statut),
            'allergies': data.get('allergies', ''),
            'traitements': data.get('traitements', ''),
            'children': data.get('children', []),
            'date_modification': datetime.utcnow()
        }
        
        success = db_manager.update_user(current_user.id, update_data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Profil mis à jour avec succès'
            })
        else:
            return jsonify({'error': 'Erreur lors de la mise à jour'}), 500
    
    except Exception as e:
        print(f"❌ Erreur API profil: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/login', methods=['POST'])
@guest_allowed
def api_login():
    """API de connexion (pour compatibilité AJAX)"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email et mot de passe requis'}), 400
        
        # Récupérer l'utilisateur
        user_data = db_manager.get_user_by_email(email)
        
        if not user_data:
            return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
        
        user = User(user_data)
        
        # Vérifier le mot de passe
        password_valid = False
        
        if user.password_hash and user.password_hash.startswith('$2b$'):
            password_valid = bcrypt.check_password_hash(user.password_hash, password)
        else:
            password_valid = user.check_password(password)
            if password_valid:
                # Mettre à jour vers Bcrypt
                user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
                db_manager.update_user(user.id, {'password_hash': user.password_hash})
        
        if password_valid:
            login_user(user)
            return jsonify({
                'status': 'success',
                'message': 'Connexion réussie !',
                'user': {
                    'prenom': user.prenom,
                    'nom': user.nom,
                    'email': user.email
                }
            })
        else:
            return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
            
    except Exception as e:
        print(f"❌ Erreur API connexion: {e}")
        return jsonify({'error': 'Erreur de connexion'}), 500

# ============ AUTRES ROUTES API ============

@app.route('/api/pregnancy', methods=['POST'])
@login_required
def update_pregnancy():
    """Crée ou met à jour une grossesse pour l'utilisateur connecté"""
    try:
        data = request.get_json()
        user_id = current_user.id
        
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
        user_id = current_user.id
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
        user_id = current_user.id
        
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
        user_id = current_user.id
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
        user_id = current_user.id
        limit = request.args.get('limit', 10, type=int)
        
        consultations = get_user_consultations(user_id, limit)
        return jsonify({'consultations': consultations})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ ROUTES UTILITAIRES ============

@app.route('/health')
def health_check():
    """Endpoint de santé de l'application - Accessible à tous"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'MongoDB',
        'version': '1.0.0',
        'authenticated': current_user.is_authenticated
    })

@app.route('/debug-session')
def debug_session():
    """Route de debug pour vérifier la session"""
    return jsonify({
        'user_id': current_user.id if current_user.is_authenticated else None,
        'is_authenticated': current_user.is_authenticated,
        'user_email': current_user.email if current_user.is_authenticated else None,
        'session_keys': list(session.keys())
    })

# ============ ROUTES NOTIFICATIONS ============

@app.route('/api/notifications')
@login_required
def get_notifications():
    """Retourne les notifications de l'utilisateur"""
    try:
        user_id = current_user.id
        
        # Pour l'instant, retourner des notifications simulées
        notifications = [
            {
                'id': '1',
                'type': 'info',
                'title': 'Bienvenue sur votre tableau de bord',
                'message': 'Votre espace personnalisé est prêt !',
                'read': False,
                'created_at': datetime.utcnow().isoformat()
            }
        ]
        
        # Récupérer les rappels de vaccins
        vaccine_reminders = []
        try:
            user_data = db_manager.get_user_by_id(user_id)
            if user_data and 'children' in user_data:
                tracker = VaccineTracker()
                for child in user_data.get('children', []):
                    if 'birth_date' in child:
                        reminders = tracker.get_upcoming_vaccines(child['birth_date'])
                        for rem in reminders:
                            vaccine_reminders.append({
                                'id': f"vaccine_{len(vaccine_reminders)}",
                                'type': 'vaccine',
                                'title': f'Rappel vaccin - {child.get("name", "Bébé")}',
                                'message': f'{", ".join(rem.get("vaccines", []))} - {rem.get("milestone", "")}',
                                'read': False,
                                'data': rem,
                                'created_at': datetime.utcnow().isoformat()
                            })
        except Exception as e:
            print(f"⚠️ Erreur récupération rappels vaccins: {e}")
        
        notifications.extend(vaccine_reminders)
        
        return jsonify({
            'notifications': notifications,
            'unread_count': len([n for n in notifications if not n.get('read', False)])
        })
    
    except Exception as e:
        print(f"❌ Erreur récupération notifications: {e}")
        return jsonify({'notifications': [], 'unread_count': 0})

@app.route('/api/notifications/<notification_id>/read', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    """Marque une notification comme lue"""
    try:
        success = db_manager.mark_notification_as_read(notification_id, current_user.id)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Notification marquée comme lue'})
        else:
            return jsonify({'error': 'Notification non trouvée'}), 404
    
    except Exception as e:
        print(f"❌ Erreur marquage notification: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_as_read():
    """Marque toutes les notifications comme lues"""
    try:
        success = db_manager.mark_all_notifications_as_read(current_user.id)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Toutes les notifications marquées comme lues'})
        else:
            return jsonify({'error': 'Erreur lors du marquage'}), 500
    
    except Exception as e:
        print(f"❌ Erreur marquage toutes notifications: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/notifications/settings', methods=['POST'])
@login_required
def update_notification_settings():
    """Met à jour les paramètres de notifications"""
    try:
        data = request.get_json()
        notification_type = data.get('type')
        enabled = data.get('enabled', True)
        
        # Mettre à jour les paramètres utilisateur
        success = db_manager.update_notification_settings(
            current_user.id, 
            notification_type, 
            enabled
        )
        
        if success:
            return jsonify({'status': 'success', 'message': 'Paramètres mis à jour'})
        else:
            return jsonify({'error': 'Erreur mise à jour paramètres'}), 500
    
    except Exception as e:
        print(f"❌ Erreur mise à jour paramètres: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/notifications/check')
@login_required
def check_new_notifications():
    """Vérifie s'il y a de nouvelles notifications"""
    try:
        user_id = current_user.id
        last_check = request.args.get('last_check')
        
        # Si pas de last_check, vérifier les 24 dernières heures
        if not last_check:
            last_check = datetime.utcnow() - timedelta(hours=24)
        else:
            # Convertir la string en datetime
            try:
                last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
            except ValueError:
                last_check = datetime.utcnow() - timedelta(hours=24)
        
        # Récupérer les nouvelles notifications depuis last_check
        try:
            new_notifications = db_manager.get_new_notifications(user_id, last_check)
        except AttributeError:
            # Si la méthode n'existe pas, retourner False
            return jsonify({'has_new': False})
        
        has_new = len(new_notifications) > 0
        
        if has_new:
            latest = new_notifications[0]
            return jsonify({
                'has_new': True,
                'new_notification': {
                    'id': str(latest['_id']),
                    'type': latest.get('type', 'info'),
                    'title': latest.get('title', 'Nouvelle notification'),
                    'message': latest.get('message', ''),
                    'data': latest.get('data', {})
                }
            })
        
        return jsonify({'has_new': False})
    
    except Exception as e:
        print(f"❌ Erreur vérification notifications: {e}")
        return jsonify({'has_new': False})

@app.route('/api/test/notification')
@login_required
def test_notification():
    """Route de test pour créer une notification"""
    try:
        # Créer une notification de test
        test_notification = {
            'user_id': current_user.id,
            'type': 'test',
            'title': 'Notification de test',
            'message': f'Ceci est une notification de test envoyée à {datetime.now().strftime("%H:%M:%S")}',
            'read': False,
            'created_at': datetime.utcnow()
        }
        
        # Sauvegarder (si la méthode existe)
        try:
            notification_id = db_manager.save_notification(test_notification)
            print(f"✅ Notification de test créée: {notification_id}")
        except AttributeError:
            print("⚠️ save_notification non disponible, simulation seulement")
        
        return jsonify({
            'status': 'success',
            'message': 'Notification de test créée',
            'notification': {
                'id': 'test_123',
                'type': 'test',
                'title': test_notification['title'],
                'message': test_notification['message'],
                'created_at': test_notification['created_at'].isoformat()
            }
        })
    
    except Exception as e:
        print(f"❌ Erreur test notification: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/stats')
@login_required
def notification_stats():
    """Retourne les statistiques des notifications"""
    try:
        # Statistiques simulées
        stats = {
            'total': 5,
            'unread': 2,
            'last_24h': 3,
            'by_type': {
                'vaccine': {'total': 2, 'unread': 1},
                'appointment': {'total': 1, 'unread': 0},
                'pregnancy': {'total': 2, 'unread': 1}
            }
        }
        
        # Essayer de récupérer les vraies stats si la méthode existe
        try:
            real_stats = db_manager.get_notification_stats(current_user.id)
            if real_stats:
                stats = real_stats
        except AttributeError:
            print("⚠️ get_notification_stats non disponible, utilisation des stats simulées")
        
        return jsonify(stats)
    
    except Exception as e:
        print(f"❌ Erreur stats notifications: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/weekly', methods=['POST'])
@login_required
def send_weekly_notification():
    """Envoie une notification hebdomadaire de grossesse"""
    try:
        data = request.get_json()
        week = data.get('week', 0)
        
        if week <= 0:
            return jsonify({'error': 'Semaine invalide'}), 400
        
        # Envoyer la notification
        try:
            from services.notification import notification_service
            success = notification_service.send_weekly_pregnancy_update(
                current_user.id,
                week,
                calculate_trimester(week),
                get_week_development(week)
            )
        except (ImportError, AttributeError):
            print("⚠️ notification_service non disponible")
            success = False
        
        if success:
            return jsonify({'status': 'success', 'message': 'Notification envoyée'})
        else:
            return jsonify({'error': 'Erreur envoi notification'}), 500
    
    except Exception as e:
        print(f"❌ Erreur envoi notification hebdomadaire: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ============ FONCTIONS UTILITAIRES ============

def get_relative_time(timestamp):
    """Calcule le temps relatif (il y a...)"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return "à l'instant"

def calculate_trimester(week):
    """Calcule le trimestre à partir de la semaine"""
    if week <= 13:
        return 1
    elif week <= 27:
        return 2
    else:
        return 3

def get_week_development(week):
    """Retourne le développement pour la semaine"""
    developments = {
        1: "Première semaine - Début du voyage !",
        4: "Cœur qui commence à battre",
        8: "Tous les organes sont présents",
        12: "Bébé fait ses premiers mouvements",
        16: "Peut sucer son pouce",
        20: "Vous pouvez sentir les mouvements",
        24: "Bébé est viable",
        28: "Ouverture des yeux",
        32: "Bébé prend sa position finale",
        36: "Prêt à naître !",
        40: "Terme - Prêt pour la rencontre !"
    }
    
    closest_week = min(developments.keys(), key=lambda x: abs(x - week))
    return developments.get(closest_week, "Développement en cours")

# ============ GESTION DES ERREURS ============

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(error):
    flash("🔒 Accès refusé - Authentification requise", "error")
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    flash("Une erreur interne est survenue", "error")
    return redirect(url_for('index'))

# ============ POINT D'ENTRÉE ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Lancement du Chatbot Santé Maternelle avec Authentification...")
    print(f"📍 URL: http://localhost:{port}")
    print(f"🔧 Mode debug: {debug}")
    print(f"🔒 Authentification: Flask-Login + Bcrypt")
    print(f"🗄️ Base de données: MongoDB")
    
    app.run(debug=debug, host='0.0.0.0', port=port)