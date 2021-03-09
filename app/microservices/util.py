import os
import shutil
from pathlib import Path
import json

from flask import current_app


def create_coords_files(wells, run_id, serv_num, well_id_name=False):
    for well in wells:
        if well_id_name:
            well_id = well.core()[0].well_data_id
        else:
            well_id = well.name
        for coords in well.coords():
            Path(f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}/input_data/coords/{well_id}")\
                .mkdir(parents=True, exist_ok=True)
            coords_json = {"Well": coords.well_id, "X": coords.x, "Y": coords.y, "RKB": coords.rkb}
            filename = f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}/input_data/coords/{well_id}/{coords.filepath}"
            with open(filename, 'w') as f:
                json.dump(coords_json, f, indent=4)


def create_strat_files(wells, run_id, serv_num):
    for well in wells:
        well_id = well.core()[0].well_data_id
        for strat in well.strats():
            Path(
                current_app.config['SERVICES_PATH'] + serv_num + '/' + str(run_id) + '/input_data/stratigraphy/' + well_id).mkdir(
                parents=True, exist_ok=True)
            strat_json = {"Well": strat.well_id, "Lingula_top": strat.lingula_top, "P2ss2_top": strat.p2ss2_top, "P2ss2_bot": strat.p2ss2_bot}
            filename = current_app.config['SERVICES_PATH'] + serv_num + '/' + str(run_id) + \
                       '/input_data/stratigraphy/' + well_id + '/' + well.name + '.json'
            with open(filename, 'w') as f:
                json.dump(strat_json, f, indent=4)
