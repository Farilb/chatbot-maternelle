import json
import re
import os
import random
import spacy
from datetime import datetime
import time

class HealthProcessor:
    def __init__(self):
        self._load_model()
        self._load_intents_cache()
        self._build_keyword_index()
        
        self.emergency_keywords = [
            'urgence', 'urgent', 'grave', 'danger', 'mort', 'crise', 
            'saignement', 'contraction', 'perte liquide', 'bébé ne bouge plus',
            'hémorragie', 'convulsion', 'éclampsie', 'pré-éclampsie',
            'fièvre élevée', 'vertiges', 'malaise', 'douleur poitrine'
        ]
        
        # Phrases d'urgence critiques
        self.critical_phrases = [
            'bébé ne bouge plus',
            'saignement abondant', 
            'contractions régulières',
            'perte des eaux',
            'douleur intense',
            'perte de connaissance',
            'difficulté à respirer',
            'vision floue'
        ]
    
    def _load_model(self):
        """Charge le modèle spaCy si disponible"""
        try:
            self.nlp = spacy.load("fr_core_news_sm")
            print("✅ Modèle spaCy chargé avec succès")
        except OSError:
            print("⚠️ Modèle spaCy non trouvé. Utilisation mode basique.")
            self.nlp = None
    
    def _load_intents_cache(self):
        """Charge et cache tous les intents"""
        try:
            # Essayer plusieurs chemins possibles
            possible_paths = [
                os.path.join(os.path.dirname(__file__), 'intents.json'),
                'nlp/intents.json',
                'intents.json'
            ]
            
            intents_data = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    intents_data = data["intents"] if "intents" in data else data
                    print(f"✅ Intents chargés depuis: {path}")
                    break
            
            if not intents_data:
                print("❌ Aucun fichier intents.json trouvé")
                self.intents_data = []
                return
                
            self.intents_data = intents_data
            print(f"✅ {len(self.intents_data)} intents chargés en cache")
            
        except Exception as e:
            print(f"❌ Erreur chargement intents: {e}")
            self.intents_data = []
    
    def _build_keyword_index(self):
        """Crée un index rapide par mots-clés"""
        self.keyword_index = {}
        for i, intent in enumerate(self.intents_data):
            # Index par mots-clés explicites
            for mot_cle in intent.get("mots_cles", []):
                if mot_cle not in self.keyword_index:
                    self.keyword_index[mot_cle] = []
                self.keyword_index[mot_cle].append(i)
            
            # Index par mots des patterns
            for pattern in intent.get("patterns", []):
                pattern_words = self.fast_preprocess(pattern).split()
                for word in pattern_words:
                    if word not in self.keyword_index:
                        self.keyword_index[word] = []
                    if i not in self.keyword_index[word]:
                        self.keyword_index[word].append(i)
    
    def fast_preprocess(self, text):
        """Prétraitement ultra-rapide"""
        if not text:
            return ""
        
        # Nettoyage basique
        text = text.lower().strip()
        
        # Normalisation
        text = re.sub(r'[^\w\sàâäéèêëîïôöùûüç]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Liste de stopwords français simples
        stopwords = {'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 
                    'à', 'au', 'aux', 'avec', 'dans', 'pour', 'sur', 'par',
                    'est', 'sont', 'ai', 'as', 'a', 'avons', 'avez', 'ont',
                    'mais', 'ou', 'où', 'donc', 'or', 'ni', 'car',
                    'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
                    'ce', 'cet', 'cette', 'ces', 'mon', 'ton', 'son',
                    'notre', 'votre', 'leur', 'mes', 'tes', 'ses',
                    'nos', 'vos', 'leurs', 'que', 'qui', 'quoi', 'quand',
                    'comment', 'pourquoi'}
        
        words = [word for word in text.split() 
                if len(word) > 2 and word not in stopwords]
        
        return " ".join(words)
    
    def detect_urgency(self, text):
        """Détection d'urgence améliorée"""
        text_lower = text.lower()
        
        # Vérifier les phrases critiques d'abord
        for phrase in self.critical_phrases:
            if phrase in text_lower:
                return 'high'
        
        # Vérifier les mots-clés d'urgence
        emergency_count = 0
        for word in self.emergency_keywords:
            if word in text_lower:
                emergency_count += 1
                if emergency_count >= 2:  # Plusieurs mots d'urgence
                    return 'high'
        
        if emergency_count >= 1:
            return 'medium'
        
        # Vérifier les combinaisons de symptômes inquiétants
        warning_patterns = [
            (r'(douleur|mal).*?(tête|ventre|poitrine)', 'medium'),
            (r'(nausée|vomissement).*?(fréquent|persistant)', 'medium'),
            (r'(fièvre).*?(38|39|40)', 'medium'),
            (r'(saignement).*?(léger|peu)', 'medium')
        ]
        
        for pattern, level in warning_patterns:
            if re.search(pattern, text_lower):
                return level
        
        return 'low'
    
    def find_best_intent(self, text):
        """Recherche d'intent optimisée avec spaCy si disponible"""
        if not text or not self.intents_data:
            return None, 0.0
        
        processed_text = self.fast_preprocess(text)
        words = set(processed_text.split())
        
        # Si spaCy est disponible, utiliser pour l'analyse sémantique
        if self.nlp and len(words) > 0:
            doc = self.nlp(processed_text)
            word_set = set([token.text for token in doc])
        else:
            word_set = words
        
        best_match = None
        best_score = 0
        
        # Recherche par index de mots-clés
        candidate_indices = set()
        for word in word_set:
            if word in self.keyword_index:
                candidate_indices.update(self.keyword_index[word])
        
        # Si pas assez de candidats, chercher dans tous
        if len(candidate_indices) < 3:
            candidate_indices = range(len(self.intents_data))
        
        # Évaluation des candidats
        for idx in candidate_indices:
            if idx >= len(self.intents_data):
                continue
                
            intent = self.intents_data[idx]
            score = 0
            
            # Score par patterns avec spaCy si disponible
            for pattern in intent.get("patterns", []):
                pattern_processed = self.fast_preprocess(pattern)
                
                if self.nlp:
                    # Similarité sémantique
                    pattern_doc = self.nlp(pattern_processed)
                    text_doc = self.nlp(processed_text) if len(processed_text) > 0 else pattern_doc
                    
                    if pattern_doc.has_vector and text_doc.has_vector:
                        semantic_score = pattern_doc.similarity(text_doc)
                        score = max(score, semantic_score * 0.7)
                
                # Score lexical
                pattern_words = set(pattern_processed.split())
                common = len(word_set & pattern_words)
                total = len(word_set | pattern_words)
                
                if total > 0:
                    lexical_score = common / total
                    score = max(score, score + lexical_score * 0.3)
            
            # Bonus pour les mots-clés exacts
            for mot_cle in intent.get("mots_cles", []):
                if mot_cle in processed_text:
                    score += 0.15
            
            # Bonus pour les tags spécifiques
            tag = intent.get("tag", "")
            if tag in ['emergency', 'urgent', 'danger']:
                score += 0.1
            
            if score > best_score and score > 0.25:
                best_score = score
                best_match = intent
        
        return best_match, best_score
    
    def process_question(self, question, user_id=None):
        """Traite une question avec analyse de l'intention"""
        start_time = time.time()
        
        if not question or not question.strip():
            return self._default_response(0, user_id)
        
        # 1. Détection d'urgence
        urgency = self.detect_urgency(question)
        if urgency == 'high':
            return self._emergency_response()
        
        # 2. Recherche d'intent
        intent, confidence = self.find_best_intent(question)
        
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        if intent and confidence > 0.3:
            # Personnaliser la réponse
            response_data = self._get_personalized_response(intent, user_id, question)
            
            return {
                "response": response_data['text'],
                "urgency": intent.get("priorite", urgency),
                "category": intent.get("categorie", "general"),
                "tag": intent.get("tag", "unknown"),
                "confidence": min(confidence, 1.0),
                "processing_time_ms": processing_time,
                "quick_replies": response_data.get('quick_replies', [])
            }
        
        # Intent inconnu
        return self._default_response(processing_time, user_id)
    
    def _get_personalized_response(self, intent, user_id=None, original_question=""):
        """Personnalise la réponse selon le contexte"""
        import random
        
        responses = intent.get("responses", [])
        if not responses:
            return {
                'text': "Je comprends votre préoccupation. Pourriez-vous préciser votre question ?",
                'quick_replies': []
            }
        
        # Choisir une réponse aléatoire
        response_text = random.choice(responses)
        
        # Personnaliser selon le tag
        tag = intent.get("tag", "")
        
        # Personnalisation temporelle
        if tag in ['greeting', 'hello', 'bonjour']:
            current_hour = datetime.now().hour
            if current_hour < 12:
                greeting = "Bonjour"
            elif current_hour < 18:
                greeting = "Bon après-midi"
            else:
                greeting = "Bonsoir"
            
            response_text = f"{greeting} ! {response_text}"
        
        # Ajouter le nom de l'utilisateur si disponible et approprié
        if user_id and tag in ['greeting', 'personal']:
            # Ici vous pourriez récupérer le nom depuis la base de données
            response_text = response_text.replace("{user}", "chère maman")
        
        # Générer des quick replies contextuelles
        quick_replies = []
        
        if tag == 'nutrition':
            quick_replies = ['Aliments à éviter', 'Suppléments', 'Recettes saines', 'Gain de poids']
        elif tag == 'vaccination':
            quick_replies = ['Calendrier vaccinal', 'Effets secondaires', 'Prise de rendez-vous', 'Vaccins obligatoires']
        elif tag == 'pregnancy':
            quick_replies = ['Symptômes normaux', 'Visites médicales', 'Préparation accouchement', 'Suivi mensuel']
        elif tag == 'baby_care':
            quick_replies = ['Allaitement', 'Sommeil bébé', 'Hygiène', 'Développement']
        elif tag == 'symptoms':
            quick_replies = ['Quand consulter', 'Remèdes maison', 'Médicaments autorisés']
        elif tag == 'appointment':
            quick_replies = ['Planifier RDV', 'Préparation consultation', 'Questions à poser']
        else:
            # Réponses générales
            quick_replies = ['Nutrition', 'Grossesse', 'Vaccins', 'Urgences']
        
        return {
            'text': response_text,
            'quick_replies': quick_replies[:4]  # Limiter à 4
        }
    
    def _emergency_response(self):
        """Réponse pour les urgences"""
        emergency_responses = [
            "🚨 **URGENCE MÉDICALE DÉTECTÉE**\n\nComposez immédiatement le **15 (SAMU)** ou le **112**. Restez calme et suivez les instructions de l'opérateur.",
            "⚠️ **SITUATION URGENTE**\n\nContactez les urgences immédiatement au **15**. Ne conduisez pas vous-même à l'hôpital.",
            "🔴 **ALERTE MÉDICALE**\n\nAppelez sans tarder le **112** ou le **15**. Prévenez quelqu'un autour de vous pour vous accompagner."
        ]
        
        return {
            "response": random.choice(emergency_responses),
            "urgency": "high",
            "category": "emergency",
            "tag": "emergency",
            "confidence": 1.0,
            "processing_time_ms": 0,
            "quick_replies": ["Appeler 15", "Appeler 112", "Symptômes urgents"]
        }
    
    def _default_response(self, processing_time, user_id=None):
        """Réponse par défaut quand l'intent n'est pas reconnu"""
        default_responses = [
            "Je comprends votre préoccupation. Pour des conseils personnalisés, veuillez consulter un professionnel de santé.",
            "C'est une bonne question. Je vous recommande d'en parler avec votre sage-femme ou votre médecin lors de votre prochaine consultation.",
            "Je voudrais pouvoir vous aider davantage. Pourriez-vous reformuler votre question ou consulter la section concernée dans votre application ?",
            "Je suis là pour vous accompagner dans votre grossesse. N'hésitez pas à poser des questions sur la nutrition, les vaccins, le suivi médical ou les symptômes."
        ]
        
        return {
            "response": random.choice(default_responses),
            "urgency": "low",
            "category": "general",
            "tag": "unknown",
            "confidence": 0.1,
            "processing_time_ms": processing_time,
            "quick_replies": ["Aide", "FAQ", "Contacter support", "Retour accueil"]
        }
    
    def process_message(self, message, user_id=None):
        """Méthode compatible avec l'ancienne interface"""
        result = self.process_question(message, user_id)
        
        # Format compatible avec l'ancien NLPProcessor
        return result.get("tag", "unknown"), {
            'text': result.get("response", ""),
            'quick_replies': result.get("quick_replies", []),
            'urgency': result.get("urgency", "low"),
            'confidence': result.get("confidence", 0.0)
        }

# Fonctions d'interface pour la compatibilité
processor = HealthProcessor()

def process_question(question):
    """Fonction d'interface principale"""
    return processor.process_question(question)

def process_message(message, user_id=None):
    """Fonction d'interface secondaire (compatibilité)"""
    return processor.process_message(message, user_id)