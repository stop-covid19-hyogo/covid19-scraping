# -*- coding: utf-8 -*-
import requests
import openpyxl
import codecs
import os
import shutil
import jaconv
import re
import time

from io import BytesIO
from bs4 import BeautifulSoup
from json import dumps, loads
from datetime import datetime, timezone, timedelta
from enum import IntEnum

from typing import Union, Dict, List

base_url = "https://web.pref.hyogo.lg.jp"
jst = timezone(timedelta(hours=9), 'JST')

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
                    'attr': '宿泊療養',
                    'value': 0,
                },
                {
                    'attr': '入院・宿泊療養調整等',
                    'value': 0,
                    'children': [
                        {
                            'attr': '入院調整',
                            'value': 0,
                        }
                    ]
                },
                {
                    'attr': '自宅療養',
                    'value': 0,
                },
                {
                    'attr': 'その他医療機関福祉施設等',
                    'value': 0,
                },
                {
                    'attr': '死亡',
                    'value': 0,
                },
                {
                    'attr': '退院',
                    'value': 0,
                }
            ]
        }
    ],
    'last_update': ''
}


class PatientsColumns(IntEnum):
    番号 = 2
    発表日 = 3
    年代 = 4
    性別 = 5
    管轄 = 6
    居住地 = 7
    職業 = 8
    発症日 = 9
    備考欄 = 13
# 以下のcolumnは未使用のため、コメントとして残しているに過ぎない
# 旧陽性者属性ファイルのcolumns
#     渡航歴 = 10
#     備考欄 = 11
# 新陽性者属性ファイルのcolumns
#     接触歴_有 = 10
#     接触歴_無 = 11
#     接触歴_調査中 = 12


class InspectionsColumns(IntEnum):
    年月日 = 1
    検査数合計 = 2
    地方衛生研究所PCR = 3
    民間検査機関PCR = 4
    民間検査機関抗原 = 5
    陽性件数 = 6


class MainSummaryColumns(IntEnum):
    発表年月日 = 1
    発表時間 = 2
    検査実施人数 = 3
    感染者数 = 4
    陽性者数 = 5
    疑似症患者数 = 6
    入院中 = 7
    中等症以下 = 8
    重症 = 9
    宿泊療養 = 10
    入院宿泊療養調整等 = 11
    入院調整 = 12
    自宅療養 = 13
    その他 = 14
    死亡 = 15
    退院 = 16


def print_log(type: str, message: str) -> None:
    print(f"[{datetime.now().astimezone(jst).strftime('%Y-%m-%d %H:%M:%S+09:00')}][covid19-scraping:{type}]: {message}")


def get_html_soup(base: str = base_url, path: str = "/") -> BeautifulSoup:
    # Webスクレイピングをして、ダウンロードしたいファイルのリンクを探索する
    url = base + path
    print_log("get", f"Get html file from {url}")
    html_doc = ""
    # 兵庫県のサイトは読み込みが遅く、タイムアウトしやすいので、最大5回までリトライするようにしている
    failed_count = 0
    while not html_doc:
        try:
            html_doc = requests.get(url).content
        except Exception:
            if failed_count >= 5:
                raise Exception(f"Failed get html file from \"{url}\"!")
            print_log("get", f"Failed get html file from \"{url}\". retrying...")
            failed_count += 1
            time.sleep(5)
    return BeautifulSoup(html_doc, "html.parser")


def get_file(path: str, save_file: bool = False, index: int = 0) -> openpyxl.workbook.workbook.Workbook:
    soup = get_html_soup(path=path)

    real_page_tags = soup.find_all("a")

    file_path = ""
    pattern = re.compile("xls[mx]?")
    found_count = 0
    for tag in real_page_tags:
        href = tag.get("href")
        if href is not None and pattern.match(href[-4:]):
            if index == found_count:
                file_path = tag.get("href")
                break
            found_count += 1

    assert file_path, "Can't get xlsx file!"
    return requests_file(file_path, file_path[-4:], save_file)


def requests_file(file_path: str, file_type: str, save_file: bool = False) -> openpyxl.workbook.workbook.Workbook:
    file_url = base_url + file_path
    print_log("requests", f"Requests {file_type} file from {file_url}")
    failed_count = 0
    # saveフラグが立っている時はファイルを保存する。
    if save_file:
        status_code = 400
        # 兵庫県のサイトは読み込みが遅く、タイムアウトしやすいので、最大5回までリトライするようにしている
        while status_code not in [200, 404]:
            try:
                res = requests.get(file_url, stream=True)
                status_code = res.status_code
            except Exception:
                if failed_count >= 5:
                    raise Exception(f"Failed get {file_type} file from \"{file_url}\"!")
                print_log("requests", f"Failed get {file_type} file from \"{file_url}\". retrying...")
                failed_count += 1
                time.sleep(5)
        if status_code == 404:
            raise Exception(f"File path has changed.({file_path})")
        # ダウンロードしたファイルを保存
        filename = './data/' + os.path.basename(file_url)
        with open(filename, 'wb') as f:
            res.raw.decode_content = True
            shutil.copyfileobj(res.raw, f)
        return openpyxl.load_workbook(filename, data_only=True)
    else:
        # ダウンロードしたものを直接binaryとしてメモリに読み込ませる。
        # あまりよろしくないと思われるが、xlsxのような容量の小さいファイルに関しては問題ないだろう
        file_bin = b""
        # 兵庫県のサイトは読み込みが遅く、タイムアウトしやすいので、最大5回までリトライするようにしている
        while not file_bin:
            try:
                file_bin = requests.get(file_url).content
            except Exception:
                if failed_count >= 5:
                    raise Exception(f"Failed get {file_type} file from \"{file_url}\"!")
                print_log("file", f"Failed get {file_type} file from \"{file_url}\". retrying...")
                failed_count += 1
                time.sleep(5)
        return openpyxl.load_workbook(BytesIO(file_bin))


def return_date(date: Union[datetime, int]) -> Union[datetime, None]:
    # Excel日時か普通のdatetimeかを判別して自動で返す関数
    # 普通のdatetimeであれば、タイムゾーンを設定して返す
    # また、どの形式にも当てはまらない場合はNoneを返す
    if isinstance(date, int):
        return excel_date(date)
    elif isinstance(date, datetime):
        return date.replace(tzinfo=jst)
    else:
        return None


def excel_date(num: int) -> datetime:
    # Excel日付と呼ばれる形式に対応するための関数
    # 詳しくは https://qiita.com/nezumi/items/23c301c661f5e9653f19
    return datetime(1899, 12, 30, tzinfo=jst) + timedelta(days=num)


def loads_json(file_name: str, path: str = "schema") -> Dict:
    # schemaなどのjsonを読み込むために用いる。
    with codecs.open(f"./{path}/" + file_name, "r", "utf-8") as f:
        return loads(f.read())


def dumps_json(file_name: str, json_data: Union[Dict, List]) -> None:
    # 日本語文字化け対策などを施したdump jsonキット
    with codecs.open("./data/" + file_name, "w", "utf-8") as f:
        f.write(dumps(json_data, ensure_ascii=False, indent=4, separators=(',', ': ')))


def get_weekday(day: int) -> str:
    weekday_list = ["月", "火", "水", "木", "金", "土", "日"]
    return weekday_list[day % 7]


def return_ymd(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


def get_numbers_in_text(text: str) -> List[int]:
    return list(map(int, re.findall('[0-9]+', jaconv.z2h(text, digit=True))))


def requests_now_data_json(json_name: str) -> dict:
    try:
        return loads(requests.get("https://stop-covid19-hyogo.github.io/covid19-scraping/" + json_name).text)
    except Exception:
        result = requests.get(
            "https://raw.githubusercontent.com/stop-covid19-hyogo/covid19-scraping/gh-pages/" + json_name
        ).text
        if result == "404: Not Found":
            return {}
        return loads(result)
