# -*- coding: utf-8 -*-
import os
import time
import requests
import json
import traceback
import glob
from datetime import datetime, timedelta
from pytz import utc, timezone
from collections import OrderedDict
import numpy as np
import pandas as pd
from inspect import currentframe
import pybybit
from itertools import groupby
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

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
    def get_trades_from_bybit(cls, start_ut, end_ut, symbol='BTCUSD', csv_path=None):
        if csv_path is None:
            csv_path = f'./bybit_{symbol}_trades.csv'
        if ((csv_path is not None) and (len(csv_path) > 0)):
            if os.path.isfile(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    if len(df.index) > 0:
                        ut = df['unixtime'].values
                        if ((start_ut >= ut[0]) & (end_ut <= ut[-1])):
                            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] < end_ut))]
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

        df_concat = df_concat[((df_concat['unixtime'] >= start_ut) & (df_concat['unixtime'] < end_ut))]

        print('trades from request.')
        return df_concat

    #---------------------------------------------------------------------------
    # BitMEX OHLCVを取得
    # (取得件数:1万/requestとなるため, 大量取得時はRateLimit注意)
    #---------------------------------------------------------------------------
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
    #---------------------------------------------------------------------------
    @classmethod
    def get_ohlcv_from_bitmex(cls, start_ut, end_ut, period=1, symbol='XBTUSD', csv_path=None, request_interval=0.5):
        df = None
        len_csv = 0
        if csv_path is None:
            csv_path = f'./bitmex_{symbol}_ohlcv_{period}.csv'
        if ((csv_path is not None) and (len(csv_path) > 0)):
            if os.path.isfile(csv_path):
                try:
                    # csv読み込み
                    df = pd.read_csv(csv_path)
                    len_csv = len(df.index)
                    if len_csv > 1:
                        ut = df['unixtime'].values
                        p = ut[1] - ut[0]
                        print(f'read csv: {ut[0]} - {ut[-1]} (len={len(ut)})')
                        # period判定
                        if p == period * 60:
                            lst_df = []
                            # csv先頭よりも開始日が過去の場合は不足分を取得
                            if start_ut < ut[0]:
                                lst_df.append(
                                    cls.__request_ohlcv_from_bitmex(start_ut, ut[0], period, symbol, request_interval)
                                )
                            lst_df.append(df)
                            # csv末尾よりも終了日が未来の場合は不足分を取得
                            if end_ut > ut[-1]:
                                lst_df.append(
                                    cls.__request_ohlcv_from_bitmex(ut[-1], end_ut, period, symbol, request_interval)
                                )
                            # DataFrame結合＆unixtimeソート
                            df = cls.concat_df(lst_df, sort_column='unixtime')
                            # 重複行削除
                            df.drop_duplicates(keep='first', subset='unixtime', inplace=True)
                            # 指定範囲フィルタリング
                            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] < end_ut))]
                            # indexリセット
                            df.reset_index(drop=True, inplace=True)
                except Exception:
                    pass

        if df is None or len(df.index) < 1:
            try:
                df = cls.__request_ohlcv_from_bitmex(start_ut, end_ut, period, symbol, request_interval)
            except Exception:
                pass

        # 読み込んだcsvよりデータが増えている場合はcsv保存
        ut = df['unixtime'].values
        if len(df.index) > len_csv:
            if ((csv_path is not None) and (len(csv_path) > 0)):
                csv_dir = os.path.dirname(csv_path)
                if not os.path.exists(csv_dir):
                    os.makedirs(csv_dir)
                df.to_csv(csv_path, header=True, index=False)
                print(f'save csv: {ut[0]} - {ut[-1]} (len={len(ut)})')

        print(f'get  df : {ut[0]} - {ut[-1]} (len={len(ut)})')
        return df

    @classmethod
    def __request_ohlcv_from_bitmex(cls, start_ut, end_ut, period=1, symbol='XBTUSD', request_interval=0.5):
        url = 'https://www.bitmex.com/api/udf/history'
        params = {
            'symbol': symbol,
            'resolution': str(period),
        }

        t=[]; o=[]; h=[]; l=[]; c=[]; v=[]
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
                t += d['t']; o += d['o']; h += d['h']; l += d['l']; c += d['c']; v += d['v']
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
        df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] < end_ut))]
        if len(df.index) > 0:
            df.reset_index(drop=True, inplace=True)
        return df

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
    @classmethod
    def get_ohlcv_from_bybit(cls, start_ut, end_ut, period=1, symbol='BTCUSD', csv_path=None, request_interval=1.0, ohlcv_kind='default'):
        df = None
        len_csv = 0
        if csv_path is None:
            csv_path = f'./bybit_{symbol}_ohlcv_{period}_{ohlcv_kind}.csv'
        if ((csv_path is not None) and (len(csv_path) > 0)):
            if os.path.isfile(csv_path):
                try:
                    # csv読み込み
                    df = pd.read_csv(csv_path)
                    len_csv = len(df.index)
                    if len_csv > 1:
                        ut = df['unixtime'].values
                        p = ut[1] - ut[0]
                        print(f'read csv: {ut[0]} - {ut[-1]} (len={len(ut)})')
                        # period判定
                        if p == period * 60:
                            lst_df = []
                            # csv先頭よりも開始日が過去の場合は不足分を取得
                            if start_ut < ut[0]:
                                lst_df.append(
                                    cls.__request_ohlcv_from_bybit(start_ut, ut[0], period, symbol, request_interval, ohlcv_kind)
                                )
                            lst_df.append(df)
                            # csv末尾よりも終了日が未来の場合は不足分を取得
                            if end_ut > ut[-1]:
                                lst_df.append(
                                    cls.__request_ohlcv_from_bybit(ut[-1], end_ut, period, symbol, request_interval, ohlcv_kind)
                                )
                            # DataFrame結合＆unixtimeソート
                            df = cls.concat_df(lst_df, sort_column='unixtime')
                            # 重複行削除
                            df.drop_duplicates(keep='first', subset='unixtime', inplace=True)
                            # 指定範囲フィルタリング
                            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] < end_ut))]
                            # indexリセット
                            df.reset_index(drop=True, inplace=True)
                except Exception:
                    pass

        if df is None or len(df.index) < 1:
            try:
                df = cls.__request_ohlcv_from_bybit(start_ut, end_ut, period, symbol, request_interval, ohlcv_kind)
            except Exception as e:
                pass

        # 読み込んだcsvよりデータが増えている場合はcsv保存
        ut = df['unixtime'].values
        if len(df.index) > len_csv:
            if ((csv_path is not None) and (len(csv_path) > 0)):
                csv_dir = os.path.dirname(csv_path)
                if not os.path.exists(csv_dir):
                    os.makedirs(csv_dir)
                df.to_csv(csv_path, header=True, index=False)
                print(f'save csv: {ut[0]} - {ut[-1]} (len={len(ut)})')

        print(f'get  df : {ut[0]} - {ut[-1]} (len={len(ut)})')
        return df

    @classmethod
    def __request_ohlcv_from_bybit(cls, start_ut, end_ut, period=1, symbol='BTCUSD', request_interval=1.0, ohlcv_kind='default'):
        url_kind = {
            'default': 'https://api.bybit.com/v2/public/kline/list',
            'mark':    'https://api.bybit.com/v2/public/mark-price-kline',
            'index':   'https://api.bybit.com/v2/public/index-price-kline',
            'premium': 'https://api.bybit.com/v2/public/premium-index-kline',
        }
        url = url_kind[ohlcv_kind]
        params = {
            'symbol':symbol,
            'interval':str(period),
            'limit':200,
        }

        lst_ohlcv = []
        cur_time = start_ut
        add_time = int(period) * 60 * 200
        retry_count = 0
        while cur_time < end_ut:
            try:
                to_time = min(cur_time + add_time, end_ut)
                params['from'] = int(cur_time)
                res = requests.get(url, params, timeout=10)
                res.raise_for_status()
                result = res.json()['result']
                if ohlcv_kind == 'default':
                    lst = [[int(r['open_time']), float(r['open']), float(r['high']), float(r['low']), float(r['close']), int(r['volume'])] for r in result]
                elif ohlcv_kind == 'mark':
                    lst = [[int(r['start_at']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])] for r in result]
                else:
                    lst = [[int(r['open_time']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])] for r in result]
                lst_ohlcv += lst
                cur_time = to_time
                time.sleep(request_interval)
            except Exception as e:
                print(f'Get ohlcv failed.(retry:{retry_count})\n{traceback.format_exc()}')
                if retry_count > 5:
                    raise e
                retry_count += 1
                time.sleep(2)
                continue
        # DataFrame生成
        if ohlcv_kind == 'default':
            df = pd.DataFrame(lst_ohlcv, columns=['unixtime', 'open', 'high', 'low', 'close', 'volume'])
        else:
            df = pd.DataFrame(lst_ohlcv, columns=['unixtime', 'open', 'high', 'low', 'close'])
        if len(df.index) > 0:
            # unixtimeソート
            df.sort_values(by='unixtime', ascending=True, inplace=True)
            # 重複行削除
            df.drop_duplicates(keep='first', subset='unixtime', inplace=True)
            # 指定範囲フィルタリング
            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] < end_ut))]
            # indexリセット
            df.reset_index(drop=True, inplace=True)

        return df

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
    @classmethod
    def get_ohlcv_from_coinbase(cls, start_ut, end_ut, period=1, symbol='BTC-USD', csv_path=None, request_interval=0.2):
        df = None
        len_csv = 0
        if csv_path is None:
            csv_path = f'./coinbase_{symbol}_ohlcv_{period}.csv'
        if ((csv_path is not None) and (len(csv_path) > 0)):
            if os.path.isfile(csv_path):
                try:
                    # csv読み込み
                    df = pd.read_csv(csv_path)
                    len_csv = len(df.index)
                    if len_csv > 1:
                        ut = df['unixtime'].values
                        p = ut[1] - ut[0]
                        print(f'read csv: {ut[0]} - {ut[-1]} (len={len(ut)})')
                        # period判定
                        if p == period * 60:
                            lst_df = []
                            # csv先頭よりも開始日が過去の場合は不足分を取得
                            if start_ut < ut[0]:
                                lst_df.append(
                                    cls.__request_ohlcv_from_coinbase(start_ut, ut[0], period, symbol, request_interval)
                                )
                            lst_df.append(df)
                            # csv末尾よりも終了日が未来の場合は不足分を取得
                            if end_ut > ut[-1]:
                                lst_df.append(
                                    cls.__request_ohlcv_from_coinbase(ut[-1], end_ut, period, symbol, request_interval)
                                )
                            # DataFrame結合＆unixtimeソート
                            df = cls.concat_df(lst_df, sort_column='unixtime')
                            # 重複行削除
                            df.drop_duplicates(keep='first', subset='unixtime', inplace=True)
                            # 指定範囲フィルタリング
                            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] < end_ut))]
                            # indexリセット
                            df.reset_index(drop=True, inplace=True)
                except Exception:
                    pass

        if df is None or len(df.index) < 1:
            try:
                df = cls.__request_ohlcv_from_coinbase(start_ut, end_ut, period, symbol, request_interval)
            except Exception:
                pass

        # 読み込んだcsvよりデータが増えている場合はcsv保存
        ut = df['unixtime'].values
        if len(df.index) > len_csv:
            if ((csv_path is not None) and (len(csv_path) > 0)):
                csv_dir = os.path.dirname(csv_path)
                if not os.path.exists(csv_dir):
                    os.makedirs(csv_dir)
                df.to_csv(csv_path, header=True, index=False)
                print(f'save csv: {ut[0]} - {ut[-1]} (len={len(ut)})')

        print(f'get  df : {ut[0]} - {ut[-1]} (len={len(ut)})')
        return df

    @classmethod
    def __request_ohlcv_from_coinbase(cls, start_ut, end_ut, period=1, symbol='BTC-USD', request_interval=0.5):
        url = f'https://api.pro.coinbase.com/products/{symbol}/candles'
        params = {
            'granularity': str(int(period) * 60),
        }

        lst_ohlcv = []
        cur_time = start_ut - int(period) * 60
        add_time = int(period) * 60 * 300
        retry_count = 0
        while cur_time < end_ut:
            try:
                to_time = min(cur_time + add_time, end_ut)
                params['start'] = datetime.fromtimestamp(cur_time, utc).isoformat()
                params['end'] = datetime.fromtimestamp(to_time, utc).isoformat()
                res = requests.get(url, params, timeout=10)
                res.raise_for_status()
                d = res.json()
                lst_ohlcv += d
                cur_time = to_time
                time.sleep(request_interval)
            except Exception as e:
                print(f'Get ohlcv failed.(retry:{retry_count})\n{traceback.format_exc()}')
                if retry_count > 5:
                    raise e
                retry_count += 1
                time.sleep(2)
                continue
        # DataFrame生成
        df = pd.DataFrame(lst_ohlcv, columns=['unixtime', 'open', 'high', 'low', 'close', 'volume'])
        if len(df.index) > 0:
            # unixtimeソート
            df.sort_values(by='unixtime', ascending=True, inplace=True)
            # 重複行削除
            df.drop_duplicates(keep='first', subset='unixtime', inplace=True)
            # 指定範囲フィルタリング
            df = df[((df['unixtime'] >= start_ut) & (df['unixtime'] < end_ut))]
            # indexリセット
            df.reset_index(drop=True, inplace=True)

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

    #---------------------------------------------------------------------------
    # デバッグ用 オブジェクト整形出力
    #---------------------------------------------------------------------------
    # [params]
    #  data        : 表示するオブジェクト
    #  indent      : 配列, リスト要素などを表示するインデント (str)
    #  print_limit : 配列, リストなどの表示上限数を指定 (0:全件表示)
    #  print_type  : オブジェクトの型情報を出力するか (bool)
    #  print_len   : 配列, リストなどの長さを出力するか (bool)
    #---------------------------------------------------------------------------
    @classmethod
    def debug_print(cls, data: object, print_limit: int = 0, indent: str = '  ', print_type: bool = False, print_len: bool = True) -> None:
        if data is None:
            return

        name = {id(v):k for k,v in currentframe().f_back.f_locals.items()}.get(id(data), '???')
        key_str = f'{name} = '

        if isinstance(data, list):
            print(key_str)
            cls.__print_list(data, 0, indent, print_limit, print_type, print_len)
        elif isinstance(data, dict):
            print(key_str)
            cls.__print_dict(data, 0, indent, print_limit, print_type, print_len)
        elif isinstance(data, np.ndarray) or isinstance(data, pd.core.series.Series):
            print(key_str)
            cls.__print_array(data, 0, indent, print_limit, print_type, print_len)
        elif isinstance(data, pd.core.frame.DataFrame):
            print(key_str)
            cls.__print_df(data, 0, indent, print_limit, print_type, print_len)
        else:
            key_str += f'{repr(data)}'
            if print_type:
                key_str += f' (type = {type(data)})'
            print(key_str)

    @classmethod
    def __get_pre_print(cls, data: object, indent_count: int = 0, indent: str = '  ', print_limit: int = 0, print_type: bool = False, print_len: bool = True):
        if data is None:
            return

        ret = {}
        ret['top_indent'] = '' if indent_count < 1 else indent * indent_count

        ret['disp_count'] = 0
        data_length = 0
        if isinstance(data, list) or isinstance(data, np.ndarray) or isinstance(data, pd.core.series.Series) or isinstance(data, pd.core.frame.DataFrame):
            data_length = len(data)
            ret['disp_count'] = data_length if print_limit is None or print_limit == 0 else min(data_length, print_limit)

        tail_str = ''
        if print_type or (print_len and data_length > 0):
            tail_str += ' ('
            if print_type:
                tail_str += f'type = {type(data)}'
            if len(tail_str) > 3:
                tail_str += ', '
            if print_len:
                tail_str += f'len = {data_length}'
            tail_str += ')'
        ret['tail_str'] = tail_str

        return ret

    @classmethod
    def __print_list(cls, data: list, indent_count: int = 0, indent: str = '  ', print_limit: int = 0, print_type: bool = False, print_len: bool = True) -> None:
        if data is None:
            return
        if isinstance(data, list) == False:
            return

        info = cls.__get_pre_print(data, indent_count, indent, print_limit, print_type, print_len)
        disp_count = info['disp_count']
        top_indent = info['top_indent']
        tail_str = info['tail_str']

        print(f'{top_indent}[')

        for i in range(disp_count):
            if isinstance(data[i], list):
                cls.__print_list(data[i], indent_count+1, indent, print_limit, print_type, print_len)
            elif isinstance(data[i], dict):
                cls.__print_dict(data[i], indent_count+1, indent, print_limit, print_type, print_len)
            elif isinstance(data[i], np.ndarray) or isinstance(data[i], pd.core.series.Series):
                cls.__print_array(data[i], indent_count+1, indent, print_limit, print_type, print_len)
            elif isinstance(data[i], pd.core.frame.DataFrame):
                cls.__print_df(data[i], indent_count+1, indent, print_limit, print_type, print_len)
            else:
                print(top_indent + indent + repr(data[i]) + ',')

        if len(data) > disp_count:
            print(top_indent + indent + '...')

        print(f'{top_indent}],' + tail_str)

    @classmethod
    def __print_dict(cls, data: dict, indent_count: int = 0, indent: str = '  ', print_limit: int = 0, print_type: bool = False, print_len: bool = True) -> None:
        if data is None:
            return
        if isinstance(data, dict) == False:
            return

        info = cls.__get_pre_print(data, indent_count, indent, print_limit, print_type, print_len)
        disp_count = info['disp_count']
        top_indent = info['top_indent']
        tail_str = info['tail_str']

        print(top_indent + '{')

        for k,v in data.items():
            key_str = top_indent + indent + repr(k) + ' : '
            if isinstance(v, list):
                print(key_str)
                cls.__print_list(v, indent_count+1, indent, print_limit, print_type, print_len)
            elif isinstance(v, dict):
                print(key_str)
                cls.__print_dict(v, indent_count+1, indent, print_limit, print_type, print_len)
            elif isinstance(v, np.ndarray) or isinstance(v, pd.core.series.Series):
                print(key_str)
                cls.__print_array(v, indent_count+1, indent, print_limit, print_type, print_len)
            elif isinstance(v, pd.core.frame.DataFrame):
                print(key_str)
                cls.__print_df(v, indent_count+1, indent, print_limit, print_type, print_len)
            else:
                print(key_str + repr(v) + ',')

        print(top_indent + '},' + tail_str)

    @classmethod
    def __print_array(cls, data: object, indent_count: int = 0, indent: str = '  ', print_limit: int = 0, print_type: bool = False, print_len: bool = True) -> None:
        if data is None:
            return
        if isinstance(data, np.ndarray) == False and isinstance(data, pd.core.series.Series) == False:
            return

        info = cls.__get_pre_print(data, indent_count, indent, print_limit, print_type, print_len)
        disp_count = info['disp_count']
        top_indent = info['top_indent']
        tail_str = info['tail_str']

        print(repr(data[:disp_count]))
        if len(data) > disp_count:
            print('...')

        if len(tail_str) > 0:
            print(tail_str)

    @classmethod
    def __print_df(cls, data: object, indent_count: int = 0, indent: str = '  ', print_limit: int = 0, print_type: bool = False, print_len: bool = True) -> None:
        if data is None:
            return
        if isinstance(data, pd.core.frame.DataFrame) == False:
            return

        info = cls.__get_pre_print(data, indent_count, indent, print_limit, print_type, print_len)
        disp_count = info['disp_count']
        top_indent = info['top_indent']
        tail_str = info['tail_str']

        print(data.head(disp_count))
        if len(data.index) > disp_count:
            print('...')

        tail_str = ''
        if print_type or print_len:
            tail_str += '('
            if print_type:
                tail_str += f'type = {type(data)}'
            if print_len:
                tail_str += f', table = row:{len(data.index)} * col:{len(data.columns)}'
            tail_str += ')'
            print(tail_str)

    #---------------------------------------------------------------------------
    # 指定値切り捨て
    #---------------------------------------------------------------------------
    # [params]
    #  value       : 切り捨てするオブジェクト (int, float, list, ndarray, Series, etc.)
    #  round_base  : 切り捨てする基準値 (int)
    # [return]
    #  valueを切り捨てしたオブジェクト (エラーの場合はNoneを返す)
    #---------------------------------------------------------------------------
    @classmethod
    def round_down(cls, value: object, round_base: int) -> object:
        try:
            if isinstance(round_base, (int, float)) == False:
                return None
            if round_base < 1:
                return None
            round = int(round_base)

            if isinstance(value, (int, float)):
                return (int(value) // round) * round

            if isinstance(value, list):
                return [(int(v) // round) * round for v in value]

            if isinstance(value, np.ndarray):
                f = np.frompyfunc(lambda x, y: (int(x) // y) * y, 2, 1)
                return f(value, round)

            if isinstance(value, pd.core.series.Series):
                return value.map(lambda x: (int(x) // round) * round)

            if type(value) is pd.core.indexes.datetimes.DatetimeIndex:
                tz = value[0].tzinfo
                if tz is None:
                    return value.map(lambda x: datetime.utcfromtimestamp(x.value // (round * 10**9) * round))
                else:
                    return value.map(lambda x: datetime.fromtimestamp(x.value // (round * 10**9) * round, tz=tz))

            return None

        except Exception:
            return None

    #---------------------------------------------------------------------------
    # 指定値切り上げ
    #---------------------------------------------------------------------------
    # [params]
    #  value       : 切り上げするオブジェクト (int, float, list, ndarray, Series, etc.)
    #  round_base  : 切り上げする基準値 (int)
    # [return]
    #  valueを切り上げしたオブジェクト (エラーの場合はNoneを返す)
    #---------------------------------------------------------------------------
    @classmethod
    def round_up(cls, value: object, round_base: int) -> object:
        try:
            if isinstance(round_base, (int, float)) == False:
                return None
            if round_base < 1:
                return None
            round = int(round_base)

            if isinstance(value, (int, float)):
                return (int(value) // round) * round + round

            if isinstance(value, list):
                return [(int(v) // round) * round + round for v in value]

            if isinstance(value, np.ndarray):
                f = np.frompyfunc(lambda x, y: (int(x) // y) * y + y, 2, 1)
                return f(value, round)

            if isinstance(value, pd.core.series.Series):
                return value.map(lambda x: (int(x) // round) * round + round)

            if type(value) is pd.core.indexes.datetimes.DatetimeIndex:
                tz = value[0].tzinfo
                if tz is None:
                    return value.map(lambda x: datetime.utcfromtimestamp(x.value // (round * 10**9) * round + round))
                else:
                    return value.map(lambda x: datetime.fromtimestamp(x.value // (round * 10**9) * round + round, tz=tz))

            return None

        except Exception:
            return None

    #---------------------------------------------------------------------------
    # datetime変換
    #---------------------------------------------------------------------------
    # [params]
    #  value : datetime変換するオブジェクト (str, list, ndarray, Series, etc.)
    #  fmt   : 日付フォーマット (str) 省略可
    # [return]
    #  valueをdatetime変換したオブジェクト (エラーの場合はNoneを返す)
    #---------------------------------------------------------------------------
    @classmethod
    def str_to_datetime(cls, value: object, fmt: str = '%Y-%m-%dT%H:%M:%S.%fZ') -> object:
        try:
            if isinstance(fmt, str) == False or len(fmt) < 10:
                return None

            if type(value) is str:
                dt, ret_fmt = cls.__str_to_datetime(value, fmt)
                return dt

            if len(value) < 1:
                return None

            if isinstance(value, list) and isinstance(value[0], str):
                dt, ret_fmt = cls.__str_to_datetime(value[0], fmt)
                if dt == None:
                    return None
                return [cls.__str_to_datetime(v, ret_fmt)[0] for v in value]

            elif isinstance(value, np.ndarray) and isinstance(value[0], str):
                df = pd.DataFrame({'str_dt': value})
                df['datetime'] = pd.to_datetime(df['str_dt'])
                return df['datetime'].values

            elif isinstance(value, pd.core.indexes.base.Index):
                if isinstance(value[0], str):
                    return pd.to_datetime(value)
                if isinstance(value[0], datetime):
                    return value

            elif isinstance(value, pd.core.series.Series):
                if isinstance(value.iloc[0], str):
                    return pd.to_datetime(value)
                if isinstance(value.iloc[0], datetime):
                    return value

            return None

        except Exception:
            return None

    @classmethod
    def __str_to_datetime(cls, str_dt, fmt):
        try:
            cnv_str = str_dt
            cnv_fmt = fmt
            dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
            if dt != None:
                return dt, cnv_fmt

            if len(cnv_str) == 19:
                cnv_str = str_dt + '.000Z'
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_str = str_dt
                cnv_fmt = '%Y/%m/%d %H:%M:%S'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

            if len(cnv_str) == 24:
                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S%z'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_str = str_dt
                cnv_fmt = '%Y/%m/%d %H:%M:%S%z'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

            if len(cnv_str) > 24:
                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%f'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_fmt = '%Y/%m/%d %H:%M:%S.%f'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ%z'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_fmt = '%Y/%m/%d %H:%M:%S.%f%z'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

            if len(cnv_str) > 22:
                cnv_str = str_dt[:23]
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%f'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

                cnv_str = str_dt[:23]
                cnv_fmt = '%Y/%m/%d %H:%M:%S.%f'
                dt = cls.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt, cnv_fmt

        except Exception:
            return None, fmt

    @classmethod
    def __convert_str_to_dt(cls, str_dt, fmt):
        try:
            dt = datetime.strptime(str_dt, fmt)
            return dt
        except ValueError:
            pass
        return None

    #---------------------------------------------------------------------------
    # unixtime変換
    #---------------------------------------------------------------------------
    # [params]
    #  value : unixtime変換するオブジェクト (str, datetime, list, ndarray, Series, etc.)
    # [return]
    #  valueをunixtime変換したオブジェクト (エラーの場合は0を返す)
    #---------------------------------------------------------------------------
    @classmethod
    def to_unixtime(cls, value: object) -> object:
        try:
            if isinstance(value, str):
                dt = cls.str_to_datetime(value)
                if dt is None:
                    return 0
                return dt.timestamp()

            if isinstance(value, datetime):
                return value.timestamp()

            if isinstance(value, list):
                if isinstance(value[0], str):
                    dt = cls.str_to_datetime(value)
                    if dt is None:
                        return 0
                    return [d.timestamp() for d in dt]

                if isinstance(value[0], datetime):
                    return [d.timestamp() for d in value]

            if isinstance(value, np.ndarray):
                if isinstance(value[0], str):
                    dt = cls.str_to_datetime(value)
                    if dt is None:
                        return 0
                    return np.array([d.timestamp() for d in dt])

                if isinstance(value[0], datetime):
                    return np.array([d.timestamp() for d in value])

            if isinstance(value, pd.core.indexes.base.Index):
                if isinstance(value[0], str):
                    dt = cls.str_to_datetime(value)
                    if dt is None:
                        return 0
                    return dt.map(lambda x: x.timestamp())

                if isinstance(value[0], datetime):
                    return value.map(lambda x: x.timestamp())

            if isinstance(value, pd.core.series.Series):
                if isinstance(value.iloc[0], str):
                    dt = cls.str_to_datetime(value)
                    if dt is None:
                        return 0
                    return dt.map(lambda x: x.timestamp())

                if isinstance(value.iloc[0], datetime):
                    return value.map(lambda x: x.timestamp())

            if isinstance(value, pd.core.indexes.datetimes.DatetimeIndex) or \
               isinstance(value.iloc[0], pd._libs.tslib.Timestamp):
                return value.astype(np.int64) // 10**9

            return 0

        except Exception:
            return 0

    #---------------------------------------------------------------------------
    # bybit状態取得
    #---------------------------------------------------------------------------
    # [params]
    #  api_key / api_secret : API Key/SECRET
    #  testnet              : 接続先(True:testnet, False:realnet)
    #  symbol               : 取得対象の通貨ペアシンボル名（デフォルトは BTCUSD）
    #---------------------------------------------------------------------------
    @classmethod
    def print_status_from_bybit(cls, api_key: str, api_secret: str, testnet: bool=False, symbol: str='BTCUSD') -> None:
        try:
            # pybybit APIインスタンス生成
            api = [api_key, api_secret]
            bybit_api = pybybit.API(*api, testnet=testnet)
            # timestamp
            now_time = datetime.now(timezone('Asia/Tokyo')).strftime('%Y/%m/%d %H:%M:%S')
            msg = f'<STATUS> {symbol} {now_time}\n'

            # 価格
            tic = bybit_api.rest.inverse.public_tickers(symbol=symbol)
            tic = tic.json()['result']
            if len(tic) > 0:
                tic = tic[0]
                ltp = float(tic['last_price'])
                bid = float(tic['bid_price'])
                ask = float(tic['ask_price'])
                mark = float(tic['mark_price'])
                idx = float(tic['index_price'])
                vol = int(tic['volume_24h'])
                oi = int(tic['open_interest'])
                fr = float(tic['funding_rate'])
                msg += f'[price]\n'
                msg += f'  ltp        : {ltp:.1f}\n'
                msg += f'  bid        : {bid:.1f}\n'
                msg += f'  ask        : {ask:.1f}\n'
                msg += f'  mark       : {mark:.2f}\n'
                msg += f'  index      : {idx:.2f}\n'
                msg += f'  vol_24     : {vol:,}\n'
                msg += f'  oi         : {oi:,}\n'
                msg += f'  fr         : {fr:.4%}\n'

            # 残高&ポジション
            pos = bybit_api.rest.inverse.private_position_list(symbol=symbol)
            pos = pos.json()['result']
            wlt = float(pos['wallet_balance'])
            side = pos['side']
            size = int(pos['size'])
            margin = float(pos['position_margin'])
            entry = float(pos['entry_price'])
            sl = float(pos['stop_loss'])
            tp = float(pos['take_profit'])
            ts = float(pos['trailing_stop'])
            liq = float(pos['liq_price'])
            lvr = float(pos['effective_leverage'])
            pnl = float(pos['unrealised_pnl'])
            used = margin + float(pos['occ_closing_fee']) + float(pos['occ_funding_fee']) - pnl
            avl = wlt - used
            price_pnl = 0
            if pos['side'] == 'Buy':
                price_pnl = ltp - entry
            elif pos['side'] == 'Sell':
                price_pnl = entry - ltp
            msg += f'[position]\n'
            msg += f'  side       : {side}\n'
            msg += f'  size       : {size:,} ({margin:.8f})\n'
            msg += f'  avr_entry  : {entry:.2f}' + f' ({price_pnl:+.2f})\n'
            msg += f'  stop_loss  : {sl:.1f}\n'
            msg += f'  take_profit: {tp:.1f}\n'
            msg += f'  trailing   : {ts:.1f}\n'
            msg += f'  liq_price  : {liq:.1f}\n'
            msg += f'  unrealised : {pnl:.8f}\n'
            msg += f'  leverage   : {lvr:.2f}\n'
            msg += f'[balance]\n'
            msg += f'  wallet     : {wlt:.8f}\n'
            msg += f'  available  : {avl:.8f}\n'

            # オープンオーダー
            odr = bybit_api.rest.inverse.private_order_list(symbol=symbol, order_status='New,PartiallyFilled')
            odr = odr.json()['result']
            if 'data' in odr and len(odr['data']) > 0:
                msg += f'[open order]\n'

            for o in odr['data']:
                if o['order_status'] == 'New':
                    os = '[New    ]:'
                elif o['order_status'] == 'PartiallyFilled':
                    os = '[Partial]:'
                else:
                    os = '[Other  ]:'
                price = float(o['price'])
                qty = int(o['qty'])
                cum = int(o['cum_exec_qty'])
                msg += '  ' + os + o['order_type'] + o['side'] + f'  [price]:{price:.1f}  [qty]:{cum}/{qty}'

                utc_dt = datetime.datetime.strptime(o['updated_at'] + '+0000', '%Y-%m-%dT%H:%M:%S.%fZ%z')
                jst_dt = utc_dt.astimezone(timezone('Asia/Tokyo'))
                msg += '  [time]:' + jst_dt.strftime('%Y/%m/%d %H:%M:%S')

                opt = ''
                if 'time_in_force' in o and len(o['time_in_force']) > 0:
                    opt += o['time_in_force']
                if 'ext_fields' in o and 'reduce_only' in o['ext_fields'] and o['ext_fields']['reduce_only']:
                    if len(opt) > 0:
                        opt += ','
                    opt += 'ReduceOnly'
                if len(opt) > 0:
                    msg += '  [option]:' + opt
                msg += '\n'
            print(msg)

        except Exception as e:
            raise Exception('get_status failed.' + str(e))

    #---------------------------------------------------------------------------
    # bybit 自注文約定履歴に損益計算を付加して取得
    #---------------------------------------------------------------------------
    # [params]
    #  api_key / api_secret : API Key/Secret
    #  testnet              : 接続先(True:testnet, False:realnet)
    #  symbol               : 取得対象の通貨ペアシンボル名（デフォルトは BTCUSD）
    #  from_ut              : 取得開始UnixTime
    #  buffer_days          : from_utより遡る日数 (デフォルトは 7 days)
    #                       ※ 損益計算の起点(ポジション=0 or ドテン)を求めるため
    # [return]
    #  指定期間内の自約定履歴DataFrame (エラーの場合はNoneを返す)
    #---------------------------------------------------------------------------
    @classmethod
    def get_executions_from_bybit(cls, api_key: str, api_secret: str, testnet: bool = False, symbol: str = 'BTCUSD', from_ut: int = 0, buffer_days: int = 7) -> pd.DataFrame:
        try:
            # pybybit APIインスタンス生成
            api = [api_key, api_secret]
            bybit_api = pybybit.API(*api, testnet=testnet)

            get_start = 0  # 期間内の取得開始レコード
            lst_execs = [] # 取得した約定履歴リスト
            while True:
                try:
                    ret = bybit_api.rest.inverse.private_execution_list(symbol=symbol, start_time=int(from_ut) - 86400 * buffer_days, page=get_start, limit=200)
                    ret = ret.json()
                    rl_status = int(ret['rate_limit_status'])
                    rl_reset = float(ret['rate_limit_reset_ms']) / 1000
                    rl_limit = int(ret['rate_limit'])
                    execs = ret['result']

                    if not ('trade_list' in execs):
                        break
                    execs = execs['trade_list']
                    if execs == None or len(execs) < 1:
                        break

                    lst = [[e['exec_id'], e['exec_time'], e['exec_type'], e['order_type'], e['side'], e['exec_price'], e['exec_qty'], e['exec_value'], e['fee_rate'], e['exec_fee']] for e in execs]
                    lst_execs += lst

                    msg = 'Success API request. last:{} execs:{} RateLimit:{}/{} Reset:{}'.format(lst_execs[-1][1], len(lst_execs), rl_status, rl_limit, rl_reset)
                    print(msg)

                    get_start += 1

                    # 安全のため、リクエスト可能数が5より小さくなったら10秒間sleep
                    if rl_status < 5:
                        to_sleep = 10
                        msg = f'Wait {to_sleep}[sec] for RateLimit...'
                        print(msg)
                        time.sleep(to_sleep)
                    else:
                        time.sleep(0.5)

                except Exception as e:
                    raise Exception(e)

            # DataDrame生成
            df_execs = pd.DataFrame(lst_execs, columns=['exec_id', 'exec_time', 'exec_type', 'order_type', 'side', 'exec_price', 'exec_qty', 'exec_value', 'fee_rate', 'exec_fee'])
            df_execs['exec_time'] = df_execs['exec_time'].astype(float)
            df_execs['exec_price'] = df_execs['exec_price'].astype(float)
            df_execs['exec_qty'] = df_execs['exec_qty'].astype(int)
            df_execs['exec_value'] = df_execs['exec_value'].astype(float)
            df_execs['fee_rate'] = df_execs['fee_rate'].astype(float)
            df_execs['exec_fee'] = df_execs['exec_fee'].astype(float)
            # exec_time昇順ソート
            df_execs.sort_values(by='exec_time', ascending=True, inplace=True)
            # 重複行削除
            df_execs.drop_duplicates(keep='last', inplace=True)
            df_execs.reset_index(drop=True, inplace=True)

            # ポジション取得
            pos = bybit_api.rest.inverse.private_position_list(symbol=symbol)
            pos = pos.json()['result']
            side = pos['side']
            size = int(pos['size'])
            cur_size = size if side == 'Buy' else - size
            # 残高取得
            cur_bal = float(pos['wallet_balance'])

            # 現在のポジションと約定履歴よりポジション推移計算
            calc_pos = np.where(df_execs['exec_type'] == 'Trade', df_execs['exec_qty'], 0)
            calc_pos = calc_pos * np.where(df_execs['side']=='Sell', 1, -1)
            # 現在のポジションを追加し、反転して累積和を計算
            calc_pos = np.append(calc_pos, [cur_size])
            calc_pos = calc_pos[::-1]
            calc_pos = calc_pos.cumsum()
            calc_pos = calc_pos[::-1]
            calc_pos = calc_pos[:-1]
            calc_pos = np.round(calc_pos, 8)
            df_execs['sum_size'] = calc_pos

            # from以前でノーポジション or ドテンを検出して集計基準とする
            pre_idx = 0
            pre_idxes = np.where(df_execs['exec_time'] <= from_ut)[0]
            if len(pre_idxes) > 0:
                pre_idx = max(pre_idxes)

            base_idx = -1
            base_pos = 0
            base_avr = 0
            for i in range(pre_idx, -1, -1):
                if calc_pos[i] == 0.0:
                    base_idx = i
                    break
                if i > 0 and calc_pos[i] * calc_pos[i-1] < 0.0:
                    base_idx = i
                    base_pos = calc_pos[i]
                    base_avr = df_execs['price'].values[i]
                    break

            if base_idx < 0:
                print(f'Base position not found {buffer_days} days before the from_ut.')

            # 集計基準から約定履歴を判定し、ポジション推移を求める
            df_execs = df_execs.iloc[base_idx:, :]
            df_execs.reset_index(drop=True, inplace=True)

            # 約定履歴より損益推移計算
            lst_exec_pl  = []
            lst_exec_fee = []
            lst_pl       = []
            lst_sum_size = []
            lst_avr_cost = []
            exec_pl  = 0
            exec_fee = 0
            pl       = 0
            sum_size = base_pos
            avr_cost = base_avr
            np_type  = df_execs['exec_type'].values
            np_side  = df_execs['side'].values
            np_size  = df_execs['exec_qty'].values
            np_cost  = df_execs['exec_value'].values
            np_fee   = df_execs['exec_fee'].values

            for i in range(df_execs.shape[0]):
                i_size = int(np_size[i])
                i_cost = float(np_cost[i])
                i_fee = float(np_fee[i])

                # Fundingの場合
                if np_type[i] == 'Funding':
                    # 手数料計算
                    exec_fee = -i_fee
                    pl = -i_fee

                # Tradeの場合
                else:
                    # 建玉積み増し
                    if sum_size == 0.0 or \
                        (sum_size > 0.0 and np_side[i] == 'Buy') or \
                        (sum_size < 0.0 and np_side[i] == 'Sell'):
                        temp_value = avr_cost * sum_size
                        if np_side[i] == 'Buy':
                            temp_value += i_cost
                            # 建玉更新
                            sum_size += i_size
                        else:
                            temp_value -= i_cost
                            # 建玉更新
                            sum_size -= i_size
                        # 平均コスト更新
                        avr_cost = abs(temp_value / sum_size)
                        # 手数料計算
                        exec_fee = -i_fee
                        pl = -i_fee

                    # 決済
                    else:
                        cost = abs(i_cost / i_size)
                        pl_cost = cost - avr_cost if np_side[i] == 'Buy' else avr_cost - cost
                        pl_size = i_size if i_size <= abs(sum_size) else abs(sum_size)
                        # PL
                        exec_pl = pl_cost * pl_size
                        pl = pl_cost * pl_size
                        # 手数料計算
                        exec_fee = -i_fee
                        pl -= i_fee

                        # 建玉更新
                        sum_size += i_size if np_side[i] == 'Buy' else -i_size
                        # ドテンの場合、平均コスト更新
                        if (sum_size > 0.0 and np_side[i] == 'Buy') or \
                            (sum_size < 0.0 and np_side[i] == 'Sell'):
                            # 平均コスト更新
                            avr_cost = cost

                lst_sum_size.append(sum_size)
                lst_avr_cost.append(avr_cost)
                lst_exec_pl.append(exec_pl)
                lst_exec_fee.append(exec_fee)
                lst_pl.append(pl)

            df_execs['pos_size'] = lst_sum_size
            df_execs['val_per_qty'] = lst_avr_cost
            df_execs['exec_pl'] = lst_exec_pl
            df_execs['exec_fee'] = lst_exec_fee
            df_execs['total_pl'] = lst_pl

            df_execs['sum_exec_pl'] = np.cumsum(df_execs['exec_pl'].values)
            df_execs['sum_exec_fee'] = np.cumsum(df_execs['exec_fee'].values)
            df_execs['sum_total_pl'] = np.cumsum(df_execs['total_pl'].values)

            start_bal = cur_bal - df_execs['sum_total_pl'].values[-1]
            df_execs['balance'] = df_execs['sum_total_pl'].values + start_bal
            df_execs['fiat_balance'] = df_execs['balance'].values * df_execs['exec_price'].values
            np_fiat = df_execs['fiat_balance'].values
            np_temp = np.append(np_fiat, np_fiat[-1])
            np_temp = np.diff(np_temp)
            df_execs['fiat_pl'] = np.roll(np_temp, shift=1)
            df_execs['sum_fiat_pl'] = np.cumsum(df_execs['fiat_pl'].values)

            df_execs = df_execs[
                ['exec_time', 'exec_type', 'order_type', 'side', 'exec_price', 'exec_qty', 'exec_value', 'fee_rate', 'exec_fee',
                 'pos_size', 'val_per_qty', 'exec_pl', 'exec_fee', 'total_pl',
                 'balance', 'fiat_balance', 'fiat_pl',
                 'sum_exec_pl', 'sum_exec_fee', 'sum_total_pl', 'sum_fiat_pl']]
            df_execs = df_execs[(df_execs['exec_time'] >= from_ut)]
            df_execs.reset_index(drop=True, inplace=True)
            df_execs['datetime'] = pd.to_datetime(df_execs['exec_time'].astype(float), unit='s', utc=True)
            df_execs = df_execs.set_index('datetime')
            df_execs.index = df_execs.index.tz_convert('Asia/Tokyo')

            # 統計情報算出
            start_dt = datetime.fromtimestamp(from_ut, tz=timezone('Asia/Tokyo'))
            end_dt = datetime.fromtimestamp(time.time(), tz=timezone('Asia/Tokyo'))
            print(f'[Execs period   ]  {start_dt:%Y/%m/%d %H:%M:%S} - {end_dt:%Y/%m/%d %H:%M:%S}\n')
            cls.__print_execution_info(df_execs, fiat_basis=False)
            cls.__print_execution_info(df_execs, fiat_basis=True)

            return df_execs

        except Exception as e:
            print('get_status failed.' + str(e))

        return None

    #---------------------------------------------------------------------------
    # 統計情報算出
    #---------------------------------------------------------------------------
    @classmethod
    def __print_execution_info(cls, df_execs: pd.DataFrame, fiat_basis=False) -> None:
        try:
            trades_info = {
                'trades' : {
                    'count'        : 0, # 総取引回数
                    'pf'           : 0, # PF
                    'sum'          : 0, # 総損益
                    'mean'         : 0, # 平均損益
                    'maxdd'        : 0, # 最大DD
                    'maxdd_ratio'  : 0, # 最大DD率
                    'maxdd_ut'     : 0, # 最大DD UnixTime
                    'sum_size'     : 0, # 総取引高
                },
                'profit' : {
                    'count'        : 0, # 勝取引数
                    'sum'          : 0, # 総利益
                    'max'          : 0, # 最大利益(1取引あたり)
                    'mean'         : 0, # 平均利益
                    'maxlen_count' : 0, # 最大連勝数
                    'maxlen_sum'   : 0, # 最大連勝利益
                },
                'loss' : {
                    'count'        : 0, # 負取引数
                    'sum'          : 0, # 総損失
                    'max'          : 0, # 最大損失(1取引あたり)
                    'mean'         : 0, # 平均損失
                    'maxlen_count' : 0, # 最大連敗数
                    'maxlen_sum'   : 0, # 最大連敗損失
                },
                'fee' : {
                    'trade'        : 0, # 総取引手数料
                    'funding'      : 0, # 総ファンディング手数料
                },
            }

            if df_execs is None or len(df_execs) < 1:
                print('execution is not exists.')
                return

            t = trades_info['trades']
            p = trades_info['profit']
            l = trades_info['loss']
            f = trades_info['fee']

            # 約定履歴を分類
            df_ex = df_execs[df_execs['exec_type'] != 'Funding'].copy()
            df_fr = df_execs[df_execs['exec_type'] == 'Funding'].copy()

            if fiat_basis == True:
                np_pnl = df_ex['fiat_pl'].values
                np_profit = np_pnl[np_pnl > 0]
                np_loss = np_pnl[np_pnl < 0]
                np_ut = df_ex['exec_time'].values
                np_fr = np.zeros(1, dtype=int)
                np_fee = np.zeros(1, dtype=int)
                np_size = np.zeros(1, dtype=int)
            else:
                np_pnl = df_ex['total_pl'].values
                np_profit = np_pnl[np_pnl > 0]
                np_loss = np_pnl[np_pnl < 0]
                np_ut = df_ex['exec_time'].values
                np_fee = df_ex['exec_fee'].values
                np_fr = df_fr['exec_fee'].values
                np_size = df_ex['exec_qty'].values
                np_size = np.where(np_size < 0, -np_size, np_size)

            t['count']    = len(np_pnl)
            t['sum']      = np_pnl.sum()
            t['mean']     = np_pnl.mean()
            t['sum_size'] = np_size.sum()
            f['trade']    = np_fee.sum()
            f['funding']  = np_fr.sum()

            if fiat_basis == True:
                start_bal = int(round(df_execs['fiat_balance'].values[0], 0))
                end_bal = int(round((df_execs['fiat_balance'].values[-1]), 0))
            else:
                start_bal = df_execs['balance'].values[0]
                end_bal = df_execs['balance'].values[-1]

            # 最大DD計算
            if fiat_basis == True:
                np_cumsum = df_ex['fiat_balance'].values
            else:
                np_cumsum = df_ex['balance'].values
            np_maxacc = np.maximum.accumulate(np_cumsum)
            np_dd = np_cumsum - np_maxacc
            np_dd_ratio = np_dd / (np_cumsum - np_dd)
            i = np.argmin(np_dd_ratio)
            t['maxdd_ratio'] = np_dd_ratio[i]
            t['maxdd'] = np_dd[i]
            t['maxdd_ut'] = np_ut[i]

            if len(np_profit) > 0:
                p['count'] = len(np_profit)
                p['sum']   = np_profit.sum()
                p['max']   = np_profit.max()
                p['mean']  = np_profit.mean()

            if len(np_loss) > 0:
                l['count'] = len(np_loss)
                l['sum']   = np_loss.sum()
                l['max']   = np_loss.min()
                l['mean']  = np_loss.mean()

            if l['sum'] != 0:
                t['pf'] = abs(p['sum'] / l['sum'])

            # 最大連勝/連敗計算
            np_nonzero = np_pnl[np_pnl != 0]
            if len(np_nonzero) > 0:
                group_sum = [[key, list(group)] for key, group in groupby(np_nonzero, key=lambda x: x > 0)]
                # 連勝
                df_group_sum = pd.DataFrame([[len(i[1]), sum(i[1])] for i in group_sum if i[0]==True], columns=['count', 'sum'])
                if len(df_group_sum.index > 0):
                    idxmax = df_group_sum['count'].idxmax()
                    p['maxlen_count'] = df_group_sum['count'].iloc[idxmax]
                    p['maxlen_sum']   = df_group_sum['sum'].iloc[idxmax]
                # 連敗
                df_group_sum = pd.DataFrame([[len(i[1]), sum(i[1])] for i in group_sum if i[0]==False], columns=['count', 'sum'])
                if len(df_group_sum.index > 0):
                    idxmax = df_group_sum['count'].idxmax()
                    l['maxlen_count'] = df_group_sum['count'].iloc[idxmax]
                    l['maxlen_sum']   = df_group_sum['sum'].iloc[idxmax]

            # 統計情報出力
            digit = 1 if fiat_basis == True else 4
            ratio_p = 0
            ratio_l = 0
            if (p['count'] + l['count']) > 0:
                ratio_p = p['count'] / (p['count'] + l['count'])
                ratio_l = l['count'] / (p['count'] + l['count'])
            t_size = round(t['sum_size'], 0)
            t_sum = round(t['sum'], digit)
            t_avr = round(t['mean'], digit)
            t_dd = round(t['maxdd'], digit)
            t_dd_dt = datetime.fromtimestamp(t['maxdd_ut'], tz=timezone('Asia/Tokyo'))
            p_sum = round(p['sum'], digit)
            p_avr = round(p['mean'], digit)
            p_max = round(p['max'], digit)
            p_lensum = round(p['maxlen_sum'], digit)
            l_sum = round(l['sum'], digit)
            l_avr = round(l['mean'], digit)
            l_max = round(l['max'], digit)
            l_lensum = round(l['maxlen_sum'], digit)
            f_trade = round(f['trade'], digit)
            f_funding = round(f['funding'], digit)

            if fiat_basis == True:
                message = f'[Fiat statistics]  PF:{t["pf"]:.2f}  Balance:{start_bal:,} -> {end_bal:,}\n'
            else:
                message = f'[BTC  statistics]  PF:{t["pf"]:.2f}  Balance:{start_bal:.4f} -> {end_bal:.4f}\n'
            message += f'  [Total   ] '
            message += f'Count:{t["count"]}(Size:{t_size:,})  PnL:{t_sum:+,}  Avr:{t_avr:+,}\n'
            message += f'  [Profit  ] '
            message += f'Count:{p["count"]}({ratio_p:.2%})  Sum:{p_sum:+,}  Avr:{p_avr:+,}  Max:{p_max:+,}  MaxLen:{p["maxlen_count"]}({p_lensum:+,})\n'
            message += f'  [Loss    ] '
            message += f'Count:{l["count"]}({ratio_l:.2%})  Sum:{l_sum:+,}  Avr:{l_avr:+,}  Max:{l_max:+,}  MaxLen:{l["maxlen_count"]}({l_lensum:+,})\n'
            message += f'  [Fee     ] '
            message += f'Trade:{f_trade:,}  Funding:{f_funding:,}\n'
            message += f'  [Max risk] '
            message += f'Drawdown:{t["maxdd_ratio"]:.2%}({t_dd:+,}) {t_dd_dt:%Y/%m/%d %H:%M:%S}\n'
            print(message)

        except Exception as e:
            print(f'__get_execution_info failed.\n{traceback.format_exc()}')
            raise e

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
    @classmethod
    def outer_join_dfs(cls, dfs: list, on_column: str, join_column: str, fillna=None, sort_index=None, is_summary=False) -> pd.DataFrame:
        try:
            if isinstance(dfs, list) == False:
                return None
            if len(dfs) < 2:
                return None
            if on_column == None or join_column == None:
                return None
            if len(on_column) < 1 or len(join_column) < 1:
                return None
            for df in dfs:
                if isinstance(df, pd.DataFrame) == False:
                    return None
                if on_column not in df.columns:
                    return None
                if join_column not in df.columns:
                    return None

            dfs = [df[[on_column, join_column]].set_index(on_column).rename(
                columns={join_column: join_column+'_'+str(i)}) for i, df in enumerate(dfs)]
            df_ret = pd.DataFrame().join(dfs, how='outer')

            if isinstance(fillna, float) or isinstance(fillna, int):
                df_ret.fillna(fillna, inplace=True)
            elif fillna == 'ffill' or fillna == 'bfill':
                df_ret.fillna(method=fillna, inplace=True)
            elif fillna == 'linear':
                df_ret.interpolate(method=fillna, inplace=True)

            if isinstance(sort_index, bool):
                df_ret.sort_index(ascending=sort_index, inplace=True)

            if is_summary:
                sr_sum = df_ret.sum(axis=1, numeric_only=True)
                df_ret = pd.DataFrame(sr_sum, columns=[join_column])

            return df_ret

        except Exception as e:
            print('outer_join_dfs failed.' + str(e))

    #---------------------------------------------------------------------------
    # 損益 統計情報取得
    #---------------------------------------------------------------------------
    # [params]
    #  lst_pnl       : 各取引毎の損益額リスト ([注意] 累積損益ではない)
    #  start_balance : 開始時残高
    # [return]
    #  dict (関数内のtrades_info参照)
    #---------------------------------------------------------------------------
    @classmethod
    def get_pnl_statistics(cls, lst_pnl, start_balance):
        try:
            trades_info = {
                'trades' : {
                    'pf'           : 0, # PF
                    'count'        : 0, # 総取引回数
                    'sum'          : 0, # 総損益
                    'mean'         : 0, # 平均損益
                    'maxdd'        : 0, # 最大DD
                    'maxdd_ratio'  : 0, # 最大DD率
                    'start_balance': 0, # 開始時残高
                    'end_balance'  : 0, # 終了時残高
                    'balance_ratio': 0, # 残高増減率
                },
                'profit' : {
                    'ratio'        : 0, # 勝取引率
                    'count'        : 0, # 勝取引数
                    'sum'          : 0, # 総利益
                    'max'          : 0, # 最大利益(1取引あたり)
                    'mean'         : 0, # 平均利益
                    'maxlen_count' : 0, # 最大連勝数
                    'maxlen_sum'   : 0, # 最大連勝利益
                },
                'loss' : {
                    'ratio'        : 0, # 負取引率
                    'count'        : 0, # 負取引数
                    'sum'          : 0, # 総損失
                    'max'          : 0, # 最大損失(1取引あたり)
                    'mean'         : 0, # 平均損失
                    'maxlen_count' : 0, # 最大連敗数
                    'maxlen_sum'   : 0, # 最大連敗損失
                },
            }

            if lst_pnl is None or len(lst_pnl) < 1:
                print('lst_pnl is not exists.')
                return trades_info

            trades = trades_info['trades']
            profit = trades_info['profit']
            loss   = trades_info['loss']

            np_pnl = np.array(lst_pnl)
            np_profit = np_pnl[np_pnl > 0]
            np_loss = np_pnl[np_pnl < 0]

            trades['count'] = len(np_pnl)
            trades['sum']   = np_pnl.sum()
            trades['mean']  = np_pnl.mean()

            # 最大DD計算
            np_cumsum = np_pnl.cumsum() + start_balance
            np_maxacc = np.maximum.accumulate(np_cumsum)
            np_dd = np_cumsum - np_maxacc
            np_dd_ratio = np_dd / (np_cumsum - np_dd)
            i = np.argmin(np_dd_ratio)
            trades['maxdd_ratio'] = np_dd_ratio[i]
            trades['maxdd'] = np_dd[i]

            trades['start_balance'] = start_balance
            trades['end_balance'] = np_cumsum[-1]
            if start_balance > 0:
                trades['balance_ratio'] = (trades['end_balance'] - start_balance) / start_balance

            len_p = len(np_profit)
            if len_p > 0:
                profit['count'] = len_p
                profit['sum']   = np_profit.sum()
                profit['max']   = np_profit.max()
                profit['mean']  = np_profit.mean()
            len_l = len(np_loss)
            if len_l > 0:
                loss['count'] = len_l
                loss['sum']   = np_loss.sum()
                loss['max']   = np_loss.min()
                loss['mean']  = np_loss.mean()
            if (len_p + len_l) > 0:
                profit['ratio'] = len_p / (len_p + len_l)
                loss['ratio']   = len_l / (len_p + len_l)
            if loss['sum'] != 0:
                trades['pf'] = abs(profit['sum'] / loss['sum'])

            # 最大連勝/連敗計算
            np_nonzero = np_pnl[np_pnl != 0]
            if len(np_nonzero) > 0:
                group_sum = [[key, list(group)] for key, group in groupby(np_nonzero, key=lambda x: x > 0)]
                # 連勝
                df_group_sum = pd.DataFrame([[len(i[1]), sum(i[1])] for i in group_sum if i[0]==True], columns=['count', 'sum'])
                if len(df_group_sum.index > 0):
                    idxmax = df_group_sum['count'].idxmax()
                    profit['maxlen_count'] = df_group_sum['count'].iloc[idxmax]
                    profit['maxlen_sum']   = df_group_sum['sum'].iloc[idxmax]
                # 連敗
                df_group_sum = pd.DataFrame([[len(i[1]), sum(i[1])] for i in group_sum if i[0]==False], columns=['count', 'sum'])
                if len(df_group_sum.index > 0):
                    idxmax = df_group_sum['count'].idxmax()
                    loss['maxlen_count'] = df_group_sum['count'].iloc[idxmax]
                    loss['maxlen_sum']   = df_group_sum['sum'].iloc[idxmax]

            return trades_info

        except Exception as e:
            print(f'get_pnl_statistics failed.\n{traceback.format_exc()}')
            raise e

    #---------------------------------------------------------------------------
    # 損益 統計情報出力
    #---------------------------------------------------------------------------
    # [params]
    #  lst_pnl       : 各取引毎の損益額リスト ([注意] 累積損益ではない)
    #  start_balance : 開始時残高
    #  round_digits  : 出力時の小数点以下桁数
    # [output example]
    #  [Profit and loss statistics]  PF: 2.00
    #    [Balance ] Result: 7,179.0 -> 55,518.0 (+673.35%)  PnL: +48,339.0  Avr: +452.0
    #    [Trade   ] Count:  107  PnL: +48,339.0  Avr: +452.0
    #    [Profit  ] Count:  37 (34.58%)  Sum: +96,696.0  Avr: +2,613.0  Max: +18,497.0  MaxLen: 4 (+1,316.0)
    #    [Loss    ] Count:  70 (65.42%)  Sum: -48,357.0  Avr: -691.0  Max: -3,477.0  MaxLen: 8 (-2,318.0)
    #    [Max risk] Drawdown: -37.82% (-3,930.0)
    #---------------------------------------------------------------------------
    @classmethod
    def print_pnl_statistics(cls, lst_pnl, start_balance, round_digits=4):
        try:
            # 統計情報算出
            info = cls.get_pnl_statistics(lst_pnl, start_balance)
            t = info['trades']
            p = info['profit']
            l = info['loss']
            t_sum = round(t['sum'], round_digits)
            t_avr = round(t['mean'], round_digits)
            t_dd = round(t['maxdd'], round_digits)
            t_sb = round(t['start_balance'], round_digits)
            t_eb = round(t['end_balance'], round_digits)
            t_ratio = round(t['balance_ratio'], round_digits+4)
            p_ratio = round(p['ratio'], round_digits+4)
            p_sum = round(p['sum'], round_digits)
            p_avr = round(p['mean'], round_digits)
            p_max = round(p['max'], round_digits)
            p_lensum = round(p['maxlen_sum'], round_digits)
            l_ratio = round(l['ratio'], round_digits+4)
            l_sum = round(l['sum'], round_digits)
            l_avr = round(l['mean'], round_digits)
            l_max = round(l['max'], round_digits)
            l_lensum = round(l['maxlen_sum'], round_digits)
            message  = f'[Profit and loss statistics]  PF: {t["pf"]:.2f}\n'
            message += f'  [Balance ] '
            message += f'Result: {t_sb:,} -> {t_eb:,} ({t_ratio:+.2%})  PnL: {t_sum:+,}  Avr: {t_avr:+,}\n'
            message += f'  [Trade   ] '
            message += f'Count:  {t["count"]}  PnL: {t_sum:+,}  Avr: {t_avr:+,}\n'
            message += f'  [Profit  ] '
            message += f'Count:  {p["count"]} ({p_ratio:.2%})  Sum: {p_sum:+,}  Avr: {p_avr:+,}  Max: {p_max:+,}  MaxLen: {p["maxlen_count"]} ({p_lensum:+,})\n'
            message += f'  [Loss    ] '
            message += f'Count:  {l["count"]} ({l_ratio:.2%})  Sum: {l_sum:+,}  Avr: {l_avr:+,}  Max: {l_max:+,}  MaxLen: {l["maxlen_count"]} ({l_lensum:+,})\n'
            message += f'  [Max risk] '
            message += f'Drawdown: {t["maxdd_ratio"]:.2%} ({t_dd:+,})\n'

            print(message)

        except Exception as e:
            print(f'print_pnl_statistics failed.\n{traceback.format_exc()}')
            raise e

    #---------------------------------------------------------------------------
    # bybit約定履歴を日別にOHLCVにリサンプリングしてcsv出力
    # (https://public.bybit.com/trading/:symbol/ より)
    #---------------------------------------------------------------------------
    # [params]
    #  start_ymd / end_ymd : str(yyyy/mm/dd)で指定
    #                        取得可能期間 : 2019-10-01以降かつ前日まで
    #  symbol              : 取得対象の通貨ペアシンボル名（デフォルトは BTCUSD）
    #  period              : リサンプルするタイムフレーム ex) '1S'(秒), '5T'(分), '4H'(時), '1D'(日)
    #  output_dir          : 日別csvを出力するディレクトリパス (Noneは'./bybit/{symbol}/ohlcv/{period}/')
    #  request_interval    : 複数request時のsleep時間(sec)
    #  progress_info       : 処理途中経過をprint
    #---------------------------------------------------------------------------
    @classmethod
    def save_daily_ohlcv_from_bybit_trading_gz(cls, start_ymd:str, end_ymd:str, symbol:str='BTCUSD', period:str='1S',
                                                output_dir:str=None, request_interval:float=1.0, progress_info:bool=True) -> None:
        try:
            # 出力ディレクトリ設定
            if output_dir is None:
                output_dir = f'./bybit/{symbol}/ohlcv/{period}/'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 取得期間
            start_dt = datetime.strptime(start_ymd, '%Y/%m/%d')
            end_dt = datetime.strptime(end_ymd, '%Y/%m/%d')
            if start_dt > end_dt:
                raise ValueError(f'end_ymd{end_ymd} should be after start_ymd{start_ymd}.')

            print(f'output dir: {output_dir}  save term: {start_dt:%Y/%m/%d} -> {end_dt:%Y/%m/%d}')

            # 日別にcsv出力
            cur_dt = start_dt
            total_count = 0
            while cur_dt <= end_dt:
                # csvパス
                csv_path = os.path.join(output_dir, f'{cur_dt:%Y%m%d}.csv')
                # csv存在チェック
                if os.path.isfile(csv_path):
                    cur_dt += timedelta(days=1)
                    continue

                df = None
                try:
                    df = pd.read_csv(f'https://public.bybit.com/trading/{symbol}/{symbol}{cur_dt:%Y-%m-%d}.csv.gz',
                                     compression='gzip',
                                     usecols=['timestamp', 'side', 'price', 'size'],
                                     dtype={'timestamp':'float', 'side':'str', 'price':'float', 'size':'int'})
                except Exception:
                    print('read_csv error', traceback.format_exc())
                    df = None

                if df is None or len(df.index) < 1:
                    print(f'Failed to read the trading file.({symbol}{cur_dt:%Y-%m-%d}.csv.gz)')
                    cur_dt += timedelta(days=1)
                    if request_interval > 0:
                        time.sleep(request_interval)
                    continue

                # 列名変更
                df.rename(columns={'timestamp': 'unixtime'}, inplace=True)

                # trade -> ohlcvリサンプリング
                df_ohlcv = cls.trade_to_ohlcv(df, period)

                # csv出力
                df_ohlcv.to_csv(csv_path, header=True, index=False)
                total_count += 1
                if progress_info:
                    print(f'Completed output {cur_dt:%Y%m%d}.csv')

                cur_dt += timedelta(days=1)
                if request_interval > 0:
                    time.sleep(request_interval)

            print(f'Total output files: {total_count}')

        except Exception as e:
            print(f'save_daily_ohlcv_from_bybit_trading_gz failed.\n{traceback.format_exc()}')
            raise e

    #---------------------------------------------------------------------------
    # ディレクトリ内の日別OHLCVをまとめて上位時間足にリサンプリングしてcsv出力
    #---------------------------------------------------------------------------
    # [params]
    #  input_dir     : 日別csvの入力ディレクトリパス
    #  output_dir    : 日別csvの出力ディレクトリパス
    #  period        : リサンプルするタイムフレーム ex) '1S'(秒), '5T'(分), '4H'(時), '1D'(日)
    #  progress_info : 処理途中経過をprint
    #---------------------------------------------------------------------------
    @classmethod
    def downsample_daily_ohlcv(cls, input_dir:str, output_dir:str, period:str='1T', progress_info:bool=True) -> None:
        try:
            # 入力ディレクトリチェック
            if not os.path.exists(input_dir):
                raise ValueError(f'Not exists input dir.({input_dir})')
            # 出力ディレクトリチェック
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            print(f'input dir: {output_dir} -> output dir: {output_dir}  period: {period}')

            # 入力ディレクトリのファイル一覧をリスト形式で取得
            input_files = glob.glob(input_dir + '*.csv')

            # 日別csv読み込み
            total_count = 0
            for input_path in input_files:
                input_csv = os.path.basename(input_path)
                # 出力ファイル存在チェック
                output_path = os.path.join(output_dir, input_csv)
                if os.path.isfile(output_path) == False:
                    # csv読み込み
                    df = pd.read_csv(input_path)
                    # 指定periodにリサンプリング
                    df_ohlcv = cls.downsample_ohlcv(df, period)
                    # csv出力
                    df_ohlcv.to_csv(output_path, header=True, index=False)
                    total_count += 1
                    if progress_info:
                        print(f'Completed output {input_csv}')

            print(f'Total output files: {total_count}')

        except Exception as e:
            print(f'downsample_daily_ohlcv failed.\n{traceback.format_exc()}')
            raise e

    #---------------------------------------------------------------------------
    # 日別OHLCVから指定期間のOHLCVを1つのDataFrameにまとめて取得
    # (periodにてリサンプリング指定可能)
    #---------------------------------------------------------------------------
    # [params]
    #  start_ymd / end_ymd : str(yyyy/mm/dd)で指定
    #  csv_dir             : 読み込む日別csvが格納されているディレクトリパス
    #  ignore_defect       : 取得期間中に日別csvが存在しなかった場合に無視して継続するか (True:無視し継続, False:エラー)
    #  period              : リサンプルするタイムフレーム ex) '1S'(秒), '5T'(分), '4H'(時), '1D'(日)
    #---------------------------------------------------------------------------
    @classmethod
    def get_ohlcv_from_daily_csv(cls, start_ymd:str, end_ymd:str, csv_dir:str, ignore_defect:bool=False, period:str=None) -> pd.DataFrame:
        try:
            if not os.path.exists(csv_dir):
                raise ValueError(f'Not exists csv dir.({csv_dir})')

            # 取得期間
            start_dt = datetime.strptime(start_ymd, '%Y/%m/%d')
            end_dt = datetime.strptime(end_ymd, '%Y/%m/%d')
            if start_dt > end_dt:
                raise ValueError(f'end_ymd{end_ymd} should be after start_ymd{start_ymd}.')

            # 日別csv読み込み
            ohlcvs = []
            cur_dt = start_dt
            while cur_dt <= end_dt:
                # csvパス
                csv_path = os.path.join(csv_dir, f'{cur_dt:%Y%m%d}.csv')
                # csv存在チェック
                if os.path.isfile(csv_path):
                    # csv読み込み
                    ohlcvs.append(pd.read_csv(csv_path))
                else:
                    error_msg = f'Not exists csv file.({cur_dt:%Y%m%d}.csv)'
                    if ignore_defect:
                        print(error_msg)
                    else:
                        raise ValueError(error_msg)
                cur_dt += timedelta(days=1)

            # リストを全て行方向に結合
            # axis=0:行方向に結合, sort
            df = pd.concat(ohlcvs, axis=0, sort=True)

            # period指定の場合はリサンプリング
            if period != None:
                df_ohlcv = cls.downsample_ohlcv(df, period)
            else:
                df_ohlcv = df

            # indexリセット
            df_ohlcv.reset_index(drop=True, inplace=True)

            return df_ohlcv
    
        except Exception as e:
            print(f'get_ohlcv_from_daily_csv failed.\n{traceback.format_exc()}')
            raise e
