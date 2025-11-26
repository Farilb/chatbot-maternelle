from datetime import datetime
from bson import ObjectId

class Consultation:
    def __init__(self, consultation_data=None):
        if consultation_data is None:
            consultation_data = {}
        
        self._id = consultation_data.get('_id')
        self.user_id = consultation_data.get('user_id')
        self.question = consultation_data.get('question', '')
        self.response = consultation_data.get('response', '')
        self.urgency = consultation_data.get('urgency', 'low')
        self.date_consultation = consultation_data.get('date_consultation', datetime.utcnow())
        self.status = consultation_data.get('status', 'completed')
        self.symptoms = consultation_data.get('symptoms', [])
        self.recommendations = consultation_data.get('recommendations', [])
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour MongoDB"""
        return {
            'user_id': self.user_id,
            'question': self.question,
            'response': self.response,
            'urgency': self.urgency,
            'date_consultation': self.date_consultation,
            'status': self.status,
            'symptoms': self.symptoms,
            'recommendations': self.recommendations
        }
    
    @classmethod
    def from_dict(cls, data):
        """Crée un objet Consultation depuis un dictionnaire MongoDB"""
        return cls(data)