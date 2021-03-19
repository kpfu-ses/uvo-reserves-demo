from matplotlib import path
import numpy as np
import pandas
import math
# from shapely.geometry import Polygon
import xlsxwriter
import scipy
from scipy import ndimage
from scipy.linalg import lstsq
from progress.bar import Bar
from sys import exit as sys_exit
import sys
import os
import json
import logging


# конвертация путей файлов в зависимости от системы
def replaceSlash(filePath):
    platform = sys.platform
    slashMap = {'win32': '\\',
                'cygwin': '\\',
                'darwin': '/',
                'linux2': '/'}
    if platform not in slashMap.keys(): platform = 'linux2'
    return filePath.replace('\\', slashMap[platform])


def loadConfig(pattern_text_log, abs_path):
    try:
        dc = None
        with open(abs_path + 'configuration_surface.json', 'r') as fc:
            dc = json.load(fc)
    except BaseException as e:
        logging.error(pattern_text_log, "", 'Ошибка при загрузке файла конфигурации. ' + str(e))
        # Err_count += 1
        return None

    return dc


class Cell(object):
    def __init__(self, point_num=[], adjacent_element=[], centre=[]):
        self.point_num = point_num
        self.adjacent_element = adjacent_element
        self.well = False


class Point(object):
    def __init__(self, x=np.nan, y=np.nan, zTB=[]):
        self.x = x
        self.y = y
        self.zTB = np.array([np.nan, np.nan])


def dist_point(p1, line):
    dist = 1 * p1[1] - (line[0] * p1[0] + line[1])
    return dist


def dist_point2(p, l):
    A = (p[0] + l[0] * p[1] - l[0] * l[1]) / (l[0] * l[0] + 1) - p[0]
    B = l[0] * (p[0] + l[0] * p[1] - l[0] * l[1]) / (l[0] * l[0] + 1) + l[1] - p[1]
    dist = math.sqrt(A * A + B * B)
    return dist


def inPolygonXY(e1, e2, e3, xp, yp, e4=None):
    if e4 is None:
        RES = False
        Polygon_path = path.Path([(e1.x, e1.y), (e2.x, e2.y), (e3.x, e3.y)])
        for i in range(0, len(xp)):
            if Polygon_path.contains_point((xp[i], yp[i])):
                RES = True
                break
        return RES
    else:
        RES = False
        Polygon_path = path.Path([(e1.x, e1.y), (e2.x, e2.y), (e4.x, e4.y), (e3.x, e3.y)])
        for i in range(0, len(xp)):
            if Polygon_path.contains_point((xp[i], yp[i])):
                RES = True
                break
        return RES


def SearchPlaneZ(well_x, well_y, _p1, _p2, _p3, _p4):
    leftABCD = GetABCD(_p1[0], _p1[1], _p1[2], _p2[0], _p2[1], _p2[2], _p3[0], _p3[1], _p3[2])
    rightABCD = GetABCD(_p2[0], _p2[1], _p2[2], _p3[0], _p3[1], _p3[2], _p4[0], _p4[1], _p4[2])

    p1 = Point(_p1[0], _p1[1])
    p2 = Point(_p2[0], _p2[1])
    p3 = Point(_p3[0], _p3[1])
    p4 = Point(_p4[0], _p4[1])

    if inPolygonXY(p1, p2, p3, [well_x], [well_y]):
        return leftABCD
    elif inPolygonXY(p2, p4, p3, [well_x], [well_y]):
        return rightABCD
    else:
        return []


def SearchPlaneZ_2(well_x, well_y, p1, p2, p3, p4, IND_Z):
    leftABCD = GetABCD(p1.x, p1.y, p1.zTB[IND_Z], p2.x, p2.y, p2.zTB[IND_Z], p3.x, p3.y, p3.zTB[IND_Z])
    rightABCD = GetABCD(p2.x, p2.y, p2.zTB[IND_Z], p3.x, p3.y, p3.zTB[IND_Z], p4.x, p4.y, p4.zTB[IND_Z])

    if inPolygonXY(p1, p2, p3, [well_x], [well_y]):
        return leftABCD
    elif inPolygonXY(p2, p4, p3, [well_x], [well_y]):
        return rightABCD
    else:
        return []


def GetABCD(x0, y0, z0, x1, y1, z1, x2, y2, z2):
    k1 = (y1 - y0) * (z2 - z0) - (z1 - z0) * (y2 - y0)
    k2 = (x1 - x0) * (z2 - z0) - (z1 - z0) * (x2 - x0)
    k3 = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
    A = k1
    B = -k2
    C = k3
    D = k1 * (-x0) - k2 * (-y0) + k3 * (-z0)
    return [A, B, C, D]


def getZ(well_x, well_y, p1, p2, p3, p4):
    resABCD = SearchPlaneZ(well_x, well_y, p1, p2, p3, p4)
    try:
        z_cord = (-resABCD[0] * well_x - resABCD[1] * well_y - resABCD[3]) / resABCD[2]
    except:
        z_cord = (-resABCD[0] * well_x - resABCD[1] * well_y - resABCD[3]) / resABCD[2]
    return z_cord


def Zoom_Z(well_x, well_y, well_z, p1, p2, p3, p4, IND_Z):
    resABCD = SearchPlaneZ_2(well_x, well_y, p1, p2, p3, p4, IND_Z)
    z_cord = (-resABCD[0] * well_x - resABCD[1] * well_y - resABCD[3]) / resABCD[2]
    if inPolygonXY(p1, p2, p3, [well_x], [well_y]):
        ABCD = GetABCD(p1.x, p1.y, z_cord, p2.x, p2.y, p2.zTB[IND_Z], p3.x, p3.y, p3.zTB[IND_Z])
        newZ = (-ABCD[0] * p1.x - ABCD[1] * p1.y - ABCD[3]) / ABCD[2]
        ind_remake = 0
    elif inPolygonXY(p2, p4, p3, [well_x], [well_y]):
        ABCD = GetABCD(p4.x, p4.y, z_cord, p2.x, p2.y, p2.zTB[IND_Z], p3.x, p3.y, p3.zTB[IND_Z])
        newZ = (-ABCD[0] * p4.x - ABCD[1] * p4.y - ABCD[3]) / ABCD[2]
        ind_remake = 3
    dist = newZ - z_cord
    return dist, ind_remake


def Struct_surface(masPoint, masCell, masN, X, Y, Z, q, eps):
    def get_NB_and_K(nx, ny, ij):
        NB = (np.ones(nx * ny) * np.nan).reshape(ny, nx)
        K = (np.ones(nx * ny) * np.nan).reshape(ny, nx)
        IC = 0
        while len(NB[np.isnan(NB)]) > 0:
            for it in range(len(ij)):
                i, j = ij[it][0], ij[it][1]
                i_l = int((max(0, i - IC)))
                i_r = int((min(nx - 1, i + IC)))
                j_t = int((min(ny - 1, j + IC)))
                j_b = int((max(0, j - IC)))

                for i_line in range(i_l, i_r + 1):
                    if np.isnan(NB[j_t][i_line]):
                        NB[j_t][i_line] = it
                        K[j_t][i_line] = IC
                    elif IC / math.sqrt(2) <= K[j_t][i_line]:
                        i0 = ij[int(NB[j_t][i_line])][0]
                        j0 = ij[int(NB[j_t][i_line])][1]
                        dold = (i_line - i0) * (i_line - i0) + (j_t - j0) * (j_t - j0)
                        dnew = (i_line - i) * (i_line - i) + (j_t - j) * (j_t - j)
                        if dold > dnew:
                            NB[j_t][i_line] = it
                            K[j_t][i_line] = IC

                for i_line in range(i_l, i_r + 1):
                    if np.isnan(NB[j_b][i_line]):
                        NB[j_b][i_line] = it
                        K[j_b][i_line] = IC
                    elif IC / math.sqrt(2) <= K[j_b][i_line]:
                        i0 = ij[int(NB[j_b][i_line])][0]
                        j0 = ij[int(NB[j_b][i_line])][1]
                        dold = (i_line - i0) * (i_line - i0) + (j_b - j0) * (j_b - j0)
                        dnew = (i_line - i) * (i_line - i) + (j_b - j) * (j_b - j)
                        if dold > dnew:
                            NB[j_b][i_line] = it
                            K[j_b][i_line] = IC

                for j_line in range(j_b + 1, j_t):
                    if np.isnan(NB[j_line][i_r]):
                        NB[j_line][i_r] = it
                        K[j_line][i_r] = IC
                    elif IC / math.sqrt(2) <= K[j_line][i_r]:
                        i0 = ij[int(NB[j_line][i_r])][0]
                        j0 = ij[int(NB[j_line][i_r])][1]
                        dold = (i_r - i0) * (i_r - i0) + (j_line - j0) * (j_line - j0)
                        dnew = (i_r - i) * (i_r - i) + (j_line - j) * (j_line - j)
                        if dold > dnew:
                            NB[j_line][i_r] = it
                            K[j_line][i_r] = IC

                for j_line in range(j_b + 1, j_t):
                    if np.isnan(NB[j_line][i_l]):
                        NB[j_line][i_l] = it
                        K[j_line][i_l] = IC
                    elif IC / math.sqrt(2) <= K[j_line][i_l]:
                        i0 = ij[int(NB[j_line][i_l])][0]
                        j0 = ij[int(NB[j_line][i_l])][1]
                        dold = (i_l - i0) * (i_l - i0) + (j_line - j0) * (j_line - j0)
                        dnew = (i_l - i) * (i_l - i) + (j_line - j) * (j_line - j)

                        if dold > dnew:
                            NB[j_line][i_l] = it
                            K[j_line][i_l] = IC
            IC += 1
        return NB, K

    def GetIJ_well(masPoint, masCell, masN, X, Y, Z):
        N_well = len(Z)
        it = 0
        ij = np.array([np.nan, np.nan, np.nan, np.nan])

        use_well = np.array([], dtype=int)

        for it_y in range(masN[1]):
            for it_x in range(masN[0]):
                p1 = masPoint[masCell[it].point_num[0]]
                p2 = masPoint[masCell[it].point_num[1]]
                p3 = masPoint[masCell[it].point_num[2]]
                p4 = masPoint[masCell[it].point_num[3]]

                it += 1

                for wi in range(N_well):
                    if wi in use_well:
                        continue
                    if inPolygonXY(p1, p2, p3, [X[wi]], [Y[wi]], p4):
                        ij = np.vstack((ij, [it_x, it_y, it - 1, wi]))
                        use_well = np.append(use_well, wi)

        ij = np.delete(ij, 0, 0)
        return np.array(ij, dtype=int)

    def TensionP(P, K, nx, ny):
        Kmax = np.nanmax(K)
        iter_start = max(4, Kmax / 2 + 2)
        for N in range(int(iter_start), 0, -1):
            for j in range(ny):
                for i in range(nx):
                    k = min(K[j][i], N)
                    i_l = int(max(0, i - k))
                    i_r = int(min(nx - 1, i + k))
                    j_t = int(min(ny - 1, j + k))
                    j_b = int(max(0, j - k))
                    P[j][i] = (P[j][i_l] + P[j][i_r] + P[j_t][i] + P[j_b][i]) / 4

    def GetFxy(masPoint, masCell, masN, ij, P, Z_real, nx, ny, N, x_w, y_w):

        Fxy = np.array([])
        Zxy = np.array([])

        for i in range(len(ij)):
            if ij[i][0] + 1 >= nx:
                il = ij[i][0] - 1
            else:
                il = ij[i][0]
            if ij[i][1] + 1 >= ny:
                jb = ij[i][1] - 1
            else:
                jb = ij[i][1]
            ir = il + 1
            jt = jb + 1

            ind_c = int(ij[i][2])
            e1 = masPoint[int(masCell[ind_c].point_num[0])]
            e2 = masPoint[int(masCell[ind_c].point_num[1])]
            e3 = masPoint[int(masCell[ind_c].point_num[2])]
            e4 = masPoint[int(masCell[ind_c].point_num[3])]

            p1 = [e1.x, e1.y, P[int(jb)][int(il)]]
            p2 = [e2.x, e2.y, P[int(jb)][int(ir)]]
            p3 = [e3.x, e3.y, P[int(jt)][int(il)]]
            p4 = [e4.x, e4.y, P[int(jt)][int(ir)]]

            z_val = getZ(x_w[int(ij[i][3])], y_w[int(ij[i][3])], p1, p2, p3, p4)
            Fxy = np.append(Fxy, z_val)
            Zxy = np.append(Zxy, Z_real[int(ij[i][3])])
        return Fxy, Zxy

    nx = masN[0] + 1
    ny = masN[1] + 1

    ij = GetIJ_well(masPoint, masCell, masN, X, Y, Z)
    NB, K = get_NB_and_K(nx, ny, ij)

    P = np.zeros(nx * ny).reshape(ny, nx)

    Z_new = np.array([])
    for iz in range(len(Z)):
        Z_new = np.append(Z_new, Z[[ij[iz][3]]])

    for j in range(ny):
        for i in range(nx):
            P[j][i] = Z_new[int(NB[j][i])]

    TensionP(P, K, nx, ny)

    P = scipy.ndimage.filters.gaussian_filter(P, 1.5)

    Fxy, Z_real = GetFxy(masPoint, masCell, masN, ij, P, Z, nx, ny, len(Z), X, Y)

    DZ = Z_new - Fxy

    thisIT = 0
    maxIT = 20
    oldIterat_min = 1e5
    oldIterat_max = 1e5
    while abs(np.nanmax(DZ)) > eps:
        DP = np.copy(P)
        for j in range(ny):
            for i in range(nx):
                P[j][i] = DZ[int(NB[j][i])]

        TensionP(P, K, nx, ny)
        P = scipy.ndimage.filters.gaussian_filter(P, 1.5)

        P = P + DP
        Fxy, Z_real = GetFxy(masPoint, masCell, masN, ij, P, Z_new, nx, ny, len(Z), X, Y)
        DZ = Z_new - Fxy

        if thisIT >= maxIT:
            break
        elif abs(oldIterat_min - np.nanmin(DZ)) < 1e-3 and abs(oldIterat_max - np.nanmax(DZ)) < 1e-3:
            break
        elif abs(np.nanmin(DZ)) > abs(oldIterat_min) and abs(np.nanmax(DZ)) > abs(oldIterat_max):
            break
        thisIT += 1
        oldIterat_max = np.nanmax(DZ)
        oldIterat_min = np.nanmin(DZ)

    resP = []
    for j in range(ny):
        for i in range(nx):
            resP.append(P[j][i])
    return resP


def Construction_Surface(tops, bots, hx, hy, pattern_text_log):
    def remakeZ(masPoint, newCell, tops, bots):
        # Устранеие около скважин погрешности при интерполяции значений глубин
        Well_ind = []
        # Расширение облости, переопределение значений координаты Z в узлах сетки
        for cell_i in range(0, len(newCell)):
            Xtop = np.array([])
            Xbot = np.array([])
            Ytop = np.array([])
            Ybot = np.array([])
            Ztop = np.array([])
            Zbot = np.array([])
            e1 = masPoint[newCell[cell_i].point_num[0]]
            e2 = masPoint[newCell[cell_i].point_num[1]]
            e3 = masPoint[newCell[cell_i].point_num[2]]
            e4 = masPoint[newCell[cell_i].point_num[3]]

            for name in tops:
                top_x = tops[name]["x"]
                top_y = tops[name]["y"]
                top_z = tops[name]["z"]
                bot_x = bots[name]["x"]
                bot_y = bots[name]["y"]
                bot_z = bots[name]["z"]
                if inPolygonXY(e1, e2, e3, [top_x], [top_y], e4):
                    Xtop = np.append(Xtop, top_x)
                    Ytop = np.append(Ytop, top_y)
                    Ztop = np.append(Ztop, top_z)
                if inPolygonXY(e1, e2, e3, [bot_x], [bot_y], e4):
                    Xbot = np.append(Xbot, bot_x)
                    Ybot = np.append(Ybot, bot_y)
                    Zbot = np.append(Zbot, bot_z)

            if not len(Ztop) == 0:
                w_x = Xtop[abs(Ztop - np.nanmax(Ztop)) < 1e-5][0]
                w_y = Ytop[abs(Ztop - np.nanmax(Ztop)) < 1e-5][0]
                w_z = Ztop[abs(Ztop - np.nanmax(Ztop)) < 1e-5][0]
                dist_val_Z, ind_remake = Zoom_Z(w_x, w_y, w_z, e1, e2, e3, e4, 0)
                masPoint[newCell[cell_i].point_num[ind_remake]].zTB[0] += dist_val_Z

            if not len(Zbot) == 0:
                w_x = Xbot[Zbot == np.nanmin(Zbot)][0]
                w_y = Ybot[Zbot == np.nanmin(Zbot)][0]
                w_z = Zbot[Zbot == np.nanmin(Zbot)][0]
                dist_val_Z, ind_remake = Zoom_Z(w_x, w_y, w_z, e1, e2, e3, e4, 1)
                masPoint[newCell[cell_i].point_num[ind_remake]].zTB[1] += dist_val_Z

    def RemakePoint(points, _masN, IND_Z):
        nx = _masN[0] + 1
        ny = _masN[1] + 1
        ind_point = 0
        N = nx * ny
        ind_nan = []
        while ind_point < N:
            for i in range(0, nx):
                if ind_point >= N:
                    break
                if np.isnan(points[ind_point].zTB[IND_Z]):
                    ind_nan.append(ind_point)
                    ind_point += 1
                else:
                    Z_for_nan = points[ind_point].zTB[IND_Z]
                    if not len(ind_nan) == 0:
                        for i_x in ind_nan:
                            points[i_x].zTB[IND_Z] = Z_for_nan
                        ind_nan = []
                    ind_point += 1
        if not len(ind_nan) == 0:
            for i_x in ind_nan:
                points[i_x].zTB[IND_Z] = Z_for_nan

    def BildGridXY(masX, masY, _hx, _hy):
        def remake_grid2(masX, masY, _hx, _hy):

            def symmetry_point(x, y, line):
                A, B, C = -line[0], 1, -line[1]
                x_new = ((B * B - A * A) * x - 2 * A * B * y - 2 * A * C) / (A * A + B * B)
                y_new = ((A * A - B * B) * y - 2 * A * B * x - 2 * B * C) / (A * A + B * B)
                return x_new, y_new

            # try
            M = np.vstack([masX, np.ones(len(masX))]).T
            line = lstsq(M, masY)[0]
            line_orto = [-1 / line[0], 1 / line[0] * (np.nanmin(masX) - 100) + masY[np.argmin(masX)]]
            ANGLE = math.atan(line[0])
            # except

            dist_y1 = np.array([])
            dist_x1 = np.array([])

            masX_rem = np.array([])
            masY_rem = np.array([])
            for i in range(len(masX)):
                val1 = dist_point([masX[i], masY[i]], line)

                val1 = val1 / abs(val1)

                val1 *= dist_point2([masX[i], masY[i]], line)
                val2 = dist_point2([masX[i], masY[i]], line_orto)

                x_new, y_new = masX[i], masY[i]

                masX_rem = np.append(masX_rem, x_new)
                masY_rem = np.append(masY_rem, y_new)

                dist_y1 = np.append(dist_y1, val1)
                dist_x1 = np.append(dist_x1, val2)

            dist_y1 = np.round(dist_y1, 2)
            dist_x1 = np.round(dist_x1, 2)

            ind_sortX = np.lexsort((masX_rem, dist_x1))
            X_min_x, X_max_x = masX_rem[ind_sortX][0], masX_rem[ind_sortX][-1]
            X_min_y, X_max_y = masY_rem[ind_sortX][0], masY_rem[ind_sortX][-1]

            ind_sortY = np.lexsort((masY_rem, dist_y1))
            Y_min_x, Y_max_x = masX_rem[ind_sortY][0], masX_rem[ind_sortY][-1]
            Y_min_y, Y_max_y = masY_rem[ind_sortY][0], masY_rem[ind_sortY][-1]

            kshft = 128
            X_min_y = line[0] * (X_min_x - kshft) + (X_min_y - line[0] * X_min_x)
            X_min_x -= kshft
            X_max_y = line[0] * (X_max_x + kshft) + (X_max_y - line[0] * X_max_x)
            X_max_x += kshft

            if abs(line_orto[0]) < 1e-5:
                Y_min_y -= kshft
                Y_max_y += kshft
            else:
                Y_min_x = ((Y_min_y - kshft) - (Y_min_y - line_orto[0] * Y_min_x)) / line_orto[0]
                Y_min_y -= kshft
                Y_max_x = ((Y_max_y + kshft) - (Y_max_y - line_orto[0] * Y_max_x)) / line_orto[0]
                Y_max_y += kshft

            LEN_Y = abs((Y_min_y - Y_max_y) - line[0] * (Y_min_x - Y_max_x)) / math.sqrt(line[0] * line[0] + 1)

            LEN_X = abs((X_min_y - X_max_y) - line_orto[0] * (X_min_x - X_max_x)) / math.sqrt(
                line_orto[0] * line_orto[0] + 1)

            Nx = int(LEN_X / _hx)
            Ny = int(LEN_Y / _hy)
            masN = [Nx, Ny]

            hx = (LEN_X) / Nx
            hy = (LEN_Y) / Ny

            h_prj_x = hx * math.cos(math.atan(line[0]))
            h_prj_y = hy * math.cos(math.atan(line[0]))

            RES_X = np.array([])
            RES_Y = np.array([])

            X0 = (X_min_y - line_orto[0] * X_min_x - Y_min_y + line[0] * Y_min_x) / (line[0] - line_orto[0])
            Y0 = line[0] * X0 + Y_min_y - line[0] * Y_min_x

            B_orto = X_min_y - line_orto[0] * X_min_x
            B_Nort = Y_min_y - line[0] * Y_min_x
            for yi in range(0, Ny + 1):
                for xi in range(0, Nx + 1):
                    x = X0 + xi * h_prj_x
                    y = line[0] * x + B_Nort
                    RES_X = np.append(RES_X, x)
                    RES_Y = np.append(RES_Y, y)
                X0 = ((Y0 + (yi + 1) * h_prj_y) - B_orto) / line_orto[0]
                B_Nort = (Y0 + (yi + 1) * h_prj_y) - line[0] * X0

            XY_bound = [[Y_min_x, Y_max_x], [X_min_y, X_max_y]]

            return RES_X, RES_Y, masN, ANGLE, hx, hy, XY_bound

        masCell = []
        masPoint = []

        RES_X, RES_Y, masN, ANGLE, hx, hy, XY_bound = remake_grid2(masX, masY, _hx, _hy)
        Nx = masN[0]
        Ny = masN[1]

        for xy_i in range(0, len(RES_X)):
            masPoint.append(Point(RES_X[xy_i], RES_Y[xy_i]))

        e_n = 0
        for yi in range(0, Ny):
            for xi in range(0, Nx):
                masPointNum = []
                adjacent_element = []
                e1 = e_n + yi
                e2 = e1 + 1
                e3 = e1 + (Nx + 1)
                e4 = e3 + 1
                masPointNum.append(e1)
                masPointNum.append(e2)
                masPointNum.append(e3)
                masPointNum.append(e4)
                for yb in [-1, 0, 1]:
                    for xb in [-1, 0, 1]:
                        if (xi + xb >= 0 and xi + xb < Nx) and (yi + yb >= 0 and yi + yb < Ny):
                            numEL = (xi + xb) + (yi + yb) * Nx
                            adjacent_element.append(int(numEL))
                masCell.append(Cell(masPointNum, adjacent_element))
                e_n += 1
        return masPoint, masCell, masN, ANGLE, hx, hy, XY_bound

    # function constant
    q = 0.5
    eps = 0.01

    x_top = np.array([])
    y_top = np.array([])
    z_top = np.array([])
    x_bot = np.array([])
    y_bot = np.array([])
    z_bot = np.array([])
    for name in tops:
        x_top = np.append(x_top, tops[name]["x"])
        y_top = np.append(y_top, tops[name]["y"])
        z_top = np.append(z_top, tops[name]["z"])
    for name in bots:
        x_bot = np.append(x_bot, bots[name]["x"])
        y_bot = np.append(y_bot, bots[name]["y"])
        z_bot = np.append(z_bot, bots[name]["z"])

    progress1 = Bar('            Building surfaces', max=5, fill='*', suffix='%(percent)d%%')

    minPower = np.nanmin(abs(z_top - z_bot))
    maxPower = np.nanmax(abs(z_top - z_bot))

    masPoint, masCellXY, masN, ANGLE, hx, hy, XY_bound = BildGridXY(np.hstack((x_top, x_bot)),
                                                                    np.hstack((y_top, y_bot)), hx, hy)

    progress1.next()

    Z_top = Struct_surface(masPoint, masCellXY, masN, x_top, y_top, z_top, q, eps)
    Z_bot = Struct_surface(masPoint, masCellXY, masN, x_bot, y_bot, z_bot, q, eps)

    progress1.next()

    nan_tops = False
    for i in range(0, len(Z_top)):
        if np.isnan(Z_top[i]):
            nan_tops = True
            break

    nan_bot = False
    for i in range(0, len(Z_bot)):
        if np.isnan(Z_bot[i]):
            nan_bot = True
            break

    progress1.next()

    for i in range(0, len(Z_top)):
        try:
            if Z_top[i] > Z_bot[i] and abs(Z_top[i] - Z_bot[i]) >= minPower:
                top_val_Z = Z_top[i]
                bot_val_Z = Z_bot[i]
            else:
                dsti_fck = (Z_top[i] + Z_bot[i]) / 2
                top_val_Z = dsti_fck + minPower / 2
                bot_val_Z = dsti_fck - minPower / 2
        except:
            top_val_Z = Z_top[i]
            bot_val_Z = Z_bot[i]
            logging.warning(pattern_text_log, "", "Possible intersection of surfaces")
            # Err_count += 1

        masPoint[i].zTB[0] = top_val_Z
        masPoint[i].zTB[1] = bot_val_Z

    progress1.next()

    if nan_tops:
        try:
            RemakePoint(masPoint, masN, 0)
        except:
            logging.warning(pattern_text_log, "", "RemakePoint: TOPS_ there is NaN-value")
            # Err_count += 1
    if nan_bot > 0:
        try:
            RemakePoint(masPoint, masN, 1)
        except:
            logging.warning(pattern_text_log, "", "RemakePoint: BOTS_ there is NaN-value")
            # Err_count += 1

    progress1.next()

    return masPoint, masCellXY, masN, ANGLE, [hx, hy], XY_bound


def Save_Surface(outfolder, masPoint, masN, Ind_s, newH, ANGLE, XY_bound):
    if Ind_s == 0:
        name_surf = "TOP"
    elif Ind_s == 1:
        name_surf = "BOT"

    hx, hy = newH[0], newH[1]

    A = (ANGLE * 180 / math.pi)

    x0, x1, y0, y1 = masPoint[0].x, masPoint[masN[0]].x, masPoint[0].y, masPoint[int((masN[0] + 1) * masN[1])].y

    STR_H_1 = str(-996) + " " + str(masN[1] + 1) + " " + str(hx) + " " + str(hy)
    STR_H_2 = str(x0) + " " + str(x1) + " " + str(y0) + " " + str(y1)
    STR_H_3 = str(masN[0] + 1) + " " + str(A) + " " + str(x0) + " " + str(y0)
    STR_H_4 = str(0) + " " + str(0) + " " + str(0) + " " + str(0) + " " + str(0) + " " + str(0) + " " + str(0)

    surf_path = outfolder + "\\Surface" + name_surf + ".txt"
    surf_path = replaceSlash(surf_path)

    f = open(surf_path, "w")
    f.write(STR_H_1 + "\n")
    f.write(STR_H_2 + "\n")
    f.write(STR_H_3 + "\n")
    f.write(STR_H_4 + "\n")

    ALL_STR = ""
    maxNumInLay = 6
    ind_i = 0
    while (ind_i < len(masPoint)):
        STR = ""
        itNumInLay = 0
        while itNumInLay < maxNumInLay and ind_i < len(masPoint):
            STR += str(round(masPoint[ind_i].zTB[Ind_s], 3)) + " "
            ind_i += 1
            itNumInLay += 1
        STR += " \n"
        ALL_STR += STR
        if ind_i >= len(masPoint):
            break

    f.write(ALL_STR)
    f.close()


def load_data_inf(_wells_list, well_coords_Path, well_strat_Path, Err_count, pattern_text_log):
    tops = {}
    bots = {}
    print(_wells_list)
    print(well_strat_Path, well_coords_Path)
    for index in _wells_list:

        T_B_X_Y_Z = []
        name1 = ""
        name2 = ""
        # стратиграфия
        try:
            topsPath = replaceSlash(well_strat_Path + "\\" + index)
            with open(replaceSlash(os.path.join(topsPath, os.listdir(topsPath)[0])), "r") as read_file:
                Tops = json.load(read_file)
                name1 = str(Tops["Well"])
                T_B_X_Y_Z.append(Tops['P2ss2_top'])
                T_B_X_Y_Z.append(Tops['P2ss2_bot'])

        except:
            logging.warning(pattern_text_log, str(index), "No read stratigraphy")
            Err_count += 1
            continue

        # координаты
        try:
            coordsPath = replaceSlash(well_coords_Path + "\\" + index)
            with open(replaceSlash(os.path.join(coordsPath, os.listdir(coordsPath)[0])), "r") as read_file:
                Coords = json.load(read_file)
                name2 = str(Coords["Well"])
                T_B_X_Y_Z.append(Coords['X'])
                T_B_X_Y_Z.append(Coords['Y'])
                T_B_X_Y_Z.append(Coords['RKB'])
        except:
            logging.warning(pattern_text_log, str(index), "No read coords")
            Err_count += 1
            continue

        if not name1 == name2:
            logging.warning(pattern_text_log, str(index), "different well names")
            Err_count += 1
        try:
            tops.update({name1: {
                "x": T_B_X_Y_Z[2],
                "y": T_B_X_Y_Z[3],
                "z": T_B_X_Y_Z[4] - T_B_X_Y_Z[0]
            }})
            bots.update({name1: {
                "x": T_B_X_Y_Z[2],
                "y": T_B_X_Y_Z[3],
                "z": T_B_X_Y_Z[4] - T_B_X_Y_Z[1]
            }})
        except:
            logging.warning(pattern_text_log, str(index), "No read data")
            Err_count += 1
            continue
    return tops, bots


def get_surfaces(run_id):
    abs_path = 'app/modules/fifth/'
    run_path = abs_path + str(run_id) + '/'

    out_path_log = replaceSlash(run_path + "\\output_data\\Report.txt")
    logging.basicConfig(format=u'%(levelname)-8s : %(message)s', level=logging.WARNING, filename=out_path_log,
                        filemode='w')
    Err_count = 0
    pattern_text_log = '   %s   :   %s'
    # if len(sys.argv) <= 1:
    #    logging.error( pattern_text_log, "", "Необходимо задать список скважин" )
    #    sys.exit()

    Err_count = 0
    # wells_list = sys.argv[1].split()

    outfolder = run_path + 'output_data'
    wells_list_coord = [str(val).replace(" ", "") for val in os.listdir(replaceSlash(run_path + "input_data\\coords"))]
    wells_list_strat = [str(val).replace(" ", "") for val in
                        os.listdir(replaceSlash(run_path + "input_data\\stratigraphy"))]
    wells_list = []
    for wsss in wells_list_coord:
        if wsss in wells_list_strat:
            wells_list.append(wsss)

    # локальный путь к папке координат
    well_coords_Path = replaceSlash(run_path + "input_data\\coords")
    # локальный путь к папке стратиграфии
    well_strat_Path = replaceSlash(run_path + "input_data\\stratigraphy")

    config = loadConfig(pattern_text_log, abs_path)
    if config is None:
        sys_exit()
    try:
        hx = float(config["hx"])
        hy = float(config["hy"])
    except BaseException as e:
        logging.error(pattern_text_log, "", "read hx, hy. " + str(e))
        Err_count += 1
        sys_exit()

    tops, bots = load_data_inf(wells_list, well_coords_Path, well_strat_Path, Err_count, pattern_text_log)

    if not len(tops) == len(bots) or (len(tops) == 0 and len(bots) == 0):
        logging.error(pattern_text_log, "", "No input_data")
        Err_count += 1
        sys_exit()

    try:
        masPoint, newCell, masN, ANGLE, newH, XY_bound = Construction_Surface(tops, bots, hx, hy, pattern_text_log)
    except BaseException as e:
        logging.error(pattern_text_log, "", "Construction_Surface:    " + str(e))
        Err_count += 1
        sys_exit()

    try:
        Save_Surface(outfolder, masPoint, masN, 0, newH, ANGLE, XY_bound)
    except BaseException as e:
        logging.error(pattern_text_log, "", "No_Save_Surface_TOP:    " + str(e))
        Err_count += 1

    try:
        Save_Surface(outfolder, masPoint, masN, 1, newH, ANGLE, XY_bound)
    except BaseException as e:
        logging.error(pattern_text_log, "", "No_Save_Surface_BOT:   " + str(e))
        Err_count += 1

    if Err_count == 0:
        logging.addLevelName(100, "INFO")
        logging.log(100, pattern_text_log, "", "No errors in data")
