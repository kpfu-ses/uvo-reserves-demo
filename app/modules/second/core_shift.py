# -*- coding: utf-8 -*-
import codecs
import lasio
import sys
import os
import re

import warnings

warnings.filterwarnings("ignore")
import logging

import numpy as np

import xlsxwriter
import pandas as pd
import json

from progress.bar import Bar
import matplotlib.pyplot as plt

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



# Функция сбора лас файлов в папке и во всех вложенных папках
def getFilePaths(wellLogsPath):
    list = [val for val in os.listdir(wellLogsPath)]
    list = [(wellLogsPath + '/' + list[i]).replace('\\', '/') for i in range(len(list))]
    paths = [fileOrPath for fileOrPath in list if os.path.isdir(fileOrPath)]
    files = [fileOrPath for fileOrPath in list if os.path.isfile(fileOrPath) and fileOrPath.lower().endswith('las')]
    for path in paths:
        files.extend(getFilePaths(path))
    return files


class WellClass:
    def __init__(self, name):
        self.name = name
        self.curves = {}
        self.keys = []
        self.list = None
        self.wellData = {}
        self.header = None


class LasInfo:
    def __init__(self, filePath, minDept, maxDept, step, encoding, las):
        self.filePath = filePath
        self.minDept = minDept
        self.maxDept = maxDept
        self.step = step
        self.encoding = encoding
        self.las = las


class CurveInfo:
    def __init__(self, unit, descr, original_mnemonic, mnemonic, file):
        self.unit = unit
        self.descr = descr
        self.original_mnemonic = original_mnemonic
        self.mnemonic = mnemonic
        self.file = file


# Доступные Python кодировки для подбора при чтении лас-файлов
encodincs = ['ascii', 'utf_8', 'cp1251', 'cp866', 'utf_8_sig', 'cp1252', 'big5',
             'big5hkscs', 'cp037', 'cp273', 'cp424', 'cp437',
             'cp500', 'cp720', 'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856',
             'cp857', 'cp858', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865',
             'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006',
             'cp1026', 'cp1125', 'cp1140', 'cp1250', 'cp1253',
             'cp1254', 'cp1255', 'cp1256', 'cp1257', 'cp1258', 'cp65001', 'euc_jp',
             'euc_jis_2004', 'euc_jisx0213', 'euc_kr', 'gb2312', 'gbk', 'gb18030',
             'hz', 'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2', 'iso2022_jp_2004',
             'iso2022_jp_3', 'iso2022_jp_ext', 'iso2022_kr', 'latin_1', 'iso8859_2',
             'iso8859_3', 'iso8859_4', 'iso8859_5', 'iso8859_6', 'iso8859_7', 'iso8859_8',
             'iso8859_9', 'iso8859_10', 'iso8859_11', 'iso8859_13', 'iso8859_14',
             'iso8859_15', 'iso8859_16', 'johab', 'koi8_r', 'koi8_t', 'koi8_u', 'kz1048',
             'mac_cyrillic', 'mac_greek', 'mac_iceland', 'mac_latin2', 'mac_roman',
             'mac_turkish', 'ptcp154', 'shift_jis', 'shift_jis_2004', 'shift_jisx0213',
             'utf_32', 'utf_32_be', 'utf_32_le', 'utf_16', 'utf_16_be', 'utf_16_le', 'utf_7']


# Попытка поправить линию в шапке
def createLine(line):
    newLine = ''
    p = line.split(':')
    newLine = newLine + p[0] + '. :'
    for i in range(1, len(p)):
        newLine = newLine + p[i]
    return newLine


# Попытка локализовать и устранить ошибку в .las файле
def checkAndFixLas(file, encoding):
    f = codecs.open(file, 'r', encoding=encoding)
    text = f.read().split('\n')
    f.close()
    needFix = False
    i = 0
    while text[i].lower().find('~curve') == -1:
        i = i + 1
    i = i + 1
    while text[i].find('~') == -1:
        line = text[i]
        if line.find(':') != -1:
            if line.find('.') == -1 or line.find('.') > line.rfind(':'):
                needFix = True
                newLine = createLine(line)
                text[i] = newLine
        else:
            if line.find('.') != -1:
                needFix = True
                p = line.split('.')
                newLine = p[0] + '. :'
                for k in range(1, len(p)):
                    newLine = newLine + p[k]
                text[i] = newLine
        i = i + 1
    if needFix == True:
        file = file.replace('.las', '').replace('.LAS', '') + '(copy).las'
        f = codecs.open(file, 'w', encoding=encoding)
        for line in text:
            f.write(line + '\n')
        f.close()
        return file
    return file


# Интерполяция для построения общей сетки глубин сшиваемых лас-файлов
def newMesh(CRV, DEPT, new_mesh):
    if abs(DEPT[0] - new_mesh[0]) < 1e-5 and len(new_mesh) == len(DEPT):
        return CRV
    else:
        new_crv = np.interp(new_mesh, DEPT, CRV, left=np.nan, right=np.nan)
        return new_crv


def parse_json(json_path, pattern_text_log):
    def get_num(json_path):
        start_idx = json_path.rfind('/') if json_path.rfind('/') != -1 else json_path.rfind('\\')
        return json_path[start_idx + 1:json_path.rfind('.')]

    with open(json_path, 'r') as f:
        s_json = ''
        for line in f:
            s_json += line
    s_json = s_json.replace('\n', '')
    s_json = s_json.replace(' ', '')
    s_json = s_json.replace('\\"', '"')
    s_json = s_json.replace('"[', '[')
    s_json = s_json.replace(']"', ']')

    s_json = json.loads(s_json)
    try:
        json_df = pd.DataFrame(s_json[0]['result'])
        # json_df = pd.read_json(json_path)
    except:
        return None, None, None
    wname_b = get_num(json_path)

    df = pd.DataFrame(columns=['Well_number', '№ об раз ца', 'Cored_interval_start',
                               'Cored_interval_end', 'вынос керна, м',
                               'место взятия образца по керну, м', 'горизонт', 'DEPT', 'Lithotype',
                               'тип насыщения', 'минералогич. плотность, г/см3', 'Volume_density',
                               'PORO_open', 'SOIL_mass', 'SOIL_vol', 'эффективная пористость, %',
                               'PERM_hor', 'PERM_vert',
                               'параметр  пористости', 'SWIRR',
                               'параметр насыщения', 'Средний диаметр поровых каналов'])
    important_fields = ['interval', 'parameters', 'original_location', 'oil_saturation', 'bulk_density', 'litho_type']
    for field in important_fields:
        if field not in json_df.columns:
            logging.error(pattern_text_log, str(wname_b), "В данных отсутствует информация по " + field)

    for i in range(len(json_df)):
        df.loc[i, 'Well_number'] = wname_b
        df.loc[i, '№ об раз ца'] = json_df.loc[i, 'num']
        df.loc[i, 'Cored_interval_start'] = json_df.loc[i, 'interval'][
            'start'] if 'interval' in json_df.columns else None
        df.loc[i, 'Cored_interval_end'] = json_df.loc[i, 'interval']['end'] if 'interval' in json_df.columns else None
        df.loc[i, 'вынос керна, м'] = json_df.loc[i, 'removal'] if 'removal' in json_df.columns else None
        df.loc[i, 'место взятия образца по керну, м'] = json_df.loc[
            i, 'original_location'] if 'original_location' in json_df.columns else None
        df.loc[i, 'горизонт'] = json_df.loc[i, 'split'] if 'split' in json_df.columns else None
        df.loc[i, 'Lithotype'] = json_df.loc[i, 'litho_type'] if 'litho_type' in json_df.columns else None
        df.loc[i, 'тип насыщения'] = json_df.loc[i, 'saturation_type'] if 'saturation_type' in json_df.columns else None

        df.loc[i, 'Volume_density'] = json_df.loc[i, 'bulk_density'] if 'bulk_density' in json_df.columns else None
        df.loc[i, 'PORO_open'] = json_df.loc[i, 'open_porosity'] if 'open_porosity' in json_df.columns else None
        df.loc[i, 'SOIL_mass'] = json_df.loc[i, 'oil_saturation'][
            'weight'] if 'oil_saturation' in json_df.columns else None
        df.loc[i, 'SOIL_vol'] = json_df.loc[i, 'oil_saturation'][
            'volumetric'] if 'oil_saturation' in json_df.columns else None
        df.loc[i, 'эффективная пористость, %'] = json_df.loc[
            i, 'eff_porosity'] if 'eff_porosity' in json_df.columns else None
        df.loc[i, 'PERM_hor'] = json_df.loc[i, 'gas_permeability'][
            'parallel'] if 'gas_permeability' in json_df.columns else None
        df.loc[i, 'PERM_vert'] = json_df.loc[i, 'gas_permeability'][
            'perpendicular'] if 'gas_permeability' in json_df.columns else None
        df.loc[i, 'параметр  пористости'] = json_df.loc[i, 'parameters'][
            'porosity'] if 'parameters' in json_df.columns else None
        df.loc[i, 'SWIRR'] = json_df.loc[i, 'water_content']['related'] if 'water_content' in json_df.columns else None
        df.loc[i, 'параметр насыщения'] = json_df.loc[i, 'parameters'][
            'saturation'] if 'parameters' in json_df.columns else None

    #     df.loc[i, 'Средний диаметр поровых каналов'] = json_df.loc[i, 'open_porosity']
    # print(df['Cored_interval_start'], df['место взятия образца по керну, м'])
    name_well = df["Well_number"].values[0]

    for i in df.columns[1:]:
        df[i] = df[i].astype(str).replace(" ", "", regex=True)
        df[i] = df[i].replace(",", ".", regex=True)
        if i == "Lithotype":
            df[i] = df[i].apply(lambda x: str(x).split("/")[0])
        df[i] = pd.to_numeric(df[i], errors='coerce')

    df['DEPT'] = df['Cored_interval_start'].fillna(method='ffill')
    df['DEPT'] += df['место взятия образца по керну, м']
    place_dept = np.where(df.columns == 'DEPT')[0][0]
    df = df.drop_duplicates(subset=['DEPT'], keep='last')

    return df, name_well, place_dept


def get_step(lito):
    i_gl = 0

    soul_p = [2, 10, 18, 19, 51]

    i_sl = None
    for i in range(i_gl, len(lito)):
        if not np.isnan(lito[i]):
            if lito[i] in soul_p:
                i_sl = i
                break
    return i_sl


# Увязка керновой плотности на нейтронный каротаж
def GetShift(dept, ik, nk, kbit, kdens, span_shift, lito):
    # dept, crv1, crv2, kbit, kden, span_shift, step0
    # try:
    h = dept[1] - dept[0]

    corr = 1e+9
    shift = 0

    c1 = np.array([])
    c2 = np.array([])

    steps = np.array([])
    ceoff = np.array([])
    ncc_k = max(abs(span_shift[0]), abs(span_shift[1]))

    for step in np.arange(span_shift[0], span_shift[1] + 1):

        if step > 0:
            kbit1 = np.hstack((np.nan * np.ones(step), kbit[:-step]))
            lito1 = np.hstack((np.nan * np.ones(step), lito[:-step]))
            kdens1 = np.hstack((np.nan * np.ones(step), kdens[:-step]))
        elif step < 0:
            kbit1 = np.hstack((kbit[-step:], np.nan * np.ones(-step)))
            lito1 = np.hstack((lito[-step:], np.nan * np.ones(-step)))
            kdens1 = np.hstack((kdens[-step:], np.nan * np.ones(-step)))
        else:
            kbit1 = kbit
            lito1 = lito
            kdens1 = kdens

        ind1 = np.ones(len(ik), dtype=bool)
        ind1[np.isnan(ik)] = False
        ind1[np.isnan(kbit1)] = False

        ind2 = np.ones(len(nk), dtype=bool)
        ind2[np.isnan(nk)] = False
        ind2[np.isnan(kdens1)] = False

        dind = np.logical_and(ind1, np.logical_and(kdens1 <= 2.1, kbit >= 5))

        c1 = np.append(c1, np.corrcoef(ik[dind], kbit1[dind])[1][0])
        c2 = np.append(c2, np.corrcoef(nk[ind2], kdens1[ind2])[1][0])

        steps = np.append(steps, step)

        val_coef = 1 - abs(step) / (ncc_k + 1)
        ceoff = np.append(ceoff, val_coef)

        if np.isnan(c1[-1]):
            c1[-1] = -1

    z = ((c1 + c2) + ceoff)

    shift = int(steps[z == np.nanmax(z)][0])

    return shift, round(c1[z == np.nanmax(z)][0], 2), round(c2[z == np.nanmax(z)][0], 2), np.nanmax(z)
    # except:
    #    return np.nan


def get_linking(run_id, wells_list):
    abs_path = 'app/modules/second/'
    run_path = abs_path + str(run_id) + '/'
    out_path_log = replaceSlash(run_path + "\\output_data\\Report.txt")
    logging.basicConfig(format=u'%(levelname)-8s : %(message)s', level=logging.WARNING, filename=out_path_log,
                        filemode='w')
    Err_count = 0
    pattern_text_log = '   %s   :   %s'

    # регулярные выражения для фильтра имен скважин
    regex = r"[^а-яА-Яa-zA-Z\s\0\^\$\`\~\!\@\"\#\№\;\%\^\:\?\*\(\)\-\_\=\+\\\|\[\]\{\}\,\.\/\'\d]"
    ignoreLiterals = True
    regWellName = r"[^0-9]"

    # локальный путь к папке обрабатываемых лас-файлов с ГИС
    wellLogsPath = run_path + "input_data\\wellLogs"
    # локальный путь к папке обрабатываемых эксель-файлов с керном
    wellCorePath = run_path + "input_data\\wellCore"
    # локальный путь к папке стратиграфии
    wellTopsPath = run_path + "input_data\\stratigraphy"

    coreNames = []
    wells = []
    log = []
    for index in wells_list:

        wellsLasFiles = {}
        wellsInfo = {}

        files = getFilePaths(os.path.abspath(replaceSlash(wellLogsPath + "\\" + index)))
        for file in files:

            file = replaceSlash(file)

            enc = 'None'
            maxLen = 999999
            maybeEnc = 'ascii'

            for e in encodincs:
                try:
                    cod = codecs.open(file, 'r', encoding=e)
                    l = str(cod.read())
                    l = l.replace(' ', '')
                    check = re.findall(regex, l)
                    curLen = len(check)
                    if curLen != 0:
                        if curLen < maxLen:
                            maxLen = curLen
                            maybeEnc = e
                    else:
                        enc = e
                        break
                except:
                    pass

            if enc == 'None': enc = maybeEnc
            if enc != 'None':
                try:
                    try:
                        f = lasio.read(file, encoding=enc)
                    except:
                        newFile = checkAndFixLas(file, enc)
                        f = lasio.read(newFile, encoding=enc, ignore_header_errors=True)
                    if str(f.well['WELL'].value) == '':
                        log.append(file)
                        log.append('No wellname')
                        continue
                    try:
                        lasInfoObj = LasInfo(file, f[f.keys()[0]][0], f[f.keys()[0]][-1],
                                             f[f.keys()[0]][1] - f[f.keys()[0]][0], enc, f)
                    except Exception as exc:
                        log.append(file)
                        log.append(str(exc))
                        continue
                    wellName = re.sub(regWellName, '', str(f.well['WELL'].value)).replace(' ', '') if (
                            ignoreLiterals == True and not isinstance(str(f.well['WELL'].value), float)) else str(
                        f.well['WELL'].value)
                    if not wellName in wellsLasFiles.keys():
                        wellsLasFiles[wellName] = []
                    wellsLasFiles[wellName].append(lasInfoObj)
                except Exception as e:
                    log.append(file)
                    log.append(str(e))

        for wellName in wellsLasFiles.keys():
            try:
                globalMinDept = (wellsLasFiles.get(wellName)[0]).minDept
                globalMaxDept = (wellsLasFiles.get(wellName)[0]).maxDept
                globalMinStep = (wellsLasFiles.get(wellName)[0]).step
                for lasInfoObject in wellsLasFiles.get(wellName):
                    minn = lasInfoObject.minDept
                    maxx = lasInfoObject.maxDept
                    step = lasInfoObject.step
                    if minn < globalMinDept:
                        globalMinDept = minn
                    if maxx > globalMaxDept:
                        globalMaxDept = maxx
                globalMinStep = 0.1
                newWell = WellClass(wellName)
                dept = np.round(np.arange(globalMinDept, globalMaxDept, globalMinStep), 1)
                if dept[-1] != np.round(globalMaxDept, 1):
                    dept = np.hstack((dept, np.round(globalMaxDept, 1)))
                globalShape = len(dept)
                curves = {}
                curvesInfo = {}
                curves['DEPT'] = dept
            except Exception as exc:
                print(index, wellName)
                print(exc)
                pass

            unexpectedError = False
            downloadedFiles = 0

            for lasInfoObject in wellsLasFiles.get(wellName):
                try:
                    crvNames = [lasInfoObject.las.keys()[i] for i in range(0, len(lasInfoObject.las.keys()))]
                    if 'UNKNOWN' in crvNames:
                        log.append(lasInfoObject.filePath)
                        log.append('Unexpected curve name')
                        continue
                    crvs = ''

                    for crv in range(1, len(lasInfoObject.las.curves.keys()) - 1):
                        crvs = crvs + lasInfoObject.las.curves.keys()[crv] + ', '

                    crvs = crvs + lasInfoObject.las.curves.keys()[len(lasInfoObject.las.curves.keys()) - 1]
                    previousInfo = lasInfoObject.las.curves
                    localDept = np.round(lasInfoObject.las[lasInfoObject.las.keys()[0]], 1)

                    try:
                        curvesInfo['DEPT'] = CurveInfo(previousInfo[0].unit, previousInfo[0].descr, 'DEPT', 'DEPT',
                                                       lasInfoObject.filePath)
                    except:
                        curvesInfo['DEPT'] = CurveInfo('', '', 'DEPT', 'DEPT', lasInfoObject.filePath)

                    for i in range(1, len(lasInfoObject.las.keys())):
                        try:
                            try:
                                curveName = lasInfoObject.las.keys()[i]
                                newCurveName = curveName
                            except:
                                continue
                            try:
                                if curveName in curves.keys():
                                    count = 1
                                    while newCurveName in curves.keys():
                                        if count > 1:
                                            newCurveName = newCurveName[:-1]
                                        newCurveName = newCurveName + str(count)
                                        count = count + 1
                            except Exception as exc:
                                print(index, wellName)
                                print(exc)
                                pass
                            newCurve = newMesh(lasInfoObject.las[curveName], localDept, dept)
                            curves[newCurveName] = newCurve
                            try:
                                curvesInfo[newCurveName] = CurveInfo(previousInfo[curveName].unit,
                                                                     previousInfo[curveName].descr,
                                                                     previousInfo[curveName].original_mnemonic,
                                                                     curveName,
                                                                     lasInfoObject.filePath)
                            except Exception as exc:
                                print(index, wellName)
                                print(exc)
                                pass
                                curvesInfo[newCurveName] = CurveInfo('', '', curveName, curveName,
                                                                     lasInfoObject.filePath)
                        except Exception as exc:
                            pass
                            print(index, wellName)
                            print(exc)

                    downloadedFiles += 1

                except Exception as e:
                    log.append(lasInfoObject.filePath)
                    log.append(str(e))

            if downloadedFiles == 0:
                unexpectedError = True

            if not unexpectedError:
                wellsInfo[wellName] = curvesInfo
                newWell.curves = curves
                newWell.keys = curves.keys()
                newWell.index = index

            # стратиграфия
            try:
                topsPath = replaceSlash(wellTopsPath + "\\" + index)
                with open(replaceSlash(
                        os.path.join(topsPath,
                                     [file for file in os.listdir(topsPath) if file.lower().endswith('json')][0])),
                        "r") as read_file:
                    xlsTops = json.load(read_file)
                    newWell.tops = [xlsTops['Lingula_top'], xlsTops['P2ss2_top'], xlsTops['P2ss2_bot']]
            except:
                logging.error(pattern_text_log, str(wellName), "ошибка чтения")
                Err_count += 1
                continue

            # Добавляем информацию по керну
            indWellPath = replaceSlash(wellCorePath + "\\" + index)
            filePaths = [replaceSlash(os.path.join(indWellPath, file)) for file in os.listdir(indWellPath) if
                         not file.startswith('.')]
            if len(filePaths) > 1:
                logging.warning(pattern_text_log, str(indWellPath),
                                "в указанной директории находятся более одного файла. ")

            for i in filePaths:
                try:
                    dataFrame, name_well, dept = parse_json(i, pattern_text_log)

                    if dataFrame is None:
                        continue
                    curves_core = {}
                    for i in range(dept, len(dataFrame.columns)):
                        curves_core[dataFrame.columns[i]] = np.array(
                            [value for value in dataFrame[dataFrame.columns[i]]])
                        if dataFrame.columns[i] not in coreNames and not dataFrame.columns[i] == 'DEPT':
                            coreNames.append(dataFrame.columns[i])

                    for key in curves_core.keys():
                        if not key == "DEPT":
                            newWell.curves[key] = np.nan * np.ones(len(newWell.curves["DEPT"]))
                            for i in range(len(curves_core["DEPT"])):
                                dept = curves_core["DEPT"][i]
                                newWell.curves[key][np.round(newWell.curves["DEPT"], 1) == round(dept, 1)] = \
                                curves_core[key][i]
                    break
                except Exception as e:
                    logging.error(pattern_text_log, str(index), str(i) + ". " + str(e))
                    Err_count += 1
            wells.append(newWell)
    # прогресс-бар для отображения процесса в консоли
    progress = Bar('   Core shifting', max=len(wells) + 1, fill='*', suffix='%(percent)d%%')
    progress.next()

    wells_crvs = {}

    Warns = ''
    for well in wells:
        try:
            Res_table = []
            # стандартизация имен кривых в скважине

            GK_names = ["gkv", "gr", "gk", "gk1", "гк", "gk:1", "гк  ", "_гк", "= gk$"]
            IK_names = ["ik", "ild", "ик", "ik1", "ik:1", "ик  ", "иk", "зонд ик", "rik", "ик$", "ик_n"]
            NGK_names = ["нгк alfa", "ngl", "нгк", "nkdt", "jb", "jm", "ngk", "ngk:1", "ннкб", "nnkb", "nnkb  (ннкб)",
                         "бз ннк", "nktd", "бз", "_нгк", "ннк", "_ннк"]
            MD_names = ["dept", "md", "depth"]

            go_keys = list(well.curves.keys())
            for name_crv in go_keys:
                if str(name_crv).lower() in GK_names:
                    well.curves["GK"] = well.curves[name_crv]
                    continue

                if str(name_crv).lower() in IK_names:
                    well.curves["IK"] = well.curves[name_crv]
                    continue

                if str(name_crv).lower() in NGK_names:
                    well.curves["NGK"] = well.curves[name_crv]
                    continue

                if str(name_crv).lower() in MD_names:
                    well.curves["DEPT"] = well.curves[name_crv]
                    continue

            # проверка наличичия необходимых кривых в скважине
            if not "GK" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no GK data")
                Err_count += 1
                progress.next()
                continue
            if not "NGK" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no NGK data")
                Err_count += 1
                progress.next()
                continue
            if not "IK" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no IK data")
                Err_count += 1
                progress.next()
                continue

            if not "Volume_density" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no Volume_density in curves keys")
                Err_count += 1
                progress.next()
                continue
            if not "SOIL_mass" in well.curves.keys():
                logging.error(pattern_text_log, str(well.index), "no SOIL_mass in curves keys")
                Err_count += 1
                progress.next()
                continue

            dept = well.curves["DEPT"]
            kden = well.curves["Volume_density"]
            kbit = well.curves["SOIL_mass"]
            lito = well.curves['Lithotype']

            if len(lito[~np.isnan(lito)]) <= 2:
                logging.error(pattern_text_log, str(well.index), "Недостаточно данных для расчетов : Lithotype")
                Err_count += 1
                progress.next()
                continue
            if len(kbit[~np.isnan(kbit)]) <= 2:
                logging.error(pattern_text_log, str(well.index), "Недостаточно данных для расчетов : SOIL_mass")
                Err_count += 1
                progress.next()
                continue
            if len(kden[~np.isnan(kden)]) <= 2:
                logging.error(pattern_text_log, str(well.index), "Недостаточно данных для расчетов : Volume_density")
                Err_count += 1
                progress.next()
                continue

            for i in range(len(kden)):
                if not np.isnan(kden[i]) and kden[i] > 4:
                    lito[i] = np.nan

            # Volume_density

            crv1 = well.curves["IK"]
            crv2 = well.curves["NGK"]

            kbit1 = np.copy(kbit)
            kden1 = np.copy(kden)
            lito1 = np.copy(lito)

            ind = np.isfinite(kden)
            kden1 = np.interp(dept, dept[ind], kden[ind], left=np.nan, right=np.nan)

            ind = np.isfinite(kbit)
            kbit1 = np.interp(dept, dept[ind], kbit[ind], left=np.nan, right=np.nan)

            I0 = get_step(lito)

            if I0 is None:
                logging.warning(pattern_text_log, str(well.index), "не установлена связь с данными <Lithotype>")
                progress.next()
                continue

            de_Dept = well.tops[1] - dept[I0]
            if de_Dept >= 0:
                if abs(de_Dept) >= 3.0:
                    logging.error(pattern_text_log, str(well.index),
                                  "необходима проверка стратиграфии, интервал отбора выходит за пределы песчаной пачки")
                    Err_count += 1
                    progress.next()
                    continue
            else:
                if abs(de_Dept) >= 7.0:
                    logging.error(pattern_text_log, str(well.index),
                                  "необходима проверка стратиграфии, интервал отбора выходит за пределы песчаной пачки")
                    Err_count += 1
                    progress.next()
                    continue

            wind_cc = 3.1
            up_sp = max(dept[I0] - wind_cc, well.tops[1])
            lft_prt = len(dept[np.logical_and(dept >= dept[I0], dept <= dept[I0] + wind_cc)])
            dpu_d = max(dept[I0] - wind_cc, well.tops[1])
            ii_di = np.nanargmin(np.abs(dept - dpu_d))
            rgt_prt = ii_di - I0
            dpt_span_cc = [rgt_prt, lft_prt]

            step, cc1, cc2, ccz = GetShift(dept, crv1, crv2, kbit, kden, dpt_span_cc, lito)

            cheS_d = dept[I0 + step]
            if abs(well.tops[1] - cheS_d) >= 4.0:
                logging.error(pattern_text_log, str(well.index),
                              "необходима проверка стратиграфии, интервал отбора выходит за пределы песчаной пачки")
                Err_count += 1
                progress.next()
                continue

            Res_table.append([well.name, round(step / 10, 1)])

            if step > 0:
                kbit = np.hstack((np.nan * np.ones(step), kbit[:-step]))
                kbit1 = np.hstack((np.nan * np.ones(step), kbit1[:-step]))
            else:
                kbit = np.hstack((kbit[-step:], np.nan * np.ones(-step)))
                kbit1 = np.hstack((kbit1[-step:], np.nan * np.ones(-step)))
            if step > 0:
                kden = np.hstack((np.nan * np.ones(step), kden[:-step]))
                kden1 = np.hstack((np.nan * np.ones(step), kden1[:-step]))
            else:
                kden = np.hstack((kden[-step:], np.nan * np.ones(-step)))
                kden1 = np.hstack((kden1[-step:], np.nan * np.ones(-step)))

            for name in coreNames:
                if name in well.curves.keys():
                    if step > 0:
                        well.curves[name] = np.hstack((np.nan * np.ones(step), well.curves[name][:-step]))
                    else:
                        well.curves[name] = np.hstack((well.curves[name][-step:], np.nan * np.ones(-step)))

            fig, f = plt.subplots(figsize=(20, 12), nrows=1, ncols=6, sharey=True)
            fig.suptitle("№" + well.name + ":  " + str(step / 10) + 'm', fontsize=30)

            dmin = dept[np.isfinite(kden)][0]
            dmax = dept[np.isfinite(kden)][-1]

            try:
                f[0].set_ylim(well.tops[0] - 5, well.tops[2] + 5)
            except Exception as exc:
                print(well)
                print(exc)
            pass
            f[0].plot(well.curves["GK"][~np.isnan(well.curves["GK"])], well.curves["DEPT"][~np.isnan(well.curves["GK"])],
                      'r', label='GK')
            f[0].set_xlabel("GK", fontsize=16)

            zone = np.logical_and(dept >= dmin - 5, dept <= dmax + 5)

            f[0].set_ylabel("DEPT, m", fontsize=16)
            f[0].invert_yaxis()
            f[0].grid()
            f[0].set_xlim(np.nanmin(well.curves["GK"][zone]), np.nanmax(well.curves["GK"][zone]))
            f[0].axhline(y=well.tops[0], linewidth=2, color='k')
            f[0].axhline(y=well.tops[1], linewidth=2, color='k')
            f[0].axhline(y=well.tops[2], linewidth=2, color='k')

            f[1].plot(well.curves["NGK"][~np.isnan(well.curves["NGK"])], well.curves["DEPT"][~np.isnan(well.curves["NGK"])],
                      'k', label='NGK')
            f[1].set_xlabel("NGK", fontsize=16)
            f[1].invert_yaxis()
            f[1].grid()
            f[1].set_xlim(0, np.nanmax(well.curves["NGK"][zone]))
            f[1].axhline(y=well.tops[0], linewidth=2, color='k')
            f[1].axhline(y=well.tops[1], linewidth=2, color='k')
            f[1].axhline(y=well.tops[2], linewidth=2, color='k')

            f[2].plot(well.curves["IK"][~np.isnan(well.curves["IK"])], well.curves["DEPT"][~np.isnan(well.curves["IK"])],
                      'k', label='IK')
            f[2].set_xlabel("IK", fontsize=16)
            f[2].set_ylabel("DEPT, m", fontsize=16)
            f[2].invert_yaxis()
            f[2].grid()
            f[2].set_xlim(np.nanmin(well.curves["IK"][zone]), np.nanmax(well.curves["IK"][zone]))
            f[2].axhline(y=well.tops[0], linewidth=2, color='k')
            f[2].axhline(y=well.tops[1], linewidth=2, color='k')
            f[2].axhline(y=well.tops[2], linewidth=2, color='k')

            f[3].plot(kbit, well.curves["DEPT"], 'g', marker='o', markersize=8, linestyle='None')
            f[3].plot(kbit1, well.curves["DEPT"], 'b')
            f[3].set_xlabel("MASS.SOIL", fontsize=16)
            f[3].invert_yaxis()
            f[3].grid()
            f[3].set_xlim(0, 15)
            f[3].axhline(y=well.tops[0], linewidth=2, color='k')
            f[3].axhline(y=well.tops[1], linewidth=2, color='k')
            f[3].axhline(y=well.tops[2], linewidth=2, color='k')

            f[4].plot(kden, well.curves["DEPT"], 'g', marker='o', markersize=8, linestyle='None')
            f[4].plot(kden1, well.curves["DEPT"], 'b')
            f[4].set_xlabel("VOL.DENSITY", fontsize=16)
            f[4].invert_yaxis()
            f[4].grid()
            f[4].set_xlim(1.6, 2.7)
            f[4].axhline(y=well.tops[0], linewidth=2, color='k')
            f[4].axhline(y=well.tops[1], linewidth=2, color='k')
            f[4].axhline(y=well.tops[2], linewidth=2, color='k')

            try:
                f[5].plot(well.curves["Lithotype"], well.curves["DEPT"], 'g', marker='o', markersize=8, linestyle='None')
                f[5].set_xlabel("Lithotype", fontsize=16)
                f[5].invert_yaxis()
                f[5].grid()
                f[5].axhline(y=well.tops[0], linewidth=2, color='k')
                f[5].axhline(y=well.tops[1], linewidth=2, color='k')
                f[5].axhline(y=well.tops[2], linewidth=2, color='k')
            except Exception as exc:
                print(well)
                print(exc)
            pass

            wells_crvs[well.name] = {'params': {'tops': [well.tops[0], well.tops[1], well.tops[2]], 'zone': zone},
                                     'x': {
                                         'GK': well.curves['GK'],
                                         'NGK': well.curves['NGK'],
                                         'IK': well.curves['IK'],
                                         'MASS.SOIL': [kbit, kbit1],
                                         'VOL.DENSITY': [kden, kden1],
                                         'Lithotype': well.curves['Lithotype']
                                     }, 'y': well.curves["DEPT"]}


            outPath = replaceSlash(run_path + 'output_data/' + well.index)
            if not os.path.exists(outPath): os.makedirs(outPath)
            plt.savefig(replaceSlash(outPath + '/' + str(well.name) + ".png"))

            las = copy.deepcopy(lasio.LASFile())
            las.well['WELL'].value = well.name

            las.add_curve("DEPT", data=well.curves["DEPT"], descr='')
            for name in well.curves.keys():
                if name != "DEPT":
                    las.add_curve(name, data=well.curves[name], descr='')

            with open(replaceSlash(outPath + '/' + str(well.name) + '.las'), mode='w', encoding='utf-8') as f:
                las.write(f, version=2.0)

            workbook = xlsxwriter.Workbook(replaceSlash(outPath + '/' + "Results.xlsx"))
            worksheet = workbook.add_worksheet('KFB')
            bold = workbook.add_format({'bold': True})
            worksheet.write('A1', 'Well', bold)
            worksheet.write('B1', 'Shift, m.', bold)

            row = 1
            for wellData in Res_table:
                for position, value in enumerate(wellData):
                    worksheet.write(row, position, value)
                row += 1
            workbook.close()

            progress.next()
        except BaseException as e:
            logging.error(pattern_text_log, str(well.index), str(e))
            Err_count += 1

    if Err_count == 0:
        logging.addLevelName(100, "INFO")
        logging.log(100, pattern_text_log, "", "No errors in data")

    print()
    print()
    print("Interpretation successfully finished")
    print()

    return wells_crvs

