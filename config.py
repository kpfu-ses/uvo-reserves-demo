import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://postgres:7c056266@localhost:5432/uvo_reserves'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None or 1
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'sumbel.enikeeva@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or '7Cc056266;'
    ADMINS = ['sumbel.enikeeva@gmail.com']
    SERVICES_PATH = 'app/modules/'

