from flask import Flask

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "top-level"

def create_sub_app():
    @app.route("/", methods=["GET"])
    def index():
        return "nested"
    return index

