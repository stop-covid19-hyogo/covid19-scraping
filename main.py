# -*- coding: utf-8 -*-
import re
import jaconv
import inspect

from datetime import datetime, timedelta

from typing import Dict, List

from util import SUMMARY_INIT, excel_date, get_file, requests_file, get_weekday, dumps_json, jst, print_log

patients_first_cell = 6
clusters_first_cell = 11
inspections_first_cell = 2
main_summary_first_cell = 2


class DataManager:
    def __init__(self):
        # データファイルの取得 この時点で取得しておくと、取得失敗時にこの時点で処理を終了させられるため
        self.patients_sheet = get_file("/kk03/corona_kanjyajyokyo.html", "xlsx", True)["公表"]
        self.inspections_sheet = requests_file("/kk03/documents/pcr.xlsx", "xlsx", True)["Sheet1"]
        # self.pdf_texts = get_file('/kk03/corona_hasseijyokyo.html', "pdf")
        self.summary_sheet = requests_file("/kk03/documents/yousei.xlsx", "xlsx", True)["yousei"]
        # データ量(行数)を調べ始める最初の行の指定
        self.patients_count = patients_first_cell
        self.clusters_count = clusters_first_cell
        self.inspections_count = inspections_first_cell
        self.data_count = main_summary_first_cell
        # クラスター一覧を収納するリスト
        self.clusters = []
        # 総病床数 TODO:適宜手動更新が必要なので自動化が望まれる
        self.sickbeds_count = 246
        # 検査数や入院者数などを格納するリスト
        self.summary_values = []
        # 以下、内部変数
        self._patients_json = {}
        self._patients_summary_json = {}
        self._clusters_json = {}
        self._clusters_summary_json = {}
        self._age_json = {}
        self._age_summary_json = {}
        self._inspections_json = {}
        self._inspections_summary_json = {}
        self._main_summary_json = {}
        self._sickbeds_summary_json = {}
        # 初期化(最大行数の取得)
        self.get_patients()
        self.get_clusters()
        self.get_inspections()
        self.get_data_count()

    def json_template_of_patients(self) -> Dict:
        # patients_sheetを用いるデータ向けのテンプレート
        return {
            "data": [],
            "last_update": self.get_patients_last_update()
        }

    def json_template_of_inspections(self) -> Dict:
        # patients_sheetを用いるデータ向けのテンプレート
        return {
            "data": [],
            "last_update": self.get_inspections_last_update()
        }

    def dump_all_data(self) -> None:
        # xxx_json の名を持つ関数のリストを生成(_で始まる内部変数は除外する)
        json_list = [
            member[0] for member in inspect.getmembers(self) if member[0][-4:] == "json" and member[0][0] != "_"
        ]
        for json in json_list:
            # 関数は"_json"で終わっているので、それを拡張子に直す必要がある
            json_name = json[:-5] + ".json"
            print_log("data_manager", f"Make {json_name}...")
            # jsonを出力、evalで文字列から関数を呼び出している
            dumps_json(json_name, eval("self." + json + "()"))

    # 以下、内部変数を読み取って空ならデータを作成し返す仕組み
    # 直接内部変数を用いるのは、"make_xxx"などでデータを編集するときのみ
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

    def age_json(self) -> Dict:
        if not self._age_json:
            self.make_age()
        return self._age_json

    def age_summary_json(self) -> Dict:
        if not self._age_summary_json:
            self.make_age_summary()
        return self._age_summary_json

    def inspections_json(self) -> Dict:
        if not self._inspections_json:
            self.make_inspections()
        return self._inspections_json

    def inspections_summary_json(self) -> Dict:
        if not self._inspections_summary_json:
            self.make_inspections_summary()
        return self._inspections_summary_json

    def main_summary_json(self) -> Dict:
        if not self._main_summary_json:
            self.make_main_summary()
        return self._main_summary_json

    def sickbeds_summary_json(self) -> Dict:
        if not self._sickbeds_summary_json:
            self.make_sickbeds_summary()
        return self._sickbeds_summary_json

    def make_patients(self) -> None:
        # patients.jsonのデータを作成する
        self._patients_json = self.json_template_of_patients()

        # patients_sheetからデータを読み取っていく
        for i in range(patients_first_cell, self.patients_count):
            data = {}
            release_date = excel_date(self.patients_sheet.cell(row=i, column=3).value)
            data["No"] = self.patients_sheet.cell(row=i, column=2).value
            data["リリース日"] = release_date.isoformat()
            data["曜日"] = get_weekday(release_date.weekday())
            data["居住地"] = self.patients_sheet.cell(row=i, column=7).value
            # sheetには年代は数字で乗っているので、現状はこのスタイルだが、まだ「10歳未満」の表記が不明なので、それが判明次第修正する形をとる
            # TODO: 10代未満の表記に関して
            data["年代"] = str(self.patients_sheet.cell(row=i, column=4).value) + "代"
            data["性別"] = self.patients_sheet.cell(row=i, column=5).value
            data["退院"] = None
            # No.の表記にブレが激しいので、ここで"No."に修正(統一)。また、"・"を"、"に置き換える
            data["備考"] = re.sub(
                'NO.|N0.|NO,|N0,|No,', 'No.', str(self.patients_sheet.cell(row=i, column=11).value)
            ).replace("・", "、")
            data["date"] = release_date.strftime("%Y-%m-%d")
            self._patients_json["data"].append(data)

        # No.1の人からリストに追加していくと、降順になるので、reverseで昇順に戻す
        self._patients_json["data"].reverse()

    # 以前、データが正常に生成されないことがあったので、inspections_sheetから生成するよう変更済み
    # 念のため、負の遺産として残してある
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

    def make_patients_summary(self) -> None:
        # patients_summary.jsonの作成
        self._patients_summary_json = self.json_template_of_inspections()

        for inspections_data in self.inspections_json()["data"]:
            date = datetime.strptime(inspections_data["判明日"], "%Y-%m-%d")
            data = {
                "日付": date.replace(tzinfo=jst).isoformat(),
                "小計": inspections_data["陽性確認"]
            }
            self._patients_summary_json["data"].append(data)

    def make_clusters(self) -> None:
        # 内部データテンプレート
        def make_data(date):
            data = {"日付": date}
            # クラスターリストからクラスターを取得し、辞書にはめ込んでいく
            for cluster in self.clusters:
                data[cluster] = 0
            # "None"のものは使われないのでpopで疑似的に削除
            data.pop("None")
            return data

        # clusters.jsonのデータを作成する
        self._clusters_json = self.json_template_of_patients()

        # Excelデータからクラスター一覧に〇がついているところをTrueとし、抜き出す
        patients_cluster_data = []
        for i in range(patients_first_cell, self.patients_count):
            # 初期化
            cluster_data = {}
            for cluster in self.clusters:
                cluster_data[cluster] = False
            # Noneの削除
            cluster_data.pop("None")
            for j in range(12, self.clusters_count):
                # クラスターの欄に〇があればTrueとする
                if self.patients_sheet.cell(row=i, column=j).value:
                    cluster_data[self.clusters[j - 12]] = True
            # 日時の反映
            cluster_data["date"] = excel_date(
                self.patients_sheet.cell(row=i, column=3).value
            ).replace(tzinfo=jst).isoformat()
            patients_cluster_data.append(cluster_data)
        # 患者ごとにデータが保管されるが、順番は関係なく、1日にどこで何人、というデータを抜き出すために、日付順でsortする
        patients_cluster_data.sort(key=lambda x: x['date'])

        # 以前のデータを保管する
        # これは、前の患者データと日付が同じであるか否かを比較するための変数
        prev_data = {}
        for patient in patients_cluster_data:
            date = patient["date"]
            if prev_data:
                prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
                # 前のデータと日付が離れている場合、その分0のデータを埋める必要があるので、そのために差を取得する
                patients_zero_days = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+09:00") - prev_date).days
                # 前のデータと日付が同じ場合、前のデータに人数を加算していく
                if prev_data["日付"] == date:
                    for j in range(clusters_first_cell + 1, self.clusters_count):
                        if self.clusters[j - clusters_first_cell - 1] == "None":
                            continue
                        # 以前抜き出したクラスター情報がTrueになっていれば、+1する
                        if patient[self.clusters[j - clusters_first_cell - 1]]:
                            prev_data[self.clusters[j - clusters_first_cell - 1]] += 1
                    # 加算し終えたら戻る
                    continue
                else:
                    # 前のデータと日付が離れていた場合、前のデータをjsonに登録する
                    self._clusters_json["data"].append(prev_data)
                    # 前のデータとの日付の差が2日以上の場合は空いている日にち分、0を埋める
                    if patients_zero_days >= 2:
                        for i in range(1, patients_zero_days):
                            self._clusters_json["data"].append(
                                make_data((prev_date + timedelta(days=i)).replace(tzinfo=jst).isoformat())
                            )
            # 新しいデータを作成し、前もって前のデータとして格納しておく
            prev_data = make_data(date)
            for j in range(clusters_first_cell + 1, self.clusters_count):
                if self.clusters[j - clusters_first_cell - 1] == "None":
                    continue
                # 以前抜き出したクラスター情報がTrueになっていれば、+1する
                if patient[self.clusters[j - clusters_first_cell - 1]]:
                    prev_data[self.clusters[j - clusters_first_cell - 1]] += 1

        # 前のデータをjsonに登録する
        self._clusters_json["data"].append(prev_data)
        prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S+09:00")
        # 最終更新のデータから日付が開いている場合、0で埋める
        patients_zero_days = (datetime.now(jst) - prev_date).days - 1
        for i in range(1, patients_zero_days):
            self._clusters_json["data"].append(
                make_data((prev_date + timedelta(days=i)).replace(tzinfo=jst).isoformat())
            )

    def make_clusters_summary(self) -> None:
        # clusters_summary.jsonのデータを作成する
        self._clusters_summary_json = self.json_template_of_patients()

        # 初期化
        for cluster in self.clusters:
            self._clusters_summary_json["data"][cluster] = 0
        # clusters.jsonを用いてデータを生成
        for clusters_data in self.clusters_json()["data"]:
            for i in range(len(self.clusters)):
                cluster_name = self.clusters[i]
                if cluster_name == "None":
                    continue
                self._clusters_summary_json["data"][cluster_name] += clusters_data[cluster_name]
        # Noneは削除
        self._clusters_summary_json["data"].pop("None")

    def make_age(self) -> None:
        # age.jsonのデータを作成する
        self._age_json = {
            "data": {},
            "last_update": self.get_patients_last_update()
        }

        # 初期化
        for i in range(10):
            suffix = "代"
            if i == 0:
                i = 1
                suffix += "未満"
            elif i == 9:
                suffix += "以上"
            self._age_json["data"][str(i * 10) + suffix] = 0

        for i in range(patients_first_cell, self.patients_count):
            age = self.patients_sheet.cell(row=i, column=4).value
            suffix = "代"
            # TODO: 10歳未満の表記がわからないので保留
            if age == 0:
                age = 10
                suffix += "未満"
            elif age >= 90:
                suffix += "以上"
            self._age_json["data"][str(age) + suffix] += 1

    def make_age_summary(self) -> None:
        # 内部データテンプレート
        def make_data():
            data = {}
            for i in range(10):
                data[str(i*10)] = 0
            return data

        # age_summary.jsonを作成する
        self._age_summary_json = {
            "data": {},
            "labels": [],
            "last_update": self.get_patients_last_update()
        }

        # 初期化
        for i in range(10):
            suffix = "代"
            if i == 0:
                i = 1
                suffix += "未満"
            elif i == 9:
                suffix += "以上"
            self._age_summary_json["data"][str(i*10) + suffix] = []

        # 以前のデータを保管する
        # これは、前の患者データと日付が同じであるか否かを比較するための変数
        patients_age_data = []
        for i in range(patients_first_cell, self.patients_count):
            age_data = {
                "年代": self.patients_sheet.cell(row=i, column=4).value,
                "date": excel_date(self.patients_sheet.cell(row=i, column=3).value).replace(tzinfo=jst).isoformat()
            }
            patients_age_data.append(age_data)
        patients_age_data.sort(key=lambda x: x['date'])

        prev_data = {}
        for patient in patients_age_data:
            date = patient["date"]
            if prev_data:
                prev_date = datetime.strptime(prev_data["date"], "%Y-%m-%dT%H:%M:%S+09:00")
                # 前のデータと日付が離れている場合、その分0のデータを埋める必要があるので、そのために差を取得する
                patients_zero_days = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%S+09:00") - prev_date).days
                # 前のデータと日付が同じ場合、前のデータに人数を加算していく
                if prev_data["date"] == date:
                    # 接尾語は扱いづらいので、数字だけに置き換えた辞書で代用している
                    # popで10代未満や90代以上などの扱いづらいデータを全部0～90に置き換えたものを取り出し、
                    # その後取り出したものに加算し、insertで置き換え直して代入する
                    data = self.pop_age_value()
                    data[str(patient["年代"])] += 1
                    self.insert_age_value(data)
                    continue
                else:
                    # 前のデータとの日付の差が2日以上の場合は空いている日にち分、0を埋める
                    if patients_zero_days >= 2:
                        for i in range(1, patients_zero_days):
                            self.insert_age_value(make_data())
                            self._age_summary_json["labels"].append(
                                (prev_date + timedelta(days=i)).replace(tzinfo=jst).strftime("%m/%d")
                            )

            data = make_data()
            data[str(patient["年代"])] += 1
            # 作成したデータをリストにinsert
            self.insert_age_value(data)
            # 日時取得のため、前のデータを登録
            prev_data = patient
            self._age_summary_json["labels"].append(
                datetime.strptime(prev_data["date"], "%Y-%m-%dT%H:%M:%S+09:00").strftime("%m/%d")
            )

        prev_date = datetime.strptime(prev_data["date"], "%Y-%m-%dT%H:%M:%S+09:00")
        # 最終更新のデータから日付が開いている場合、0で埋める
        patients_zero_days = (datetime.now(jst) - prev_date).days - 1
        for i in range(1, patients_zero_days):
            self._clusters_json["data"].append(make_data())

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

    def make_inspections(self) -> None:
        # inspections.jsonの作成
        self._inspections_json = self.json_template_of_inspections()

        for i in range(inspections_first_cell, self.inspections_count):
            date = self.inspections_sheet.cell(row=i, column=1).value
            data = {"判明日": date.strftime("%Y-%m-%d")}
            # 0すら入ってない場合はNoneが返ってくるので、その対策
            pcr = self.inspections_sheet.cell(row=i, column=2).value
            data["検査検体数"] = pcr if pcr else 0
            data["陽性確認"] = self.inspections_sheet.cell(row=i, column=3).value
            self._inspections_json["data"].append(data)

    def make_inspections_summary(self) -> None:
        # inspections_summary.jsonの作成
        self._inspections_summary_json = {
            "data": {
                "検査検体数": [],
                "陽性確認": []
            },
            "labels": [],
            "last_update": self.get_inspections_last_update()
        }

        for inspections_data in self.inspections_json()["data"]:
            date = datetime.strptime(inspections_data["判明日"], "%Y-%m-%d")
            self._inspections_summary_json["data"]["検査検体数"].append(inspections_data["検査検体数"])
            self._inspections_summary_json["data"]["陽性確認"].append(inspections_data["陽性確認"])
            self._inspections_summary_json["labels"].append(date.strftime("%m/%d"))

    def make_main_summary(self) -> None:
        # main_summary.jsonの作成
        # これに関してはテンプレートが大きいのでSUMMARY_INITとして別ファイルに退避している
        self._main_summary_json = SUMMARY_INIT
        self._main_summary_json['last_update'] = self.get_summary_last_update()

        # 以下の式はPDFからデータを取得していた際に使用していたもの。
        # 現在はsummary_sheetの取得に移行しているため、使われていないが、過去にPRしていただいたものとして残している。
        # これ以降、"pdf mode is disabled..."と一緒にコメントアウトされいるものは同意。
        # content = ''.join(self.pdf_texts[3:])
        # self.values = get_numbers_in_text(content)

        # summary_sheetから数値リストを取得
        self.summary_values = self.get_values()
        self.set_summary_values(self._main_summary_json)

    def make_sickbeds_summary(self) -> None:
        # pdf mode is disabled...
        # content = ''.join(self.pdf_texts[3:])
        # self.values = get_numbers_in_text(content)

        # summary_sheetから数値リストを取得
        self.summary_values = self.get_values()
        self._sickbeds_summary_json = {
            "data": {
                "入院患者数": self.summary_values[2],
                "残り病床数": self.sickbeds_count - self.summary_values[2]
            },
            "last_update": self.get_summary_last_update()
        }

    def get_values(self) -> List:
        values = []
        for i in range(3, 10):
            values.append(self.summary_sheet.cell(row=self.data_count - 1, column=i).value)
        return values

    def set_summary_values(self, obj) -> None:
        # リストの先頭の値を"value"にセットする
        obj["value"] = self.summary_values[0]
        # objが辞書型で"children"を持っている場合のみ実行
        if isinstance(obj, dict) and obj.get("children"):
            for child in obj["children"]:
                # 再起させて値をセット
                self.summary_values = self.summary_values[1:]
                self.set_summary_values(child)

    def get_patients_last_update(self) -> str:
        # patients_sheetから"M/D H時現在"の形式で記載されている最終更新日時を取得する
        # クラスターが増えれば端に寄っていき、固定値にすると取得できないので、whileで探索させている
        column_num = 16
        data_time_str = ""
        while not data_time_str:
            if not self.patients_sheet.cell(row=3, column=column_num).value:
                column_num += 1
                continue
            # 数字に全角半角が混じっていることがあるので、半角に統一
            data_time_str = jaconv.z2h(str(self.patients_sheet.cell(row=3, column=column_num).value), digit=True, ascii=True)
        plus_day = 0
        # datetime.strptimeでは24時は読み取れないため。24時を次の日の0時として扱わせる
        if data_time_str[-5:] == "24時現在":
            # 12/31や1/1など、文字数の増減に対応するため、whileで探索させている
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
        # 最後に、頭に"2020/"を付け加えてdatetimeに読み取らせている
        # 2021年になった時などどうするかは未定
        # TODO: 年が変わった場合の対応
        last_update = datetime.strptime("2020/" + data_time_str, "%Y/%m/%d %H時現在") + timedelta(days=plus_day)
        return last_update.replace(tzinfo=jst).isoformat()

    def get_inspections_last_update(self) -> str:
        # 最終データの日の次の日を最終更新日としている
        data_time = self.inspections_sheet.cell(row=self.inspections_count - 1, column=1).value + timedelta(days=1)
        return data_time.replace(tzinfo=jst).isoformat()

    def get_summary_last_update(self) -> str:
        # pdf mode is disabled...
        # caption = self.pdf_texts[0]
        # dt_vals = get_numbers_in_text(caption)
        # last_update = datetime(datetime.now().year, dt_vals[0], dt_vals[1]) + timedelta(hours=dt_vals[2])
        # return datetime.strftime(last_update, '%Y/%m/%d %H:%M')

        # summary_sheetは一列目が日付、二列目が時間なので、それを読み取って反映させている
        return (
                self.summary_sheet.cell(row=self.data_count - 1, column=1).value +
                timedelta(hours=int(self.summary_sheet.cell(row=self.data_count - 1, column=2).value[:-1]))
        ).replace(tzinfo=jst).isoformat()

    def get_patients(self) -> None:
        # 患者データの行数の取得
        while self.patients_sheet:
            self.patients_count += 1
            value = self.patients_sheet.cell(row=self.patients_count, column=2).value
            if not value:
                break

    def get_clusters(self) -> None:
        # クラスターリストの取得とクラスターの列数の取得

        # 一列分、空列があるので、そこを処理するための変数
        none_count = 0
        # "その他/行動歴調査中"がグルーピングされたために、セルが結合されて2行になったので、over_cellとunder_cellの取得が必要になった。
        # under_cellに行きついた際は、under_cell一つ目になるので、最初から1を代入しておく
        under_cell_count = 1
        while self.patients_sheet:
            self.clusters_count += 1
            over_cell = self.patients_sheet.cell(row=4, column=self.clusters_count).value
            under_cell = self.patients_sheet.cell(row=5, column=self.clusters_count).value
            if not over_cell:
                # 上のセルが空で、none_countが0の時、読み飛ばす
                if none_count:
                    # 上のセルが空で、none_countが1、更にunder_cellはある時は、under_cellの内容を読み取る
                    if under_cell:
                        # under_cellをグルーピングしているover_cellを除外するために、under_cellの数をカウントしている
                        under_cell_count += 1
                        self.clusters.append(str(under_cell).replace("\n", ""))
                        continue
                    # 上のセルが空で、none_countが1、そのうえunder_cellもない時は、while文を抜ける
                    break
                none_count += 1

            self.clusters.append(str(over_cell).replace("\n", ""))
        # 最後のunder_cellをグルーピングしているover_cellをNoneに置き換える
        self.clusters[-under_cell_count] = "None"

    def get_inspections(self) -> None:
        # 検査データの行数の取得
        while self.inspections_sheet:
            self.inspections_count += 1
            value = self.inspections_sheet.cell(row=self.inspections_count, column=1).value
            if not value:
                break

    def get_data_count(self) -> None:
        # サマリーデータの行数の取得
        while self.summary_sheet:
            self.data_count += 1
            value = self.summary_sheet.cell(row=self.data_count, column=1).value
            if not value:
                break


if __name__ == '__main__':
    print_log("main", "Init classes")
    data_manager = DataManager()
    data_manager.dump_all_data()
    print_log("main", "Make last_update.json...")
    dumps_json("last_update.json", {
        "last_update": datetime.now(jst).strftime("%Y-%m-%dT%H:%M:00+09:00")
    })
    print_log("main", "Make files complete!")
