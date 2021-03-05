import os
import re
import shutil
from pathlib import Path
import json
from app import db
from flask import current_app
from app.models import Core, Run
from app.modules.second.core_shift import get_linking

regWellName = r"[^0-9]"


def create_strat_files(wells, run_id):
    for well in wells:
        well_id = well.core()[0].well_data_id
        for strat in well.strats():
            Path(
                current_app.config['SERVICES_PATH'] + 'second/' + str(run_id) + '/input_data/stratigraphy/' + well_id).mkdir(
                parents=True, exist_ok=True)
            strat_json = {"Well": strat.well_id, "Lingula_top": strat.lingula_top, "P2ss2_top": strat.p2ss2_top, "P2ss2_bot": strat.p2ss2_bot}
            filename = current_app.config['SERVICES_PATH'] + 'second/' + str(run_id) + \
                       '/input_data/stratigraphy/' + well_id + '/' + well.name + '.json'
            with open(filename, 'w') as f:
                json.dump(strat_json, f, indent=4)


def save_results(wells, run_id):
    for well in wells:
        well_id = well.core()[0].well_data_id
        wellName = re.sub(regWellName, '', well.name.replace(' ', ''))
        filepath = current_app.config['SERVICES_PATH'] + \
                   'second/' + str(run_id) + '/output_data/' + well_id + '/' + wellName + '.png'
        core_from = Core.query.filter_by(well_id=well.id, ).first()
        core = Core(well_id=core_from.well_id, run_id=run_id, res_filepath=core_from.filepath.split('.')[0] + '.png',
                    well_data_id=core_from.well_data_id, project_id=core_from.project_id, filepath=core_from.filepath)
        shutil.copyfile(filepath, 'app/static/' + core.res_filepath)
        db.session.add(core)
        db.session.commit()
    report_filepath = current_app.config['SERVICES_PATH'] + 'second/' + str(run_id) + '/output_data/Report.txt'
    new_report_filepath = 'report_2_{}_Report.txt'.format(run_id)
    shutil.copyfile(report_filepath, new_report_filepath)
    run = Run.query.get(run_id)
    run.report_2 = new_report_filepath
    db.session.commit()


def run_second(wells, run_id):
    Path(current_app.config['SERVICES_PATH'] + 'second/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'second/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    create_strat_files(wells, run_id)
    wells_list = []
    for well in wells:
        for logs in well.logs():
            well_id = well.core()[0].well_data_id
            Path(current_app.config['SERVICES_PATH'] + 'second/' + str(
                run_id) + '/input_data/wellLogs/' + well_id).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], logs.filepath),
                            current_app.config['SERVICES_PATH'] + 'second/' + str(
                                run_id) + '/input_data/wellLogs/' + well_id + '/' + logs.filepath)

        for core in well.core():
            wells_list.append(core.well_data_id)
            Path(current_app.config['SERVICES_PATH'] + 'second/' + str(
                run_id) + '/input_data/wellCore/' + core.well_data_id).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], core.filepath),
                            current_app.config['SERVICES_PATH'] + 'second/' + str(
                                run_id) + '/input_data/wellCore/' + core.well_data_id + '/' + core.well_data_id + '.json')

    get_linking(run_id, wells_list)
    save_results(wells, run_id)
