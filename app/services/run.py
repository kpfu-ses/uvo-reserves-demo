from app.models import Stratigraphy, Well


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

    return res_data
