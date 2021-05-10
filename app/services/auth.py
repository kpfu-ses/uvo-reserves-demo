from flask import make_response
from flask_jwt_extended import create_access_token, set_access_cookies
from sqlalchemy.exc import IntegrityError

from app.api.errors import bad_request
from app.models import User
from app import db


def login_user(username, password):
    if not username:
        return bad_request('Missing username')
    if not password:
        return bad_request('Missing password')
    user = User.query.filter_by(username=username).first()
    if not user:
        return bad_request('User Not Found!', 404)
    if user.check_password(password):
        access_token = create_access_token(identity={"username": username})
        response = make_response(dict(access_token=access_token), 200)
        set_access_cookies(response, access_token)
        return response
    else:
        return bad_request('Invalid Login Info!')


def register_user(username, email, password):
    try:
        if not username:
            return bad_request('Missing username')
        if not password:
            return bad_request('Missing password')
        if not email:
            return bad_request('Missing email')
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity={"username": username})
        response = make_response(dict(access_token=access_token), 200)
        set_access_cookies(response, access_token)
        return response

    except IntegrityError:
        db.session.rollback()
        return bad_request('User Already Exists')
