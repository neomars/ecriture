from flask import Flask
import os
import threading

app = Flask(__name__)

if __name__ == "__main__":
    def open_browser():
        print("OPENING BROWSER!")

    # Fix: Use os.environ.get("WERKZEUG_RUN_MAIN") == "true" to only run once when debug is true
    # Wait, the issue is that without setting app.debug=True before the check, app.debug is False
    # So `not app.debug` is True in the master process, and `WERKZEUG_RUN_MAIN == "true"` is true in the worker process!
    print(f"app.debug={app.debug} WERKZEUG_RUN_MAIN={os.environ.get('WERKZEUG_RUN_MAIN')}")
