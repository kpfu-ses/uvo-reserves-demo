from flask import Blueprint

bp = Blueprint('run', __name__)

from app.run import routes
