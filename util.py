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
from pdfminer.high_level import extract_text

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


def print_log(type: str, message: str) -> None:
    print(f"[{datetime.now().astimezone(jst).strftime('%Y-%m-%d %H:%M:%S+09:00')}][covid19-scraping:{type}]: {message}")


def get_file(path: str, file_type: str, save_file: bool = False) \
        -> Union[openpyxl.workbook.workbook.Workbook, List[str]]:
    # Webスクレイピングをして、ダウンロードしたいファイルのリンクを探索する
    print_log("get", "get html file...")
    html_doc = ""
    # 兵庫県のサイトは読み込みが遅く、タイムアウトしやすいので、最大5回までリトライするようにしている
    failed_count = 0
    while not html_doc:
        try:
            html_doc = requests.get(base_url + path).text
        except Exception:
            if failed_count >= 5:
                raise Exception(f"Failed get html file from \"{base_url + path}\"!")
            print_log("get", f"Failed get html file from \"{base_url + path}\". retrying...")
            failed_count += 1
            time.sleep(5)
    soup = BeautifulSoup(html_doc, 'html.parser')

    real_page_tags = soup.find_all("a")

    file_path = ""
    for tag in real_page_tags:
        if tag.get("href")[-len(file_type):] == file_type:
            file_path = tag.get("href")
            break

    assert file_path, f"Can't get {file_type} file!"
    return requests_file(file_path, file_type, save_file)


def requests_file(file_path: str, file_type: str, save_file: bool = False) \
        -> Union[openpyxl.workbook.workbook.Workbook, List[str]]:
    file_url = base_url + file_path
    print_log("requests", f"Requests {file_type} file from {file_url}")
    failed_count = 0
    # saveフラグが立っているか、ファイルがpdfの時はファイルを保存する。
    # 現状対応してるファイルタイプはxlsx(Excelデータ)とpdfのみ
    if save_file or file_type == "pdf":
        status_code = 404
        # 兵庫県のサイトは読み込みが遅く、タイムアウトしやすいので、最大5回までリトライするようにしている
        while not status_code == 200:
            try:
                res = requests.get(file_url, stream=True)
                status_code = res.status_code
            except Exception:
                if failed_count >= 5:
                    raise Exception(f"Failed get {file_type} file from \"{file_url}\"!")
                print_log("requests", f"Failed get {file_type} file from \"{file_url}\". retrying...")
                failed_count += 1
                time.sleep(5)
        # ダウンロードしたファイルを保存
        filename = './data/' + os.path.basename(file_url)
        with open(filename, 'wb') as f:
            res.raw.decode_content = True
            shutil.copyfileobj(res.raw, f)
        if file_type == "pdf":
            return extract_text(filename).split('\n')
        elif file_type == "xlsx":
            return openpyxl.load_workbook(filename, data_only=True)
        else:
            raise Exception(f"Not support file type: {file_type}")
    else:
        # ダウンロードしたものを直接binaryとしてメモリに読み込ませる。
        # あまりよろしくないと思われるが、xlsxなどの容量の小さいファイルに関しては問題ないだろう
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
        if file_type == "xlsx":
            return openpyxl.load_workbook(BytesIO(file_bin))
        else:
            raise Exception(f"Not support file type: {file_type}")


def return_date(date: Union[datetime, int]) -> datetime:
    # Excel日時か普通のdatetimeかを判別して自動で返す関数
    # 普通のdatetimeであれば、タイムゾーンを設定して返す
    if isinstance(date, int):
        return excel_date(date)
    else:
        assert isinstance(date, datetime)
        return date.replace(tzinfo=jst)


def excel_date(num: int) -> datetime:
    # Excel日付と呼ばれる形式に対応するための関数
    # 詳しくは https://qiita.com/nezumi/items/23c301c661f5e9653f19
    return datetime(1899, 12, 30, tzinfo=jst) + timedelta(days=num)


def loads_schema(file_name: str) -> Dict:
    # schemaを読み込むために用いる。
    with codecs.open("./schema/" + file_name, "r", "utf-8") as f:
        return loads(f.read())


def dumps_json(file_name: str, json_data: Dict) -> None:
    # 日本語文字化け対策などを施したdump jsonキット
    with codecs.open("./data/" + file_name, "w", "utf-8") as f:
        f.write(dumps(json_data, ensure_ascii=False, indent=4, separators=(',', ': ')))


def get_weekday(day: int) -> str:
    weekday_list = ["月", "火", "水", "木", "金", "土", "日"]
    return weekday_list[day % 7]


def month_and_day(date: datetime) -> str:
    return f"{date.month}/{date.day}"


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
