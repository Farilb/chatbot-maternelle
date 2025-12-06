from datetime import datetime
from bson import ObjectId
import hashlib
import secrets
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data=None):
        if user_data is None:
            user_data = {}
        
        self._id = user_data.get('_id')
        self.id = str(self._id) if self._id else None
        self.nom = user_data.get('nom', '')
        self.prenom = user_data.get('prenom', '')
        self.email = user_data.get('email', '')
        self.phone = user_data.get('phone', '')
        self.password_hash = user_data.get('password_hash', '')
        self.password_salt = user_data.get('password_salt', '')
        self.statut = user_data.get('statut', 'enceinte')
        self.allergies = user_data.get('allergies', '')
        self.traitements = user_data.get('traitements', '')
        self.children = user_data.get('children', [])
        self.date_creation = user_data.get('date_creation', datetime.utcnow())
        self.date_modification = user_data.get('date_modification', datetime.utcnow())
        self.role = user_data.get('role', 'user')
        self.is_active = user_data.get('is_active', True)
    
    def set_password(self, password):
        """Hash le mot de passe avec un salt (méthode SHA256 pour compatibilité)"""
        self.password_salt = secrets.token_hex(16)
        self.password_hash = self._hash_password(password, self.password_salt)
    
    def check_password(self, password):
        """Vérifie le mot de passe"""
        return self.password_hash == self._hash_password(password, self.password_salt)
    
    def _hash_password(self, password, salt):
        """Hash le mot de passe avec le salt"""
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour MongoDB"""
        data = {
            'nom': self.nom,
            'prenom': self.prenom,
            'email': self.email,
            'phone': self.phone,
            'password_hash': self.password_hash,
            'password_salt': self.password_salt,
            'statut': self.statut,
            'allergies': self.allergies,
            'traitements': self.traitements,
            'children': self.children,
            'role': self.role,
            'is_active': self.is_active,
            'date_creation': self.date_creation,
            'date_modification': datetime.utcnow()
        }
        
        if self._id:
            data['_id'] = ObjectId(self._id) if isinstance(self._id, str) else self._id
        
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Crée un objet User depuis un dictionnaire MongoDB"""
        return cls(data)
    
    def get_id(self):
        """Retourne l'ID de l'utilisateur pour Flask-Login"""
        return self.id
    
    def is_authenticated(self):
        """Vérifie si l'utilisateur est authentifié"""
        return True
    
    def is_active(self):
        """Vérifie si le compte est actif"""
        return self.is_active
    
    def is_anonymous(self):
        """Vérifie si l'utilisateur est anonyme"""
        return False
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        return f"{self.prenom} {self.nom}".strip()