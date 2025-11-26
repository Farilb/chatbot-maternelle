// Application principale - Fonctions utilitaires
class HealthApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkUserStatus();
        this.setupServiceWorker();
    }

    // Vérification du statut utilisateur
    checkUserStatus() {
        const userType = document.body.getAttribute('data-user-type') || 'guest';
        if (userType === 'guest') {
            this.showGuestNotification();
        }
    }

    // Notification pour les utilisateurs non enregistrés
    showGuestNotification() {
        if (!document.getElementById('guestAlert')) {
            const alert = document.createElement('div');
            alert.id = 'guestAlert';
            alert.className = 'alert alert-info alert-dismissible fade show m-3';
            alert.innerHTML = `
                <i class="fas fa-info-circle me-2"></i>
                <strong>Profitez pleinement de l'application !</strong> 
                <a href="/profile-setup" class="alert-link">Créez votre profil</a> 
                pour un suivi personnalisé de votre grossesse et des rappels de vaccins.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('main').prepend(alert);
        }
    }

    // Configuration des écouteurs d'événements globaux
    setupEventListeners() {
        // Gestion des tooltips Bootstrap
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Gestion des popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });

        // Confirmation des actions importantes
        this.setupConfirmations();
    }

    // Configuration des confirmations
    setupConfirmations() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-confirm]')) {
                const message = e.target.closest('[data-confirm]').getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                }
            }
        });
    }

    // Service Worker pour les notifications push (future implémentation)
    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('SW registered: ', registration);
                })
                .catch(registrationError => {
                    console.log('SW registration failed: ', registrationError);
                });
        }
    }

    // Fonction utilitaire pour formater les dates
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }

    // Fonction utilitaire pour formater les heures
    formatTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // Gestion des chargements
    showLoading(element) {
        element.classList.add('loading');
        element.disabled = true;
        const originalText = element.innerHTML;
        element.innerHTML = `<span class="loading-spinner me-2"></span>Chargement...`;
        return originalText;
    }

    hideLoading(element, originalText) {
        element.classList.remove('loading');
        element.disabled = false;
        element.innerHTML = originalText;
    }

    // Gestion des erreurs
    showError(message, container = null) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        if (container) {
            container.prepend(errorDiv);
        } else {
            document.querySelector('main').prepend(errorDiv);
        }

        // Auto-dismiss après 5 secondes
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }

    // Gestion des succès
    showSuccess(message, container = null) {
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success alert-dismissible fade show';
        successDiv.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        if (container) {
            container.prepend(successDiv);
        } else {
            document.querySelector('main').prepend(successDiv);
        }

        // Auto-dismiss après 3 secondes
        setTimeout(() => {
            if (successDiv.parentElement) {
                successDiv.remove();
            }
        }, 3000);
    }

    // Calcul de l'âge gestationnel
    calculatePregnancyWeek(startDate) {
        const start = new Date(startDate);
        const today = new Date();
        const diffTime = Math.abs(today - start);
        const diffWeeks = Math.floor(diffTime / (1000 * 60 * 60 * 24 * 7));
        return Math.min(diffWeeks, 42); // Max 42 semaines
    }

    // Validation de formulaire
    validateForm(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });

        return isValid;
    }

    // Formatage des numéros de téléphone
    formatPhoneNumber(phone) {
        return phone.replace(/(\d{2})(?=\d)/g, '$1 ');
    }

    // Copie dans le presse-papier
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showSuccess('Copié dans le presse-papier !');
        } catch (err) {
            console.error('Erreur de copie: ', err);
            this.showError('Erreur lors de la copie');
        }
    }
}

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', function() {
    window.healthApp = new HealthApp();
});

// Fonctions globales utilitaires
window.utils = {
    // Débounce pour limiter les appels API
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Capitalisation
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    },

    // Truncate text
    truncate(text, length = 100) {
        if (text.length <= length) return text;
        return text.substring(0, length) + '...';
    },

    // Sanitize HTML
    sanitize(html) {
        const temp = document.createElement('div');
        temp.textContent = html;
        return temp.innerHTML;
    }
};