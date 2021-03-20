import math
from tqdm import tqdm
from pykrige.ok import OrdinaryKriging
import numpy as np


class fes_interpolation(object):
    def __init__(self):
        self.TypeInterpolate = "spherical"
        self.variogram_range = 350

    def GetABCD(self, x0, y0, z0, x1, y1, z1, x2, y2, z2):
        k1 = (y1 - y0) * (z2 - z0) - (z1 - z0) * (y2 - y0)
        k2 = (x1 - x0) * (z2 - z0) - (z1 - z0) * (x2 - x0)
        k3 = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
        A = k1
        B = -k2
        C = k3
        D = k1 * (-x0) - k2 * (-y0) + k3 * (-z0)
        return [A, B, C, D]

    def Cell_FES(self, LD):
        N = int(LD.masN[0] * LD.masN[1])
        for W in tqdm(LD.WELLS):
            Ind0 = W.Icell
            if LD.inPolygonXY(LD.masPoint[LD.newCell[Ind0].point_num[0]],
                              LD.masPoint[LD.newCell[Ind0].point_num[1]],
                              LD.masPoint[LD.newCell[Ind0].point_num[2]],
                              W.X, W.Y):
                location_well = 0
            else:
                location_well = 1

            for li in range(LD.layerZ):
                IndI = Ind0 + li * N
                if LD.newCell[IndI].collapsed == True:
                    continue
                p1 = LD.masPoint[LD.newCell[IndI].point_num[0]]
                p2 = LD.masPoint[LD.newCell[IndI].point_num[1]]
                p3 = LD.masPoint[LD.newCell[IndI].point_num[2]]
                p4 = LD.masPoint[LD.newCell[IndI].point_num[3]]
                p5 = LD.masPoint[LD.newCell[IndI].point_num[4]]
                p6 = LD.masPoint[LD.newCell[IndI].point_num[5]]
                p7 = LD.masPoint[LD.newCell[IndI].point_num[6]]
                p8 = LD.masPoint[LD.newCell[IndI].point_num[7]]

                try:
                    if location_well == 0:
                        ABCD_top = self.GetABCD(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z, p3.x, p3.y, p3.z)
                        ABCD_bot = self.GetABCD(p5.x, p5.y, p5.z, p6.x, p6.y, p6.z, p7.x, p7.y, p7.z)
                    else:
                        ABCD_top = self.GetABCD(p2.x, p2.y, p2.z, p3.x, p3.y, p3.z, p4.x, p4.y, p4.z)
                        ABCD_bot = self.GetABCD(p6.x, p6.y, p6.z, p7.x, p7.y, p7.z, p8.x, p8.y, p8.z)

                    z_top_i = (-ABCD_top[0] * W.X - ABCD_top[1] * W.Y - ABCD_top[3]) / ABCD_top[2]
                    z_bot_i = (-ABCD_bot[0] * W.X - ABCD_bot[1] * W.Y - ABCD_bot[3]) / ABCD_bot[2]

                    for nm_crv in LD.name_interp_crv:
                        crv_fes = W.crv[nm_crv][np.logical_and(W.crv["Z"] <= z_top_i, W.crv["Z"] >= z_bot_i)]
                        LD.newCell[IndI].FES.update({nm_crv: crv_fes})
                except Exception as e:
                    print(e)
                    pass

    def oneFES_interp(self, fes_n, LD):
        def upscaling_fes(x):
            res = np.nanmean(x)
            return res

        N = int(LD.masN[0] * LD.masN[1])
        for lay in tqdm(range(0, LD.layerZ)):
            x_grid, y_grid = [], []
            interp_x, interp_y = [], []
            interp_fes = []
            ind_lay = np.array([])

            for i in range(N):
                i_c = i + lay * N

                x_grid.append(LD.newCell[i_c].centre[0])
                y_grid.append(LD.newCell[i_c].centre[1])

                ind_lay = np.append(ind_lay, i_c)

                if LD.newCell[i_c].ACTNUM == 0 or LD.newCell[i_c].collapsed == True:
                    ind_lay[-1] = np.nan
                    continue

                if fes_n in LD.newCell[i_c].FES.keys():
                    if not len(LD.newCell[i_c].FES[fes_n]) == 0 and not len(
                            LD.newCell[i_c].FES[fes_n][~np.isnan(LD.newCell[i_c].FES[fes_n])]) == 0:
                        interp_x.append(LD.newCell[i_c].centre[0])
                        interp_y.append(LD.newCell[i_c].centre[1])
                        interp_fes.append(upscaling_fes(LD.newCell[i_c].FES[fes_n]))

            if len(interp_fes) < 4:
                for ind in range(len(ind_lay)):
                    if not np.isnan(ind_lay[ind]):
                        i_c = int(ind_lay[ind])
                        LD.newCell[i_c].ACTNUM == 0
                        if not fes_n in LD.newCell[i_c].FES_c.keys():
                            LD.newCell[i_c].FES_c.update({fes_n: np.nan})
                        else:
                            LD.newCell[i_c].FES_c[fes_n] = np.nan
                continue

            OK = OrdinaryKriging(interp_x, interp_y, interp_fes, variogram_model=self.TypeInterpolate,
                                 variogram_parameters={'sill': 1, 'range': self.variogram_range, 'nugget': 0}
                                 )

            fes_data_loc = OK.execute('points', x_grid, y_grid)[0].data

            for ind in range(len(ind_lay)):
                if not np.isnan(ind_lay[ind]):
                    val = fes_data_loc[ind]
                    if fes_n.upper() == "PORO_OPEN_AUTO":
                        if val <= 0:
                            val = 0
                        if val >= 1:
                            val = 1
                    elif fes_n.upper() == "SOIL_VOL_AUTO":
                        if val <= 0:
                            val = 0
                        if val >= 0.9:
                            val = 0.9
                    elif fes_n.upper() == "AGK_AUTO":
                        if val <= 0:
                            val = 0
                        if val >= 1.0:
                            val = 1.0
                    elif fes_n.upper() == "SOIL_MASS_AUTO":
                        if val <= 0:
                            val = 0
                    elif fes_n.upper() == "PERM_HOR_AUTO":
                        if val <= 0:
                            val = 0
                    elif fes_n.upper() == "VOLUME_DENSITY_AUTO":
                        if val <= 0:
                            val = 0

                    i_c = int(ind_lay[ind])
                    if not fes_n in LD.newCell[i_c].FES_c.keys():
                        LD.newCell[i_c].FES_c.update({fes_n: val})
                    else:
                        LD.newCell[i_c].FES_c[fes_n] = val
            del x_grid
            del y_grid
            del ind_lay
            del interp_x
            del interp_y
            del interp_fes

    def FES_interp(self, LD):
        for fes_n in LD.name_interp_crv:
            self.oneFES_interp(fes_n, LD)
