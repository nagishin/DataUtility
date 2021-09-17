# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.style as mplstyle
import mplfinance.original_flavor as mpf
from matplotlib import ticker
from matplotlib.animation import FuncAnimation
import japanize_matplotlib
import seaborn as sns

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
        self.__dpi = 100
        self.__title = {'title': None, 'loc': 'center', 'fontsize': 16, 'obj':None,}
        self.__xaxis = {'col':None, 'grid':True, 'converter':None,}
        self.__yaxis = {0:{'title':None, 'grid':True, 'legend':False, 'gridspec':1, 'autoscale':True},}
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
        self.__axes = {}
        self.__ani = None
        self.__auto_scroll_range = 0
        self.__animation_obj = {'x_text': None, 'f_text': None, 'x_vlines': []}

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
    #  dpi      : DPI
    #---------------------------------------------------------------------------
    def set_size(self, width: int=16, height: int=12, dpi: int=100):
        if Chart.is_numeric(width) and width > 0:
            self.__width = width
        if Chart.is_numeric(height) and height > 0:
            self.__height = height
        if Chart.is_numeric(dpi) and dpi > 0:
            self.__dpi = dpi
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
    #  autoscale: 自動スケールON/OFF
    #
    # [複数チャートの高さ調整]
    # 各チャートのgridspec値の合計から各チャートの高さ比率が設定される
    #  ex) [ax0]gridspec=2, [ax1]gridspec=1, [ax2]gridspec=1の場合
    #      ax0 : ax1 : ax2の高さは 2:1:1 となる
    #---------------------------------------------------------------------------
    def set_y(self, ax: int=0, title: str=None, grid: bool=True, legend: bool=False, gridspec: int=1, autoscale: bool=True):
        if Chart.is_int(ax) and ax >= 0:
            if ax in self.__yaxis.keys():
                self.__yaxis[ax]['title'] = title
                self.__yaxis[ax]['grid'] = grid
                self.__yaxis[ax]['legend'] = legend
                self.__yaxis[ax]['gridspec'] = gridspec
                self.__yaxis[ax]['autoscale'] = autoscale
            else:
                self.__yaxis[ax] = {
                    'title': title,
                    'grid': grid,
                    'legend': legend,
                    'gridspec': gridspec,
                    'autoscale': autoscale,
                }
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
        plt.savefig(filepath, dpi=self.__dpi, bbox_inches='tight', pad_inches=0.2, transparent=False)

        plt.close()
        # plot設定初期化
        plt.rcdefaults()

    #---------------------------------------------------------------------------
    # アニメーションチャート作成
    # [params]
    #  filepath          : 保存するファイルパス(.gif/.html)
    #  step              : アニメーションで表示していくindex数
    #  interval          : 表示更新間隔[ms]
    #  auto_scroll_range : 自動スクロールするindex幅 (default:0->全体表示)
    #---------------------------------------------------------------------------
    def save_animation(self, filepath: str, step: int=1, interval: int=100, auto_scroll_range: int=0):
        split = os.path.splitext(filepath)
        if len(split) < 2:
            return
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in ['.gif', '.html']:
            return

        if self.__ani == None:
            self.__create_animation(step, interval, auto_scroll_range)

        # gifファイル出力
        if ext == '.gif':
            writer = 'pillow'  # 'pillow'/'imagemagick'
            self.__ani.save(filepath, writer=writer)

        # htmlファイル出力
        elif ext == '.html':
            html_video = self.__ani.to_html5_video()
            html_string = f'<html><head></head><body>{html_video}</body></html>'
            with open(filepath, 'w') as f:
                f.write(html_string)

        plt.close()
        # plot設定初期化
        plt.rcdefaults()


    #---------------------------------------------------------------------------
    # チャート作成
    #---------------------------------------------------------------------------
    def __create(self):
        # 言語設定
        sns.set(font='IPAexGothic')
        # マージン設定
        matplotlib.rcParams['axes.xmargin'] = 0.003 # X軸
        matplotlib.rcParams['axes.ymargin'] = 0.05  # Y軸
        # 高速スタイル設定
        mplstyle.use('fast')
        # グラフ設定
        self.__fig = plt.figure(figsize=(self.__width, self.__height), dpi=self.__dpi)
        self.__fig.autofmt_xdate()
        plt.subplots_adjust(wspace=0.0, hspace=0.0) # グラフ間余白

        # チャート配置割り
        grids = {k: self.__yaxis[k]['gridspec'] if k in self.__yaxis.keys() else 1 for k in self.__indicators.keys()}
        total_grid = sum(grids.values())
        #total_grid = len(self.__indicators.keys())
        gs = gridspec.GridSpec(total_grid, 1)

        # X軸列設定
        lst_x = range(len(self.__df.index))

        self.__animation_obj = {'x_text': None, 'f_text': None, 'x_vlines': []}
        self.__axes = {}
        ax_idx = 0
        grid = 0
        ax0 = None
        for k,g in grids.items():
            if grid == 0: # 最上段チャートはタイトル設定
                # axis作成
                ax = plt.subplot(gs[grid:grid+g, 0])
                ax0 = ax # X軸同期のため
                # タイトル
                self.__title['obj'] = ax.set_title(self.__title['title'], loc=self.__title['loc'], fontsize=self.__title['fontsize'])

                # アニメーション用フレームtext (default alpha=0)
                self.__animation_obj['f_text'] = ax.text(1, 1, 'text',
                                                         color='black',
                                                         #backgroundcolor='#2f4f4f',
                                                         alpha=0.0,
                                                         fontsize=11,
                                                         fontweight='medium',
                                                         fontstretch='normal',
                                                         #fontfamily='Impact',
                                                         horizontalalignment='right',
                                                         verticalalignment='bottom',
                                                         transform=ax.transAxes,
                                                         #style='italic',
                                                         )
            else:
                # axis作成
                ax = plt.subplot(gs[grid:grid+g, 0], sharex=ax0) # 最上段チャートにX軸同期

            # ax登録
            self.__axes[k] = ax

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

                # アニメーション用X軸text (default alpha=0)
                self.__animation_obj['x_text'] = ax.text(0, 0, 'text',
                                                         color='black',
                                                         #backgroundcolor='#2f4f4f',
                                                         alpha=0.0,
                                                         fontsize=12,
                                                         fontweight='medium',
                                                         fontstretch='normal',
                                                         #fontfamily='Impact',
                                                         horizontalalignment='center',
                                                         verticalalignment='top',
                                                         #transform=ax.transAxes,
                                                         #style='italic',
                                                         )

            else:
                # x軸目盛り非表示
                ax.tick_params(labelbottom=False, bottom=False)

            # アニメーション用X軸vline (default alpha=0)
            self.__animation_obj['x_vlines'].append(
                ax.axvline(x=0, color='dimgray', alpha=0.0, linestyle='--', linewidth=0.7)
            )

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
                    lines, patches = mpf.candlestick2_ohlc(ax,
                                          opens=self.__df[indi['open']].values,
                                          highs=self.__df[indi['high']].values,
                                          lows=self.__df[indi['low']].values,
                                          closes=self.__df[indi['close']].values,
                                          width=indi['width'],
                                          colorup=indi['upcolor'],
                                          colordown=indi['downcolor'])
                    # アニメーション用plotデータ
                    indi['plot_data'] = {
                        'range': { # spikes
                            'obj': lines,
                            'segments': lines.get_segments(),
                            'colors': lines.get_colors(),
                        },
                        'bar': { # bodies
                            'obj': patches,
                            'verts': [p.vertices for p in patches.get_paths()],
                            'edge_colors': patches.get_edgecolors(),
                            'face_colors': patches.get_facecolors(),
                        },
                    }

                # line
                elif indi['type'] == 'line':
                    lines = ax.plot(lst_x, self.__df[indi['y']], color=indi['color'], linewidth=indi['linewidth'], linestyle=indi['linestyle'], label=indi['label'])
                    # アニメーション用plotデータ
                    line = lines[0]  # lines: Line2D collection
                    data = line.get_data()
                    indi['plot_data'] = {
                        'obj': line,
                        'x': data[0],
                        'y': data[1],
                    }

                # bar
                elif indi['type'] == 'bar':
                    bars = ax.bar(lst_x, self.__df[indi['y']], color=indi['color'], width=indi['width'], label=indi['label'])
                    # アニメーション用plotデータ
                    indi['plot_data'] = {
                        'obj': bars, # Rectangle collection
                        'heights': [b.get_height() for b in bars],
                    }

                # mark
                elif indi['type'] == 'mark':
                    marks = ax.scatter(lst_x, self.__df[indi['y']], marker=indi['marker'], s=indi['size'], c=indi['color'])
                    # アニメーション用plotデータ
                    indi['plot_data'] = {
                        'obj': marks, # Path collection
                        'x': np.array(lst_x),
                        'y': self.__df[indi['y']].values,
                    }

                # band
                elif indi['type'] == 'band':
                    fill1 = ax.fill_between(lst_x, self.__df[indi['y1']], self.__df[indi['y2']], where=self.__df[indi['y1']] >= self.__df[indi['y2']],
                            facecolor=indi['upcolor'], alpha=indi['alpha'], interpolate=True, zorder=0)
                    fill2 = ax.fill_between(lst_x, self.__df[indi['y1']], self.__df[indi['y2']], where=self.__df[indi['y1']] <= self.__df[indi['y2']],
                            facecolor=indi['downcolor'], alpha=indi['alpha'], interpolate=True, zorder=0)
                    lines = ax.plot(lst_x, self.__df[indi['y1']], lst_x, self.__df[indi['y2']], color=indi['linecolor'], linewidth=indi['linewidth'], label=indi['label'])
                    # アニメーション用plotデータ
                    indi['plot_data'] = {
                        'obj': {
                            'line1': lines[0],
                            'line2': lines[1],
                            'fill1': fill1,  # PolyCollection
                            'fill2': fill2,  # PolyCollection
                        },
                        'x': np.array(lst_x),
                        'y1': self.__df[indi['y1']].values,
                        'y2': self.__df[indi['y2']].values,
                        'verts1': [p.vertices.copy() for p in fill1.get_paths()],
                        'verts2': [p.vertices.copy() for p in fill2.get_paths()],
                    }

                # ラベル設定チェック
                if indi['type'] != 'candlestick' and indi['label'] != None and len(indi['label']) > 0:
                    has_label = True

            # X軸グリッド
            ax.xaxis.grid(self.__xaxis['grid'], which='major', linestyle='dotted', color='lightgray')
            if k in self.__yaxis.keys():
                # Y軸グリッド
                ax.yaxis.grid(self.__yaxis[k]['grid'], which='major', linestyle='dotted', color='lightgray')
                # Y軸ラベル
                ax.set_ylabel(self.__yaxis[k]['title'], fontsize=12, color='dimgray')
                # 凡例表示
                if self.__yaxis[k]['legend'] and has_label:
                    ax.legend()

            grid += g
            ax_idx += 1

        # アニメーションオブジェクト位置調整
        max_ax = self.__axes[max(self.__axes.keys())]
        left, right = max_ax.get_xlim()
        bottom, top = max_ax.get_ylim()

        # x軸 vline
        for v in self.__animation_obj['x_vlines']:
            v.set_xdata(left)

        # x軸 text
        x_text = self.__animation_obj['x_text']
        x_text.set_position((left, bottom))

    #---------------------------------------------------------------------------
    # アニメーション作成
    #---------------------------------------------------------------------------
    def __create_animation(self, step, interval, auto_scroll_range):
        if self.__fig == None:
            self.__create()

        rows = len(self.__df.index) + 1
        self.__auto_scroll_range = auto_scroll_range
        self.__ani = FuncAnimation(fig=self.__fig, func=self.__update_animation, frames=range(0, rows, step),
                                   init_func=self.__init_animation, interval=interval, repeat=False, blit=True)

    #---------------------------------------------------------------------------
    # アニメーション初期処理
    #---------------------------------------------------------------------------
    def __init_animation(self):
        return self.__fig,

    #---------------------------------------------------------------------------
    # アニメーション更新処理
    #---------------------------------------------------------------------------
    def __update_animation(self, frame):
        if not self.__indicators:
            return

        # x: アニメーションindex描画範囲
        from_idx = 0
        to_idx = max(min(frame, len(self.__df.index)), from_idx)

        # x軸範囲設定
        if self.__auto_scroll_range > 0:
            lim_max_x = to_idx
            lim_min_x = max(to_idx - self.__auto_scroll_range, 0)
            lim_max_x = max(lim_min_x + self.__auto_scroll_range, lim_max_x)
            self.__axes[0].set_xlim(lim_min_x, lim_max_x)
        else:
            lim_min_x = 0
            lim_max_x = len(self.__df.index)

        # y軸最大範囲計算dict
        y_limit = {k: [sys.float_info.max, -sys.float_info.max] for k in self.__axes.keys()}

        # 各インジケータ更新
        for k, indies in self.__indicators.items():
            for indi in indies:
                if 'plot_data' not in indi.keys():
                    continue
                dic_data = indi['plot_data']

                # candlestick
                if indi['type'] == 'candlestick':
                    if 'range' not in dic_data.keys() or 'bar' not in dic_data.keys():
                        continue
                    dic_lines = dic_data['range']
                    dic_patches = dic_data['bar']
                    if 'obj' not in dic_lines.keys() or 'obj' not in dic_patches.keys():
                        continue
                    # spikes
                    lines = dic_lines['obj']
                    lines.set_segments(dic_lines['segments'][from_idx:to_idx])
                    lines.set_color(dic_lines['colors'][from_idx:to_idx])
                    lines.set_linewidth(2.0)
                    # bodies
                    patches = dic_patches['obj']
                    patches.set_verts(dic_patches['verts'][from_idx:to_idx])
                    patches.set_edgecolors(dic_patches['edge_colors'][from_idx:to_idx])
                    patches.set_facecolors(dic_patches['face_colors'][from_idx:to_idx])
                    # y軸範囲更新
                    if self.__yaxis[k]['autoscale']:
                        l = min(self.__df[indi['low']].values[lim_min_x:lim_max_x])
                        h = max(self.__df[indi['high']].values[lim_min_x:lim_max_x])
                    else:
                        l = min(self.__df[indi['low']].values)
                        h = max(self.__df[indi['high']].values)
                    y_limit[k][0] = min(y_limit[k][0], l)
                    y_limit[k][1] = max(y_limit[k][1], h)

                # line
                elif indi['type'] == 'line':
                    if 'obj' not in dic_data.keys():
                        continue
                    line = dic_data['obj']
                    line.set_data(dic_data['x'][from_idx:to_idx], dic_data['y'][from_idx:to_idx])
                    # y軸範囲更新
                    if self.__yaxis[k]['autoscale']:
                        l = min(self.__df[indi['y']].values[lim_min_x:lim_max_x])
                        h = max(self.__df[indi['y']].values[lim_min_x:lim_max_x])
                    else:
                        l = min(self.__df[indi['y']].values)
                        h = max(self.__df[indi['y']].values)
                    y_limit[k][0] = min(y_limit[k][0], l)
                    y_limit[k][1] = max(y_limit[k][1], h)

                # bar
                elif indi['type'] == 'bar':
                    if 'obj' not in dic_data.keys():
                        continue
                    bars = dic_data['obj']
                    heights = dic_data['heights']
                    [bar.set_height(heights[i] if ((i >= from_idx) & (i < to_idx)) else 0.0) for i, bar in enumerate(bars)]
                    # y軸範囲更新
                    if self.__yaxis[k]['autoscale']:
                        l = min(self.__df[indi['y']].values[lim_min_x:lim_max_x])
                        h = max(self.__df[indi['y']].values[lim_min_x:lim_max_x])
                    else:
                        l = min(self.__df[indi['y']].values)
                        h = max(self.__df[indi['y']].values)
                    y_limit[k][0] = min(y_limit[k][0], l)
                    y_limit[k][1] = max(y_limit[k][1], h)

                # mark
                elif indi['type'] == 'mark':
                    if 'obj' not in dic_data.keys():
                        continue
                    marks = dic_data['obj']
                    x = dic_data['x']
                    y = dic_data['y']
                    data = np.hstack((x[:to_idx, np.newaxis], y[:to_idx, np.newaxis]))
                    marks.set_offsets(data)
                    # y軸範囲更新
                    if self.__yaxis[k]['autoscale']:
                        l = min(self.__df[indi['y']].values[lim_min_x:lim_max_x])
                        h = max(self.__df[indi['y']].values[lim_min_x:lim_max_x])
                    else:
                        l = min(self.__df[indi['y']].values)
                        h = max(self.__df[indi['y']].values)
                    y_limit[k][0] = min(y_limit[k][0], l)
                    y_limit[k][1] = max(y_limit[k][1], h)

                # band
                elif indi['type'] == 'band':
                    if 'obj' not in dic_data.keys():
                        continue
                    line1 = dic_data['obj']['line1']
                    line2 = dic_data['obj']['line2']
                    fill1 = dic_data['obj']['fill1']
                    fill2 = dic_data['obj']['fill2']
                    x = dic_data['x']
                    y1 = dic_data['y1']
                    y2 = dic_data['y2']
                    verts1 = dic_data['verts1']
                    verts2 = dic_data['verts2']
                    # lines
                    line1.set_data(x[from_idx:to_idx], y1[from_idx:to_idx])
                    line2.set_data(x[from_idx:to_idx], y2[from_idx:to_idx])
                    # fill1
                    for i, path in enumerate(fill1.get_paths()):
                        verts = verts1[i]
                        min_x = min(verts[:, 0])
                        max_x = max(verts[:, 0])
                        if from_idx <= min_x and max_x <= to_idx - 1:
                            if np.all(path.vertices == verts):
                                continue
                        df = pd.DataFrame(verts.copy(), columns=['x', 'y'])
                        df.loc[df['x'] < from_idx, 'x'] = from_idx
                        df.loc[df['x'] > to_idx - 1, 'x'] = to_idx - 1
                        path.vertices = df.values
                    # fill2
                    for i, path in enumerate(fill2.get_paths()):
                        verts = verts2[i]
                        min_x = min(verts[:, 0])
                        max_x = max(verts[:, 0])
                        if from_idx <= min_x and max_x <= to_idx - 1:
                            if np.all(path.vertices == verts):
                                continue
                        df = pd.DataFrame(verts.copy(), columns=['x', 'y'])
                        df.loc[df['x'] < from_idx, 'x'] = from_idx
                        df.loc[df['x'] > to_idx - 1, 'x'] = to_idx - 1
                        path.vertices = df.values
                    # y軸範囲更新
                    if self.__yaxis[k]['autoscale']:
                        l1 = min(self.__df[indi['y1']].values[lim_min_x:lim_max_x])
                        h1 = max(self.__df[indi['y1']].values[lim_min_x:lim_max_x])
                        l2 = min(self.__df[indi['y2']].values[lim_min_x:lim_max_x])
                        h2 = max(self.__df[indi['y2']].values[lim_min_x:lim_max_x])
                    else:
                        l1 = min(self.__df[indi['y1']].values)
                        h1 = max(self.__df[indi['y1']].values)
                        l2 = min(self.__df[indi['y2']].values)
                        h2 = max(self.__df[indi['y2']].values)
                    y_limit[k][0] = min(y_limit[k][0], l1)
                    y_limit[k][1] = max(y_limit[k][1], h1)
                    y_limit[k][0] = min(y_limit[k][0], l2)
                    y_limit[k][1] = max(y_limit[k][1], h2)

        # y軸範囲設定
        for k, lim in y_limit.items():
            if lim[0] < lim[1] and lim[0] < sys.float_info.max and lim[1] > -sys.float_info.max:
                range_y = lim[1] - lim[0]
                margin_y = range_y * 0.05
                lim_min_y = lim[0] - margin_y
                lim_max_y = lim[1] + margin_y
                self.__axes[k].set_ylim(lim_min_y, lim_max_y)

        # x軸 vline設定
        cur_x = max(to_idx - 1, 0)
        for v in self.__animation_obj['x_vlines']:
            v.set_xdata(cur_x)
            v.set_alpha(1.0)

        # x軸 text設定
        cur_text = self.__animation_obj['x_text']
        # 透過率/枠設定
        cur_text.set_alpha(1.0)
        cur_text.set_bbox({
            'facecolor': 'white',
            'edgecolor': 'black',
            #'boxstyle': 'Round',
            'linewidth': 0.7,
            'alpha': 1.0,
            'pad': 2,
        })
        # ラベル設定
        xcol = self.__df[self.__xaxis['col']].values if self.__xaxis['col'] in self.__df.columns else self.__df.index.values
        text_x = str(xcol[cur_x]) if self.__xaxis['converter'] == None else str(self.__xaxis['converter'](xcol[int(cur_x)]))
        cur_text.set_text(text_x)
        # 位置設定
        max_ax = self.__axes[max(self.__axes.keys())]
        bottom, top = max_ax.get_ylim()
        cur_text.set_position((cur_x, bottom))

        # Frame text設定
        cur_text = self.__animation_obj['f_text']
        # 透過率/枠設定
        cur_text.set_alpha(1.0)
        # ラベル設定
        cur_text.set_text(f'Index: {lim_min_x}-{to_idx} / {len(self.__df.index)}')

        # タイトル設定
        #self.__title['obj'].set_text(f'{self.__title["title"]}  Frame: {frame}  Draw index:{lim_min_x} - {lim_max_x}')

        return self.__fig,


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
