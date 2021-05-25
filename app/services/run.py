from app.models import Stratigraphy, Well, CoreResults


def get_data(run):
    res_data = {'1': []}
    # результаты первого модуля
    strats = Stratigraphy.query.filter_by(run_id=run.id).all()
    for strat in strats:
        well = Well.query.get(strat.well_id)
        res_data['1'].append({well: {'lingula_top': strat.lingula_top,
                                     'p2ss2_top': strat.p2ss2_top,
                                     'p2ss2_bot': strat.p2ss2_bot}})
    # результаты второго модуля
    core_results = CoreResults.query.filter_by(run_id=run.id).all()
    for core_res in core_results:
        well = Well.query.get(core_res.well_id)
        res_data['2'].append({'well': {'well_name': well.name, 'well_id': well.id}})
    return res_data
