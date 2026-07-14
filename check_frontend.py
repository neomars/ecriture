import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def run_checks():
    # 1. Start Flask app
    print("Starting Flask server...")
    flask_proc = subprocess.Popen([sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3) # Wait for server to boot

    errors = []
    logs = []

    # 2. Run Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Listen to console messages and errors
        page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(f"Page Error: {err.message}\n{err.stack}"))

        print("Navigating to http://localhost:5000...")
        try:
            page.goto("http://localhost:5000", timeout=10000)
            time.sleep(3) # Wait for SPA initialization and fetch API calls

            # Take screenshot
            page.screenshot(path="check_frontend_screenshot.png")
            print("Screenshot saved to check_frontend_screenshot.png")

        except Exception as e:
            print(f"Exception during navigation: {e}")

        browser.close()

    # 3. Kill Flask app
    flask_proc.terminate()
    flask_proc.wait()

    print("\n--- CONSOLE LOGS ---")
    for log in logs:
        print(log)

    print("\n--- PAGE ERRORS ---")
    if not errors:
        print("None!")
    for err in errors:
        print(err)

if __name__ == "__main__":
    run_checks()
