# COVID-19 Scraping and Validation Script for Hyogo
[![Deploy JSON Files](https://github.com/stop-covid19-hyogo/covid19-scraping/actions/workflows/deploy.yml/badge.svg)](https://github.com/stop-covid19-hyogo/covid19-scraping/actions/workflows/deploy.yml)

## What's this?
兵庫県公式サイトや、ひょうごオープンデータカタログで公開されている情報を集め、jsonとして出力するPythonスクリプトです。
[兵庫県 新型コロナウイルスまとめサイト](https://stop-covid19-hyogo.org/)で使用する形に整形し、出力します。  
加えてオープンデータの検証も行い、検証結果も出力します。

## Make data
```shell script
pip install -r requirements.txt
python3 main.py
```

## Reference data list
このスクリプトでは、以下のデータを参照し、jsonを出力しています。

|ファイル名|データの詳細|データの参照元|
|---|---|---|
|main_summary.json|検査状況/患者状況の総まとめ|[ひょうごオープンデータカタログ「新型コロナウイルス陽性者の状況（推移）」](http://open-data.pref.hyogo.lg.jp/index.php?key=muq1trrqj-175#_175)|
|patients.json|患者についての情報|[兵庫県「新型コロナウイルスに感染した患者の状況」](https://web.pref.hyogo.lg.jp/kk03/corona_kanjyajyokyo.html)|
|patients_summary.json|日別患者数|[ひょうごオープンデータカタログ「新型コロナウィルス感染症の県内検査状況」](http://open-data.pref.hyogo.lg.jp/index.php?key=muve6rx2r-175#_175)|
|inspections.json|PCR検査数(ページでは未使用のデータ)|[ひょうごオープンデータカタログ「新型コロナウィルス感染症の県内検査状況」](http://open-data.pref.hyogo.lg.jp/index.php?key=muve6rx2r-175#_175)|
|inspections_summary.json|PCR検査の総合計等|[ひょうごオープンデータカタログ「新型コロナウィルス感染症の県内検査状況」](http://open-data.pref.hyogo.lg.jp/index.php?key=muve6rx2r-175#_175)|
|last_update.json|データの最終更新日|スクリプト実行日時|

以上が東京都版で使われていて、兵庫県版でも使用しているデータです。そして、以下が兵庫県版で独自に生成、使用しているデータです。

|ファイル名|データの詳細|データの参照元|
|---|---|---|
|clusters.json|クラスター別の患者数(ページでは未使用のデータ)|[兵庫県「新型コロナウイルスに感染した患者の状況」](https://web.pref.hyogo.lg.jp/kk03/corona_kanjyajyokyo.html)|
|clusters_summary.json|クラスター別の総患者数|[兵庫県「新型コロナウイルスに感染した患者の状況」](https://web.pref.hyogo.lg.jp/kk03/corona_kanjyajyokyo.html)|
|age.json|年代別の総患者数|[兵庫県「新型コロナウイルスに感染した患者の状況」](https://web.pref.hyogo.lg.jp/kk03/corona_kanjyajyokyo.html)|
|age_summary.json|日別の年代別総患者数(ページでは未使用のデータ)|[兵庫県「新型コロナウイルスに感染した患者の状況」](https://web.pref.hyogo.lg.jp/kk03/corona_kanjyajyokyo.html)|
|sickbeds_summary.json|入院患者数と残り病床数(ページでは未使用のデータ)|[ひょうごオープンデータカタログ「新型コロナウイルス陽性者の状況（推移）」](http://open-data.pref.hyogo.lg.jp/index.php?key=muq1trrqj-175#_175)|
|current_patients.json|治療中患者(入院患者)数の推移|[ひょうごオープンデータカタログ「新型コロナウイルス陽性者の状況（推移）」](http://open-data.pref.hyogo.lg.jp/index.php?key=muq1trrqj-175#_175)|
|positive_or_negative.json|陽性数/陰性数と7日間移動平均の陽性数/陽性率|[ひょうごオープンデータカタログ「新型コロナウィルス感染症の県内検査状況」](http://open-data.pref.hyogo.lg.jp/index.php?key=muve6rx2r-175#_175)|

## Data Validation
このスクリプトでは、COVID-19の陽性患者の属性や陽性者数、検査数といったセンシティブな情報を正確に把握するためにオープンデータを検証し、ヒューマンエラーやミスを一覧化するといったことを行っています。  
また、これらの一覧化されたデータは[こちらのサイト](https://warnings.stop-covid19-hyogo.org)で閲覧可能です。

## License
このスクリプトは[MITライセンス](LICENSE)で公開されています。
