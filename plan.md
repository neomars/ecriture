1.  **UI - Settings Modal:**
    *   Add an icon/button next to the "Configuration des Sauvegardes" title in the Project Settings modal (`templates/index.html`) for "Restauration / Importation" (Restore / Import).
2.  **UI - Restoration Modal:**
    *   Create a new modal (`#restore-modal`) in `templates/index.html` (initially hidden).
    *   The modal should contain a warning message emphasizing that **all current project data will be overwritten** by restoring or importing.
    *   The modal should have two sections:
        *   **Local Backups List:** A container to dynamically list existing `.json` backups for the current project.
        *   **File Import:** An `<input type="file" accept=".txt,.rtf,.odt,.doc,.docx,.epub">` for importing a project from standard text/document formats.
    *   Include "Annuler" and "Continuer/Restaurer" buttons.
3.  **Backend - List Backups:**
    *   Create a new Flask route (`/api/backups/local/list`) in `main.py` that reads the configured backup directory and returns a list of backup files (sorted by date) associated with the current project ID.
4.  **Backend - Restore Backup (.json):**
    *   Create a route (`/api/backups/local/restore`) in `main.py` that takes a backup filename, reads it, and forcefully overwrites the active project's state in memory and on disk.
5.  **Backend - Import Document (.txt, .docx, .odt, etc):**
    *   Create a route (`/api/import/document`) in `main.py` that accepts a file upload.
    *   It will parse the uploaded file, extract the raw text, and create a basic single-chapter/single-scene structure containing that text, overwriting the current project's manuscript. It should support `.txt`, `.docx` (via `python-docx` if available), and `.epub`/`.odt` (by reading the text contents inside the zip).
6.  **Frontend - Integration:**
    *   Update `moteur.js` to handle opening the restore modal, fetching and rendering the backup list, and handling the restore/import actions (which trigger the endpoints and force a page reload upon success).
7.  **Pre-commit Checks:**
    *   Run tests and use Playwright to verify the UI.
