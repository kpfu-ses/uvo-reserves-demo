import json
import os

from app import app


def read_coords(filepath):
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filepath), 'r') as f:
        data = f.read().replace('\n', '')
    return json.loads(data)
