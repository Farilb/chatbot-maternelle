from pymongo import MongoClient
from datetime import datetime
import os
from bson import ObjectId
import json

class MongoDBManager:
    def __init__(self):
        self.uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/chatbot-sante')
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Établit la connexion à MongoDB"""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Test de connexion
            self.client.admin.command('ping')
            self.db = self.client.get_database()
            print("✅ Connecté à MongoDB avec succès")
            self.init_db()
        except Exception as e:
            print(f"❌ Erreur de connexion MongoDB: {e}")
            print("💡 Vérifiez que MongoDB est démarré: mongod")
            raise e
    
    def init_db(self):
        """Initialise les collections et indexes"""
        try:
            # Collection utilisateurs
            users_col = self.db['users']
            users_col.create_index('email', unique=True, sparse=True)
            users_col.create_index('phone', unique=True, sparse=True)
            
            # Collection consultations
            consultations_col = self.db['consultations']
            consultations_col.create_index('user_id')
            consultations_col.create_index([('user_id', 1), ('date_consultation', -1)])
            consultations_col.create_index('urgency')
            
            # Collection grossesses
            pregnancies_col = self.db['pregnancies']
            pregnancies_col.create_index('user_id', unique=True)
            pregnancies_col.create_index('due_date')
            
            print("✅ Base de données MongoDB initialisée")
        except Exception as e:
            print(f"⚠️ Erreur initialisation MongoDB: {e}")
    
    def save_consultation(self, user_id, question, response, urgency='low'):
        """Sauvegarde une consultation"""
        try:
            consultations_col = self.db['consultations']
            
            consultation_data = {
                'user_id': user_id,
                'question': question,
                'response': response,
                'urgency': urgency,
                'date_consultation': datetime.utcnow(),
                'status': 'completed'
            }
            
            result = consultations_col.insert_one(consultation_data)
            print(f"💾 Consultation sauvegardée: {question[:50]}...")
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Erreur sauvegarde consultation: {e}")
            return None
    
    def get_user_consultations(self, user_id, limit=10):
        """Récupère l'historique des consultations d'un utilisateur"""
        try:
            consultations_col = self.db['consultations']
            
            consultations = list(consultations_col.find(
                {'user_id': user_id}
            ).sort('date_consultation', -1).limit(limit))
            
            # Conversion des ObjectId en string pour JSON
            for consult in consultations:
                consult['_id'] = str(consult['_id'])
                if isinstance(consult.get('date_consultation'), datetime):
                    consult['date_consultation'] = consult['date_consultation'].isoformat()
            
            return consultations
        except Exception as e:
            print(f"❌ Erreur récupération consultations: {e}")
            return []
    
    def save_user(self, user_data):
        """Sauvegarde un nouvel utilisateur"""
        try:
            users_col = self.db['users']
            
            # Préparation des données
            user_data['date_creation'] = datetime.utcnow()
            user_data['date_modification'] = datetime.utcnow()
            
            # Conversion des enfants si présents
            if 'children' in user_data:
                for child in user_data['children']:
                    if 'birth_date' in child and isinstance(child['birth_date'], str):
                        child['birth_date'] = datetime.fromisoformat(child['birth_date'].replace('Z', '+00:00'))
            
            result = users_col.insert_one(user_data)
            user_id = str(result.inserted_id)
            print(f"👤 Utilisateur sauvegardé: {user_data.get('prenom', 'Anonyme')}")
            return user_id
        except Exception as e:
            print(f"❌ Erreur sauvegarde utilisateur: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Trouve un utilisateur par son ID"""
        try:
            users_col = self.db['users']
            user = users_col.find_one({'_id': ObjectId(user_id)})
            
            if user:
                user['_id'] = str(user['_id'])
                # Conversion des dates pour JSON
                for key in ['date_creation', 'date_modification']:
                    if key in user and isinstance(user[key], datetime):
                        user[key] = user[key].isoformat()
                
                # Conversion des dates des enfants
                if 'children' in user:
                    for child in user['children']:
                        if 'birth_date' in child and isinstance(child['birth_date'], datetime):
                            child['birth_date'] = child['birth_date'].isoformat()
            
            return user
        except Exception as e:
            print(f"❌ Erreur recherche utilisateur: {e}")
            return None
    
    def save_pregnancy(self, pregnancy_data):
        """Sauvegarde les données de grossesse"""
        try:
            pregnancies_col = self.db['pregnancies']
            
            # Conversion des dates
            if 'start_date' in pregnancy_data and isinstance(pregnancy_data['start_date'], str):
                pregnancy_data['start_date'] = datetime.fromisoformat(pregnancy_data['start_date'].replace('Z', '+00:00'))
            
            if 'due_date' in pregnancy_data and isinstance(pregnancy_data['due_date'], str):
                pregnancy_data['due_date'] = datetime.fromisoformat(pregnancy_data['due_date'].replace('Z', '+00:00'))
            
            pregnancy_data['created_at'] = datetime.utcnow()
            pregnancy_data['updated_at'] = datetime.utcnow()
            
            # Vérifier si une grossesse existe déjà pour cet utilisateur
            existing = pregnancies_col.find_one({'user_id': pregnancy_data['user_id']})
            if existing:
                result = pregnancies_col.update_one(
                    {'_id': existing['_id']},
                    {'$set': pregnancy_data}
                )
                pregnancy_id = str(existing['_id'])
                print(f"🤰 Grossesse mise à jour: {pregnancy_id}")
            else:
                result = pregnancies_col.insert_one(pregnancy_data)
                pregnancy_id = str(result.inserted_id)
                print(f"🤰 Nouvelle grossesse sauvegardée: {pregnancy_id}")
            
            return pregnancy_id
        except Exception as e:
            print(f"❌ Erreur sauvegarde grossesse: {e}")
            return None
    
    def get_user_pregnancy(self, user_id):
        """Récupère la grossesse en cours d'un utilisateur"""
        try:
            pregnancies_col = self.db['pregnancies']
            pregnancy = pregnancies_col.find_one({'user_id': user_id})
            
            if pregnancy:
                pregnancy['_id'] = str(pregnancy['_id'])
                # Conversion des dates pour JSON
                for key in ['start_date', 'due_date', 'created_at', 'updated_at']:
                    if key in pregnancy and isinstance(pregnancy[key], datetime):
                        pregnancy[key] = pregnancy[key].isoformat()
            
            return pregnancy
        except Exception as e:
            print(f"❌ Erreur récupération grossesse: {e}")
            return None
    
    def save_child_info(self, user_id, child_data):
        """Ajoute un enfant au profil utilisateur"""
        try:
            users_col = self.db['users']
            
            # Conversion de la date de naissance
            if 'birth_date' in child_data and isinstance(child_data['birth_date'], str):
                child_data['birth_date'] = datetime.fromisoformat(child_data['birth_date'].replace('Z', '+00:00'))
            
            child_data['created_at'] = datetime.utcnow()
            
            result = users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$push': {'children': child_data}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Erreur sauvegarde enfant: {e}")
            return False
    
    def update_user_profile(self, user_id, update_data):
        """Met à jour le profil utilisateur"""
        try:
            users_col = self.db['users']
            update_data['date_modification'] = datetime.utcnow()
            
            result = users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Erreur mise à jour utilisateur: {e}")
            return False

# Instance globale de la base de données
try:
    db_manager = MongoDBManager()
    print("🚀 MongoDBManager initialisé avec succès")
except Exception as e:
    print(f"💥 Échec critique de MongoDB: {e}")
    print("❌ L'application ne peut pas démarrer sans base de données")
    exit(1)

# Fonctions d'interface pour Flask
def init_db():
    return db_manager.init_db()

def save_consultation(user_id, question, response, urgency='low'):
    return db_manager.save_consultation(user_id, question, response, urgency)

def get_user_consultations(user_id, limit=10):
    return db_manager.get_user_consultations(user_id, limit)

def format_date_for_display(date_value):
    """Formate une date pour l'affichage, qu'elle soit string ou datetime"""
    if not date_value:
        return ""
    
    if isinstance(date_value, str):
        # Si c'est une string ISO, extraire la partie date
        if 'T' in date_value:
            return date_value.split('T')[0]
        return date_value[:10]
    elif hasattr(date_value, 'strftime'):
        # Si c'est un objet datetime
        return date_value.strftime('%Y-%m-%d')
    else:
        return str(date_value)