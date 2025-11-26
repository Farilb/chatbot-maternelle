from datetime import datetime
from bson import ObjectId

class User:
    def __init__(self, user_data=None):
        if user_data is None:
            user_data = {}
        
        self._id = user_data.get('_id')
        self.nom = user_data.get('nom', '')
        self.prenom = user_data.get('prenom', '')
        self.email = user_data.get('email', '')
        self.phone = user_data.get('phone', '')
        self.date_naissance = user_data.get('date_naissance')
        self.statut = user_data.get('statut', 'enceinte')  # enceinte, jeune_mere, les_deux
        self.groupe_sanguin = user_data.get('groupe_sanguin', '')
        self.allergies = user_data.get('allergies', '')
        self.traitements = user_data.get('traitements', '')
        self.children = user_data.get('children', [])
        self.date_creation = user_data.get('date_creation', datetime.utcnow())
        self.date_modification = user_data.get('date_modification', datetime.utcnow())
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour MongoDB"""
        data = {
            'nom': self.nom,
            'prenom': self.prenom,
            'email': self.email,
            'phone': self.phone,
            'date_naissance': self.date_naissance,
            'statut': self.statut,
            'groupe_sanguin': self.groupe_sanguin,
            'allergies': self.allergies,
            'traitements': self.traitements,
            'children': self.children,
            'date_creation': self.date_creation,
            'date_modification': self.date_modification
        }
        
        # N'inclure l'_id que s'il existe
        if self._id:
            data['_id'] = ObjectId(self._id) if isinstance(self._id, str) else self._id
        
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Crée un objet User depuis un dictionnaire MongoDB"""
        return cls(data)
    
    def calculate_age(self):
        """Calcule l'âge à partir de la date de naissance"""
        if not self.date_naissance:
            return None
        
        if isinstance(self.date_naissance, str):
            birth_date = datetime.fromisoformat(self.date_naissance.replace('Z', '+00:00'))
        else:
            birth_date = self.date_naissance
            
        today = datetime.utcnow()
        age = today.year - birth_date.year
        
        # Ajuster si l'anniversaire n'est pas encore passé cette année
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
            
        return age