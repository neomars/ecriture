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
    import urllib.request
    import urllib.error
    from ai_prompts import DESCRIBE_PROMPT, REWRITE_PROMPT, EXPAND_PROMPT

    payload = request.json or {}
    tool = payload.get("tool", "describe").lower().strip()
    style = payload.get("style", "elegant").lower().strip()
    text = payload.get("text", "").strip()

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

    # Build chat messages payload
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]

    ollama_url = "http://localhost:11434"
    selected_model = payload.get("model", "llama3").strip()
    temperature = payload.get("temperature", 0.7)

    # 1. Try to verify/find an active model on Ollama
    try:
        req_tags = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        with urllib.request.urlopen(req_tags, timeout=2) as response:
            tags_data = json.loads(response.read().decode('utf-8'))
            models = tags_data.get("models", [])
            if models:
                available_names = [m["name"] for m in models]
                if selected_model not in available_names and f"{selected_model}:latest" not in available_names:
                    selected_model = models[0]["name"]
    except Exception:
        pass

    # 2. Call Ollama
    try:
        chat_payload = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        req_chat = urllib.request.Request(
            f"{ollama_url}/api/chat",
            data=json.dumps(chat_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req_chat, timeout=15) as response:
            chat_response = json.loads(response.read().decode('utf-8'))
            assistant_message = chat_response.get("message", {}).get("content", "").strip()
            return jsonify({
                "status": "success",
                "message": assistant_message,
                "model": selected_model
            })
    except Exception:
        # Fallback interactive simulation based on the tool
        is_french = any(word in text.lower() for word in ["le", "la", "les", "une", "un", "est", "et", "de", "je", "tu", "il"])

        if tool == "describe":
            if is_french:
                simulated_output = f"Une description riche et sensorielle de « {text} » : Des nuances subtiles se détachent, capturant la lumière changeante avec une précision artistique, éveillant un sentiment profond d'émerveillement et de mystère."
            else:
                simulated_output = f"A rich and sensory description of '{text}': Subtle textures and fine details catch the ambient light, casting delicate shadows that evoke a deep sense of atmospheric presence and quiet contemplation."
        elif tool == "rewrite":
            if is_french:
                style_fr = {
                    "elegant": f"Version élégante de « {text} » : Une formulation raffinée, drapée de tournures mélodieuses et d'un vocabulaire choisi avec le plus grand soin.",
                    "dramatic": f"Version dramatique de « {text} » : Soudain, l'air devint lourd de menaces. Chaque mot résonnait comme un coup de tonnerre sur le point d'éclater, scellant à jamais leur destin tragique.",
                    "poetic": f"Version poétique de « {text} » : Comme un murmure d'étoiles filantes glissant sur le velours de la nuit, les mots dansent et s'envolent au gré des songes.",
                    "humorous": f"Version humoristique de « {text} » : Bon, d'accord, « {text} »... Mais en plus rigolo, avec un zeste d'ironie et deux cuillères à soupe d'auto-dérision !",
                    "action": f"Version action de « {text} » : Impact immédiat. Le souffle court. Pas un instant à perdre. Tout s'accélère à un rythme effréné !"
                }
                simulated_output = style_fr.get(style, style_fr["elegant"])
            else:
                style_en = {
                    "elegant": f"Elegant version of '{text}': A polished expression, woven with sophisticated syntax and literary precision.",
                    "dramatic": f"Dramatic version of '{text}': Suddenly, a suffocating tension filled the room, matching the perilous stakes of this critical hour.",
                    "poetic": f"Poetic version of '{text}': Like starlight kissing the dark surface of a sleeping lake, the words shimmer with ethereal grace.",
                    "humorous": f"Humorous version of '{text}': Well, let's add a playful twist to '{text}'—with a dash of wit and a side of healthy sarcasm!",
                    "action": f"Action version of '{text}': High-octane response. Heart pounding. Every second counted. Move or die!"
                }
                simulated_output = style_en.get(style, style_en["elegant"])
        else:  # expand
            if is_french:
                simulated_output = f"« {text} » de manière plus développée : Nous pouvons explorer l'arrière-plan avec soin, en ajoutant des détails descriptifs substantiels, en ralentissant le rythme et en enrichissant les émotions intérieures des personnages présents."
            else:
                simulated_output = f"Expanded version of '{text}': Elaborating further on this moment, we unfold layers of quiet thoughts and sensory nuances, breathing full dimension into the atmosphere and pacing of the narrative."

        return jsonify({
            "status": "offline_fallback",
            "message": simulated_output,
            "model": "Simulation"
        })

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Proxy or fallback endpoint for a local Ollama AI assistant."""
    import urllib.request
    import urllib.error

    payload = request.json or {}
    messages = payload.get("messages", [])
    selected_model = payload.get("model", "llama3").strip()
    temperature = payload.get("temperature", 0.7)

    # 1. Check if Ollama is reachable and find any installed models
    ollama_url = "http://localhost:11434"

    try:
        # Check available tags/models to auto-select if user did not specify/fallback
        req_tags = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        with urllib.request.urlopen(req_tags, timeout=2) as response:
            tags_data = json.loads(response.read().decode('utf-8'))
            models = tags_data.get("models", [])
            if models:
                available_names = [m["name"] for m in models]
                if selected_model not in available_names and f"{selected_model}:latest" not in available_names:
                    selected_model = models[0]["name"]
    except Exception:
        # If we can't reach Ollama, trigger fallback/simulation mode
        pass

    # 2. Try querying Ollama chat endpoint
    try:
        chat_payload = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        req_chat = urllib.request.Request(
            f"{ollama_url}/api/chat",
            data=json.dumps(chat_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req_chat, timeout=15) as response:
            chat_response = json.loads(response.read().decode('utf-8'))
            assistant_message = chat_response.get("message", {}).get("content", "")
            return jsonify({
                "status": "success",
                "message": assistant_message,
                "model": selected_model
            })
    except Exception as e:
        # Graceful fallback simulation
        user_text = ""
        if messages:
            user_text = messages[-1].get("content", "").lower()

        # Build simulated responses based on keywords
        if any(kw in user_text for kw in ["plan", "intrigue", "plot"]):
            simulation = (
                "[Assistant IA (Ollama Simulation - Hors ligne)]\n"
                "Pour structurer votre intrigue, je vous suggère de suivre le schéma narratif :\n"
                "1. Situation initiale : Présentation du protagoniste et du cadre.\n"
                "2. Élément déclencheur : Un bouleversement majeur.\n"
                "3. Péripéties : Obstacles et évolution des personnages.\n"
                "4. Climax : Le point de tension maximale.\n"
                "5. Dénouement : Résolution de l'intrigue."
            )
        elif any(kw in user_text for kw in ["personnage", "character", "heros", "héro"]):
            simulation = (
                "[Assistant IA (Ollama Simulation - Hors ligne)]\n"
                "Voici quelques idées pour approfondir un personnage :\n"
                "- Quel est son plus grand secret ?\n"
                "- Quelle est sa motivation principale (désir profond vs. besoin inconscient) ?\n"
                "- Ajoutez un défaut physique ou une habitude unique pour le rendre mémorable."
            )
        else:
            simulation = (
                "[Assistant IA (Ollama Simulation - Hors ligne)]\n"
                "Bonjour ! Je suis votre assistant d'écriture Écriture.\n"
                "Ollama semble être hors ligne sur http://localhost:11434.\n"
                "Voici une suggestion pour continuer : déterminez l'enjeu principal de votre scène actuelle !"
            )

        return jsonify({
            "status": "offline_fallback",
            "message": simulation,
            "model": "Simulation"
        })

if __name__ == "__main__":
    # Start the local development web server on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
