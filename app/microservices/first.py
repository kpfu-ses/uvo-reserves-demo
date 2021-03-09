import os
import shutil
from pathlib import Path

from flask import current_app

from app import db
from app.helpers.parser import read_strat
from app.models import Stratigraphy, Run
from app.modules.first.Strat_P2ss2 import get_strat
from app.microservices.util import create_coords_files


def save_strat(wells, run_id):
    for well in wells:
        filepath = current_app.config['SERVICES_PATH'] + \
                   'first/' + str(run_id) + '/output_data/' + well.name + '/stratigraphy.json'
        strat_data = read_strat(filepath)
        strat = Stratigraphy(run_id=run_id, project_id=well.project_id, well_id=well.id,
                             lingula_top=strat_data['Lingula_top'], p2ss2_top=strat_data['P2ss2_top'],
                             p2ss2_bot=strat_data['P2ss2_bot'])
        db.session.add(strat)

    report_filepath = current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/output_data/Report.txt'
    new_report_filepath = 'report_1_{}_Report.txt'.format(run_id)
    shutil.copyfile(report_filepath, "app/static/" + new_report_filepath)
    run = Run.query.get(run_id)
    run.report_1 = new_report_filepath
    db.session.commit()

def run_first(wells, run_id):
    Path(current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    create_coords_files(wells, run_id, 'first')
    for well in wells:
        for logs in well.logs():
            Path(current_app.config['SERVICES_PATH'] + 'first/' + str(
                run_id) + '/input_data/wellLogs/' + well.name).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], logs.filepath),
                            current_app.config['SERVICES_PATH'] + 'first/' + str(
                                run_id) + '/input_data/wellLogs/' + well.name + '/' + logs.filepath)

    get_strat(run_id)
    save_strat(wells, run_id)
