from pathlib import Path
import shutil
import os
from flask import current_app
from datetime import datetime
from app import db
from app.models import StructFile, Run, Struct
from app.microservices.util import create_coords_files, create_log_files
from app.modules.seventh.Interpolation_main import get_interpolation


def save_res(run_id):
    run = Run.query.get(run_id)
    grid_struct = f"{current_app.config['SERVICES_PATH']}seventh/{str(run_id)}/output_data/grid_structFES.pickle"
    filename_grid = f"{run.project_id}_grid_fes_{datetime.now()}_grid_structFES.pickle"
    if Path(grid_struct).is_file():
        shutil.copyfile(grid_struct, 'app/static/' + filename_grid)
        struct = StructFile(project_id=run.project_id, filepath=filename_grid, type=Struct.GRID_FES, run_id=run_id)
        db.session.add(struct)

    db.session.commit()


def run_seventh(wells, run_id):
    run = Run.query.get(run_id)

    Path(current_app.config['SERVICES_PATH'] + 'seventh/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'seventh/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    Path(f"{current_app.config['SERVICES_PATH']}seventh/{str(run_id)}/input_data/").mkdir(parents=True, exist_ok=True)
    grid = StructFile.query.filter_by(project_id=run.project_id, type=Struct.GRID).first()
    if grid.run_id is None:
        shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], grid.filepath),
                        f"{current_app.config['SERVICES_PATH']}seventh/{str(run_id)}"
                        f"/input_data/grid_struct.pickle")
    else:
        shutil.copyfile('app/static/' + grid.filepath,
                        f"{current_app.config['SERVICES_PATH']}seventh/{str(run_id)}"
                        f"/input_data/grid_struct.pickle")
    create_coords_files(wells, run_id, 'seventh', well_id_name=True)
    create_log_files(wells, run_id, 'seventh', well_id_name=True)
    wells_list = []
    for well in wells:
        for core in well.core():
            wells_list.append(core.well_data_id)
            break
    get_interpolation(run_id, wells_list)
    save_res(run_id)
