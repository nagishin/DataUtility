# -*- coding: utf-8 -*-
import calendar
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

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

        if isinstance(value, datetime):
            self.__unixtime = value.timestamp()
            if tz == 0 and value.tzinfo is not None:
                self.__timezone = value.tzinfo

        elif isinstance(value, str):
            dt = self.__str_to_datetime(value, str_fmt)
            if dt is not None:
                dt = dt.replace(tzinfo=self.__timezone)
                self.__unixtime = dt.timestamp()

        elif self.__is_numeric(value):
            self.__unixtime = float(value)

    #---------------------------------------------------------------------------
    # 演算子定義
    #---------------------------------------------------------------------------
    # operator <
    def __lt__(self, other):
        if isinstance(other, Time):
            return self.__unixtime < other.unixtime()
        elif isinstance(other, datetime):
            return self.__unixtime < other.timestamp()
        elif self.__is_numeric(other):
            return self.__unixtime < float(other)
        else:
            return False

    # operator <=
    def __le__(self, other):
        if isinstance(other, Time):
            return self.__unixtime <= other.unixtime()
        elif isinstance(other, datetime):
            return self.__unixtime <= other.timestamp()
        elif self.__is_numeric(other):
            return self.__unixtime <= float(other)
        else:
            return False

    # operator >
    def __gt__(self, other):
        if isinstance(other, Time):
            return self.__unixtime > other.unixtime()
        elif isinstance(other, datetime):
            return self.__unixtime > other.timestamp()
        elif self.__is_numeric(other):
            return self.__unixtime > float(other)
        else:
            return False

    # operator >=
    def __ge__(self, other):
        if isinstance(other, Time):
            return self.__unixtime >= other.unixtime()
        elif isinstance(other, datetime):
            return self.__unixtime >= other.timestamp()
        elif self.__is_numeric(other):
            return self.__unixtime >= float(other)
        else:
            return False

    # operator ==
    def __eq__(self, other):
        if isinstance(other, Time):
            return self.__unixtime == other.unixtime()
        elif isinstance(other, datetime):
            return self.__unixtime == other.timestamp()
        elif self.__is_numeric(other):
            return self.__unixtime == float(other)
        else:
            return False

    # operator !=
    def __ne__(self, other):
        if isinstance(other, Time):
            return self.__unixtime != other.unixtime()
        elif isinstance(other, datetime):
            return self.__unixtime != other.timestamp()
        elif self.__is_numeric(other):
            return self.__unixtime != float(other)
        else:
            return True

    # operator +
    def __add__(self, other):
        if isinstance(other, (timedelta, relativedelta)):
            return Time(self.datetime() + other, self.__timezone)
        elif self.__is_numeric(other):
            return Time(self.unixtime() + float(other), self.__timezone)

    # operator -
    def __sub__(self, other):
        if isinstance(other, (timedelta, relativedelta)):
            return Time(self.datetime() - other, self.__timezone)
        elif self.__is_numeric(other):
            return Time(self.unixtime() - float(other), self.__timezone)

    # operator +=
    def __iadd__(self, other):
        if isinstance(other, (timedelta, relativedelta)):
            dt = self.datetime() + other
            self.__unixtime = dt.timestamp()
        elif self.__is_numeric(other):
            self.__unixtime += float(other)
        return self

    # operator -=
    def __isub__(self, other):
        if isinstance(other, (timedelta, relativedelta)):
            dt = self.datetime() - other
            self.__unixtime = dt.timestamp()
        elif self.__is_numeric(other):
            self.__unixtime -= float(other)
        return self

    #---------------------------------------------------------------------------
    # タイムゾーン変換
    #---------------------------------------------------------------------------
    # [params]
    #  tz       : 変換するタイムゾーンをhours(int)または'UTC'/'JST'で設定 (デフォルトはUTC)
    #---------------------------------------------------------------------------
    def convert_timezone(self, tz: object = 0):
        if isinstance(tz, timezone):
            self.__timezone = tz
        elif isinstance(tz, int) or isinstance(tz, float):
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
    def unixtime(self) -> float:
        return self.__unixtime

    #---------------------------------------------------------------------------
    # datetime取得
    #---------------------------------------------------------------------------
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.__unixtime, self.__timezone)

    # 設定時刻からみた月初日
    def month_first_day(self) -> datetime:
        return self.datetime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 設定時刻からみた月末日
    def month_last_day(self) -> datetime:
        dt = self.datetime()
        last_day = calendar.monthrange(dt.year, dt.month)[1]
        return dt.replace(day=last_day, hour=0, minute=0, second=0, microsecond=0)

    # 設定時刻からみた年初日
    def year_first_day(self) -> datetime:
        return self.datetime().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # 設定時刻からみた年末日
    def year_last_day(self) -> datetime:
        return self.datetime().replace(month=12, day=31, hour=0, minute=0, second=0, microsecond=0)

    #---------------------------------------------------------------------------
    # 時刻数値取得
    #---------------------------------------------------------------------------
    def date(self):
        dt = self.datetime()
        return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond)

    def year(self) -> int:
        return self.datetime().year

    def month(self) -> int:
        return self.datetime().month

    def day(self) -> int:
        return self.datetime().day

    def hour(self) -> int:
        return self.datetime().hour

    def minute(self) -> int:
        return self.datetime().minute

    def second(self) -> int:
        return self.datetime().second

    def microsecond(self) -> int:
        return self.datetime().microsecond

    def weekday(self) -> int:
        return self.datetime().weekday()

    def weekday_name(self) -> str:
        return calendar.day_name[self.weekday()]

    #---------------------------------------------------------------------------
    # 日付文字列取得
    #---------------------------------------------------------------------------
    # [params]
    #  str_fmt  : 取得する日付フォーマット (省略可)
    #---------------------------------------------------------------------------
    def str(self, str_fmt: str = '%Y-%m-%dT%H:%M:%S.%fZ') -> str:
        return self.datetime().strftime(str_fmt)

    #---------------------------------------------------------------------------
    # 時刻計算
    #---------------------------------------------------------------------------
    # value : 加算する時刻
    def add_date(self, years: int = 0, months: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0, microseconds: int = 0):
        self.add_years(years)
        self.add_months(months)
        self.add_days(days)
        self.add_hours(hours)
        self.add_minutes(minutes)
        self.add_seconds(seconds)
        self.add_microseconds(microseconds)
        return self

    # value : 加算する年数(years)
    def add_years(self, value):
        if self.__is_numeric(value):
            if int(value) != 0:
                dt = self.datetime() + relativedelta(years=int(value))
                self.__unixtime = dt.timestamp()
        return self

    # value : 加算する月数(months)
    def add_months(self, value):
        if self.__is_numeric(value):
            if int(value) != 0:
                dt = self.datetime() + relativedelta(months=int(value))
                self.__unixtime = dt.timestamp()
        return self

    # value : 加算する日数(days)
    def add_days(self, value):
        if self.__is_numeric(value):
            if int(value) != 0:
                dt = self.datetime() + relativedelta(days=int(value))
                self.__unixtime = dt.timestamp()
        #if isinstance(value, int) or isinstance(value, float):
        #    self.__unixtime += value * 86400
        return self

    # value : 加算する時間数(hours)
    def add_hours(self, value):
        if self.__is_numeric(value):
            if int(value) != 0:
                dt = self.datetime() + relativedelta(hours=int(value))
                self.__unixtime = dt.timestamp()
        #if isinstance(value, int) or isinstance(value, float):
        #    self.__unixtime += value * 3600
        return self

    # value : 加算する分数(minutes)
    def add_minutes(self, value):
        if self.__is_numeric(value):
            if int(value) != 0:
                dt = self.datetime() + relativedelta(minutes=int(value))
                self.__unixtime = dt.timestamp()
        #if isinstance(value, int) or isinstance(value, float):
        #    self.__unixtime += value * 60
        return self

    # value : 加算する秒数(seconds)
    def add_seconds(self, value):
        if self.__is_numeric(value):
            if int(value) != 0:
                dt = self.datetime() + relativedelta(seconds=int(value))
                self.__unixtime = dt.timestamp()
        #if isinstance(value, int) or isinstance(value, float):
        #    self.__unixtime += value
        return self

    # value : 加算するマイクロ秒数(microseconds)
    def add_microseconds(self, value):
        if self.__is_numeric(value):
            if int(value) != 0:
                dt = self.datetime() + relativedelta(microseconds=int(value))
                self.__unixtime = dt.timestamp()
        return self

    # 設定時刻からみた月初日に設定
    def set_month_first_day(self):
        self.__unixtime = self.month_first_day().timestamp()
        return self

    # 設定時刻からみた月末日に設定
    def set_month_last_day(self):
        self.__unixtime = self.month_last_day().timestamp()
        return self

    # 設定時刻からみた年初日に設定
    def set_year_first_day(self):
        self.__unixtime = self.year_first_day().timestamp()
        return self

    # 設定時刻からみた年末日に設定
    def set_year_last_day(self):
        self.__unixtime = self.year_last_day().timestamp()
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

            if len(cnv_str) == 6:
                cnv_str = str_dt
                cnv_fmt = '%Y%m'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

            if len(cnv_str) == 7:
                cnv_str = str_dt
                cnv_fmt = '%Y-%m'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt
                cnv_fmt = '%Y/%m'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

            if len(cnv_str) == 8:
                cnv_str = str_dt
                cnv_fmt = '%Y%m%d'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

            if len(cnv_str) == 10:
                cnv_str = str_dt
                cnv_fmt = '%Y-%m-%d'
                dt = self.__convert_str_to_dt(cnv_str, cnv_fmt)
                if dt != None:
                    return dt

                cnv_str = str_dt
                cnv_fmt = '%Y/%m/%d'
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
                cnv_fmt = '%Y-%m-%d %H:%M:%S'
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
                cnv_fmt = '%Y-%m-%d %H:%M:%S%z'
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

                cnv_fmt = '%Y-%m-%d %H:%M:%S.%f%z'
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

    def __is_int(self, val) -> bool:
        try:
            int(val)
            return True
        except:
            return False

    def __is_float(self, val) -> bool:
        try:
            float(val)
            return True
        except:
            return False

    def __is_numeric(self, val) -> bool:
        return self.__is_int(val) or self.__is_float(val)
