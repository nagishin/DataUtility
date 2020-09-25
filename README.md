# DataUtility

## インストール
`pip install git+https://github.com/nagishin/DataUtility.git`

## 使い方
```
import DataUtility as du

#-------------------------------------------------------------------------------
# bybit約定履歴を取得
#-------------------------------------------------------------------------------
# [params]
#  start_ut / end_ut : UnixTimeで指定
#                      取得可能期間 : 2019-10-01以降かつ前日まで
#  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
#                      ファイルがない or 期間を満たしていない場合はrequestで取得
#                      csvファイル保存
# [return]
#  DataFrame columns=['unixtime', 'side', 'size', 'price']
#-------------------------------------------------------------------------------
df_bybit_trades = du.Tool.get_trades_from_bybit(start_ut, end_ut, csv_path='./bybit_trades.csv')


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
#  period            : 分を指定
#  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
#                      ファイルがない or 期間を満たしていない場合はrequestで取得
#                      csvファイル保存
# [return]
#  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
#-------------------------------------------------------------------------------
df_bitmex_ohlcv = du.Tool.get_ohlcv_from_bitmex(start_ut, end_ut, period=1, csv_path='./bitmex_ohlcv.csv')


#-------------------------------------------------------------------------------
# OHLCVを上位時間足にリサンプリング
#-------------------------------------------------------------------------------
# [params]
#  df     : DateTimeIndexとopen,high,low,close,volume列を含むDataFrame
#  period : リサンプルするタイムフレーム('1S'(秒), '5T'(分), '4H'(時), '1D'(日) etc.)
# [return]
#  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
#-------------------------------------------------------------------------------
df_bitmex_ohlcv_1h = du.Tool.downsample_ohlcv(df_bitmex_ohlcv, period='1H')
```
