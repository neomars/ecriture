from flask import Flask
import os
app = Flask(__name__)
if __name__ == "__main__":
    print(f"Master/worker? WERKZEUG_RUN_MAIN={os.environ.get('WERKZEUG_RUN_MAIN')} app.debug={app.debug}")
    app.run(port=5001, debug=True)
