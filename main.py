import os
import json
from flask import Flask, jsonify, request, send_file, render_template
from project_manager import NovelProject

app = Flask(__name__, template_folder='templates')

# Load the core project file
PROJECT_FILE = "my_novel_project.json"
project = NovelProject(PROJECT_FILE)

# Ensure the project data has a default language setting if not present
if "lang" not in project.data["settings"]:
    project.data["settings"]["lang"] = "fr"  # Default to French as requested

@app.route('/')
def index():
    """Renders the main single-page web interface."""
    return render_template('index.html')

@app.route('/api/project', methods=['GET'])
def get_project():
    """Returns the full project state."""
    # Ensure recalculation is up to date
    project.recalculate_word_counts()
    return jsonify(project.data)

@app.route('/api/project', methods=['POST'])
def save_project():
    """Updates the project state from client data and persists it to JSON."""
    client_data = request.json
    if not client_data:
        return jsonify({"error": "No data provided"}), 400

    project.data = client_data
    project.save()
    return jsonify({"status": "success", "data": project.data})

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
