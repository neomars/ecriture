        // Textarea caret position locator utility
        const properties = [
            'direction', 'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
            'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth', 'borderStyle',
            'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
            'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize',
            'fontSizeAdjust', 'lineHeight', 'fontFamily', 'textAlign', 'textTransform',
            'textIndent', 'textDecoration', 'letterSpacing', 'wordSpacing', 'tabSize', 'MozTabSize'
        ];
        const isFirefox = (typeof window !== 'undefined' && window.mozInnerScreenX != null);

        function getCaretCoordinates(element, position) {
            const div = document.createElement('div');
            div.id = 'input-textarea-caret-position-mirror-div';
            document.body.appendChild(div);

            const style = div.style;
            const computed = window.getComputedStyle(element);

            style.whiteSpace = 'pre-wrap';
            style.wordWrap = 'break-word';
            style.position = 'absolute';
            style.visibility = 'hidden';

            properties.forEach(prop => {
                style[prop] = computed[prop];
            });

            if (isFirefox) {
                if (element.scrollHeight > parseInt(computed.height)) {
                    style.overflowY = 'scroll';
                }
            } else {
                style.overflow = 'hidden';
            }

            div.textContent = element.value.substring(0, position);

            const span = document.createElement('span');
            span.textContent = element.value.substring(position) || '.';
            div.appendChild(span);

            const coordinates = {
                top: span.offsetTop + parseInt(computed['borderTopWidth']),
                left: span.offsetLeft + parseInt(computed['borderLeftWidth']),
                height: parseInt(computed['lineHeight'])
            };

            document.body.removeChild(div);
            return coordinates;
        }

        // Core application data state
        let projectData = null;
        let translations = {};
        let activeLang = "fr";

        let activeNodeId = null;     // ID of current active workspace item (scene/chap/char/note)
        let activeNodeType = null;   // "scene", "chapter", "character", "note", or "plot_grid"
        let activePlotSubView = "grid"; // Sub-view for plotting: "grid" or "timeline"

        // Auto-save debounce timer
        let autoSaveTimer = null;

        // Drag and drop state for chapters
        let draggedChapId = null;

        // Pomodoro Focus Timer variables
        let timerDurationMinutes = 15;
        let timerSecondsLeft = 15 * 60;
        let timerIntervalId = null;
        let timerIsRunning = false;

        // Initialize application
        window.addEventListener('DOMContentLoaded', async () => {
            // Close resource quick menu if clicked outside
            document.addEventListener('click', (e) => {
                const dropdown = document.getElementById('asset-menu-dropdown');
                if (dropdown && !e.target.closest('.relative')) {
                    dropdown.classList.add('hidden');
                }
                const exportMenu = document.getElementById('export-dropdown-menu');
                if (exportMenu && !e.target.closest('#export-dropdown-wrapper')) {
                    exportMenu.classList.add('hidden');
                }

                const rewriteMenu = document.getElementById('ai-rewrite-dropdown-menu');
                if (rewriteMenu && !e.target.closest('#ai-rewrite-dropdown-wrapper')) {
                    rewriteMenu.classList.add('hidden');
                }

                const synonymsMenu = document.getElementById('synonyms-dropdown-menu');
                if (synonymsMenu && !e.target.closest('#synonyms-dropdown-wrapper')) {
                    synonymsMenu.classList.add('hidden');
                }

                // Hide selection menu if clicked outside selection and selection menu
                const selectionMenu = document.getElementById('ai-selection-menu');
                if (selectionMenu && !e.target.closest('#ai-selection-menu') && !e.target.closest('#editor-content')) {
                    selectionMenu.classList.add('hidden');
                    if (rewriteMenu) rewriteMenu.classList.add('hidden');
                    if (synonymsMenu) synonymsMenu.classList.add('hidden');
                }
            });

            // Listen for text selection inside the editor using delegation to survive dynamic editor recreations
            document.addEventListener('mouseup', function(e) {
                const editor = document.getElementById('editor-content');
                if (editor && e.target === editor) {
                    handleTextSelection(e);
                }
            });
            document.addEventListener('keyup', function(e) {
                const editor = document.getElementById('editor-content');
                if (editor && e.target === editor) {
                    handleTextSelection(e);
                }
            });

            // Initialize AI option from localStorage
            const storedAiVal = localStorage.getItem('ai-enabled');
            const aiEnabled = (storedAiVal !== 'false'); // defaults to true
            const aiCheckbox = document.getElementById('ai-toggle-checkbox');
            if (aiCheckbox) {
                aiCheckbox.checked = aiEnabled;
            }
            toggleAiOption(aiEnabled);

            await loadProjectsList();
            await loadProject();
        });

        // LOAD PROJECTS LIST FOR DROPDOWN
        async function loadProjectsList() {
            try {
                const res = await fetch('/api/projects');
                const projects = await res.json();

                const select = document.getElementById('project-select');
                select.innerHTML = "";

                projects.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.filename;
                    opt.innerText = p.title;
                    select.appendChild(opt);
                });

                // Get active project filename
                const activeRes = await fetch('/api/projects/active');
                const activeData = await activeRes.json();
                select.value = activeData.active_filename;
            } catch (err) {
                console.error("Error loading projects list:", err);
            }
        }

        // SWITCH CURRENT ACTIVE NOVEL
        async function switchProject(filename) {
            try {
                // Save current project state first
                if (projectData) {
                    await persistProject();
                }

                const res = await fetch('/api/projects/active', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename })
                });

                if (res.ok) {
                    activeNodeId = null;
                    activeNodeType = null;
                    await loadProjectsList();
                    await loadProject();
                }
            } catch (err) {
                console.error("Failed to switch project:", err);
            }
        }

        // OPEN / CLOSE NEW PROJECT MODAL
        function openNewProjectModal() {
            document.getElementById('new-project-title-input').value = "";
            document.getElementById('new-project-modal').classList.remove('hidden');
        }

        function closeNewProjectModal() {
            document.getElementById('new-project-modal').classList.add('hidden');
        }

        // CREATE NEW NOVEL PROJECT
        async function createNewProject() {
            const title = document.getElementById('new-project-title-input').value.trim();
            if (!title) {
                alert("Please enter a title.");
                return;
            }

            try {
                // Save current first
                if (projectData) {
                    await persistProject();
                }

                const res = await fetch('/api/projects/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title })
                });

                if (res.ok) {
                    closeNewProjectModal();
                    activeNodeId = null;
                    activeNodeType = null;
                    await loadProjectsList();
                    await loadProject();
                }
            } catch (err) {
                console.error("Failed to create new project:", err);
            }
        }

        // ENFORCE LOCK STATE IN FRONTEND
        function applyLockState() {
            const isLocked = !!(projectData && projectData.settings && projectData.settings.locked);

            // Disable editing inputs
            const editorTitle = document.getElementById('editor-title');
            if (editorTitle) editorTitle.disabled = isLocked;

            const editorContent = document.getElementById('editor-content');
            if (editorContent) {
                editorContent.disabled = isLocked;
                if (isLocked) {
                    editorContent.classList.add('bg-slate-50/30', 'cursor-not-allowed');
                    editorContent.setAttribute('placeholder', translations["locked_warning"] || "Ce roman est verrouillé.");
                } else {
                    editorContent.classList.remove('bg-slate-50/30', 'cursor-not-allowed');
                    editorContent.setAttribute('placeholder', translations["editor_placeholder"] || "Commencez à rédiger votre chef-d'œuvre ici...");
                }
            }

            const resourceTitle = document.getElementById('resource-title');
            if (resourceTitle) resourceTitle.disabled = isLocked;

            const charRole = document.getElementById('char-role');
            if (charRole) charRole.disabled = isLocked;

            const charDesc = document.getElementById('char-desc');
            if (charDesc) charDesc.disabled = isLocked;

            const noteType = document.getElementById('note-type');
            if (noteType) noteType.disabled = isLocked;

            const noteContent = document.getElementById('note-content');
            if (noteContent) noteContent.disabled = isLocked;

            const dailyGoalInput = document.getElementById('daily-goal-input');
            if (dailyGoalInput) dailyGoalInput.disabled = isLocked;

            // Hide or disable sidebar additions
            const addChapterBtn = document.querySelector('[onclick="addNewChapter()"]');
            if (addChapterBtn) addChapterBtn.style.display = isLocked ? 'none' : 'block';

            const addSceneBtn = document.querySelector('[onclick="addNewScene()"]');
            if (addSceneBtn) addSceneBtn.style.display = isLocked ? 'none' : 'block';

            const showAssetMenuBtn = document.querySelector('[onclick="showAssetMenu(); event.stopPropagation();"]');
            if (showAssetMenuBtn) {
                const parentDiv = showAssetMenuBtn.parentElement;
                if (parentDiv) parentDiv.style.display = isLocked ? 'none' : 'block';
            }

            // Adjust quick actions footer visibility
            const quickActionsFooter = document.querySelector('.grid-cols-3');
            if (quickActionsFooter) {
                if (isLocked) {
                    quickActionsFooter.classList.add('hidden');
                } else {
                    quickActionsFooter.classList.remove('hidden');
                }
            }
        }

        // APPLY USER-DEFINED LAYOUT AND TYPOGRAPHY SETTINGS TO THE EDITOR
        function applyEditorLayoutSettings() {
            if (!projectData || !projectData.settings) return;
            if (!projectData.settings.editor_layout) {
                // Set defaults: Georgia 12pt, 1.6 spacing, left alignment
                projectData.settings.editor_layout = {
                    font_family: "Georgia, serif",
                    font_size: "12pt",
                    line_spacing: "1.6",
                    text_align: "left"
                };
            }

            const layout = projectData.settings.editor_layout;
            const editor = document.getElementById('editor-content');
            if (editor) {
                editor.style.fontFamily = layout.font_family || "Georgia, serif";
                editor.style.fontSize = layout.font_size || "12pt";
                editor.style.lineHeight = layout.line_spacing || "1.6";
                editor.style.textAlign = layout.text_align || "left";

                // Also adjust paragraph separation spacing inside textarea
                editor.style.paddingAfter = "6px";
            }
        }

        // LOAD ACTIVE PROJECT FROM BACKEND JSON
        async function loadProject() {
            try {
                const res = await fetch('/api/project');
                projectData = await res.json();

                // Normalize all characters to ensure backward compatibility
                if (projectData && projectData.characters) {
                    projectData.characters.forEach(c => ensureCharacterFields(c));
                }

                // Read language preference
                activeLang = projectData.settings.lang || "fr";
                document.getElementById('lang-select').value = activeLang;

                // Load appropriate language translation file
                await loadLocale(activeLang);

                // Build navigation pane
                renderTree();

                // Apply layout configuration to the text canvas
                applyEditorLayoutSettings();

                // Update settings modals and right sidebar progress goals
                updateRightSidebar();

                // Load first scene into editor if none selected
                if (!activeNodeId) {
                    loadFirstAvailableScene();
                } else {
                    refreshActiveWorkspace();
                }

                // Apply locking restrictions frontend
                applyLockState();

            } catch (err) {
                console.error("Error loading project state:", err);
            }
        }

        // FETCH EXTERNAL LOCALIZATION
        async function loadLocale(lang) {
            try {
                const res = await fetch(`/api/locale/${lang}`);
                translations = await res.json();
                activeLang = lang;
                translateDOM();
            } catch (err) {
                console.error("Could not load locale:", err);
            }
        }

        // TRANSLATE DOM ELEMENTS USING TRANSLATIONS MAP
        function translateDOM() {
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[key]) {
                    el.innerHTML = translations[key];
                }
            });

            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                const key = el.getAttribute('data-i18n-placeholder');
                if (translations[key]) {
                    el.setAttribute('placeholder', translations[key]);
                }
            });

            if (typeof updateChatWelcomeMessage === "function") {
                updateChatWelcomeMessage();
            }
        }

        // HELPER: Format strings with curly braces (e.g., "Written: {written} / {goal}")
        function formatTranslation(key, params = {}) {
            let val = translations[key] || "";
            for (const [k, v] of Object.entries(params)) {
                val = val.replace(`{${k}}`, v);
            }
            return val;
        }

        // SAVE STATE BACK TO JSON FILE
        async function persistProject() {
            try {
                const res = await fetch('/api/project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(projectData)
                });
                const result = await res.json();
                projectData = result.data;
                updateRightSidebar();
            } catch (err) {
                console.error("Failed to save project data:", err);
            }
        }

        // DEBOUNCED AUTOMATED SAVING
        function triggerAutoSave() {
            if (autoSaveTimer) clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(() => {
                persistProject();
            }, 800); // 800ms quiet period before saving
        }

        // DYNAMIC TREE VIEW RENDER
        function renderTree(filterText = "") {
            const searchVal = filterText.toLowerCase().trim();
            const isLocked = !!(projectData && projectData.settings && projectData.settings.locked);

            // Project title in Left Sidebar
            const lockIndicator = isLocked ? " 🔒" : "";
            document.getElementById('project-title-display').innerText = ((projectData && projectData.settings && projectData.settings.title) || "") + lockIndicator;

            // 1. Render Manuscript (Chapters & Scenes)
            const msList = document.getElementById('manuscript-nodes-list');
            msList.innerHTML = "";

            if (projectData && projectData.manuscript) {
                projectData.manuscript.forEach(chap => {
                    const chapTitle = chap.title || "";
                    const matchesChap = chapTitle.toLowerCase().includes(searchVal);

                    // Gather matching scenes
                    const childrenList = chap.children || [];
                    const matchingScenes = childrenList.filter(scene => {
                        const sceneTitle = scene.title || "";
                        const sceneContent = scene.content || "";
                        return sceneTitle.toLowerCase().includes(searchVal) ||
                               sceneContent.toLowerCase().includes(searchVal);
                    });

                    if (searchVal && !matchesChap && matchingScenes.length === 0) {
                        return; // Skip since it doesn't match query
                    }

                    // Create Chapter node element
                    const chapEl = document.createElement('div');
                    chapEl.className = "group transition-all duration-150 border-t-2 border-b-2 border-transparent";
                    if (!isLocked) {
                        chapEl.draggable = true;
                        chapEl.setAttribute('data-chap-id', chap.id);
                        chapEl.addEventListener('dragstart', handleChapDragStart);
                        chapEl.addEventListener('dragover', handleChapDragOver);
                        chapEl.addEventListener('dragleave', handleChapDragLeave);
                        chapEl.addEventListener('drop', handleChapDrop);
                        chapEl.addEventListener('dragend', handleChapDragEnd);
                    }

                    const isChapActive = (activeNodeId === chap.id);
                    const chapButtons = isLocked ? "" : `
                        <div class="opacity-0 group-hover:opacity-100 flex items-center space-x-1 shrink-0">
                            <button onclick="event.stopPropagation(); renameItem('${chap.id}', 'chapter')" class="hover:text-indigo-600 p-0.5 text-xs">✏️</button>
                            <button onclick="event.stopPropagation(); deleteItem('${chap.id}', 'chapter')" class="hover:text-red-600 p-0.5 text-xs">🗑️</button>
                        </div>
                    `;

                    chapEl.innerHTML = `
                        <div class="flex items-center justify-between px-2 py-1 rounded-lg text-sm font-semibold ${isChapActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-200/50'} cursor-pointer select-none">
                            <div class="flex items-center space-x-1.5 flex-1 min-w-0" onclick="selectChapter('${chap.id}')">
                                <span>📁</span>
                                <span class="truncate">${chapTitle}</span>
                            </div>
                            ${chapButtons}
                        </div>
                        <div class="pl-4 mt-0.5 space-y-0.5">
                            ${(searchVal ? matchingScenes : childrenList).map(scene => {
                                const isSceneActive = (activeNodeId === scene.id);
                                const sceneTitle = scene.title || "";
                                const sceneButtons = isLocked ? "" : `
                                        <div class="opacity-0 group-hover/scene:opacity-100 flex items-center space-x-1 shrink-0">
                                            <button onclick="event.stopPropagation(); renameItem('${scene.id}', 'scene')" class="hover:text-indigo-600 p-0.5">✏️</button>
                                            <button onclick="event.stopPropagation(); deleteItem('${scene.id}', 'scene')" class="hover:text-red-600 p-0.5">🗑️</button>
                                        </div>
                                `;
                                return `
                                    <div class="group/scene flex items-center justify-between px-2 py-1 rounded-lg text-xs font-medium ${isSceneActive ? 'bg-indigo-100 text-indigo-800 font-bold' : 'text-slate-500 hover:bg-slate-200/50'} cursor-pointer">
                                        <div class="flex items-center space-x-1.5 flex-1 min-w-0" onclick="selectScene('${scene.id}')">
                                            <span>📄</span>
                                            <span class="truncate">${sceneTitle}</span>
                                        </div>
                                        ${sceneButtons}
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    `;
                    msList.appendChild(chapEl);
                });
            }

            // Highlight active state on Plot Grid menu button
            const plotGridBtn = document.getElementById('plot-grid-menu-item');
            if (activeNodeType === "plot_grid") {
                plotGridBtn.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-bold bg-indigo-50 text-indigo-700 cursor-pointer transition-all";
            } else {
                plotGridBtn.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-200 hover:text-slate-900 cursor-pointer transition-all";
            }

            // 2. Render Characters
            const charList = document.getElementById('characters-list');
            charList.innerHTML = "";
            if (projectData && projectData.characters) {
                projectData.characters.forEach(char => {
                    const charName = char.name || "";
                    const charRole = char.role || "";
                    if (searchVal && !charName.toLowerCase().includes(searchVal) && !charRole.toLowerCase().includes(searchVal)) {
                        return;
                    }
                    const isCharActive = (activeNodeId === char.id);
                    const charEl = document.createElement('div');
                    charEl.className = "group/char flex items-center justify-between px-2.5 py-1 rounded-lg text-sm font-medium " +
                                      (isCharActive ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-200/50') +
                                      " cursor-pointer";
                    const charButtons = isLocked ? "" : `
                        <div class="opacity-0 group-hover/char:opacity-100 flex items-center space-x-1 shrink-0">
                            <button onclick="event.stopPropagation(); renameItem('${char.id}', 'character')" class="hover:text-indigo-600 p-0.5 text-xs">✏️</button>
                            <button onclick="event.stopPropagation(); deleteItem('${char.id}', 'character')" class="hover:text-red-600 p-0.5 text-xs">🗑️</button>
                        </div>
                    `;
                    charEl.innerHTML = `
                        <div class="flex items-center space-x-1.5 flex-1 min-w-0" onclick="selectCharacter('${char.id}')">
                            <span>👤</span>
                            <span class="truncate">${charName}</span>
                        </div>
                        ${charButtons}
                    `;
                    charList.appendChild(charEl);
                });
            }

            // 3. Render Story Notes
            const noteList = document.getElementById('notes-list');
            noteList.innerHTML = "";
            if (projectData && projectData.story_notes) {
                projectData.story_notes.forEach(note => {
                    const noteTitle = note.title || "";
                    const noteContent = note.content || "";
                    if (searchVal && !noteTitle.toLowerCase().includes(searchVal) && !noteContent.toLowerCase().includes(searchVal)) {
                        return;
                    }
                    const isNoteActive = (activeNodeId === note.id);
                    const noteEl = document.createElement('div');
                    noteEl.className = "group/note flex items-center justify-between px-2.5 py-1 rounded-lg text-sm font-medium " +
                                      (isNoteActive ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-200/50') +
                                      " cursor-pointer";
                    const noteButtons = isLocked ? "" : `
                        <div class="opacity-0 group-hover/note:opacity-100 flex items-center space-x-1 shrink-0">
                            <button onclick="event.stopPropagation(); renameItem('${note.id}', 'note')" class="hover:text-indigo-600 p-0.5 text-xs">✏️</button>
                            <button onclick="event.stopPropagation(); deleteItem('${note.id}', 'note')" class="hover:text-red-600 p-0.5 text-xs">🗑️</button>
                        </div>
                    `;
                    noteEl.innerHTML = `
                        <div class="flex items-center space-x-1.5 flex-1 min-w-0" onclick="selectNote('${note.id}')">
                            <span>📌</span>
                            <span class="truncate">${noteTitle}</span>
                        </div>
                        ${noteButtons}
                    `;
                    noteList.appendChild(noteEl);
                });
            }
        }

        // TRIGGER TREE FILTERING
        function filterTree(val) {
            renderTree(val);
        }

        // LOAD FIRST SCENE ON START
        function loadFirstAvailableScene() {
            let firstSceneId = null;
            if (projectData && projectData.manuscript) {
                for (const chap of projectData.manuscript) {
                    if (chap.children && chap.children.length > 0) {
                        firstSceneId = chap.children[0].id;
                        break;
                    }
                }
            }
            if (firstSceneId) {
                selectScene(firstSceneId);
            } else {
                selectPlotGrid();
            }
        }

        // PANELS NAVIGATION & VIEW SWITCHING
        function switchView(viewName) {
            document.getElementById('editor-view').classList.add('hidden');
            document.getElementById('plot-grid-view').classList.add('hidden');
            document.getElementById('resource-view').classList.add('hidden');

            if (viewName === 'editor') {
                document.getElementById('editor-view').classList.remove('hidden');
            } else if (viewName === 'plot') {
                document.getElementById('plot-grid-view').classList.remove('hidden');
            } else if (viewName === 'resource') {
                document.getElementById('resource-view').classList.remove('hidden');
            }
        }

        function findParentChapter(sceneId) {
            for (const chap of projectData.manuscript) {
                if (chap.children) {
                    for (const scene of chap.children) {
                        if (scene.id === sceneId) {
                            return chap;
                        }
                    }
                }
            }
            return null;
        }

        function autoResizeTextarea(el) {
            el.style.height = 'auto';
            el.style.height = el.scrollHeight + 'px';
        }

        function onChapterBlockInput(chapId, field, val) {
            const node = findNodeById(chapId);
            if (node) {
                node[field] = val;
                triggerAutoSave();
                // Live update tree title
                const treeTitleEl = document.querySelector(`[data-chap-id="${chapId}"] .chap-title`);
                if (treeTitleEl) treeTitleEl.innerText = val;
            }
        }

        function onSceneBlockInput(sceneId, field, val) {
            const node = findNodeById(sceneId);
            if (node) {
                node[field] = val;
                triggerAutoSave();
                if (field === 'title') {
                    // Live update tree title
                    const treeTitleEl = document.querySelector(`[data-scene-id="${sceneId}"] .scene-title`);
                    if (treeTitleEl) treeTitleEl.innerText = val;
                }
                updateEditorWordsCount();
            }
        }

        function onSceneBlockFocus(sceneId) {
            // Restore previous active textarea's id if any
            const previousActive = document.getElementById('editor-content');
            if (previousActive && previousActive.getAttribute('data-scene-id') !== sceneId) {
                const oldId = previousActive.getAttribute('data-scene-id');
                previousActive.id = `editor-content-${oldId}`;
            }

            // Assign 'editor-content' id to focused textarea
            const currentTextarea = document.getElementById(`editor-content-${sceneId}`);
            if (currentTextarea) {
                currentTextarea.id = 'editor-content';
            }

            // Update active node state & highlights
            if (activeNodeId !== sceneId) {
                activeNodeId = sceneId;
                activeNodeType = "scene";
                renderTree();
                updateEditorWordsCount();
            }
        }

        // ACTIVE WORKSPACE REFRESH
        function refreshActiveWorkspace() {
            if (activeNodeType === "scene" || activeNodeType === "chapter") {
                let chapter = null;
                let targetSceneId = null;

                if (activeNodeType === "scene") {
                    targetSceneId = activeNodeId;
                    chapter = findParentChapter(targetSceneId);
                } else {
                    chapter = findNodeById(activeNodeId);
                }

                if (chapter) {
                    switchView('editor');
                    const wrapper = document.getElementById('editor-layout-wrapper');

                    // Render Chapter header & scenes stacked
                    let html = `
                        <!-- Chapter Header -->
                        <div class="chapter-header-block mb-10 pb-4 border-b border-slate-200 shrink-0">
                            <span class="text-xs font-bold text-indigo-600 uppercase tracking-wider">Chapitre / Chapter</span>
                            <input type="text" id="editor-title" value="${escapeHtml(chapter.title)}" oninput="onChapterBlockInput('${chapter.id}', 'title', this.value)" placeholder="Titre du chapitre..." class="w-full text-3xl font-bold font-georgia border-none outline-none focus:ring-0 text-slate-900 placeholder-slate-300 bg-transparent mt-1">
                        </div>
                    `;

                    chapter.children = chapter.children || [];
                    if (chapter.children.length === 0) {
                        html += `
                            <div class="text-slate-400 italic text-sm text-center py-10">
                                Aucune scène dans ce chapitre. Créez-en une pour commencer à rédiger !
                            </div>
                        `;
                    } else {
                        chapter.children.forEach(scene => {
                            const isCurrentActive = (scene.id === targetSceneId);
                            const textareaId = isCurrentActive ? 'editor-content' : `editor-content-${scene.id}`;
                            html += `
                                <div id="scene-block-${scene.id}" class="scene-block mb-12 pb-12 border-b border-slate-100">
                                    <div class="flex items-center justify-between mb-2">
                                        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Scène / Scene</span>
                                    </div>
                                    <input type="text" value="${escapeHtml(scene.title)}" oninput="onSceneBlockInput('${scene.id}', 'title', this.value)" placeholder="Titre de la scène..." class="w-full text-2xl font-bold font-georgia border-none outline-none focus:ring-0 text-slate-800 placeholder-slate-300 pb-2 mb-4 bg-transparent">
                                    <textarea id="${textareaId}" data-scene-id="${scene.id}" onfocus="onSceneBlockFocus('${scene.id}')" oninput="onSceneBlockInput('${scene.id}', 'content', this.value); autoResizeTextarea(this)" placeholder="Commencez à rédiger votre scène ici..." class="w-full resize-none font-georgia text-lg leading-relaxed text-slate-800 border-none outline-none focus:ring-0 placeholder-slate-300 bg-transparent min-h-[150px]">${escapeHtml(scene.content || "")}</textarea>
                                </div>
                            `;
                        });
                    }

                    wrapper.innerHTML = html;

                    // Compute textareas heights and scroll to active
                    setTimeout(() => {
                        // Trigger auto-resize on all textareas
                        const textareas = wrapper.querySelectorAll('textarea');
                        textareas.forEach(ta => autoResizeTextarea(ta));

                        // Navigation scrolling
                        if (targetSceneId) {
                            const activeBlock = document.getElementById(`scene-block-${targetSceneId}`);
                            if (activeBlock) {
                                activeBlock.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                // Focus active scene input
                                const activeTa = document.getElementById('editor-content');
                                if (activeTa) activeTa.focus();
                            }
                        } else {
                            // Sliced at chapter level, scroll to top of editor container
                            const scrollContainer = document.getElementById('editor-scroll-container');
                            if (scrollContainer) scrollContainer.scrollTop = 0;
                        }
                        updateEditorWordsCount();
                    }, 50);

                }
            } else if (activeNodeType === "character") {
                let char = projectData.characters.find(c => c.id === activeNodeId);
                if (char) {
                    char = ensureCharacterFields(char);
                    switchView('resource');
                    document.getElementById('resource-icon').innerText = "👤";
                    document.getElementById('resource-title').value = char.name;
                    document.getElementById('character-fields').classList.remove('hidden');
                    document.getElementById('note-fields').classList.add('hidden');

                    renderCharacterFields(char);
                }
            } else if (activeNodeType === "note") {
                const note = projectData.story_notes.find(n => n.id === activeNodeId);
                if (note) {
                    switchView('resource');
                    document.getElementById('resource-icon').innerText = "📌";
                    document.getElementById('resource-title').value = note.title;
                    document.getElementById('character-fields').classList.add('hidden');
                    document.getElementById('note-fields').classList.remove('hidden');

                    document.getElementById('note-type').value = note.type || "";
                    document.getElementById('note-content').value = note.content || "";
                }
            } else if (activeNodeType === "plot_grid") {
                switchView('plot');
                refreshPlotView();
            }
            applyLockState();
            applyEditorLayoutSettings();
        }

        // DRAG AND DROP HANDLERS FOR CHAPTERS
        function handleChapDragStart(e) {
            draggedChapId = this.getAttribute('data-chap-id');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', draggedChapId);
            this.classList.add('opacity-50');
        }

        function handleChapDragOver(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';

            const rect = this.getBoundingClientRect();
            const midpoint = rect.top + rect.height / 2;

            if (e.clientY < midpoint) {
                this.classList.add('border-t-indigo-500');
                this.classList.remove('border-t-transparent', 'border-b-indigo-500');
                this.classList.add('border-b-transparent');
            } else {
                this.classList.add('border-b-indigo-500');
                this.classList.remove('border-b-transparent', 'border-t-indigo-500');
                this.classList.add('border-t-transparent');
            }
        }

        function handleChapDragLeave(e) {
            this.classList.remove('border-t-indigo-500', 'border-b-indigo-500');
            this.classList.add('border-t-transparent', 'border-b-transparent');
        }

        function handleChapDragEnd(e) {
            this.classList.remove('opacity-50', 'border-t-indigo-500', 'border-b-indigo-500');
            this.classList.add('border-t-transparent', 'border-b-transparent');
            document.querySelectorAll('#manuscript-nodes-list > .group').forEach(el => {
                el.classList.remove('border-t-indigo-500', 'border-b-indigo-500');
                el.classList.add('border-t-transparent', 'border-b-transparent');
            });
        }

        function handleChapDrop(e) {
            e.preventDefault();
            this.classList.remove('border-t-indigo-500', 'border-b-indigo-500');
            this.classList.add('border-t-transparent', 'border-b-transparent');

            const targetChapId = this.getAttribute('data-chap-id');
            if (!draggedChapId || draggedChapId === targetChapId) return;

            // Reorder in projectData.manuscript
            const manuscript = projectData.manuscript;
            const draggedIdx = manuscript.findIndex(c => c.id === draggedChapId);
            const targetIdx = manuscript.findIndex(c => c.id === targetChapId);

            if (draggedIdx === -1 || targetIdx === -1) return;

            const rect = this.getBoundingClientRect();
            const midpoint = rect.top + rect.height / 2;

            // Determine insertion index
            let newIdx = targetIdx;
            if (e.clientY >= midpoint) {
                newIdx = targetIdx + 1;
            }

            // Remove from old position
            const [draggedChap] = manuscript.splice(draggedIdx, 1);

            // Adjust target index if old index was before target index
            let insertIdx = newIdx;
            if (draggedIdx < newIdx) {
                insertIdx = newIdx - 1;
            }

            // Insert at new position
            manuscript.splice(insertIdx, 0, draggedChap);

            // Save and re-render
            triggerAutoSave();
            renderTree();
        }

        // SELECT HANDLERS
        function selectScene(id) {
            activeNodeId = id;
            activeNodeType = "scene";
            renderTree();
            refreshActiveWorkspace();
        }

        function selectChapter(id) {
            activeNodeId = id;
            activeNodeType = "chapter";
            renderTree();
            refreshActiveWorkspace();
        }

        function selectCharacter(id) {
            activeNodeId = id;
            activeNodeType = "character";
            renderTree();
            refreshActiveWorkspace();
        }

        function selectNote(id) {
            activeNodeId = id;
            activeNodeType = "note";
            renderTree();
            refreshActiveWorkspace();
        }

        function selectPlotGrid() {
            activeNodeId = "PLOT_GRID";
            activeNodeType = "plot_grid";
            renderTree();
            refreshActiveWorkspace();
        }

        // FIND NODE IN MANUSCRIPT HIERARCHY
        function findNodeById(id, list = projectData.manuscript) {
            for (const item of list) {
                if (item.id === id) return item;
                if (item.children) {
                    const found = findNodeById(id, item.children);
                    if (found) return found;
                }
            }
            return null;
        }

        // INPUT CHANGED HANDLERS (EDITOR / RESOURCE)
        function onEditorInput(field, val) {
            if (activeNodeType === "scene") {
                const node = findNodeById(activeNodeId);
                if (node) {
                    node[field] = val;
                    if (field === 'title') {
                        // Refresh tree live to show title change
                        renderTree();
                    } else if (field === 'content') {
                        updateEditorWordsCount(val);
                    }
                    triggerAutoSave();
                }
            } else if (activeNodeType === "chapter" && field === "title") {
                const node = findNodeById(activeNodeId);
                if (node) {
                    node.title = val;
                    renderTree();
                    triggerAutoSave();
                }
            }
        }

        // RESOURCE FIELDS SAVE
        function onResourceInput(field, val) {
            if (activeNodeType === "character") {
                const char = projectData.characters.find(c => c.id === activeNodeId);
                if (char) {
                    if (field === 'title') {
                        char.name = val;
                        renderTree();
                    } else {
                        char[field] = val;
                    }
                    triggerAutoSave();
                }
            } else if (activeNodeType === "note") {
                const note = projectData.story_notes.find(n => n.id === activeNodeId);
                if (note) {
                    if (field === 'title') {
                        note.title = val;
                        renderTree();
                    } else {
                        note[field] = val;
                    }
                    triggerAutoSave();
                }
            }
        }

        // CHARACTER LORE MODEL AND RENDERING HELPERS
        function ensureCharacterFields(char) {
            if (!char) return char;
            if (char.type === undefined) char.type = "personnage";
            if (char.aliases === undefined) char.aliases = [];
            if (char.traits === undefined) char.traits = [];
            if (char.appearance === undefined) char.appearance = "";
            if (char.notes === undefined) char.notes = "";
            if (char.relations === undefined) char.relations = [];
            if (char.linked_scenes === undefined) char.linked_scenes = [];
            return char;
        }

        function renderCharacterFields(char) {
            const container = document.getElementById('character-fields');
            if (!container) return;
            container.innerHTML = "";

            // Ensure compatibility
            ensureCharacterFields(char);

            // 1. ROLE / FONCTION
            const roleDiv = document.createElement('div');
            roleDiv.className = "space-y-1";
            roleDiv.innerHTML = `
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_role">${translations["character_role"] || "Rôle / Fonction"}</label>
                <input type="text" id="char-role" value="${char.role || ''}" class="w-full rounded-lg border-slate-300 text-sm focus:border-indigo-500 focus:ring-indigo-500 shadow-sm">
            `;
            const roleInput = roleDiv.querySelector('#char-role');
            roleInput.addEventListener('input', (e) => {
                char.role = e.target.value;
                triggerAutoSave();
            });
            container.appendChild(roleDiv);

            // 2. ALIASES / SURNOMS (TAGS + INPUT)
            const aliasDiv = document.createElement('div');
            aliasDiv.className = "space-y-2";

            // Render existing tags
            let aliasTagsHtml = char.aliases.map((alias, idx) => `
                <span class="inline-flex items-center gap-1 bg-slate-100 text-slate-700 text-xs px-2.5 py-1 rounded-full border border-slate-200">
                    <span>${escapeHtml(alias)}</span>
                    <button class="text-slate-400 hover:text-slate-600 font-bold focus:outline-none" onclick="removeAlias(${idx})">&times;</button>
                </span>
            `).join('');

            aliasDiv.innerHTML = `
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_aliases">${translations["character_aliases"] || "Surnoms / Alias"}</label>
                <div class="flex flex-wrap gap-1.5 mb-2">${aliasTagsHtml || '<span class="text-xs text-slate-400 italic">Aucun surnom</span>'}</div>
                <div class="flex gap-1.5">
                    <input type="text" id="new-alias-input" placeholder="${translations["placeholder_new_alias"] || "Nouveau surnom..."}" class="flex-1 rounded-lg border-slate-300 text-xs focus:border-indigo-500 focus:ring-indigo-500 shadow-sm">
                    <button onclick="addAlias()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-1.5 rounded-lg text-xs transition-all" data-i18n="add_alias">${translations["add_alias"] || "Ajouter"}</button>
                </div>
            `;
            container.appendChild(aliasDiv);

            // Add alias enter listener
            const aliasInput = aliasDiv.querySelector('#new-alias-input');
            aliasInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addAlias();
                }
            });

            window.addAlias = () => {
                const input = document.getElementById('new-alias-input');
                const val = input.value.trim();
                if (val) {
                    char.aliases.push(val);
                    triggerAutoSave();
                    renderCharacterFields(char);
                }
            };
            window.removeAlias = (idx) => {
                char.aliases.splice(idx, 1);
                triggerAutoSave();
                renderCharacterFields(char);
            };

            // 3. TRAITS / CARACTÈRE (TAGS + INPUT)
            const traitDiv = document.createElement('div');
            traitDiv.className = "space-y-2";

            let traitTagsHtml = char.traits.map((trait, idx) => `
                <span class="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 text-xs px-2.5 py-1 rounded-full border border-indigo-100">
                    <span>${escapeHtml(trait)}</span>
                    <button class="text-indigo-400 hover:text-indigo-600 font-bold focus:outline-none" onclick="removeTrait(${idx})">&times;</button>
                </span>
            `).join('');

            traitDiv.innerHTML = `
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_traits">${translations["character_traits"] || "Traits de caractère"}</label>
                <div class="flex flex-wrap gap-1.5 mb-2">${traitTagsHtml || '<span class="text-xs text-slate-400 italic">Aucun trait</span>'}</div>
                <div class="flex gap-1.5">
                    <input type="text" id="new-trait-input" placeholder="${translations["placeholder_new_trait"] || "Nouveau trait..."}" class="flex-1 rounded-lg border-slate-300 text-xs focus:border-indigo-500 focus:ring-indigo-500 shadow-sm">
                    <button onclick="addTrait()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-1.5 rounded-lg text-xs transition-all" data-i18n="add_trait">${translations["add_trait"] || "Ajouter"}</button>
                </div>
            `;
            container.appendChild(traitDiv);

            // Add trait enter listener
            const traitInput = traitDiv.querySelector('#new-trait-input');
            traitInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addTrait();
                }
            });

            window.addTrait = () => {
                const input = document.getElementById('new-trait-input');
                const val = input.value.trim();
                if (val) {
                    char.traits.push(val);
                    triggerAutoSave();
                    renderCharacterFields(char);
                }
            };
            window.removeTrait = (idx) => {
                char.traits.splice(idx, 1);
                triggerAutoSave();
                renderCharacterFields(char);
            };

            // 4. DESCRIPTION PHYSIQUE
            const appDiv = document.createElement('div');
            appDiv.className = "space-y-1";
            appDiv.innerHTML = `
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_appearance">${translations["character_appearance"] || "Apparence physique"}</label>
                <textarea id="char-appearance" rows="3" class="w-full rounded-lg border-slate-300 text-sm focus:border-indigo-500 focus:ring-indigo-500 shadow-sm resize-none" placeholder="cicatrices, style vestimentaire, particularités...">${char.appearance || ''}</textarea>
            `;
            const appTextarea = appDiv.querySelector('#char-appearance');
            appTextarea.addEventListener('input', (e) => {
                char.appearance = e.target.value;
                triggerAutoSave();
            });
            container.appendChild(appDiv);

            // 5. DESCRIPTION GÉNÉRALE
            const descDiv = document.createElement('div');
            descDiv.className = "space-y-1";
            descDiv.innerHTML = `
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_desc">${translations["character_desc"] || "Description du personnage"}</label>
                <textarea id="char-desc" rows="4" class="w-full rounded-lg border-slate-300 text-sm focus:border-indigo-500 focus:ring-indigo-500 shadow-sm resize-none">${char.description || ''}</textarea>
            `;
            const descTextarea = descDiv.querySelector('#char-desc');
            descTextarea.addEventListener('input', (e) => {
                char.description = e.target.value;
                triggerAutoSave();
            });
            container.appendChild(descDiv);

            // 6. RELATIONS (DYNAMIC CARDS LIST)
            const relDiv = document.createElement('div');
            relDiv.className = "space-y-3 pt-4 border-t border-slate-100";

            let relationsHtml = "";
            const availableChars = projectData.characters.filter(c => c.id !== char.id);

            if (char.relations.length === 0) {
                relationsHtml = `<div class="text-xs text-slate-400 italic">Aucune relation définie.</div>`;
            } else {
                char.relations.forEach((rel, idx) => {
                    const selectOptions = availableChars.map(c => `
                        <option value="${c.id}" ${c.id === rel.target_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>
                    `).join('');

                    relationsHtml += `
                        <div class="bg-slate-50 border border-slate-200 p-3 rounded-lg flex flex-col gap-2 relative group shadow-2xs">
                            <button onclick="removeRelation(${idx})" class="absolute top-2 right-2 text-slate-400 hover:text-red-500 text-sm focus:outline-none">🗑️</button>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-0.5" data-i18n="relation_target">${translations["relation_target"] || "Personnage cible"}</label>
                                    <select onchange="updateRelation(${idx}, 'target_id', this.value)" class="w-full bg-white border border-slate-300 rounded-lg text-xs py-1 px-1.5 focus:border-indigo-500 focus:ring-indigo-500">
                                        <option value="" disabled ${!rel.target_id ? 'selected' : ''}>Sélectionner...</option>
                                        ${selectOptions}
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-0.5" data-i18n="relation_type">${translations["relation_type"] || "Type de relation"}</label>
                                    <input type="text" value="${escapeHtml(rel.type || '')}" oninput="updateRelation(${idx}, 'type', this.value)" placeholder="${translations["placeholder_relation_type"] || "e.g. Rival, Amant..."}" class="w-full bg-white border border-slate-300 rounded-lg text-xs py-1 px-1.5 focus:border-indigo-500 focus:ring-indigo-500">
                                </div>
                            </div>
                            <div>
                                <label class="block text-[10px] font-semibold text-slate-400 mb-0.5" data-i18n="relation_desc">${translations["relation_desc"] || "Description de la relation"}</label>
                                <input type="text" value="${escapeHtml(rel.description || '')}" oninput="updateRelation(${idx}, 'description', this.value)" placeholder="${translations["placeholder_relation_desc"] || "Description..."}" class="w-full bg-white border border-slate-300 rounded-lg text-xs py-1 px-1.5 focus:border-indigo-500 focus:ring-indigo-500">
                            </div>
                        </div>
                    `;
                });
            }

            relDiv.innerHTML = `
                <div class="flex justify-between items-center">
                    <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_relations">${translations["character_relations"] || "Relations"}</label>
                    <button onclick="addRelation()" class="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 font-bold px-2.5 py-1 rounded-lg text-xs transition-all" data-i18n="add_relation">${translations["add_relation"] || "+ Ajouter relation"}</button>
                </div>
                <div class="space-y-2.5">${relationsHtml}</div>
            `;
            container.appendChild(relDiv);

            window.addRelation = () => {
                char.relations.push({ target_id: "", type: "", description: "" });
                triggerAutoSave();
                renderCharacterFields(char);
            };
            window.removeRelation = (idx) => {
                char.relations.splice(idx, 1);
                triggerAutoSave();
                renderCharacterFields(char);
            };
            window.updateRelation = (idx, key, val) => {
                char.relations[idx][key] = val;
                triggerAutoSave();
            };

            // 7. SCÈNES RELIÉES (CHECKLIST OF ALL SCENES IN MANUSCRIPT)
            const scenesDiv = document.createElement('div');
            scenesDiv.className = "space-y-2 pt-4 border-t border-slate-100";

            // Collect all scenes
            const allScenes = [];
            projectData.manuscript.forEach(chap => {
                chap.children.forEach(scene => {
                    allScenes.push({ id: scene.id, title: scene.title, chapterTitle: chap.title });
                });
            });

            let scenesChecklistHtml = "";
            if (allScenes.length === 0) {
                scenesChecklistHtml = `<div class="text-xs text-slate-400 italic">Aucune scène disponible dans le manuscrit.</div>`;
            } else {
                allScenes.forEach(scene => {
                    const isChecked = char.linked_scenes && char.linked_scenes.includes(scene.id);
                    scenesChecklistHtml += `
                        <label class="flex items-center space-x-2 text-xs text-slate-600 hover:text-slate-900 cursor-pointer py-0.5">
                            <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleLinkedScene('${scene.id}', this.checked)" class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer">
                            <span>${escapeHtml(scene.chapterTitle)} : <strong class="text-slate-700">${escapeHtml(scene.title)}</strong></span>
                        </label>
                    `;
                });
            }

            scenesDiv.innerHTML = `
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_scenes">${translations["character_scenes"] || "Scènes associées"}</label>
                <div class="max-h-36 overflow-y-auto bg-slate-50 border border-slate-200 p-2.5 rounded-lg space-y-1 shadow-2xs">${scenesChecklistHtml}</div>
            `;
            container.appendChild(scenesDiv);

            window.toggleLinkedScene = (sceneId, isChecked) => {
                if (!char.linked_scenes) char.linked_scenes = [];
                if (isChecked) {
                    if (!char.linked_scenes.includes(sceneId)) char.linked_scenes.push(sceneId);
                } else {
                    char.linked_scenes = char.linked_scenes.filter(id => id !== sceneId);
                }
                triggerAutoSave();
            };

            // 8. NOTES LIBRES / LORE
            const notesDiv = document.createElement('div');
            notesDiv.className = "space-y-1 pt-4 border-t border-slate-100";
            notesDiv.innerHTML = `
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-400" data-i18n="character_notes">${translations["character_notes"] || "Notes libres / Lore"}</label>
                <textarea id="char-notes" rows="4" class="w-full rounded-lg border-slate-300 text-sm focus:border-indigo-500 focus:ring-indigo-500 shadow-sm resize-none" placeholder="Notes de l'auteur sur son passé, motivations...">${char.notes || ''}</textarea>
            `;
            const notesTextarea = notesDiv.querySelector('#char-notes');
            notesTextarea.addEventListener('input', (e) => {
                char.notes = e.target.value;
                triggerAutoSave();
            });
            container.appendChild(notesDiv);
        }

        // Helper to escape HTML characters securely
        function escapeHtml(str) {
            if (!str) return '';
            return str
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        // WORD COUNTERS UPDATES
        function updateEditorWordsCount(text) {
            if (text === undefined) {
                const el = document.getElementById('editor-content');
                text = el ? (el.value || "") : "";
            }
            const cleanText = text.trim();
            const words = cleanText ? cleanText.split(/\s+/).length : 0;
            const chars = text.length;

            document.getElementById('editor-words-count').innerText = formatTranslation("words_count", { words });
            document.getElementById('editor-chars-count').innerText = formatTranslation("chars_count", { chars });
        }

        // WORD GOALS & PROGRESS UPDATE
        function updateRightSidebar() {
            // Recompute overall written word count
            let totalWords = 0;
            projectData.manuscript.forEach(chap => {
                chap.children.forEach(scene => {
                    const cleanText = (scene.content || "").trim();
                    if (cleanText) {
                        totalWords += cleanText.split(/\s+/).length;
                    }
                });
            });

            projectData.settings.overall_written = totalWords;

            const dailyGoal = projectData.settings.daily_goal || 500;
            const overallGoal = projectData.settings.overall_goal || 50000;
            const dailyWritten = Math.min(dailyGoal, totalWords); // simplified simulation

            // Update inputs and sliders
            document.getElementById('daily-goal-input').value = dailyGoal;

            // Update text elements
            document.getElementById('daily-progress-text').innerText = formatTranslation("daily_progress", { written: dailyWritten, goal: dailyGoal });
            document.getElementById('overall-progress-text').innerText = formatTranslation("overall_progress", { written: totalWords, goal: overallGoal });

            // Update bars
            const dailyPct = Math.min(100, (dailyWritten / dailyGoal) * 100);
            const overallPct = Math.min(100, (totalWords / overallGoal) * 100);

            document.getElementById('daily-progress-bar').style.width = `${dailyPct}%`;
            document.getElementById('overall-progress-bar').style.width = `${overallPct}%`;
        }

        function onDailyGoalChange(val) {
            projectData.settings.daily_goal = parseInt(val) || 500;
            updateRightSidebar();
            persistProject();
        }

        // ADDING NODES (CHAPTERS / SCENES / ASSETS)
        function generateId(prefix) {
            return `${prefix}_${Math.random().toString(36).substr(2, 9)}`;
        }

        // DATASET FOR SPECIAL CHAPTER TYPES
        const CHAPTER_TYPES = {
            "page_titre": {
                emoji: "📝",
                category: "liminaires",
                title_fr: "Page de titre",
                title_en: "Title Page",
                desc_fr: "Titre + sous-titre + auteur",
                desc_en: "Title + subtitle + author",
                default_title_fr: "Page de Titre",
                default_title_en: "Title Page",
                template_fr: "[TITRE DU ROMAN]\n[SOUS-TITRE (OPTIONNEL)]\n\n\nÉcrit par [NOM DE L'AUTEUR]",
                template_en: "[NOVEL TITLE]\n[SUBTITLE (OPTIONAL)]\n\n\nWritten by [AUTHOR NAME]"
            },
            "copyright": {
                emoji: "⚖️",
                category: "liminaires",
                title_fr: "Page de copyright / mentions légales",
                title_en: "Copyright Page / Legal notes",
                desc_fr: "Droits d'auteur, ISBN, année, maison d'édition",
                desc_en: "Copyright, ISBN, year, publisher",
                default_title_fr: "Copyright",
                default_title_en: "Copyright",
                template_fr: "© [ANNÉE] [NOM DE L'AUTEUR]. Tous droits réservés.\n\nISBN : [ISBN-13]\nMaison d'édition : [NOM DE LA MAISON D'ÉDITION]\n\nAucune partie de ce livre ne peut être reproduite ou transmise sous quelque forme ou par quelque moyen que ce soit, électronique ou mécanique, y compris la photocopie, l'enregistrement ou par tout système de stockage et de récupération d'informations, sans l'autorisation écrite de l'auteur.",
                template_en: "© [YEAR] [AUTHOR NAME]. All rights reserved.\n\nISBN: [ISBN-13]\nPublisher: [PUBLISHER NAME]\n\nNo part of this book may be reproduced or transmitted in any form or by any means, electronic or mechanical, including photocopying, recording, or by any information storage and retrieval system, without written permission from the author."
            },
            "dedicace": {
                emoji: "💝",
                category: "liminaires",
                title_fr: "Dédicace",
                title_en: "Dedication",
                desc_fr: "Citation ou hommage personnel en ouverture",
                desc_en: "Opening quote or personal tribute",
                default_title_fr: "Dédicace",
                default_title_en: "Dedication",
                template_fr: "À [Nom de la personne],\n\n[Votre dédicace personnelle ici, par exemple : pour m'avoir toujours soutenu et inspiré tout au long de cette aventure.]",
                template_en: "To [Person's Name],\n\n[Your personal dedication here, e.g.: for always supporting and inspiring me throughout this journey.]"
            },
            "epigraphe": {
                emoji: "💬",
                category: "liminaires",
                title_fr: "Épigraphe",
                title_en: "Epigraph",
                desc_fr: "Citation en ouverture du livre",
                desc_en: "Citation in opening of the book",
                default_title_fr: "Épigraphe",
                default_title_en: "Epigraph",
                template_fr: "\"Le secret de commencer est de s'y mettre.\"\n— Mark Twain",
                template_en: "\"The secret of getting ahead is getting started.\"\n— Mark Twain"
            },
            "preface": {
                emoji: "✍️",
                category: "liminaires",
                title_fr: "Préface / Avant-propos",
                title_en: "Preface / Foreword",
                desc_fr: "Texte de présentation rédigé par l'auteur",
                desc_en: "Presentation text written by the author",
                default_title_fr: "Préface",
                default_title_en: "Preface",
                template_fr: "PRÉFACE\n\n[Écrivez ici votre préface. Expliquez le contexte de l'œuvre, votre inspiration, les motivations qui vous ont poussé à écrire ce livre, ou tout message préalable à l'intention de vos lecteurs.]",
                template_en: "PREFACE\n\n[Write your preface here. Explain the context of the work, your inspiration, the motivations that drove you to write this book, or any introductory message for your readers.]"
            },
            "preambule": {
                emoji: "🌌",
                category: "liminaires",
                title_fr: "Préambule",
                title_en: "Preamble",
                desc_fr: "Texte court posant l'univers ou un événement antérieur",
                desc_en: "Short text setting up the universe or prior event",
                default_title_fr: "Préambule",
                default_title_en: "Preamble",
                template_fr: "PRÉAMBULE\n\n[Le préambule présente brièvement l'univers ou un événement marquant survenu antérieurement au début de l'intrigue principale.]",
                template_en: "PREAMBLE\n\n[The preamble briefly introduces the universe or a significant event that occurred prior to the start of the main plot.]"
            },
            "introduction": {
                emoji: "📘",
                category: "liminaires",
                title_fr: "Introduction",
                title_en: "Introduction",
                desc_fr: "Surtout pour la non-fiction ou romans littéraires",
                desc_en: "Mainly for non-fiction or literary novels",
                default_title_fr: "Introduction",
                default_title_en: "Introduction",
                template_fr: "INTRODUCTION\n\n[Introduction générale posant les thèmes majeurs du roman, particulièrement adapté pour la non-fiction ou les œuvres littéraires complexes.]",
                template_en: "INTRODUCTION\n\n[General introduction establishing the major themes of the book, particularly suitable for non-fiction or complex literary works.]"
            },
            "table_matieres": {
                emoji: "📊",
                category: "liminaires",
                title_fr: "Table des matières",
                title_en: "Table of Contents",
                desc_fr: "Générée automatiquement lors de l'export final",
                desc_en: "Automatically generated during final export",
                default_title_fr: "Table des Matières",
                default_title_en: "Table of Contents",
                template_fr: "TABLE DES MATIÈRES (GÉNÉRÉE AUTOMATIQUEMENT)\n\n[La table des matières sera générée dynamiquement lors de la publication ou de l'export final.]",
                template_en: "TABLE OF CONTENTS (AUTOMATICALLY GENERATED)\n\n[The table of contents will be generated dynamically during publication or final export.]"
            },
            "prologue": {
                emoji: "🎬",
                category: "corps",
                title_fr: "Prologue",
                title_en: "Prologue",
                desc_fr: "Scène d'ouverture se passant avant l'histoire principale",
                desc_en: "Opening scene taking place before the main story",
                default_title_fr: "Prologue",
                default_title_en: "Prologue",
                template_fr: "PROLOGUE\n\n[Scène d'ouverture se déroulant généralement avant le début de l'intrigue principale, posant une ambiance dramatique ou un événement fondateur.]",
                template_en: "PROLOGUE\n\n[Opening scene usually taking place before the main plot starts, setting a dramatic mood or seminal event.]"
            },
            "chapitre_ouverture": {
                emoji: "🔑",
                category: "corps",
                title_fr: "Chapitre d'ouverture / Incipit",
                title_en: "Opening Chapter / Incipit",
                desc_fr: "Premier chapitre posant le protagoniste et la situation",
                desc_en: "First chapter setting up protagonist and initial situation",
                default_title_fr: "Chapitre d'ouverture",
                default_title_en: "Opening Chapter",
                template_fr: "[Entrez ici le texte de votre scène d'ouverture. L'incipit a pour but de capter l'intérêt du lecteur, d'introduire le protagoniste et de poser les bases de la situation initiale.]",
                template_en: "[Enter your opening scene text here. The incipit aims to capture reader interest, introduce the protagonist, and establish the initial situation.]"
            },
            "chapitre_standard": {
                emoji: "📖",
                category: "corps",
                title_fr: "Chapitre",
                title_en: "Chapter",
                desc_fr: "Le cœur et le corps principal du roman",
                desc_en: "The heart and main body of the novel",
                default_title_fr: "Chapitre",
                default_title_en: "Chapter",
                template_fr: "[Entrez ici le texte de votre scène. Développez l'intrigue, les dialogues et les péripéties de vos personnages.]",
                template_en: "[Enter your scene text here. Develop the plot, dialogue, and adventures of your characters.]"
            },
            "epilogue": {
                emoji: "🏁",
                category: "finales",
                title_fr: "Épilogue",
                title_en: "Epilogue",
                desc_fr: "Scène finale après la résolution de l'intrigue",
                desc_en: "Final scene after the resolution of the plot",
                default_title_fr: "Épilogue",
                default_title_en: "Epilogue",
                template_fr: "ÉPILOGUE\n\n[Scène de clôture se déroulant après la résolution de l'intrigue, montrant l'avenir des personnages ou offrant une conclusion finale à l'histoire.]",
                template_en: "EPILOGUE\n\n[Closing scene taking place after plot resolution, showing the characters' future or offering a final conclusion to the story.]"
            },
            "remerciements": {
                emoji: "🙏",
                category: "finales",
                title_fr: "Remerciements",
                title_en: "Acknowledgments",
                desc_fr: "Remerciements à votre entourage et relecteurs",
                desc_en: "Thanks to helpers, family and editors",
                default_title_fr: "Remerciements",
                default_title_en: "Acknowledgments",
                template_fr: "REMERCIEMENTS\n\n[Prenez un moment pour remercier les personnes qui vous ont aidé à concevoir, écrire, corriger et publier ce roman (famille, amis, relecteurs, bêta-lecteurs, éditeurs, etc.).]",
                template_en: "ACKNOWLEDGMENTS\n\n[Take a moment to thank the people who helped you design, write, edit, and publish this book (family, friends, editors, beta readers, etc.).]"
            },
            "biographie_auteur": {
                emoji: "🧑‍💻",
                category: "finales",
                title_fr: "Biographie de l'auteur",
                title_en: "Author Biography",
                desc_fr: "Présentation de l'auteur et de ses œuvres",
                desc_en: "Brief presentation of the author and works",
                default_title_fr: "Biographie de l'Auteur",
                default_title_en: "About the Author",
                template_fr: "À PROPOS DE L'AUTEUR\n\n[Écrivez une brève notice biographique. Présentez votre parcours, vos autres œuvres, vos passions et comment les lecteurs peuvent vous suivre ou vous contacter.]",
                template_en: "ABOUT THE AUTHOR\n\n[Write a brief biographical note. Present your background, other works, passions, and how readers can follow or contact you.]"
            },
            "notes_auteur": {
                emoji: "📝",
                category: "finales",
                title_fr: "Notes de l'auteur",
                title_en: "Author Notes",
                desc_fr: "Explications, sources documentaires ou historiques",
                desc_en: "Explanations, documentary or historical sources",
                default_title_fr: "Notes de l'Auteur",
                default_title_en: "Author Notes",
                template_fr: "NOTES DE L'AUTEUR\n\n[Fournissez ici des explications complémentaires, des sources historiques ou de recherche, ou des détails sur les choix artistiques effectués durant l'écriture.]",
                template_en: "AUTHOR NOTES\n\n[Provide additional explanations, historical or research sources, or details about artistic choices made during writing.]"
            },
            "glossaire": {
                emoji: "🔤",
                category: "finales",
                title_fr: "Glossaire",
                title_en: "Glossary",
                desc_fr: "Pour les univers imaginaires, fantasy, SF ou historiques",
                desc_en: "For fictional, fantasy, sci-fi or historical lore",
                default_title_fr: "Glossaire",
                default_title_en: "Glossary",
                template_fr: "GLOSSAIRE\n\nTerme 1 : Définition ou explication du terme dans votre univers.\nTerme 2 : Définition ou explication...",
                template_en: "GLOSSARY\n\nTerm 1: Definition or explanation of the term in your universe.\nTerm 2: Definition or explanation..."
            },
            "annexes": {
                emoji: "🗺️",
                category: "finales",
                title_fr: "Annexes",
                title_en: "Appendices",
                desc_fr: "Cartes, arbres généalogiques, chronologie",
                desc_en: "Maps, family trees, detailed chronologies",
                default_title_fr: "Annexes",
                default_title_en: "Appendices",
                template_fr: "ANNEXES\n\n[Ajoutez ici des éléments complémentaires pour enrichir votre œuvre : chronologies détaillées, arbres généalogiques décrits, listes de dynasties ou descriptions de documents fictifs.]",
                template_en: "APPENDICES\n\n[Add supplementary elements to enrich your work here: detailed timelines, family trees, list of dynasties, or fictional document descriptions.]"
            },
            "index": {
                emoji: "🔍",
                category: "finales",
                title_fr: "Index",
                title_en: "Index",
                desc_fr: "Index alphabétique (rare en pure fiction)",
                desc_en: "Alphabetical index of terms (rare in pure fiction)",
                default_title_fr: "Index",
                default_title_en: "Index",
                template_fr: "INDEX\n\n[Index alphabétique des notions clés ou des personnages importants.]",
                template_en: "INDEX\n\n[Alphabetical index of key terms or important characters.]"
            },
            "teaser": {
                emoji: "🔥",
                category: "finales",
                title_fr: "Teaser / Extrait du prochain tome",
                title_en: "Teaser / Next Volume Extract",
                desc_fr: "Extrait exclusif pour fidéliser vos lecteurs",
                desc_en: "Exclusive extract to hook your readers",
                default_title_fr: "Teaser - Prochain Tome",
                default_title_en: "Teaser - Next Book",
                template_fr: "EXTRAIT EXCLUSIF DU TOME SUIVANT\n\n[Insérez ici les premières lignes ou un chapitre d'accroche de votre prochain roman pour donner envie aux lecteurs de lire la suite de votre série.]",
                template_en: "EXCLUSIVE EXTRACT FROM NEXT VOLUME\n\n[Insert the first lines or hook chapter of your next novel here to entice readers to follow your series.]"
            }
        };

        let activeChapterCategory = "liminaires";

        function openChapterTypeModal() {
            document.getElementById('chapter-type-modal').classList.remove('hidden');
            selectChapterCategory('liminaires');
        }

        function closeChapterTypeModal() {
            document.getElementById('chapter-type-modal').classList.add('hidden');
        }

        function selectChapterCategory(category) {
            activeChapterCategory = category;

            // Highlight active tab
            const categories = ['liminaires', 'corps', 'finales'];
            categories.forEach(cat => {
                const tab = document.getElementById(`tab-category-${cat}`);
                if (cat === category) {
                    tab.className = "flex-1 py-1.5 rounded-md font-semibold transition-all bg-white text-slate-800 shadow-xs";
                } else {
                    tab.className = "flex-1 py-1.5 rounded-md font-semibold transition-all text-slate-500 hover:text-slate-800";
                }
            });

            // Render the grid of cards
            const grid = document.getElementById('chapter-cards-grid');
            grid.innerHTML = "";

            Object.keys(CHAPTER_TYPES).forEach(key => {
                const item = CHAPTER_TYPES[key];
                if (item.category !== category) return;

                const title = activeLang === 'fr' ? item.title_fr : item.title_en;
                const desc = activeLang === 'fr' ? item.desc_fr : item.desc_en;

                const card = document.createElement('div');
                card.className = "flex items-start space-x-3 p-3 bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-300 rounded-lg cursor-pointer transition-all";
                card.onclick = () => createSpecialChapter(key);

                card.innerHTML = `
                    <span class="text-2xl shrink-0">${item.emoji}</span>
                    <div class="min-w-0">
                        <h4 class="text-xs font-bold text-slate-800">${title}</h4>
                        <p class="text-[10px] text-slate-500 mt-0.5 leading-tight">${desc}</p>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function createSpecialChapter(subType) {
            const item = CHAPTER_TYPES[subType];
            if (!item) return;

            const isFr = (activeLang === 'fr');

            // Generate customized Title
            let defaultTitle = isFr ? item.default_title_fr : item.default_title_en;
            if (subType === "chapitre_standard" || subType === "chapitre_ouverture" || subType === "chapter") {
                const count = projectData.manuscript.filter(c => c.subType === "chapitre_standard" || c.subType === "chapitre_ouverture" || c.subType === "chapter").length + 1;
                defaultTitle = `${defaultTitle} ${count}`;
            }

            const newChap = {
                id: generateId("chap"),
                type: "chapter",
                subType: subType,
                title: defaultTitle,
                children: []
            };

            // Create initial scene containing formatted content template
            const defaultSceneTitle = isFr ? item.default_title_fr : item.default_title_en;
            const contentTemplate = isFr ? item.template_fr : item.template_en;

            const newScene = {
                id: generateId("scene"),
                type: "scene",
                title: defaultSceneTitle,
                content: contentTemplate
            };

            newChap.children.push(newScene);
            projectData.manuscript.push(newChap);

            renderTree();
            selectScene(newScene.id);
            persistProject();
            closeChapterTypeModal();
        }

        function addNewChapter() {
            openChapterTypeModal();
        }

        function addNewScene() {
            let parentChapId = null;

            // Use currently selected chapter if scene/chapter is selected
            if (activeNodeType === "chapter") {
                parentChapId = activeNodeId;
            } else if (activeNodeType === "scene") {
                // Find parent chapter
                for (const chap of projectData.manuscript) {
                    if (chap.children.some(s => s.id === activeNodeId)) {
                        parentChapId = chap.id;
                        break;
                    }
                }
            }

            // Fallback to last chapter
            if (!parentChapId && projectData.manuscript.length > 0) {
                parentChapId = projectData.manuscript[projectData.manuscript.length - 1].id;
            }

            if (!parentChapId) {
                // Create a chapter first if none exists
                addNewChapter();
                return;
            }

            const chap = findNodeById(parentChapId);
            const num = chap.children.length + 1;
            const newTitle = `${translations["new_scene_title"] || "New Scene"} ${num}`;
            const newScene = {
                id: generateId("scene"),
                type: "scene",
                title: newTitle,
                content: ""
            };
            chap.children.push(newScene);

            renderTree();
            selectScene(newScene.id);
            persistProject();
        }

        function showAssetMenu() {
            const dropdown = document.getElementById('asset-menu-dropdown');
            dropdown.classList.toggle('hidden');
        }

        function addNewCharacter() {
            document.getElementById('asset-menu-dropdown').classList.add('hidden');
            const num = projectData.characters.length + 1;
            const newChar = {
                id: generateId("char"),
                type: "personnage",
                name: `${translations["new_character_title"] || "New Character"} ${num}`,
                aliases: [],
                role: "Major Character",
                description: "",
                traits: [],
                appearance: "",
                notes: "",
                relations: [],
                linked_scenes: []
            };
            projectData.characters.push(newChar);

            renderTree();
            selectCharacter(newChar.id);
            persistProject();
        }

        function addNewNote() {
            document.getElementById('asset-menu-dropdown').classList.add('hidden');
            const num = projectData.story_notes.length + 1;
            const newNote = {
                id: generateId("note"),
                title: `${translations["new_note_title"] || "New Note"} ${num}`,
                type: "Location",
                content: ""
            };
            projectData.story_notes.push(newNote);

            renderTree();
            selectNote(newNote.id);
            persistProject();
        }


        // DELETING & RENAMING NODES
        function deleteItem(id, type) {
            const confirmMsg = translations["confirm_delete"] || "Are you sure you want to delete this item?";
            if (!confirm(confirmMsg)) return;

            if (type === "chapter" || type === "scene") {
                deleteManuscriptNode(id, projectData.manuscript);
            } else if (type === "character") {
                projectData.characters = projectData.characters.filter(c => c.id !== id);
            } else if (type === "note") {
                projectData.story_notes = projectData.story_notes.filter(n => n.id !== id);
            }

            // Clean up active state if deleted item was selected
            if (activeNodeId === id) {
                activeNodeId = null;
                activeNodeType = null;
            }

            renderTree();
            loadFirstAvailableScene();
            persistProject();
        }

        function deleteManuscriptNode(id, list) {
            for (let i = 0; i < list.length; i++) {
                if (list[i].id === id) {
                    // Clean related plot cards if deleting a scene
                    if (list[i].type === "scene") {
                        projectData.plot.cards = projectData.plot.cards.filter(card => card.scene_id !== id);
                    }
                    list.splice(i, 1);
                    return true;
                }
                if (list[i].children) {
                    const deleted = deleteManuscriptNode(id, list[i].children);
                    if (deleted) return true;
                }
            }
            return false;
        }

        function renameItem(id, type) {
            const item = (type === "character") ? projectData.characters.find(c => c.id === id) :
                         (type === "note") ? projectData.story_notes.find(n => n.id === id) : findNodeById(id);

            if (!item) return;
            const nameField = (type === "character") ? "name" : "title";

            const newName = prompt("Rename / Renommer :", item[nameField]);
            if (newName && newName.trim()) {
                item[nameField] = newName.trim();
                renderTree();
                refreshActiveWorkspace();
                persistProject();
            }
        }

        function toggleExportDropdown(event) {
            event.stopPropagation();
            const menu = document.getElementById('export-dropdown-menu');
            if (menu) {
                menu.classList.toggle('hidden');
            }
        }

        // EXPORT THE ENTIRE NOVEL
        async function exportDraft(format = 'txt') {
            try {
                // Hide menu immediately
                const menu = document.getElementById('export-dropdown-menu');
                if (menu) {
                    menu.classList.add('hidden');
                }

                // Post save first to ensure we export latest
                await persistProject();

                const response = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ format: format })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;

                    const cleanTitle = (projectData.settings.title || "roman").replace(/\s+/g, '_');
                    a.download = `${cleanTitle}_draft.${format}`;

                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                } else {
                    const errorJson = await response.json().catch(() => ({}));
                    alert("Export failed: " + (errorJson.error || "Unknown error"));
                }
            } catch (err) {
                console.error("Export error:", err);
            }
        }

        // AI OPTION TOGGLE HANDLER
        function toggleAiOption(enabled) {
            const aiChatSection = document.getElementById('ai-chat-section');
            if (aiChatSection) {
                if (enabled) {
                    aiChatSection.classList.remove('hidden');
                } else {
                    aiChatSection.classList.add('hidden');
                }
            }
            localStorage.setItem('ai-enabled', enabled ? 'true' : 'false');
        }

        // LANGUAGE CHANGE HANDLER
        async function changeLanguage(lang) {
            projectData.settings.lang = lang;
            await loadLocale(lang);
            renderTree();
            updateRightSidebar();
            persistProject();
        }

        async function populateOllamaModels() {
            const selectEl = document.getElementById('settings-ai-model-input');
            if (!selectEl) return;

            selectEl.innerHTML = "";
            const activeModel = projectData.settings.ai_model || "llama3";

            try {
                const response = await fetch('/api/ai/models');
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === "success" && data.models && data.models.length > 0) {
                        data.models.forEach(modelName => {
                            const opt = document.createElement('option');
                            opt.value = modelName;
                            opt.textContent = modelName;
                            selectEl.appendChild(opt);
                        });

                        if (data.models.includes(activeModel)) {
                            selectEl.value = activeModel;
                        } else {
                            selectEl.value = data.models[0];
                        }
                        return;
                    }
                }
            } catch (err) {
                console.error("Failed to fetch Ollama models:", err);
            }

            const offlineText = activeLang === 'fr' ? " (Simulé / Hors ligne)" : " (Simulated / Offline)";
            const standardModels = [
                { value: "llama3", label: "Llama 3" },
                { value: "llama3.1", label: "Llama 3.1" },
                { value: "gemma2", label: "Gemma 2" },
                { value: "mistral", label: "Mistral" },
                { value: "phi3", label: "Phi 3" }
            ];

            standardModels.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.value;
                opt.textContent = m.label + offlineText;
                selectEl.appendChild(opt);
            });

            selectEl.value = activeModel;
        }

        // MODAL MANAGEMENT: SETTINGS
        async function openSettingsModal() {
            document.getElementById('settings-title-input').value = projectData.settings.title;
            document.getElementById('settings-goal-input').value = projectData.settings.overall_goal;
            document.getElementById('settings-lock-input').checked = !!projectData.settings.locked;

            // Set Layout/Typography values
            if (!projectData.settings.editor_layout) {
                projectData.settings.editor_layout = {
                    font_family: "Georgia, serif",
                    font_size: "12pt",
                    line_spacing: "1.6",
                    text_align: "left"
                };
            }
            const layout = projectData.settings.editor_layout;
            document.getElementById('settings-layout-font').value = layout.font_family || "Georgia, serif";
            document.getElementById('settings-layout-size').value = layout.font_size || "12pt";
            document.getElementById('settings-layout-spacing').value = layout.line_spacing || "1.6";
            document.getElementById('settings-layout-align').value = layout.text_align || "left";

            // Set AI values
            const aiTemp = (projectData.settings.ai_temperature !== undefined) ? projectData.settings.ai_temperature : 0.7;
            document.getElementById('settings-ai-temp-input').value = aiTemp;
            document.getElementById('settings-ai-temp-display').innerText = parseFloat(aiTemp).toFixed(1);

            await populateOllamaModels();

            document.getElementById('settings-ai-context-input').checked = (projectData.settings.inject_lore_context !== undefined) ? !!projectData.settings.inject_lore_context : true;

            document.getElementById('settings-modal').classList.remove('hidden');
        }

        // CLOSE NOVEL SETTINGS MODAL
        function closeSettingsModal() {
            document.getElementById('settings-modal').classList.add('hidden');
        }

        // SAVE NOVEL SETTINGS
        async function saveProjectSettings() {
            const oldTitle = projectData.settings.title;
            const newTitle = document.getElementById('settings-title-input').value.trim();
            projectData.settings.title = newTitle || oldTitle;
            projectData.settings.overall_goal = parseInt(document.getElementById('settings-goal-input').value) || 50000;
            projectData.settings.locked = document.getElementById('settings-lock-input').checked;

            // Read Layout/Typography values
            if (!projectData.settings.editor_layout) {
                projectData.settings.editor_layout = {};
            }
            projectData.settings.editor_layout.font_family = document.getElementById('settings-layout-font').value;
            projectData.settings.editor_layout.font_size = document.getElementById('settings-layout-size').value;
            projectData.settings.editor_layout.line_spacing = document.getElementById('settings-layout-spacing').value;
            projectData.settings.editor_layout.text_align = document.getElementById('settings-layout-align').value;

            // Read AI values
            projectData.settings.ai_temperature = parseFloat(document.getElementById('settings-ai-temp-input').value);
            projectData.settings.ai_model = document.getElementById('settings-ai-model-input').value.trim() || "llama3";
            projectData.settings.inject_lore_context = document.getElementById('settings-ai-context-input').checked;

            closeSettingsModal();
            renderTree();
            applyEditorLayoutSettings();
            updateRightSidebar();
            await persistProject();

            // Apply locking restrictions frontend
            applyLockState();

            // Reload list to update titles in selector
            await loadProjectsList();
        }

        // DELETE CURRENT NOVEL
        async function deleteCurrentProject() {
            const confirmMsg = translations["confirm_delete_novel"] || "Are you sure you want to permanently delete this novel?";
            if (!confirm(confirmMsg)) return;

            const select = document.getElementById('project-select');
            const filename = select.value;

            try {
                const res = await fetch('/api/projects/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename })
                });

                if (res.ok) {
                    closeSettingsModal();
                    activeNodeId = null;
                    activeNodeType = null;
                    await loadProjectsList();
                    await loadProject();
                } else {
                    alert("Failed to delete project.");
                }
            } catch (err) {
                console.error("Error deleting project:", err);
            }
        }

        // MODAL MANAGEMENT: ABOUT
        function openAboutModal() {
            document.getElementById('about-modal').classList.remove('hidden');
        }
        function closeAboutModal() {
            document.getElementById('about-modal').classList.add('hidden');
        }

        // --- RELECTURE MODAL CONTROL LOGIC ---
        let activeRelectureCategory = "repetitions";
        let activeRelectureScope = "scene";

        function openRelectureModal() {
            if (!activeNodeId || activeNodeType !== "scene") {
                alert(activeLang === 'fr' ? "Veuillez sélectionner une scène du manuscrit pour ouvrir l'Atelier de Relecture." : "Please select a manuscript scene to open the Proofreading Workshop.");
                return;
            }

            // Show modal
            document.getElementById('relecture-modal').classList.remove('hidden');

            // Set active scene title
            const activeNode = findNodeById(activeNodeId);
            document.getElementById('relecture-active-scene-title').innerText = activeNode ? activeNode.title : "-";

            // Default scope and category
            activeRelectureScope = "scene";
            document.getElementById('relecture-scope-select').value = "scene";
            selectRelectureCategory('repetitions');

            // Run stats and repetitions calculations
            updateRelectureStatsAndPanes();
        }

        function closeRelectureModal() {
            document.getElementById('relecture-modal').classList.add('hidden');
        }

        function changeRelectureScope(scope) {
            activeRelectureScope = scope;
            // Hide synonym list when scope changes
            const container = document.getElementById('relecture-repetition-synonyms-container');
            if (container) container.classList.add('hidden');
            updateRelectureStatsAndPanes();
        }

        function getChapterText() {
            const chapter = findParentChapter(activeNodeId);
            if (!chapter || !chapter.children) return "";
            return chapter.children.map(scene => scene.content || "").join("\n\n");
        }
        // POMODORO TIMER MANAGEMENT
        function onTimerSlider(val) {
            timerDurationMinutes = val;
            timerSecondsLeft = val * 60;
            updateTimerDisplay();
        }

        function updateTimerDisplay() {
            const mins = Math.floor(timerSecondsLeft / 60);
            const secs = timerSecondsLeft % 60;
            document.getElementById('timer-display').innerText =
                `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }

        function toggleTimer() {
            const startBtn = document.getElementById('timer-start-btn');

            if (timerIsRunning) {
                // Pause timer
                clearInterval(timerIntervalId);
                timerIsRunning = false;
                startBtn.innerText = translations["start"] || "Start";
                startBtn.className = "flex-1 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold py-1.5 px-2 rounded-lg shadow-sm transition-all";
            } else {
                // Start timer
                timerIsRunning = true;
                startBtn.innerText = translations["pause"] || "Pause";
                startBtn.className = "flex-1 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold py-1.5 px-2 rounded-lg shadow-sm transition-all";

                timerIntervalId = setInterval(() => {
                    if (timerSecondsLeft > 0) {
                        timerSecondsLeft--;
                        updateTimerDisplay();
                    } else {
                        // Timer completed!
                        clearInterval(timerIntervalId);
                        timerIsRunning = false;
                        startBtn.innerText = translations["start"] || "Start";
                        startBtn.className = "flex-1 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold py-1.5 px-2 rounded-lg shadow-sm transition-all";
                        alert("Focus session completed! Take a short break! ☕");
                        resetTimer();
                    }
                }, 1000);
            }
        }

        function resetTimer() {
            clearInterval(timerIntervalId);
            timerIsRunning = false;
            timerSecondsLeft = timerDurationMinutes * 60;
            updateTimerDisplay();

            const startBtn = document.getElementById('timer-start-btn');
            startBtn.innerText = translations["start"] || "Start";
            startBtn.className = "flex-1 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold py-1.5 px-2 rounded-lg shadow-sm transition-all";
        }


        // PLOT GRID DYNAMIC RENDERING
        let currentEditingCard = null;

        function getScenesList() {
            const scenes = [];
            projectData.manuscript.forEach(chap => {
                chap.children.forEach(scene => {
                    scenes.push(scene);
                });
            });
            return scenes;
        }

        function renderPlotGrid() {
            const scenes = getScenesList();

            // Build headers (Column 1 is the Title Corner, then all Scenes)
            const headersRow = document.getElementById('plot-grid-headers');
            headersRow.innerHTML = `
                <th class="p-4 border border-slate-200/80 text-left bg-slate-100 font-bold text-slate-500 text-xs w-48" data-i18n="plot_lanes_scenes">Intrigues / Scènes</th>
                ${scenes.map(scene => `
                    <th class="p-4 border border-slate-200/80 text-center bg-teal-50 text-teal-950 font-bold text-xs min-w-[180px] max-w-[200px]">
                        <div class="truncate" title="${scene.title}">${scene.title}</div>
                    </th>
                `).join('')}
            `;

            // Build body rows for each plotline
            const body = document.getElementById('plot-grid-body');
            body.innerHTML = "";

            projectData.plot.plotlines.forEach(plotline => {
                const tr = document.createElement('tr');

                // Plotline Title Cell
                let tdHtml = `
                    <td class="p-4 border border-slate-200/80 bg-purple-50/40 font-bold text-purple-950 text-sm align-middle">
                        <div class="font-georgia italic">${plotline.title}</div>
                    </td>
                `;

                // Render cell for each scene
                scenes.forEach(scene => {
                    const card = projectData.plot.cards.find(c => c.plotline_id === plotline.id && c.scene_id === scene.id);
                    const isLocked = !!(projectData && projectData.settings && projectData.settings.locked);

                    if (card) {
                        card.characters = card.characters || [];
                        let charactersHtml = "";
                        if (card.characters.length > 0) {
                            charactersHtml = `
                                <div class="flex flex-wrap gap-1 mt-1.5 pt-1 border-t border-indigo-100/40">
                                    ${card.characters.map(charId => {
                                        const ch = projectData.characters.find(c => c.id === charId);
                                        if (!ch) return "";
                                        return `
                                            <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-teal-50 text-teal-800 border border-teal-100 max-w-[150px] truncate" title="${ch.name}">
                                                👤 ${ch.name}
                                            </span>
                                        `;
                                    }).join('')}
                                </div>
                            `;
                        }

                        tdHtml += `
                            <td class="p-3 border border-slate-200/80 align-top max-w-[200px]">
                                <div onclick="openPlotCardModal('${card.id}')" data-card-id="${card.id}" class="bg-indigo-50/50 hover:bg-indigo-50 border border-indigo-200 rounded-lg p-2.5 min-h-[96px] h-auto flex flex-col justify-between cursor-pointer shadow-xs transition-all select-none">
                                    <div>
                                        <div class="text-xs font-bold text-indigo-900 truncate mb-1" title="${card.title}">${card.title}</div>
                                        <div class="text-[11px] text-slate-500 line-clamp-3 leading-tight overflow-hidden">${card.content || "..."}</div>
                                    </div>
                                    ${charactersHtml}
                                </div>
                            </td>
                        `;
                    } else {
                        if (isLocked) {
                            tdHtml += `
                                <td class="p-3 border border-slate-200/80 align-middle max-w-[200px]">
                                    <div class="text-center text-slate-300 text-xs py-3">—</div>
                                </td>
                            `;
                        } else {
                            tdHtml += `
                                <td class="p-3 border border-slate-200/80 align-middle max-w-[200px]">
                                    <button onclick="addPlotCard('${plotline.id}', '${scene.id}')" class="w-full py-3 hover:bg-slate-50 border border-dashed border-slate-200 hover:border-slate-300 rounded-lg text-slate-400 hover:text-slate-600 text-xs font-medium transition-all" data-i18n="add_plot_card">
                                        + Ajouter carte
                                    </button>
                                </td>
                            `;
                        }
                    }
                });

                tr.innerHTML = tdHtml;
                body.appendChild(tr);
            });

            translateDOM();

            // Connect cards visually
            setTimeout(drawPlotConnections, 60);

            // Listen to grid scrolling or resizing to redraw connections
            const container = document.getElementById('plot-grid-table-container');
            if (container && !container.dataset.hasScrollListener) {
                container.dataset.hasScrollListener = "true";
                container.addEventListener('scroll', () => {
                    drawPlotConnections();
                });
                window.addEventListener('resize', () => {
                    if (activeNodeType === "plot_grid") {
                        drawPlotConnections();
                    }
                });
            }
        }

        function drawPlotConnections() {
            const canvas = document.getElementById('plot-grid-svg-canvas');
            const container = document.getElementById('plot-grid-table-container');
            if (!canvas || !container || activeNodeType !== "plot_grid" || activePlotSubView !== "grid") return;

            // Clear canvas
            canvas.innerHTML = "";

            // Ensure canvas dimensions match container scroll area
            const scrollWidth = container.scrollWidth;
            const scrollHeight = container.scrollHeight;
            canvas.setAttribute("width", scrollWidth);
            canvas.setAttribute("height", scrollHeight);
            canvas.style.width = scrollWidth + "px";
            canvas.style.height = scrollHeight + "px";

            const containerRect = container.getBoundingClientRect();

            // Setup marker definitions for arrowheads
            const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
            defs.innerHTML = `
                <marker id="arrow" viewBox="0 0 10 10" refX="15" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#6366f1" />
                </marker>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#6366f1" flood-opacity="0.3" />
                </filter>
            `;
            canvas.appendChild(defs);

            const renderedCards = projectData.plot.cards || [];
            renderedCards.forEach(card => {
                const cardEl = container.querySelector(`[data-card-id="${card.id}"]`);
                if (!cardEl) return;

                const links = card.links || [];
                links.forEach(linkId => {
                    const targetCard = renderedCards.find(c => c.id === linkId);
                    if (!targetCard) return;

                    const targetEl = container.querySelector(`[data-card-id="${linkId}"]`);
                    if (!targetEl) return;

                    // Get positions relative to canvas/container
                    const rectA = cardEl.getBoundingClientRect();
                    const rectB = targetEl.getBoundingClientRect();

                    const x1 = rectA.left - containerRect.left + container.scrollLeft + rectA.width / 2;
                    const y1 = rectA.top - containerRect.top + container.scrollTop + rectA.height / 2;

                    const x2 = rectB.left - containerRect.left + container.scrollLeft + rectB.width / 2;
                    const y2 = rectB.top - containerRect.top + container.scrollTop + rectB.height / 2;

                    // Draw Bezier path
                    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

                    // Simple cubic bezier curve
                    const dx = Math.abs(x2 - x1);
                    const controlX1 = x1 + dx * 0.4 * (x2 > x1 ? 1 : -1);
                    const controlY1 = y1;
                    const controlX2 = x2 - dx * 0.4 * (x2 > x1 ? 1 : -1);
                    const controlY2 = y2;

                    const d = `M ${x1} ${y1} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${x2} ${y2}`;

                    path.setAttribute("d", d);
                    path.setAttribute("fill", "none");
                    path.setAttribute("stroke", "#6366f1");
                    path.setAttribute("stroke-width", "2");
                    path.setAttribute("stroke-dasharray", "4 4"); // dashed lines look beautiful and clean
                    path.setAttribute("marker-end", "url(#arrow)");
                    path.setAttribute("filter", "url(#glow)");
                    path.setAttribute("opacity", "0.75");

                    canvas.appendChild(path);
                });
            });
        }

        // SUB-VIEWS TOGGLING & TIMELINE RENDERING
        function setPlotSubView(subview) {
            activePlotSubView = subview;
            const gridTab = document.getElementById('plot-view-grid-tab');
            const timelineTab = document.getElementById('plot-view-timeline-tab');
            const gridContainer = document.getElementById('plot-grid-table-container');
            const timelineContainer = document.getElementById('plot-grid-timeline-container');

            if (subview === 'grid') {
                gridTab.classList.add('bg-white', 'text-slate-800', 'shadow-xs');
                gridTab.classList.remove('text-slate-600');
                timelineTab.classList.remove('bg-white', 'text-slate-800', 'shadow-xs');
                timelineTab.classList.add('text-slate-600');

                gridContainer.classList.remove('hidden');
                timelineContainer.classList.add('hidden');

                renderPlotGrid();
            } else {
                timelineTab.classList.add('bg-white', 'text-slate-800', 'shadow-xs');
                timelineTab.classList.remove('text-slate-600');
                gridTab.classList.remove('bg-white', 'text-slate-800', 'shadow-xs');
                gridTab.classList.add('text-slate-600');

                gridContainer.classList.add('hidden');
                timelineContainer.classList.remove('hidden');

                renderPlotTimeline();
            }
        }

        function refreshPlotView() {
            if (activePlotSubView === "grid") {
                renderPlotGrid();
            } else {
                renderPlotTimeline();
            }
        }

        function renderPlotTimeline() {
            const flowContainer = document.getElementById('plot-timeline-flow');
            if (!flowContainer) return;

            flowContainer.innerHTML = "";

            const scenes = getScenesList();
            if (scenes.length === 0) {
                flowContainer.innerHTML = `
                    <div class="flex flex-col items-center justify-center p-12 bg-white rounded-xl border border-slate-200 text-center mx-auto">
                        <span class="text-4xl mb-2">📜</span>
                        <div class="text-slate-500 font-semibold" data-i18n="no_scenes_yet">Aucune scène disponible. Créez des chapitres et des scènes pour commencer !</div>
                    </div>
                `;
                return;
            }

            scenes.forEach((scene, index) => {
                const sceneCol = document.createElement('div');
                sceneCol.className = "flex flex-col items-center shrink-0 w-52";

                // 1. Scene header node (positioned at the top)
                let sceneHeaderHtml = `
                    <div class="px-4 py-2.5 bg-teal-600 text-white rounded-xl shadow-md text-xs font-bold text-center w-52 border border-teal-500/20 relative">
                        <div class="uppercase tracking-wider opacity-75">${activeLang === 'fr' ? 'Scène' : 'Scene'} ${index + 1}</div>
                        <div class="truncate text-sm font-georgia mt-0.5" title="${scene.title}">${scene.title}</div>
                        <div class="absolute -bottom-3 left-1/2 transform -translate-x-1/2 bg-teal-600 text-white border-2 border-slate-100 rounded-full w-6 h-6 flex items-center justify-center text-[10px] font-bold shadow-xs">↓</div>
                    </div>
                    <div class="w-0.5 h-10 bg-teal-300"></div>
                `;

                // 2. Stack of connected cards below the scene
                const cardsInScene = projectData.plot.cards.filter(c => c.scene_id === scene.id);
                let cardsStackHtml = `<div class="space-y-4 w-52">`;

                if (cardsInScene.length === 0) {
                    cardsStackHtml += `
                        <div class="bg-white border border-dashed border-slate-200 text-slate-400 rounded-xl p-4 text-center text-xs italic">
                            ${activeLang === 'fr' ? 'Aucune carte.' : 'No cards.'}
                        </div>
                    `;
                } else {
                    cardsInScene.forEach(card => {
                        const plotline = projectData.plot.plotlines.find(p => p.id === card.plotline_id);
                        const plotlineTitle = plotline ? plotline.title : '';

                        // Render characters
                        let charactersHtml = "";
                        card.characters = card.characters || [];
                        if (card.characters.length > 0) {
                            charactersHtml = `
                                <div class="flex flex-wrap gap-1 mt-2 pt-1.5 border-t border-slate-100/80">
                                    ${card.characters.map(charId => {
                                        const ch = projectData.characters.find(c => c.id === charId);
                                        if (!ch) return "";
                                        return `
                                            <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-teal-50 text-teal-800 border border-teal-100 max-w-[150px] truncate" title="${ch.name}">
                                                👤 ${ch.name}
                                            </span>
                                        `;
                                    }).join('')}
                                </div>
                            `;
                        }

                        cardsStackHtml += `
                            <div onclick="openPlotCardModal('${card.id}')" data-timeline-card-id="${card.id}" class="bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-xl p-3 shadow-xs hover:shadow-md cursor-pointer transition-all flex flex-col justify-between min-h-[96px] h-auto relative group select-none">
                                <div>
                                    <div class="text-[9px] uppercase font-bold tracking-wider text-purple-600 mb-1">${plotlineTitle}</div>
                                    <div class="text-xs font-bold text-slate-800 line-clamp-2 mb-1 group-hover:text-indigo-600" title="${card.title}">${card.title}</div>
                                    <div class="text-[10px] text-slate-500 line-clamp-3 leading-snug overflow-hidden">${card.content || "..."}</div>
                                </div>
                                ${charactersHtml}
                            </div>
                        `;
                    });
                }

                cardsStackHtml += `</div>`;

                sceneCol.innerHTML = sceneHeaderHtml + cardsStackHtml;
                flowContainer.appendChild(sceneCol);
            });

            // Translate newly loaded DOM strings
            translateDOM();

            // Connect cards visually on the timeline view
            setTimeout(drawTimelineConnections, 60);

            // Connect scroll and resize listeners
            const timelineContainer = document.getElementById('plot-grid-timeline-container');
            if (timelineContainer && !timelineContainer.dataset.hasScrollListener) {
                timelineContainer.dataset.hasScrollListener = "true";
                timelineContainer.addEventListener('scroll', () => {
                    drawTimelineConnections();
                });
                window.addEventListener('resize', () => {
                    if (activeNodeType === "plot_grid" && activePlotSubView === "timeline") {
                        drawTimelineConnections();
                    }
                });
            }
        }

        function drawTimelineConnections() {
            const canvas = document.getElementById('plot-timeline-svg-canvas');
            const container = document.getElementById('plot-grid-timeline-container');
            if (!canvas || !container || activeNodeType !== "plot_grid" || activePlotSubView !== "timeline") return;

            // Clear canvas
            canvas.innerHTML = "";

            // Ensure canvas dimensions match scroll area
            const scrollWidth = container.scrollWidth;
            const scrollHeight = container.scrollHeight;
            canvas.setAttribute("width", scrollWidth);
            canvas.setAttribute("height", scrollHeight);
            canvas.style.width = scrollWidth + "px";
            canvas.style.height = scrollHeight + "px";

            const containerRect = container.getBoundingClientRect();

            // Marker definition
            const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
            defs.innerHTML = `
                <marker id="timeline-arrow" viewBox="0 0 10 10" refX="15" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#6366f1" />
                </marker>
                <filter id="timeline-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#6366f1" flood-opacity="0.3" />
                </filter>
            `;
            canvas.appendChild(defs);

            const cards = projectData.plot.cards || [];
            cards.forEach(card => {
                const cardEl = container.querySelector(`[data-timeline-card-id="${card.id}"]`);
                if (!cardEl) return;

                const links = card.links || [];
                links.forEach(linkId => {
                    const targetCard = cards.find(c => c.id === linkId);
                    if (!targetCard) return;

                    const targetEl = container.querySelector(`[data-timeline-card-id="${linkId}"]`);
                    if (!targetEl) return;

                    // Get coordinates
                    const rectA = cardEl.getBoundingClientRect();
                    const rectB = targetEl.getBoundingClientRect();

                    const x1 = rectA.left - containerRect.left + container.scrollLeft + rectA.width / 2;
                    const y1 = rectA.top - containerRect.top + container.scrollTop + rectA.height / 2;

                    const x2 = rectB.left - containerRect.left + container.scrollLeft + rectB.width / 2;
                    const y2 = rectB.top - containerRect.top + container.scrollTop + rectB.height / 2;

                    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

                    // Simple cubic bezier curve
                    const dx = Math.abs(x2 - x1);
                    const controlX1 = x1 + dx * 0.4 * (x2 > x1 ? 1 : -1);
                    const controlY1 = y1;
                    const controlX2 = x2 - dx * 0.4 * (x2 > x1 ? 1 : -1);
                    const controlY2 = y2;

                    const d = `M ${x1} ${y1} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${x2} ${y2}`;

                    path.setAttribute("d", d);
                    path.setAttribute("fill", "none");
                    path.setAttribute("stroke", "#6366f1");
                    path.setAttribute("stroke-width", "2");
                    path.setAttribute("stroke-dasharray", "4 4");
                    path.setAttribute("marker-end", "url(#timeline-arrow)");
                    path.setAttribute("filter", "url(#timeline-glow)");
                    path.setAttribute("opacity", "0.75");

                    canvas.appendChild(path);
                });
            });
        }

        // PLOT CARDS INTERACTIONS
        function addPlotCard(plotlineId, sceneId) {
            const cardId = generateId("card");
            const newCard = {
                id: cardId,
                plotline_id: plotlineId,
                scene_id: sceneId,
                title: translations["new_scene_title"] ? `${translations["new_scene_title"]} Card` : "New Card",
                content: ""
            };
            projectData.plot.cards.push(newCard);
            refreshPlotView();
            openPlotCardModal(cardId);
        }

        function openPlotCardModal(cardId) {
            const card = projectData.plot.cards.find(c => c.id === cardId);
            if (!card) return;

            // Initialize fields defensively
            card.characters = card.characters || [];
            card.links = card.links || [];

            const isLocked = !!(projectData && projectData.settings && projectData.settings.locked);
            document.getElementById('plot-card-title-input').disabled = isLocked;
            document.getElementById('plot-card-desc-input').disabled = isLocked;

            const selectEl = document.getElementById('plot-card-connections-select');
            const addConnectionBtn = document.getElementById('plot-card-add-connection-btn');
            if (selectEl) selectEl.disabled = isLocked;
            if (addConnectionBtn) addConnectionBtn.style.display = isLocked ? 'none' : 'block';

            const saveBtn = document.querySelector('[onclick="savePlotCard()"]');
            if (saveBtn) saveBtn.style.display = isLocked ? 'none' : 'block';

            const deleteBtn = document.querySelector('[onclick="deletePlotCard()"]');
            if (deleteBtn) deleteBtn.style.display = isLocked ? 'none' : 'block';

            currentEditingCard = card;
            document.getElementById('plot-card-title-input').value = card.title;
            document.getElementById('plot-card-desc-input').value = card.content || "";

            // Populate characters and connections in the UI
            renderPlotCardModalCharacters();
            renderPlotCardModalConnections();

            document.getElementById('plot-card-modal').classList.remove('hidden');
        }

        function renderPlotCardModalCharacters() {
            const container = document.getElementById('plot-card-characters-container');
            if (!container) return;
            container.innerHTML = "";

            const isLocked = !!(projectData && projectData.settings && projectData.settings.locked);
            const chars = projectData.characters || [];
            if (chars.length === 0) {
                container.innerHTML = `<span class="text-slate-400 italic" data-i18n="no_characters_yet">${translations["no_characters_yet"] || "Aucun personnage créé"}</span>`;
                return;
            }

            chars.forEach(char => {
                const isSelected = currentEditingCard.characters.includes(char.id);
                const badge = document.createElement('div');
                badge.className = `px-2.5 py-1 rounded-full border cursor-pointer font-semibold transition-all flex items-center space-x-1 ${
                    isSelected
                    ? "bg-teal-50 text-teal-700 border-teal-300 hover:bg-teal-100"
                    : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100"
                }`;
                badge.innerHTML = `
                    <span>👤</span>
                    <span>${char.name}</span>
                `;
                if (!isLocked) {
                    badge.onclick = () => {
                        if (isSelected) {
                            currentEditingCard.characters = currentEditingCard.characters.filter(id => id !== char.id);
                        } else {
                            currentEditingCard.characters.push(char.id);
                        }
                        renderPlotCardModalCharacters();
                    };
                }
                container.appendChild(badge);
            });
        }

        function renderPlotCardModalConnections() {
            const selectEl = document.getElementById('plot-card-connections-select');
            const container = document.getElementById('plot-card-connections-container');
            if (!selectEl || !container) return;

            selectEl.innerHTML = "";
            container.innerHTML = "";

            const isLocked = !!(projectData && projectData.settings && projectData.settings.locked);

            // Populate SELECT element with OTHER cards
            const otherCards = (projectData.plot.cards || []).filter(c => c.id !== currentEditingCard.id);
            if (otherCards.length === 0) {
                const opt = document.createElement('option');
                opt.value = "";
                opt.textContent = translations["no_cards_yet"] || "Aucune autre carte d'intrigue";
                selectEl.appendChild(opt);
            } else {
                // Add placeholder option
                const optPlaceholder = document.createElement('option');
                optPlaceholder.value = "";
                optPlaceholder.textContent = translations["link_select_placeholder"] || "Sélectionner une carte...";
                selectEl.appendChild(optPlaceholder);

                otherCards.forEach(c => {
                    // Do not suggest cards already connected
                    if (!currentEditingCard.links.includes(c.id)) {
                        const opt = document.createElement('option');
                        opt.value = c.id;
                        // Find plotline name and scene title for clean description
                        const pl = projectData.plot.plotlines.find(p => p.id === c.plotline_id);
                        const sc = getScenesList().find(s => s.id === c.scene_id);
                        const suffix = `${pl ? pl.title : ''} - ${sc ? sc.title : ''}`;
                        opt.textContent = `${c.title} (${suffix})`;
                        selectEl.appendChild(opt);
                    }
                });
            }

            // Populate CURRENT links
            if (currentEditingCard.links.length === 0) {
                container.innerHTML = `<span class="text-slate-400 italic text-[11px]">${activeLang === 'fr' ? 'Aucune connexion active.' : 'No active connections.'}</span>`;
                return;
            }

            currentEditingCard.links.forEach(linkId => {
                const connectedCard = projectData.plot.cards.find(c => c.id === linkId);
                if (!connectedCard) return;

                const badge = document.createElement('div');
                badge.className = "px-2.5 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg flex items-center space-x-1 font-semibold";

                const pl = projectData.plot.plotlines.find(p => p.id === connectedCard.plotline_id);
                const plTitle = pl ? pl.title : '';

                badge.innerHTML = `
                    <span class="truncate max-w-[120px]" title="${connectedCard.title}">${connectedCard.title} [${plTitle}]</span>
                    ${!isLocked ? `
                        <button onclick="removeCardLink('${linkId}')" class="text-indigo-400 hover:text-indigo-600 font-bold ml-1 hover:bg-indigo-100 rounded-full w-4 h-4 flex items-center justify-center transition-colors">
                            &times;
                        </button>
                    ` : ""}
                `;
                container.appendChild(badge);
            });
        }

        function addCardLinkFromModal() {
            const selectEl = document.getElementById('plot-card-connections-select');
            if (!selectEl || !currentEditingCard) return;

            const targetCardId = selectEl.value;
            if (!targetCardId) return;

            currentEditingCard.links = currentEditingCard.links || [];
            if (!currentEditingCard.links.includes(targetCardId)) {
                currentEditingCard.links.push(targetCardId);
            }

            renderPlotCardModalConnections();
        }

        function removeCardLink(targetCardId) {
            if (!currentEditingCard) return;
            currentEditingCard.links = (currentEditingCard.links || []).filter(id => id !== targetCardId);
            renderPlotCardModalConnections();
        }

        function closePlotCardModal() {
            document.getElementById('plot-card-modal').classList.add('hidden');
            currentEditingCard = null;
        }

        function savePlotCard() {
            if (currentEditingCard) {
                currentEditingCard.title = document.getElementById('plot-card-title-input').value;
                currentEditingCard.content = document.getElementById('plot-card-desc-input').value;
                closePlotCardModal();
                refreshPlotView();
                persistProject();
            }
        }

        function deletePlotCard() {
            if (currentEditingCard) {
                projectData.plot.cards = projectData.plot.cards.filter(c => c.id !== currentEditingCard.id);
                closePlotCardModal();
                refreshPlotView();
                persistProject();
            }
        }
        // Right Sidebar Resizer Logic
        (function() {
            const rightSidebar = document.getElementById('right-sidebar');
            const resizeHandle = document.getElementById('sidebar-resize-handle');
            let isResizing = false;

            // Load saved sidebar width
            const savedWidth = localStorage.getItem('right-sidebar-width');
            if (savedWidth) {
                rightSidebar.style.width = savedWidth + 'px';
            }

            resizeHandle.addEventListener('mousedown', (e) => {
                isResizing = true;
                document.body.classList.add('select-none');
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                const newWidth = window.innerWidth - e.clientX;
                // Enforce constraints: min 240px, max 700px
                if (newWidth >= 240 && newWidth <= 700) {
                    rightSidebar.style.width = newWidth + 'px';
                    localStorage.setItem('right-sidebar-width', newWidth);
                }
            });

            document.addEventListener('mouseup', () => {
                if (isResizing) {
                    isResizing = false;
                    document.body.classList.remove('select-none');
                }
            });
        })();
