# Ecriture - Guide d'Utilisation (README)

Créé par Martial Limousin - 2026.
Licence libre CeCILL (http://www.cecill.info/licences/Licence_CeCILL_V2.1-fr.html)

Ce guide vous explique l'objectif, les technologies utilisées, l'installation et l'utilisation de l'application **Ecriture**, un outil d'aide à la rédaction de romans en Python.

---

## 1. Objectif

L'objectif d'**Ecriture** est de fournir aux romanciers et écrivains un environnement de travail moderne, intuitif, web et sans distraction pour planifier, structurer et rédiger leurs œuvres littéraires.

Le logiciel propose :
* **Un éditeur de texte épuré** : Un focus absolu sur les mots avec une police élégante (Georgia) et des marges optimales.
* **Une structuration hiérarchique** : Gestion visuelle des chapitres et des scènes à l'aide d'un arbre de navigation.
* **Le Plot Grid (Grille d'intrigue)** : Un tableau interactif (lignes pour les intrigues secondaires, colonnes pour les scènes) pour planifier l'évolution narrative.
* **Suivi des objectifs et statistiques** : Définition d'objectifs de mots quotidiens et globaux avec des barres de progression dynamiques.
* **Gestion des fiches personnages et notes de recherche** : Fiches détaillées pour centraliser toutes vos idées et la psychologie des personnages.
* **Chronomètre de focus (Focus Timer)** : Un minuteur réglable pour pratiquer la méthode Pomodoro et booster sa productivité.
* **Internationalisation (i18n)** : Une interface disponible en anglais ou en français, gérée par des fichiers de traduction indépendants stockés en dehors du code.

---

## 2. Librairies et Technologies Utilisées

L'application est une Single Page Application (SPA) moderne construite sur une architecture client-serveur ultra-légère :
* **Backend Flask (Python 3)** : Gère les API REST de chargement/sauvegarde de projet et d'export.
* **Données JSON** : Les données du roman sont stockées sous forme structurée dans un fichier JSON (`my_novel_project.json`) géré par `project_manager.py`.
* **Fichiers de Langue Externes** : Traduction gérée par des fichiers JSON situés dans le répertoire `/locales/` (`en.json` et `fr.json`).
* **Frontend Web Moderne** : Une interface construite en HTML, Tailwind CSS et JavaScript moderne (Vanilla JS) avec des animations fluides.

---

## 3. Installation

Pour exécuter le serveur web de l'application sur votre machine, suivez ces étapes simples :

### Prérequis
* **Python 3.8** ou supérieur installé sur votre système.

### Étape 1 : Créer et activer un environnement virtuel (Recommandé)
Il est fortement recommandé d'utiliser un environnement virtuel pour isoler les dépendances de l'application.

Sur **macOS / Linux** :
```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate
```

Sur **Windows** :
```cmd
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement virtuel (Command Prompt)
venv\Scripts\activate.bat

# Activer l'environnement virtuel (PowerShell)
venv\Scripts\Activate.ps1
```

Une fois l'environnement virtuel activé, votre terminal affichera le préfixe `(venv)`.

### Étape 2 : Installer Flask
Exécutez la commande suivante dans votre terminal actif pour installer Flask :
```bash
pip install flask
```

---

## 4. Utilisation

### Lancement du serveur d'application
Démarrez le serveur local de l'application en exécutant :
```bash
python main.py
```

Une fois le serveur démarré, ouvrez votre navigateur web préféré et accédez à :
👉 **[http://localhost:5000](http://localhost:5000)**

### Fonctionnalités Clés & Navigation

1. **Arbre de Navigation (Barre Latérale Gauche)** :
   * **Recherche** : Saisissez du texte dans la barre supérieure pour filtrer instantanément vos scènes, personnages et notes.
   * **Boutons Rapides** : Utilisez `+ Chapitre`, `+ Scène` et `+ Ressource` (Personnage/Note) en bas de la barre latérale pour enrichir votre roman.
   * **Boutons d'action (✏️/🗑️)** : Permettent de renommer ou de supprimer à la volée n'importe quel élément.

2. **Éditeur de Texte Sans Distraction (Zone Centrale)** :
   * Cliquez sur une scène ou un chapitre dans la barre latérale pour l'ouvrir dans l'éditeur.
   * Modifiez le titre ou le contenu directement. L'application sauvegarde vos modifications **automatiquement et silencieusement** en arrière-plan à chaque frappe.
   * Le compteur en bas à droite affiche le nombre exact de mots et de caractères en temps réel.

3. **Grille d'Intrigue (Plot Grid)** :
   * Cliquez sur le bouton **Grille d'intrigue** dans la barre latérale gauche pour l'afficher.
   * Ajoutez des cartes à vos lignes narratives en cliquant sur `+ Ajouter carte`.
   * Cliquez sur une carte existante pour ouvrir un dialogue modal afin de modifier son titre, son résumé ou de la supprimer.

4. **Objectifs & Focus (Barre Latérale Droite)** :
   * Ajustez votre objectif de mots quotidiens directement dans le champ de saisie. Les barres de progression se mettront à jour en temps réel à mesure que vous écrivez.
   * Utilisez le **Minuteur Focus** pour configurer vos sessions de rédaction. Ajustez la durée avec le curseur, puis cliquez sur `Démarrer` / `Pause` / `Réinitialiser`.

5. **Barre de Titre (En-tête)** :
   * **Sélecteur de Langue** : Changez instantanément la langue de l'application (Français 🇫🇷 / Anglais 🇬🇧). L'interface sera traduite dynamiquement sans aucun rechargement de page.
   * **Bouton Exporter en .txt** : Compiles et télécharge instantanément l'intégralité de votre roman structuré dans un fichier texte brut `.txt`.
   * **Bouton Paramètres** : Permet de renommer l'œuvre et d'ajuster l'objectif de mots global.
