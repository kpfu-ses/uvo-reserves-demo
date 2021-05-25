from flask import jsonify
from flask_jwt_extended import jwt_required

from app.api import bp
from app.helpers.decorators import user_run_access
from app.models import CoreResults, Well


# результаты модуля увязки с керн
@bp.route('/runs/<run_id>/<well_id>', methods=['GET'])
@jwt_required(locations=['cookies'])
# @user_run_access()
def core_view(run_id, well_id):
    well = Well.query.get(well_id)
    core_res = CoreResults.query.filter_by(run_id=run_id, well_id=well_id).first()
    return jsonify(
        {
            'well': well.name,
            'data': core_res.data
        }
    )
