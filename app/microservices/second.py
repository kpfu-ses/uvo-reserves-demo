import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from app import db
from flask import current_app
from app.models import Core, Run, Logs
from app.modules.second.core_shift import get_linking
from app.microservices.util import create_strat_files

regWellName = r"[^0-9]"


def save_results(wells, run_id):
    run = Run.query.get(run_id)
    wells_done = []
    for well in wells:
        well_id = well.core()[0].well_data_id
        # well name without letters
        well_name = re.sub(regWellName, '', well.name.replace(' ', ''))
        # save core
        filepath = f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/output_data/{well_id}/{well_name}"
        if Path(filepath + ".png").is_file():
            wells_done.append(well)
            core_from = Core.query.filter_by(well_id=well.id, ).first()
            core = Core(well_id=core_from.well_id, run_id=run_id, res_filepath=core_from.filepath.split('.')[0] + '.png',
                        well_data_id=core_from.well_data_id, project_id=core_from.project_id, filepath=core_from.filepath)
            shutil.copyfile(filepath + ".png", 'app/static/' + core.res_filepath)
            db.session.add(core)

            # change las-path
            log = Logs.query.filter_by(well_id=core_from.well_id, project_id=run.project_id).first()
            las_path = f"{str(run.project_id)}_logs_{str(datetime.now())}{well_name}.las"
            # shutil.move(filepath + ".las", las_path)
            shutil.copyfile(filepath + ".las", 'uploads/' + las_path)
            log.filepath = las_path

        # db.session.commit()

    # save report file
    report_filepath = f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/output_data/Report.txt"
    new_report_filepath = 'report_2_{}_Report.txt'.format(run_id)
    shutil.copyfile(report_filepath, "app/static/" + new_report_filepath)
    run = Run.query.get(run_id)
    run.report_2 = new_report_filepath

    db.session.commit()
    return wells_done


def run_second(wells, run_id):
    Path(f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/output_data/").mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/output_data/Report.txt").touch(exist_ok=True)
    create_strat_files(wells, run_id, 'second')
    wells_list = []
    for well in wells:
        for logs in well.logs():
            well_id = well.core()[0].well_data_id
            Path(f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/input_data/wellLogs/{well_id}").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], logs.filepath),
                            f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}"
                            f"/input_data/wellLogs/{well_id}/{logs.filepath}")

        for core in well.core():
            wells_list.append(core.well_data_id)
            Path(f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/input_data/wellCore/{core.well_data_id}")\
                .mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], core.filepath),
                            f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}"
                            f"/input_data/wellCore/{core.well_data_id}/{core.well_data_id}.json")

    get_linking(run_id, wells_list)
    return save_results(wells, run_id)
