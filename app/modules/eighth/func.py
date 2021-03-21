import math
from tqdm import tqdm
import numpy as np
from matplotlib import path

class Zapas(object):
    def __init__(self):
        self.poro_bnd  = 0.2
        self.soilM_bnd = 4.5
        self.soilV_bnd = 0.05
        self.Zapas_all = None
        self.Zapas_ton = None
    
    def GetABCD(self, x0, y0, z0, x1, y1, z1, x2, y2, z2):
        k1 = (y1 - y0) * (z2 - z0) - (z1 - z0) * (y2 - y0)
        k2 = (x1 - x0) * (z2 - z0) - (z1 - z0) * (x2 - x0)
        k3 = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
        A = k1
        B = -k2
        C = k3
        D = k1 * (-x0) - k2 * (-y0) + k3 * (-z0)
        return [A, B, C, D]
    
    def inPolygonXY(self, e1, e2, e3, xp, yp):
        RES = False
        
        if abs(e2.y - e1.y) < 1e-5:
            if (xp >= e1.x) and (xp <= e2.x) and abs(e2.y - yp) < 1e-5:
                return True
                
        Polygon_path = path.Path([(e1.x, e1.y), (e2.x, e2.y), (e3.x, e3.y)])
        if Polygon_path.contains_point((xp, yp)):
            RES =  True
        return RES
    
    def get_Volume(self, p1, p2, p3, p4, p5, p6, p7, p8, angle):
        try:
            ABCD_T_l = self.GetABCD(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z, p3.x, p3.y, p3.z)
            ABCD_B_l = self.GetABCD(p5.x, p5.y, p5.z, p6.x, p6.y, p6.z, p7.x, p7.y, p7.z)
            ABCD_T_r = self.GetABCD(p2.x, p2.y, p2.z, p3.x, p3.y, p3.z, p4.x, p4.y, p4.z)
            ABCD_B_r = self.GetABCD(p6.x, p6.y, p6.z, p7.x, p7.y, p7.z, p8.x, p8.y, p8.z)
            
            I = 0
            
            nx = 5
            ny = 5
            
            angle = angle * math.pi / 180
            
            hx = math.sqrt((p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y)) / nx
            hy = math.sqrt((p1.x - p3.x) * (p1.x - p3.x) + (p1.y - p3.y) * (p1.y - p3.y)) / ny
            
            x_min = p1.x + hx / 2 * math.cos(angle) - hy / 2 * math.sin(angle)
            y_min = p1.y + hx / 2 * math.sin(angle) + hy / 2 * math.cos(angle)
            
            
            for j in range(ny):
                for i in range(nx):
                    xc = i * hx * math.cos(angle) + x_min - j * hy * math.sin(angle)
                    yc = i * hx * math.sin(angle) + y_min + j * hy * math.cos(angle)
                    
                    if self.inPolygonXY(p1, p2, p3, xc, yc):
                        z_min = (-ABCD_B_l[0] * xc - ABCD_B_l[1] * yc - ABCD_B_l[3]) / ABCD_B_l[2]
                        z_max = (-ABCD_T_l[0] * xc - ABCD_T_l[1] * yc - ABCD_T_l[3]) / ABCD_T_l[2]
                    elif self.inPolygonXY(p2, p3, p4, xc, yc):
                        z_min = (-ABCD_B_r[0] * xc - ABCD_B_r[1] * yc - ABCD_B_r[3]) / ABCD_B_r[2]
                        z_max = (-ABCD_T_r[0] * xc - ABCD_T_r[1] * yc - ABCD_T_r[3]) / ABCD_T_r[2]
                    else:
                        continue
                    
                    I += (hx * hy * abs(z_max - z_min))
            return I
        except Exception as e:
            return 0
    
    def get_zapas(self, LD):
        N = LD.masN[0] * LD.masN[1]
        if not LD.contr is None:
            X = LD.contr[:, 0][0 : -1]
            Y = LD.contr[:, 1][0 : -1]
            Z = LD.contr[:, 2][0 : -1]
            Xsc = np.array([])
            Ysc = np.array([])
            
            for c in LD.newCell[0: N]:
                Xsc = np.append(Xsc, c.centre[0])
                Ysc = np.append(Ysc, c.centre[1])
            
            Polygon_path = path.Path(list(zip(X, Y)))
            ind_w = Polygon_path.contains_points(list(zip(Xsc, Ysc)), radius = 1e-3)
        else:
            ind_w = np.array(list(range(N)), dtype = int)
        
        ZAPAS = 0.0
        
        for ci in tqdm(range(len(ind_w))):
            if ind_w[ci]:
                for l in range(LD.layerZ):
                    ind_c = ci + l * N
                    c = LD.newCell[ind_c]
                    if not c.ACTNUM == 0:
                        try:
                            bool1 = c.FES_c["PORO_OPEN_AUTO"] > self.poro_bnd 
                            bool2 = c.FES_c["SOIL_MASS_AUTO"] > self.soilM_bnd
                            bool3 = c.FES_c["SOIL_VOL_AUTO" ] > self.soilV_bnd
                            volume = self.get_Volume(LD.masPoint[c.point_num[0]], LD.masPoint[c.point_num[1]],
                                                    LD.masPoint[c.point_num[2]], LD.masPoint[c.point_num[3]],
                                                    LD.masPoint[c.point_num[4]], LD.masPoint[c.point_num[5]],
                                                    LD.masPoint[c.point_num[6]], LD.masPoint[c.point_num[7]],
                                                    LD.angle)
                            if bool1 and bool2 and bool3:
                                val = volume * c.FES_c["PORO_OPEN_AUTO"] * c.FES_c["SOIL_VOL_AUTO"]
                                ZAPAS += val
                                if not "reserves_M" in c.FES_c.keys():
                                    c.FES_c.update({"reserves_M" : val})
                                else:
                                    c.FES_c["reserves_M"] = val
                                    
                                if not "reserves_T" in c.FES_c.keys():
                                    c.FES_c.update({"reserves_T" : val * LD.ro_oil})
                                else:
                                    c.FES_c["reserves_T"] = val * LD.ro_oil
                        except Exception as e:
                            print(e)
                            pass
        self.Zapas_all = round(ZAPAS, 4)
        self.Zapas_ton = self.Zapas_all * LD.ro_oil
        LD.name_interp_crv.append("reserves_VOL")
        LD.name_interp_crv.append("reserves_MASS")
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    