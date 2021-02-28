from app import db
from app.microservices.first import run_first
from app.microservices.second import run_second
from app.models import Well, Logs, Coords, Run, Stratigraphy, Core, User
from app.models import run_well
from datetime import datetime


def run_services(user_id, wells_ids_str, services, run_id):
    wells_ids = wells_ids_str.split(',')
    wells = Well.query.filter(Well.id.in_(wells_ids)).all()
    for well_id in wells_ids:
        statement = run_well.insert().values(well_id=well_id, run_id=run_id, )
        db.session.execute(statement)

    db.session.commit()
    if '1' in services:
        run_first(wells, run_id)

    if '2' in services:
        run_second(wells, run_id)

    user = User.query.get(user_id)
    user.add_notification('done', len(user.new_runs()))
    db.session.commit()

    run = Run.query.filter_by(id=run_id).first()
    run.date = datetime.now()
    db.session.commit()


def get_wells_list(services_str, run_id):
    run = Run.query.filter_by(id=run_id).first()
    result = []
    services = services_str.split(',')
    if '1' in services:
        result = db.session.query(Well, Logs, Coords) \
            .filter(Well.project_id == run.project_id) \
            .filter(Logs.well_id == Well.id) \
            .filter(Coords.well_id == Well.id).distinct(Well.id).all()
        result = [well for well, log, coords in result]
        if '2' in services:
            result2 = db.session.query(Well, Core) \
                .filter(Well.project_id == run.project_id) \
                .filter(Core.well_id == Well.id).distinct(Well.id).all()
            result2 = [well for well, core in result2]
            result = list(set(result2).intersection(result))
    elif '2' in services:
        result = db.session.query(Well, Logs, Core, Stratigraphy) \
            .filter(Well.project_id == run.project_id) \
            .filter(Logs.well_id == Well.id) \
            .filter(Core.well_id == Well.id) \
            .filter(Stratigraphy.well_id == Well.id).distinct(Well.id).all()
        result = [well for well, log, core, strat in result]
    elif '3' in services:
        result = db.session.query(Well, Logs, Coords) \
            .filter(Well.project_id == run.project_id) \
            .filter(Logs.well_id == Well.id) \
            .filter(Coords.well_id == Well.id).distinct(Well.id).all()
        result = [well for well, log, coords in result]
    result_wells = [(well.id, well.name) for well in result]
    return result_wells
