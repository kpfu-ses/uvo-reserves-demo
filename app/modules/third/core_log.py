import matplotlib.pyplot as plt

import logging
import warnings

warnings.filterwarnings("ignore")

import os
from os.path import join as joinpath
import sys

import pickle

import numpy as np
from scipy.stats import mode
from scipy.signal import savgol_filter
from scipy.signal import medfilt

from app.modules.third.wellClass import Well
import lasio
import xlsxwriter
import json

from progress.bar import Bar

import copy


# конвертация путей файлов в зависимости от системы
def replaceSlash(filePath):
    platform = sys.platform
    slashMap = {'win32': '\\',
                'cygwin': '\\',
                'darwin': '/',
                'linux2': '/'}
    if platform not in slashMap.keys(): platform = 'linux2'
    return filePath.replace('\\', slashMap[platform])


def Save_Excel(path, catalog):
    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet('NeuroPower')

    # Bold format to use to highlight cells.
    bold = workbook.add_format({'align': 'center', 'bold': True})
    center = workbook.add_format({'align': 'center', 'bold': False})

    # Write some data headers.
    worksheet.write('A1', 'Номер', bold)
    worksheet.write('B1', 'Альтитуда', bold)
    worksheet.merge_range('C1:D1', 'Глубина', bold)
    worksheet.merge_range('E1:F1', 'Абс.отм', bold)
    worksheet.merge_range('G1:I1', 'Толщина', bold)
    worksheet.merge_range('J1:N1', 'Геофиз.пар', bold)

    worksheet.write('A2', 'скважины', bold)
    worksheet.write('B2', 'RKB', bold)
    worksheet.write('C2', 'кровли', bold)
    worksheet.write('D2', 'подошвы', bold)
    worksheet.write('E2', 'кровли', bold)
    worksheet.write('F2', 'подошвы', bold)
    worksheet.write('G2', 'Но, м', bold)
    worksheet.write('H2', 'Нн, м', bold)
    worksheet.write('I2', 'Hв, м', bold)
    worksheet.write('J2', 'КП, доля', bold)
    worksheet.write('K2', 'КН_ОБ, доля', bold)
    worksheet.write('L2', 'КН_ВЕС, %', bold)
    worksheet.write('M2', 'аГК, доля', bold)
    worksheet.write('N2', 'КПр, мД', bold)

    # Iterate over the data and write it out row by row.
    row = 2
    for wellData in catalog:
        for position, value in enumerate(wellData):
            worksheet.write(row, position, value, center)
        row += 1

    workbook.close()


def nk_normd(d, nk, tops):
    ling = np.logical_and(d >= tops[0], d <= tops[1])
    sand = np.logical_and(d >= tops[1], d <= tops[2])
    sper = np.logical_and(d >= tops[0] - 5, d <= tops[0])
    nkn = (nk - np.nanmin(nk[ling])) / (np.nanmax(nk[sper]) - np.nanmin(nk[ling]))
    return nkn


def gk_norm(d, gk, tops):
    ling = np.logical_and(d >= tops[0], d <= tops[1])
    sand = np.logical_and(d >= tops[1], d <= tops[2])
    sper = np.logical_and(d >= tops[0] - 5, d <= tops[0])
    gmin = np.nanmin(gk[sand])
    gmax = np.nanmax(gk[ling])
    if np.isnan(gmin): gmin = np.nanmin(gk)
    if np.isnan(gmax): gmax = np.nanmax(gk)
    gkn = (gk - gmin) / (gmax - gmin)
    gkn[gkn > 1] = 1
    gkn[gkn < 0] = 0
    return gkn


def nk_norm(d, nk, tops):
    ling = np.logical_and(d >= tops[0], d <= tops[1])
    sand = np.logical_and(d >= tops[1], d <= tops[2])
    sper = np.logical_and(d >= tops[0] - 5, d <= tops[0])
    nmin = np.nanmin(nk[ling])
    nmax = max(np.nanmax(nk[sand]), np.nanmax(nk[sper]))
    nmax = np.nanmax(nk[sper]) * 2
    if np.isnan(nmin): nmin = np.nanmin(nk)
    if np.isnan(nmax): nmax = np.nanmax(nk)
    nkn = (nk - nmin) / (nmax - nmin)
    nkn[nkn > 1] = 1
    nkn[nkn < 0] = 0
    return nkn


def nk_norm1(d, nk, tops):
    ling = np.logical_and(d >= tops[0], d <= tops[1])
    sand = np.logical_and(d >= tops[1], d <= tops[2])
    sper = np.logical_and(d >= tops[0] - 5, d <= tops[0])
    nmin = np.nanmin(nk[ling])
    nmax = np.nanmax(nk[sper])
    if np.isnan(nmin): nmin = np.nanmin(nk)
    if np.isnan(nmax): nmax = np.nanmax(nk)
    nkn = (nk - nmin) / (nmax - nmin)
    nkn[nkn < 0] = 0
    return nkn


def ik_norm(dept, ik, ind, tops):
    d = dept[ind > 0]
    aik = ik[ind > 0]
    sand = np.logical_and(d >= tops[1], d <= tops[2])
    sper = np.logical_and(dept >= tops[0] - 5, dept <= tops[0])
    nmin = np.nanmin(ik)
    nmax = np.nanmax(ik[sper])
    ikn = (ik - nmin) / (nmax - nmin)
    ikn = ik / nmax
    ikn[ikn < 0] = 0
    return ikn


def nk_sper(dept, crv, tops):
    sper = np.logical_and(dept >= tops[0] - 5, dept <= tops[0])
    nmax = np.nanmax(crv[sper])
    crvn = crv / nmax
    return crvn


def avg_upper(y, d, h):
    avg = np.ones(y.shape) * np.nan
    for i in range(d + h, y.size):
        data = np.nanmean(y[i - d - h:i - d + 1])
        avg[i] = [np.nan, data][np.isfinite(data)]
    return avg


def avg_lower(y, d, h):
    avg = np.ones(y.shape) * np.nan
    for i in range(0, y.size - d - h):
        data = np.nanmean(y[i + d:i + d + h + 1])
        avg[i] = [np.nan, data][np.isfinite(data)]
    return avg


def Boundary_averaging(crv_for_obj, dpt, crv_mean):
    def get_class(_lit, _dpt):
        lit = np.copy(_lit)
        dpt = np.copy(_dpt)

        lit[np.isnan(lit)] = -9999

        keyslit = list(set(lit))
        obj_lito = {str(k): [] for k in keyslit}

        obj_i = []
        obj_i.append(0)
        for i in range(1, len(dpt)):
            if abs(lit[i] - lit[i - 1]) < 1e-3:
                obj_i.append(i)
            else:
                obj_lito[str(lit[i - 1])].append([dpt[obj_i[0]], dpt[obj_i[-1]]])
                obj_i = []
                obj_i.append(i)

        if len(obj_i) > 1:
            obj_lito[str(lit[obj_i[0]])].append([dpt[obj_i[0]], dpt[obj_i[-1]]])
        return obj_lito

    obj_crv = get_class(crv_for_obj, dpt)

    new_crv = np.ones(len(crv_mean)) * np.nan
    bnd = np.array([])

    for k in obj_crv:

        mas = obj_crv[k]

        for m in mas:
            extr = np.array([])
            extr = np.append(extr, m[0])
            ind = np.logical_and(dpt >= m[0], dpt <= m[1])
            crv_cut = crv_mean[ind]
            dpt_cut = dpt[ind]
            for i in range(2, len(crv_cut) - 2):
                if (crv_cut[i] >= crv_cut[i + 1] and crv_cut[i] > crv_cut[i - 1]) or \
                        (crv_cut[i] <= crv_cut[i + 1] and crv_cut[i] < crv_cut[i - 1]):
                    extr = np.append(extr, dpt_cut[i])
            extr = np.append(extr, m[1])
            extr = np.sort(extr)

            BND = np.array([])
            for i in range(1, len(extr) - 2):
                BND = np.append(BND, round((extr[i] + extr[i + 1]) / 2, 1))

            BND = np.append(BND, extr[0])
            BND = np.append(BND, extr[-1])
            BND = np.array(list(set(BND)))
            BND = np.sort(BND)

            new_crv_cut = np.ones(len(dpt_cut)) * np.nan
            this_obj = []

            for i in range(len(BND) - 1):
                ind_L = np.where(abs(dpt_cut - BND[i]) < 1e-3)[0][0]
                ind_R = np.where(abs(dpt_cut - BND[i + 1]) < 1e-3)[0][0]
                if crv_cut[ind_L] < crv_cut[ind_L + 1]:
                    val = (np.nanmean(crv_cut[ind_L: ind_R]) + np.nanmax(crv_cut[ind_L: ind_R])) / 2
                else:
                    val = (np.nanmean(crv_cut[ind_L: ind_R]) + np.nanmin(crv_cut[ind_L: ind_R])) / 2
                new_crv_cut[ind_L: ind_R + 1] = val
                this_obj.append([ind_L, ind_R + 1])

            this_obj2 = []
            for i in range(len(this_obj) - 1):
                obj = this_obj[i]
                obj1 = this_obj[i + 1]
                if abs(mode(new_crv_cut[obj[0]:obj[1]])[0][0] - mode(new_crv_cut[obj1[0]:obj1[1]])[0][0]) < 0.02:
                    new_crv_cut[obj1[0]: obj1[1]] = mode(new_crv_cut[obj[0]: obj[1]])[0][0]
                    this_obj[i + 1] = [obj[0], obj1[1]]
                    this_obj2.append([obj[0], obj1[1]])
                else:
                    this_obj2.append(obj)

            for i in range(len(this_obj2) - 1):
                obj = this_obj2[i]
                obj1 = this_obj2[i + 1]
                if abs(obj[0] - obj[1]) <= 20:
                    new_crv_cut[obj[0]: obj[1]] = mode(new_crv_cut[obj1[0]: obj1[1]])[0][0]
                    this_obj2[i + 1] = [obj[0], obj1[1]]
            new_crv[ind] = new_crv_cut

    bnd_vcl = get_class(new_crv, dpt)

    for k in bnd_vcl:
        mas = bnd_vcl[k]
        for m in mas:
            bnd = np.append(bnd, m[0])
            bnd = np.append(bnd, m[1])
    bnd = list(set(bnd))
    bnd = np.sort(bnd)

    flag = True
    while flag:
        ind_del = np.array([], dtype=int)
        flag = False
        if bnd[1] - bnd[0] < 0.8:
            if bnd[2] - bnd[1] < 0.11 and np.isfinite(crv_for_obj[dpt == bnd[1]]) \
                    and np.isfinite(crv_for_obj[dpt == bnd[2]]) \
                    and crv_for_obj[dpt == bnd[1]] == crv_for_obj[dpt == bnd[2]]:
                ind_del = np.append(ind_del, 1)
                ind_del = np.append(ind_del, 2)
                flag = True
                bnd = [bnd[k] for k in range(len(bnd)) if not k in ind_del]
                ind_del = np.array([], dtype=int)
                continue

        for i in range(1, len(bnd) - 2):
            if bnd[i + 1] - bnd[i] < 0.8:
                if bnd[i + 2] - bnd[i + 1] < 0.11 and np.isfinite(crv_for_obj[dpt == bnd[i + 1]]) \
                        and np.isfinite(crv_for_obj[dpt == bnd[i + 2]]) \
                        and crv_for_obj[dpt == bnd[i + 1]] == crv_for_obj[dpt == bnd[i + 2]]:
                    ind_del = np.append(ind_del, i + 1)
                    ind_del = np.append(ind_del, i + 2)
                    flag = True
                    bnd = [bnd[k] for k in range(len(bnd)) if k not in ind_del]
                    ind_del = np.array([], dtype=int)
                    break
                elif bnd[i] - bnd[i - 1] < 0.11 and np.isfinite(crv_for_obj[dpt == bnd[i]]) \
                        and np.isfinite(crv_for_obj[dpt == bnd[i - 1]]) \
                        and crv_for_obj[dpt == bnd[i]] == crv_for_obj[dpt == bnd[i - 1]]:
                    ind_del = np.append(ind_del, i)
                    ind_del = np.append(ind_del, i - 1)
                    flag = True
                    bnd = [bnd[k] for k in range(len(bnd)) if k not in ind_del]
                    ind_del = np.array([], dtype=int)
                    break

        if bnd[-1] - bnd[-2] < 0.8:
            if bnd[-2] - bnd[-3] < 0.11 and np.isfinite(crv_for_obj[dpt == bnd[-2]]) \
                    and np.isfinite(crv_for_obj[dpt == bnd[-3]]) \
                    and crv_for_obj[dpt == bnd[-2]] == crv_for_obj[dpt == bnd[-3]]:
                ind_del = np.append(ind_del, len(bnd) - 2)
                ind_del = np.append(ind_del, len(bnd) - 3)
                flag = True
                bnd = [bnd[k] for k in range(len(bnd)) if k not in ind_del]
                ind_del = np.array([], dtype=int)
                continue
    return new_crv, bnd


abs_path = 'app/modules/third/'

# подгрузка обученностей
with open(replaceSlash(abs_path + 'pickle\\poro_light.pickle'), 'rb') as f:
    loadedData = pickle.load(f)
    scaler_porlight = loadedData['scaler']
    mlp_porlight = loadedData['mlp']
with open(replaceSlash(abs_path + 'pickle\\poro_hard.pickle'), 'rb') as f:
    loadedData = pickle.load(f)
    scaler_porhard = loadedData['scaler']
    mlp_porhard = loadedData['mlp']

with open(replaceSlash(abs_path + 'pickle\\soil_light.pickle'), 'rb') as f:
    loadedData = pickle.load(f)
    scaler_solight = loadedData['scaler']
    mlp_solight = loadedData['mlp']
with open(replaceSlash(abs_path + 'pickle\\soil_hard.pickle'), 'rb') as f:
    loadedData = pickle.load(f)
    scaler_sohard = loadedData['scaler']
    mlp_sohard = loadedData['mlp']

with open(replaceSlash(abs_path + "pickle\\MLP_dens.pickle"), 'rb') as f:
    tmp = pickle.load(f)
    scaler_dens = tmp['scaler']
    mlp_dens = tmp['mlp']
with open(replaceSlash(abs_path + "pickle\\MLP_voil.pickle"), 'rb') as f:
    tmp = pickle.load(f)
    scaler_voil = tmp['scaler']
    mlp_voil = tmp['mlp']


def get_interpolation(run_id):
    run_path = abs_path + str(run_id) + '/'
    out_path_log = replaceSlash(run_path + "\\output_data\\Report.txt")
    logging.basicConfig(format=u'%(levelname)-8s : %(message)s', level=logging.WARNING, filename=out_path_log,
                        filemode='w')
    Err_count = 0
    pattern_text_log = '   %s   :   %s'

    wells_list_strat = [str(val) for val in os.listdir(replaceSlash(run_path + "input_data\\stratigraphy"))]
    # wells_list_core  = [str(val) for val in os.listdir("input_data\\wellCore")]
    wells_list_logs = [str(val) for val in os.listdir(replaceSlash(run_path + "input_data\\wellLogs"))]

    wells_list = []
    for wsss in wells_list_strat:
        if wsss in wells_list_logs:
            wells_list.append(wsss)

    # локальный путь к папке обрабатываемых лас-файлов с ГИС
    wellLogsPath = replaceSlash(run_path + "input_data\\wellLogs")
    # локальный путь к папке стратиграфии
    wellTopsPath = replaceSlash(run_path + "input_data\\stratigraphy")

    # регулярные выражения для фильтра имен скважин
    regex = r"[^а-яА-Яa-zA-Z\s\0\^\$\`\~\!\@\"\#\№\;\%\^\:\?\*\(\)\-\_\=\+\\\|\[\]\{\}\,\.\/\'\d]"
    ignoreLiterals = True
    regWellName = r"[^0-9]"
    # прогресс-бар для отображения процесса в консоли
    progress = Bar('   Calculating', max=len(wells_list) + 1, fill='*', suffix='%(percent)d%%')
    progress.next()

    for index in wells_list:

        catalog = []

        path = replaceSlash(joinpath(replaceSlash(wellLogsPath + '\\' + index)))
        try:
            lasFile = [val for val in os.listdir(path) if val.lower().endswith('las')][0]
            path = replaceSlash(joinpath(path, lasFile))
        except:
            logging.error(pattern_text_log, str(index), path + " . " + "can't read LAS- file")
            continue
        # try:
        well = Well(path)
        well.index = index
        # except:
        #     progress.next()
        #     logging.error( pattern_text_log, str(index), path + " . " + "can't read" )
        #     Err_count += 1
        #     continue

        # стратиграфия
        try:
            topsPath = replaceSlash(wellTopsPath + "\\" + index)
            with open(replaceSlash(os.path.join(topsPath, os.listdir(topsPath)[0])), "r") as read_file:
                Tops = json.load(read_file)
                well.tops = [Tops['Lingula_top'], Tops['P2ss2_top'], Tops['P2ss2_bot']]
        except:
            progress.next()
            logging.error(pattern_text_log, str(index), topsPath + " . " + "can't read Stratigraphy")
            Err_count += 1
            continue

        # координаты
        try:
            # coordsPath = replaceSlash("input_data\\coords\\" + index)
            # with open(replaceSlash(os.path.join(coordsPath, os.listdir(coordsPath)[0])), "r") as read_file:
            #    Coords = json.load(read_file)
            #    well.coords = {"X" : Coords['X'], "Y" : Coords['Y'], "RKB" : Coords['RKB']}
            well.coords = dict(X=0, Y=0, RKB=0)
        except:
            progress.next()
            # logging.error( pattern_text_log, str(index), coordsPath + " . " + "can't read Coords" )
            Err_count += 1
            continue

        # стандартизация исходных данных и проверка
        try:
            # стандартизация имен кривых в скважине
            GK_names = ["ГК", "GKV", "GR", "ГK", "gk", "GK1", "гк", "GK:1", "ГК  ", "_ГК", "= GK$"]
            for name in GK_names:
                if name in well.curves.keys():
                    well.curves["GK"] = well.curves[name]

            NGK_names = ["НГК ALFA", "NGL", "НГК", "NKDT", "JB", "JM", "ngk", "NGK:1", "ННКБ", "NNKB", "NNKB  (ННКБ)",
                         "БЗ ННК", "NKTD", "_НГК", "ННК", "_ННК"]
            for name in NGK_names:
                if name in well.curves.keys():
                    well.curves["NGK"] = well.curves[name]

            IK_names = ["ik", "ILD", "ИК", "IK1", "IK:1", "ИK  ", "ИK", "Зонд ИК", "RIK", "ЗОНД ИК", "ИК$", "ИК_N"]
            for name in IK_names:
                if name in well.curves.keys():
                    well.curves["IK"] = well.curves[name]

            # проверка наличичия необходимых кривых в скважине
            if not "GK" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no GK data")
                Err_count += 1
                progress.next()
                continue
            if not "NGK" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no NGK data")
                progress.next()
                continue
            if not "IK" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no IK data")
                progress.next()
                continue
        except Exception as e:
            print(e)
            pass

        try:
            ind = np.logical_and(well.curves["DEPT"] >= well.tops[0] - 1, well.curves["DEPT"] < well.tops[2] + 2)
            ind[np.isnan(well.curves["IK"])] = False
            ind[np.isnan(well.curves["GK"])] = False
            if round(np.corrcoef(well.curves["GK"][ind], well.curves["IK"][ind])[0][1], 2) > 0.5:
                well.curves["IK"] = 1000 / well.curves["IK"]
        except Exception as e:
            print(e)
            pass
        try:
            dept = well.curves["DEPT"]

            sper = np.logical_and(dept >= well.tops[0] - 5, dept <= well.tops[0])
            imaxs = well.curves["NGK"][sper]
            imaxs = np.sort(imaxs)
            imaxs = imaxs[-25:]
            nmax = np.nanmean(imaxs)

            nkDif = well.curves["NGK"] - nmax
            nkDif[nkDif >= 0] = 0
            nkDif[nkDif < 0] = 1
            nkDif = medfilt(nkDif, 13)
            nkDif = medfilt(nkDif, 13)

            ind = np.logical_and(dept >= well.tops[1], dept <= well.tops[2])
            well.curves["Cluster"] = np.nan * np.ones(np.shape(dept), dtype=bool)
            well.curves["Cluster"][ind] = nkDif[ind]

            well.curves["aIK"] = ik_norm(dept, well.curves["IK"], well.curves["Cluster"], well.tops)
        except Exception as e:
            print(e)
            pass

        # POROSITY
        try:
            dept = well.curves["DEPT"]

            c1 = gk_norm(dept, well.curves["GK"], well.tops)
            c2 = nk_norm(dept, well.curves["NGK"], well.tops)

            uc1 = avg_upper(c1, 3, 5)
            uc2 = avg_upper(c2, 3, 5)

            lc1 = avg_lower(c1, 3, 5)
            lc2 = avg_lower(c2, 3, 5)

            uc1s = avg_upper(c1, 8, 5)
            uc2s = avg_upper(c2, 8, 5)

            lc1s = avg_lower(c1, 8, 5)
            lc2s = avg_lower(c2, 8, 5)

            ind = np.logical_and(dept >= well.tops[1] - 10, dept <= well.tops[2] + 10)

            for curve in (c1, c2,
                          uc1, uc2, uc1s, uc2s,
                          lc1, lc2, lc1s, lc2s):
                ind[np.isnan(curve)] = False

            nkDif = well.curves["NGK"] - np.nanmax(
                well.curves["NGK"][np.logical_and(dept >= well.tops[0] - 5, dept <= well.tops[0])])
            nkDif[nkDif < 0] = -1
            nkDif[nkDif > 0] = 1
            nkDif = medfilt(nkDif, 9)
            nkDif = medfilt(nkDif, 9)
            buf = copy.deepcopy(ind)
            ind[nkDif > 0] = False

            features = np.array([c1[ind], c2[ind],
                                 uc1[ind], uc2[ind], uc2s[ind],
                                 lc1[ind], lc2[ind], lc2s[ind], ])

            well.curves["PORO_OPEN_auto"] = np.nan * np.ones(np.shape(dept), dtype=bool)
            well.curves["PORO_OPEN_auto"][ind] = mlp_porlight.predict(scaler_porlight.transform(features.T))

            ind = buf
            ind[nkDif <= 0] = False

            features = np.array([c1[ind], c2[ind],
                                 uc1[ind], uc2[ind], uc2s[ind],
                                 lc1[ind], lc2[ind], lc2s[ind],
                                 ])

            well.curves["PORO_OPEN_auto"][ind] = mlp_porhard.predict(scaler_porhard.transform(features.T))

            well.curves["PORO_OPEN_auto"][well.curves["PORO_OPEN_auto"] < 0] = 0
            well.curves["PORO_OPEN_auto"][well.curves["PORO_OPEN_auto"] > 0.45] = 0.45
            well.curves["PORO_OPEN_auto"] *= 100
        except Exception as e:
            print('porosity ' + index)
            print(e)
            pass

        # DENSITY
        try:
            dept = well.curves["DEPT"]
            c2 = nk_normd(dept, well.curves["NGK"], well.tops)
            c1 = c2
            c2 = savgol_filter(c2, 31, 3)

            ind = np.logical_and(dept >= well.tops[1], dept < well.tops[2])

            for curve in (c1, c2):
                ind[np.isnan(curve)] = False

            features = np.array([c1[ind], c2[ind]])

            well.curves["VOLUME_DENSITY_auto"] = np.nan * np.ones(np.shape(dept), dtype=bool)
            well.curves["VOLUME_DENSITY_auto"][ind] = mlp_dens.predict(scaler_dens.transform(features.T))

            if "VOLUME_DENSITY" in well.curves.keys():
                snd = np.logical_and(dept >= well.tops[1] - 5, dept < well.tops[2] + 5)
                dif = np.nanmean(well.curves["VOLUME_DENSITY"][snd]) - np.nanmean(
                    well.curves["VOLUME_DENSITY_auto"][snd])
                if np.isfinite(dif): well.curves["VOLUME_DENSITY_auto"] += dif

            well.curves["VOLUME_DENSITY_auto"][well.curves["VOLUME_DENSITY_auto"] < 0] = 0
            well.curves["VOLUME_DENSITY_auto"][well.curves["VOLUME_DENSITY_auto"] > 4] = 4
        except BaseException as e:
            print('Density ' + index)
            print(e)
        # except:
        #    pass

        # SOIL_LIGHT
        try:
            dept = well.curves["DEPT"]

            mid = well.tops[1] + (well.tops[2] - well.tops[1]) / 2
            ind = np.logical_and(dept >= well.tops[1], dept <= mid)

            c1 = well.curves["aIK"]

            ind[well.curves["Cluster"] == 0] = False

            well.curves["SOIL_MASS_auto"] = np.nan * np.ones(np.shape(dept))
            well.curves["SOIL_MASS_auto"][ind] = 8 * c1[ind] - 4

            if np.nanmax(well.curves["SOIL_MASS_auto"][ind]) > 14:
                well.curves["SOIL_MASS_auto"][ind] = well.curves["SOIL_MASS_auto"][ind] / np.nanmax(
                    well.curves["SOIL_MASS_auto"][ind]) * 14
            (well.curves["SOIL_MASS_auto"][ind])[well.curves["SOIL_MASS_auto"][ind] < 5] = np.nan
            well.curves["SOIL_MASS_auto"][ind] /= 15

            well.curves["SOIL_MASS_auto"][well.curves["SOIL_MASS_auto"] < 0] = 0
        except Exception as e:
            print('soil_light ' + index)
            print(e)
            pass

        # SOIL_HARD
        try:
            dept = well.curves["DEPT"]
            ind = np.logical_and(dept >= well.tops[1] - 10, dept <= well.tops[2] + 10)

            c0 = gk_norm(dept, well.curves["GK"], well.tops)
            c1 = nk_norm(dept, well.curves["IK"], well.tops)
            c2 = nk_norm(dept, well.curves["NGK"], well.tops)

            uc1 = avg_upper(c1, 3, 5)
            uc2 = avg_upper(c2, 3, 5)

            lc1 = avg_lower(c1, 3, 5)
            lc2 = avg_lower(c2, 3, 5)

            uc1s = avg_upper(c1, 8, 5)
            uc2s = avg_upper(c2, 8, 5)

            lc1s = avg_lower(c1, 8, 5)
            lc2s = avg_lower(c2, 8, 5)

            for curve in (c0, c1, c2,
                          uc1, uc2, uc1s, uc2s,
                          lc1, lc2, lc1s, lc2s):
                ind[np.isnan(curve)] = False

            ind[np.isfinite(well.curves["SOIL_MASS_auto"])] = False

            buf = copy.deepcopy(ind)

            ind[well.curves["Cluster"] == 0] = False

            features = np.array([c0[ind], c1[ind], c2[ind],
                                 uc1[ind], uc2[ind], uc2s[ind],
                                 lc1[ind], lc2[ind], lc2s[ind],
                                 ])

            well.curves["SOIL_MASS_auto"][ind] = mlp_solight.predict(scaler_solight.transform(features.T))

            ind = buf
            ind[well.curves["Cluster"] == 1] = False

            features = np.array([c0[ind], c1[ind], c2[ind],
                                 uc1[ind], uc2[ind], uc2s[ind],
                                 lc1[ind], lc2[ind], lc2s[ind],
                                 ])
            well.curves["SOIL_MASS_auto"][ind] = mlp_sohard.predict(scaler_sohard.transform(features.T))

            well.curves["SOIL_MASS_auto"] *= 15
            well.curves["SOIL_MASS_auto"][well.curves["SOIL_MASS_auto"] < 0] = 0
            well.curves["SOIL_MASS_auto"][well.curves["SOIL_MASS_auto"] > 15] = 15
        except Exception as e:
            print('soil_hard ' + index)
            print(e)
            pass
        # cluster 2 gash
        try:
            dept = well.curves["DEPT"]
            well.curves["Cluster"][nk_sper(dept, well.curves["NGK"], well.tops) >= 2] = 2
            for rep in range(5): well.curves["Cluster"] = medfilt(well.curves["Cluster"], 13)
            well.curves["SOIL_MASS_auto"][well.curves["Cluster"] == 2] = 0
        except Exception as e:
            print('cluster 2 gash ' + index)
            print(e)
            pass

        try:
            for name in ["PORO_OPEN_auto", "SOIL_MASS_auto"]:
                core = name[:-5]
                if not core in well.curves.keys(): continue
                mid = well.tops[1] - 5 + (well.tops[2] + 5 - well.tops[1] - 5) / 2
                snd1 = np.logical_and(well.curves["DEPT"] >= well.tops[1], well.curves["DEPT"] < mid)
                snd2 = np.logical_and(well.curves["DEPT"] >= mid, well.curves["DEPT"] < well.tops[2] + 5)
                for zone in [snd1, snd2]:
                    for i in [0, 1, 2]:
                        ind = np.logical_and(zone, well.curves["Cluster"] == i)
                        dif = np.nanmean(well.curves[core][ind]) - np.nanmean(well.curves[name][ind])
                        if np.isfinite(dif): well.curves[name][ind] += dif
        except Exception as e:
            print(e)
            pass

        try:
            well.curves["SOIL_MASS_auto"][well.curves["SOIL_MASS_auto"] < 0] = 0
            well.curves["SOIL_MASS_auto"][well.curves["SOIL_MASS_auto"] > 15] = 15
            well.curves["PORO_OPEN_auto"][well.curves["PORO_OPEN_auto"] < 0] = 0
            well.curves["PORO_OPEN_auto"][well.curves["PORO_OPEN_auto"] > 45] = 45
        except Exception as e:
            print(e)
            pass

        # VOL_SOIL
        try:
            dept = well.curves["DEPT"]
            c1 = well.curves["SOIL_MASS_auto"]
            c2 = well.curves["PORO_OPEN_auto"] / 100

            ind = np.logical_and(dept >= well.tops[1], dept < well.tops[2])

            for curve in (c1, c2): ind[np.isnan(curve)] = False

            features = np.array([c1[ind], c2[ind]])

            well.curves["SOIL_VOL_auto"] = np.nan * np.ones(np.shape(dept), dtype=bool)
            well.curves["SOIL_VOL_auto"][ind] = mlp_voil.predict(scaler_voil.transform(features.T))

            if "SOIL_VOL" in well.curves.keys():
                snd = np.logical_and(dept >= well.tops[1] - 5, dept <= well.tops[2] + 5)
                dif = np.nanmean(well.curves["SOIL_VOL"][snd]) / 100 - np.nanmean(well.curves["SOIL_VOL_auto"][snd])

                flag = True
                if "SOIL_MASS" in well.curves.keys():
                    n1 = np.isfinite(well.curves["SOIL_MASS"])
                    n2 = np.isfinite(well.curves["SOIL_VOL"])
                    if len(n1[n1 == True]) >= len(n2[n2 == True]) * 2: flag = False

                if flag and np.isfinite(dif): well.curves["SOIL_VOL_auto"] += dif

            well.curves["SOIL_VOL_auto"][well.curves["SOIL_VOL_auto"] < 0] = 0
            well.curves["SOIL_VOL_auto"][well.curves["SOIL_VOL_auto"] > 1] = 1

            well.curves["SOIL_VOL_auto"] *= 100
        except Exception as e:
            print("vol_soil " + index)
            print(e)
            continue

        try:
            name = "SOIL_VOL_auto"
            core = name[:-5]
            if not core in well.curves.keys(): continue
            mid = well.tops[1] + (well.tops[2] - well.tops[1]) / 2
            snd1 = np.logical_and(well.curves["DEPT"] >= well.tops[1], well.curves["DEPT"] < mid)
            snd2 = np.logical_and(well.curves["DEPT"] >= mid, well.curves["DEPT"] < well.tops[2])
            for zone in [snd1, snd2]:
                for i in [0, 1, 2]:
                    ind = np.logical_and(zone, well.curves["Cluster"] == i)
                    dif = np.nanmean(well.curves[core][ind]) - np.nanmean(well.curves[name][ind])
                    if np.isfinite(dif): well.curves[name][ind] += dif

            well.curves["SOIL_VOL_auto"][well.curves["SOIL_VOL_auto"] < 0] = 0
            well.curves["SOIL_VOL_auto"][well.curves["SOIL_VOL_auto"] > 100] = 100
        except Exception as e:
            print("soil_vol_auto " + index)
            print(e)
            pass
        try:
            ind = np.logical_or(well.curves["DEPT"] <= well.tops[1], well.curves["DEPT"] >= well.tops[2])
            for key in ["SOIL_VOL_auto", "PORO_OPEN_auto", "SOIL_MASS_auto", "VOLUME_DENSITY_auto"]:
                well.curves[key][ind] = np.nan
        except Exception as e:
            print(e)
            pass

        try:
            well.curves["SOIL_VOL_auto"] *= 0.01
            well.curves["PORO_OPEN_auto"] *= 0.01
        except Exception as e:
            print(e)
            pass

        outPath = replaceSlash(run_path + 'output_data' + "\\" + well.index)
        if not os.path.exists(outPath): os.makedirs(outPath)

        # plot
        try:
            fig, f = plt.subplots(figsize=(20, 18), nrows=1, ncols=6, sharey=True)
            fig.suptitle(well.name, fontsize=30)

            dmin = well.tops[0]
            dmax = well.tops[2]

            try:
                f[0].set_ylim(well.tops[0] - 10, well.tops[2] + 10)
            except Exception as e:
                print(e)
                pass

            ind = np.logical_and(well.curves["DEPT"] >= dmin - 10, well.curves["DEPT"] < dmax + 10)

            f[0].set_ylabel("DEPT, m", fontsize=16)
            f[0].plot(gk_norm(well.curves["DEPT"], well.curves["GK"], well.tops), well.curves["DEPT"], 'r')
            f[0].plot(nk_norm(well.curves["DEPT"], well.curves["NGK"], well.tops), well.curves["DEPT"], 'k')
            f[0].set_xlabel("GK_NK_norm", fontsize=16)
            f[0].set_xlim(0, 2)
            f[0].invert_yaxis()
            f[0].grid()
            f[0].axhline(y=well.tops[0], linewidth=2, color='k')
            f[0].axhline(y=well.tops[1], linewidth=2, color='k')
            f[0].axhline(y=well.tops[2], linewidth=2, color='k')

            f[1].plot(well.curves["IK"], well.curves["DEPT"], 'k')
            f[1].set_xlabel("IK", fontsize=16)
            f[1].set_xlim(0, 100)
            # f[1].invert_yaxis()
            f[1].grid()
            f[1].axhline(y=well.tops[0], linewidth=2, color='k')
            f[1].axhline(y=well.tops[1], linewidth=2, color='k')
            f[1].axhline(y=well.tops[2], linewidth=2, color='k')

            f[2].plot(well.curves["PORO_OPEN"] / 100, well.curves["DEPT"], 'r', linestyle='', marker='o', markersize=10)
            f[2].plot(well.curves["PORO_OPEN_auto"], well.curves["DEPT"], 'k', linewidth=2)
            # f[2].set_ylim(well.tops[0] - 6, well.tops[2] + 10)
            f[2].set_xlabel("PORO_OPEN, p.u.", fontsize=16)
            f[2].set_xlim(0, 0.45)
            # f[2].invert_yaxis()
            f[2].grid()
            f[2].axhline(y=well.tops[0], linewidth=2, color='k')
            f[2].axhline(y=well.tops[1], linewidth=2, color='k')
            f[2].axhline(y=well.tops[2], linewidth=2, color='k')

            f[3].plot(well.curves["SOIL_MASS"], well.curves["DEPT"], 'r', linestyle='', marker='o', markersize=10)
            f[3].plot(well.curves["SOIL_MASS_auto"], well.curves["DEPT"], 'k', linewidth=2)
            f[3].set_xlabel("SOIL_MASS, %", fontsize=16)
            # f[3].invert_yaxis()
            f[3].grid()
            f[3].axhline(y=well.tops[0], linewidth=2, color='k')
            f[3].axhline(y=well.tops[1], linewidth=2, color='k')
            f[3].axhline(y=well.tops[2], linewidth=2, color='k')
            f[3].set_xlim(0, 15)

            f[4].plot(well.curves["SOIL_VOL"] / 100, well.curves["DEPT"], 'r', linestyle='', marker='o', markersize=10)
            f[4].plot(well.curves["SOIL_VOL_auto"], well.curves["DEPT"], 'k', linewidth=2)
            f[4].set_xlabel("SOIL_VOL, p.u.", fontsize=16)
            # f[4].invert_yaxis()
            f[4].grid()
            f[4].axhline(y=well.tops[0], linewidth=2, color='k')
            f[4].axhline(y=well.tops[1], linewidth=2, color='k')
            f[4].axhline(y=well.tops[2], linewidth=2, color='k')
            f[4].set_xlim(0, 1)

            f[5].plot(well.curves["VOLUME_DENSITY"], well.curves["DEPT"], 'r', linestyle='', marker='o', markersize=10)
            f[5].plot(well.curves["VOLUME_DENSITY_auto"], well.curves["DEPT"], 'k', linewidth=2)
            f[5].set_xlabel("VOLUME_DENSITY, p.u.", fontsize=16)
            # f[5].invert_yaxis()
            f[5].grid()
            f[5].axhline(y=well.tops[0], linewidth=2, color='k')
            f[5].axhline(y=well.tops[1], linewidth=2, color='k')
            f[5].axhline(y=well.tops[2], linewidth=2, color='k')
            f[5].set_xlim(1, 3.5)

            plt.savefig(replaceSlash(outPath + '\\' + str(well.name) + ".png"))
        except BaseException as e:
            logging.error(pattern_text_log, str(well.index), str(e))
            Err_count += 1

        # aGK_auto
        try:
            if "GK" in well.curves and 'DEPT' in well.curves:
                # first method
                # gmax = np.nanmax(well.curves["GK"])
                # well.curves["aGK"] = 1 - (gmax - well.curves["GK"])/gmax

                # second method
                ind_list = [i for i in range(len(well.curves['DEPT'])) if
                            well.tops[0] <= well.curves['DEPT'][i] <= well.tops[1]]
                ind_list_2 = [i for i in range(len(well.curves['DEPT'])) if
                              well.tops[1] <= well.curves['DEPT'][i] <= well.tops[2]]
                gmax = np.nanmax(well.curves["GK"][ind_list[0]:ind_list[-1]]) * 0.95
                gmin = np.nanmin(well.curves["GK"][ind_list_2[0]:ind_list_2[-1]]) * 1.05
                gkn = 1 - (gmax - well.curves["GK"]) / (gmax - gmin)
                gkn[gkn > 1] = 1
                gkn[gkn < 0] = 0
                well.curves["aGK_auto"] = gkn
            else:
                logging.warning('У скважины {} отсутствует GK или DEPT'.format(well.name))
        except BaseException as e:
            logging.error("Ошибка при расчете aGK_auto: ", str(e))

        # PERM_HOR_auto
        try:

            # ind_list = np.where(np.isfinite(well.curves['PERM_HOR']))[0]
            # xp = [well.curves['DEPT'][i] for i in ind_list]
            # yp = [well.curves['PERM_HOR'][i] for i in ind_list]
            # xx = [well.curves['DEPT'][i] for j in range(len(ind_list)-1) for i in range(ind_list[j]+1, ind_list[j+1])]
            # res = np.interp(xx, xp, yp)
            # shift = 0
            # well.curves['PERM_HOR_auto'] = well.curves['PERM_HOR']
            # for j in range(len(ind_list)-1):
            #    start, end = ind_list[j]+1, ind_list[j+1]
            #    el_num = end - start
            #    well.curves['PERM_HOR'][start:end] = res[shift:shift + el_num]
            #    shift += el_num

            if 'PORO_OPEN_auto' in well.curves and 'PERM_HOR' in well.curves and 'Cluster' in well.curves and 'DEPT' in well.curves:
                well.curves['PERM_HOR_auto'] = np.power(10., -0.669784 + 0.173226 * well.curves[
                    'PORO_OPEN_auto'] * 100 - 0.00146718 * np.power(well.curves['PORO_OPEN_auto'] * 100, 2))

                mid = well.tops[1] - 5 + (well.tops[2] + 5 - well.tops[1] - 5) / 2
                snd2 = np.logical_and(well.curves["DEPT"] >= mid, well.curves["DEPT"] < well.tops[2] + 5)
                snd2 = np.logical_and(well.curves["DEPT"] >= mid, well.curves["DEPT"] < well.tops[2])

                Clusterz = np.nan * np.ones(len(well.curves['DEPT']))
                cur_clust = None
                clust = None
                cur_ind = -1
                for i in range(len(well.curves['Cluster'])):
                    if np.isnan(well.curves['Cluster'][i]): continue
                    cur_clust = well.curves['Cluster'][i]
                    if cur_clust != clust:
                        clust = cur_clust
                        cur_ind += 1
                    Clusterz[i] = cur_ind

                for zone in [snd1, snd2]:
                    for i in range(cur_ind + 1):
                        ind = np.logical_and(zone, Clusterz == i)
                        dif = np.nanmean(well.curves['PERM_HOR'][ind]) - np.nanmean(well.curves['PERM_HOR_auto'][ind])
                        if np.isfinite(dif):
                            well.curves['PERM_HOR_auto'][ind] += dif
                well.curves["PERM_HOR_auto"][well.curves["PERM_HOR_auto"] < 0] = 0
            else:
                wrn_msg = 'Для скважины {} отсутствует: DEPT, PORO_OPEN_auto, PERM_HOR или Cluster'.format(well.name)
                print(wrn_msg)
                logging(wrn_msg)

        except BaseException as e:
            logging.error("Ошибка при расчете PERM_HOR_auto: ", str(e))

        # las-data
        try:
            las = copy.deepcopy(lasio.LASFile())
            las.well['WELL'].value = well.name
            las.add_curve("DEPT", data=well.curves["DEPT"], descr='')
            for name in well.curves.keys():
                if name != "DEPT":
                    las.add_curve(name, data=well.curves[name], descr='')

            las.write(replaceSlash(outPath + '\\' + str(well.name) + '.las'), version=2.0)
            # las.write(replaceSlash('C:\\yarullin_ad\\Актуальная цепочка микросервисов СВН\\3KernInterpolisPyApp_05_02_2020\\las\\' + str(well.name) + '.las'), version=2.0)
        except BaseException as e:
            logging.error(pattern_text_log, str(well.index), str(e))
            Err_count += 1

        # catalog
        try:
            wellFlag = False
            layerFlag = False

            layerName = "P2ss2_top"
            tops = well.tops[1:]

            hStep = well.curves['DEPT'][1] - well.curves['DEPT'][0]
            ind = np.logical_and(well.curves['DEPT'] >= tops[0], well.curves['DEPT'] <= tops[1] + hStep + 1e-3)
            dpt = well.curves["DEPT"][ind]

            sat = 26 * np.ones(len(well.curves["DEPT"]))[ind]
            kp = well.curves["PORO_OPEN_auto"][ind]
            kn = well.curves["SOIL_VOL_auto"][ind]
            knm = well.curves["SOIL_MASS_auto"][ind]
            agk_auto = well.curves["aGK_auto"][ind]
            perm_hor_auto = well.curves["PERM_HOR_auto"][ind]

            if "Z" in well.curves.keys():
                tvd = well.curves["Z"][ind]
            else:
                tvd = well.curves["DEPT"][ind] - well.coords["RKB"]

            Kp_new, bnd = Boundary_averaging(sat, dpt, kp)

            for ind in range(len(bnd) - 1):

                ind_cut = np.logical_and(dpt >= bnd[ind], dpt <= bnd[ind + 1])
                sat_type = mode(sat[ind_cut])[0][0]

                top_dept = bnd[ind]
                bot_dept = bnd[ind + 1]

                if abs(bot_dept - top_dept) <= 0.11:
                    continue
                if ind + 2 < len(bnd) and (
                        sat[dpt == bnd[ind + 2]] != sat[dpt == bnd[ind + 1]] or bnd[ind + 2] - bnd[
                    ind + 1] < 0.1 + 1e-3):
                    bot_dept += hStep

                top_tvd = round(tvd[abs(dpt - top_dept) < 1e-3][0], 1)
                bot_tvd = round(tvd[abs(dpt - bot_dept) < 1e-3][0], 1)

                Ho = round(abs(top_tvd - bot_tvd), 1)

                if abs(sat_type - 26.0) < 1e-3 or abs(sat_type - 96.0) < 1e-3:
                    Hn = round(abs(top_tvd - bot_tvd), 1)
                    Hv = 0
                elif abs(sat_type - 28.0) < 1e-3:
                    Hn = 0
                    Hv = round(abs(top_tvd - bot_tvd), 1)
                else:
                    Hn = 0
                    Hv = 0

                md0 = tops[0]
                z0 = round(tvd[dpt == md0][0], 1)

                md1 = tops[1]
                md1 = min(dpt[-1], md1)
                z1 = round(tvd[dpt == md1][0], 1)

                kp_avg = round(np.nanmean(kp[ind_cut]), 2)
                kn_avg = round(np.nanmean(kn[ind_cut]), 2)
                knm_avg = round(np.nanmean(knm[ind_cut]), 2)
                agk_auto_avg = round(np.nanmean(agk_auto[ind_cut]), 2)
                perm_hor_auto_avg = round(np.nanmean(perm_hor_auto[ind_cut]), 2)

                if not wellFlag:
                    catalog.append([well.name, well.coords["RKB"]])
                    wellFlag = True
                    well.name = ''
                else:
                    well.name = ''

                if not layerFlag:
                    catalog.append([well.name, layerName, round(md0, 1), round(md1, 1), z0, z1, abs(z1 - z0), 0, 0])
                    layerFlag = True
                    layerName = ''
                else:
                    layerName = ''

                catalog.append([well.name, layerName,
                                round(top_dept, 1), round(bot_dept, 1),
                                top_tvd, bot_tvd,
                                Ho, Hn, Hv,
                                kp_avg, kn_avg, knm_avg, agk_auto_avg, perm_hor_auto_avg
                                ])

            i = 0
            while i < len(catalog):

                if not catalog[i][0] == '':
                    i += 1
                    continue

                if not catalog[i][1] == '':

                    i0 = i
                    i += 1

                    nsum = 0
                    vsum = 0

                    while i < len(catalog):

                        nsum += catalog[i][7]
                        vsum += catalog[i][8]

                        i += 1
                        if i >= len(catalog) or not catalog[i][0] == '' or not catalog[i][1] == '':
                            break

                    catalog[i0][7] = nsum
                    catalog[i0][8] = vsum

            for i in range(len(catalog)):
                for j in range(len(catalog[i])):
                    try:
                        if np.isnan(catalog[i][j]): catalog[i][j] = '-'
                    except:
                        pass
        except Exception as e:
            print(e)
            pass

        Save_Excel(replaceSlash(run_path + 'output_data' + "\\" + well.index + "\\" + "Catalog.xlsx"), catalog)

        progress.next()

    if Err_count == 0:
        logging.addLevelName(100, "INFO")
        logging.log(100, pattern_text_log, "", "No errors in data")

    print()
    print()
    print("Interpretation successfully finished")
    print()
