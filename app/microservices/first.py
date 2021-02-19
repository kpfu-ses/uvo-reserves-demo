import os
import shutil
from pathlib import Path
import json

from flask import current_app

from app import db
from app.helpers.parser import read_strat
from app.models import Stratigraphy
from app.modules.first.Strat_P2ss2 import get_strat


def create_coords_files(wells, run_id):
    for well in wells:
        for coords in well.coords():
            Path(
                current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/input_data/coords/' + well.name).mkdir(
                parents=True, exist_ok=True)
            coords_json = {"Well": coords.well_id, "X": coords.x, "Y": coords.y, "RKB": coords.rkb}
            filename = current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + \
                       '/input_data/coords/' + well.name + '/' + coords.filepath
            with open(filename, 'w') as f:
                json.dump(coords_json, f, indent=4)


def save_strat(wells, run_id):
    for well in wells:
        filepath = current_app.config['SERVICES_PATH'] + \
                   'first/' + str(run_id) + '/output_data/' + well.name + '/stratigraphy.json'
        strat_data = read_strat(filepath)
        strat = Stratigraphy(run_id=run_id, project_id=well.project_id, well_id=well.id,
                             lingula_top=strat_data['Lingula_top'], p2ss2_top=strat_data['P2ss2_top'],
                             p2ss2_bot=strat_data['P2ss2_bot'])
        db.session.add(strat)
        db.session.commit()


def run_first(wells, run_id):
    Path(current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'first/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    create_coords_files(wells, run_id)
    for well in wells:
        for logs in well.logs():
            Path(current_app.config['SERVICES_PATH'] + 'first/' + str(
                run_id) + '/input_data/wellLogs/' + well.name).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], logs.filepath),
                            current_app.config['SERVICES_PATH'] + 'first/' + str(
                                run_id) + '/input_data/wellLogs/' + well.name + '/' + logs.filepath)

    get_strat(run_id)
    save_strat(wells, run_id)
