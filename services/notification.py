import os
from twilio.rest import Client
from datetime import datetime, timedelta
from bson import ObjectId
from services.database import db_manager
import schedule
import time
from threading import Thread

class EnhancedNotificationService:
    def __init__(self):
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.client = None
        
        if self.twilio_account_sid and self.twilio_auth_token:
            try:
                self.client = Client(self.twilio_account_sid, self.twilio_auth_token)
                print("✅ Service Twilio initialisé")
            except Exception as e:
                print(f"❌ Erreur initialisation Twilio: {e}")
        else:
            print("⚠️ Twilio non configuré - mode simulation activé")
        
        # Démarrer le scheduler en arrière-plan
        self.start_scheduler()
    
    def start_scheduler(self):
        """Démarre le scheduler pour les notifications planifiées"""
        def run_scheduler():
            schedule.every().day.at("09:00").do(self.check_daily_notifications)
            schedule.every().monday.at("10:00").do(self.send_weekly_pregnancy_updates)
            schedule.every().day.at("08:00").do(self.send_vaccine_reminders)
            
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        thread = Thread(target=run_scheduler, daemon=True)
        thread.start()
        print("✅ Scheduler de notifications démarré")
    
    def send_sms(self, to_phone, message):
        """Envoie un SMS via Twilio"""
        if not self.client:
            print(f"📱 SMS simulé vers {to_phone}: {message}")
            return True
        
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=to_phone
            )
            print(f"✅ SMS envoyé: {message.sid}")
            
            # Enregistrer dans la base de données
            self.log_notification(to_phone, 'sms', 'sent', message.body)
            return True
        except Exception as e:
            print(f"❌ Erreur envoi SMS: {e}")
            self.log_notification(to_phone, 'sms', 'failed', str(e))
            return False
    
    def send_push_notification(self, user_id, title, message, notification_type='info'):
        """Envoie une notification push (à implémenter avec FCM/APN)"""
        # Pour l'instant, nous simulons avec un log
        print(f"📱 Push notification pour {user_id}: {title} - {message}")
        self.log_notification(user_id, 'push', 'sent', f"{title}: {message}")
        return True
    
    def send_vaccine_reminder(self, user_id, child_name, vaccines, due_date):
        """Envoie un rappel de vaccin"""
        user = db_manager.get_user_by_id(user_id)
        if not user or 'phone' not in user:
            return False
        
        message = f"💉 Rappel vaccin pour {child_name}\n"
        message += f"Vaccins: {', '.join(vaccines)}\n"
        message += f"Date recommandée: {due_date.strftime('%d/%m/%Y')}\n"
        message += "📞 Prenez RDV avec votre pédiatre\n"
        message += "-- Maman & Bébé --"
        
        # Envoyer SMS
        sms_sent = self.send_sms(user['phone'], message)
        
        # Envoyer notification push
        push_sent = self.send_push_notification(
            user_id, 
            "💉 Rappel vaccin", 
            f"{child_name} : {', '.join(vaccines)}",
            'vaccine'
        )
        
        # Créer une notification dans la base de données
        notification_data = {
            'user_id': user_id,
            'type': 'vaccine',
            'title': 'Rappel vaccin',
            'message': f"{child_name} - {', '.join(vaccines)}",
            'data': {
                'child_name': child_name,
                'vaccines': vaccines,
                'due_date': due_date,
                'status': 'pending'
            },
            'read': False,
            'created_at': datetime.utcnow()
        }
        db_manager.save_notification(notification_data)
        
        return sms_sent or push_sent
    
    def send_emergency_alert(self, user_id, symptoms):
        """Envoie une alerte d'urgence"""
        user = db_manager.get_user_by_id(user_id)
        if not user or 'phone' not in user:
            return False
        
        message = f"🚨 ALERTE SANTÉ 🚨\n"
        message += f"Symptômes signalés: {symptoms}\n"
        message += f"📞 Contactez IMMÉDIATEMENT le 15 (SAMU)\n"
        message += "⚠️ Ne prenez aucun risque\n"
        message += "-- Maman & Bébé --"
        
        sms_sent = self.send_sms(user['phone'], message)
        
        # Notification push urgente
        push_sent = self.send_push_notification(
            user_id,
            "🚨 Alerte Urgente",
            f"Symptômes: {symptoms[:50]}...",
            'emergency'
        )
        
        # Enregistrer l'alerte
        notification_data = {
            'user_id': user_id,
            'type': 'emergency',
            'title': 'Alerte Urgente',
            'message': f"Symptômes: {symptoms}",
            'data': {'symptoms': symptoms, 'timestamp': datetime.utcnow()},
            'read': False,
            'created_at': datetime.utcnow()
        }
        db_manager.save_notification(notification_data)
        
        return sms_sent or push_sent
    
    def send_weekly_pregnancy_update(self, user_id, week, trimester, development_info):
        """Envoie une mise à jour hebdomadaire de grossesse"""
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return False
        
        message = f"🤰 Semaine {week} de grossesse\n"
        message += f"🎉 {trimester}ème trimestre\n"
        message += f"👶 {development_info}\n"
        message += f"📅 Prochaine étape dans {self.get_next_milestone(week)}\n"
        message += "❤️ Prenez soin de vous\n"
        message += "-- Maman & Bébé --"
        
        sms_sent = False
        if 'phone' in user:
            sms_sent = self.send_sms(user['phone'], message)
        
        push_sent = self.send_push_notification(
            user_id,
            f"🤰 Semaine {week}",
            f"Vous êtes dans votre {trimester}ème trimestre",
            'pregnancy'
        )
        
        return sms_sent or push_sent
    
    def send_milestone_reminder(self, user_id, milestone_week, milestone_text):
        """Envoie un rappel d'étape importante"""
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return False
        
        message = f"🎯 ÉTAPE IMPORTANTE\n"
        message += f"Semaine {milestone_week}: {milestone_text}\n"
        message += "📅 Préparez votre rendez-vous\n"
        message += "📋 Préparez vos questions\n"
        message += "-- Maman & Bébé --"
        
        sms_sent = False
        if 'phone' in user:
            sms_sent = self.send_sms(user['phone'], message)
        
        push_sent = self.send_push_notification(
            user_id,
            f"🎯 Semaine {milestone_week}",
            milestone_text,
            'milestone'
        )
        
        return sms_sent or push_sent
    
    def send_appointment_reminder(self, user_id, appointment_type, date, doctor):
        """Envoie un rappel de rendez-vous"""
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return False
        
        message = f"📅 RAPPEL RENDEZ-VOUS\n"
        message += f"Type: {appointment_type}\n"
        message += f"Date: {date.strftime('%d/%m/%Y à %H:%M')}\n"
        message += f"Avec: {doctor}\n"
        message += "📌 N'oubliez pas votre carte vitale\n"
        message += "-- Maman & Bébé --"
        
        sms_sent = False
        if 'phone' in user:
            sms_sent = self.send_sms(user['phone'], message)
        
        push_sent = self.send_push_notification(
            user_id,
            "📅 Rappel RDV",
            f"{appointment_type} - {date.strftime('%d/%m à %H:%M')}",
            'appointment'
        )
        
        return sms_sent or push_sent
    
    def check_daily_notifications(self):
        """Vérifie et envoie les notifications quotidiennes"""
        print("🔔 Vérification des notifications quotidiennes")
        
        # Vérifier les vaccins en retard
        self.check_overdue_vaccines()
        
        # Vérifier les grossesses à risque
        self.check_high_risk_pregnancies()
        
        # Envoyer les rappels du jour
        self.send_today_reminders()
    
    def send_weekly_pregnancy_updates(self):
        """Envoie les mises à jour hebdomadaires de grossesse"""
        print("🤰 Envoi des mises à jour hebdomadaires")
        
        # Récupérer toutes les grossesses actives
        pregnancies = db_manager.get_active_pregnancies()
        
        for pregnancy in pregnancies:
            user_id = pregnancy['user_id']
            week = pregnancy.get('current_week', 0)
            trimester = pregnancy.get('trimester', 1)
            
            if week > 0:
                development_info = self.get_week_development(week)
                self.send_weekly_pregnancy_update(user_id, week, trimester, development_info)
    
    def send_vaccine_reminders(self):
        """Envoie les rappels de vaccins"""
        print("💉 Envoi des rappels de vaccins")
        
        # Récupérer tous les utilisateurs avec enfants
        users = db_manager.get_users_with_children()
        
        for user in users:
            user_id = str(user['_id'])
            children = user.get('children', [])
            
            for child in children:
                if 'birth_date' in child:
                    # Vérifier les vaccins à venir
                    upcoming_vaccines = self.get_upcoming_vaccines(child['birth_date'])
                    
                    for vaccine in upcoming_vaccines:
                        if vaccine['status'] == 'due':
                            self.send_vaccine_reminder(
                                user_id,
                                child.get('name', 'Bébé'),
                                vaccine['vaccines'],
                                vaccine['due_date']
                            )
    
    def check_overdue_vaccines(self):
        """Vérifie les vaccins en retard"""
        users = db_manager.get_users_with_children()
        
        for user in users:
            user_id = str(user['_id'])
            children = user.get('children', [])
            
            for child in children:
                if 'birth_date' in child:
                    overdue_vaccines = self.get_overdue_vaccines(child['birth_date'])
                    
                    for vaccine in overdue_vaccines:
                        self.send_vaccine_reminder(
                            user_id,
                            child.get('name', 'Bébé'),
                            vaccine['vaccines'],
                            vaccine['due_date']
                        )
    
    def get_next_milestone(self, current_week):
        """Calcule la prochaine étape importante"""
        milestones = {
            12: "Échographie de datation",
            22: "Échographie morphologique",
            32: "Dernière échographie",
            36: "Consultation pré-anesthésique",
            40: "Terme prévu"
        }
        
        for week, milestone in milestones.items():
            if week > current_week:
                return f"{milestone} (semaine {week})"
        
        return "Fin de la grossesse"
    
    def get_week_development(self, week):
        """Retourne les infos de développement pour la semaine"""
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
        
        # Trouver la description la plus proche
        closest_week = min(developments.keys(), key=lambda x: abs(x - week))
        return developments.get(closest_week, "Développement en cours")
    
    def get_upcoming_vaccines(self, birth_date):
        """Retourne les vaccins à venir (simplifié)"""
        # À remplacer par votre logique réelle de vaccine_tracker
        return []
    
    def get_overdue_vaccines(self, birth_date):
        """Retourne les vaccins en retard (simplifié)"""
        # À remplacer par votre logique réelle de vaccine_tracker
        return []
    
    def log_notification(self, recipient, notification_type, status, content):
        """Enregistre une notification dans les logs"""
        log_entry = {
            'recipient': recipient,
            'type': notification_type,
            'status': status,
            'content': content,
            'timestamp': datetime.utcnow()
        }
        
        try:
            # À implémenter : sauvegarder dans la base de données
            pass
        except Exception as e:
            print(f"❌ Erreur log notification: {e}")

# Instance globale
notification_service = EnhancedNotificationService()

# Fonctions d'interface
def send_sms_alert(phone, message):
    return notification_service.send_sms(phone, message)

def send_emergency_alert(user_id, symptoms):
    return notification_service.send_emergency_alert(user_id, symptoms)

def send_vaccine_reminder(user_id, child_name, vaccines, due_date):
    return notification_service.send_vaccine_reminder(user_id, child_name, vaccines, due_date)