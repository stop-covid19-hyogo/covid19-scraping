# -*- coding: utf-8 -*-
import re

from datetime import datetime, timedelta

from typing import Dict

from util import excel_date, get_file, get_weekday, dumps_json, jst, print_log
from summary import MainSummary


class Patients:
    def __init__(self):
        self.sheets = get_file("/kk03/corona_kanjyajyokyo.html", "xlsx", True)["公表"]
        self.patients_count = 5
        self.clusters_count = 11
        self.clusters = []
        self._patients_json = {}
        self._patients_summary_json = {}
        self._clusters_json = {}
        self._clusters_summary_json = {}
        self._age_summary_json = {}
        self.get_patients()
        self.get_clusters()

    def patients_json(self) -> Dict:
        if not self._patients_json:
            self.make_patients()
        return self._patients_json

    def patients_summary_json(self) -> Dict:
        if not self._patients_summary_json:
            self.make_patients_summary()
        return self._patients_summary_json

    def clusters_json(self) -> Dict:
        if not self._clusters_json:
            self.make_clusters()
        return self._clusters_json

    def clusters_summary_json(self) -> Dict:
        if not self._clusters_summary_json:
            self.make_clusters_summary()
        return self._clusters_summary_json

    def age_summary_json(self) -> Dict:
        if not self._age_summary_json:
            self.make_age_summary()
        return self._age_summary_json

    def make_patients(self) -> None:
        self._patients_json = {
            "data": [],
            "last_update": self.get_last_update()
        }
        for i in range(5, self.patients_count):
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

    def make_patients_summary(self) -> None:
        def make_data(date):
            data = {}
            data["日付"] = date
            data["小計"] = 1
            return data

        self._patients_summary_json = {
            "data": [],
            "last_update": self.get_last_update()
        }

        prev_data = {}
        for patients_data in self.patients_json()["data"]:
            date = patients_data["リリース日"]
            if prev_data:
                prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
                patients_zero_days = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+09:00") - prev_date).days
                if prev_data["日付"] == date:
                    prev_data["小計"] += 1
                    continue
                else:
                    self._patients_summary_json["data"].append(prev_data)
                    if patients_zero_days >= 2:
                        for i in range(1, patients_zero_days):
                            self._patients_summary_json["data"].append(
                                {
                                    "日付": (prev_date + timedelta(days=i)).astimezone(jst).isoformat(),
                                    "小計": 0
                                }
                            )
            prev_data = make_data(date)
        self._patients_summary_json["data"].append(prev_data)

    def make_clusters(self) -> None:
        self._clusters_json = {
            "data": [],
            "last_update": self.get_last_update()
        }

        cell_num = 4
        for patients in reversed(self.patients_summary_json()["data"]):
            data = {}
            data["日付"] = patients["日付"]
            for cluster in self.clusters:
                data[cluster] = 0
            for i in range(patients["小計"]):
                cell_num += 1
                for j in range(12, self.clusters_count + 1):
                    if self.sheets.cell(row=cell_num, column=j).value == "〇":
                        data[self.clusters[j-12]] += 1
                        break
                    if j == self.clusters_count:
                        data["不明"] += 1
                        break
            self._clusters_json["data"].append(data)
        self._clusters_json["data"].reverse()

    def make_clusters_summary(self) -> None:
        self._clusters_summary_json = {
            "data": {},
            "labels": [],
            "last_update": self.get_last_update()
        }
        for cluster in self.clusters:
            self._clusters_summary_json["data"][cluster] = []
        for clusters_data in self.clusters_json()["data"]:
            date = datetime.strptime(clusters_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
            for i in range(len(self.clusters)):
                self._clusters_summary_json["data"][self.clusters[i]].append(clusters_data[self.clusters[i]])
            self._clusters_summary_json["labels"].append(date.strftime("%m/%d"))

    def make_age_summary(self) -> None:
        self._age_summary_json = {
            "data": {},
            "labels": [],
            "last_update": self.get_last_update()
        }

        data_num = 0
        for i in range(10):
            suffix = "代"
            if i == 0:
                i = 1
                suffix += "未満"
            elif i == 9:
                suffix += "以上"
            self._age_summary_json["data"][str(i*10) + suffix] = []

        for patients in self.patients_summary_json()["data"]:
            date = datetime.strptime(patients["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
            day_age = {}
            for i in range(10):
                day_age[str(i*10)] = 0
            for i in range(patients["小計"]):
                age = int(self.patients_json()["data"][data_num]["年代"][:-1])
                if age >= 90:
                    age = 90
                day_age[str(age)] += 1
                data_num += 1

            for i in range(10):
                j = i
                suffix = "代"
                if i == 0:
                    i = 1
                    suffix += "未満"
                elif i == 9:
                    suffix += "以上"
                self._age_summary_json["data"][str(i*10) + suffix].append(day_age[str(j*10)])
            self._age_summary_json["labels"].append(date.strftime("%m/%d"))

    def get_last_update(self) -> str:
        column_num = 16
        data_time_str = ""
        while not data_time_str:
            if not self.sheets.cell(row=3, column=column_num).value:
                column_num += 1
                continue
            data_time_str = str(self.sheets.cell(row=3, column=column_num).value).replace("\u3000", " ")
        if data_time_str[-5:] == "24時現在":
            day_str, hour_str = data_time_str[-8:].split()
            day_int = int(day_str)
            data_time_str = data_time_str[:-8] + str(day_int + 1) + " 0時現在"
        return datetime.strptime(
            "2020/" + data_time_str, "%Y/%m/%d %H時現在"
        ).strftime("%Y/%m/%d %H:%M")

    def get_patients(self) -> None:
        while self.sheets:
            self.patients_count += 1
            value = self.sheets.cell(row=self.patients_count, column=2).value
            if not value:
                break

    def get_clusters(self) -> None:
        while self.sheets:
            self.clusters_count += 1
            value = self.sheets.cell(row=4, column=self.clusters_count).value
            if not value:
                break
            self.clusters.append(str(value).replace("\n", ""))
        self.clusters.append("不明")


class Inspections:
    def __init__(self):
        self.sheets = get_file("/kf16/singatakoronakensa.html", "xlsx", True)["Sheet1"]
        self.inspections_count = 2
        self._inspections_json = {}
        self._inspections_summary_json = {}
        self.get_inspections()

    def inspections_json(self) -> Dict:
        if not self._inspections_json:
            self.make_inspections()
        return self._inspections_json

    def inspection_summary_json(self) -> Dict:
        if not self._inspections_summary_json:
            self.make_inspections()
            self.make_inspections_summary()
        return self._inspections_summary_json

    def make_inspections(self) -> None:
        self._inspections_json = {
            "data": [],
            "last_update": self.get_last_update()
        }
        for i in range(2, self.inspections_count):
            date = self.sheets.cell(row=i, column=1).value
            data = {}
            data["判明日"] = date.strftime("%d/%m/%Y")
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
            date = datetime.strptime(inspections_data["判明日"], "%d/%m/%Y")
            self._inspections_summary_json["data"]["検査検体数"].append(inspections_data["検査検体数"])
            self._inspections_summary_json["data"]["陽性確認"].append(inspections_data["陽性確認"])
            self._inspections_summary_json["labels"].append(date.strftime("%m/%d"))

    def get_last_update(self) -> str:
        data_time = self.sheets.cell(row=self.inspections_count-1, column=1).value + timedelta(days=1)
        return data_time.strftime("%Y/%m/%d %H:%M")

    def get_inspections(self) -> None:
        while self.sheets:
            self.inspections_count += 1
            value = self.sheets.cell(row=self.inspections_count, column=1).value
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
    dumps_json("patients_summary.json", patients.patients_summary_json())
    print_log("main", "make clusters.json...")
    dumps_json("clusters.json", patients.clusters_json())
    print_log("main", "make clusters_summary.json...")
    dumps_json("clusters_summary.json", patients.clusters_summary_json())
    print_log("main", "make age_summary.json...")
    dumps_json("age_summary.json", patients.age_summary_json())
    print_log("main", "make inspection.json...")
    dumps_json("inspections.json", inspections.inspections_json())
    print_log("main", "make inspection_summary.json...")
    dumps_json("inspections_summary.json", inspections.inspection_summary_json())
    print_log("main", "make main_summary.json...")
    dumps_json("main_summary.json", main_summary.get_summary_json())
    print_log("main", "make last_update.json...")
    dumps_json("last_update.json", {"last_update": str(datetime.today().astimezone(jst).strftime("%Y/%m/%d %H:%M"))})
    print_log("main", "make files complete!")
