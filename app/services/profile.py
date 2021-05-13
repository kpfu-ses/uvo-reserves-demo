from app import db


def edit_profile(user, username, email):
    if username is not None:
        user.username = username
    if email is not None:
        user.email = email
    db.session.commit()
