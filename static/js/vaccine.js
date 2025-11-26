// Gestion des rappels de vaccins
class VaccineTracker {
    constructor() {
        this.reminders = [];
        this.init();
    }

    async init() {
        await this.loadVaccineReminders();
        this.setupEventListeners();
        this.setupReminderNotifications();
    }

    async loadVaccineReminders() {
        try {
            const response = await fetch('/api/vaccine-reminders');
            if (response.ok) {
                const data = await response.json();
                this.reminders = data.reminders || [];
                this.displayReminders();
            }
        } catch (error) {
            console.error('Erreur chargement rappels:', error);
        }
    }

    displayReminders() {
        const container = document.getElementById('vaccineReminders');
        if (!container) return;

        if (this.reminders.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-syringe fa-2x mb-2"></i>
                    <p>Aucun rappel de vaccin pour le moment</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.reminders.map(reminder => `
            <div class="alert alert-${this.getReminderAlertType(reminder)}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="alert-heading">
                            <i class="fas fa-bell me-2"></i>
                            ${reminder.child_name} - ${reminder.milestone}
                        </h6>
                        <p class="mb-1">
                            <strong>Vaccins :</strong> ${reminder.vaccines.join(', ')}
                        </p>
                        <small>
                            Date recommandée : ${new Date(reminder.recommended_date).toLocaleDateString('fr-FR')}
                        </small>
                    </div>
                    <span class="badge bg-${this.getReminderBadgeType(reminder)}">
                        ${reminder.status === 'due' ? 'À faire' : 'Prochainement'}
                    </span>
                </div>
                ${reminder.status === 'due' ? `
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary me-2" onclick="vaccineTracker.markAsDone('${reminder.child_name}', ${JSON.stringify(reminder.vaccines).replace(/'/g, "\\'")})">
                        <i class="fas fa-check me-1"></i>Marquer comme fait
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="vaccineTracker.snoozeReminder('${reminder.child_name}', ${JSON.stringify(reminder.vaccines).replace(/'/g, "\\'")})">
                        <i class="fas fa-clock me-1"></i>Rappeler plus tard
                    </button>
                </div>
                ` : ''}
            </div>
        `).join('');
    }

    getReminderAlertType(reminder) {
        return reminder.status === 'due' ? 'warning' : 'info';
    }

    getReminderBadgeType(reminder) {
        return reminder.status === 'due' ? 'danger' : 'warning';
    }

    setupEventListeners() {
        // Actualiser les rappels
        document.getElementById('refreshReminders')?.addEventListener('click', () => {
            this.loadVaccineReminders();
        });

        // Ajouter un enfant
        document.getElementById('addChild')?.addEventListener('click', () => {
            this.showAddChildForm();
        });
    }

    setupReminderNotifications() {
        // Vérifier les rappels échus toutes les heures
        setInterval(() => {
            this.checkDueReminders();
        }, 60 * 60 * 1000);

        // Vérification immédiate au chargement
        this.checkDueReminders();
    }

    checkDueReminders() {
        const dueReminders = this.reminders.filter(r => r.status === 'due');
        
        if (dueReminders.length > 0 && Notification.permission === 'granted') {
            dueReminders.forEach(reminder => {
                new Notification('💉 Rappel de vaccin - Maman & Bébé', {
                    body: `${reminder.child_name} : ${reminder.vaccines.join(', ')}`,
                    icon: '/static/images/vaccine-icon.png',
                    tag: 'vaccine-reminder'
                });
            });
        }
    }

    async markAsDone(childName, vaccines) {
        if (confirm(`Marquer les vaccins ${vaccines.join(', ')} de ${childName} comme effectués ?`)) {
            try {
                // Ici, vous enverriez une requête au backend pour marquer comme fait
                console.log(`Vaccins marqués comme faits: ${vaccines.join(', ')} pour ${childName}`);
                
                window.healthApp.showSuccess('Vaccins marqués comme effectués !');
                await this.loadVaccineReminders();
            } catch (error) {
                window.healthApp.showError('Erreur lors de la mise à jour');
            }
        }
    }

    snoozeReminder(childName, vaccines) {
        // Implémentation pour reporter le rappel
        console.log(`Rappel reporté pour: ${vaccines.join(', ')} de ${childName}`);
        window.healthApp.showSuccess('Rappel reporté de 7 jours');
    }

    showAddChildForm() {
        // Implémentation du formulaire d'ajout d'enfant
        console.log('Afficher formulaire ajout enfant');
    }

    // Calculatrice de date de vaccin
    calculateNextVaccine(birthDate, vaccineName) {
        const birth = new Date(birthDate);
        const schedules = {
            'BCG': 0,
            'DTP': 60,
            'Hib': 60,
            'Hépatite B': 60,
            'Pneumocoque': 60,
            'Rotavirus': 60,
            'ROR': 365,
            'Méningocoque C': 365
        };

        const days = schedules[vaccineName];
        if (days !== undefined) {
            const nextDate = new Date(birth);
            nextDate.setDate(nextDate.getDate() + days);
            return nextDate;
        }

        return null;
    }
}

// Initialisation du tracker de vaccins
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('vaccineReminders')) {
        window.vaccineTracker = new VaccineTracker();
    }
});