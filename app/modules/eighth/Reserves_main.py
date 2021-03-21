import logging
import sys
from sys import exit as sys_exit

import numpy as np

from app.modules.eighth.data_load_module import data_load_module
from app.modules.eighth.func import Zapas
from app.modules.eighth.to_save_GRDECL import to_save_GRDECL


class Cell(object):
    def __init__(self, point_num=[], centre=[]):
        self.point_num = point_num
        self.FES = {}
        self.ACTNUM = 0
        self.layZ = np.nan
        self.FES_c = {}
        self.centre = centre
        self.well = False
        self.collapsed = False


class Point(object):
    def __init__(self, x=np.nan, y=np.nan, z=np.nan):
        self.x = x
        self.y = y
        self.z = z


def Save_report(Z, LD, outfolder):
    f = open(LD.replaceSlash(outfolder + '\\reserves.txt'), 'w')
    s1 = "Рассчитанные геологические запасы нефти:"
    f.write(s1 + '\n')
    f.write(str(Z.Zapas_all) + " m3" + '\n')
    f.write(str(Z.Zapas_ton) + " t" + '\n')
    f.close()


# конвертация путей файлов в зависимости от системы
def replaceSlash(filePath):
    platform = sys.platform
    slashMap = {'win32': '\\',
                'cygwin': '\\',
                'darwin': '/',
                'linux2': '/'}
    if platform not in slashMap.keys(): platform = 'linux2'
    return filePath.replace('\\', slashMap[platform])


def get_reserves(run_id):
    abs_path = 'app/modules/eighth/'
    run_path = abs_path + str(run_id) + '/'
    out_path_log = replaceSlash(run_path + "\\output_data\\Report.txt")
    logging.basicConfig(format=u'%(levelname)-8s : %(message)s', level=logging.WARNING, filename=out_path_log,
                        filemode='w')
    Err_count = 0
    pattern_text_log = '   %s   :   %s'
    outfolder = run_path + 'output_data'
    LD = data_load_module(pattern_text_log, abs_path, run_path)
    try:
        LD.load_pickle()
        LD.load_config()
        LD.load_contour()
        Err_count += LD.Err_count
    except BaseException as e:
        logging.error(pattern_text_log, "", "data_load_module. " + str(e))
        Err_count += 1
        sys_exit()

    Z = Zapas()
    try:
        Z.get_zapas(LD)
    except BaseException as e:
        logging.error(pattern_text_log, "", "calc_reserves. " + str(e))
        Err_count += 1
        sys_exit()

    try:
        SM = to_save_GRDECL(LD, outfolder, 'properties')
    except BaseException as e:
        logging.error(pattern_text_log, "", "to_save_GRDECL. " + str(e))
        Err_count += 1

    Save_report(Z, LD, outfolder)

    if Err_count == 0:
        logging.addLevelName(100, "INFO")
        logging.log(100, pattern_text_log, "", "No errors in data")

