from pathlib import Path
import shutil
from flask import current_app
from datetime import datetime
from app import db
from app.models import StructFile, Run
from app.modules.fifth.surface import get_surfaces
from app.microservices.util import create_coords_files, create_strat_files


def save_res(run_id):
    run = Run.query.get(run_id)
    filepath_top = f"{current_app.config['SERVICES_PATH']}fifth/{str(run_id)}/output_data/SurfaceTOP.txt"
    filepath_bot = f"{current_app.config['SERVICES_PATH']}fifth/{str(run_id)}/output_data/SurfaceBOT.txt"
    filename_top = f"{run.project_id}_surf_top_{datetime.now()}_SurfaceTOP.txt"
    filename_bot = f"{run.project_id}_surf_top_{datetime.now()}_SurfaceBOT.txt"
    if Path(filepath_top).is_file():
        shutil.copyfile(filepath_top, 'app/static/' + filename_top)
        struct = StructFile(project_id=run.project_id, filepath=filename_top, type='SURF_TOP', run_id=run_id)
        db.session.add(struct)
    if Path(filepath_bot).is_file():
        shutil.copyfile(filepath_bot, 'app/static/' + filename_bot)
        struct = StructFile(project_id=run.project_id, filepath=filename_bot, type='SURF_BOT', run_id=run_id)
        db.session.add(struct)
    db.session.commit()


def run_fifth(wells, run_id):
    Path(current_app.config['SERVICES_PATH'] + 'fifth/' + str(run_id) + '/output_data/').mkdir(parents=True,
                                                                                               exist_ok=True)
    Path(current_app.config['SERVICES_PATH'] + 'fifth/' + str(run_id) + '/output_data/Report.txt').touch(exist_ok=True)
    create_coords_files(wells, run_id, 'fifth', well_id_name=True)
    create_strat_files(wells, run_id, 'fifth')
    get_surfaces(run_id)
    save_res(run_id)
