from pathlib import Path
import shutil
import os
from flask import current_app
from datetime import datetime
from app import db
from app.models import StructFile, Run
from app.modules.eighth.Reserves_main import get_reserves


def save_res(run_id):
    run = Run.query.get(run_id)
    grid_struct = f"{current_app.config['SERVICES_PATH']}eighth/{str(run_id)}/output_data/reserves.txt"
    filename_grid = f"{run.project_id}_reserves_{datetime.now()}_reserves.txt"
    if Path(grid_struct).is_file():
        shutil.copyfile(grid_struct, 'app/static/' + filename_grid)
        struct = StructFile(project_id=run.project_id, filepath=filename_grid, type='RESERVES', run_id=run_id)
        db.session.add(struct)

    db.session.commit()


def run_eighth(run_id):
    run = Run.query.get(run_id)

    Path(current_app.config['SERVICES_PATH'] + 'eighth/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'eighth/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    Path(f"{current_app.config['SERVICES_PATH']}eighth/{str(run_id)}/input_data/").mkdir(parents=True, exist_ok=True)
    grid = StructFile.query.filter_by(project_id=run.project_id, type='GRID_FES').first()
    if grid.run_id is None:
        shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], grid.filepath),
                        f"{current_app.config['SERVICES_PATH']}eighth/{str(run_id)}"
                        f"/input_data/grid_structFES.pickle")
    else:
        shutil.copyfile('app/static/' + grid.filepath,
                        f"{current_app.config['SERVICES_PATH']}eighth/{str(run_id)}"
                        f"/input_data/grid_structFES.pickle")

    get_reserves(run_id)
    save_res(run_id)
