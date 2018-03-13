# 競馬予想AI

ニューラルネットワークによる競馬のレース予想

* Python3
* Chainer3

[データの入手先][1]
[詳しい解説][2]

## Make dataset

学習のためのデータは、csvファイルで用意します

* レース情報：
```
レース名|競馬場|馬場|距離|天気|オッズ|日付
```

* 出走馬情報：
```
着順|馬名|騎手名
```

* csvデータ：
```
レース情報,出走馬情報,出走馬情報,出走馬情報・・・
```

* 例：
```SH
$ head -n1 race_train.csv
新潟日報賞|新潟|芝|1400|曇|600:230_160_980:410:1210:490_6730_3340:2700:22900:102190|20170812,1|アポロノシンザン|津村明秀,2|ビップライブリー|大野拓弥,3|ディアマイダーリン|田中勝春,4|ラプソディーア|吉田豊,5|ルグランパントル|柴田善臣,6|メイショウメイゲツ|江田照男,7|ネオスターダム|内田博幸,8|ピンストライプ|Ｍ．デム,9|ナイトフォックス|丸田恭介,10|テンテマリ|丸山元気,11|エリーティアラ|北村宏司,12|クリノタカラチャン|野中悠太,13|スズカシャーマン|伊藤工真,14|スズカアーサー|武士沢友,15|オヒア|小崎綾也,16|マリオーロ|吉田隼人,17|フレンドスイート|柴田大知,18|ディープジュエリー|石橋脩
```

## Training

* 学習

```SH
$ python3 train.py -t race_train.csv -s race_test.csv -g 0
epoch main/loss validation/main/loss main/tansho validation/main/tansho main/fukusho1 validation/main/fukusho1 main/fukusho2 validation/main/fukusho2 main/fukusho3 validation/main/fukusho3 main/umaren validation/main/umaren main/wide validation/main/wide main/triren validation/main/triren main/tritan validation/main/tritan
1 10.0332 9.07242 570.22 530.64 181.864 166.5 119.914 107.2 107.6 92.5467 150.764 81.14 136.028 55.58 304.788 33.68 991.616 0 
2 7.31421 8.79142 593.248 518.24 188.616 164.32 130.716 106.23 115.605 95.7067 187.872 83.66 135.752 47.6 145.276 3.64 272.876 7.5 
・・・（略）
```
## Prefigure

* 予想

```SH
$ python3 prefigure.py -e "中山|芝|1800|晴" -r "サトノスティング|横山典弘,ウイングチップ|丸田恭介,カレンリスベット|蛯名正義,キャプテンペリー|大野拓弥,コスモナインボール|柴田大知,バルデ ス|戸崎圭太,ブラックスビーチ|北村宏司,ウインファビラス|松岡正海,クラウンディバイダ|石橋脩,タブレットピーシー|田中勝春"
予想順位    馬名    Accuracy
1    ウイングチップ    0.10088613
2    キャプテンペリー    0.10074568
3    コスモナインボール    0.09816859
・・・（略）
```

## License

[Gnu AGPL 3.0](LICENSE)

[1]: https://jra-van.jp/
[2]: https://cocon-corporation.com/cocontoco/horseraceprediction_ai/
