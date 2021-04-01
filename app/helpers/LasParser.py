import os
import codecs
import lasio
import re
import numpy as np

from app import db
from app.helpers.util import guess_enc
from app.models import Well, Curve, Logs
from app.helpers.util import well_name_re


class ImportLasFiles:
    def __init__(self, file_paths, project_id, unnamed_well):
        self.project_id = project_id
        self.file_paths = file_paths
        self.wells = []
        self.list_well = []
        self.wells_from_files = {}  # сгруппированные по названиям скважин лас-файлы
        self.wells_with_empty_name = {}  # скважины с пустыми названиями
        self.md_keys = ["dept", "md", "depth", "dpt"]
        self.globalStep = 0.1
        self.unnamed_well = unnamed_well

    @staticmethod
    def create_line(line):
        new_line = ''
        p = line.split(':')
        new_line = new_line + p[0] + '. :'
        for i in range(1, len(p)):
            new_line = new_line + p[i]
        return new_line

    def check_and_fix_las(self, file):
        """исправление  Las-файла

        Args:
            file ([str]): [путь до файла]

        Returns:
            file - путь до файла
            encoding -кодировка для лас-файла
            is_new_file - True, если создали новый файл, иначе False
        """

        encoding = guess_enc(file)
        f = codecs.open(file, 'r', encoding=encoding)

        text = f.read()
        if text.lower().find('~parameter'):
            fix_param = True
        else:
            fix_param = False
        text = text.split('\n')
        f.close()
        need_fix = False

        is_new_file = False

        i = 0
        while text[i].lower().find('~well') == -1:
            i = i + 1
        i = i + 1
        while text[i].find('~') == -1:
            i = i + 1
            line = text[i]
            if line.find(':') != -1:
                if line.split(' ')[0].find('.') == -1:
                    need_fix = True
                    # Прибавляем к первому слову '.' и соединяем оставшуюся строку
                    new_line = line.split(' ')[0] + '.' + ' '.join(
                        line.split(' ')[1:])
                    text[i] = new_line

        while text[i].lower().find('~curve') == -1:
            i = i + 1
        i = i + 1
        while text[i].find('~') == -1:
            line = text[i]
            if line.find(':') != -1:
                if line.find('.') == -1 or line.find('.') > line.rfind(':'):
                    need_fix = True
                    new_line = self.create_line(line)
                    text[i] = new_line
            else:
                if line.find('.') != -1:
                    need_fix = True
                    p = line.split('.')
                    new_line = p[0] + '. :'
                    for k in range(1, len(p)):
                        new_line = new_line + p[k]
                    text[i] = new_line
            i = i + 1
        if fix_param:
            while i < len(text) and text[i].lower().find('~parameter') == -1:
                if i - 1 < len(text):
                    i = i + 1

            i = i + 1
            while i < len(text) and text[i].find('~') == -1:
                i = i + 1
                line = text[i]
                if line.find(':') != -1:
                    if line.split(' ')[0].find('.') == -1:
                        need_fix = True
                        # Прибавляем к первому слову '.' и соединяем оставшуюся строку
                        new_line = line.split(' ')[0] + '.' + ' '.join(
                            line.split(' ')[1:])
                        text[i] = new_line
        if need_fix:
            file = file.replace('.las', '').replace('.LAS', '') + '(copy).las'
            f = codecs.open(file, 'w', encoding=encoding)
            is_new_file = True
            for line in text:
                f.write(line + '\n')
            f.close()
            need_fix = False
            i = 0
            while text[i].lower().find('~curve') == -1:
                i = i + 1
            i = i + 1
            while text[i].find('~') == -1:
                line = text[i]
                if line.find(':') != -1:
                    if line.find('.') == -1 or line.find('.') > line.rfind(
                            ':'):
                        need_fix = True
                        new_line = self.create_line(line)
                        text[i] = new_line
                else:
                    if line.find('.') != -1:
                        need_fix = True
                        p = line.split('.')
                        new_line = p[0] + '. :'
                        for k in range(1, len(p)):
                            new_line = new_line + p[k]
                        text[i] = new_line
                i = i + 1
            if need_fix:
                file = file.replace('.las', '').replace('.LAS',
                                                        '') + '(copy).las'
                is_new_file = True
        f = codecs.open(file, 'w', encoding=encoding)
        for line in text:
            f.write(line + '\n')
        f.close()
        rewrite_file = ""
        with open(file, "r", encoding=encoding) as f:
            for line in f:
                if line[0:4] == "NULL" and line[5] != ".":
                    if line.find("Missing value") != -1:
                        rewrite_file += line[0:4] + line[line.rfind("."):]
                    else:
                        rewrite_file += line[0:4] + line[line.find("."):]
                else:
                    rewrite_file += line
        with open(file, "w", encoding=encoding) as f:
            f.write(rewrite_file)

        return file, encoding, is_new_file

    def import_data(self):
        file_names, incorrect_files = self.check_las_files()
        if len(file_names) > 0:
            self.start_las_reader(file_names)
        return incorrect_files

    def wells_info_struct(self):
        # функция формирующая список из объектов класса скважина. Выполняется приведение данных ГИС к общей сетке относительных глубин
        list_names = list(self.wells_from_files.keys())
        list_names = [str(name).replace(' ', '') for name in list_names]
        if "empty_well" in list_names:
            list_names.remove("empty_well")

        res_wells = {}
        for w_name in list_names:
            dept = self.get_global_dept(w_name)

            well = self.create_well_obj(w_name, dept)

            res_wells.update({w_name: well})
        return res_wells

    def create_curve_obj(self, data, mnem, unit, file_name, well):
        """Создание объекта Curve из CurveItem las-файла
        Args:
            las_curve_item ([type]): [элемент кривой из лас файла]
        """
        # if well:
        curve = Curve()
        if len(file_name.split('.')) > 1:
            curve.filename = file_name.split('.')[0]
        else:
            curve.filename = file_name
        curve.name = mnem
        curve.unit = unit
        curve.data = data
        curve.well_id = well.id
        curve.project_id = self.project_id

        if well:
            dpt = np.array(well.depth)
            dpt_cut = dpt[~np.isnan(data)]
            if len(dpt_cut) > 0:
                curve.top = self.round_on_condition(dpt_cut[0])
                curve.bottom = self.round_on_condition(dpt_cut[-1])
                # curve.top = round(dpt_cut[0], 2)
                # curve.bottom = round(dpt_cut[-1], 2)
            else:
                curve.top, curve.bottom = None, None

        # curve.data.setCurvesMgr(self.dataMgr.curves())
        # curve.data.set(values)
        return curve

    # Интерполяция для построения общей сетки глубин
    @staticmethod
    def new_mesh(CRV, DEPT, new_mesh):
        if len(CRV[~np.isnan(CRV)]) < 3:
            new_crv = np.ones(len(new_mesh)) * np.nan
        else:
            # new_crv = np.interp(new_mesh, DEPT[~np.isnan(CRV)], CRV[~np.isnan(CRV)], left=np.nan, right=np.nan)
            new_crv = np.interp(new_mesh, DEPT, CRV, left=np.nan, right=np.nan)
        return new_crv

    @staticmethod
    def round_on_condition(cell):
        """Округление по условию"""
        if cell >= 1:
            cell = round(cell, 2)
        elif cell > 0.1:
            cell = round(cell, 3)
        else:
            cell = round(cell, 5)
        return cell

    def create_well_obj(self, w_name, dept):
        well = Well.query.filter_by(name=w_name, project_id=self.project_id).first()
        if well is None:
            well = Well(name=w_name, project_id=self.project_id)
            db.session.add(well)
            db.session.flush()

        if Logs.query.filter_by(well_id=well.id, project_id=self.project_id).first() is None:
            log = Logs(well_id=well.id, project_id=self.project_id)
            db.session.add(log)
        well.depth = dept
        db.session.flush()
        for i in range(len(self.wells_from_files[w_name]["las"])):
            list_crv_keys = self.wells_from_files[w_name]["las"][i].keys()
            list_crv_keys.remove(self.wells_from_files[w_name]["MD_keys"][i])
            for crv_k in list_crv_keys:
                new_crv = self.new_mesh(
                    self.wells_from_files[w_name]["las"][i].curves[crv_k].data,
                    self.wells_from_files[w_name]["las"][i].curves[
                        self.wells_from_files[w_name]["MD_keys"][i]].data,
                    dept)
                mnem = str(self.wells_from_files[w_name]["las"][i].curves[
                               crv_k].mnemonic).split(".")[0].replace(" ", "")
                unit = self.wells_from_files[w_name]["las"][i].curves[
                    crv_k].unit
                crv_i = self.create_curve_obj(new_crv, mnem, unit,
                                              self.wells_from_files[w_name][
                                                  "path"][i], well)
                db.session.add(crv_i)
                # well.curves.append(crv_i)
        # db.session.add(well)
        return well

    def get_global_dept(self, w_name):

        use_well = Well.query.filter_by(name=w_name, project_id=self.project_id).first()
        if (use_well is None) or (use_well.depth is None):
            dept = np.round(np.arange(self.wells_from_files[w_name]["MD_min"],
                                      self.wells_from_files[w_name]["MD_max"],
                                      self.globalStep), 1)
            if len(dept) != 0:
                if abs(dept[-1] - round(self.wells_from_files[w_name]["MD_max"],
                                        1)) > 1e-3:
                    dept = np.hstack(
                        (dept, round(self.wells_from_files[w_name]["MD_max"], 1)))
            else:
                dept = [round(self.wells_from_files[w_name]["MD_max"],
                              1)]
        else:
            dpt_min_old = np.nanmin(use_well.depth)
            dpt_max_old = np.nanmax(use_well.depth)

            dpt_min_new = self.wells_from_files[w_name]["MD_min"]
            dpt_max_new = self.wells_from_files[w_name]["MD_max"]
            if dpt_min_old <= dpt_min_new and dpt_max_new <= dpt_max_old:
                dept = use_well.depth
            else:
                dept = use_well.depth
                if dpt_min_new < dpt_min_old:
                    left_dpt = np.round(np.arange(dpt_min_new, dept[0] - self.globalStep, self.globalStep), 1)
                    if len(left_dpt) != 0:
                        if abs(left_dpt[-1] - round(dept[0] - self.globalStep, 1)) > 1e-3:
                            left_dpt = np.hstack((left_dpt, round(dept[0] - self.globalStep, 1)))
                        left_dpt = list(left_dpt)
                    else:
                        left_dpt = [round(dept[0] - self.globalStep, 1)]
                    dept = left_dpt + dept
                else:
                    left_dpt = []
                if dpt_max_old < dpt_max_new:

                    right_dpt = np.round(np.arange(dept[-1] + self.globalStep, dpt_max_new, self.globalStep), 1)
                    if len(right_dpt) != 0:
                        if abs(right_dpt[-1] - round(dpt_max_new, 1)) > 1e-3:
                            right_dpt = np.hstack((right_dpt, round(dpt_max_new, 1)))
                        right_dpt = list(right_dpt)
                    else:
                        right_dpt = [round(dpt_max_new, 1)]
                    dept = dept + right_dpt
                else:
                    right_dpt = []

                ### заменить имеющийся dept на Расширенный
                use_well.depth = dept
                list_crvs = list(Curve.query.filter_by(well_id=use_well.id).all())
                for crv in list_crvs:
                    left_crv = list(np.ones(len(left_dpt)) * np.nan)
                    right_crv = list(np.ones(len(right_dpt)) * np.nan)

                    crv.data = left_crv + crv.data + right_crv

                db.session.commit()
        return dept

    def check_las_files(self):
        incorrect_files = []
        file_names = []
        for path in self.file_paths:
            if os.path.isfile(path) and path.lower().endswith('las'):
                file_names.append(path)
            else:
                incorrect_files.append(path)

        return file_names, incorrect_files

    def start_las_reader(self, file_names):
        for file_name in file_names:
            self._well_from_las_file(file_name)
        self._prepare_data_from_files()

    def _well_from_las_file(self, file_name):
        """Получение из файла fileInfo данных для отображения на форме ImportForm"""

        if os.path.exists(file_name):
            try:
                new_file, encoding, is_new_file = self.check_and_fix_las(file_name)
                las = lasio.read(new_file, encoding=encoding)

                # Название скважины
                well_name = str(las.well['WELL'].value).replace(" ", "")
                well_name = well_name.replace(",", "")
                well_name = well_name.replace(".", "")
                well_name = re.sub(r"[,.|/*:?\"\'\\<>]", "", well_name)
                well_name = well_name_re(well_name)
                if well_name == "":
                    if self.unnamed_well:
                        well_name = file_name.split('.las')[0].split("_file_")[1].replace(" ", "")
                        well_name = well_name_re(well_name)
                    else:
                        well_name = "000"


                this_md_key = None
                for md_k in las.keys():
                    if str(md_k).lower() in self.md_keys:
                        this_md_key = md_k
                        break

                if this_md_key is None:
                    print(str(
                        file_name) + " : Ошибка загрузки файла *.las : Не найдена информация по относительной глубине ")
                    return None
                elif len(las.curves[this_md_key].data) < 2:
                    print(str(
                        file_name) + " : Ошибка загрузки файла *.las : Недостаточно данных ")
                    try:
                        os.remove(file_name.split(".las")[0] + "(copy)" + ".las")
                    except:
                        pass
                    return None

                if not this_md_key is None:
                    if well_name in self.wells_from_files.keys():

                        self.wells_from_files[well_name]["las"].append(las)
                        self.wells_from_files[well_name]["path"].append(
                            file_name)
                        self.wells_from_files[well_name]["MD_keys"].append(
                            this_md_key)
                        this_md_min = np.nanmin(las.curves[this_md_key].data)
                        this_md_max = np.nanmax(las.curves[this_md_key].data)
                        if this_md_min < self.wells_from_files[well_name][
                            "MD_min"]:
                            self.wells_from_files[well_name][
                                "MD_min"] = this_md_min
                        if this_md_max > self.wells_from_files[well_name][
                            "MD_max"]:
                            self.wells_from_files[well_name][
                                "MD_max"] = this_md_max

                    else:
                        self.wells_from_files.update({well_name: {
                            "las": [las],
                            "path": [file_name],
                            "MD_keys": [this_md_key],
                            "MD_min": np.nanmin(las.curves[this_md_key].data),
                            "MD_max": np.nanmax(las.curves[this_md_key].data)
                        }
                        })
                else:
                    print("Не найдена информация по относительной глубине.",
                          file_name)

                if is_new_file:
                    os.remove(new_file)
            except BaseException as e:
                print(str(
                    file_name) + " : Ошибка загрузки файла *.las : " + str(
                    e))

    def _prepare_data_from_files(self):
        """Получение из файлов filePaths данных для отображения на форме ImportForm"""

        # Группируем выбранные .las файлы по скважинам. Файлы без информации по имени скважины, собираются под ключом empty_well


        # Если есть файл(ы) без имени скважины
        # if "empty_well" in self.wells_from_files.keys():
        #     retval = show_message_box_yesno(
        #         'В файлах содержатся скважины с пустыми названиями, хотите присвоить им названия датасетов?')
        #     if retval == QMessageBox.Yes:
        #         # Присваиваем названиям пустых скважин названия файлов из котрых мы их считали
        #         loc_wells = self.add_NoName_wells(loc_wells)
        #     else:
        #         # Создаем новую скважину, которая будет содержать в себе все кривые пустых скважин
        #         wname = "empty_well"
        #         dept = self.get_global_dept(wname)
        #         well = self.create_well_obj(wname, dept)
        #         loc_wells.update({wname: well})
        #         del dept
        #         del well

        wells = list(self.wells_info_struct())

        del self.wells_from_files

        self.wells = wells
