from flask import Flask
import os
import threading

app = Flask(__name__)

if __name__ == "__main__":
    def open_browser():
        print("OPENING BROWSER!")

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(0.1, open_browser).start()

    app.run(port=5001, debug=True)
