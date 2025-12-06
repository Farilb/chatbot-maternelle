import os
from twilio.rest import Client
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer les identifiants
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')

print("🔍 Vérification Twilio...")
print(f"Account SID: {account_sid[:10]}...")
print(f"Auth Token: {auth_token[:10]}...")
print(f"Phone Number: {twilio_phone}")

try:
    # Initialiser le client Twilio
    client = Client(account_sid, auth_token)
    
    # Tester la connexion en récupérant les infos du compte
    account = client.api.accounts(account_sid).fetch()
    print(f"✅ Twilio connecté - Compte: {account.friendly_name}")
    
    # Vérifier le solde
    balance = client.api.v2010.accounts(account_sid).balance.fetch()
    print(f"💰 Solde: ${balance.balance} {balance.currency}")
    
    # Tester l'envoi d'un SMS (à un numéro vérifié)
    test_number = input("Entrez un numéro vérifié pour tester (format: +336...): ").strip()
    
    if test_number:
        message = client.messages.create(
            body="✅ Test SMS depuis Maman & Bébé - Twilio fonctionne !",
            from_=twilio_phone,
            to=test_number
        )
        print(f"📱 SMS envoyé ! SID: {message.sid}")
        print(f"📊 Statut: {message.status}")
    
except Exception as e:
    print(f"❌ Erreur Twilio: {e}")