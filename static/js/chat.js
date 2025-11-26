// Gestion du chat
class HealthChat {
    constructor() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.sendButton = document.getElementById('sendButton');
        this.consultationsList = document.getElementById('consultationsList');
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.scrollToBottom();
        this.loadConsultationHistory();
    }

    setupEventListeners() {
        // Envoi de message
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Questions rapides
        document.querySelectorAll('.quick-question').forEach(button => {
            button.addEventListener('click', (e) => {
                const question = e.target.getAttribute('data-question');
                this.messageInput.value = question;
                this.sendMessage();
            });
        });

        // Touche Entrée pour envoyer (avec Shift+Enter pour nouvelle ligne)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Effacer la conversation
        document.getElementById('clearChat')?.addEventListener('click', () => {
            this.clearConversation();
        });

        // Auto-resize du textarea
        this.messageInput.addEventListener('input', this.autoResize.bind(this));
    }

    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message) return;

        // Ajouter le message de l'utilisateur
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.autoResize();

        // Afficher l'indicateur de frappe
        this.showTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();

            // Supprimer l'indicateur de frappe
            this.hideTypingIndicator();

            if (response.ok) {
                this.addMessage(data.response, 'bot', data.urgency, data.category);
                this.updateConsultationHistory();
                
                // Alerte visuelle pour les urgences
                if (data.urgency === 'high') {
                    this.showUrgencyAlert();
                }
            } else {
                throw new Error(data.error || 'Erreur lors de l\'envoi du message');
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage(
                'Désolé, une erreur est survenue. Veuillez réessayer.', 
                'bot', 
                'low',
                'error'
            );
            console.error('Erreur chat:', error);
        }
    }

    addMessage(content, sender, urgency = 'low', category = 'general') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = sender === 'bot' ? 
            '<i class="fas fa-robot"></i>' : 
            '<i class="fas fa-user"></i>';
        
        const urgencyBadge = urgency !== 'low' ? 
            `<span class="badge urgency-${urgency} ms-2">${urgency}</span>` : '';
        
        const categoryIcon = this.getCategoryIcon(category);

        messageDiv.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    ${categoryIcon}
                    ${this.formatMessage(content)}
                    ${urgencyBadge}
                </div>
                <small class="message-time">${this.getCurrentTime()}</small>
            </div>
        `;

        // Animation d'apparition
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        
        this.messagesContainer.appendChild(messageDiv);
        
        // Animation
        setTimeout(() => {
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
            messageDiv.style.transition = 'all 0.3s ease-in-out';
        }, 10);

        this.scrollToBottom();
    }

    formatMessage(content) {
        // Convertir les retours à la ligne en <br>
        content = content.replace(/\n/g, '<br>');
        
        // Mise en forme des listes
        content = content.replace(/\•\s*(.+?)(?=\n|$)/g, '<li>$1</li>');
        if (content.includes('<li>')) {
            content = content.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        }
        
        return content;
    }

    getCategoryIcon(category) {
        const icons = {
            'nutrition': '🍎 ',
            'vaccine': '💉 ',
            'emergency': '🚨 ',
            'pregnancy': '🤰 ',
            'baby_care': '👶 ',
            'error': '⚠️ ',
            'general': '💬 '
        };
        return icons[category] || icons.general;
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'message bot-message';
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <small>L'assistant écrit</small>
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    getCurrentTime() {
        return new Date().toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    async loadConsultationHistory() {
        try {
            const response = await fetch('/api/consultations?limit=10');
            const data = await response.json();
            
            if (response.ok && data.consultations) {
                this.updateConsultationsList(data.consultations);
            }
        } catch (error) {
            console.error('Erreur chargement historique:', error);
        }
    }

    updateConsultationHistory() {
        // Recharger l'historique après un nouveau message
        setTimeout(() => {
            this.loadConsultationHistory();
        }, 1000);
    }

    updateConsultationsList(consultations) {
        if (!this.consultationsList) return;

        this.consultationsList.innerHTML = '';

        if (consultations.length === 0) {
            this.consultationsList.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>Aucune conversation</p>
                </div>
            `;
            return;
        }

        consultations.forEach(consult => {
            const consultDiv = document.createElement('div');
            consultDiv.className = `consultation-item p-3 border-bottom urgency-${consult.urgency}`;
            
            const date = new Date(consult.date_consultation);
            const dateStr = date.toLocaleDateString('fr-FR', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });

            consultDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <small class="text-muted">${dateStr}</small>
                    <span class="badge bg-${this.getUrgencyColor(consult.urgency)}">
                        ${consult.urgency}
                    </span>
                </div>
                <p class="mb-1 small text-truncate">${consult.question}</p>
            `;

            consultDiv.addEventListener('click', () => {
                this.loadConsultation(consult);
            });

            this.consultationsList.appendChild(consultDiv);
        });
    }

    getUrgencyColor(urgency) {
        const colors = {
            'high': 'danger',
            'medium': 'warning',
            'low': 'info'
        };
        return colors[urgency] || 'secondary';
    }

    loadConsultation(consultation) {
        // Vider la conversation actuelle
        this.messagesContainer.innerHTML = '';
        
        // Recréer la conversation
        this.addMessage(consultation.question, 'user');
        this.addMessage(consultation.response, 'bot', consultation.urgency);
    }

    clearConversation() {
        if (confirm('Voulez-vous vraiment effacer cette conversation ?')) {
            this.messagesContainer.innerHTML = '';
            
            // Message de bienvenue
            this.addMessage(
                'Conversation effacée. Comment puis-je vous aider ?', 
                'bot', 
                'low'
            );
        }
    }

    showUrgencyAlert() {
        const alertSound = document.getElementById('alertSound');
        if (alertSound) {
            alertSound.play().catch(e => console.log('Audio play failed:', e));
        }

        // Notification visuelle
        if (Notification.permission === 'granted') {
            new Notification('Alerte Santé - Maman & Bébé', {
                body: 'Une situation nécessite une attention médicale immédiate',
                icon: '/static/images/icon.png'
            });
        }

        // Flash du navigateur si supporté
        if ('vibrate' in navigator) {
            navigator.vibrate([200, 100, 200]);
        }
    }
}

// Initialisation du chat
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('chatMessages')) {
        window.healthChat = new HealthChat();
    }
});