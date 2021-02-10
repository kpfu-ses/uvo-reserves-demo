import json
import os

from flask import current_app


def read_coords(filepath):
    with open(os.path.join(current_app.config['UPLOAD_FOLDER'], filepath), 'r') as f:
        data = f.read().replace('\n', '')
    return json.loads(data)


def read_strat(filepath):
    with open(filepath, 'r') as f:
        data = f.read().replace('\n', '')
    return json.loads(data)