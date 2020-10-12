# DataUtility

## インストール
`pip install git+https://github.com/nagishin/DataUtility.git`

## アンインストール
`pip uninstall DataUtility`

## 使い方
```
from datetime import datetime
import DataUtility as du

start_date = datetime.strptime('2020/09/01 09:00:00+0900', '%Y/%m/%d %H:%M:%S%z')
end_date   = datetime.strptime('2020/09/05 09:00:00+0900', '%Y/%m/%d %H:%M:%S%z')
start_ut   = int(start_date.timestamp())
end_ut     = int(end_date.timestamp())

#-------------------------------------------------------------------------------
# bybit約定履歴を取得
# (https://public.bybit.com/trading/BTCUSD/ より)
#-------------------------------------------------------------------------------
# [params]
#  start_ut / end_ut : UnixTimeで指定
#                      取得可能期間 : 2019-10-01以降かつ前日まで
#  symbol            : 取得対象の通貨ペアシンボル名（デフォルトは BTCUSD）
#  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
#                      ファイルがない or 期間を満たしていない場合はrequestで取得
#                      csvファイル保存 (None or 空文字は保存しない)
# [return]
#  DataFrame columns=['unixtime', 'side', 'size', 'price']
#-------------------------------------------------------------------------------
df_bybit_trades = du.Tool.get_trades_from_bybit(start_ut, end_ut, symbol='BTCUSD', csv_path='./bybit_trades.csv')


#-------------------------------------------------------------------------------
# 約定履歴をOHLCVにリサンプリング
#-------------------------------------------------------------------------------
# [params]
#  df     : DateTimeIndexとprice,size列を含むDataFrame
#  period : リサンプルするタイムフレーム ex) '1S'(秒), '5T'(分), '4H'(時), '1D'(日)
# [return]
#  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
#-------------------------------------------------------------------------------
df_bybit_ohlcv = du.Tool.trade_to_ohlcv(df_bybit_trades, period='1T')


#-------------------------------------------------------------------------------
# BitMEX OHLCVを取得
#-------------------------------------------------------------------------------
# [params]
#  start_ut / end_ut : UnixTimeで指定
#  period            : 分を指定 (1 or 5 or 60 or 1D)
#  symbol            : 取得対象の通貨ペアシンボル名 (デフォルトはXBTUSD)
#  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
#                      ファイルがない or 期間を満たしていない場合はrequestで取得
#                      csvファイル保存 (None or 空文字は保存しない)
#  request_interval  : 複数request時のsleep時間(sec)
# [return]
#  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
#-------------------------------------------------------------------------------
df_bitmex_ohlcv = du.Tool.get_ohlcv_from_bitmex(start_ut, end_ut, period=1, symbol='XBTUSD', csv_path='./bitmex_ohlcv.csv', request_interval=0.5)


#-------------------------------------------------------------------------------
# OHLCVを上位時間足にリサンプリング
#-------------------------------------------------------------------------------
# [params]
#  df     : DateTimeIndexとopen,high,low,close,volume列を含むDataFrame
#  period : リサンプルするタイムフレーム ex) '1S'(秒), '5T'(分), '4H'(時), '1D'(日)
# [return]
#  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
#-------------------------------------------------------------------------------
df_bitmex_ohlcv_1h = du.Tool.downsample_ohlcv(df_bitmex_ohlcv, period='1H')


#-------------------------------------------------------------------------------
# DataFrameの行を指定列の値範囲で絞り込み
#-------------------------------------------------------------------------------
# [params]
#  df        : column列を含むDataFrame
#  column    : 絞り込み判定を行う列名
#  min_value : 絞り込み下限値
#  max_value : 絞り込み上限値
#-------------------------------------------------------------------------------
divided_date = datetime.strptime('2020/09/03 09:00:00+0900', '%Y/%m/%d %H:%M:%S%z')
divided_ut   = int(divided_date.timestamp())

df_filtered1 = du.Tool.filter_df(df_bitmex_ohlcv_1h, column='unixtime', min_value=start_ut, max_value=divided_ut-1)
df_filtered2 = du.Tool.filter_df(df_bitmex_ohlcv_1h, column='unixtime', min_value=divided_ut, max_value=end_ut)


#-------------------------------------------------------------------------------
# DataFrameを結合
#-------------------------------------------------------------------------------
# [params]
#  concat_dfs  : 結合するDataFrameリスト
#  sort_column : 結合後にソートする列名
#-------------------------------------------------------------------------------
df_concat = du.Tool.concat_df([df_filtered1, df_filtered2], sort_column='unixtime')
```

## GitHub Gist
[DataUtilityの使い方](https://gist.github.com/nagishin/1677ffa401476e9e98191a04012ac189)
