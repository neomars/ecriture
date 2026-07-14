import os
import json
from flask import Flask, jsonify, request, send_file, render_template
from project_manager import NovelProject

app = Flask(__name__, template_folder='templates')

PROJECTS_DIR = "projects"
ACTIVE_CONFIG_FILE = "active_project.txt"

# Ensure projects directory exists
if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)

def get_active_project_filename():
    """Gets the currently active project filename from config or defaults."""
    if os.path.exists(ACTIVE_CONFIG_FILE):
        with open(ACTIVE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            fn = f.read().strip()
            if fn and os.path.exists(os.path.join(PROJECTS_DIR, fn)):
                return fn

    # Fallback: scan projects directory or create a default one
    files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith(".json")]
    if files:
        # Save first as active
        set_active_project_filename(files[0])
        return files[0]

    # If no files exist, create a default one
    default_fn = "my_novel_project.json"
    default_path = os.path.join(PROJECTS_DIR, default_fn)

    # If we have an existing my_novel_project.json in root, move it or create a clean one
    if os.path.exists("my_novel_project.json"):
        import shutil
        shutil.copy("my_novel_project.json", default_path)
    else:
        proj = NovelProject(default_path)
        proj.save()

    set_active_project_filename(default_fn)
    return default_fn

def set_active_project_filename(filename):
    """Saves the active project filename to the config file."""
    with open(ACTIVE_CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(filename)

# Instantiate the active project
active_filename = get_active_project_filename()
project = NovelProject(os.path.join(PROJECTS_DIR, active_filename))

# Ensure the active project data has a default language setting if not present
if "lang" not in project.data["settings"]:
    project.data["settings"]["lang"] = "fr"

@app.route('/')
def index():
    """Renders the main single-page web interface."""
    return render_template('index.html')

@app.route('/api/project', methods=['GET'])
def get_project():
    """Returns the currently active project state."""
    global project
    project.recalculate_word_counts()
    return jsonify(project.data)

@app.route('/api/project', methods=['POST'])
def save_project():
    """Updates the active project state from client data and persists it to JSON."""
    global project
    client_data = request.json
    if not client_data:
        return jsonify({"error": "No data provided"}), 400

    project.data = client_data
    project.save()
    return jsonify({"status": "success", "data": project.data})

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """Lists all available projects in the projects/ directory with their titles."""
    projects_list = []
    files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith(".json")]
    for filename in files:
        filepath = os.path.join(PROJECTS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                title = data.get("settings", {}).get("title", filename)
                projects_list.append({"filename": filename, "title": title})
        except Exception as e:
            # Skip corrupted files
            continue
    return jsonify(projects_list)

@app.route('/api/projects/active', methods=['GET'])
def get_active_project():
    """Gets the active project's filename."""
    return jsonify({"active_filename": get_active_project_filename()})

@app.route('/api/projects/active', methods=['POST'])
def change_active_project():
    """Changes the active project to a different JSON file."""
    global project
    payload = request.json
    if not payload or "filename" not in payload:
        return jsonify({"error": "No filename specified"}), 400

    filename = payload["filename"]
    filepath = os.path.join(PROJECTS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Project file not found"}), 404

    set_active_project_filename(filename)
    project = NovelProject(filepath)
    return jsonify({"status": "success", "active_filename": filename, "data": project.data})

@app.route('/api/projects/create', methods=['POST'])
def create_project():
    """Creates a new project file and sets it as active."""
    global project
    payload = request.json
    if not payload or "title" not in payload:
        return jsonify({"error": "Title is required"}), 400

    title = payload["title"].strip()
    if not title:
        return jsonify({"error": "Title cannot be empty"}), 400

    # Generate safe filename
    safe_title = "".join([c for c in title if c.isalnum() or c in " _-"]).rstrip()
    safe_title = safe_title.replace(" ", "_").lower()
    if not safe_title:
        safe_title = "unnamed_project"

    filename = f"{safe_title}.json"
    filepath = os.path.join(PROJECTS_DIR, filename)

    # If filename already exists, append a unique count
    counter = 1
    while os.path.exists(filepath):
        filename = f"{safe_title}_{counter}.json"
        filepath = os.path.join(PROJECTS_DIR, filename)
        counter += 1

    # Initialize clean project state
    new_proj = NovelProject(filepath)
    new_proj.data = new_proj.get_default_data()
    new_proj.data["settings"]["title"] = title
    new_proj.data["settings"]["overall_written"] = 0
    new_proj.data["settings"]["daily_written"] = 0
    new_proj.data["manuscript"] = []
    new_proj.data["plot"]["cards"] = []
    new_proj.data["characters"] = []
    new_proj.data["story_notes"] = []
    new_proj.save()

    set_active_project_filename(filename)
    project = new_proj

    return jsonify({"status": "success", "filename": filename, "data": project.data})

@app.route('/api/locale/<lang>', methods=['GET'])
def get_locale(lang):
    """Loads and returns external translation files."""
    if lang not in ["en", "fr"]:
        lang = "en"

    locale_path = os.path.join("locales", f"{lang}.json")
    try:
        with open(locale_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        return jsonify(translations)
    except Exception as e:
        return jsonify({"error": f"Failed to load translations: {str(e)}"}), 500

@app.route('/api/export', methods=['POST'])
def export_draft():
    """Compiles the entire manuscript and exports it as a .txt file."""
    global project
    try:
        title = project.data["settings"].get("title", "My Novel")
        content_lines = [f"=== {title} ===\n\n"]

        for chap in project.data["manuscript"]:
            content_lines.append(f"\n--- {chap['title']} ---\n\n")
            for scene in chap.get("children", []):
                content_lines.append(f"[{scene['title']}]\n")
                content_lines.append(f"{scene.get('content', '')}\n\n")

        compiled_text = "".join(content_lines)

        # Temp file to send
        temp_file_path = "novel_export_temp.txt"
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(compiled_text)

        # Standard clean filename for downloading
        clean_filename = f"{title.replace(' ', '_')}_draft.txt"

        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=clean_filename,
            mimetype="text/plain"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to export: {str(e)}"}), 500

if __name__ == "__main__":
    # Start the local development web server on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
