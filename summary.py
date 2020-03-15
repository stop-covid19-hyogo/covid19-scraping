from datetime import datetime, timedelta
from typing import Dict

from util import get_file, SUMMARY_INIT, get_numbers_in_text


class MainSummary:
    def __init__(self):
        self.summary = SUMMARY_INIT
        self.values = []

    def set_summary_values(self, obj) -> None:
        obj['value'] = self.values[0]
        if isinstance(obj, dict) and obj.get('children'):
            for child in obj['children']:
                self.values = self.values[1:]
                self.set_summary_values(child)

    def get_summary_json(self) -> Dict:
        pdf_texts = get_file('/kk03/corona_hasseijyokyo.html', "pdf")

        # Set summary values
        content = ''.join(pdf_texts[3:])
        self.values = get_numbers_in_text(content)
        self.set_summary_values(self.summary)

        # Set last update
        caption = pdf_texts[0]
        dt_vals = get_numbers_in_text(caption)
        last_update = datetime(datetime.now().year, dt_vals[0], dt_vals[1]) + timedelta(hours=dt_vals[2])
        self.summary['last_update'] = datetime.strftime(last_update, '%Y-%m-%dT%H:%M:%S+09:00')

        return self.summary
