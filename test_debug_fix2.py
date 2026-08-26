from flask import Flask
import os
import threading

app = Flask(__name__)

if __name__ == "__main__":
    def open_browser():
        print("OPENING BROWSER!")

    # For production vs debug
    # Production (no debug): WERKZEUG_RUN_MAIN is not set, we open browser.
    # Debug (with reloader): WERKZEUG_RUN_MAIN is set in the child process.
    is_debug = os.environ.get("FLASK_DEBUG") == "1" or True # Simulating debug=True below

    # Actually, when using `app.run(debug=True)`, `app.debug` isn't updated until inside `app.run()`.
    # Let's just check WERKZEUG_RUN_MAIN.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("Child process - not opening browser if we only want it once")

    # If we want it only once:
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(0.1, open_browser).start()

    app.run(port=5001, debug=True)
