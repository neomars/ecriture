# Dabble Novelist Studio - Guide d'Utilisation (HOWTO)

Ce guide vous explique l'objectif, les librairies utilisées, l'installation et l'utilisation de l'application **Dabble Novelist Studio**, un outil d'aide à la rédaction de romans en Python inspiré de Dabble Writer.

---

## 1. Objectif

L'objectif de **Dabble Novelist Studio** est de fournir aux romanciers et écrivains un environnement de travail moderne, intuitif et sans distraction pour planifier, structurer et rédiger leurs œuvres littéraires.

Le logiciel propose :
* **Un éditeur de texte épuré** : Un focus absolu sur les mots avec une police élégante (Georgia) et des marges optimales.
* **Une structuration hiérarchique** : Gestion visuelle des chapitres et des scènes à l'aide d'un arbre de navigation.
* **Le Plot Grid (Grille d'intrigue)** : Un tableau à double entrée (lignes pour les intrigues secondaires, colonnes pour les scènes) pour planifier l'évolution narrative à la manière de Dabble Writer.
* **Suivi des objectifs et statistiques** : Définition d'objectifs de mots quotidiens et globaux avec des barres de progression interactives.
* **Gestion des fiches personnages et notes de recherche** : Fiches détaillées pour centraliser toutes vos idées et la psychologie des personnages.
* **Chronomètre de focus (Focus Timer)** : Un minuteur réglable pour pratiquer la méthode Pomodoro et booster sa productivité.

---

## 2. Librairies Utilisées

L'application est entièrement écrite en Python 3 et s'appuie sur les bibliothèques suivantes :
* **Tkinter** (Standard Python) : Pour la structure de base des fenêtres de dialogue et les composants Treeview.
* **CustomTkinter** (`customtkinter`) : Pour l'interface utilisateur moderne, les boutons stylisés, les barres de progression et le thème clair élégant.
* **JSON** (Standard Python) : Utilisé pour la sérialisation et la sauvegarde automatique et structurée de vos projets.

---

## 3. Installation

Pour exécuter l'application sur votre machine, suivez ces étapes simples :

### Prérequis
* **Python 3.8** ou supérieur installé sur votre système.

### Étape 1 : Installer CustomTkinter
Exécutez la commande suivante dans votre terminal pour installer la bibliothèque d'interface moderne :
```bash
pip install customtkinter
```

*(Optionnel)* Si vous utilisez Linux sans environnement graphique natif (par exemple sur un serveur ou un conteneur), assurez-vous d'avoir un serveur X virtuel installé comme `Xvfb`.

---

## 4. Utilisation

### Lancement de l'application
Démarrez l'application en exécutant le script principal :
```bash
python main.py
```

### Fonctionnalités Clés & Navigation

1. **Arbre de Navigation (Barre Latérale Gauche)** :
   * **Recherche** : Saisissez du texte dans la barre supérieure pour filtrer instantanément vos scènes, personnages et notes.
   * **Boutons Rapides** : Utilisez `+ Chapter`, `+ Scene` et `+ Asset` (Personnage/Note) en bas de la barre latérale pour enrichir votre roman.
   * **Clic Droit (Menu Contextuel)** : Faites un clic droit sur n'importe quel élément pour le renommer, le supprimer, ou lui ajouter un sous-élément.

2. **Éditeur de Texte Sans Distraction (Zone Centrale)** :
   * Cliquez sur une scène dans la barre latérale pour l'ouvrir.
   * Modifiez le titre ou le contenu directement. L'application sauvegarde vos modifications **automatiquement et silencieusement** à chaque frappe.
   * Le compteur en bas à droite affiche le nombre exact de mots et de caractères en temps réel.

3. **Grille d'Intrigue (Plot Grid)** :
   * Double-cliquez sur l'option **Plot Grid** dans la barre latérale gauche pour l'afficher.
   * Ajoutez des cartes à vos lignes narratives (Romance, Scandale, Classe, etc.) en cliquant sur `+ Add Card`.
   * Double-cliquez sur une carte existante pour modifier son titre, son résumé ou la supprimer.

4. **Objectifs & Focus (Barre Latérale Droite)** :
   * Ajustez votre objectif de mots quotidiens directement dans la case d'entrée. Les barres de progression se mettront à jour à mesure que vous écrivez.
   * Utilisez le **Focus Timer** pour configurer vos sessions d'écriture. Réglez la durée avec le curseur, puis cliquez sur `Start` / `Pause` / `Reset`.

5. **Menu Fichier (Barre de Menu)** :
   * **File -> New Project** : Crée un nouveau canevas vide pour votre roman.
   * **File -> Open Project** : Recharge votre projet depuis le fichier JSON.
   * **File -> Export as Text file** : Compile et exporte l'intégralité de votre manuscrit structuré dans un fichier texte brut `.txt` prêt à être partagé ou publié.
   * **Edit -> Project Settings** : Modifiez le titre de votre œuvre et l'objectif de mots global (ex: 50 000 mots pour le NaNoWriMo).
