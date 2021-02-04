from threading import Thread
import os


def save_async_file(file, filename, app):
    with app.app_context():
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))


def save_file(file, filename, app):
    Thread(target=save_async_file, args=(file, filename, app)).start()
