import os
from twilio.rest import Client
from datetime import datetime

class NotificationService:
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
            return True
        except Exception as e:
            print(f"❌ Erreur envoi SMS: {e}")
            return False
    
    def send_vaccine_reminder(self, user_phone, child_name, vaccines, due_date):
        """Envoie un rappel de vaccin"""
        message = f"💉 Rappel vaccin {child_name}\nVaccins: {', '.join(vaccines)}\nDate: {due_date.strftime('%d/%m/%Y')}\n-- Maman & Bébé --"
        return self.send_sms(user_phone, message)
    
    def send_emergency_alert(self, user_phone, symptoms):
        """Envoie une alerte d'urgence"""
        message = f"🚨 Alerte Santé\nSymptômes: {symptoms}\nContactez immédiatement le 15\n-- Maman & Bébé --"
        return self.send_sms(user_phone, message)
    
    def send_appointment_reminder(self, user_phone, appointment_type, date):
        """Envoie un rappel de rendez-vous"""
        message = f"📅 Rappel rendez-vous\n{appointment_type}\nLe {date.strftime('%d/%m/%Y à %H:%M')}\n-- Maman & Bébé --"
        return self.send_sms(user_phone, message)

# Instance globale
notification_service = NotificationService()

# Fonction d'interface
def send_sms_alert(phone, message):
    return notification_service.send_sms(phone, message)