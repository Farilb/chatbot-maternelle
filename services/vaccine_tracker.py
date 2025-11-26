from datetime import datetime, timedelta
from services.database import db_manager

class VaccineTracker:
    def __init__(self):
        self.vaccine_schedule = {
            'naissance': ['BCG', 'Hépatite B'],
            '2_mois': ['DTP', 'Hib', 'Hépatite B', 'Pneumocoque', 'Rotavirus'],
            '4_mois': ['DTP', 'Hib', 'Hépatite B', 'Pneumocoque', 'Rotavirus'],
            '11_mois': ['DTP', 'Hib', 'Hépatite B', 'Pneumocoque'],
            '12_mois': ['ROR', 'Méningocoque C'],
            '16_18_mois': ['ROR'],
            '6_ans': ['DTP'],
            '11_13_ans': ['DTP', 'Hépatite B', 'HPV']
        }
    
    def get_upcoming_vaccines(self, birth_date):
        """Calcule les vaccins à venir selon la date de naissance"""
        if isinstance(birth_date, str):
            birth_date = datetime.fromisoformat(birth_date.replace('Z', '+00:00'))
        
        age_days = (datetime.utcnow() - birth_date).days
        upcoming = []
        
        milestones = {
            'naissance': 0,
            '2_mois': 60,
            '4_mois': 120,
            '11_mois': 335,
            '12_mois': 365,
            '16_18_mois': 480,
            '6_ans': 2190,
            '11_13_ans': 4015
        }
        
        for milestone, days in milestones.items():
            if age_days >= days - 14 and age_days <= days + 30:  # Fenêtre ±2 semaines
                upcoming.append({
                    'milestone': milestone,
                    'vaccines': self.vaccine_schedule[milestone],
                    'recommended_date': birth_date + timedelta(days=days),
                    'status': 'due' if age_days >= days else 'upcoming'
                })
        
        return upcoming
    
    def send_vaccine_reminders(self):
        """Envoie les rappels de vaccins (à appeler périodiquement)"""
        try:
            users_col = db_manager.db['users']
            users_with_children = users_col.find({'children': {'$exists': True, '$ne': []}})
            
            reminders_sent = 0
            for user in users_with_children:
                for child in user.get('children', []):
                    birth_date = child.get('birth_date')
                    if birth_date:
                        upcoming = self.get_upcoming_vaccines(birth_date)
                        for vaccine_info in upcoming:
                            if vaccine_info['status'] == 'due':
                                message = f"Rappel vaccin {child.get('name', 'Bébé')}: {', '.join(vaccine_info['vaccines'])} - Date recommandée: {vaccine_info['recommended_date'].strftime('%d/%m/%Y')}"
                                
                                # Envoyer SMS/notification
                                from services.notification import send_sms_alert
                                if send_sms_alert(user.get('phone'), message):
                                    reminders_sent += 1
            
            print(f"📧 {reminders_sent} rappels de vaccins envoyés")
            return reminders_sent
        except Exception as e:
            print(f"❌ Erreur envoi rappels vaccins: {e}")
            return 0
    
    def get_child_vaccine_schedule(self, birth_date, child_name="Bébé"):
        """Retourne le calendrier vaccinal complet pour un enfant"""
        if isinstance(birth_date, str):
            birth_date = datetime.fromisoformat(birth_date.replace('Z', '+00:00'))
        
        schedule = []
        for milestone, days in {
            'naissance': 0,
            '2_mois': 60,
            '4_mois': 120,
            '11_mois': 335,
            '12_mois': 365,
            '16_18_mois': 480,
            '6_ans': 2190,
            '11_13_ans': 4015
        }.items():
            vaccine_date = birth_date + timedelta(days=days)
            status = 'completed' if (datetime.utcnow() - vaccine_date).days > 30 else 'pending'
            
            schedule.append({
                'milestone': milestone,
                'vaccines': self.vaccine_schedule.get(milestone, []),
                'date': vaccine_date,
                'status': status,
                'child_name': child_name
            })
        
        return schedule