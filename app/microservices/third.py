import shutil
import uuid
from pathlib import Path
import re
from flask import current_app

from app import db
from app.helpers.LasParser import ImportLasFiles
from app.helpers.services import add_log
from app.models import Logs, Run
from app.modules.third.core_log import get_interpolation
from app.microservices.util import create_coords_files, create_strat_files, create_log_files

regWellName = r"[^0-9]"


def save_results(wells, run_id):
    run = Run.query.get(run_id)
    wells_done = []

    for well in wells:
        well_id = well.core()[0].well_data_id
        # well name without letters
        well_name = re.sub(regWellName, '', well.name.replace(' ', ''))
        # save las
        filepath = f"{current_app.config['SERVICES_PATH']}third/{str(run_id)}/output_data/{well_id}/{well_name}"
        if Path(filepath + ".png").is_file():
            wells_done.append(well)
            log_from = Logs.query.filter_by(well_id=well.id, project_id=run.project_id).first()
            res_filepath = log_from.filepath.split('.')[0] + '.png'
            log = Logs(well_id=well.id, project_id=log_from.project_id, run_id=run_id, res_filepath=res_filepath)

            shutil.copyfile(filepath + ".png", 'app/static/' + res_filepath)

            # change las-path
            # importer = ImportLasFiles(filepath + ".las", project_id=run.project_id)
            # importer.import_data()
            add_log(filepath + ".las", project_id=run.project_id)
            las_path = f"{str(run.project_id)}_logs_{str(uuid.uuid4())}{well_name}.las"
            shutil.copyfile(filepath + ".las", 'uploads/' + las_path)
            log.filepath = las_path
            db.session.add(log)
    db.session.commit()
    # shutil.rmtree(f'{current_app.config["SERVICES_PATH"]}third/{str(run_id)}/')
    return wells_done


def run_third(wells, run_id):
    Path(f"{current_app.config['SERVICES_PATH']}third/{str(run_id)}/output_data/").mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(f"{current_app.config['SERVICES_PATH']}third/{str(run_id)}/output_data/Report.txt").touch(exist_ok=True)
    create_coords_files(wells, run_id, 'third', well_id_name=True)
    create_strat_files(wells, run_id, 'third')
    create_log_files(wells, run_id, 'third', well_id_name=True)

    get_interpolation(run_id)
    return save_results(wells, run_id)
