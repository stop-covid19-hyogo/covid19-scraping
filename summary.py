from datetime import datetime, timedelta
from typing import Dict

from util import get_file, SUMMARY_INIT, get_numbers_in_text


class MainSummary:
    def __init__(self):
        self.pdf_texts = get_file('/kk03/corona_hasseijyokyo.html', "pdf")
        self.sickbeds_count = 212
        self.values = []
        self._main_summary = {}
        self._sickbeds_summary_json = {}

    def main_summary_json(self) -> Dict:
        if not self._main_summary:
            self.make_main_summary()
        return self._main_summary

    def sickbeds_summary_json(self) -> Dict:
        if not self._sickbeds_summary_json:
            self.make_sickbeds_summary()
        return self._sickbeds_summary_json

    def make_main_summary(self) -> None:
        self._main_summary = SUMMARY_INIT
        self._main_summary['last_update'] = self.get_last_update()

        content = ''.join(self.pdf_texts[3:])
        self.values = get_numbers_in_text(content)
        self.set_summary_values(self._main_summary)

    def set_summary_values(self, obj) -> None:
        obj['value'] = self.values[0]
        if isinstance(obj, dict) and obj.get('children'):
            for child in obj['children']:
                self.values = self.values[1:]
                self.set_summary_values(child)

    def make_sickbeds_summary(self) -> None:
        content = ''.join(self.pdf_texts[3:])
        self.values = get_numbers_in_text(content)
        self._sickbeds_summary_json = {
            "data": {
                "入院患者数": self.values[2],
                "残り病床数": self.sickbeds_count - self.values[2]
            },
            "last_update": self.get_last_update()
        }

    def get_last_update(self) -> str:
        caption = self.pdf_texts[0]
        dt_vals = get_numbers_in_text(caption)
        last_update = datetime(datetime.now().year, dt_vals[0], dt_vals[1]) + timedelta(hours=dt_vals[2])
        return datetime.strftime(last_update, '%Y/%m/%d %H:%M')
