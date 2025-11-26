import json
import re
import os
from datetime import datetime

class HealthProcessor:
    def __init__(self):
        self.intents = self.load_intents()
        self.emergency_keywords = [
            'urgence', 'urgent', 'grave', 'danger', 'mort', 'crise', 
            'saignement', 'contraction', 'perte liquide', 'bébé ne bouge plus'
        ]
        self.symptom_keywords = [
            'mal', 'douleur', 'fièvre', 'toux', 'fatigue', 'nausée',
            'vomissement', 'migraine', 'brûlure', 'crampe'
        ]
    
    def load_intents(self):
        """Charge les intents depuis le fichier JSON"""
        try:
            intents_path = os.path.join(os.path.dirname(__file__), 'intents.json')
            with open(intents_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ Fichier intents.json non trouvé")
            return {"intents": []}
        except json.JSONDecodeError:
            print("❌ Erreur de décodage JSON")
            return {"intents": []}
    
    def preprocess_text(self, text):
        """Prétraite le texte pour la recherche"""
        text = text.lower().strip()
        # Supprime la ponctuation et les caractères spéciaux
        text = re.sub(r'[^\w\s]', ' ', text)
        return text
    
    def detect_urgency(self, text):
        """Détecte les mots-clés d'urgence"""
        text_lower = text.lower()
        emergency_phrases = [
            'bébé ne bouge plus',
            'saignement abondant',
            'contractions régulières',
            'perte de liquide',
            'douleur intense',
            'difficulté à respirer'
        ]
        
        # Vérifie les phrases d'urgence complètes
        for phrase in emergency_phrases:
            if phrase in text_lower:
                return 'high'
        
        # Vérifie les mots-clés individuels
        emergency_words = ['urgence', 'urgent', 'grave', 'danger', 'saignement', 'contraction']
        if any(word in text_lower for word in emergency_words):
            return 'high'
            
        return 'low'
    
    def find_best_intent(self, text):
        """Trouve l'intent qui correspond le mieux au texte"""
        processed_text = self.preprocess_text(text)
        
        best_match = None
        highest_score = 0
        
        for intent in self.intents.get("intents", []):
            score = 0
            for pattern in intent.get("patterns", []):
                pattern_clean = self.preprocess_text(pattern)
                # Score basé sur la présence de mots-clés
                pattern_words = set(pattern_clean.split())
                text_words = set(processed_text.split())
                common_words = pattern_words.intersection(text_words)
                
                current_score = len(common_words) / len(pattern_words) if pattern_words else 0
                if current_score > score:
                    score = current_score
            
            if score > highest_score and score > 0.3:  # Seuil de similarité
                highest_score = score
                best_match = intent
        
        return best_match
    
    def process_question(self, question):
        """Traite une question et retourne une réponse"""
        if not question or not question.strip():
            return {
                "response": "Je n'ai pas compris votre question. Pouvez-vous reformuler ?",
                "urgency": "low",
                "category": "general"
            }
        
        # Détection d'urgence
        urgency_level = self.detect_urgency(question)
        if urgency_level == 'high':
            return {
                "response": "🚨 URGENCE MÉDICALE DÉTECTÉE. Composez immédiatement le 15 (SAMU) ou le 112. Ce chatbot ne peut pas gérer les situations d'urgence. Restez calme et suivez les instructions des secours.",
                "urgency": "high",
                "category": "emergency"
            }
        
        # Recherche dans les intents
        matched_intent = self.find_best_intent(question)
        
        if matched_intent:
            import random
            response = random.choice(matched_intent.get("responses", ["Je ne peux pas répondre à cette question pour le moment."]))
            
            return {
                "response": response,
                "urgency": matched_intent.get("urgency", "low"),
                "category": matched_intent.get("category", "general")
            }
        
        # Réponse par défaut
        default_responses = [
            "Je comprends votre préoccupation. Pour des conseils personnalisés, veuillez consulter un professionnel de santé.",
            "C'est une bonne question. Je vous recommande d'en parler avec votre sage-femme ou votre médecin lors de votre prochaine consultation.",
            "Je suis spécialisé dans les questions de santé maternelle et infantile. Pouvez-vous préciser votre question ?",
            "Pour cette question spécifique, il est préférable de consulter un professionnel de santé qui pourra vous accompagner personnellement."
        ]
        
        import random
        return {
            "response": random.choice(default_responses),
            "urgency": "low",
            "category": "general"
        }

# Instance globale pour l'import
processor = HealthProcessor()

# Fonction d'export pour Flask
def process_question(question):
    return processor.process_question(question)