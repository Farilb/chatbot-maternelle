from pymongo import MongoClient
from datetime import datetime, timedelta  # Ajout de timedelta
import os
from bson import ObjectId
import json

class MongoDBManager:
    def __init__(self):
        self.uri = os.getenv('MONGODB_URI')
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
            users_col.create_index([('email', 'text'), ('prenom', 'text'), ('nom', 'text')])
            
            # Collection consultations
            consultations_col = self.db['consultations']
            consultations_col.create_index('user_id')
            consultations_col.create_index([('user_id', 1), ('date_consultation', -1)])
            consultations_col.create_index('urgency')
            
            # Collection grossesses
            pregnancies_col = self.db['pregnancies']
            pregnancies_col.create_index('user_id', unique=True)
            pregnancies_col.create_index('due_date')
            
            # Collection notifications
            notifications_col = self.db['notifications']
            notifications_col.create_index('user_id')
            notifications_col.create_index([('user_id', 1), ('created_at', -1)])
            notifications_col.create_index([('user_id', 1), ('read', 1)])
            
            print("✅ Base de données MongoDB initialisée")
        except Exception as e:
            print(f"⚠️ Erreur initialisation MongoDB: {e}")
    
    # ============ MÉTHODES UTILISATEURS ============
    
    def get_user_by_email(self, email):
        """Trouve un utilisateur par son email (insensible à la casse)"""
        try:
            users_col = self.db['users']
            user = users_col.find_one({'email': email.lower().strip()})
            
            if user:
                user['_id'] = str(user['_id'])
                # Conversion des dates pour JSON
                for key in ['date_creation', 'date_modification', 'date_naissance']:
                    if key in user and isinstance(user[key], datetime):
                        user[key] = user[key].isoformat()
                
                # Conversion des dates des enfants
                if 'children' in user:
                    for child in user['children']:
                        if 'birth_date' in child and isinstance(child['birth_date'], datetime):
                            child['birth_date'] = child['birth_date'].isoformat()
            
            return user
        except Exception as e:
            print(f"❌ Erreur recherche utilisateur par email: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Trouve un utilisateur par son ID"""
        try:
            users_col = self.db['users']
            user = users_col.find_one({'_id': ObjectId(user_id)})
            
            if user:
                user['_id'] = str(user['_id'])
                # Conversion des dates pour JSON
                for key in ['date_creation', 'date_modification', 'date_naissance']:
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
    
    def save_user(self, user_data):
        """Sauvegarde un nouvel utilisateur"""
        try:
            users_col = self.db['users']
            
            # Validation des données requises
            if 'email' not in user_data:
                raise ValueError("L'email est obligatoire")
            
            # Vérifier si l'utilisateur existe déjà
            existing_user = self.get_user_by_email(user_data['email'])
            if existing_user:
                raise ValueError("Un utilisateur avec cet email existe déjà")
            
            # Normaliser l'email
            user_data['email'] = user_data['email'].lower().strip()
            
            # Préparation des données
            user_data.setdefault('date_creation', datetime.utcnow())
            user_data['date_modification'] = datetime.utcnow()
            user_data.setdefault('role', 'user')
            user_data.setdefault('is_active', True)
            
            # Conversion de la date de naissance si présente
            if 'date_naissance' in user_data and isinstance(user_data['date_naissance'], str):
                try:
                    user_data['date_naissance'] = datetime.fromisoformat(
                        user_data['date_naissance'].replace('Z', '+00:00')
                    )
                except:
                    pass  # Garder la string si conversion échoue
            
            # Conversion des enfants si présents
            if 'children' in user_data:
                for child in user_data['children']:
                    if 'birth_date' in child and isinstance(child['birth_date'], str):
                        try:
                            child['birth_date'] = datetime.fromisoformat(
                                child['birth_date'].replace('Z', '+00:00')
                            )
                        except:
                            pass
            
            result = users_col.insert_one(user_data)
            user_id = str(result.inserted_id)
            print(f"👤 Utilisateur sauvegardé: {user_data.get('prenom', 'Anonyme')} ({user_data['email']})")
            return user_id
        except ValueError as e:
            raise e  # Propager les erreurs de validation
        except Exception as e:
            print(f"❌ Erreur sauvegarde utilisateur: {e}")
            return None
    
    def update_user(self, user_id, update_data):
        """Met à jour un utilisateur"""
        try:
            users_col = self.db['users']
            
            # Exclure les champs qui ne doivent pas être mis à jour
            update_data.pop('_id', None)
            update_data.pop('email', None)  # Ne pas permettre de changer l'email
            update_data.pop('date_creation', None)
            
            # Mettre à jour la date de modification
            update_data['date_modification'] = datetime.utcnow()
            
            # Conversion de la date de naissance si présente
            if 'date_naissance' in update_data and isinstance(update_data['date_naissance'], str):
                try:
                    update_data['date_naissance'] = datetime.fromisoformat(
                        update_data['date_naissance'].replace('Z', '+00:00')
                    )
                except:
                    pass
            
            result = users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            success = result.modified_count > 0
            if success:
                print(f"✅ Utilisateur {user_id} mis à jour")
            return success
        except Exception as e:
            print(f"❌ Erreur mise à jour utilisateur: {e}")
            return False
    
    def delete_user(self, user_id):
        """Supprime un utilisateur et ses données associées"""
        try:
            users_col = self.db['users']
            consultations_col = self.db['consultations']
            pregnancies_col = self.db['pregnancies']
            notifications_col = self.db['notifications']
            
            # Supprimer l'utilisateur
            user_result = users_col.delete_one({'_id': ObjectId(user_id)})
            
            # Supprimer les consultations associées
            consultations_col.delete_many({'user_id': user_id})
            
            # Supprimer les données de grossesse associées
            pregnancies_col.delete_many({'user_id': user_id})
            
            # Supprimer les notifications associées
            notifications_col.delete_many({'user_id': user_id})
            
            success = user_result.deleted_count > 0
            if success:
                print(f"🗑️ Utilisateur {user_id} supprimé")
            return success
        except Exception as e:
            print(f"❌ Erreur suppression utilisateur: {e}")
            return False
    
    def verify_user_credentials(self, email, password):
        """Vérifie les identifiants de connexion (support Bcrypt et SHA256)"""
        try:
            from flask_bcrypt import Bcrypt
            from models.user import User
            
            bcrypt = Bcrypt()
            user_data = self.get_user_by_email(email)
            
            if not user_data:
                return None
            
            user = User(user_data)
            password_hash = user.password_hash
            
            # Vérifier avec Bcrypt d'abord (si le hash commence par $2b$)
            if password_hash and password_hash.startswith('$2b$'):
                if bcrypt.check_password_hash(password_hash, password):
                    return user_data
            # Sinon vérifier avec l'ancienne méthode SHA256
            elif user.check_password(password):
                # Mettre à jour le hash vers Bcrypt pour la prochaine connexion
                new_hash = bcrypt.generate_password_hash(password).decode('utf-8')
                self.update_user(user.id, {'password_hash': new_hash})
                return user_data
            
            return None
        except Exception as e:
            print(f"❌ Erreur vérification credentials: {e}")
            return None
    
    def search_users(self, query, limit=10):
        """Recherche des utilisateurs par nom, prénom ou email"""
        try:
            users_col = self.db['users']
            
            # Recherche textuelle
            results = list(users_col.find(
                {'$text': {'$search': query}},
                {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'})]).limit(limit))
            
            # Formatage des résultats
            for user in results:
                user['_id'] = str(user['_id'])
                
            return results
        except Exception as e:
            print(f"❌ Erreur recherche utilisateurs: {e}")
            return []
    
    # ============ MÉTHODES CONSULTATIONS ============
    
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
    
    def get_urgent_consultations(self, hours=24):
        """Récupère les consultations urgentes des dernières heures"""
        try:
            consultations_col = self.db['consultations']
            
            time_threshold = datetime.utcnow() - timedelta(hours=hours)  # Correction: utiliser timedelta
            
            consultations = list(consultations_col.find({
                'urgency': {'$in': ['high', 'medium']},
                'date_consultation': {'$gte': time_threshold}
            }).sort('date_consultation', -1).limit(50))
            
            # Formatage des résultats
            for consult in consultations:
                consult['_id'] = str(consult['_id'])
                if isinstance(consult.get('date_consultation'), datetime):
                    consult['date_consultation'] = consult['date_consultation'].isoformat()
            
            return consultations
        except Exception as e:
            print(f"❌ Erreur récupération consultations urgentes: {e}")
            return []
    
    # ============ MÉTHODES GROSSESSE ============
    
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
    
    def delete_pregnancy(self, user_id):
        """Supprime les données de grossesse d'un utilisateur"""
        try:
            pregnancies_col = self.db['pregnancies']
            result = pregnancies_col.delete_one({'user_id': user_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"❌ Erreur suppression grossesse: {e}")
            return False
    
    # ============ MÉTHODES ENFANTS ============
    
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
    
    def update_child_info(self, user_id, child_index, child_data):
        """Met à jour les informations d'un enfant"""
        try:
            users_col = self.db['users']
            
            # Construction du chemin pour la mise à jour
            update_path = f'children.{child_index}'
            update_query = {f'{update_path}.{key}': value for key, value in child_data.items()}
            
            result = users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_query}
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Erreur mise à jour enfant: {e}")
            return False
    
    def delete_child(self, user_id, child_index):
        """Supprime un enfant du profil utilisateur"""
        try:
            users_col = self.db['users']
            
            result = users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$unset': {f'children.{child_index}': ''}}
            )
            
            # Ensuite, supprimer les valeurs null
            if result.modified_count > 0:
                users_col.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$pull': {'children': None}}
                )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Erreur suppression enfant: {e}")
            return False
    
    # ============ MÉTHODES STATISTIQUES ============
    
    def get_user_stats(self, user_id):
        """Récupère les statistiques d'un utilisateur"""
        try:
            consultations_col = self.db['consultations']
            pregnancies_col = self.db['pregnancies']
            users_col = self.db['users']
            
            user = users_col.find_one({'_id': ObjectId(user_id)})
            
            if not user:
                return None
            
            stats = {
                'total_consultations': consultations_col.count_documents({'user_id': user_id}),
                'urgent_consultations': consultations_col.count_documents({
                    'user_id': user_id,
                    'urgency': {'$in': ['high', 'medium']}
                }),
                'has_pregnancy': pregnancies_col.find_one({'user_id': user_id}) is not None,
                'children_count': len(user.get('children', [])),
                'account_age_days': (datetime.utcnow() - user.get('date_creation', datetime.utcnow())).days
            }
            
            return stats
        except Exception as e:
            print(f"❌ Erreur récupération statistiques: {e}")
            return None
    
    def get_system_stats(self):
        """Récupère les statistiques globales du système"""
        try:
            users_col = self.db['users']
            consultations_col = self.db['consultations']
            pregnancies_col = self.db['pregnancies']
            
            stats = {
                'total_users': users_col.count_documents({}),
                'active_users': users_col.count_documents({'is_active': True}),
                'total_consultations': consultations_col.count_documents({}),
                'urgent_consultations': consultations_col.count_documents({
                    'urgency': {'$in': ['high', 'medium']}
                }),
                'active_pregnancies': pregnancies_col.count_documents({
                    'due_date': {'$gte': datetime.utcnow()}
                }),
                'users_with_children': users_col.count_documents({
                    'children': {'$exists': True, '$ne': []}
                })
            }
            
            return stats
        except Exception as e:
            print(f"❌ Erreur récupération statistiques système: {e}")
            return None

    # ============ MÉTHODES NOTIFICATIONS (CORRIGÉES) ============
    
    def get_user_notifications(self, user_id, unread_only=False, limit=50):
        """Récupère les notifications d'un utilisateur"""
        try:
            notifications_col = self.db['notifications']
            
            query = {'user_id': user_id}
            if unread_only:
                query['read'] = False
            
            notifications = notifications_col.find(query)\
                .sort('created_at', -1)\
                .limit(limit)
            
            # Convertir les résultats
            result = []
            for notification in notifications:
                notification['_id'] = str(notification['_id'])
                if isinstance(notification.get('created_at'), datetime):
                    notification['created_at'] = notification['created_at'].isoformat()
                if isinstance(notification.get('read_at'), datetime):
                    notification['read_at'] = notification['read_at'].isoformat()
                result.append(notification)
            
            return result
        except Exception as e:
            print(f"❌ Erreur récupération notifications: {e}")
            return []
    
    def get_new_notifications(self, user_id, since_timestamp):
        """Récupère les nouvelles notifications depuis un timestamp"""
        try:
            notifications_col = self.db['notifications']
            
            query = {
                'user_id': user_id,
                'read': False
            }
        
            if since_timestamp:
                # Si since_timestamp est déjà un datetime, l'utiliser directement
                if isinstance(since_timestamp, datetime):
                    query['created_at'] = {'$gt': since_timestamp}
                # Sinon, essayer de le convertir
                elif isinstance(since_timestamp, str):
                    try:
                        since_datetime = datetime.fromisoformat(
                            since_timestamp.replace('Z', '+00:00')
                        )
                        query['created_at'] = {'$gt': since_datetime}
                    except ValueError:
                        print(f"⚠️ Format de timestamp invalide: {since_timestamp}")
                        # Si conversion échoue, récupérer les 24 dernières heures
                        query['created_at'] = {'$gt': datetime.utcnow() - timedelta(hours=24)}
        
            notifications = notifications_col.find(query)\
                .sort('created_at', -1)\
                .limit(10)
            
            # Convertir les résultats
            result = []
            for notification in notifications:
                notification['_id'] = str(notification['_id'])
                if isinstance(notification.get('created_at'), datetime):
                    notification['created_at'] = notification['created_at'].isoformat()
                result.append(notification)
            
            return result
        except Exception as e:
            print(f"❌ Erreur récupération nouvelles notifications: {e}")
            return []
    
    def save_notification(self, notification_data):
        """Sauvegarde une notification"""
        try:
            notifications_col = self.db['notifications']
            
            # S'assurer que created_at est présent
            if 'created_at' not in notification_data:
                notification_data['created_at'] = datetime.utcnow()
            
            result = notifications_col.insert_one(notification_data)
            notification_id = str(result.inserted_id)
            print(f"📱 Notification sauvegardée: {notification_id}")
            return notification_id
        except Exception as e:
            print(f"❌ Erreur sauvegarde notification: {e}")
            return None
    
    def mark_notification_as_read(self, notification_id, user_id):
        """Marque une notification comme lue"""
        try:
            notifications_col = self.db['notifications']
            
            result = notifications_col.update_one(
                {'_id': ObjectId(notification_id), 'user_id': user_id},
                {'$set': {'read': True, 'read_at': datetime.utcnow()}}
            )
            
            success = result.modified_count > 0
            if success:
                print(f"✅ Notification {notification_id} marquée comme lue")
            return success
        except Exception as e:
            print(f"❌ Erreur marquage notification: {e}")
            return False
    
    def mark_all_notifications_as_read(self, user_id):
        """Marque toutes les notifications comme lues"""
        try:
            notifications_col = self.db['notifications']
            
            result = notifications_col.update_many(
                {'user_id': user_id, 'read': False},
                {'$set': {'read': True, 'read_at': datetime.utcnow()}}
            )
            
            success = result.modified_count > 0
            if success:
                print(f"✅ Toutes les notifications marquées comme lues pour l'utilisateur {user_id}")
            return success
        except Exception as e:
            print(f"❌ Erreur marquage toutes notifications: {e}")
            return False
    
    def update_notification_settings(self, user_id, notification_type, enabled):
        """Met à jour les paramètres de notifications"""
        try:
            users_col = self.db['users']
            
            result = users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {f'notification_settings.{notification_type}': enabled}}
            )
            
            success = result.modified_count > 0
            if success:
                print(f"✅ Paramètres notifications mis à jour: {notification_type} = {enabled}")
            return success
        except Exception as e:
            print(f"❌ Erreur mise à jour paramètres: {e}")
            return False
    
    def get_active_pregnancies(self):
        """Récupère toutes les grossesses actives"""
        try:
            pregnancies_col = self.db['pregnancies']
            
            # Grossesses avec une date de début dans les 40 dernières semaines
            cutoff_date = datetime.utcnow() - timedelta(weeks=40)
            
            pregnancies = pregnancies_col.find({
                'start_date': {'$gte': cutoff_date},
                'user_id': {'$exists': True}
            })
            
            # Convertir les résultats
            result = []
            for pregnancy in pregnancies:
                pregnancy['_id'] = str(pregnancy['_id'])
                result.append(pregnancy)
            
            return result
        except Exception as e:
            print(f"❌ Erreur récupération grossesses actives: {e}")
            return []
    
    def get_users_with_children(self):
        """Récupère les utilisateurs avec enfants"""
        try:
            users_col = self.db['users']
            
            users = users_col.find({
                'children': {'$exists': True, '$ne': []}
            })
            
            # Convertir les résultats
            result = []
            for user in users:
                user['_id'] = str(user['_id'])
                result.append(user)
            
            return result
        except Exception as e:
            print(f"❌ Erreur récupération utilisateurs avec enfants: {e}")
            return []
    
    def get_notification_stats(self, user_id):
        """Retourne les statistiques des notifications"""
        try:
            notifications_col = self.db['notifications']
            
            total = notifications_col.count_documents({'user_id': user_id})
            unread = notifications_col.count_documents({'user_id': user_id, 'read': False})
            
            # Notifications des dernières 24 heures
            last_24h = notifications_col.count_documents({
                'user_id': user_id,
                'created_at': {'$gte': datetime.utcnow() - timedelta(hours=24)}
            })
            
            # Statistiques par type
            by_type = {}
            notification_types = notifications_col.distinct('type', {'user_id': user_id})
            
            for n_type in notification_types:
                total_type = notifications_col.count_documents({
                    'user_id': user_id,
                    'type': n_type
                })
                unread_type = notifications_col.count_documents({
                    'user_id': user_id,
                    'type': n_type,
                    'read': False
                })
                by_type[n_type] = {'total': total_type, 'unread': unread_type}
            
            stats = {
                'total': total,
                'unread': unread,
                'last_24h': last_24h,
                'by_type': by_type
            }
            
            return stats
        except Exception as e:
            print(f"❌ Erreur récupération statistiques notifications: {e}")
            return None

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

def get_user_by_email(email):
    return db_manager.get_user_by_email(email)

def verify_user_credentials(email, password):
    return db_manager.verify_user_credentials(email, password)

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