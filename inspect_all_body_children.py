import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def inspect_all_body_children():
    flask_proc = subprocess.Popen([sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:5000")
        time.sleep(2)

        children = page.evaluate("""() => {
            const getStructure = (node) => {
                return {
                    tagName: node.tagName,
                    id: node.id,
                    className: node.className,
                    children: Array.from(node.children).map(getStructure)
                };
            };
            return getStructure(document.body);
        }""")
        import json
        print(json.dumps(children, indent=2))

        browser.close()

    flask_proc.terminate()
    flask_proc.wait()

if __name__ == "__main__":
    inspect_all_body_children()
