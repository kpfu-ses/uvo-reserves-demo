from threading import Thread
import os
import codecs
import re


def save_async_file(file, filename, app):
    with app.app_context():
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))


def save_file(file, filename, app):
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Thread(target=save_async_file, args=(file, filename, app)).start()


def guess_enc(file):
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
    regex = r"[^а-яА-Яa-zA-Z\s\0\^\$\`\~\!\@\"\#\№\;\%\^\:\?\*\(\)\-\_\=\+\\\|\[\]\{\}\,\.\/\'\d]"

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
        except BaseException as exc:
            pass
    return enc if enc is not 'None' else maybeEnc


def well_name_re(well_name):
    reg_well_name = r"[^0-9]"
    return re.sub(reg_well_name, '', well_name.replace(' ', ''))
