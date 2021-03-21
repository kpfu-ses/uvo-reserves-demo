import logging
import pickle
import sys

from app.modules.seventh.data_load_module import data_load_module
from app.modules.seventh.fes_interpolation import fes_interpolation
from app.modules.seventh.to_save_GRDECL import to_save_GRDECL


# конвертация путей файлов в зависимости от системы
def replaceSlash(filePath):
    platform = sys.platform
    slashMap = {'win32': '\\',
                'cygwin': '\\',
                'darwin': '/',
                'linux2': '/'}
    if platform not in slashMap.keys(): platform = 'linux2'
    return filePath.replace('\\', slashMap[platform])


def save_pickle(LD, path_pickle):
    obj = {
        "masPoint": LD.masPoint,
        "newCell": LD.newCell,
        "masN": LD.masN,
        "layerZ": LD.layerZ,
        "angle": LD.angle
    }

    output = open(replaceSlash(path_pickle + "\\grid_structFES.pickle"), 'wb')
    pickle.dump(obj, output)
    output.close()


def get_interpolation(run_id, wells_list):
    abs_path = 'app/modules/seventh/'
    run_path = abs_path + str(run_id) + '/'
    out_path_log = replaceSlash(run_path + "\\output_data\\Report.txt")
    logging.basicConfig(format=u'%(levelname)-8s : %(message)s', level=logging.WARNING, filename=out_path_log,
                        filemode='w')
    Err_count = 0
    pattern_text_log = '   %s   :   %s'
    outfolder = run_path + 'output_data'
    LD = data_load_module(wells_list, pattern_text_log, run_path, abs_path)

    FI = fes_interpolation()

    try:
        LD.load_coords()
        LD.load_pickle()
        LD.load_wells()
        Err_count += LD.Err_count
    except BaseException as e:
        logging.error(pattern_text_log, "", "data_load_module. " + str(e))
        Err_count += 1
        sys.exit()


    try:
        FI.Cell_FES(LD)
        FI.FES_interp(LD)
    except BaseException as e:
        logging.error(pattern_text_log, "", "fes_interpolation. " + str(e))
        Err_count += 1
        sys.exit()

    try:
        SM = to_save_GRDECL(LD, outfolder)
    except BaseException as e:
        logging.error(pattern_text_log, "", "to_save_GRDECL. " + str(e))
        Err_count += 1

    try:
        save_pickle(LD, outfolder)
    except BaseException as e:
        logging.error(pattern_text_log, "", "write pickle-file. " + str(e))
        Err_count += 1

    if Err_count == 0:
        logging.addLevelName(100, "INFO")
        logging.log(100, pattern_text_log, "", "No errors in data")
