from pathlib import Path
import shutil
import os
from flask import current_app
from datetime import datetime
from app import db
from app.models import StructFile, Run
from app.modules.sixth.Grid3D import get_3D


def save_res(run_id):
    run = Run.query.get(run_id)
    grid_struct = f"{current_app.config['SERVICES_PATH']}sixth/{str(run_id)}/output_data/grid_struct.pickle"
    filename_grid = f"{run.project_id}_grid_{datetime.now()}_grid_struct.pickle"
    if Path(grid_struct).is_file():
        shutil.copyfile(grid_struct, 'app/static/' + filename_grid)
        struct = StructFile(project_id=run.project_id, filepath=filename_grid, type='GRID', run_id=run_id)
        db.session.add(struct)

    db.session.commit()


def run_sixth(run_id):
    run = Run.query.get(run_id)

    Path(current_app.config['SERVICES_PATH'] + 'sixth/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'sixth/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    Path(f"{current_app.config['SERVICES_PATH']}sixth/{str(run_id)}/input_data/").mkdir(parents=True, exist_ok=True)
    surf_top = StructFile.query.filter_by(project_id=run.project_id, type='SURF_TOP').first()
    surf_bot = StructFile.query.filter_by(project_id=run.project_id, type='SURF_BOT').first()
    if surf_top.run_id is None:
        shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], surf_top.filepath),
                        f"{current_app.config['SERVICES_PATH']}sixth/{str(run_id)}"
                        f"/input_data/SurfaceTOP.txt")
    else:
        shutil.copyfile('app/static/' + surf_top.filepath,
                        f"{current_app.config['SERVICES_PATH']}sixth/{str(run_id)}"
                        f"/input_data/SurfaceTOP.txt")
    if surf_bot.run_id is None:
        shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], surf_bot.filepath),
                        f"{current_app.config['SERVICES_PATH']}sixth/{str(run_id)}"
                        f"/input_data/SurfaceBOT.txt")
    else:
        shutil.copyfile('app/static/' + surf_bot.filepath,
                        f"{current_app.config['SERVICES_PATH']}sixth/{str(run_id)}"
                        f"/input_data/SurfaceBOT.txt")
    get_3D(run_id)
    save_res(run_id)
