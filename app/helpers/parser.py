import json
import os
import lasio
import numpy as np
from flask import current_app
from app.helpers.util import guess_enc, well_name_re


def read_coords(filepath):
    with open(os.path.join(current_app.config['UPLOAD_FOLDER'], filepath), 'r') as f:
        data = f.read().replace('\n', '')
    return json.loads(data)


def read_strat(filepath):
    with open(filepath, 'r') as f:
        data = f.read().replace('\n', '')
    return json.loads(data)


def read_lasio(filepath):
    # path_lasio = os.path.join(current_app.config['UPLOAD_FOLDER'], filepath)
    path_lasio = filepath
    Z_names = ["tvdss", "tvd", "z"]
    GK_names = ["gkv", "gr", "gk", "gk1", "гк", "gk:1", "гк  ", "_гк", "= gk$"]
    IK_names = ["ik", "ild", "ик", "ik1", "ik:1", "ик  ", "иk", "зонд ик", "rik", "ик$", "ик_n"]
    NGK_names = ["нгк alfa", "ngl", "нгк", "nkdt", "jb", "jm", "ngk", "ngk:1", "ннкб", "nnkb", "nnkb  (ннкб)",
                 "бз ннк", "nktd", "бз", "_нгк", "ннк", "_ннк"]
    MD_names = ["dept", "md", "depth"]
    PZ_names = ["pz", "ks", "pz:1", "pz1", "пз", "кс"]

    well_info = {}
    enc = guess_enc(path_lasio)
    W_i = lasio.read(path_lasio, encoding=enc)
    wname = well_name_re(str(W_i.well["WELL"].value))
    well_info['name'] = wname
    for name_crv in W_i.curves.keys():
        if str(name_crv).lower() in GK_names:
            well_info.update({"GK": np.array(W_i.curves[name_crv].data)})
            continue

        if str(name_crv).lower() in IK_names:
            well_info.update({"IK": np.array(W_i.curves[name_crv].data)})
            continue

        if str(name_crv).lower() in NGK_names:
            well_info.update({"NGK": np.array(W_i.curves[name_crv].data)})
            continue

        if str(name_crv).lower() in MD_names:
            well_info.update({"DEPT": np.array(W_i.curves[name_crv].data)})
            continue

        if str(name_crv).lower() in PZ_names:
            well_info.update({"PZ": np.array(W_i.curves[name_crv].data)})
            continue

        if str(name_crv).lower() in Z_names:
            well_info.update({"Z": np.array(W_i.curves[name_crv].data)})
            continue
        well_info.update({name_crv: np.array(W_i.curves[name_crv].data)})

    return well_info
