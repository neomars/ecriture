import os
import json
from flask import Flask, jsonify, request, send_file, render_template
from project_manager import NovelProject
from ai_client import OllamaClient

def get_synonyms(word, lang="fr"):
    """Lookup other orthographic forms with same lemma inside lexique.db SQLite database."""
    if lang != "fr":
        return []

    db_path = "lexique.db"
    if not os.path.exists(db_path):
        return []

    w_clean = word.lower().strip(".,!?;:\"'()[]{}«»")
    if not w_clean:
        return []

    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get the lemma of the selected word
        cursor.execute("SELECT lemme FROM lexique WHERE ortho = ? LIMIT 1", (w_clean,))
        row = cursor.fetchone()
        if not row or not row[0]:
            conn.close()
            return []

        lemma = row[0]

        # Get other words sharing the same lemma
        cursor.execute(
            "SELECT DISTINCT ortho FROM lexique WHERE lemme = ? AND ortho != ? ORDER BY freqlemlivres DESC LIMIT 20",
            (lemma, w_clean)
        )
        syns = [r[0] for r in cursor.fetchall() if r[0]]
        conn.close()
        return syns
    except Exception as e:
        print("Error querying synonyms from lexique.db:", e)
        return []

app = Flask(__name__, template_folder='templates')
ai_client = OllamaClient()

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

    # Prioritize the Corneille "Le Cid" example as first-time default if it exists
    if os.path.exists(os.path.join(PROJECTS_DIR, "le_cid_corneille.json")):
        set_active_project_filename("le_cid_corneille.json")
        return "le_cid_corneille.json"

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

def get_scene_context(scene_id):
    """
    Gathers structured lore context about characters and notes associated with the active scene.
    A character is associated if linked via the checklist or via a plot card in this scene.
    A note is associated if its title is mentioned in the scene's title, content, or plot cards.
    """
    if not scene_id or not project or not project.data:
        return ""

    # 1. Collect associated character IDs
    char_ids = set()
    for char in project.data.get("characters", []):
        if scene_id in char.get("linked_scenes", []):
            char_ids.add(char["id"])

    # Plot cards for this scene
    for card in project.data.get("plot", {}).get("cards", []):
        if card.get("scene_id") == scene_id:
            for c_id in card.get("characters", []):
                char_ids.add(c_id)

    char_name_map = {c["id"]: c.get("name", "Inconnu") for c in project.data.get("characters", [])}

    char_lore_blocks = []
    for char in project.data.get("characters", []):
        if char["id"] in char_ids:
            name = char.get("name", "Inconnu")
            role = char.get("role", "")
            aliases = ", ".join(char.get("aliases", []))
            traits = ", ".join(char.get("traits", []))
            appearance = char.get("appearance", "")
            desc = char.get("description", "")
            notes = char.get("notes", "")

            rel_strs = []
            for rel in char.get("relations", []):
                target_id = rel.get("target_id")
                target_name = char_name_map.get(target_id, "Inconnu")
                rel_type = rel.get("type", "")
                rel_desc = rel.get("description", "")

                parts = []
                if rel_type:
                    parts.append(rel_type)
                if rel_desc:
                    parts.append(rel_desc)
                if parts:
                    rel_strs.append(f"- Relation avec {target_name} : {', '.join(parts)}")

            block = []
            block.append(f"Personnage : {name}")
            if role:
                block.append(f"  Rôle : {role}")
            if aliases:
                block.append(f"  Alias/Surnoms : {aliases}")
            if traits:
                block.append(f"  Traits de caractère : {traits}")
            if appearance:
                block.append(f"  Apparence physique : {appearance}")
            if desc:
                block.append(f"  Description : {desc}")
            if notes:
                block.append(f"  Notes : {notes}")
            if rel_strs:
                block.append("  Relations :\n" + "\n".join(rel_strs))

            char_lore_blocks.append("\n".join(block))

    # 2. Collect associated story notes by scanning scene content, title and plot cards
    scene_title = ""
    scene_content = ""

    def find_scene_text(nodes):
        for n in nodes:
            if n.get("id") == scene_id:
                return n.get("title", ""), n.get("content", "")
            if "children" in n:
                t, c = find_scene_text(n["children"])
                if t or c:
                    return t, c
        return "", ""

    scene_title, scene_content = find_scene_text(project.data.get("manuscript", []))
    combined_scene_text = f"{scene_title}\n{scene_content}".lower()

    for card in project.data.get("plot", {}).get("cards", []):
        if card.get("scene_id") == scene_id:
            combined_scene_text += f"\n{card.get('title', '')}\n{card.get('content', '')}".lower()

    note_lore_blocks = []
    for note in project.data.get("story_notes", []):
        note_title = note.get("title", "")
        if note_title and note_title.lower() in combined_scene_text:
            note_type = note.get("type", "")
            note_content = note.get("content", "")

            block = []
            block.append(f"Note : {note_title}")
            if note_type:
                block.append(f"  Type : {note_type}")
            if note_content:
                block.append(f"  Contenu : {note_content}")
            note_lore_blocks.append("\n".join(block))

    context_parts = []
    if char_lore_blocks:
        context_parts.append("=== LORE DES PERSONNAGES ASSOCIÉS À CETTE SCÈNE ===\n" + "\n\n".join(char_lore_blocks))
    if note_lore_blocks:
        context_parts.append("=== LORE DES NOTES ASSOCIÉES À CETTE SCÈNE ===\n" + "\n\n".join(note_lore_blocks))

    if context_parts:
        return "\n\n".join(context_parts)
    return ""

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

@app.route('/api/projects/delete', methods=['POST'])
def delete_project():
    """Deletes a project file securely."""
    global project
    payload = request.json or {}
    filename = payload.get("filename")
    if not filename:
        return jsonify({"error": "No filename specified"}), 400

    filepath = os.path.join(PROJECTS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Project file not found"}), 404

    try:
        os.remove(filepath)
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500

    # If we deleted the active project, find a new active project or create one
    active_fn = get_active_project_filename()
    if active_fn == filename or not os.path.exists(os.path.join(PROJECTS_DIR, active_fn)):
        if os.path.exists(ACTIVE_CONFIG_FILE):
            os.remove(ACTIVE_CONFIG_FILE)
        new_active = get_active_project_filename()
        project = NovelProject(os.path.join(PROJECTS_DIR, new_active))
        return jsonify({
            "status": "success",
            "switched": True,
            "active_filename": new_active,
            "data": project.data
        })

    return jsonify({
        "status": "success",
        "switched": False,
        "active_filename": active_fn
    })

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

@app.route('/api/synonyms', methods=['POST'])
def api_synonyms():
    """Returns a list of curated synonyms for a given word and language."""
    payload = request.get_json(silent=True) or {}
    word = payload.get("word", "").strip()
    lang = payload.get("lang", "fr").strip()

    if not word:
        return jsonify({"synonyms": []})

    syns = get_synonyms(word, lang)
    return jsonify({"synonyms": syns})

@app.route('/api/export', methods=['POST'])
def export_draft():
    """Compiles the entire manuscript and exports it in the chosen format."""
    global project
    try:
        payload = request.get_json(silent=True) or {}
        fmt = payload.get("format", "txt").lower().strip()

        title = project.data["settings"].get("title", "My Novel")
        safe_title = title.replace(' ', '_')

        # Compile clean manuscript text representation
        content_lines = [f"=== {title} ===\n\n"]
        for chap in project.data["manuscript"]:
            content_lines.append(f"\n--- {chap['title']} ---\n\n")
            for scene in chap.get("children", []):
                content_lines.append(f"[{scene['title']}]\n")
                content_lines.append(f"{scene.get('content', '')}\n\n")
        compiled_text = "".join(content_lines)

        if fmt == "txt":
            temp_file_path = "novel_export_temp.txt"
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(compiled_text)
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"{safe_title}_draft.txt",
                mimetype="text/plain"
            )

        elif fmt == "docx":
            import docx
            temp_file_path = "novel_export_temp.docx"
            doc = docx.Document()
            doc.add_heading(title, 0)

            for chap in project.data["manuscript"]:
                doc.add_heading(chap['title'], level=1)
                for scene in chap.get("children", []):
                    doc.add_heading(scene['title'], level=2)
                    doc.add_paragraph(scene.get('content', ''))

            doc.save(temp_file_path)
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"{safe_title}_draft.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        elif fmt == "pdf":
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

            temp_file_path = "novel_export_temp.pdf"
            doc = SimpleDocTemplate(temp_file_path, pagesize=letter)
            story = []

            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                alignment=TA_CENTER,
                fontSize=24,
                spaceAfter=20
            )
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 20))

            heading1_style = ParagraphStyle(
                'Heading1Style',
                parent=styles['Heading2'],
                fontSize=18,
                spaceBefore=15,
                spaceAfter=10
            )
            heading2_style = ParagraphStyle(
                'Heading2Style',
                parent=styles['Heading3'],
                fontSize=14,
                spaceBefore=10,
                spaceAfter=6
            )
            body_style = ParagraphStyle(
                'BodyStyle',
                parent=styles['BodyText'],
                fontSize=11,
                leading=14,
                alignment=TA_JUSTIFY,
                spaceAfter=10
            )

            for chap in project.data["manuscript"]:
                story.append(Paragraph(chap['title'], heading1_style))
                for scene in chap.get("children", []):
                    story.append(Paragraph(scene['title'], heading2_style))
                    content = scene.get('content', '').replace('\n', '<br/>')
                    story.append(Paragraph(content, body_style))
                    story.append(Spacer(1, 10))

            doc.build(story)
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"{safe_title}_draft.pdf",
                mimetype="application/pdf"
            )

        elif fmt == "odt":
            import zipfile
            import html
            temp_file_path = "novel_export_temp.odt"

            manifest_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">\n'
                ' <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.text"/>\n'
                ' <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>\n'
                ' <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>\n'
                ' <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>\n'
                '</manifest:manifest>\n'
            )

            meta_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" office:version="1.2">\n'
                ' <office:meta>\n'
                '  <meta:generator>Ecriture Novel Assistant</meta:generator>\n'
                f'  <meta:title>{html.escape(title)}</meta:title>\n'
                ' </office:meta>\n'
                '</office:document-meta>\n'
            )

            styles_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.2">\n'
                '</office:document-styles>\n'
            )

            body_xml_lines = []
            for chap in project.data["manuscript"]:
                body_xml_lines.append(f'<text:h text:outline-level="1">{html.escape(chap["title"])}</text:h>')
                for scene in chap.get("children", []):
                    body_xml_lines.append(f'<text:h text:outline-level="2">{html.escape(scene["title"])}</text:h>')
                    for para in scene.get("content", "").split("\n"):
                        if para.strip():
                            body_xml_lines.append(f'<text:p>{html.escape(para)}</text:p>')
            body_xml = "\n".join(body_xml_lines)

            content_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2">\n'
                ' <office:body>\n'
                '  <office:text>\n'
                f'   <text:h text:outline-level="1">{html.escape(title)}</text:h>\n'
                f'   {body_xml}\n'
                '  </office:text>\n'
                ' </office:body>\n'
                '</office:document-content>\n'
            )

            with zipfile.ZipFile(temp_file_path, 'w', zipfile.ZIP_DEFLATED) as o:
                o.writestr('mimetype', 'application/vnd.oasis.opendocument.text', compress_type=zipfile.ZIP_STORED)
                o.writestr('META-INF/manifest.xml', manifest_xml)
                o.writestr('meta.xml', meta_xml)
                o.writestr('styles.xml', styles_xml)
                o.writestr('content.xml', content_xml)

            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"{safe_title}_draft.odt",
                mimetype="application/vnd.oasis.opendocument.text"
            )

        elif fmt == "epub":
            import zipfile
            import html
            temp_file_path = "novel_export_temp.epub"

            container_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
                '  <rootfiles>\n'
                '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
                '  </rootfiles>\n'
                '</container>\n'
            )

            content_opf = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookID" version="2.0">\n'
                '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">\n'
                f'    <dc:title>{html.escape(title)}</dc:title>\n'
                '    <dc:language>fr</dc:language>\n'
                '    <dc:creator>Ecriture Novel Assistant</dc:creator>\n'
                '    <dc:identifier id="BookID">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>\n'
                '  </metadata>\n'
                '  <manifest>\n'
                '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
                '    <item id="text" href="text.html" media-type="application/xhtml+xml"/>\n'
                '  </manifest>\n'
                '  <spine toc="ncx">\n'
                '    <itemref idref="text"/>\n'
                '  </spine>\n'
                '</package>\n'
            )

            toc_ncx = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE ncx PUBLIC "-//NISO//DTD NCX 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n'
                '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
                '  <head>\n'
                '    <meta name="dtb:uid" content="urn:uuid:12345678-1234-1234-1234-123456789abc"/>\n'
                '    <meta name="dtb:depth" content="1"/>\n'
                '    <meta name="dtb:totalPageCount" content="0"/>\n'
                '    <meta name="dtb:maxPageNumber" content="0"/>\n'
                '  </head>\n'
                '  <docTitle>\n'
                f'    <text>{html.escape(title)}</text>\n'
                '  </docTitle>\n'
                '  <navMap>\n'
                '    <navPoint id="navPoint-1" playOrder="1">\n'
                '      <navLabel>\n'
                '        <text>Start</text>\n'
                '      </navLabel>\n'
                '      <content src="text.html"/>\n'
                '    </navPoint>\n'
                '  </navMap>\n'
                '</ncx>\n'
            )

            html_body_lines = []
            for chap in project.data["manuscript"]:
                html_body_lines.append(f'<h2>{html.escape(chap["title"])}</h2>')
                for scene in chap.get("children", []):
                    html_body_lines.append(f'<h3>{html.escape(scene["title"])}</h3>')
                    for para in scene.get("content", "").split("\n"):
                        if para.strip():
                            html_body_lines.append(f'<p>{html.escape(para)}</p>')
            html_body = "\n".join(html_body_lines)

            text_html = (
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
                '<html xmlns="http://www.w3.org/1999/xhtml">\n'
                '<head>\n'
                f'  <title>{html.escape(title)}</title>\n'
                '</head>\n'
                '<body>\n'
                f'  <h1>{html.escape(title)}</h1>\n'
                f'  {html_body}\n'
                '</body>\n'
                '</html>\n'
            )

            with zipfile.ZipFile(temp_file_path, 'w', zipfile.ZIP_DEFLATED) as o:
                o.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                o.writestr('META-INF/container.xml', container_xml)
                o.writestr('OEBPS/content.opf', content_opf)
                o.writestr('OEBPS/toc.ncx', toc_ncx)
                o.writestr('OEBPS/text.html', text_html)

            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"{safe_title}_draft.epub",
                mimetype="application/epub+zip"
            )

        elif fmt == "mobi":
            import struct
            temp_file_path = "novel_export_temp.mobi"

            title_bytes = title.encode('utf-8')[:31].ljust(32, b'\0')
            num_records = 3

            pdb_header = struct.pack(
                '>32sHHIIIIII4s4sIIH',
                title_bytes,
                0, # attributes
                0, # version
                0, 0, 0, 0, # dates
                0, # app info
                0, # sort info
                b'BOOK',
                b'MOBI',
                0, # unique id seed
                0, # next record
                num_records
            )

            text_bytes = compiled_text.encode('utf-8')
            text_len = len(text_bytes)

            # Rec0 is the PalmDOC/Mobi description header:
            # - compression: 1 (none)
            # - unused: 0
            # - text length
            # - record count: 1 (text records count)
            # - record size: 4096
            # - encryption: 0
            rec0 = struct.pack('>HHIIHH', 1, 0, text_len, num_records - 1, 4096, 0)
            rec1 = text_bytes
            rec2 = b'\xe9\x8e\r\n' # EOF

            offset0 = 78 + (num_records * 8) + 2
            offset1 = offset0 + len(rec0)
            offset2 = offset1 + len(rec1)

            rec_info = b''
            rec_info += struct.pack('>II', offset0, 0)
            rec_info += struct.pack('>II', offset1, 2)
            rec_info += struct.pack('>II', offset2, 4)

            mobi_bytes = pdb_header + rec_info + b'\0\0' + rec0 + rec1 + rec2

            with open(temp_file_path, 'wb') as f:
                f.write(mobi_bytes)

            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"{safe_title}_draft.mobi",
                mimetype="application/x-mobipocket-ebook"
            )

        else:
            return jsonify({"error": f"Unsupported format: {fmt}"}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to export: {str(e)}"}), 500

@app.route('/api/ai', methods=['POST'])
def handle_ai_tool():
    """Handles contextual AI writing tools: Describe, Rewrite, and Expand."""
    from ai_prompts import DESCRIBE_PROMPT, REWRITE_PROMPT, EXPAND_PROMPT

    payload = request.json or {}
    tool = payload.get("tool", "describe").lower().strip()
    style = payload.get("style", "elegant").lower().strip()
    text = payload.get("text", "").strip()
    inject_lore = payload.get("inject_lore_context", True)
    scene_id = payload.get("scene_id")

    if not text:
        return jsonify({"error": "No text selected"}), 400

    # Match the appropriate system prompt
    if tool == "describe":
        system_prompt = DESCRIBE_PROMPT
    elif tool == "rewrite":
        system_prompt = REWRITE_PROMPT.format(style=style)
    elif tool == "expand":
        system_prompt = EXPAND_PROMPT
    else:
        return jsonify({"error": f"Unknown tool: {tool}"}), 400

    # Prepend Lore context to the system prompt if enabled and context is found
    if inject_lore and scene_id:
        lore_ctx = get_scene_context(scene_id)
        if lore_ctx:
            system_prompt = (
                f"{lore_ctx}\n\n"
                "Consignes de l'assistant :\n"
                f"{system_prompt}"
            )

    # Build chat messages payload
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]

    selected_model = payload.get("model", "llama3").strip()
    temperature = payload.get("temperature", 0.7)

    # Call Ollama via unified Client
    try:
        res = ai_client.chat(messages, model=selected_model, temperature=temperature, timeout=15)
        return jsonify({
            "status": "success",
            "message": res["message"],
            "model": res["model"]
        })
    except Exception:
        # Fallback using unified client fallbacks
        lang = "fr" if any(word in text.lower() for word in ["le", "la", "les", "une", "un", "est", "et", "de", "je", "tu", "il"]) else "en"
        simulated_output = ai_client.get_fallback_response(tool, text, style=style, lang=lang)
        return jsonify({
            "status": "offline_fallback",
            "message": simulated_output,
            "model": "Simulation"
        })

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Proxy or fallback endpoint for a local Ollama AI assistant."""
    payload = request.json or {}
    messages = payload.get("messages", [])
    selected_model = payload.get("model", "llama3").strip()
    temperature = payload.get("temperature", 0.7)
    inject_lore = payload.get("inject_lore_context", True)
    scene_id = payload.get("scene_id")

    # Prepend system message with lore context if enabled and context is found
    if inject_lore and scene_id:
        lore_ctx = get_scene_context(scene_id)
        if lore_ctx:
            system_msg = f"Voici des informations sur le contexte et le Lore de la scène en cours. Intègre et respecte ces éléments si nécessaire dans vos réponses :\n\n{lore_ctx}"
            # Insert at the beginning or as a system prompt
            messages.insert(0, {"role": "system", "content": system_msg})

    # Call Ollama via unified client
    try:
        res = ai_client.chat(messages, model=selected_model, temperature=temperature, timeout=15)
        return jsonify({
            "status": "success",
            "message": res["message"],
            "model": res["model"]
        })
    except Exception:
        # Graceful fallback simulation
        simulation = ai_client.get_fallback_response("chat", messages)
        return jsonify({
            "status": "offline_fallback",
            "message": simulation,
            "model": "Simulation"
        })

@app.route('/api/ai/models', methods=['GET'])
def get_ollama_models():
    """Queries the local Ollama API to fetch installed models."""
    models = ai_client.get_available_models()
    if models:
        return jsonify({
            "status": "success",
            "models": models
        })
    else:
        return jsonify({
            "status": "offline",
            "models": []
        })

@app.route('/api/relecture/ai', methods=['POST'])
def api_relecture_ai():
    """AI relecture assistance: Style & Prose or Cohérence."""
    payload = request.json or {}
    category = payload.get("category", "style").lower().strip()
    text = payload.get("text", "").strip()
    selected_model = payload.get("model", "llama3").strip()
    temperature = payload.get("temperature", 0.7)
    lang = payload.get("lang", "fr").strip()

    if not text:
        return jsonify({"feedback": "Texte vide" if lang == "fr" else "Empty text", "status": "empty"})

    # Formulate prompt based on category and language
    if category == "style":
        if lang == "fr":
            system_prompt = (
                "Tu es un relecteur professionnel de romans et correcteur littéraire de style et prose.\n"
                "Analyse le texte suivant et donne des retours constructifs détaillés.\n"
                "Suggère des améliorations précises de vocabulaire, de rythme des phrases, de style, "
                "de fluidité et des reformulations d'échantillons de texte s'il y a lieu.\n"
                "Réponds en français."
            )
        else:
            system_prompt = (
                "You are a professional novel proofreader and copyeditor of style and prose.\n"
                "Analyze the following text and provide detailed constructive feedback.\n"
                "Suggest precise improvements for vocabulary, sentence pacing, style, "
                "flow, and sample rewrites where applicable.\n"
                "Respond in English."
            )
    else: # coherence
        if lang == "fr":
            system_prompt = (
                "Tu es un relecteur professionnel de romans et conseiller en cohérence narrative.\n"
                "Analyse le texte suivant pour en évaluer la cohérence logique, les motivations et actions des personnages, "
                "la pertinence temporelle et spatiale, et signale toute anomalie ou incohérence flagrante.\n"
                "Réponds en français."
            )
        else:
            system_prompt = (
                "You are a professional novel proofreader and narrative coherence consultant.\n"
                "Analyze the following text to evaluate logical consistency, character motivations and actions, "
                "temporal and spatial sense, and flag any logical fallacies or glaring inconsistencies.\n"
                "Respond in English."
            )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]

    # Call Ollama via unified client
    try:
        res = ai_client.chat(messages, model=selected_model, temperature=temperature, timeout=25)
        return jsonify({
            "status": "success",
            "feedback": res["message"],
            "model": res["model"]
        })
    except Exception:
        # Fallback using unified client fallbacks
        simulated_feedback = ai_client.get_fallback_response(f"relecture_{category}", text, lang=lang)
        return jsonify({
            "status": "offline_fallback",
            "feedback": simulated_feedback,
            "model": "Simulation"
        })

if __name__ == "__main__":
    # Start the local development web server on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
