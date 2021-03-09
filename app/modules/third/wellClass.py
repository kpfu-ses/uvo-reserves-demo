import lasio
import codecs
import re


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


class Well:
    def __init__(self, filename):
    
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
        enc = 'None'
        maxLen = 999999
        maybeEnc = 'ascii'
        regex = r"[^а-яА-Яa-zA-Z\s\0\^\$\`\~\!\@\"\#\№\;\%\^\:\?\*\(\)\-\_\=\+\\\|\[\]\{\}\,\.\/\'\d]"
        for e in encodincs:
            try:
                cod = codecs.open(filename, 'r', encoding=e)
                l = str(cod.read())
                l = l.replace(' ','')
                check = re.findall(regex,l)
                curLen = len(check)
                if curLen != 0:
                    if curLen < maxLen:
                        maxLen = curLen
                        maybeEnc = e
                else:
                    enc = e
                    break
            except Exception as e:
                continue
        if enc == 'None': enc = maybeEnc
        if enc != 'None':
            try:
                self.lasObject = lasio.read(filename, encoding=enc)
            except:
                newFile = checkAndFixLas(filename,enc)
                self.lasObject = lasio.read(newFile,encoding=enc,ignore_header_errors=True)
        
        #self.lasObject = lasio.read(filename, encoding='cp1251')
        #считываем с полученного лас-объекта все кривые(геофизические методы ГК НГК....)
        self.curves = {curve.mnemonic : curve.data for curve in self.lasObject.curves}
    
        #считываем с лас-объекта имя скважины
        self.name = str(self.lasObject.well["WELL"].value)
    
        IK_names = ["ik", "ILD", "ИК", "IK1", "IK:1", "ИK  "]
        for name in IK_names:
            if name in self.curves.keys():
                self.curves["IK"] = self.curves[name]
    
        GK_names = ["GKV", "GR", "ГK", "gk", "GK1", "гк", "GK:1", "ГК  "]
        for name in GK_names:
            if name in self.curves.keys():
                self.curves["GK"] = self.curves[name]
    
        NGK_names = ["NGL", "НГК", "NKDT", "JB", "JM", "ngk", "NGK:1", "ННКБ", "NNKB", "NNKB  (ННКБ)", "БЗ ННК", "NKTD"]
        for name in NGK_names:
            if name in self.curves.keys():
                self.curves["NGK"] = self.curves[name]
    
        if "MD" in self.curves.keys():
            self.curves["DEPT"] = self.curves["MD"]
            del self.curves["MD"]
