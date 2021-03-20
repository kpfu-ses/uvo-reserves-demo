import numpy as np
import math
import pickle
from tqdm import tqdm
import logging
import os
import sys

from sys import exit as sys_exit
import json
import logging
import math
import os
import pickle
import sys
from sys import exit as sys_exit
import json
import numpy as np
from tqdm import tqdm


class Cell(object):
    def __init__(self, point_num=[], adjacent_element=[], centre=[]):
        self.point_num = point_num
        self.adjacent_element = adjacent_element
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


def Construction_3D_grid(tops_inf, bots_inf, vertical_split, angle, err_inf):
    # !!!
    # !!! vertical_split - struct
    # !!! vertical_split["type"] -> N_fix, h_fix
    # !!! vertical_split["val"]  -> Параметр разбиения
    # !!!
    def RemakePoint(points, _masN, start_ind_point):
        nx = _masN[0] + 1
        ny = _masN[1] + 1
        ind_point = start_ind_point
        N = nx * ny
        ind_nan = []
        while ind_point < start_ind_point + N:
            for i in range(0, nx):
                if ind_point >= start_ind_point + N:
                    break
                if np.isnan(points[ind_point].z):
                    ind_nan.append(ind_point)
                    ind_point += 1
                else:
                    Z_for_nan = points[ind_point].z
                    if not len(ind_nan) == 0:
                        for i_x in ind_nan:
                            points[i_x].z = Z_for_nan
                        ind_nan = []
                    ind_point += 1
        if not len(ind_nan) == 0:
            for i_x in ind_nan:
                points[i_x].z = Z_for_nan

    def Get_num_Lay(v_s, maxP):
        if v_s["type"] == "DRC":
            res = int(v_s["val"][0] * (v_s["val"][1] + 1) + 1)
        elif v_s["type"] == "N_fix":
            res = v_s["val"]
        elif v_s["type"] == "h_fix":
            res = int(maxP / v_s["val"])
            v_s["val"] = maxP / res
        else:
            res = np.nan
        return res

    def BildGridXY(tops_inf, layers):
        def remake_grid2(tops_inf):
            x_min, x_max = tops_inf["Xmin"], tops_inf["Xmax"]
            y_min, y_max = tops_inf["Ymin"], tops_inf["Ymax"]
            angle = tops_inf["angle"]
            angle = angle * math.pi / 180

            Nx, Ny = tops_inf["Nx"], tops_inf["Ny"]
            hx = tops_inf["hx"]
            hy = tops_inf["hy"]

            Res_x = np.array([])
            Res_y = np.array([])

            for j in range(Ny + 1):
                for i in range(Nx + 1):
                    xi = i * hx * math.cos(angle) + x_min - j * hy * math.sin(angle)
                    yi = i * hx * math.sin(angle) + y_min + j * hy * math.cos(angle)
                    Res_x = np.append(Res_x, xi)
                    Res_y = np.append(Res_y, yi)

            masN = [Nx, Ny]
            return Res_x, Res_y, masN

        masCell = []
        masPoint = []

        RES_X, RES_Y, masN = remake_grid2(tops_inf)
        Nx = masN[0]
        Ny = masN[1]
        for lay in range(0, layers + 1):
            for xyi in range(0, len(RES_X)):
                masPoint.append(Point(RES_X[xyi], RES_Y[xyi]))

        e_n = 0
        for yi in range(0, Ny):
            for xi in range(0, Nx):
                masPointNum = []
                adjacent_element = []
                e1 = e_n + yi
                e2 = e1 + 1
                e3 = e1 + (Nx + 1)
                e4 = e3 + 1
                e5 = e1 + (Nx + 1) * (Ny + 1) * (layers)
                e6 = e5 + 1
                e7 = e5 + (Nx + 1)
                e8 = e7 + 1
                masPointNum.append(e1)
                masPointNum.append(e2)
                masPointNum.append(e3)
                masPointNum.append(e4)
                masPointNum.append(e5)
                masPointNum.append(e6)
                masPointNum.append(e7)
                masPointNum.append(e8)

                for yb in [-1, 0, 1]:
                    for xb in [-1, 0, 1]:
                        if (xi + xb >= 0 and xi + xb < Nx) and (yi + yb >= 0 and yi + yb < Ny):
                            numEL = (xi + xb) + (yi + yb) * Nx
                            adjacent_element.append(int(numEL))
                masCell.append(Cell(masPointNum, adjacent_element))
                e_n += 1
        return masPoint, masCell, masN, tops_inf["hx"], tops_inf["hy"]

    def Remake_Point_coord_Z(masPoint, masN, v_s, LAY_NUM, Idw):
        def V_S_Nfix(masPoint, masN, Lay_num):
            N = (masN[0] + 1) * (masN[1] + 1)
            dwnI = N * Lay_num
            for i in range(0, N):
                eTop = masPoint[i]
                eBot = masPoint[i + dwnI]
                this_hz = (eBot.z - eTop.z) / Lay_num
                for l in range(1, Lay_num):
                    ind_l = i + (masN[0] + 1) * (masN[1] + 1) * l
                    masPoint[ind_l].z = eTop.z + l * this_hz

        def V_S_Hfix(masPoint, masN, hz_base, layer):
            hz_optimal = hz_base
            N = (masN[0] + 1) * (masN[1] + 1)
            dwnI = N * layer
            h_min = hz_optimal - 0.0
            h_max = hz_optimal + 0.0

            eTop = masPoint[0]
            eBot = masPoint[0 + dwnI]
            base_Nz = round(abs(eBot.z - eTop.z) / hz_optimal, 0)

            for i in range(0, N):
                eTop = masPoint[i]
                eBot = masPoint[i + dwnI]

                if np.isnan(eBot.z) or np.isnan(eTop.z):
                    for l in range(layer - 1, -1, -1):
                        ind_l = i + (masN[0] + 1) * (masN[1] + 1) * l
                        masPoint[ind_l].z = eBot.z
                    continue

                if abs(eTop.z - eBot.z) < hz_optimal:
                    for l in range(layer - 1, 0, -1):
                        ind_l = i + (masN[0] + 1) * (masN[1] + 1) * l
                        masPoint[ind_l].z = eBot.z
                    continue

                if np.isnan(base_Nz):
                    base_Nz = round(abs(eBot.z - eTop.z) / hz_optimal, 0)

                new_hz = (eBot.z - eTop.z) / base_Nz
                if abs(new_hz) < h_min:
                    thisNz = round(abs(eBot.z - eTop.z) / h_min, 0)
                    new_hz = (eBot.z - eTop.z) / thisNz
                    base_Nz = thisNz
                elif abs(new_hz) > h_max:
                    thisNz = round(abs(eBot.z - eTop.z) / h_max, 0)
                    new_hz = (eBot.z - eTop.z) / thisNz
                    base_Nz = thisNz
                else:
                    thisNz = base_Nz
                    new_hz = (eBot.z - eTop.z) / thisNz

                N_thisNz = int(layer - thisNz)

                if thisNz <= layer:
                    for l in range(layer - 1, N_thisNz, -1):
                        ind_l = i + (masN[0] + 1) * (masN[1] + 1) * l
                        masPoint[ind_l].z = eBot.z - (layer - l) * new_hz
                    for l in range(N_thisNz, 0, -1):
                        ind_l = i + (masN[0] + 1) * (masN[1] + 1) * l
                        masPoint[ind_l].z = eTop.z
                else:
                    pass

        if v_s["type"] == "N_fix":
            V_S_Nfix(masPoint, masN, LAY_NUM)
        elif v_s["type"] == "h_fix":
            V_S_Hfix(masPoint, masN, v_s["val"], LAY_NUM)
        else:
            return

    def Bild3DMesh(layers, masCell, workSpaceIndCell, masPoint, masN, angle, err_inf):
        if layers < 1:
            return masCell, []
        resCell = [Cell() for itrCell in range(layers * len(masCell))]
        N_mc = len(masCell)

        for i in tqdm(range(0, N_mc)):
            for lay in range(0, layers):
                collapsed = False
                num_el_1 = masCell[i].point_num[0] + (masN[0] + 1) * (masN[1] + 1) * lay
                num_el_2 = masCell[i].point_num[1] + (masN[0] + 1) * (masN[1] + 1) * lay
                num_el_3 = masCell[i].point_num[2] + (masN[0] + 1) * (masN[1] + 1) * lay
                num_el_4 = masCell[i].point_num[3] + (masN[0] + 1) * (masN[1] + 1) * lay
                num_el_5 = masCell[i].point_num[0] + (masN[0] + 1) * (masN[1] + 1) * (lay + 1)
                num_el_6 = masCell[i].point_num[1] + (masN[0] + 1) * (masN[1] + 1) * (lay + 1)
                num_el_7 = masCell[i].point_num[2] + (masN[0] + 1) * (masN[1] + 1) * (lay + 1)
                num_el_8 = masCell[i].point_num[3] + (masN[0] + 1) * (masN[1] + 1) * (lay + 1)

                num_i = i + lay * len(masCell)
                if not layers == 1:
                    base_adj_el = np.array(masCell[i].adjacent_element)
                    if lay == 0:
                        this_adj_el = np.hstack((base_adj_el, base_adj_el + N_mc))
                    elif lay == layers - 1:
                        this_adj_el = np.hstack((base_adj_el + (lay - 1) * N_mc, base_adj_el + lay * N_mc))
                    else:
                        this_adj_el = np.hstack((base_adj_el + (lay - 1) * N_mc, base_adj_el + lay * N_mc))
                        this_adj_el = np.hstack((this_adj_el, base_adj_el + (lay + 1) * N_mc))
                else:
                    this_adj_el = np.array(masCell[i].adjacent_element)

                e1_i = masPoint[num_el_1]
                e2_i = masPoint[num_el_2]
                e3_i = masPoint[num_el_3]
                e4_i = masPoint[num_el_4]
                e5_i = masPoint[num_el_5]
                e6_i = masPoint[num_el_6]
                e7_i = masPoint[num_el_7]
                e8_i = masPoint[num_el_8]

                check_Znan_top = np.array([e1_i.z, e2_i.z, e3_i.z, e4_i.z])
                if len(check_Znan_top[np.isnan(check_Znan_top)]) > 0:
                    actnum_val = 0
                else:
                    actnum_val = 1

                if abs(e1_i.z - e5_i.z) < 1e-5 and abs(e2_i.z - e6_i.z) < 1e-5 and abs(e3_i.z - e7_i.z) < 1e-5 and abs(
                        e4_i.z - e8_i.z) < 1e-5:
                    collapsed = True

                X_all = [e1_i.x, e2_i.x, e3_i.x, e4_i.x]
                Y_all = [e1_i.y, e2_i.y, e3_i.y, e4_i.y]
                x_c = (np.nanmax(X_all) + np.nanmin(X_all)) / 2
                y_c = (np.nanmax(Y_all) + np.nanmin(Y_all)) / 2

                try:
                    z_0 = (e2_i.z + e6_i.z) / 2
                    z_1 = (e3_i.z + e7_i.z) / 2
                    if abs(z_1 - z_0) < 1e-1:
                        z_c = z_1
                    else:
                        z_c = (e2_i.y - e3_i.y) / (z_0 - z_1) * (y_c - e3_i.y) + z_1
                except:
                    z_c = np.average(
                        [(e1_i.z + e5_i.z) / 2, (e2_i.z + e6_i.z) / 2, (e3_i.z + e7_i.z) / 2, (e4_i.z + e8_i.z) / 2])

                this_cell = Cell([num_el_1, num_el_2, num_el_3, num_el_4, num_el_5, num_el_6, num_el_7, num_el_8],
                                 this_adj_el, [x_c, y_c, z_c])
                this_cell.layZ = lay

                if collapsed:
                    this_cell.collapsed = True

                this_cell.ACTNUM = actnum_val

                resCell[num_i] = this_cell
        workSpaceIndCell = np.array(workSpaceIndCell)
        base_WS = workSpaceIndCell
        for lay in range(1, layers):
            workSpaceIndCell = np.hstack((workSpaceIndCell, base_WS + lay * N_mc))
        return resCell, workSpaceIndCell

    minPower = 0.1
    maxPower = np.nanmax(np.abs(tops_inf["Z"] - bots_inf["Z"]))

    layerZ = Get_num_Lay(vertical_split, maxPower)

    masPoint, masCellXY, masN, hx, hy = BildGridXY(tops_inf, layerZ)

    Z_top = tops_inf["Z"]
    Z_bot = bots_inf["Z"]

    Z_top[np.abs(Z_top - 9999900.0) < 1e-5] = np.nan
    Z_bot[np.abs(Z_bot - 9999900.0) < 1e-5] = np.nan

    dwnI = (masN[0] + 1) * (masN[1] + 1) * layerZ
    for i in range(0, len(Z_top)):
        if Z_top[i] > Z_bot[i]:
            top_val_Z = Z_top[i]
            bot_val_Z = Z_bot[i]
        else:
            dsti_fck = (Z_top[i] + Z_bot[i]) / 2
            top_val_Z = dsti_fck + minPower / 2
            bot_val_Z = dsti_fck - minPower / 2
        masPoint[i].z = top_val_Z
        masPoint[i + dwnI].z = bot_val_Z

    # Заполняем значения Z-координат точек сетки в соответствии с типом вертикального разбиения
    Remake_Point_coord_Z(masPoint, masN, vertical_split, layerZ, dwnI)
    workSpaceIndCell = range(len(masCellXY))

    Cell3D, workSpaceIndCell = Bild3DMesh(layerZ, masCellXY, workSpaceIndCell, masPoint, masN, angle, err_inf)
    return masPoint, Cell3D, workSpaceIndCell, masN, layerZ


def getZcord2(masN, masPoint, outfolder, layerZ):
    f = open(replaceSlash(outfolder + "\\GRID_ZCORN.GRDECL"), "w")
    f.write("-- Generated [ \n")
    f.write("-- Format      : ECLIPSE keywords (ASCII)\n")
    f.write("-- User name   : NeuroPower\n")
    f.write("-- Generated ]\n")
    f.write("\n")
    f.write("ZCORN                                  -- Generated : Petrel \n")

    lenWrite = 0
    vectIndNewCell = 0
    maxEl_str = 20
    thsEl_itr = 0

    for lay in range(0, layerZ):
        for j in range(0, masN[1]):
            for i in range(0, masN[0]):
                f.write(str(-1 * round(masPoint[vectIndNewCell].z, 1)) + " ")
                f.write(str(-1 * round(masPoint[vectIndNewCell + 1].z, 1)) + " ")
                thsEl_itr += 2
                lenWrite += 2
                if thsEl_itr >= maxEl_str:
                    f.write("\n")
                    thsEl_itr = 0
                vectIndNewCell += 1

            vectIndNewCell = vectIndNewCell + 1

            for i in range(0, masN[0]):
                f.write(str(-1 * round(masPoint[vectIndNewCell].z, 1)) + " ")
                f.write(str(-1 * round(masPoint[vectIndNewCell + 1].z, 1)) + " ")
                thsEl_itr += 2
                lenWrite += 2
                if thsEl_itr >= maxEl_str:
                    f.write("\n")
                    thsEl_itr = 0
                vectIndNewCell += 1

            if j == masN[1] - 1:
                vectIndNewCell = vectIndNewCell + 1
            else:
                vectIndNewCell = vectIndNewCell - masN[0]

        for j in range(0, masN[1]):
            for i in range(0, masN[0]):
                f.write(str(-1 * round(masPoint[vectIndNewCell].z, 1)) + " ")
                f.write(str(-1 * round(masPoint[vectIndNewCell + 1].z, 1)) + " ")
                thsEl_itr += 2
                lenWrite += 2
                if thsEl_itr >= maxEl_str:
                    f.write("\n")
                    thsEl_itr = 0
                vectIndNewCell += 1

            vectIndNewCell = vectIndNewCell + 1

            for i in range(0, masN[0]):
                f.write(str(-1 * round(masPoint[vectIndNewCell].z, 1)) + " ")

                if i == masN[0] - 1 and j == masN[1] - 1 and lay == layerZ - 1:
                    f.write(str(-1 * round(masPoint[vectIndNewCell + 1].z, 1)) + " /")
                else:
                    f.write(str(-1 * round(masPoint[vectIndNewCell + 1].z, 1)) + " ")
                thsEl_itr += 2
                lenWrite += 2
                if thsEl_itr >= maxEl_str:
                    f.write("\n")
                    thsEl_itr = 0
                vectIndNewCell += 1

            if j == masN[1] - 1:
                vectIndNewCell = vectIndNewCell + 1
            else:
                vectIndNewCell = vectIndNewCell - masN[0]
        vectIndNewCell = vectIndNewCell - (masN[0] + 1) * (masN[1] + 1)
    f.close()


def getCoord(masN, masPoint, LZ, outfolder):
    f = open(replaceSlash(outfolder + "\\GRID_COORD.GRDECL"), "w")
    f.write("-- Generated [ \n")
    f.write("-- Format      : ECLIPSE keywords (ASCII)\n")
    f.write("-- User name   : NeuroPower\n")
    f.write("-- Generated ]\n")
    f.write("\n")
    f.write("COORD                                  -- Generated : Petrel \n")

    STR = ""
    N = (masN[0] + 1) * (masN[1] + 1)
    n = (masN[0] + 1) * (masN[1] + 1) * LZ
    inddd = 0

    for i in range(0, N):
        e1 = masPoint[i]
        e2 = masPoint[i + n]
        inddd += 2
        STR += str(e1.x) + " " + str(e1.y) + " " + str(-1 * round(e1.z, 1)) + " "
        if i == N - 1:
            STR += str(e2.x) + " " + str(e2.y) + " " + str(-1 * round(e2.z, 1)) + " /\n"
        else:
            STR += str(e2.x) + " " + str(e2.y) + " " + str(-1 * round(e2.z, 1)) + "\n"
    f.write(STR)
    f.close()


def getACTNUM(masN, newCell, outfolder):
    f = open(replaceSlash(outfolder + "\\GRID_ACTNUM.GRDECL"), "w")
    f.write("-- Generated [ \n")
    f.write("-- Format      : ECLIPSE keywords (ASCII)\n")
    f.write("-- User name   : NeuroPower\n")
    f.write("-- Generated ]\n")
    f.write("\n")
    f.write("ACTNUM                                  -- Generated : Petrel \n")

    ACTNUM_str = ""
    i20 = 0
    for i in range(0, len(newCell)):
        if i20 == 25:
            ACTNUM_str += str(newCell[i].ACTNUM) + " \n"
            i20 = 0
        else:
            ACTNUM_str += str(newCell[i].ACTNUM) + " "
        i20 += 1
    ACTNUM_str += "/"
    f.write(ACTNUM_str + "\n")
    f.close()


def Save_Model(outfolder, masPoint, newCell, masN, layerZ):
    GRID = open(replaceSlash(outfolder + "\\GRID.GRDECL"), "w")
    GRID.write("-- Generated [ \n")
    GRID.write("-- Format      : ECLIPSE keywords (grid geometry and properties) (ASCII)\n")
    GRID.write("-- Exported by : Petrel 2013.2 (64-bit) Schlumberger\n")
    GRID.write("-- User name   : NeuroPower\n")
    GRID.write("-- Date        : Monday, February 12 2018 10:21:07\n")
    GRID.write("-- Project     : Carb_oil_18-12-2017.pet\n")
    GRID.write("-- Grid        : 3D grid\n")
    GRID.write("-- Generated ]\n")

    GRID.write("PINCH                                  -- Generated : Petrel \n")
    GRID.write("  /\n")
    GRID.write("\n")

    GRID.write("NOECHO                                  -- Generated : Petrel \n")
    GRID.write("\n")

    GRID.write("MAPUNITS                                  -- Generated : Petrel \n")
    GRID.write("  METRES /\n")
    GRID.write("\n")

    GRID.write("MAPAXES                                  -- Generated : Petrel \n")
    MAPAXES_str = str(masPoint[newCell[0].point_num[2]].x) + " " + str(masPoint[newCell[0].point_num[2]].y) + " "
    MAPAXES_str += str(masPoint[newCell[0].point_num[0]].x) + " " + str(masPoint[newCell[0].point_num[0]].y) + " "
    MAPAXES_str += str(masPoint[newCell[0].point_num[1]].x) + " " + str(masPoint[newCell[0].point_num[1]].y) + " "
    MAPAXES_str += "/\n"
    GRID.write(MAPAXES_str)
    GRID.write("\n")

    GRID.write("GRIDUNIT                                  -- Generated : Petrel \n")
    GRID.write("  METRES MAP /\n")
    GRID.write("\n")

    GRID.write("SPECGRID                                  -- Generated : Petrel \n")
    SPECGRID_str = "  " + str(masN[0]) + " " + str(masN[1]) + " " + str(layerZ) + " 1 F /\n"
    GRID.write(SPECGRID_str)
    GRID.write("\n")

    GRID.write("COORDSYS                                  -- Generated : Petrel \n")
    COORDSYS_str = "  1 " + str(layerZ) + " /\n"
    GRID.write(COORDSYS_str)
    GRID.write("\n")

    GRID.write("INCLUDE                                  -- Generated : Petrel \n")
    GRID.write("'GRID_COORD.GRDECL' /\n")
    GRID.write("\n")
    GRID.write("INCLUDE                                  -- Generated : Petrel \n")
    GRID.write("'GRID_ZCORN.GRDECL' /\n")
    GRID.write("\n")
    GRID.write("INCLUDE                                  -- Generated : Petrel \n")
    GRID.write("'GRID_ACTNUM.GRDECL' /\n")
    GRID.write("\n")
    GRID.write("ECHO                                  -- Generated : Petrel \n")

    GRID.close()

    getZcord2(masN, masPoint, outfolder, layerZ)
    getCoord(masN, masPoint, layerZ, outfolder)
    getACTNUM(masN, newCell, outfolder)


def Read_surface(path_top, path_bot):
    tops_inf = {}
    tops_inf.update({"Z": np.array([])})
    bots_inf = {}
    bots_inf.update({"Z": np.array([])})

    f_tops = open(path_top)
    it_line = 0
    for line_t in f_tops.readlines():
        line_splt = line_t.split(" ")
        line_splt = [line.rstrip() for line in line_splt]

        if it_line == 0:
            tops_inf.update({
                "Ny": int(line_splt[1]) - 1,
                "hx": float(line_splt[2]),
                "hy": float(line_splt[3])
            })
        elif it_line == 1:
            tops_inf.update({
                "Xmin": float(line_splt[0]),
                "Xmax": float(line_splt[1]),
                "Ymin": float(line_splt[2]),
                "Ymax": float(line_splt[3])
            })
        elif it_line == 2:
            tops_inf.update({
                "Nx": int(line_splt[0]) - 1,
                "angle": float(line_splt[1])
            })
        elif it_line == 3:
            pass
        else:
            for i in range(len(line_splt)):
                try:
                    tops_inf["Z"] = np.append(tops_inf["Z"], float(line_splt[i]))
                except BaseException as exc:
                    # print(exc)

                    pass
        it_line += 1

    f_bots = open(path_bot)
    it_line = 0
    for line_b in f_bots.readlines():
        line_splt = line_b.split(" ")
        line_splt = [line.rstrip() for line in line_splt]

        if it_line == 0:
            bots_inf.update({
                "Ny": int(line_splt[1]) - 1,
                "hx": float(line_splt[2]),
                "hy": float(line_splt[3])
            })
        elif it_line == 1:
            bots_inf.update({
                "Xmin": float(line_splt[0]),
                "Xmax": float(line_splt[1]),
                "Ymin": float(line_splt[2]),
                "Ymax": float(line_splt[3])
            })
        elif it_line == 2:
            bots_inf.update({
                "Nx": int(line_splt[0]) - 1,
                "angle": float(line_splt[1])
            })
        elif it_line == 3:
            pass
        else:
            for i in range(len(line_splt)):
                try:
                    bots_inf["Z"] = np.append(bots_inf["Z"], float(line_splt[i]))
                except BaseException as exc:
                    # print(exc)
                    pass
        it_line += 1

    # check
    check_bound = abs(tops_inf["Xmin"] - bots_inf["Xmin"]) < 1e-5 and abs(
        tops_inf["Xmax"] - bots_inf["Xmax"]) < 1e-5 and abs(tops_inf["Ymin"] - bots_inf["Ymin"]) < 1e-5 and abs(
        tops_inf["Ymax"] - bots_inf["Ymax"]) < 1e-5

    check_hx_hy = abs(tops_inf["hx"] - bots_inf["hx"]) < 1e-5 and abs(tops_inf["hy"] - bots_inf["hy"]) < 1e-5

    check_angle = abs(tops_inf["angle"] - bots_inf["angle"]) < 1e-5

    check_size = abs(tops_inf["Nx"] - bots_inf["Nx"]) < 1e-5 and abs(tops_inf["Ny"] - bots_inf["Ny"]) < 1e-5

    if check_bound and check_hx_hy and check_angle and check_size:
        check_surf = True
    else:
        check_surf = False

    return tops_inf, bots_inf, check_surf


# конвертация путей файлов в зависимости от системы
def replaceSlash(filePath):
    platform = sys.platform
    slashMap = {'win32': '\\',
                'cygwin': '\\',
                'darwin': '/',
                'linux2': '/'}
    if platform not in slashMap.keys(): platform = 'linux2'
    return filePath.replace('\\', slashMap[platform])


def loadConfig(Err_count, pattern_text_log, abs_path):
    try:
        dc = None
        with open(abs_path + 'configuration_3D_grid.json', 'r') as fc:
            dc = json.load(fc)
    except BaseException as e:
        logging.error(pattern_text_log, "", 'Ошибка при загрузке файла конфигурации. ' + str(e))
        Err_count += 1
        return None

    return dc


def get_3D(run_id):
    abs_path = 'app/modules/sixth/'
    run_path = abs_path + str(run_id) + '/'

    out_path_log = replaceSlash(run_path + "\\output_data\\Report.txt")
    logging.basicConfig(format=u'%(levelname)-8s : %(message)s', level=logging.WARNING, filename=out_path_log,
                        filemode='w')
    Err_count = 0
    pattern_text_log = '   %s   :   %s'


    Err_count = 0

    outfolder = run_path + 'output_data'
    path_top = replaceSlash(run_path + "input_data\\SurfaceTOP.txt")
    path_bot = replaceSlash(run_path + "input_data\\SurfaceBOT.txt")

    config = loadConfig(Err_count, pattern_text_log, abs_path)
    if config is None:
        sys_exit()

    try:
        HZ_val = float(config["hz"])
    except BaseException as e:
        logging.error(pattern_text_log, "", "read hz. " + str(e))
        Err_count += 1
        sys_exit()

    try:
        tops_inf, bots_inf, check_surf = Read_surface(path_top, path_bot)
    except BaseException as e:
        logging.error(pattern_text_log, "", "Read_surface. " + str(e))
        Err_count += 1
        sys_exit()

    if check_surf == False:
        sys_exit()

    vertical_split = {"type": "h_fix",
                      "val": HZ_val
                      }

    try:
        masPoint, newCell, workSpaceIndCell, masN, layerZ = Construction_3D_grid(tops_inf, bots_inf, vertical_split,
                                                                                 tops_inf["angle"], [])
    except BaseException as e:
        logging.error(pattern_text_log, "", "Construction_3D_grid. " + str(e))
        Err_count += 1
        sys_exit()

    try:
        obj = {
            "masPoint": masPoint,
            "newCell": newCell,
            "masN": masN,
            "layerZ": layerZ,
            "angle": tops_inf["angle"]
        }
        out_pp = replaceSlash(outfolder + "\\" + "grid_struct.pickle")
        output = open(out_pp, 'wb')
        pickle.dump(obj, output)
        output.close()
    except BaseException as e:
        logging.error(pattern_text_log, "", "write pickle-file. " + str(e))
        Err_count += 1

    try:
        val_mean = np.nanmean(np.hstack((tops_inf["Z"], bots_inf["Z"])))
        for p in masPoint:
            if np.isnan(p.z):
                p.z = val_mean
        Save_Model(outfolder, masPoint, newCell, masN, layerZ)
    except BaseException as e:
        logging.error(pattern_text_log, "", "Save_Model. " + str(e))
        Err_count += 1

    if Err_count == 0:
        logging.addLevelName(100, "INFO")
        logging.log(100, pattern_text_log, "", "No errors in data")
