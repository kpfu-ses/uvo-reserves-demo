from pathlib import Path

from flask import current_app

from app import db
from app.helpers.parser import read_strat
from app.models import Stratigraphy, Run
from app.modules.first.Strat_P2ss2 import get_strat
from app.microservices.util import create_coords_files, create_log_files


def save_strat(wells, run_id):
    wells_done = []
    for well in wells:
        filepath = current_app.config['SERVICES_PATH'] + \
                   'first/' + str(run_id) + '/output_data/' + well.name + '/stratigraphy.json'
        if Path(filepath).is_file():
            wells_done.append(well)

            strat_data = read_strat(filepath)
            strat = Stratigraphy(run_id=run_id, project_id=well.project_id, well_id=well.id,
                                 lingula_top=strat_data['Lingula_top'], p2ss2_top=strat_data['P2ss2_top'],
                                 p2ss2_bot=strat_data['P2ss2_bot'])
            db.session.add(strat)
    db.session.commit()
    return wells_done


def run_first(wells, run_id):
    Path(current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    create_coords_files(wells, run_id, 'first')
    create_log_files(wells, run_id, 'first')
    get_strat(run_id)
    return save_strat(wells, run_id)
