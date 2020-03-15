import jaconv
import os
import re
import requests
import shutil

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pdfminer.high_level import extract_text
from pdfminer.layout import LTContainer, LTTextBox
from typing import Dict, List


base_url = 'https://web.pref.hyogo.lg.jp'
SUMMARY_INIT = {
    'attr': '検査実施人数',
    'value': 0,
    'children': [
        {
            'attr': '陽性患者数',
            'value': 0,
            'children': [
                {
                    'attr': '入院中',
                    'value': 0,
                    'children': [
                        {
                            'attr': '軽症・中等症',
                            'value': 0,
                        },
                        {
                            'attr': '重症',
                            'value': 0,
                        }
                    ]
                },
                {
                    'attr': '退院',
                    'value': 0,
                },
                {
                    'attr': '死亡',
                    'value': 0,
                }
            ]
        }
    ],
    'last_update': ''
}


def get_pdf(url: str) -> str:
    html_doc = requests.get(base_url + url).text
    soup = BeautifulSoup(html_doc, 'html.parser')

    real_page_tags = soup.find_all('a')

    pdf_file_url = ''
    for tag in real_page_tags:
        href = tag.get('href')
        if href[-4:] == '.pdf':
            pdf_file_url = base_url + href
            break

    assert pdf_file_url, "Can't get pdf file!"

    filename = './data/' + os.path.basename(pdf_file_url)
    res = requests.get(pdf_file_url, stream=True)
    if res.status_code == 200:
        with open(filename, 'wb') as f:
            res.raw.decode_content = True
            shutil.copyfileobj(res.raw, f)

    return filename


def get_numbers_in_text(text: str) -> List[int]:
    return list(map(int, re.findall('[0-9]+', jaconv.z2h(text, digit=True))))


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
        filename = get_pdf('/kk03/corona_hasseijyokyo.html')

        pdf_texts = extract_text(filename).split('\n')

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
