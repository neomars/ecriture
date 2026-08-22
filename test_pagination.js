function applyPagination() {
    // Clear existing dynamically generated page numbers
    const existing = document.querySelectorAll('.dynamic-page-number');
    existing.forEach(e => e.remove());

    const wrapper = document.getElementById('editor-layout-wrapper');
    if (!wrapper) return;

    // An A4 page roughly has a certain height based on text lines and spacing.
    // We will estimate it using pixels. E.g., 900px
    const PAGE_HEIGHT = 900;

    const totalHeight = wrapper.scrollHeight;
    const numPages = Math.floor(totalHeight / PAGE_HEIGHT);

    for (let i = 1; i <= numPages; i++) {
        const pageIndicator = document.createElement('div');
        pageIndicator.className = 'dynamic-page-number';
        pageIndicator.style.position = 'absolute';
        pageIndicator.style.top = `${i * PAGE_HEIGHT}px`;
        pageIndicator.style.left = '50%';
        pageIndicator.style.transform = 'translateX(-50%)';
        pageIndicator.style.color = '#cbd5e1';
        pageIndicator.style.fontSize = '0.75rem';
        pageIndicator.style.fontStyle = 'italic';
        pageIndicator.style.pointerEvents = 'none';
        pageIndicator.innerText = `Page ${i}`;

        wrapper.appendChild(pageIndicator);
    }
}
