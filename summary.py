from datetime import datetime, timedelta
from typing import Dict, List

from util import requests_file, SUMMARY_INIT, get_numbers_in_text


class MainSummary:
    def __init__(self):
        # self.pdf_texts = get_file('/kk03/corona_hasseijyokyo.html', "pdf")
        self.sheets = requests_file("https://web.pref.hyogo.lg.jp/kk03/documents/yousei.xlsx", "xlsx", True)["yousei"]
        self.sickbeds_count = 246
        self.values = []
        self.data_count = 2
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
        #content = ''.join(self.pdf_texts[3:])
        #self.values = get_numbers_in_text(content)
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
        ).strftime("%Y/%m/%d %H:%M")

    def get_data_count(self) -> None:
        while self.sheets:
            self.data_count += 1
            value = self.sheets.cell(row=self.data_count, column=1).value
            if not value:
                break
