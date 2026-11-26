"""Flask blueprint routes — API-S3. PATTERN: ROUTE-FLASK-01."""
from flask import Flask, Blueprint
from src.controllers.profile_controller import profile_controller

app = Flask(__name__)
bp = Blueprint("profile", __name__)

@app.route("/api/v1/match", methods=["POST"])
def match_route():
    """Flask match route."""
    return profile_controller()

@bp.route("/api/v1/profile")
def profile_route():
    """Blueprint profile route."""
    return profile_controller()

app.register_blueprint(bp)
