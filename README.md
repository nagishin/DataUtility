# DataUtility

## インストール
`pip install git+https://github.com/nagishin/DataUtility.git`

## アンインストール
`pip uninstall DataUtility`

## 1. Timeクラス
日付変換・加工をサポートするクラス
 * UnixTime, datetime, 日付文字列のいずれかを設定してTimeオブジェクトを作成します.
 * Timeオブジェクトは必要に応じてタイムゾーン変換や時刻計算・丸めが可能です.
 * TimeオブジェクトからUnixTime, datetime, 日付文字列の形式で時刻を取得できます.

```
import time
from datetime import datetime
import DataUtility as du

#-------------------------------------------------------------------------------
# Timeオブジェクト生成
#-------------------------------------------------------------------------------
# UnixTimeから
t = du.Time(time.time(), tz='UTC')
# datetimeから
t = du.Time(datetime.now(), tz='JST')
# 日付文字列から
t = du.Time('2021/03/15 10:10:22', tz=+9)

#-------------------------------------------------------------------------------
# Timeオブジェクトから時刻取得
#-------------------------------------------------------------------------------
# UnixTime取得
ut = t.unixtime()
# datetime取得
dt = t.datetime()
# 日付文字列取得
st = t.str('%Y/%m/%d %H:%M:%S')

#-------------------------------------------------------------------------------
# 日付文字列をUnixTimeに変換
#-------------------------------------------------------------------------------
t = du.Time('2021/03/15 10:10:22', tz='JST')
ut = t.unixtime()

# メソッドチェーンで記述 (上記と同処理)
ut = du.Time('2021/03/15 10:10:22', tz='JST').unixtime()

#-------------------------------------------------------------------------------
# 現在時刻の4H足 開始時刻をdatetimeで取得
#-------------------------------------------------------------------------------
t = du.Time(datetime.now(), tz='UTC')
t.round_hours(4)
dt = t.datetime()

# メソッドチェーンで記述 (上記と同処理)
dt = du.Time(datetime.now(), tz='UTC').round_hours(4).datetime()

#-------------------------------------------------------------------------------
# 現在時刻(JST)の8時間30分後の15m足 開始時刻をUTC日付文字列('%Y/%m/%d %H:%M:%S')で取得
#-------------------------------------------------------------------------------
t = du.Time(datetime.now(), tz='JST')
t.add_hours(8)
t.add_minutes(30)
t.round_minutes(15)
t.convert_timezone('UTC')
st = t.str('%Y/%m/%d %H:%M:%S')

# メソッドチェーンで記述 (上記と同処理)
st = du.Time(datetime.now(), tz='JST') \
    .add_hours(8) \
    .add_minutes(30) \
    .round_minutes(15) \
    .convert_timezone('UTC') \
    .str('%Y/%m/%d %H:%M:%S')
```

## 2. Toolクラス
BitMEX, bybitのOHLCVや約定履歴の取得・加工をサポートするクラス<br>
DataFrameでよく行う加工や変換を簡単に行う機能を関数化

```
from datetime import datetime
import DataUtility as du

#start_date = datetime.strptime('2020/09/01 09:00:00+0900', '%Y/%m/%d %H:%M:%S%z')
#end_date   = datetime.strptime('2020/09/05 09:00:00+0900', '%Y/%m/%d %H:%M:%S%z')
#start_ut   = int(start_date.timestamp())
#end_ut     = int(end_date.timestamp())

start_ut = int(du.Time('2020/09/01 09:00:00', 'JST').unixtime())
end_ut   = int(du.Time('2020/09/05 09:00:00', 'JST').unixtime())

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

#---------------------------------------------------------------------------
# bybit OHLCVを取得
# (取得件数:200/requestとなるため, 大量取得時はRateLimit注意)
#---------------------------------------------------------------------------
# [params]
#  start_ut / end_ut : UnixTimeで指定
#  period            : 期間指定 (1 3 5 15 30 60 120 240 360 720 'D' 'M' 'W')
#  symbol            : 取得対象の通貨ペアシンボル名 (デフォルトはBTCUSD)
#  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
#                      ファイルがない or 期間を満たしていない場合はrequestで取得
#                      csvファイル保存 (None or 空文字は保存しない)
#  request_interval  : 複数request時のsleep時間(sec)
#  ohlcv_kind        : end point指定
#                      'default':kline, 'mark':mark-price, 'index':index-price, 'premium':premium-index
# [return]
#  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', ('volume')]
#---------------------------------------------------------------------------
df_bybit_ohlcv = du.Tool.get_ohlcv_from_bybit(start_ut, end_ut, period=1, symbol='BTCUSD', csv_path='./bybit_ohlcv.csv', ohlcv_kind='default')
df_bybit_index_ohlcv = du.Tool.get_ohlcv_from_bybit(start_ut, end_ut, period=1, symbol='BTCUSD', csv_path='./bybit_index_ohlcv.csv', ohlcv_kind='index')
df_bybit_mark_ohlcv = du.Tool.get_ohlcv_from_bybit(start_ut, end_ut, period=1, symbol='BTCUSD', csv_path='./bybit_mark_ohlcv.csv', ohlcv_kind='mark')
df_bybit_premium_ohlcv = du.Tool.get_ohlcv_from_bybit(start_ut, end_ut, period=1, symbol='BTCUSD', csv_path='./bybit_premium_ohlcv.csv', ohlcv_kind='premium')

#---------------------------------------------------------------------------
# coinbase OHLCVを取得
# (取得件数:300/requestとなるため, 大量取得時はRateLimit注意)
#---------------------------------------------------------------------------
# [params]
#  start_ut / end_ut : UnixTimeで指定
#  period            : 分を指定 (1 or 5 or 15 or 60 or 360 or 1440)
#  symbol            : 取得対象の通貨ペアシンボル名 (デフォルトはBTC-USD)
#  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
#                      ファイルがない or 期間を満たしていない場合はrequestで取得
#                      csvファイル保存 (None or 空文字は保存しない)
#  request_interval  : 複数request時のsleep時間(sec)
# [return]
#  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
#---------------------------------------------------------------------------
df_coinbase_ohlcv = du.Tool.get_ohlcv_from_coinbase(start_ut, end_ut, period=1, symbol='BTC-USD', request_interval=0.5)

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


#---------------------------------------------------------------------------
# デバッグ用 オブジェクト整形出力
#---------------------------------------------------------------------------
# [params]
#  data        : 表示するオブジェクト (int, float, str, list, dict, DataFrame, ndarray etc...)
#  indent      : 配列, リスト要素などを表示するインデント (str)
#  print_limit : 配列, リストなどの表示上限数を指定 (0:全件表示)
#  print_type  : オブジェクトの型情報を出力するか (bool)
#  print_len   : 配列, リストなどの長さを出力するか (bool)
#---------------------------------------------------------------------------
du.Tool.debug_print(data, print_limit=5, print_type=False, print_len=True)


#---------------------------------------------------------------------------
# 指定値切り捨て
#---------------------------------------------------------------------------
# [params]
#  value       : 切り捨てするオブジェクト (int, float, list, ndarray, Series, etc.)
#  round_base  : 切り捨てする基準値 (int)
# [return]
#  valueを切り捨てしたオブジェクト (エラーの場合はNoneを返す)
#---------------------------------------------------------------------------
ret = du.Tool.round_down(value, round_base=10)


#---------------------------------------------------------------------------
# 指定値切り上げ
#---------------------------------------------------------------------------
# [params]
#  value       : 切り上げするオブジェクト (int, float, list, ndarray, Series, etc.)
#  round_base  : 切り上げする基準値 (int)
# [return]
#  valueを切り上げしたオブジェクト (エラーの場合はNoneを返す)
#---------------------------------------------------------------------------
ret = du.Tool.round_up(value, round_base=10)


#---------------------------------------------------------------------------
# datetime変換
#---------------------------------------------------------------------------
# [params]
#  value : datetime変換するオブジェクト (str, list, ndarray, Series, etc.)
#  fmt   : 日付フォーマット (str) 省略可
# [return]
#  valueをdatetime変換したオブジェクト (エラーの場合はNoneを返す)
#---------------------------------------------------------------------------
dt = du.Tool.str_to_datetime(value)


#---------------------------------------------------------------------------
# unixtime変換
#---------------------------------------------------------------------------
# [params]
#  value : unixtime変換するオブジェクト (str, datetime, list, ndarray, Series, etc.)
# [return]
#  valueをunixtime変換したオブジェクト (エラーの場合は0を返す)
#---------------------------------------------------------------------------
dt = du.Tool.to_unixtime(value)


#---------------------------------------------------------------------------
# bybit状態取得
#---------------------------------------------------------------------------
# [params]
#  api_key / api_secret : API Key/SECRET
#  testnet              : 接続先(True:testnet, False:realnet)
#  symbol               : 取得対象の通貨ペアシンボル名（デフォルトは BTCUSD）
#---------------------------------------------------------------------------
api_key = 'your api key',
api_secret = 'your api secret'
du.Tool.print_status_from_bybit(api_key, api_secret, testnet=False, symbol='BTCUSD')


#---------------------------------------------------------------------------
# bybit 自注文約定履歴に損益計算を付加して取得
#---------------------------------------------------------------------------
# [params]
#  api_key / api_secret : API Key/Secret
#  testnet              : 接続先(True:testnet, False:realnet)
#  symbol               : 取得対象の通貨ペアシンボル名（デフォルトは BTCUSD）
#  from_ut              : 取得開始UnixTime
# [return]
#  指定期間内の自約定履歴DataFrame (エラーの場合はNoneを返す)
#---------------------------------------------------------------------------
api_key = 'your api key',
api_secret = 'your api secret'
from_ut = du.Tool.to_unixtime('2021/01/01 00:00:00')
df_execs = du.Tool.get_executions_from_bybit(api_key, api_secret, testnet=False, symbol='BTCUSD', from_ut=from_ut)


#---------------------------------------------------------------------------
# 複数DataFrameを外部結合
#---------------------------------------------------------------------------
# [params]
#  dfs         : 結合するDataFrameリスト
#  on_column   : key列名
#  join_column : 結合する列名
#  fillna      : 欠損値補間
#                 * None:しない
#                 * 数値     : 指定値で補間
#                 * 'ffill'  : 前の値で補間
#                 * 'bfill'  : 後の値で補間
#                 * 'linear' : 前後の値で線形補間
#  sort_index  : 結合したDataFrameをindexでソート(None:しない, True:昇順, False:降順)
#  is_summary  : 結合した列を合計(True:合計列のみ, False:各結合列)
# [return]
#  DataFrame
#---------------------------------------------------------------------------
dfs = [df1, df2, df3, df4, df5]
df_joined = du.Tool.outer_join_dfs(dfs, on_column='key_col', join_column='val_col', fillna=0, sort_index=True, is_summary=False)
```

## GitHub Gist
[DataUtilityの使い方](https://gist.github.com/nagishin/1677ffa401476e9e98191a04012ac189)
