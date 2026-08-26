from flask import Flask
import os
import threading

app = Flask(__name__)

if __name__ == "__main__":
    if not os.environ.get("BROWSER_OPENED"):
        os.environ["BROWSER_OPENED"] = "1"
        print("Opening browser!")
    else:
        print("Browser already opened!")

    app.run(port=5001, debug=True)
