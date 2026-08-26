from flask import Flask
import os
import threading

app = Flask(__name__)

if __name__ == "__main__":
    def open_browser():
        print("OPENING BROWSER!")

    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print(f"Condition true! app.debug={app.debug} WERKZEUG_RUN_MAIN={os.environ.get('WERKZEUG_RUN_MAIN')}")
        threading.Timer(0.1, open_browser).start()

    app.run(port=5001, debug=True)
