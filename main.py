# -*- coding: utf-8 -*-
import re
import jaconv

from datetime import datetime, timedelta

from typing import Dict, List

from util import SUMMARY_INIT, excel_date, get_file, requests_file, get_weekday, dumps_json, jst, print_log

patients_first_cell = 6
clusters_first_cell = 11
inspections_first_cell = 2
main_summary_first_cell = 2


class Patients:
    def __init__(self):
        self.sheets = get_file("/kk03/corona_kanjyajyokyo.html", "xlsx", True)["公表"]
        self.patients_count = patients_first_cell
        self.clusters_count = clusters_first_cell
        self.clusters = []
        self._patients_json = {}
        # self._patients_summary_json = {}
        self._clusters_json = {}
        self._clusters_summary_json = {}
        self._age_json = {}
        self._age_summary_json = {}
        self.get_patients()
        self.get_clusters()

    def patients_json(self) -> Dict:
        if not self._patients_json:
            self.make_patients()
        return self._patients_json

    # def patients_summary_json(self) -> Dict:
    #     if not self._patients_summary_json:
    #         self.make_patients_summary()
    #     return self._patients_summary_json

    def clusters_json(self) -> Dict:
        if not self._clusters_json:
            self.make_clusters()
        return self._clusters_json

    def clusters_summary_json(self) -> Dict:
        if not self._clusters_summary_json:
            self.make_clusters_summary()
        return self._clusters_summary_json

    def age_json(self) -> Dict:
        if not self._age_json:
            self.make_age()
        return self._age_json

    def age_summary_json(self) -> Dict:
        if not self._age_summary_json:
            self.make_age_summary()
        return self._age_summary_json

    def make_patients(self) -> None:
        self._patients_json = {
            "data": [],
            "last_update": self.get_last_update()
        }
        for i in range(patients_first_cell, self.patients_count):
            data = {}
            release_date = excel_date(self.sheets.cell(row=i, column=3).value)
            data["No"] = self.sheets.cell(row=i, column=2).value
            data["リリース日"] = release_date.isoformat()
            data["曜日"] = get_weekday(release_date.weekday())
            data["居住地"] = self.sheets.cell(row=i, column=7).value
            data["年代"] = str(self.sheets.cell(row=i, column=4).value) + "代"
            data["性別"] = self.sheets.cell(row=i, column=5).value
            data["退院"] = None
            data["備考"] = re.sub('NO.|N0.|NO,|N0,|No,', 'No.', str(self.sheets.cell(row=i, column=11).value)).replace("・", "、")
            data["date"] = release_date.strftime("%Y-%m-%d")
            self._patients_json["data"].append(data)

        self._patients_json["data"].reverse()

    # def make_patients_summary(self) -> None:
    #     def make_data(date, value=1):
    #         data = {"日付": date, "小計": value}
    #         return data

    #     self._patients_summary_json = {
    #         "data": [],
    #         "last_update": self.get_last_update()
    #     }

    #     prev_data = {}
    #     for patients_data in sorted(self.patients_json()["data"], key=lambda x: x['date']):
    #         date = patients_data["リリース日"]
    #         if prev_data:
    #             prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
    #             patients_zero_days = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+09:00") - prev_date).days
    #             if prev_data["日付"] == date:
    #                 prev_data["小計"] += 1
    #                 continue
    #             else:
    #                 self._patients_summary_json["data"].append(prev_data)
    #                 if patients_zero_days >= 2:
    #                     for i in range(1, patients_zero_days):
    #                         self._patients_summary_json["data"].append(
    #                             make_data((prev_date + timedelta(days=i)).replace(tzinfo=jst).isoformat(), 0)
    #                         )
    #         prev_data = make_data(date)
    #     self._patients_summary_json["data"].append(prev_data)
    #     prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
    #     patients_zero_days = (datetime.now() - prev_date).days
    #     for i in range(1, patients_zero_days):
    #         self._patients_summary_json["data"].append(
    #             make_data((prev_date + timedelta(days=i)).replace(tzinfo=jst).isoformat(), 0)
    #         )

    def make_clusters(self) -> None:
        def make_data(date):
            data = {"日付": date}
            for cluster in self.clusters:
                data[cluster] = 0
            data.pop("None")
            return data

        self._clusters_json = {
            "data": [],
            "last_update": self.get_last_update()
        }

        patients_cluster_data = []
        for i in range(patients_first_cell, self.patients_count):
            cluster_data = {}
            for cluster in self.clusters:
                cluster_data[cluster] = False
            cluster_data.pop("None")
            for j in range(12, self.clusters_count + 1):
                if self.sheets.cell(row=i, column=j).value:
                    cluster_data[self.clusters[j - 12]] = True
            cluster_data["date"] = excel_date(self.sheets.cell(row=i, column=3).value).replace(tzinfo=jst).isoformat()
            patients_cluster_data.append(cluster_data)
        patients_cluster_data.sort(key=lambda x: x['date'])

        prev_data = {}
        for patient in patients_cluster_data:
            date = patient["date"]
            if prev_data:
                prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
                patients_zero_days = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+09:00") - prev_date).days
                if prev_data["日付"] == date:
                    for j in range(12, self.clusters_count):
                        if self.clusters[j - 12] == "None":
                            continue
                        if patient[self.clusters[j - 12]]:
                            prev_data[self.clusters[j - 12]] += 1
                    continue
                else:
                    self._clusters_json["data"].append(prev_data)
                    if patients_zero_days >= 2:
                        for i in range(1, patients_zero_days):
                            self._clusters_json["data"].append(
                                make_data((prev_date + timedelta(days=i)).replace(tzinfo=jst).isoformat())
                            )
            prev_data = make_data(date)
            for j in range(12, self.clusters_count):
                if self.clusters[j - 12] == "None":
                    continue
                if patient[self.clusters[j - 12]]:
                    prev_data[self.clusters[j - 12]] += 1

        self._clusters_json["data"].append(prev_data)
        prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
        patients_zero_days = (datetime.now() - prev_date).days - 1
        for i in range(1, patients_zero_days):
            self._clusters_json["data"].append(
                make_data((prev_date + timedelta(days=i)).replace(tzinfo=jst).isoformat())
            )

    def make_clusters_summary(self) -> None:
        self._clusters_summary_json = {
            "data": {},
            "last_update": self.get_last_update()
        }
        for cluster in self.clusters:
            self._clusters_summary_json["data"][cluster] = 0
        for clusters_data in self.clusters_json()["data"]:
            for i in range(len(self.clusters)):
                cluster_name = self.clusters[i]
                if cluster_name == "None":
                    continue
                self._clusters_summary_json["data"][cluster_name] += clusters_data[cluster_name]
        self._clusters_summary_json["data"].pop("None")

    def make_age(self) -> None:
        self._age_json = {
            "data": {},
            "last_update": self.get_last_update()
        }

        for patients in self.age_summary_json()["data"].keys():
            total = 0
            for count in self.age_summary_json()["data"][patients]:
                total += count
            self._age_json["data"][patients] = total
        self._age_json["last_update"] = self.age_summary_json()["last_update"]

    def make_age_summary(self) -> None:
        def make_data(date):
            data = {"date": date}
            for i in range(10):
                data[str(i*10)] = 0
            return data

        self._age_summary_json = {
            "data": {},
            "labels": [],
            "last_update": self.get_last_update()
        }

        for i in range(10):
            suffix = "代"
            if i == 0:
                i = 1
                suffix += "未満"
            elif i == 9:
                suffix += "以上"
            self._age_summary_json["data"][str(i*10) + suffix] = []

        patients_age_data = []
        for i in range(patients_first_cell, self.patients_count):
            age_data = {
                "年代": self.sheets.cell(row=i, column=4).value,
                "date": excel_date(self.sheets.cell(row=i, column=3).value).replace(tzinfo=jst).isoformat()
            }
            patients_age_data.append(age_data)
        patients_age_data.sort(key=lambda x: x['date'])

        prev_data = {}
        for patient in patients_age_data:
            date = patient["date"]
            if prev_data:
                prev_date = datetime.strptime(prev_data["date"], "%Y-%m-%dT%H:%M:%S+09:00")
                patients_zero_days = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+09:00") - prev_date).days
                if prev_data["date"] == date:
                    data = self.pop_age_value()
                    data[str(patient["年代"])] += 1
                    self.insert_age_value(data)
                    continue
                else:
                    if patients_zero_days >= 2:
                        for i in range(1, patients_zero_days):
                            self.insert_age_value(
                                make_data((prev_date + timedelta(days=i)).replace(tzinfo=jst).isoformat())
                            )
                            self._age_summary_json["labels"].append(
                                (prev_date + timedelta(days=i)).replace(tzinfo=jst).strftime("%m/%d")
                            )

            data = make_data(date)
            data[str(patient["年代"])] += 1
            self.insert_age_value(data)
            prev_data = patient
            self._age_summary_json["labels"].append(
                datetime.strptime(prev_data["date"], "%Y-%m-%dT%H:%M:%S+09:00").strftime("%m/%d")
            )

    def insert_age_value(self, day_age: Dict) -> None:
        for i in range(10):
            j = i
            suffix = "代"
            if i == 0:
                i = 1
                suffix += "未満"
            elif i == 9:
                suffix += "以上"
            self._age_summary_json["data"][str(i * 10) + suffix].append(day_age[str(j * 10)])

    def pop_age_value(self) -> Dict:
        result = {}
        for i in range(10):
            j = i
            suffix = "代"
            if i == 0:
                i = 1
                suffix += "未満"
            elif i == 9:
                suffix += "以上"
            result[str(j * 10)] = self._age_summary_json["data"][str(i * 10) + suffix].pop()
        return result

    def get_last_update(self) -> str:
        column_num = 16
        data_time_str = ""
        while not data_time_str:
            if not self.sheets.cell(row=3, column=column_num).value:
                column_num += 1
                continue
            data_time_str = jaconv.z2h(str(self.sheets.cell(row=3, column=column_num).value), digit=True, ascii=True)
        plus_day = 0
        if data_time_str[-5:] == "24時現在":
            count = 8
            while True:
                try:
                    day_str, hour_str = data_time_str[-count:].split()
                    if day_str.startswith("/"):
                        raise
                    break
                except Exception:
                    count -= 1
            data_time_str = data_time_str[:-count] + day_str + " 0時現在"
            plus_day = 1
        last_update = datetime.strptime("2020/" + data_time_str, "%Y/%m/%d %H時現在") + timedelta(days=plus_day)
        return last_update.replace(tzinfo=jst).isoformat()

    def get_patients(self) -> None:
        while self.sheets:
            self.patients_count += 1
            value = self.sheets.cell(row=self.patients_count, column=2).value
            if not value:
                break

    def get_clusters(self) -> None:
        none_count = 0
        under_cell_count = 1
        while self.sheets:
            self.clusters_count += 1
            over_cell = self.sheets.cell(row=4, column=self.clusters_count).value
            under_cell = self.sheets.cell(row=5, column=self.clusters_count).value
            if not over_cell:
                if none_count:
                    if under_cell:
                        under_cell_count += 1
                        self.clusters.append(str(under_cell).replace("\n", ""))
                        continue
                    break
                none_count += 1

            self.clusters.append(str(over_cell).replace("\n", ""))
        self.clusters[-under_cell_count] = "None"


class Inspections:
    def __init__(self):
        self.sheets = requests_file("https://web.pref.hyogo.lg.jp/kk03/documents/pcr.xlsx", "xlsx", True)["Sheet1"]
        self.inspections_count = inspections_first_cell
        self._inspections_json = {}
        self._inspections_summary_json = {}
        self._patients_summary_json = {}
        self.get_inspections()

    def inspections_json(self) -> Dict:
        if not self._inspections_json:
            self.make_inspections()
        return self._inspections_json

    def inspection_summary_json(self) -> Dict:
        if not self._inspections_summary_json:
            self.make_inspections_summary()
        return self._inspections_summary_json

    def patients_summary_json(self) -> Dict:
        if not self._patients_summary_json:
            self.make_patients_summary()
        return self._patients_summary_json

    def make_inspections(self) -> None:
        self._inspections_json = {
            "data": [],
            "last_update": self.get_last_update()
        }
        for i in range(inspections_first_cell, self.inspections_count):
            date = self.sheets.cell(row=i, column=1).value
            data = {"判明日": date.strftime("%Y-%m-%d")}
            pcr = self.sheets.cell(row=i, column=2).value
            data["検査検体数"] = pcr if pcr else 0
            data["陽性確認"] = self.sheets.cell(row=i, column=3).value
            self._inspections_json["data"].append(data)

    def make_inspections_summary(self) -> None:
        self._inspections_summary_json = {
            "data": {
                "検査検体数": [],
                "陽性確認": []
            },
            "labels": [],
            "last_update": self.get_last_update()
        }
        for inspections_data in self.inspections_json()["data"]:
            date = datetime.strptime(inspections_data["判明日"], "%Y-%m-%d")
            self._inspections_summary_json["data"]["検査検体数"].append(inspections_data["検査検体数"])
            self._inspections_summary_json["data"]["陽性確認"].append(inspections_data["陽性確認"])
            self._inspections_summary_json["labels"].append(date.strftime("%m/%d"))

    def make_patients_summary(self) -> None:
        self._patients_summary_json = {
            "data": [],
            "last_update": self.get_last_update()
        }
        for inspections_data in self.inspections_json()["data"]:
            date = datetime.strptime(inspections_data["判明日"], "%Y-%m-%d")
            data = {
                "日付": date.replace(tzinfo=jst).isoformat(),
                "小計": inspections_data["陽性確認"]
            }
            self._patients_summary_json["data"].append(data)

    def get_last_update(self) -> str:
        data_time = self.sheets.cell(row=self.inspections_count-1, column=1).value + timedelta(days=1)
        return data_time.replace(tzinfo=jst).isoformat()

    def get_inspections(self) -> None:
        while self.sheets:
            self.inspections_count += 1
            value = self.sheets.cell(row=self.inspections_count, column=1).value
            if not value:
                break


class MainSummary:
    def __init__(self):
        # self.pdf_texts = get_file('/kk03/corona_hasseijyokyo.html', "pdf")
        self.sheets = requests_file("https://web.pref.hyogo.lg.jp/kk03/documents/yousei.xlsx", "xlsx", True)["yousei"]
        self.sickbeds_count = 246
        self.values = []
        self.data_count = main_summary_first_cell
        self._main_summary_json = {}
        self._sickbeds_summary_json = {}
        self.get_data_count()

    def main_summary_json(self) -> Dict:
        if not self._main_summary_json:
            self.make_main_summary()
        return self._main_summary_json

    def sickbeds_summary_json(self) -> Dict:
        if not self._sickbeds_summary_json:
            self.make_sickbeds_summary()
        return self._sickbeds_summary_json

    def make_main_summary(self) -> None:
        self._main_summary_json = SUMMARY_INIT
        self._main_summary_json['last_update'] = self.get_last_update()

        # pdf mode is disabled...
        # content = ''.join(self.pdf_texts[3:])
        # self.values = get_numbers_in_text(content)
        self.values = self.get_values()
        self.set_summary_values(self._main_summary_json)

    def make_sickbeds_summary(self) -> None:
        # pdf mode is disabled...
        # content = ''.join(self.pdf_texts[3:])
        # self.values = get_numbers_in_text(content)
        self.values = self.get_values()
        self._sickbeds_summary_json = {
            "data": {
                "入院患者数": self.values[2],
                "残り病床数": self.sickbeds_count - self.values[2]
            },
            "last_update": self.get_last_update()
        }

    def get_values(self) -> List:
        values = []
        for i in range(3, 10):
            values.append(self.sheets.cell(row=self.data_count - 1, column=i).value)
        return values

    def set_summary_values(self, obj) -> None:
        obj['value'] = self.values[0]
        if isinstance(obj, dict) and obj.get('children'):
            for child in obj['children']:
                self.values = self.values[1:]
                self.set_summary_values(child)

    def get_last_update(self) -> str:
        # pdf mode is disabled...
        # caption = self.pdf_texts[0]
        # dt_vals = get_numbers_in_text(caption)
        # last_update = datetime(datetime.now().year, dt_vals[0], dt_vals[1]) + timedelta(hours=dt_vals[2])
        # return datetime.strftime(last_update, '%Y/%m/%d %H:%M')
        return (
                self.sheets.cell(row=self.data_count - 1, column=1).value +
                timedelta(hours=int(self.sheets.cell(row=self.data_count - 1, column=2).value[:-1]))
        ).replace(tzinfo=jst).isoformat()

    def get_data_count(self) -> None:
        while self.sheets:
            self.data_count += 1
            value = self.sheets.cell(row=self.data_count, column=1).value
            if not value:
                break


if __name__ == '__main__':
    print_log("main", "Init classes")
    patients = Patients()
    inspections = Inspections()
    main_summary = MainSummary()
    print_log("main", "make patients.json...")
    dumps_json("patients.json", patients.patients_json())
    print_log("main", "make patients_summary.json...")
    # assert inspections.patients_summary_json() == patients.patients_summary_json()
    dumps_json("patients_summary.json", inspections.patients_summary_json())
    print_log("main", "make clusters.json...")
    dumps_json("clusters.json", patients.clusters_json())
    print_log("main", "make clusters_summary.json...")
    dumps_json("clusters_summary.json", patients.clusters_summary_json())
    print_log("main", "make age.json...")
    dumps_json("age.json", patients.age_json())
    print_log("main", "make age_summary.json...")
    dumps_json("age_summary.json", patients.age_summary_json())
    print_log("main", "make inspection.json...")
    dumps_json("inspections.json", inspections.inspections_json())
    print_log("main", "make inspection_summary.json...")
    dumps_json("inspections_summary.json", inspections.inspection_summary_json())
    print_log("main", "make main_summary.json...")
    dumps_json("main_summary.json", main_summary.main_summary_json())
    print_log("main", "make sickbed_summary.json...")
    dumps_json("sickbeds_summary.json", main_summary.sickbeds_summary_json())
    print_log("main", "make last_update.json...")
    dumps_json("last_update.json", {
        "last_update": datetime.now().astimezone(jst).strftime("%Y-%m-%dT%H:%M:00+09:00")
    })
    print_log("main", "make files complete!")
