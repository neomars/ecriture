with open('static/js/linguistique.js', 'r') as f:
    content = f.read()

search = """            } else if (type === 'annotation') {
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const selectedText = range.toString();
                    if (selectedText.length > 0) {
                        const span = document.createElement('span');
                        span.className = 'annotation-highlight border-b-2 border-dashed border-indigo-500 cursor-help relative inline';
                        const defaultText = activeLang === 'fr' ? "Saisissez votre note d'annotation ici..." : "Enter your annotation note here...";
                        span.setAttribute('data-annotation', defaultText);
                        span.setAttribute('data-annotation-id', 'anno-' + Date.now() + '-' + Math.floor(Math.random() * 1000));
                        span.appendChild(document.createTextNode(selectedText));

                        range.deleteContents();
                        range.insertNode(span);"""

replace = """            } else if (type === 'annotation') {
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const selectedText = range.toString();
                    if (selectedText.length > 0) {
                        const span = document.createElement('span');
                        span.className = 'annotation-highlight border-b-2 border-dashed border-indigo-500 cursor-help relative inline';
                        const defaultText = activeLang === 'fr' ? "Saisissez votre note d'annotation ici..." : "Enter your annotation note here...";
                        span.setAttribute('data-annotation', defaultText);
                        span.setAttribute('data-annotation-id', 'anno-' + Date.now() + '-' + Math.floor(Math.random() * 1000));

                        // Use extractContents to preserve HTML elements like <br> and other formatting tags
                        const extracted = range.extractContents();
                        span.appendChild(extracted);

                        range.insertNode(span);"""

if search in content:
    content = content.replace(search, replace)
    with open('static/js/linguistique.js', 'w') as f:
        f.write(content)
    print("Fixed annotation HTML loss issue.")
else:
    print("Search string not found.")
