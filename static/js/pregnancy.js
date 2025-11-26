// Gestion du suivi de grossesse
class PregnancyTracker {
    constructor() {
        this.currentPregnancy = null;
        this.init();
    }

    async init() {
        await this.loadPregnancyData();
        this.setupEventListeners();
        this.updatePregnancyProgress();
    }

    async loadPregnancyData() {
        try {
            const response = await fetch('/api/pregnancy');
            if (response.ok) {
                const data = await response.json();
                this.currentPregnancy = data.pregnancy;
                this.updateUI();
            }
        } catch (error) {
            console.error('Erreur chargement grossesse:', error);
        }
    }

    setupEventListeners() {
        // Formulaire de grossesse
        document.getElementById('pregnancyForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.savePregnancy();
        });

        // Calcul automatique de la date prévue
        document.getElementById('startDate')?.addEventListener('change', (e) => {
            this.calculateDueDate(e.target.value);
        });

        // Boutons d'action rapide
        this.setupQuickActions();
    }

    calculateDueDate(startDate) {
        if (!startDate) return;

        const start = new Date(startDate);
        const dueDate = new Date(start);
        dueDate.setDate(dueDate.getDate() + 280); // 40 semaines

        const dueDateElement = document.getElementById('dueDatePreview');
        if (dueDateElement) {
            dueDateElement.textContent = dueDate.toLocaleDateString('fr-FR');
            dueDateElement.style.display = 'block';
        }
    }

    async savePregnancy() {
        const form = document.getElementById('pregnancyForm');
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = window.healthApp.showLoading(submitButton);

        try {
            const formData = {
                start_date: document.getElementById('startDate').value,
                medical_history: {
                    diabetes: document.getElementById('diabetes').checked,
                    hypertension: document.getElementById('hypertension').checked,
                    allergies: document.getElementById('allergies').checked
                }
            };

            const response = await fetch('/api/pregnancy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok) {
                window.healthApp.showSuccess('Grossesse enregistrée avec succès !');
                
                // Fermer le modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('pregnancyModal'));
                modal.hide();
                
                // Recharger les données
                await this.loadPregnancyData();
            } else {
                throw new Error(data.error || 'Erreur lors de la sauvegarde');
            }
        } catch (error) {
            window.healthApp.showError(error.message);
        } finally {
            window.healthApp.hideLoading(submitButton, originalText);
        }
    }

    updateUI() {
        if (!this.currentPregnancy) return;

        // Mise à jour de la progression
        this.updateProgressBar();
        
        // Mise à jour des informations
        this.updatePregnancyInfo();
        
        // Mise à jour du développement du bébé
        this.updateBabyDevelopment();
    }

    updateProgressBar() {
        const progressBar = document.querySelector('.progress-bar');
        const weekDisplay = document.querySelector('.week-display');
        
        if (progressBar && weekDisplay) {
            const percentage = (this.currentPregnancy.week_current / 40) * 100;
            progressBar.style.width = `${percentage}%`;
            progressBar.textContent = `${this.currentPregnancy.week_current}/40 semaines`;
            weekDisplay.textContent = `${this.currentPregnancy.week_current} SA`;
        }
    }

    updatePregnancyInfo() {
        // Mise à jour des dates
        const startDateElement = document.getElementById('startDateDisplay');
        const dueDateElement = document.getElementById('dueDateDisplay');
        
        if (startDateElement) {
            startDateElement.textContent = new Date(this.currentPregnancy.start_date).toLocaleDateString('fr-FR');
        }
        if (dueDateElement) {
            dueDateElement.textContent = new Date(this.currentPregnancy.due_date).toLocaleDateString('fr-FR');
        }

        // Mise à jour du trimestre
        const trimesterElement = document.getElementById('trimesterDisplay');
        if (trimesterElement) {
            trimesterElement.textContent = this.currentPregnancy.trimester;
            trimesterElement.className = `badge bg-${this.getTrimesterColor(this.currentPregnancy.trimester)}`;
        }
    }

    async updateBabyDevelopment() {
        try {
            const response = await fetch('/api/baby-development');
            if (response.ok) {
                const data = await response.json();
                this.displayBabyDevelopment(data);
            }
        } catch (error) {
            console.error('Erreur développement bébé:', error);
        }
    }

    displayBabyDevelopment(data) {
        const developmentElement = document.getElementById('babyDevelopment');
        if (developmentElement && data.development) {
            developmentElement.innerHTML = `
                <h6>Semaine ${data.week} - ${this.getTrimesterName(data.trimester)} trimestre</h6>
                <p class="mb-0">${data.development}</p>
            `;
        }
    }

    getTrimesterColor(trimester) {
        const colors = {
            1: 'success',
            2: 'warning', 
            3: 'danger'
        };
        return colors[trimester] || 'secondary';
    }

    getTrimesterName(trimester) {
        const names = {
            1: 'premier',
            2: 'deuxième',
            3: 'troisième'
        };
        return names[trimester] || '';
    }

    updatePregnancyProgress() {
        if (!this.currentPregnancy) return;

        // Mise à jour quotidienne de la progression
        const today = new Date();
        const startDate = new Date(this.currentPregnancy.start_date);
        const daysPassed = Math.floor((today - startDate) / (1000 * 60 * 60 * 24));
        const currentWeek = Math.floor(daysPassed / 7);

        if (currentWeek !== this.currentPregnancy.week_current) {
            // La semaine a changé, mettre à jour l'affichage
            this.currentPregnancy.week_current = currentWeek;
            this.updateUI();
        }
    }

    setupQuickActions() {
        // Ajouter un rappel de visite
        document.getElementById('addAppointment')?.addEventListener('click', () => {
            this.addAppointment();
        });

        // Ajouter un symptôme
        document.getElementById('addSymptom')?.addEventListener('click', () => {
            this.trackSymptom();
        });

        // Partager la progression
        document.getElementById('shareProgress')?.addEventListener('click', () => {
            this.shareProgress();
        });
    }

    addAppointment() {
        // Implémentation pour ajouter un rendez-vous
        console.log('Ajouter un rendez-vous');
    }

    trackSymptom() {
        // Implémentation pour tracker un symptôme
        console.log('Tracker un symptôme');
    }

    shareProgress() {
        if (!this.currentPregnancy) return;

        const shareText = `🤰 Ma grossesse : ${this.currentPregnancy.week_current} semaines - ${this.getTrimesterName(this.currentPregnancy.trimester)} trimestre. Suivi avec Maman & Bébé ❤️`;
        
        if (navigator.share) {
            navigator.share({
                title: 'Ma progression de grossesse',
                text: shareText,
                url: window.location.href
            });
        } else {
            window.healthApp.copyToClipboard(shareText);
        }
    }

    // Calcul des prochaines étapes importantes
    getNextMilestones() {
        if (!this.currentPregnancy) return [];

        const milestones = [
            { week: 12, title: 'Échographie de datation', type: 'scan' },
            { week: 22, title: 'Échographie morphologique', type: 'scan' },
            { week: 32, title: 'Dernière échographie', type: 'scan' },
            { week: 36, title: 'Consultation pré-anesthésique', type: 'consultation' },
            { week: 41, title: 'Dépassement de terme', type: 'monitoring' }
        ];

        return milestones.filter(milestone => milestone.week > this.currentPregnancy.week_current)
                        .slice(0, 3);
    }
}

// Initialisation du tracker de grossesse
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('pregnancyTracker')) {
        window.pregnancyTracker = new PregnancyTracker();
    }
});