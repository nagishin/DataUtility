# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

#---------------------------------------------------------------------------
# 日付変換・加工クラス
#---------------------------------------------------------------------------
# ・UnixTime, datetime, 日付文字列のいずれかを設定してTimeオブジェクトを作成する
# ・Timeオブジェクトはタイムゾーン変換や時刻計算、丸めを行うことができる
# ・TimeオブジェクトからUnixTime, datetime, 日付文字列を取得することができる
#---------------------------------------------------------------------------

class Time(object):

    #---------------------------------------------------------------------------
    # Timeオブジェクト生成
    #---------------------------------------------------------------------------
    # [params]
    #  value    : 設定する日付オブジェクト (UnixTime, datetime, str)
    #  tz       : 設定するタイムゾーンをhours(int)または'UTC'/'JST'で設定 (デフォルトはUTC)
    #  str_fmt  : valueがstrの場合に適用する日付フォーマット (省略可)
    #---------------------------------------------------------------------------
    def __init__(self, value: object, tz: object = 0, str_fmt: str = '%Y-%m-%dT%H:%M:%S.%fZ'):
        self.__unixtime = 0
        self.convert_timezone(tz)

        if isinstance(value, int) or isinstance(value, float):
            self.__unixtime = value

        elif isinstance(value, datetime):
            self.__unixtime = value.timestamp()

        elif isinstance(value, str):
            dt = self.__str_to_datetime(value, str_fmt)
            if dt is not None:
                dt = dt.replace(tzinfo=self.__timezone)
                self.__unixtime = dt.timestamp()

    #---------------------------------------------------------------------------
    # タイムゾーン変換
    #---------------------------------------------------------------------------
    # [params]
    #  tz       : 変換するタイムゾーンをhours(int)または'UTC'/'JST'で設定 (デフォルトはUTC)
    #---------------------------------------------------------------------------
    def convert_timezone(self, tz: object = 0):
        if isinstance(tz, int) or isinstance(tz, float):
            self.__timezone = timezone(timedelta(hours=tz))
        elif isinstance(tz, str):
            if str(tz).upper() == 'UTC':
                self.__timezone = timezone.utc
            elif str(tz).upper() == 'JST':
                self.__timezone = timezone(timedelta(hours=+9), 'JST')
        return self

    #---------------------------------------------------------------------------
    # UnixTime取得
    #---------------------------------------------------------------------------
    def unixtime(self):
        return self.__unixtime

    #---------------------------------------------------------------------------
    # datetime取得
    #---------------------------------------------------------------------------
    def datetime(self):
        return datetime.fromtimestamp(self.__unixtime, self.__timezone)

    #---------------------------------------------------------------------------
    # 日付文字列取得
    #---------------------------------------------------------------------------
    # [params]
    #  str_fmt  : 取得する日付フォーマット (省略可)
    #---------------------------------------------------------------------------
    def str(self, str_fmt: str = '%Y-%m-%dT%H:%M:%S.%fZ'):
        return self.datetime().strftime(str_fmt)

    #---------------------------------------------------------------------------
    # 時刻計算
    #---------------------------------------------------------------------------
    # value : 加算する日数(days)
    def add_days(self, value):
        if isinstance(value, int) or isinstance(value, float):
            self.__unixtime += value * 86400
        return self

    # value : 加算する時間数(hours)
    def add_hours(self, value):
        if isinstance(value, int) or isinstance(value, float):
            self.__unixtime += value * 3600
        return self

    # value : 加算する分数(minutes)
    def add_minutes(self, value):
        if isinstance(value, int) or isinstance(value, float):
            self.__unixtime += value * 60
        return self

    # value : 加算する秒数(seconds)
    def add_seconds(self, value):
        if isinstance(value, int) or isinstance(value, float):
            self.__unixtime += value
        return self

    #---------------------------------------------------------------------------
    # 時刻丸め
    #---------------------------------------------------------------------------
    # [params]
    #  is_down  : True:切り捨て, False:切り上げ
    #---------------------------------------------------------------------------
    # value : 丸め日数(days)
    def round_days(self, value, is_down=True):
        if isinstance(value, int) or isinstance(value, float):
            offset = datetime.now(self.__timezone).utcoffset().seconds
            self.__unixtime += offset
            unit = value * 86400
            self.__round(unit, is_down)
            self.__unixtime -= offset
        return self

    # value : 丸め時間数(hours)
    def round_hours(self, value, is_down=True):
        if isinstance(value, int) or isinstance(value, float):
            unit = value * 3600
            self.__round(unit, is_down)
        return self

    # value : 丸め分数(minutes)
    def round_minutes(self, value, is_down=True):
        if isinstance(value, int) or isinstance(value, float):
            unit = value * 60
            self.__round(unit, is_down)
        return self

    # value : 丸め秒数(seconds)
    def round_seconds(self, value, is_down=True):
        if isinstance(value, int) or isinstance(value, float):
            unit = value
            self.__round(unit, is_down)
        return self


    def __round(self, unit, is_down):
        ut = (self.__unixtime // unit) * unit
        if is_down:
            self.__unixtime = ut
        else:
            self.__unixtime = ut + unit

    def __str_to_datetime(self, str_dt, fmt):
        try:
            cnv_str = str_dt
            cnv_fmt = fmt
            dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
            if dt != None:
                return dt

            if len(cnv_str) == 19:
                cnv_str = str_dt + '.000Z'
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt
                cnv_fmt = '%Y/%m/%d %H:%M:%S'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

            if len(cnv_str) == 24:
                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S%z'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt
                cnv_fmt = '%Y/%m/%d %H:%M:%S%z'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

            if len(cnv_str) > 24:
                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%f'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_fmt = '%Y/%m/%d %H:%M:%S.%f'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%fZ%z'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_fmt = '%Y/%m/%d %H:%M:%S.%f%z'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

            if len(cnv_str) > 22:
                cnv_str = str_dt[:23]
                cnv_fmt = '%Y-%m-%dT%H:%M:%S.%f'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt[:23]
                cnv_fmt = '%Y/%m/%d %H:%M:%S.%f'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

        except Exception:
            return None

    def __convert_str_to_dt(self, str_dt, fmt):
        try:
            dt = datetime.strptime(str_dt, fmt)
            return dt
        except ValueError:
            pass
        return None
