import jaconv
import os
import re
import requests
import shutil
from datetime import datetime, timezone

from pdfminer.high_level import extract_text
from pdfminer.layout import LTContainer, LTTextBox


def find_textboxes_recursively(layout_obj):
    if isinstance(layout_obj, LTTextBox):
        return layout_obj

    # LTContainer objects have children
    if isinstance(layout_obj, LTContainer):
        ltboxes = [find_textboxes_recursively(child) for child in layout_obj]
        return [box for box in ltboxes if box]

    return None


def download(url: str):
    filename = os.path.basename(url)
    res = requests.get(url, stream=True)
    if res.status_code == 200:
        with open(filename, 'wb') as file:
            res.raw.decode_content = True
            shutil.copyfileobj(res.raw, file)


class MainSummary:
    def __init__(self):
        self.summary = {
            "attr": "検査実施人数",
            "value": 0,
            "children": [
                {
                    "attr": "陽性患者数",
                    "value": 0,
                    "children": [
                        {
                            "attr": "入院中",
                            "value": 0,
                            "children": [
                                {
                                    "attr": "軽症・中等症",
                                    "value": 0,
                                },
                                {
                                    "attr": "重症",
                                    "value": 0,
                                }
                            ]
                        },
                        {
                            "attr": "退院",
                            "value": 0,
                        },
                        {
                            "attr": "死亡",
                            "value": 0,
                        }
                    ]
                }
            ],
        }
        self.values = []


    def set_values(self, obj):
        obj['value'] = self.values[0]
        if isinstance(obj, dict) and obj.get('children'):
            for child in obj['children']:
                self.values = self.values[1:]
                self.set_values(child)

        # TODO: get last_update from PDF
        self.summary['last_update'] = datetime.strftime(datetime.today(), "%Y-%m-%dT%H:%M:%S+09:00")


    def get_summary_json(self, url):
        # TODO: fetch latest PDF file
        url = 'https://web.pref.hyogo.lg.jp/kk03/documents/kensayosei0313.pdf'
        filename = os.path.basename(url)
        # download(url)

        text = ''.join(extract_text(filename).split('\n')[3:])
        self.values = list(map(int, re.findall('[0-9]+', jaconv.z2h(text, digit=True))))

        self.set_values(self.summary)
        return self.summary
