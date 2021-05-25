import os
import re
import shutil
from pathlib import Path
from app import db
from flask import current_app
import uuid
import simplejson

from app.helpers.LasParser import ImportLasFiles
from app.models import Core, Run, Logs, CoreResults
from app.modules.second.core_shift import get_linking
from app.microservices.util import create_strat_files, create_log_files
from app.helpers.services import add_log

regWellName = r"[^0-9]"


def save_results(wells, run_id, well_crvs):
    run = Run.query.get(run_id)
    wells_done = []
    for well in wells:
        well_id = well.core()[0].well_data_id
        # well name without letters
        well_name = re.sub(regWellName, '', well.name.replace(' ', ''))
        well_data = simplejson.dumps(well_crvs.get(well_name), ignore_nan=True)
        # save core
        core_res = CoreResults(well_id=well.id, run_id=run.id, data=well_data)
        db.session.add(core_res)
        filepath = f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/output_data/{well_id}/{well_name}"
        if Path(filepath + ".png").is_file():
            wells_done.append(well)
            core_from = Core.query.filter_by(well_id=well.id).first()
            core = Core(well_id=core_from.well_id, run_id=run_id, res_filepath=core_from.filepath.split('.')[0] + '.png',
                        well_data_id=core_from.well_data_id, project_id=core_from.project_id, filepath=core_from.filepath)
            shutil.copyfile(filepath + ".png", 'app/static/' + core.res_filepath)
            db.session.add(core)

            # change las-path
            # importer = ImportLasFiles(filepath + ".las", project_id=run.project_id)
            # importer.import_data()
            add_log(filepath + ".las", project_id=run.project_id)
            log = Logs.query.filter_by(well_id=core_from.well_id, project_id=run.project_id).first()
            las_path = f"{str(run.project_id)}_logs_{str(uuid.uuid4())}{well_name}.las"
            shutil.copyfile(filepath + ".las", 'uploads/' + las_path)
            log.filepath = las_path

    db.session.commit()
    # shutil.rmtree(f'{current_app.config["SERVICES_PATH"]}second/{str(run_id)}/')

    return wells_done


def run_second(wells, run_id):
    Path(f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/output_data/").mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/output_data/Report.txt").touch(exist_ok=True)
    create_strat_files(wells, run_id, 'second')
    create_log_files(wells, run_id, 'second', well_id_name=True)
    wells_list = []
    for well in wells:
        for core in well.core():
            wells_list.append(core.well_data_id)
            Path(f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}/input_data/wellCore/{core.well_data_id}")\
                .mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], core.filepath),
                            f"{current_app.config['SERVICES_PATH']}second/{str(run_id)}"
                            f"/input_data/wellCore/{core.well_data_id}/{core.well_data_id}.json")

    well_crvs = get_linking(run_id, wells_list)
    return save_results(wells, run_id, well_crvs)
