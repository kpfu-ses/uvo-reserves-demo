import numpy as np
from matplotlib import path
import cloudpickle as pickle
import lasio
from tqdm import tqdm
from os import listdir
from os.path import join as joinpath
import os
import sys
import logging
import json
from app.modules.sixth.Grid3D import Cell, Point


class well_class(object):
    def __init__(self, crv, Icell, X, Y):
        self.crv = crv
        self.Icell = Icell
        self.X = X
        self.Y = Y


class data_load_module(object):
    def __init__(self, wells_list, pattern_text_log, run_path, abs_path):
        self.wells_list = wells_list
        self.pattern_text_log = pattern_text_log
        self.masPoint = None
        self.newCell = None
        self.masN = None
        self.layerZ = None
        self.WELLS = []
        self.XYA = None
        self.angle = None
        self.config = None
        self.name_interp_crv = [
            "SOIL_MASS_AUTO",
            "PORO_OPEN_AUTO",
            "SOIL_VOL_AUTO",
            "AGK_AUTO",
            "VOLUME_DENSITY_AUTO",
            "PERM_HOR_AUTO"
        ]
        self.abs_path = abs_path
        self.MD_name = ["MD", "DEPT", "md", "dept"]
        self.Err_count = 0
        self.well_coord_Path = run_path + "input_data\\coords\\"
        self.well_lasio_Path = run_path + "input_data\\wellLogs\\"
        self.Geo_model_Path = run_path + "input_data\\grid_struct.pickle"

    def loadConfig(self):
        config = {}
        try:
            dc = None
            with open(self.abs_path + 'configuration.json', 'r') as fc:
                dc = json.load(fc)
            for k in dc.keys():
                config.update({str(k).split()[0]: float(dc[k])})
        except BaseException as e:
            logging.error(self.pattern_text_log, "", 'Ошибка при загрузке файла конфигурации. ' + str(e))
            self.Err_count += 1
            return False
        self.config = config
        return True

    # Функция сбора лас файлов в папке и во всех вложенных папках
    def getFilePaths(self, wellLogsPath):
        list = [val for val in os.listdir(wellLogsPath)]
        list = [(wellLogsPath + '/' + list[i]).replace('\\', '/') for i in range(len(list))]
        paths = [fileOrPath for fileOrPath in list if os.path.isdir(fileOrPath)]
        files = [fileOrPath for fileOrPath in list if os.path.isfile(fileOrPath) and fileOrPath.lower().endswith('las')]
        for path in paths:
            files.extend(self.getFilePaths(path))
        return files

    # конвертация путей файлов в зависимости от системы
    def replaceSlash(self, filePath):
        platform = sys.platform
        slashMap = {'win32': '\\',
                    'cygwin': '\\',
                    'darwin': '/',
                    'linux2': '/'}
        if platform not in slashMap.keys(): platform = 'linux2'
        return filePath.replace('\\', slashMap[platform])

    def inPolygonXY(self, e1, e2, e3, xp, yp, e4=None):
        if e4 is None:
            RES = False
            Polygon_path = path.Path([(e1.x, e1.y), (e2.x, e2.y), (e3.x, e3.y)])
            if Polygon_path.contains_point((xp, yp)):
                RES = True
            return RES
        else:
            RES = False
            X = (xp - e1.x) / (e2.x - e1.x)
            Y = (yp - e1.y) / (e2.y - e1.y)
            if abs(Y - X) < 1e-5:
                return True
            elif abs(e2.y - e1.y) < 1e-5:
                if (xp >= e1.x) and (xp <= e2.x) and abs(e2.y - yp) < 1e-5:
                    return True
            Polygon_path = path.Path([(e1.x, e1.y), (e2.x, e2.y), (e4.x, e4.y), (e3.x, e3.y)])
            if Polygon_path.contains_point((xp, yp)):
                RES = True
            return RES

    def GetCurve(self, well, names):
        for name in names:
            if name in well.curves.keys():
                crv = well.curves[name].data
                break
        return crv

    def load_coords(self):
        XYA_incl = {}
        for index in self.wells_list:
            try:
                coordsPath = self.replaceSlash(self.well_coord_Path + index)
                with open(self.replaceSlash(os.path.join(coordsPath, os.listdir(coordsPath)[0])), "r",
                          encoding='UTF-8') as read_file:
                    Coords = json.load(read_file)
                    name = str(Coords["Well"])

                    XYA_incl.update({str(index): {
                        "X": Coords['X'],
                        "Y": Coords['Y'],
                        "A": Coords['RKB']
                    }})

            except:
                logging.warning(self.pattern_text_log, str(index), "No read coords")
                self.Err_count += 1
                continue
        self.XYA = XYA_incl

    def load_pickle(self):
        # try:
        with open(self.replaceSlash(self.Geo_model_Path), 'rb') as f:
            tmp = pickle.load(f)

            self.masPoint = tmp["masPoint"]
            self.newCell = tmp["newCell"]
            self.masN = tmp["masN"]
            self.layerZ = tmp["layerZ"]
            self.angle = tmp["angle"]
        print('masN', self.masN)
        print('angle', self.angle)

        # f.close()
        # except BaseException as e:
        #     logging.error(self.pattern_text_log, "", "load_pickle. " + str(e))
        #     self.Err_count += 1

    def Get_wells_inf(self, well, index):
        w_name = str(well.well["WELL"].value)
        try:
            X_vrt = self.XYA[index]["X"]
            Y_vrt = self.XYA[index]["Y"]
            RKB = self.XYA[index]["A"]
        except:
            logging.error(self.pattern_text_log, str(index),
                          "There is no coincidence between the object WELLS and the elements TOPS_BOTS! ")
            self.Err_count += 1
            return None

        DEPT = self.GetCurve(well, self.MD_name)

        Z = RKB - DEPT

        crv = {"Z": Z}

        for keysW in well.keys():
            try:
                if keysW.upper() in self.name_interp_crv:
                    crv_fes = well[keysW]
                    crv.update({keysW.upper(): crv_fes})
            except BaseException as e:
                logging.error(self.pattern_text_log, str(index), str(e))
                self.Err_count += 1
                continue

        ind_cell = np.nan

        for yi in range(0, self.masN[1]):
            well_cell = False
            for xi in range(0, self.masN[0]):
                i_c = xi + yi * self.masN[0]

                e1 = self.masPoint[self.newCell[i_c].point_num[0]]
                e2 = self.masPoint[self.newCell[i_c].point_num[1]]
                e3 = self.masPoint[self.newCell[i_c].point_num[2]]
                e4 = self.masPoint[self.newCell[i_c].point_num[3]]

                try:
                    if self.inPolygonXY(e1, e2, e3, X_vrt, Y_vrt, e4):
                        if self.newCell[i_c].well == False:
                            self.newCell[i_c].well = True
                            ind_cell = i_c
                            well_cell = True
                        else:
                            search_cell = False
                            for yb in [-1, 0, 1]:
                                for xb in [-1, 0, 1]:
                                    if (xi + xb >= 0 and xi + xb < self.masN[0]) and (
                                            yi + yb >= 0 and yi + yb < self.masN[1]):
                                        i_c_loc = (xi + xb) + (yi + yb) * self.masN[0]
                                        e1_loc = self.masPoint[self.newCell[i_c_loc].point_num[0]]
                                        e2_loc = self.masPoint[self.newCell[i_c_loc].point_num[1]]
                                        e3_loc = self.masPoint[self.newCell[i_c_loc].point_num[2]]
                                        e4_loc = self.masPoint[self.newCell[i_c_loc].point_num[3]]
                                        if self.inPolygonXY(e1_loc, e2_loc, e3_loc, X_vrt, Y_vrt, e4_loc):
                                            if self.newCell[i_c_loc].well == False:
                                                self.newCell[i_c_loc].well = True
                                                ind_cell = i_c_loc
                                                search_cell = True
                                                well_cell = True
                                                break
                                if search_cell:
                                    break
                            if search_cell == False:
                                ind_cell = i_c
                                well_cell = True
                        break
                except BaseException as e:
                    logging.error(self.pattern_text_log, str(index), str(e))
                    self.Err_count += 1
                    continue
            if well_cell:
                break
        return well_class(crv, ind_cell, X_vrt, Y_vrt)

    def load_wells(self):
        for index in tqdm(self.wells_list):

            files = self.getFilePaths(os.path.abspath(self.replaceSlash(self.well_lasio_Path + index)))
            for file in files:
                try:
                    file = self.replaceSlash(file)
                    crv = {}
                    W_i = lasio.read(file, autodetect_encoding=True)

                    w_name = str(W_i.well["WELL"].value)
                    if index in self.XYA.keys():
                        val = self.Get_wells_inf(W_i, index)
                        if not val is None:
                            self.WELLS.append(val)
                except BaseException as e:
                    logging.error(self.pattern_text_log, str(index), str(file) + ". " + str(e))
                    self.Err_count += 1
                    continue
        print()
