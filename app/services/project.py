from app import db
from app.models import Project
from app.models import projects_users


def save_project(user, project_name):
    project = Project(name=project_name)
    db.session.add(project)
    db.session.flush()

    statement = projects_users.insert().values(user_id=user.id,
                                               project_id=project.id,
                                               access='r')
    db.session.execute(statement)
    db.session.commit()