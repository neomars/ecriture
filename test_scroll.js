function setupScrollSync() {
    const scrollContainer = document.getElementById('editor-scroll-container');
    if (!scrollContainer) return;

    scrollContainer.addEventListener('scroll', () => {
        // Implement scroll sync logic here
        // Find which scene is currently in the viewport
        const scenes = document.querySelectorAll('.editor-scene-contenteditable');
        let visibleScene = null;

        for (let i = 0; i < scenes.length; i++) {
            const rect = scenes[i].getBoundingClientRect();
            // Check if scene is mostly in view or near the top
            if (rect.top >= 0 && rect.top <= window.innerHeight / 2) {
                visibleScene = scenes[i];
                break;
            } else if (rect.top < 0 && rect.bottom > window.innerHeight / 2) {
                visibleScene = scenes[i];
                break;
            }
        }

        if (visibleScene) {
            const sceneId = visibleScene.getAttribute('data-scene-id');
            if (activeNodeId !== sceneId) {
                activeNodeId = sceneId;
                activeNodeType = 'scene';
                // Update tree visually without re-rendering if possible,
                // but since renderTree exists we can call it (might be heavy on scroll though)
                // renderTree();

                // Optimized tree update:
                const prevActive = document.querySelector('.tree-node.bg-indigo-100');
                if (prevActive) {
                    prevActive.classList.remove('bg-indigo-100', 'text-indigo-900', 'font-semibold');
                    prevActive.classList.add('text-slate-700', 'hover:bg-slate-100');
                }
                const newActive = document.querySelector(`.tree-node[data-id="${sceneId}"]`);
                if (newActive) {
                    newActive.classList.add('bg-indigo-100', 'text-indigo-900', 'font-semibold');
                    newActive.classList.remove('text-slate-700', 'hover:bg-slate-100');
                }
            }
        }
    });
}
