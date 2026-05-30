import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import numpy as np

# Configuration
fig, ax = plt.subplots(figsize=(14, 10))

# Définition des couleurs
colors = {
    'conception': '#4A90E2',      # Bleu
    'backend': '#7ED321',         # Vert
    'frontend': '#F5A623',        # Orange
    'tests': '#D0021B',           # Rouge
    'documentation': '#9013FE'    # Violet
}

# Définition des tâches
tasks = [
    # Sprint 1 - Conception (Semaine 1)
    {'name': 'Cahier des charges', 'start': 0, 'duration': 1, 'color': colors['conception']},
    {'name': 'Diagrammes UML', 'start': 0, 'duration': 1, 'color': colors['conception']},
    {'name': 'Diagrammes séquence', 'start': 0, 'duration': 1, 'color': colors['conception']},
    {'name': 'Wireframes', 'start': 0, 'duration': 1, 'color': colors['conception']},
    
    # Sprint 2 - Backend Auth (Semaine 2)
    {'name': 'Configuration Flask', 'start': 1, 'duration': 1, 'color': colors['backend']},
    {'name': 'Modèles SQLAlchemy', 'start': 1, 'duration': 1, 'color': colors['backend']},
    {'name': 'Routes Auth', 'start': 1, 'duration': 1, 'color': colors['backend']},
    {'name': 'Bcrypt + JWT', 'start': 1, 'duration': 1, 'color': colors['backend']},
    
    # Sprint 3 - Backend Logs (Semaine 3)
    {'name': 'Table Logs étendue', 'start': 2, 'duration': 1, 'color': colors['backend']},
    {'name': 'Capture métadonnées', 'start': 2, 'duration': 1, 'color': colors['backend']},
    {'name': 'Géolocalisation IP', 'start': 2, 'duration': 1, 'color': colors['backend']},
    
    # Sprint 4 - Backend IA (Semaine 4)
    {'name': 'Dataset simulé', 'start': 3, 'duration': 1, 'color': colors['backend']},
    {'name': 'Isolation Forest', 'start': 3, 'duration': 1, 'color': colors['backend']},
    {'name': 'Feature Engineering', 'start': 3, 'duration': 1, 'color': colors['backend']},
    {'name': 'Système alertes', 'start': 3, 'duration': 1, 'color': colors['backend']},
    {'name': 'Emails automatiques', 'start': 3, 'duration': 1, 'color': colors['backend']},
    
    # Sprint 5 - Frontend + Tests (Semaine 5)
    {'name': 'Interfaces Tailwind', 'start': 4, 'duration': 1, 'color': colors['frontend']},
    {'name': 'Dashboard Admin', 'start': 4, 'duration': 1, 'color': colors['frontend']},
    {'name': 'Gestion utilisateurs', 'start': 4, 'duration': 1, 'color': colors['frontend']},
    {'name': 'Tests 8 scénarios', 'start': 4, 'duration': 1, 'color': colors['tests']},
    {'name': 'Corrections bugs', 'start': 4, 'duration': 1, 'color': colors['tests']},
    
    # Sprint 6 - Documentation (Semaine 6)
    {'name': 'Documentation technique', 'start': 5, 'duration': 1, 'color': colors['documentation']},
    {'name': 'Rapport PFA (50 pages)', 'start': 5, 'duration': 1, 'color': colors['documentation']},
    {'name': 'Préparation soutenance', 'start': 5, 'duration': 1, 'color': colors['documentation']},
]

# Dessiner les barres
y_pos = np.arange(len(tasks))
for i, task in enumerate(tasks):
    ax.barh(i, task['duration'], left=task['start'], 
            height=0.8, color=task['color'], 
            edgecolor='white', linewidth=1.5)
    
    # Ajouter le nom de la tâche à gauche
    ax.text(-0.2, i, task['name'], 
            va='center', ha='right', fontsize=9, fontweight='normal')

# Configuration des axes
ax.set_yticks([])
ax.set_xticks(range(7))
ax.set_xticklabels(['', 'Semaine 1', 'Semaine 2', 'Semaine 3', 
                     'Semaine 4', 'Semaine 5', 'Semaine 6'], 
                    fontsize=11, fontweight='bold')

# Grille verticale
ax.set_xlim(-0.5, 6)
ax.set_ylim(-1, len(tasks))
ax.grid(axis='x', color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
ax.invert_yaxis()

# Titre
ax.set_title('Diagramme de Gantt - Projet AuthGuard IA\nPlateforme d\'Authentification Intelligente avec Détection d\'Anomalies par IA', 
             fontsize=14, fontweight='bold', pad=20)

# Légende
legend_elements = [
    mpatches.Patch(facecolor=colors['conception'], edgecolor='white', label='Conception et modélisation'),
    mpatches.Patch(facecolor=colors['backend'], edgecolor='white', label='Développement backend'),
    mpatches.Patch(facecolor=colors['frontend'], edgecolor='white', label='Développement frontend'),
    mpatches.Patch(facecolor=colors['tests'], edgecolor='white', label='Tests et validation'),
    mpatches.Patch(facecolor=colors['documentation'], edgecolor='white', label='Documentation et livraison')
]
ax.legend(handles=legend_elements, loc='upper center', 
          bbox_to_anchor=(0.5, -0.05), ncol=3, 
          frameon=True, fontsize=10, title='Légende', title_fontsize=11)

# Ajouter les groupes de sprints
sprint_labels = [
    {'text': 'Sprint 1\n(10h)', 'x': 0.5, 'y': -0.5},
    {'text': 'Sprint 2\n(11h)', 'x': 1.5, 'y': -0.5},
    {'text': 'Sprint 3\n(10h)', 'x': 2.5, 'y': -0.5},
    {'text': 'Sprint 4\n(16h)', 'x': 3.5, 'y': -0.5},
    {'text': 'Sprint 5\n(15h)', 'x': 4.5, 'y': -0.5},
    {'text': 'Sprint 6\n(13h)', 'x': 5.5, 'y': -0.5}
]

for label in sprint_labels:
    ax.text(label['x'], label['y'], label['text'], 
            ha='center', va='top', fontsize=9, 
            fontweight='bold', color='#333333',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#f0f0f0', edgecolor='gray', linewidth=1))

# Retirer les bordures
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)

# Ajustement layout
plt.tight_layout()

# Sauvegarder l'image
plt.savefig('gantt_authguard.png', dpi=300, bbox_inches='tight', facecolor='white')
print("✅ Diagramme de Gantt généré : gantt_authguard.png")

# Afficher
plt.show()