from datetime import datetime, timedelta
from bson import ObjectId

class Pregnancy:
    def __init__(self, pregnancy_data=None):
        if pregnancy_data is None:
            pregnancy_data = {}
        
        self._id = pregnancy_data.get('_id')
        self.user_id = pregnancy_data.get('user_id')
        self.start_date = pregnancy_data.get('start_date')
        self.due_date = pregnancy_data.get('due_date')
        self.week_current = pregnancy_data.get('week_current', 0)
        self.trimester = pregnancy_data.get('trimester', 1)
        self.medical_history = pregnancy_data.get('medical_history', {})
        self.vaccines_received = pregnancy_data.get('vaccines_received', [])
        self.appointments = pregnancy_data.get('appointments', [])
        self.created_at = pregnancy_data.get('created_at', datetime.utcnow())
        self.updated_at = pregnancy_data.get('updated_at', datetime.utcnow())
    
    def calculate_week(self):
        """Calcule la semaine de grossesse actuelle"""
        if not self.start_date:
            return 0
        
        # Gérer les différents formats de date
        if isinstance(self.start_date, str):
            start_date = datetime.fromisoformat(self.start_date.replace('Z', '+00:00'))
        else:
            start_date = self.start_date
            
        today = datetime.utcnow()
        
        # Calculer la différence en semaines
        delta = today - start_date
        weeks = delta.days // 7
        
        # Mettre à jour le trimestre
        self.week_current = weeks
        if weeks < 14:
            self.trimester = 1
        elif weeks < 28:
            self.trimester = 2
        else:
            self.trimester = 3
            
        return self.week_current
    
    def get_baby_development(self):
        """Retourne le développement du bébé selon la semaine"""
        current_week = self.calculate_week()
        
        developments = {
            4: "Cœur qui bat, formation du système nerveux",
            8: "Tous les organes présents, premiers mouvements",
            12: "Visage formé, échographie de datation",
            16: "Mouvements actifs, sexe identifiable",
            20: "Mouvements ressentis, échographie morphologique", 
            24: "Bébé entend, poumons en développement",
            28: "Ouverture des yeux, sensibilité à la lumière",
            32: "Prise de poids rapide, dernière échographie",
            36: "Bébé se positionne, organes matures",
            40: "Terme, bébé prêt à naître"
        }
        
        # Trouver la description la plus proche
        closest_week = 0
        for week in sorted(developments.keys()):
            if current_week >= week:
                closest_week = week
            else:
                break
                
        if closest_week in developments:
            return f"Semaine {current_week} : {developments[closest_week]}"
        else:
            return f"Semaine {current_week} : Début de grossesse - implantation"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour MongoDB"""
        data = {
            'user_id': self.user_id,
            'start_date': self.start_date,
            'due_date': self.due_date,
            'week_current': self.calculate_week(),
            'trimester': self.trimester,
            'medical_history': self.medical_history,
            'vaccines_received': self.vaccines_received,
            'appointments': self.appointments,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }
        
        # N'inclure l'_id que s'il existe
        if self._id:
            data['_id'] = ObjectId(self._id) if isinstance(self._id, str) else self._id
        
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Crée un objet Pregnancy depuis un dictionnaire MongoDB"""
        return cls(data)
    
    def get_next_appointments(self):
        """Retourne les prochains rendez-vous"""
        today = datetime.utcnow()
        upcoming = []
        
        for appointment in self.appointments:
            if isinstance(appointment.get('date'), str):
                appt_date = datetime.fromisoformat(appointment['date'].replace('Z', '+00:00'))
            else:
                appt_date = appointment.get('date')
                
            if appt_date and appt_date >= today:
                upcoming.append(appointment)
        
        return sorted(upcoming, key=lambda x: x['date'])[:3]