import os


class Config(object):
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_SECURE = True
    CORS_SUPPORTS_CREDENTIALS = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    JWT_SECRET_KEY = 'asgdhasgdhagsdhjkkdlkcl'
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_CSRF_PROTECT = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///sqlite.db'
    # SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://postgres:7c056266@localhost:5432/uvo_reserves'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None or 1
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'sumbel.enikeeva@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or '7Cc056266;'
    ADMINS = ['sumbel.enikeeva@gmail.com']
    SERVICES_PATH = 'app/modules/'
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
