from pathlib import Path
import json
import lasio
import copy

from flask import current_app


def create_coords_files(wells, run_id, serv_num, well_id_name=False):
    for well in wells:
        if well_id_name:
            well_id = well.core()[0].well_data_id
        else:
            well_id = well.name
        Path(f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}/input_data/coords/{well_id}") \
            .mkdir(parents=True, exist_ok=True)
        for coords in well.coords():
            coords_json = {"Well": coords.well_id, "X": coords.x, "Y": coords.y, "RKB": coords.rkb}
            filename = f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}/input_data/coords/{well_id}/{coords.filepath}"
            with open(filename, 'w') as f:
                json.dump(coords_json, f, indent=4)


def create_strat_files(wells, run_id, serv_num):
    for well in wells:
        well_id = well.core()[0].well_data_id
        Path(f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}/input_data/stratigraphy/{well_id}") \
            .mkdir(parents=True, exist_ok=True)
        for strat in well.strats():
            strat_json = {"Well": strat.well_id, "Lingula_top": strat.lingula_top,
                          "P2ss2_top": strat.p2ss2_top, "P2ss2_bot": strat.p2ss2_bot}
            filename = f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}" \
                       f"/input_data/stratigraphy/{well_id}/{well.name}.json"
            with open(filename, 'w') as f:
                json.dump(strat_json, f, indent=4)


def create_log_files(wells, run_id, serv_num,  well_id_name=False):
    for well in wells:
        if well_id_name:
            well_id = well.core()[0].well_data_id
        else:
            well_id = well.name

        Path(f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}/input_data/wellLogs/{well_id}") \
            .mkdir(parents=True, exist_ok=True)

        filename = f"{current_app.config['SERVICES_PATH']}{serv_num}/{str(run_id)}" \
                   f"/input_data/wellLogs/{well_id}/{well.name}.las"

        las = copy.deepcopy(lasio.LASFile())
        las.well['WELL'].value = well.name
        las.add_curve("DEPT", data=list(well.depth), descr='')
        for crv in well.curves():
            las.add_curve(crv.name, data=list(crv.data), descr='')

        with open(filename, mode='w', encoding='utf-8') as f:
            las.write(f, version=2.0)


