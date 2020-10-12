# -*- coding: utf-8 -*-
import os
import time
import requests
import traceback
from datetime import datetime, timedelta
from pytz import utc, timezone
from collections import OrderedDict
import numpy as np
import pandas as pd

class Tool(object):

    #---------------------------------------------------------------------------
    # bybit約定履歴を取得
    # (https://public.bybit.com/trading/:symbol/ より)
    #---------------------------------------------------------------------------
    # [params]
    #  start_ut / end_ut : UnixTimeで指定
    #                      取得可能期間 : 2019-10-01以降かつ前日まで
    #  symbol            : 取得対象の通貨ペアシンボル名（デフォルトは BTCUSD）
    #  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
    #                      ファイルがない or 期間を満たしていない場合はrequestで取得
    #                      csvファイル保存 (None or 空文字は保存しない)
    # [return]
    #  DataFrame columns=['unixtime', 'side', 'size', 'price']
    #---------------------------------------------------------------------------
    @classmethod
    def get_trades_from_bybit(cls, start_ut, end_ut, symbol='BTCUSD', csv_path='./bybit_trades.csv'):
        if ((csv_path is not None) and (len(csv_path) > 0)):
            if os.path.isfile(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    if len(df.index) > 0:
                        ut = df['unixtime'].values
                        if ((start_ut >= ut[0]) & (end_ut <= ut[-1])):
                            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] <= end_ut))]
                            df.reset_index(drop=True, inplace=True)
                            print('trades from csv.')
                            return df
                except Exception:
                    pass

        start_utc = datetime.utcfromtimestamp(start_ut)
        end_utc = datetime.utcfromtimestamp(end_ut)
        from_dt = datetime(start_utc.year, start_utc.month, start_utc.day)
        to_dt = datetime(end_utc.year, end_utc.month, end_utc.day)
        df_concat = None
        cur_dt = from_dt
        while cur_dt <= to_dt:
            try:
                df = pd.read_csv(f'https://public.bybit.com/trading/{symbol}/{symbol}{cur_dt:%Y-%m-%d}.csv.gz',
                                 compression='gzip',
                                 usecols=['timestamp', 'side', 'price', 'size'],
                                 dtype={'timestamp':'float', 'side':'str', 'price':'float', 'size':'int'})
            except Exception:
                cur_dt += timedelta(days=1)
                continue

            df.rename(columns={'timestamp': 'unixtime'}, inplace=True)
            if df is not None and len(df.index) > 0:
                if df_concat is None:
                    df_concat = df
                else:
                    df_concat = pd.concat([df_concat, df])
            cur_dt += timedelta(days=1)

        if df_concat is None:
            return None
        if len(df_concat.index) < 1:
            return df_concat

        df_concat.sort_values(by='unixtime', ascending=True, inplace=True)
        df_concat.reset_index(drop=True, inplace=True)

        if ((csv_path is not None) and (len(csv_path) > 0)):
            csv_dir = os.path.dirname(csv_path)
            if not os.path.exists(csv_dir):
                os.makedirs(csv_dir)
            df_concat.to_csv(csv_path, header=True, index=False)

        df_concat = df_concat[((df_concat['unixtime'] >= start_ut) & (df_concat['unixtime'] <= end_ut))]

        print('trades from request.')
        return df_concat

    #---------------------------------------------------------------------------
    # BitMEX OHLCVを取得
    # (取得件数:1万/requestとなるため, 大量取得時はRateLimit注意)
    #---------------------------------------------------------------------------
    # [params]
    #  start_ut / end_ut : UnixTimeで指定
    #  period            : 分を指定
    #  symbol            : 取得対象の通貨ペアシンボル名（デフォルトは XBTUSD）
    #  csv_path          : 該当ファイルがあれば読み込んで対象期間をチェック
    #                      ファイルがない or 期間を満たしていない場合はrequestで取得
    #                      csvファイル保存 (None or 空文字は保存しない)
    #  request_interval  : 複数request時のsleep時間(sec)
    # [return]
    #  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
    #---------------------------------------------------------------------------
    @classmethod
    def get_ohlcv_from_bitmex(cls, start_ut, end_ut, period=1, symbol='XBTUSD', csv_path='./bitmex_ohlcv.csv', request_interval=0.5):
        if ((csv_path is not None) and (len(csv_path) > 0)):
            if os.path.isfile(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    if len(df.index) > 0:
                        ut = df['unixtime'].values
                        p = ut[1] - ut[0]
                        if ((start_ut >= ut[0]) & (end_ut <= ut[-1]) & (p == period * 60)):
                            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] <= end_ut))]
                            df.reset_index(drop=True, inplace=True)
                            print('ohlcv from csv.')
                            return df
                except Exception:
                    pass

        url = 'https://www.bitmex.com/api/udf/history'
        params = {
            'symbol': symbol,
            'resolution': str(period),
        }

        t=[]; o=[]; h=[]; l=[]; c=[]; v=[];
        cur_time = start_ut
        add_time = period * 60 * 10000
        retry_count = 0
        while cur_time < end_ut:
            try:
                to_time = min(cur_time + add_time, end_ut)
                params['from'] = cur_time
                params['to'] = to_time
                res = requests.get(url, params, timeout=10)
                res.raise_for_status()
                d = res.json()
                t += d['t']; o += d['o']; h += d['h']; l += d['l']; c += d['c']; v += d['v'];
                cur_time = to_time + (period * 60 + 1)
                time.sleep(request_interval)
            except Exception as e:
                print(f'Get ohlcv failed.(retry:{retry_count})\n{traceback.format_exc()}')
                if retry_count > 5:
                    raise e
                retry_count += 1
                time.sleep(2)
                continue

        df = pd.DataFrame(
            OrderedDict(unixtime=t, open=o, high=h, low=l, close=c, volume=v)
        )
        df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] <= end_ut))]
        if len(df.index) == 0:
            return df
        df.reset_index(drop=True, inplace=True)

        if ((csv_path is not None) and (len(csv_path) > 0)):
            csv_dir = os.path.dirname(csv_path)
            if not os.path.exists(csv_dir):
                os.makedirs(csv_dir)
            df.to_csv(csv_path, header=True, index=False)

        print('ohlcv from request.')
        return df

    #---------------------------------------------------------------------------
    # 約定履歴をOHLCVにリサンプリング
    #---------------------------------------------------------------------------
    # [params]
    #  df     : DateTimeIndexとprice,size列を含むDataFrame
    #  period : リサンプルするタイムフレーム ex) '1S'(秒), '5T'(分), '4H'(時), '1D'(日)
    # [return]
    #  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
    #---------------------------------------------------------------------------
    @classmethod
    def trade_to_ohlcv(cls, df, period):
        df_org = df.copy()
        if type(df_org.index) is not pd.core.indexes.datetimes.DatetimeIndex:
            cls.set_unixtime_to_dateindex(df_org)

        df_ohlcv = df_org.resample(period).agg({
                            'price' : 'ohlc',
                            'size'  : 'sum',}).ffill()
        df_ohlcv.columns = ['open', 'high', 'low', 'close', 'volume']
        df_ohlcv['unixtime'] = df_ohlcv.index.astype(np.int64) / 10**9
        df_ohlcv['unixtime'] = df_ohlcv.unixtime.astype(np.int64)
        df_ohlcv = df_ohlcv[['unixtime', 'open', 'high', 'low', 'close', 'volume']]
        return df_ohlcv

    #---------------------------------------------------------------------------
    # OHLCVを上位時間足にリサンプリング
    #---------------------------------------------------------------------------
    # [params]
    #  df     : DateTimeIndexとopen,high,low,close,volume列を含むDataFrame
    #  period : リサンプルするタイムフレーム ex) '1S'(秒), '5T'(分), '4H'(時), '1D'(日)
    # [return]
    #  DataFrame columns=['unixtime', 'open', 'high', 'low', 'close', 'volume']
    #---------------------------------------------------------------------------
    @classmethod
    def downsample_ohlcv(cls, df, period):
        df_org = df.copy()
        if type(df_org.index) is not pd.core.indexes.datetimes.DatetimeIndex:
            cls.set_unixtime_to_dateindex(df_org)

        df_ohlcv = df_org.resample(period).agg({
                            'open'   : 'first',
                            'high'   : 'max',
                            'low'    : 'min',
                            'close'  : 'last',
                            'volume' : 'sum',})
        df_ohlcv['unixtime'] = df_ohlcv.index.astype(np.int64) / 10**9
        df_ohlcv['unixtime'] = df_ohlcv.unixtime.astype(np.int64)
        df_ohlcv = df_ohlcv[['unixtime', 'open', 'high', 'low', 'close', 'volume']]
        return df_ohlcv

    #---------------------------------------------------------------------------
    # DataFrameのunixtime列からDateTimeIndexを設定
    #---------------------------------------------------------------------------
    # [params]
    #  df : unixtime(sec)列を含むDataFrame
    #---------------------------------------------------------------------------
    @classmethod
    def set_unixtime_to_dateindex(cls, df):
        df['datetime'] = pd.to_datetime(df['unixtime'], unit='s', utc=True)
        df.set_index('datetime', inplace=True)

    #---------------------------------------------------------------------------
    # DataFrameの行を指定列の値範囲で絞り込み
    #---------------------------------------------------------------------------
    # [params]
    #  df        : column列を含むDataFrame
    #  column    : 絞り込み判定を行う列名
    #  min_value : 絞り込み下限値
    #  max_value : 絞り込み上限値
    #---------------------------------------------------------------------------
    @classmethod
    def filter_df(cls, df, column, min_value, max_value):
        if not column in df.columns:
            print(f'DataFrame columns is not exist {column}.')
            return
        return df[((df[column] >= min_value) & (df[column] <= max_value))]

    #---------------------------------------------------------------------------
    # DataFrameを結合
    #---------------------------------------------------------------------------
    # [params]
    #  concat_dfs  : 結合するDataFrameリスト
    #  sort_column : 結合後にソートする列名
    #---------------------------------------------------------------------------
    @classmethod
    def concat_df(cls, concat_dfs, sort_column=None):
        if len(concat_dfs) < 2:
            print(f'Concat DataFrame is not exist.')
            return None
        if not sort_column in concat_dfs[0].columns:
            print(f'DataFrame columns is not exist {sort_column}.')
            return
        df_concat = pd.concat(concat_dfs)
        if sort_column is not None:
            df_concat.sort_values(by=sort_column, ascending=True, inplace=True)
        df_concat.reset_index(drop=True, inplace=True)
        return df_concat
