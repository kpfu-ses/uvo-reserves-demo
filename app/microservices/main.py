from app import db
from app.microservices.first import run_first
from app.models import Well
from app.models import run_well


def run_services(wells_ids, services, run_id):
    wells = Well.query.filter(Well.id.in_(wells_ids)).all()
    for well_id in wells_ids:
        statement = run_well.insert().values(well_id=well_id, run_id=run_id,)
        db.session.execute(statement)

    db.session.commit()
    if 1 in services:
        run_first(wells, run_id)



