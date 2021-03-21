import json
import logging
import pickle
import sys
from sys import exit as sys_exit

import numpy as np


class data_load_module(object):
    def __init__(self, pattern_text_log, abs_path, run_path):
        self.pattern_text_log = pattern_text_log
        self.Err_count = 0
        self.masPoint = None
        self.newCell = None
        self.masN = None
        self.layerZ = None
        self.angle = None
        self.ro_oil = None
        self.contr = None
        self.abs_path = abs_path
        self.Geo_model_Path = run_path + "input_data\\grid_structFES.pickle"
        self.path_contour = run_path + "input_data\\Контур.txt"
        self.name_interp_crv = [
            "SOIL_MASS_AUTO",
            "PORO_OPEN_AUTO",
            "SOIL_VOL_AUTO"
        ]
        self.MD_name = ["MD", "DEPT", "md", "dept"]

    def load_pickle(self):
        with open(self.replaceSlash(self.Geo_model_Path), 'rb') as f:
            tmp = pickle.load(f)

            self.masPoint = tmp["masPoint"]
            self.newCell = tmp["newCell"]
            self.masN = tmp["masN"]
            self.layerZ = tmp["layerZ"]
            self.angle = tmp["angle"]

        f.close()

    # конвертация путей файлов в зависимости от системы
    def replaceSlash(self, filePath):
        platform = sys.platform
        slashMap = {'win32': '\\',
                    'cygwin': '\\',
                    'darwin': '/',
                    'linux2': '/'}
        if platform not in slashMap.keys(): platform = 'linux2'
        return filePath.replace('\\', slashMap[platform])

    def load_config(self):
        try:
            dc = None
            with open(self.abs_path + 'configuration_reserves.json', 'r') as fc:
                dc = json.load(fc)
            self.ro_oil = float(dc["ro_oil"])
        except BaseException as e:
            logging.error(self.pattern_text_log, "", 'Ошибка при загрузке файла конфигурации. ' + str(e))
            self.Err_count += 1
            sys_exit()

    def load_contour(self):
        try:
            self.contr = np.genfromtxt(self.replaceSlash(self.path_contour), delimiter=' ', dtype=np.float)
        except BaseException as e:
            logging.warning(self.pattern_text_log, "", 'load_contour. ' + str(e))
            self.Err_count += 1
