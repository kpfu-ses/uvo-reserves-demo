import codecs
import lasio
import sys
import os
import re

import logging
import warnings

warnings.filterwarnings("ignore")

from scipy.signal import savgol_filter
import numpy as np
import math
from scipy.signal import argrelextrema
import xlsxwriter
import json
import pickle
from progress.bar import Bar
import matplotlib.pyplot as plt

abs_path = 'app/modules/1/'


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


def replaceMultiple(mainString, toBeReplaces, newString):
    for elem in toBeReplaces:
        if elem in mainString: mainString = mainString.replace(elem, newString)
    return mainString


class WellClass:
    def __init__(self, name):
        self.name = name
        self.curves = {}
        self.keys = []
        self.index = None
        self.list = None
        self.wellData = {}
        self.header = None
        self.bounds = None
        self.segments = None


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
        new_crv = np.interp(new_mesh, DEPT[~np.isnan(CRV)], CRV[~np.isnan(CRV)], left=np.nan, right=np.nan)
        # new_crv = np.interp(new_mesh, DEPT, CRV, left=np.nan, right=np.nan)
        return new_crv


# выгрузка в .xlsx автоматических отбивок
def output_stratigraphy(table):
    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook('Stratigraphy.xlsx')
    worksheet = workbook.add_worksheet('NeuroPower')

    # Bold format to use to highlight cells.
    bold = workbook.add_format({'bold': True})

    # Write some data headers.
    worksheet.write('A1', 'Well', bold)
    worksheet.write('B1', 'Lingula_top', bold)
    worksheet.write('C1', 'P2ss2_top', bold)
    worksheet.write('D1', 'P2ss2_bot', bold)

    # Iterate over the data and write it out row by row.
    row = 1
    for well_data in (table):
        for position, value in enumerate(well_data):
            worksheet.write(row, position, value)
        row += 1

    workbook.close()


class search_ClayTop(object):
    def __init__(self, gk, nk, ik, dpt):
        self.gk = gk
        self.nk = nk
        self.ik = ik
        self.dpt = dpt

        self.My_Top = None
        self.IndTop = None
        self.myClay = None

    def get_nu_sigma(self, f):
        nu = np.nanmean(f)
        sigma = math.sqrt(np.nanvar(f))
        return nu, sigma

    def med_fltr(self, f):
        res = np.ones(len(f)) * np.nan
        for i in range(2, len(f) - 1):
            if np.isnan(f[i]):
                continue
            val = np.nanmedian(f[i - 3: i + 2])
            res[i] = val
        return res

    def get_ints(self, dept, crv, extrems):
        boundaries = [dept[~np.isnan(crv)][0]]
        for i in range(1, len(extrems) - 1):
            try:

                crvAvg = (crv[extrems[i]] + crv[extrems[i + 1]]) / 2

                dx = dept[extrems[i]: extrems[i + 1] + 1]

                try:
                    v1 = dx[crv[extrems[i]: extrems[i + 1] + 1] <= crvAvg][0]
                    v2 = dx[crv[extrems[i]: extrems[i + 1] + 1] <= crvAvg][-1]
                except:
                    v1 = dept[extrems[i]]
                    v2 = dept[extrems[i]]

                if abs(crv[dept == v1] - crvAvg) < abs(crv[dept == v2] - crvAvg):
                    boundaries.append(v1)
                else:
                    boundaries.append(v2)
            except Exception as exc:
                print(exc)
                pass

        boundaries.append(dept[~np.isnan(crv)][-1])
        boundaries = list(set(boundaries))
        boundaries.sort()

        return boundaries

    def dop_func4bnd_fltr(self, dpt, bnd, f):
        res = np.ones(len(dpt)) * np.nan
        for i in range(len(dpt)):
            if dpt[i] in bnd:
                res[i] = dpt[i]
        return res

    def norm(self, f):
        return (f - np.nanmin(f)) / (np.nanmax(f) - np.nanmin(f))

    def get_feat1(self, gk, nk, bnds):
        # delte RK
        def get_left_val(dRK, i):
            I = 0.0
            n = 100
            Nmin = max(i - 55, 0)
            dRK_cut = dRK[Nmin: i]
            I = len(dRK_cut[dRK_cut >= 0]) / len(dRK_cut)
            return I, len(dRK_cut[dRK_cut >= 0])

        def get_right_val(dRK, i):
            I = 0.0
            n = 100
            Nmax = min(i + 55, len(dRK))
            dRK_cut = dRK[i: Nmax]
            I = len(dRK_cut[dRK_cut <= 0]) / len(dRK_cut)
            return I, len(dRK_cut[dRK_cut <= 0])

        dRK = gk - (nk + 0.35)

        res = np.ones(len(gk)) * np.nan

        for i in range(10, len(gk) - 10):
            if not np.isnan(bnds[i]):
                Ileft, nl = get_left_val(dRK, i)
                Iright, nr = get_right_val(dRK, i)

                if nl <= 20 or nr <= 20:
                    val = 0.0
                else:
                    val = (Ileft + Iright)

                res[i] = val

        return self.norm(res)

    def phi(self, x, nu, sigms2):
        a = 1 / (math.sqrt(2 * math.pi * sigms2))
        b = ((x - nu) * (x - nu)) / (2 * sigms2)
        c = math.exp(-b)
        res = a * c
        return res

    def function_ro(self, f, k, span=77, ind0=0):
        val_0k = 0
        val_kN = 0

        ind_l = ind0
        ind_r = min(len(f), k + span)

        x1_mean = np.nanmean(f[ind_l: k])
        s1_dsp2 = np.nanvar(f[ind_l: k])

        x2_mean = np.nanmean(f[k + 1: ind_r])
        s2_dsp2 = np.nanvar(f[k + 1: ind_r])

        for i in range(k):
            if not np.isnan(f[i]):
                val_0k += math.log1p(self.phi(f[i], x1_mean, s1_dsp2))
        for i in range(k + 1, len(f) - 1):
            if not np.isnan(f[i]):
                val_kN += math.log1p(self.phi(f[i], x2_mean, s2_dsp2))

        result = val_0k + val_kN
        return result, [x1_mean, x2_mean]

    def feat_bot_corr(self, gk, bnd, ind0=0):
        def get_koef_f(f, k):
            span1 = 50
            span2 = 50
            ind1 = max(0, k - span1)
            ind2 = min(len(f) - 1, k + span2)

            max_val = np.nanmax(f)
            min_val = np.nanmin(f)
            Pow = max_val - min_val
            left_val = np.nanmax(f) - 0.1 * Pow

            k1 = 1 - (left_val - np.nanmean(f[ind1: k])) / Pow

            k2 = 1 - (np.nanmean(f[k + 1: ind2]) - min_val) / Pow

            return (k1 + k2) / 2

        dx_top = 20
        dx_bot = 20
        f = np.copy(gk)

        N = len(f)

        PowerF = np.nanmax(f) - np.nanmin(f)
        span2 = 200

        feat = np.ones(N) * np.nan
        for k in range(dx_top, N - dx_bot):
            if not np.isnan(bnd[k]):
                val, x_mean = self.function_ro(f, k, 77, ind0)

                koef = (x_mean[0] - x_mean[1]) / PowerF

                feat[k] = val * koef

        return self.norm(feat)

    def get_feat2(self, gk, nk, ik, bnds):

        res = np.ones(len(gk)) * np.nan
        koef = gk - nk

        for i in range(10, len(gk) - 10):
            if not np.isnan(bnds[i]):
                il = max(i - 13, 0)
                ir = min(i + 13, len(gk))
                kl = max(i - 53, 0)

                val1 = math.sqrt(np.nanvar(gk[il: ir]))
                val2 = math.sqrt(np.nanvar(nk[il: ir]))
                val3 = math.sqrt(np.nanvar(ik[il: ir]))
                valk = np.nanmean(koef[kl: i])

                res[i] = valk * (val1 + val2 + val3)

        return self.norm(res)

    def get_feat3(self, gk, nk, ik, bnds):

        def get_val_feat(dRK, ik, i):
            IndR = None
            old_val = None
            for l in range(i, -1, -1):
                var_l = len(dRK[l - 5: l + 6][dRK[l - 5: l + 6] > 0]) / len(dRK[l - 5: l + 6])
                if old_val is None:
                    old_val = var_l
                    continue

                if var_l <= 0.7 and old_val >= var_l:
                    IndR = l
                    break
                else:
                    pass
                old_val = var_l

            if IndR is None or abs(IndR - i) < 15:
                return 0.0
            else:
                minIn = max(IndR - 25, 0)
                maxIn = min(i + 55, len(ik))
                Rik = (np.nanmean(ik[i + 5: maxIn]) + np.nanmax(ik[i + 5: maxIn])) / 2
                Lik = (np.nanmean(ik[minIn: IndR]) + np.nanmax(ik[minIn: IndR])) / 2
                Aik = np.nanmean(ik[IndR + 1: i - 1])
                val = ((Lik - Aik) + (Rik - Aik)) / 2
            return val

        dRK = gk - nk
        res = np.ones(len(gk)) * np.nan
        for i in range(9, len(gk) - 10):
            if not np.isnan(bnds[i]):

                try:
                    val = get_val_feat(dRK, ik, i)
                except:
                    val = 0
                res[i] = val
        return self.norm(res)

    def get_extr_crv(self, crv):
        crv_max = argrelextrema(crv, np.greater_equal, order=4, mode='wrap')[0]
        crv_min = argrelextrema(crv, np.less_equal, order=4, mode='wrap')[0]

        extr = np.hstack((crv_max, crv_min))
        extr = list(set(extr))
        extr = np.sort(extr)

        extr_crv = np.ones(len(crv)) * np.nan
        for ie in extr:
            extr_crv[ie] = crv[ie]
        return extr_crv

    def get_coef_K(self, drk_a, i, I1):
        drk1 = drk_a[i + 7: I1 - 4]
        Ir = len(drk1[drk1 > 0.0])
        Nr = len(drk1)
        ind_l = [max(i - 45, 0), max(i - 5, 0)]
        drk2 = drk_a[ind_l[0]: ind_l[1]]
        Il = len(drk2[drk2 > 0.0])
        Nl = len(drk2)
        gol = 0
        for i in range(ind_l[0], 0, -1):
            if gol >= 2:
                break
            if drk_a[i] > 0:
                Il += 1
            else:
                gol += 1
        if (Ir / Nr) <= 0.75:
            res = 0
        else:
            res = (Ir + Il) / (Nr + Nl)
        return min(2.0, res)

    def get_feat_please(self, _gk, _nk, _ik, I1, MaxIk):

        I0 = max(I1 - 345, 5)

        drk = _gk - _nk

        gk = self.get_extr_crv(_gk)  # np.copy(_gk) #
        nk = self.get_extr_crv(_nk)  # np.copy(_nk) #

        ik = np.copy(_ik)
        for i in range(len(ik)):
            if ik[i] > MaxIk:
                vlik = MaxIk - ik[i]
                ik[i] += vlik
        ik = self.get_extr_crv(ik)

        gk[0: I0] = np.nan
        gk[I1 + 1:] = np.nan
        ik[0: I0] = np.nan
        ik[I1 + 1:] = np.nan
        nk[0: I0] = np.nan
        nk[I1 + 1:] = np.nan

        gk = self.norm(-gk)
        nk = self.norm(nk)
        ik = self.norm(ik)

        span = 5
        res = np.ones(len(_gk)) * np.nan
        for i in range(I0, I1 - 15):
            try:
                s1 = np.nanmax(gk[i - 5: i + 6]) + np.nanmax(nk[i - 5: i + 6]) + np.nanmax(ik[i - 5: i + 6])
                k1 = self.get_coef_K(drk, i, I1)
                res[i] = k1 * s1
            except Exception as exc:
                print(exc)
                pass
        return res

    def cor_clay(self, gk, nk, ik, dpt, myClayInd, Itop):

        wnd = 25

        if myClayInd + wnd <= Itop - 5:
            span = [myClayInd, min(myClayInd + wnd + 1, Itop)]
            gk_var = np.ones(len(gk)) * np.nan
            nk_var = np.ones(len(nk)) * np.nan
            ik_var = np.ones(len(ik)) * np.nan

            for i in range(span[0], span[1]):
                if ((gk[i + 1] > gk[i]) and (nk[i + 1] < nk[i])) or (ik[i - 1] > ik[i] and ik[i] >= ik[i + 1]):
                    var_gk = np.nanvar(gk[i - 5: i + 6])
                    var_nk = np.nanvar(nk[i - 5: i + 6])
                    var_ik = np.nanvar(ik[i - 5: i + 6])

                    gk_var[i] = var_gk
                    nk_var[i] = var_nk
                    ik_var[i] = var_ik

            sum_var = (gk_var) + (nk_var) + (ik_var)
            res = dpt[np.nanargmax(sum_var)]
        else:
            res = dpt[myClayInd]
        return res

    def get_Top(self):
        gk = self.gk[~np.isnan(self.ik)]
        nk = self.nk[~np.isnan(self.ik)]
        dpt = self.dpt[~np.isnan(self.ik)]
        ik = self.ik[~np.isnan(self.ik)]

        # fig, f = plt.subplots(nrows = 1, ncols = 2, sharey = True, figsize = (11,16))
        # fig.suptitle("Well #" + str(well.name), fontsize=30)
        #
        #
        ##f[0].plot(gk[~np.isnan(gk)],  dept[~np.isnan(gk)], 'r')
        # f[0].plot(gk, dpt, 'r')
        # ax1 = f[0].twiny()
        # ax1.plot(nk, dpt, 'k')
        # f[1].plot(ik, dpt, 'y')

        top_gk = gk[dpt >= 40]
        top_nk = nk[dpt >= 40]
        top_ik = ik[dpt >= 40]
        top_dpt = dpt[dpt >= 40]

        try:
            top_gk = self.med_fltr(top_gk)
        except Exception as exc:
            print(exc)
            pass
        try:
            top_nk = self.med_fltr(top_nk)
        except Exception as exc:
            print(exc)
            pass
        try:
            top_ik = self.med_fltr(top_ik)
        except Exception as exc:
            print(exc)
            pass
        nu, sigma = self.get_nu_sigma(top_gk)
        top_gk = (top_gk - nu) / sigma

        nu, sigma = self.get_nu_sigma(top_nk)
        top_nk = (top_nk - nu) / sigma

        nu, sigma = self.get_nu_sigma(top_ik)
        top_ik = (top_ik - nu) / sigma

        gk_max = argrelextrema(top_gk, np.greater_equal, order=4, mode='wrap')[0]
        gk_min = argrelextrema(top_gk, np.less_equal, order=4, mode='wrap')[0]
        extr = np.hstack((gk_max, gk_min))
        extr = list(set(extr))
        extr = np.sort(extr)

        bnds = self.get_ints(top_dpt, top_gk, extr)
        bnds = self.dop_func4bnd_fltr(top_dpt, bnds, top_gk)

        try:
            feat1 = self.get_feat1(top_gk, top_nk, bnds)
        except:
            feat1 = np.zeros(len(top_gk))

        try:
            feat2 = self.feat_bot_corr(top_gk, bnds)
        except:
            feat2 = np.zeros(len(top_gk))

        try:
            feat3 = self.get_feat2(top_gk, top_nk, top_ik, bnds)
        except:
            feat3 = np.zeros(len(top_gk))

        try:
            feat4 = self.get_feat3(top_gk, top_nk, top_ik, bnds)
        except:
            feat4 = np.zeros(len(top_gk))

        FEAT_TOP = np.zeros(len(feat1))
        for j in range(len(feat1)):
            if np.isnan(feat1[j]):
                bool_f1 = False
            else:
                bool_f1 = True
            if np.isnan(feat2[j]):
                bool_f2 = False
            else:
                bool_f2 = True
            if np.isnan(feat3[j]):
                bool_f3 = False
            else:
                bool_f3 = True
            if np.isnan(feat4[j]):
                bool_f4 = False
            else:
                bool_f4 = True
            bools = np.array([bool_f1, bool_f2, bool_f3, bool_f3], dtype=bool)
            if len([bools[bools == True]]) >= 1:
                if bool_f1:
                    FEAT_TOP[j] += feat1[j]
                if bool_f2:
                    FEAT_TOP[j] += feat2[j]
                if bool_f3:
                    FEAT_TOP[j] += feat3[j]
                if bool_f4:
                    FEAT_TOP[j] += feat4[j]

        ind_max_top = np.nanargmax(FEAT_TOP)
        self.My_Top = top_dpt[ind_max_top]

        # f[0].axhline(y = self.My_Top, linewidth = 3, color = 'g')
        # f[1].axhline(y = self.My_Top, linewidth = 3, color = 'g')
        #
        # f[0].set_xlabel("GK / NK", fontsize=30)
        # f[1].set_xlabel("IK", fontsize=30)
        # f[0].set_ylim(0, np.nanmax(dpt))
        # f[0].grid()
        # f[1].grid()
        # f[0].invert_yaxis()
        # plt.show()

        self.IndTop = np.nanargmin(np.abs(dpt - self.My_Top))

    def get_Clay(self):
        gk = self.gk[~np.isnan(self.ik)]
        nk = self.nk[~np.isnan(self.ik)]
        dpt = self.dpt[~np.isnan(self.ik)]
        ik = self.ik[~np.isnan(self.ik)]

        gk = self.med_fltr(gk)
        nk = self.med_fltr(nk)
        ik = self.med_fltr(ik)

        nu, sigma = self.get_nu_sigma(gk)
        gk = (gk - nu) / sigma

        nu, sigma = self.get_nu_sigma(nk)
        nk = (nk - nu) / sigma

        nu, sigma = self.get_nu_sigma(ik)
        ik = (ik - nu) / sigma

        max_indF1 = self.IndTop

        masx_IKJ_1 = (np.nanmax(ik[max_indF1 + 10: max_indF1 + 100]) - np.nanmin(ik[max_indF1 + 10: max_indF1 + 100]))
        masx_IKJ = np.nanmin(ik[max_indF1 + 10: max_indF1 + 100]) + 0.5 * masx_IKJ_1
        feat = self.get_feat_please(gk, nk, ik, max_indF1, masx_IKJ)

        myClayInd = np.nanargmax(feat)
        try:
            myClay = self.cor_clay(gk, nk, ik, dpt, myClayInd, max_indF1)
        except:
            myClay = dpt[myClayInd]

        self.myClay = myClay

    def get_strat(self):
        self.get_Top()
        self.get_Clay()
        return self.My_Top, self.myClay


# In[12]:


# нормировка кривой
def norm(crv):
    return (crv - np.nanmin(crv)) / (np.nanmax(crv) - np.nanmin(crv))


# сегменитрование кривой по серединам амплитуд между экстремумами
def segmentation(dept, crv):
    def find_mins(crv, d):
        mins = []
        for i in range(1, len(crv) - 1):
            if ((crv[i - 1] - crv[i]) >= 0 and (crv[i + 1] - crv[i]) > 0) or (
                    (crv[i - 1] - crv[i]) > 0 and (crv[i + 1] - crv[i]) >= 0):
                mins.append(d[i])
        return mins

    def find_maxs(crv, d):
        maxs = []
        for i in range(1, len(crv) - 1):
            if ((crv[i - 1] - crv[i]) <= 0 and (crv[i + 1] - crv[i]) < 0) or (
                    (crv[i - 1] - crv[i]) < 0 and (crv[i + 1] - crv[i]) <= 0):
                maxs.append(d[i])
        return maxs

    mins = find_mins(crv, dept)
    maxs = find_maxs(crv, dept)

    extrems = np.hstack((mins, maxs))
    extrems.sort()

    boundaries = []

    for i in range(len(extrems) - 1):
        try:

            crvAvg = (crv[dept == extrems[i]] + crv[dept == extrems[i + 1]]) / 2

            ind = np.logical_and(dept >= extrems[i], dept <= extrems[i + 1])
            dx = dept[ind]

            v1 = dx[crv[ind] <= crvAvg][0]
            v2 = dx[crv[ind] <= crvAvg][-1]

            if abs(crv[dept == v1] - crvAvg) < abs(crv[dept == v2] - crvAvg):
                boundaries.append(v1)
            else:
                boundaries.append(v2)
        except Exception as exc:
            print(exc)
            pass

    boundaries.sort()

    return np.array(boundaries)


def get_layers_bot(d, crv, top, rkb, bot_zbound, hmin, hmax, sm_window, sm_deg):
    layers = []

    sm_crv = savgol_filter(crv, sm_window, sm_deg)
    segs = segmentation(d, sm_crv)

    jsegs = segs[np.logical_and(segs > top + hmin, segs <= top + hmax)]

    for j in range(len(jsegs)):

        # if jsegs[j]-rkb > bot_zbound:
        #    continue

        if not sm_crv[d == jsegs[j]] > sm_crv[d == d[d < jsegs[j]][-1]]:
            continue

        layers.append([top, jsegs[j]])

    return np.array(layers)


# вычисление матрицы признаков для машинного алгоритма
def get_features_bot(well):
    dept = well.curves["DEPT"]
    gk = well.curves["GK"]
    nk = well.curves["NGK"]
    layers = well.layers

    n = len(layers)
    f1 = np.nan * np.ones(n)
    f2 = np.nan * np.ones(n)
    f3 = np.nan * np.ones(n)
    f4 = np.nan * np.ones(n)
    f5 = np.nan * np.ones(n)

    for i in range(n):
        ind1 = np.logical_and(dept >= layers[i][0], dept < layers[i][1])
        ind3 = np.logical_and(dept >= layers[i][1], dept <= layers[i][1] + 3)
        ind4 = np.logical_and(dept >= layers[i][1] - 3, dept < layers[i][1])
        ind5 = np.logical_and(dept >= layers[i][1], dept < layers[i][1] + 20)

        f1[i] = np.nanmean(gk[ind1])
        f2[i] = np.nanmean(nk[ind1])
        f4[i] = np.nanmean(gk[ind3]) / np.nanmean(gk[ind4])
        f5[i] = np.nanmean(nk[ind3]) / np.nanmean(nk[ind4])
        f3[i] = np.nanmean(gk[ind5])

    features = np.vstack((f1, f2, f3, f4, f5))

    return features


def get_strat(run_id):
    abs_path = 'app/modules/first/'
    run_path = abs_path + str(run_id) + '/'
    out_path_log = replaceSlash(run_path + "\\output_data\\Report.txt")
    logging.basicConfig(format=u'%(levelname)-8s : %(message)s', level=logging.WARNING, filename=out_path_log,
                        filemode='w')
    Err_count = 0
    pattern_text_log = '   %s   :   %s'
    wells_list_strat = [str(val) for val in os.listdir(replaceSlash(run_path + "input_data\\coords"))]
    # wells_list_core  = [str(val) for val in os.listdir("input_data\\wellCore")]
    wells_list_logs = [str(val) for val in os.listdir(replaceSlash(run_path + "input_data\\wellLogs"))]

    wells_list = []
    for wsss in wells_list_strat:
        if wsss in wells_list_logs:
            wells_list.append(wsss)

    wells_list = [str(val) for val in os.listdir(replaceSlash(run_path + "input_data\\wellLogs"))]

    # wells_list = [str(val) for val in os.listdir("input_data\\coords")]
    # wells_list = sys.argv[1].split()

    # регулярные выражения для фильтра имен скважин
    regex = r"[^а-яА-Яa-zA-Z\s\0\^\$\`\~\!\@\"\#\№\;\%\^\:\?\*\(\)\-\_\=\+\\\|\[\]\{\}\,\.\/\'\d]"
    regWellName = r"[^0-9]"

    ignoreLiterals = True

    # локальный путь к папке обрабатываемых лас-файлов с ГИС
    wellLogsPath = replaceSlash(run_path + "input_data\\wellLogs")
    path = "wellData"

    wells = []
    wellCoords = {}
    log = []

    for index in wells_list:

        wellsLasFiles = {}
        smokerSFiles = []
        wellsInfo = {}
        importLog = {}

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
                    continue

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
                        smokerSFiles.append(file)
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
                    smokerSFiles.append(file)

        for wellName in wellsLasFiles.keys():
            try:
                globalMinDept = (wellsLasFiles.get(wellName)[0]).minDept
                globalMaxDept = (wellsLasFiles.get(wellName)[0]).maxDept
                globalMinStep = (wellsLasFiles.get(wellName)[0]).step
                # print('LAS FILES COUNT FOR ' + str(wellName) + ' : ' + str(len(wellsLasFiles.get(wellName))))
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
                importLog[wellName] = []
                curves['DEPT'] = dept
            except Exception as exc:
                print(index, wellName)
                print(exc)

            unexpectedError = False
            downloadedFiles = 0

            for lasInfoObject in wellsLasFiles.get(wellName):
                try:
                    crvNames = [lasInfoObject.las.keys()[i] for i in range(0, len(lasInfoObject.las.keys()))]
                    if 'UNKNOWN' in crvNames:
                        log.append(lasInfoObject.filePath)
                        log.append('Unexpected curve name')
                        # print('Unknown curve in ' + lasInfoObject.filePath)
                        smokerSFiles.append(lasInfoObject.filePath)
                        continue
                    crvs = ''

                    for crv in range(1, len(lasInfoObject.las.curves.keys()) - 1):
                        crvs = crvs + lasInfoObject.las.curves.keys()[crv] + ', '

                    crvs = crvs + lasInfoObject.las.curves.keys()[len(lasInfoObject.las.curves.keys()) - 1]
                    importLog[wellName].append(lasInfoObject.filePath + ' |/+/| ' + crvs)
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
                            if curveName == "GR":
                                a = 2
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
                            print(index, wellName)
                            print(exc)
                            pass

                    downloadedFiles += 1

                except Exception as e:
                    log.append(lasInfoObject.filePath)
                    log.append(str(e))
                    smokerSFiles.append(lasInfoObject.filePath)

            if downloadedFiles == 0:
                unexpectedError = True

            if not unexpectedError:
                wellsInfo[wellName] = curvesInfo
                newWell.curves = curves
                newWell.keys = curves.keys()
                newWell.index = index

                coordsPath = replaceSlash(run_path + "input_data\\coords\\" + index)

                # wellCoords.update({newWell.name : {"X" : 0, "Y" : 0, "RKB" : 0}})

                # wells.append(newWell)

                try:
                    with open(replaceSlash(os.path.join(coordsPath, os.listdir(coordsPath)[0])), "r") as read_file:
                        xlsCoords = json.load(read_file)
                        XYZ = [xlsCoords['X'], xlsCoords['Y'], xlsCoords['RKB']]
                        wellCoords.update({newWell.name: {"X": XYZ[0], "Y": XYZ[1], "RKB": XYZ[2]}})

                    wells.append(newWell)
                except Exception as exc:
                    print(index, wellName)
                    print(exc)
                    pass
            else:
                logging.error(pattern_text_log, str(wellName), "ошибка чтения")
                Err_count += 1

    print()
    print('Bad files :', log)
    print()

    # In[9]:

    # SOLVER

    strati_table = []

    try:
        with open(abs_path + 'SVM_files/SVM_S.pickle', 'rb') as f:
            tmp = pickle.load(f)
            scaler2 = tmp['scaler']
            sv2 = tmp['sv']
    except BaseException as e:
        pass

    progress = Bar('   Interpretation', max=len(wells) + 1, fill='*', suffix='%(percent)d%%')
    progress.next()

    Log = ''

    # главный цикл по сформированным скважинам для обработки

    for well in wells:
        if not well.name in wellCoords:
            progress.next()
            Log += well.name + " : " + "no coords data" + '\n' + '\n'
            logging.error(pattern_text_log, str(well.index), " не содержит данные по координатам")
            Err_count += 1
            continue

        # переименовка и фильтр скважин по наличию кривых гк-нк
        try:

            GK_names = ["gkv", "gr", "gk", "gk1", "гк", "gk:1"]
            IK_names = ["ik", "ild", "ик", "ik1", "ik:1", "rik", "ik (ик)"]
            NGK_names = ["ngl", "нгк", "nkdt", "jb", "jm", "ngk", "ngk:1", "ннкб", "nnkb", "nnkb  (ннкб)", "бз ннк",
                         "nktd",
                         "бз"]
            MD_names = ["dept", "md", "depth"]

            go_keys = list(well.curves.keys())
            for name_crv in go_keys:
                if str(name_crv).lower() in GK_names:
                    well.curves["GK"] = well.curves[name_crv]
                    GK_names = []
                    continue

                if str(name_crv).lower() in IK_names:
                    well.curves["IK"] = well.curves[name_crv]
                    IK_names = []
                    continue

                if str(name_crv).lower() in NGK_names:
                    well.curves["NGK"] = well.curves[name_crv]
                    NGK_names = []
                    continue

                if str(name_crv).lower() in MD_names:
                    well.curves["DEPT"] = well.curves[name_crv]
                    MD_names = []
                    continue

            if not "GK" in well.curves.keys():
                Log += well.name + " : " + "no GK data" + '\n' + '\n'
                logging.error(pattern_text_log, str(well.index), "no GK data")
                Err_count += 1
                progress.next()
                continue
            if not "NGK" in well.curves.keys():
                Log += well.name + " : " + "no NGK data" + '\n' + '\n'
                logging.error(pattern_text_log, str(well.index), "no NGK data")
                Err_count += 1
                progress.next()
                continue
        except Exception as exc:
            print(well)
            print(exc)
            pass

        # лингулы - автоматическая отбивка искомого интервала машинным обучением SVM по сформированной матрице признаков

        try:
            gk = well.curves["GK"]
            nk = well.curves["NGK"]
            dpt = well.curves["DEPT"]
            ik = well.curves["IK"]
            ik[ik <= 0] = np.nan

            sCT = search_ClayTop(gk, nk, ik, dpt)

            My_Top, myClay = sCT.get_strat()

            sumGis = gk + nk + ik
            check_gis = sumGis[dpt <= myClay]

            if len(check_gis[~np.isnan(check_gis)]) < 100:
                logging.warning(pattern_text_log, str(well.index),
                                "TOP:  недостаточная длина кривой ГИС для определения спириферового известняка или неверный формат кривой ГИС. ")

            well.stratigraphy = [myClay, My_Top]
        except BaseException as e:
            logging.error(pattern_text_log, str(well.index), "TOP: " + str(e))
            Err_count += 1
            continue

        # песчаник - автоматическая отбивка искомого интервала машинным обучением SVM по сформированной матрице признаков
        try:
            well.layers = get_layers_bot(well.curves["DEPT"], well.curves["GK"], well.stratigraphy[1],
                                         wellCoords[well.name]["RKB"], 32, 3, 42, 13, 3)
            features = get_features_bot(well).T

            ind = np.ones(len(features), dtype=bool)
            for i in range(len(features)):
                if any(np.isnan(features[i])):
                    ind[i] = False

            scores = sv2.predict_proba(scaler2.transform(features[ind]))
            ind = scores[:, 1].argmax()

            well.stratigraphy = np.append(well.stratigraphy, well.layers[ind][1])
        except BaseException as e:
            logging.error(pattern_text_log, str(well.index), "BOT: " + str(e))
            Err_count += 1
            pass

        # подтяжка по проблемным гис подошвы
        try:
            d = well.curves["DEPT"]
            gk = well.curves["GK"]

            layers = well.layers[:, 1]

            i = None
            n = np.where(layers == well.stratigraphy[2])[0][0]
            flag = False

            for i in range(n, len(layers)):
                well.stratigraphy[2] = layers[i]
                bot = well.stratigraphy[2]

                i1 = np.logical_and(d >= bot - 3, d <= bot)
                i2 = np.logical_and(d >= bot, d <= bot + 3)
                if np.nanmean(gk[i2]) / np.nanmean(gk[i1]) >= 1.22:
                    flag = True
                    break
            if flag or i is None:
                pass
            else:
                start = np.where(well.curves["DEPT"] == well.stratigraphy[2])[0][0]
                stop = \
                    np.where(well.curves["DEPT"] == np.nanmin([well.curves["DEPT"][-1], well.stratigraphy[1] + 42]))[0][
                        0]
                for i in range(start, stop):
                    if np.isnan(well.curves["GK"][i]) or well.curves["DEPT"][i] - wellCoords[well.name]["RKB"] >= 32:
                        break
                well.stratigraphy[2] = well.curves["DEPT"][i]
        except Exception as exc:
            print(well)
            print(exc)
            pass

        if len(well.stratigraphy) < 3:
            ind = np.logical_and(~np.isnan(well.curves["GK"]), ~np.isnan(well.curves["NGK"]))
            well.stratigraphy = np.append(well.stratigraphy, well.curves["DEPT"][ind][-1])

        # заполнение таблицы отбивок по полученным результатам текущей скважины
        try:
            strati_table.append([well.name, well.stratigraphy[0], well.stratigraphy[1], well.stratigraphy[2]])
        except Exception as exc:
            print(well)
            print(exc)
            pass

        # создание графических изображений кривых ГК-НГК вместе с полученными отбивками и печать картинок в папку
        try:
            fig, f = plt.subplots(nrows=1, ncols=2, sharey=True, figsize=(11, 16))
            fig.suptitle("Well #" + str(well.name), fontsize=30)

            dept = well.curves["DEPT"]
            gk = well.curves["GK"]

            lims = [well.stratigraphy[0] - 15, well.stratigraphy[2] + 15]
            ind = np.logical_and(dept >= lims[0], dept <= lims[1])

            f[0].plot(gk[~np.isnan(gk)], dept[~np.isnan(gk)], 'r')
            f[0].set_xlim(np.nanmin(gk[ind]), np.nanmax(gk[ind]))

            if not "NGK" in well.curves.keys() and "NGK:1" in well.curves.keys():
                nk = well.curves["NGK:1"]
                f[1].plot(nk[~np.isnan(nk)], dept[~np.isnan(nk)], 'k')
                f[1].set_xlim(np.nanmin(nk[ind]), np.nanmax(nk[ind]))
            elif "NGK" in well.curves.keys():
                nk = well.curves["NGK"]
                f[1].plot(nk[~np.isnan(nk)], dept[~np.isnan(nk)], 'k')
                f[1].set_xlim(np.nanmin(nk[ind]), np.nanmax(nk[ind]))

            # Fitted stratigraphy
            f[0].axhline(y=well.stratigraphy[0], linewidth=3, color='g')
            f[0].axhline(y=well.stratigraphy[1], linewidth=3, color='g')
            f[0].axhline(y=well.stratigraphy[2], linewidth=3, color='g')
            f[1].axhline(y=well.stratigraphy[0], linewidth=3, color='g')
            f[1].axhline(y=well.stratigraphy[1], linewidth=3, color='g')
            f[1].axhline(y=well.stratigraphy[2], linewidth=3, color='g')

            # f[0].set_ylim(lims)

            f[0].set_xlabel("GK", fontsize=30)
            f[1].set_xlabel("NK", fontsize=30)

            f[0].grid()
            f[1].grid()
            f[0].invert_yaxis()
        except Exception as exc:
            print(well)
            print(exc)
            pass

        outPath = replaceSlash(run_path + 'output_data/' + well.index)
        if not os.path.exists(outPath): os.makedirs(outPath)
        plt.savefig(replaceSlash(outPath + '/' + str(well.name) + ".png"))

        topsOut = {"Well": well.name, "Lingula_top": well.stratigraphy[0], "P2ss2_top": well.stratigraphy[1],
                   "P2ss2_bot": well.stratigraphy[2]}
        with open(replaceSlash(outPath + '/' + "stratigraphy.json"), "w") as write_file:
            json.dump(topsOut, write_file)

        progress.next()

    if Err_count == 0:
        logging.addLevelName(100, "INFO")
        logging.log(100, pattern_text_log, "", "No errors in data")

    print()
    print()
    print("Interpretation successfully finished")
    print()
