# -*- coding: utf-8 -*-
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
#import mpl_finance as mpf
import mplfinance.original_flavor as mpf
from matplotlib import ticker
import japanize_matplotlib
import seaborn as sns
sns.set(font='IPAexGothic')

#---------------------------------------------------------------------------
# Chart作成クラス
#---------------------------------------------------------------------------
# ・DataFrameからチャートを作成する
# ・X軸同期したサブチャートを設定することができる
# ・DataFrame列をシンプルな設定で可視化する
#---------------------------------------------------------------------------

class Chart:
    FormatX = '%y/%m/%d %H:%M:%S'

    #---------------------------------------------------------------------------
    # Chartオブジェクト生成
    #---------------------------------------------------------------------------
    # [params]
    #  df : チャートを作成するDataFrame
    #---------------------------------------------------------------------------
    def __init__(self, df: pd.DataFrame):
        self.__df = df.copy()
        self.reset()

    #---------------------------------------------------------------------------
    # 初期化
    #---------------------------------------------------------------------------
    def reset(self):
        Chart.FormatX = '%y/%m/%d %H:%M:%S'
        self.__width = 16
        self.__height = 12
        self.__title = {'title':None, 'loc':'center', 'fontsize':16,}
        self.__xaxis = {'col':None, 'grid':True, 'converter':None,}
        self.__yaxis = {0:{'title':None, 'grid':True, 'legend':False, 'gridspec':1},}
        self.__indicators = {0:[],}
        self.__default = {
            'candlestick': {'type':'candlestick', 'open':None, 'high':None, 'low':None, 'close':None, 'upcolor':'#53B987', 'downcolor':'#EB4D5C', 'width':0.8,},
            'line': {'type':'line', 'y':None, 'linewidth':1.0, 'linestyle':'solid', 'color':'green', 'label':None,},
            'bar': {'type':'bar', 'y':None, 'color':'orange', 'width':0.8, 'label':None,},
            'mark': {'type':'mark', 'y':None, 'marker':'.', 'size':10, 'color':'green', 'label':None,},
            'band': {'type':'band', 'y1':None, 'y2':None, 'linewidth':1.0, 'linecolor':'dimgray', 'upcolor':'skyblue', 'downcolor':'pink', 'alpha':0.2, 'label':None,},
        }
        self.__backcolor = ['#FAFAFA', '#F5F5F5',]
        self.__fig = None

    #---------------------------------------------------------------------------
    # タイトル設定
    #---------------------------------------------------------------------------
    # [params]
    #  title    : チャートタイトル
    #  loc      : タイトル位置('left', 'center', 'right')
    #  fontsize : タイトルフォントサイズ
    #---------------------------------------------------------------------------
    def set_title(self, title: str, loc: str='center', fontsize: int=16):
        if title != None:
            self.__title['title'] = title
        if loc != None:
            self.__title['loc'] = loc
        if Chart.is_numeric(fontsize) and fontsize > 0:
            self.__title['fontsize'] = fontsize
        return self

    #---------------------------------------------------------------------------
    # チャートサイズ設定
    #---------------------------------------------------------------------------
    # [params]
    #  width    : チャート幅
    #  height   : チャート高さ
    #---------------------------------------------------------------------------
    def set_size(self, width: int=16, height: int=12):
        if Chart.is_numeric(width) and width > 0:
            self.__width = width
        if Chart.is_numeric(height) and height > 0:
            self.__height = height
        return self

    #---------------------------------------------------------------------------
    # X軸設定
    #---------------------------------------------------------------------------
    # [params]
    #  col       : X軸に使用する列名(Noneはindex)
    #  grid      : X軸グリッド表示ON/OFF
    #  converter : X軸ラベルの変換関数
    #  format    : X軸ラベルの日付変換フォーマット
    #
    # [X軸変換]
    # UnixTimeやdatetimeを指定フォーマットでラベル設定する場合
    # converterにto_date_format、formatに書式を指定する
    #  ex) set_x(col=None, grid=True, converter=Chart.to_date_format, format='%m/%d')
    #
    # また、任意の変換関数をconverterに設定することでX軸に適用可能
    #  ex) set_x(col=None, grid=True, converter=lambda x: f'{x} sec')
    #---------------------------------------------------------------------------
    def set_x(self, col: str=None, grid: bool=True, converter=None, format: str='%m/%d %H:%M'):
        if col != None and col in self.__df.columns:
            self.__xaxis['col'] = col
        self.__xaxis['grid'] = grid
        if converter != None:
            self.__xaxis['converter'] = converter
        if format != None:
            Chart.FormatX = format
        return self

    #---------------------------------------------------------------------------
    # Y軸設定
    #---------------------------------------------------------------------------
    # [params]
    #  ax       : チャート番号(0:メイン, 1～:サブチャート)
    #  title    : Y軸タイトル
    #  grid     : Y軸グリッド表示ON/OFF
    #  legend   : 凡例表示ON/OFF
    #  gridspec : 複数チャート時の高さ配分
    #
    # [複数チャートの高さ調整]
    # 各チャートのgridspec値の合計から各チャートの高さ比率が設定される
    #  ex) [ax0]gridspec=2, [ax1]gridspec=1, [ax2]gridspec=1の場合
    #      ax0 : ax1 : ax2の高さは 2:1:1 となる
    #---------------------------------------------------------------------------
    def set_y(self, ax: int=0, title: str=None, grid: bool=True, legend: bool=False, gridspec: int=1):
        if Chart.is_int(ax) and ax >= 0:
            if ax in self.__yaxis.keys():
                self.__yaxis[ax]['title'] = title
                self.__yaxis[ax]['grid'] = grid
                self.__yaxis[ax]['legend'] = legend
                self.__yaxis[ax]['gridspec'] = gridspec
            else:
                self.__yaxis[ax] = {'title':title, 'grid':grid, 'legend':legend, 'gridspec':gridspec}
        return self

    #---------------------------------------------------------------------------
    # ロウソク足設定
    #---------------------------------------------------------------------------
    # [params]
    #  ax        : チャート番号(0:メイン, 1～:サブチャート)
    #  open      : open列名  (省略時は列名から自動検索)
    #  high      : high列名  (省略時は列名から自動検索)
    #  low       : low列名   (省略時は列名から自動検索)
    #  close     : close列名 (省略時は列名から自動検索)
    #  upcolor   : 陽線色
    #  downcolor : 陰線色
    #  width     : バー幅
    #---------------------------------------------------------------------------
    def set_candlestick(self, ax: int=0, open: str=None, high: str=None, low: str=None, close: str=None, upcolor: str='#53B987', downcolor: str='#EB4D5C', width: float=0.8):
        indi = self.__default['candlestick'].copy()

        if open != None and open in self.__df.columns:
            indi['open'] = open
        else:
            if 'open' in self.__df.columns:
                indi['open'] = 'open'
            elif 'Open' in self.__df.columns:
                indi['open'] = 'Open'
            elif 'o' in self.__df.columns:
                indi['open'] = 'o'
            elif 'op' in self.__df.columns:
                indi['open'] = 'op'

        if high != None and high in self.__df.columns:
            indi['high'] = high
        else:
            if 'high' in self.__df.columns:
                indi['high'] = 'high'
            elif 'High' in self.__df.columns:
                indi['high'] = 'High'
            elif 'h' in self.__df.columns:
                indi['high'] = 'h'
            elif 'hi' in self.__df.columns:
                indi['high'] = 'hi'

        if low != None and low in self.__df.columns:
            indi['low'] = low
        else:
            if 'low' in self.__df.columns:
                indi['low'] = 'low'
            elif 'Low' in self.__df.columns:
                indi['low'] = 'Low'
            elif 'l' in self.__df.columns:
                indi['low'] = 'l'
            elif 'lo' in self.__df.columns:
                indi['low'] = 'lo'

        if close != None and close in self.__df.columns:
            indi['close'] = close
        else:
            if 'close' in self.__df.columns:
                indi['close'] = 'close'
            elif 'Close' in self.__df.columns:
                indi['close'] = 'Close'
            elif 'c' in self.__df.columns:
                indi['close'] = 'c'
            elif 'cl' in self.__df.columns:
                indi['close'] = 'cl'

        if upcolor != None:
            indi['upcolor'] = upcolor
        if downcolor != None:
            indi['downcolor'] = downcolor
        if Chart.is_numeric(width) and width > 0:
            indi['width'] = width

        if Chart.is_int(ax) and ax >= 0:
            if ax in self.__indicators.keys():
                self.__indicators[ax].append(indi)
            else:
                self.__indicators[ax] = [indi]

        # converter自動設定
        if self.__xaxis['converter'] == None:
            col_x = None
            if self.__xaxis['col'] == None:
                col_x = self.__df.index.values
            else:
                col_x = self.__df[self.__xaxis['col']].values

            if col_x is None or len(col_x) < 2:
                pass
            else:
                unit = 0
                x0 = col_x[0]
                x1 = col_x[1]
                if isinstance(x0, np.datetime64):
                    self.__xaxis['converter'] = Chart.to_date_format
                    unit = pd.to_datetime(x1).timestamp() - pd.to_datetime(x0).timestamp()
                elif isinstance(x0, datetime):
                    self.__xaxis['converter'] = Chart.to_date_format
                    unit = x1.timestamp() - x0.timestamp()
                elif Chart.is_numeric(x0) and (x0 > 1000000000):
                    self.__xaxis['converter'] = Chart.to_date_format
                    unit = x1 - x0

                if unit == 0:
                    pass
                elif unit < 60:
                    Chart.FormatX = '%m/%d %H:%M:%S'
                elif unit < 3600:
                    Chart.FormatX = '%m/%d %H:%M'
                elif unit < 86400:
                    Chart.FormatX = '%m/%d %H:%M'
                else:
                    Chart.FormatX = '%y/%m/%d'

        return self

    #---------------------------------------------------------------------------
    # LINE設定
    #---------------------------------------------------------------------------
    # [params]
    #  ax        : チャート番号(0:メイン, 1～:サブチャート)
    #  y         : y列名
    #  linewidth : 線幅
    #  linestyle : 線種('solid', 'dashed', 'dashdot', 'dotted', etc.)
    #  color     : 線色
    #  label     : 見出し
    #---------------------------------------------------------------------------
    def set_line(self, ax: int=0, y: str=None, linewidth: float=1.0, linestyle: str='solid', color: str='green', label: str=None):
        indi = self.__default['line'].copy()

        if y != None and y in self.__df.columns:
            indi['y'] = y
        else:
            if 'y' in self.__df.columns:
                indi['y'] = 'y'
            elif 'Y' in self.__df.columns:
                indi['y'] = 'Y'

        if Chart.is_numeric(linewidth) and linewidth > 0:
            indi['linewidth'] = linewidth
        if linestyle != None:
            indi['linestyle'] = linestyle
        if color != None:
            indi['color'] = color
        if label != None:
            indi['label'] = label

        if Chart.is_int(ax) and ax >= 0:
            if ax in self.__indicators.keys():
                self.__indicators[ax].append(indi)
            else:
                self.__indicators[ax] = [indi]
        return self

    #---------------------------------------------------------------------------
    # BAR設定
    #---------------------------------------------------------------------------
    # [params]
    #  ax        : チャート番号(0:メイン, 1～:サブチャート)
    #  y         : y列名
    #  color     : バー色
    #  width     : バー幅
    #  label     : 見出し
    #---------------------------------------------------------------------------
    def set_bar(self, ax: int=0, y: str=None, color: str='orange', width: float=0.8, label: str=None):
        indi = self.__default['bar'].copy()

        if y != None and y in self.__df.columns:
            indi['y'] = y
        else:
            if 'y' in self.__df.columns:
                indi['y'] = 'y'
            elif 'Y' in self.__df.columns:
                indi['y'] = 'Y'

        if color != None:
            indi['color'] = color
        if Chart.is_numeric(width) and width > 0:
            indi['width'] = width
        if label != None:
            indi['label'] = label

        if Chart.is_int(ax) and ax >= 0:
            if ax in self.__indicators.keys():
                self.__indicators[ax].append(indi)
            else:
                self.__indicators[ax] = [indi]
        return self

    #---------------------------------------------------------------------------
    # MARK設定
    #---------------------------------------------------------------------------
    # [params]
    #  ax        : チャート番号(0:メイン, 1～:サブチャート)
    #  y         : y列名
    #  marker    : マーク('.', 'o', 'x', '+', '*', etc.)
    #  size      : サイズ
    #  color     : 色
    #  label     : 見出し
    #---------------------------------------------------------------------------
    def set_mark(self, ax: int=0, y: str=None, marker: str='.', size: float=10, color: str='green', label: str=None):
        indi = self.__default['mark'].copy()

        if y != None and y in self.__df.columns:
            indi['y'] = y
        else:
            if 'y' in self.__df.columns:
                indi['y'] = 'y'
            elif 'Y' in self.__df.columns:
                indi['y'] = 'Y'

        if marker != None:
            indi['marker'] = marker
        if Chart.is_numeric(size) and size > 0:
            indi['size'] = size
        if color != None:
            indi['color'] = color
        if label != None:
            indi['label'] = label

        if Chart.is_int(ax) and ax >= 0:
            if ax in self.__indicators.keys():
                self.__indicators[ax].append(indi)
            else:
                self.__indicators[ax] = [indi]
        return self

    #---------------------------------------------------------------------------
    # BAND設定
    #---------------------------------------------------------------------------
    # [params]
    #  ax        : チャート番号(0:メイン, 1～:サブチャート)
    #  y1        : y1列名
    #  y2        : y2列名
    #  linewidth : 線幅
    #  linecolor : 線色
    #  upcolor   : y1 > y2 色
    #  downcolor : y1 < y2 色
    #  label     : 見出し
    #---------------------------------------------------------------------------
    def set_band(self, ax: int=0, y1: str=None, y2: str=None, linewidth: float=1.0, linecolor: str='dimgray', upcolor: str='skyblue', downcolor: str='pink', alpha: float=0.2, label: str=None):
        indi = self.__default['band'].copy()

        if y1 != None and y1 in self.__df.columns:
            indi['y1'] = y1
        else:
            if 'y1' in self.__df.columns:
                indi['y1'] = 'y1'
            elif 'Y1' in self.__df.columns:
                indi['y1'] = 'Y1'

        if y2 != None and y2 in self.__df.columns:
            indi['y2'] = y2
        else:
            if 'y2' in self.__df.columns:
                indi['y2'] = 'y2'
            elif 'Y2' in self.__df.columns:
                indi['y2'] = 'Y2'

        if Chart.is_numeric(linewidth) and linewidth > 0:
            indi['linewidth'] = linewidth
        if upcolor != None:
            indi['upcolor'] = upcolor
        if downcolor != None:
            indi['downcolor'] = downcolor
        if Chart.is_numeric(alpha) and alpha > 0:
            indi['alpha'] = alpha
        if label != None:
            indi['label'] = label

        if Chart.is_int(ax) and ax >= 0:
            if ax in self.__indicators.keys():
                self.__indicators[ax].append(indi)
            else:
                self.__indicators[ax] = [indi]
        return self

    #---------------------------------------------------------------------------
    # チャート表示
    #---------------------------------------------------------------------------
    # 設定した内容でチャートを表示する
    # (jupyterなどで使用する場合は事前に「%matplotlib inline」を記述しておく)
    #---------------------------------------------------------------------------
    def plot(self):
        if self.__fig == None:
            self.__create()
        plt.show()

    #---------------------------------------------------------------------------
    # チャート出力
    #---------------------------------------------------------------------------
    # [params]
    #  filepath  : 保存するファイルパス(.png)
    #---------------------------------------------------------------------------
    def save(self, filepath: str):
        if self.__fig == None:
            self.__create()
        # pngファイル出力
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2, transparent=False)
        plt.close()

    #---------------------------------------------------------------------------
    # チャート作成
    #---------------------------------------------------------------------------
    def __create(self):
        # マージン設定
        matplotlib.rcParams['axes.xmargin'] = 0.001 # X軸
        matplotlib.rcParams['axes.ymargin'] = 0.05  # Y軸
        # グラフ設定
        self.__fig = plt.figure(figsize=(self.__width, self.__height))
        self.__fig.autofmt_xdate()
        plt.subplots_adjust(wspace=0.0, hspace=0.0) # グラフ間余白

        # チャート配置割り
        grids = {k: self.__yaxis[k]['gridspec'] if k in self.__yaxis.keys() else 1 for k in self.__indicators.keys()}
        total_grid = sum(grids.values())
        #total_grid = len(self.__indicators.keys())
        gs = gridspec.GridSpec(total_grid, 1)

        # X軸列設定
        lst_x = range(len(self.__df.index))

        ax_idx = 0
        grid = 0
        ax0 = None
        for k,g in grids.items():
            if grid == 0: # 最上段チャートはタイトル設定
                # axis作成
                ax = plt.subplot(gs[grid:grid+g, 0])
                ax0 = ax # X軸同期のため
                # タイトル
                ax.set_title(self.__title['title'], loc=self.__title['loc'], fontsize=self.__title['fontsize'])
            else:
                # axis作成
                ax = plt.subplot(gs[grid:grid+g, 0], sharex=ax0) # 最上段チャートにX軸同期

            # 最下段チャートはX軸目盛り設定
            if grid + g == total_grid:
                ax.xaxis.set_major_locator(ticker.MaxNLocator(10))
                if self.__xaxis['col'] in self.__df.columns:
                    xcol = self.__df[self.__xaxis['col']].values
                else:
                    xcol = self.__df.index.values
                def mydate(x, pos):
                    try:
                        if self.__xaxis['converter'] == None:
                            return x
                        else:
                            return self.__xaxis['converter'](xcol[int(x)])
                    except IndexError:
                        return ''
                ax.xaxis.set_major_formatter(ticker.FuncFormatter(mydate))
            else:
                # x軸目盛り非表示
                ax.tick_params(labelbottom=False, bottom=False)

            # 枠線設定
            axis=['top','bottom','left','right']
            line_width=[1, 1, 1, 1]
            for a,w in zip(axis, line_width):
                ax.spines[a].set_visible(True)
                ax.spines[a].set_linewidth(w)
                ax.spines[a].set_color('dimgray')

            # 背景色設定
            color_idx = ax_idx % len(self.__backcolor)
            ax.patch.set_facecolor(self.__backcolor[color_idx])
            ax.set_axisbelow(True) # グリッドがプロットした点や線の下に隠れる

            #メモリの長さ,太さ, ラベルサイズの調整
            ax.tick_params(direction='out', length=1, width=1, labelsize=10)

            #ax.ticklabel_format(useOffset=False, style='plain') # オフセットと科学表記を無効
            ax.yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True)) # Y軸目盛りを10のべき乗表記

            # インジケータ設定
            has_label = False
            for indi in self.__indicators[k]:
                # candlestick
                if indi['type'] == 'candlestick':
                    mpf.candlestick2_ohlc(ax,
                                          opens=self.__df[indi['open']].values,
                                          highs=self.__df[indi['high']].values,
                                          lows=self.__df[indi['low']].values,
                                          closes=self.__df[indi['close']].values,
                                          width=indi['width'],
                                          colorup=indi['upcolor'],
                                          colordown=indi['downcolor'])
                # line
                elif indi['type'] == 'line':
                    ax.plot(lst_x, self.__df[indi['y']], color=indi['color'], linewidth=indi['linewidth'], linestyle=indi['linestyle'], label=indi['label'])
                # bar
                elif indi['type'] == 'bar':
                    ax.bar(lst_x, self.__df[indi['y']], color=indi['color'], width=indi['width'], label=indi['label'])
                # mark
                elif indi['type'] == 'mark':
                    ax.scatter(lst_x, self.__df[indi['y']], marker=indi['marker'], s=indi['size'], c=indi['color'])
                # band
                elif indi['type'] == 'band':
                    ax.fill_between(lst_x, self.__df[indi['y1']], self.__df[indi['y2']], where=self.__df[indi['y1']] >= self.__df[indi['y2']],
                             facecolor=indi['upcolor'], alpha=indi['alpha'], interpolate=True)
                    ax.fill_between(lst_x, self.__df[indi['y1']], self.__df[indi['y2']], where=self.__df[indi['y1']] <= self.__df[indi['y2']],
                             facecolor=indi['downcolor'], alpha=indi['alpha'], interpolate=True)
                    ax.plot(lst_x, self.__df[indi['y1']], lst_x, self.__df[indi['y2']], color=indi['linecolor'], linewidth=indi['linewidth'], label=indi['label'])
                # ラベル設定チェック
                if indi['type'] != 'candlestick' and indi['label'] != None and len(indi['label']) > 0:
                    has_label = True

            # X軸グリッド
            ax.xaxis.grid(self.__xaxis['grid'], which='major', linestyle='dotted', color='lightgray')
            if k in self.__yaxis.keys():
                # Y軸グリッド
                ax.yaxis.grid(self.__yaxis[k]['grid'], which='major', linestyle='dotted', color='lightgray')
                # 凡例表示
                if self.__yaxis[k]['legend'] and has_label:
                    ax.legend()

            grid += g
            ax_idx += 1

    #---------------------------------------------------------------------------
    # 日付変換関数(クラスメソッド)
    #   set_x関数のconverterに使用する
    #---------------------------------------------------------------------------
    @classmethod
    def to_date_format(cls, x):
        # numpy.datetime64
        if isinstance(x, np.datetime64):
            return pd.to_datetime(x).strftime(cls.FormatX)
        # datetime
        elif isinstance(x, datetime):
            return x.strftime(cls.FormatX)
        # UnixTime
        elif Chart.is_numeric(x) and x > 1000000000:
            return pd.to_datetime(x, unit='s').strftime(cls.FormatX)
        else:
            return x

    @staticmethod
    def is_int(val) -> bool:
        try:
            int(val)
            return True
        except:
            return False

    @staticmethod
    def is_float(val) -> bool:
        try:
            float(val)
            return True
        except:
            return False

    @staticmethod
    def is_numeric(val) -> bool:
        return Chart.is_int(val) or Chart.is_float(val)
