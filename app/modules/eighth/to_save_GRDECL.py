from tqdm import tqdm
import numpy as np

class to_save_GRDECL(object):
    def __init__(self, _LD, outfolder, val_save = 'all'):
        
        self.LD = _LD
        self.outfolder = outfolder
        
        for p in self.LD.masPoint:
            if np.isnan(p.z):
                p.z = -9999
                
        if val_save == "all":
            self.getZcord2(self.LD.masN, self.LD.masPoint, self.LD.layerZ)
            self.getCoord (self.LD.masN, self.LD.masPoint, self.LD.layerZ)
            self.getACTNUM(self.LD.masN, self.LD.newCell)
        
        if val_save == "all" or val_save == 'properties':
            for k in self.LD.name_interp_crv:
                self.Save_properties(self.LD.newCell, k)

    def getZcord2(self, masN, masPoint, layerZ):
        f = open( self.LD.replaceSlash( self.outfolder + "\\GRID_ZCORN.GRDECL" ), "w" )
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
        
    def getCoord(self, masN, masPoint, LZ):
        f = open( self.LD.replaceSlash( self.outfolder + "\\GRID_COORD.GRDECL" ), "w" )
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
        
    def getACTNUM(self, masN, newCell):
        f = open( self.LD.replaceSlash( self.outfolder + "\\GRID_ACTNUM.GRDECL" ), "w" )
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
    
    def Save_properties(self, newCell, keyFES):
        GRID = open( self.LD.replaceSlash( self.outfolder + "\\GRID_PROP_" + keyFES + ".GRDECL" ), "w" )
        GRID.write(keyFES + "                                  -- Generated : Petrel \n")
        _str = ""
        i20 = 0
        for i in range(0, len(newCell)):
            try:
                if np.isnan(newCell[i].FES_c[keyFES]):
                    newCell[i].ACTNUM = 0
                    val = -9999
                else:
                    val = round(newCell[i].FES_c[keyFES], 4)
            except:
                newCell[i].ACTNUM = 0
                val = -9999
            
            
            
            if i20 == 25:
                _str += str(val) + " \n"
                i20 = 0
            else:
                _str += str(val) + " "
            i20 += 1
        _str += "/"
        GRID.write(_str + "\n")
        GRID.close()
    
    def Save_Model(self, masPoint, newCell, masN, layerZ):
        GRID = open( self.LD.replaceSlash( self.outfolder + "\\GRID.GRDECL" ), "w" )
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
        MAPAXES_str = str(masPoint[newCell[0].point_num[2]].x) + " "+ str(masPoint[newCell[0].point_num[2]].y) + " "
        MAPAXES_str += str(masPoint[newCell[0].point_num[0]].x) + " "+ str(masPoint[newCell[0].point_num[0]].y) + " "
        MAPAXES_str += str(masPoint[newCell[0].point_num[1]].x) + " "+ str(masPoint[newCell[0].point_num[1]].y) + " "
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
    

