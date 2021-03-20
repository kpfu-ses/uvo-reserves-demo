from app import db
from app.microservices.first import run_first
from app.microservices.second import run_second
from app.microservices.third import run_third
from app.microservices.fifth import run_fifth
from app.microservices.sixth import run_sixth
from app.microservices.seventh import run_seventh
from app.models import Well, Logs, Coords, Run, Stratigraphy, Core, User, StructFile, Struct
from app.models import run_well
from flask import current_app
import shutil
from datetime import datetime


def run_services(user_id, wells_ids_str, services, run_id):
    wells_ids = wells_ids_str.split(',')
    wells = Well.query.filter(Well.id.in_(wells_ids)).all()
    for well_id in wells_ids:
        statement = run_well.insert().values(well_id=well_id, run_id=run_id, )
        db.session.execute(statement)

    db.session.commit()
    rep_serv = ''
    if '1' in services:
        wells = run_first(wells, run_id)
        rep_serv = 'first/'

    if '2' in services:
        wells = run_second(wells, run_id)
        if rep_serv == '':
            rep_serv = 'second/'

    if '3' in services:
        wells = run_third(wells, run_id)
        if rep_serv == '':
            rep_serv = 'third/'

    if '5' in services:
        run_fifth(wells, run_id)
        if rep_serv == '':
            rep_serv = 'fifth/'

    if '6' in services:
        run_sixth(run_id)
        if rep_serv == '':
            rep_serv = 'sixth/'

    if '7' in services:
        run_seventh(wells, run_id)
        if rep_serv == '':
            rep_serv = 'seventh/'

    user = User.query.get(user_id)
    user.add_notification('done', len(user.new_runs()))
    db.session.commit()

    # updating run time for notifications
    run = Run.query.filter_by(id=run_id).first()
    run.date = datetime.now()

    # saving report_file
    report_filepath = current_app.config['SERVICES_PATH'] + rep_serv + str(run_id) + '/output_data/Report.txt'
    new_report_filepath = 'report_1_{}_Report.txt'.format(run_id)
    shutil.copyfile(report_filepath, "app/static/" + new_report_filepath)
    run.report_1 = new_report_filepath
    db.session.commit()


def get_wells_list(services_str, run_id):
    run = Run.query.get(run_id)
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
    elif '5' in services:
        result = db.session.query(Well, Stratigraphy, Coords) \
            .filter(Well.project_id == run.project_id) \
            .filter(Stratigraphy.well_id == Well.id) \
            .filter(Coords.well_id == Well.id).distinct(Well.id).all()
        result = [well for well, strat, coords in result]

    if '6' in services:
        surf_top = StructFile.query.filter_by(project_id=run.project_id, type=Struct.SURF_TOP).first()
        if surf_top is None:
            return []
        else:
            surf_bot = StructFile.query.filter_by(project_id=run.project_id, type=Struct.SURF_BOT).first()
            if surf_bot is None:
                return []
            elif len(services) == 1:
                result = Well.query.filter_by(project_id=run.project_id).all()
        if '7' in services:
            result2 = db.session.query(Well, Logs, Coords) \
                .filter(Well.project_id == run.project_id) \
                .filter(Logs.well_id == Well.id) \
                .filter(Coords.well_id == Well.id).distinct(Well.id).all()
            result2 = [well for well, log, coords in result2]
            result = list(set(result2).intersection(result))
    elif '7' in services:
        grid = StructFile.query.filter_by(project_id=run.project_id, type=Struct.GRID).first()
        if grid is None:
            return []
        result2 = db.session.query(Well, Logs, Coords) \
            .filter(Well.project_id == run.project_id) \
            .filter(Logs.well_id == Well.id) \
            .filter(Coords.well_id == Well.id).distinct(Well.id).all()
        result2 = [well for well, log, coords in result2]
        result = list(set(result2).intersection(result)) if len(result) > 0 else result2
    elif '8' in services:
        grid = StructFile.query.filter_by(project_id=run.project_id, type=Struct.GRID_FES).first()
        if grid is None:
            return []
        elif len(services) == 1:
            result = Well.query.filter_by(project_id=run.project_id).all()
    result_wells = [(well.id, well.name) for well in result]
    return result_wells
