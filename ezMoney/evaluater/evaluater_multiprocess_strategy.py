from functools import lru_cache
import os
from re import A
from tkinter import E
from typing import ItemsView
from venv import logger
import time
from py import log
import uuid
from filelock import FileLock
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import pandas_market_calendars as mcal
import pandas as pd
import akshare as ak
import gc
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.dates as mdates
import numpy as np
import sqlite3

from datetime import datetime, timedelta
from arrow import get
import pandas_market_calendars as mcal
import pandas as pd
import pandas_market_calendars as mcal
import akshare as ak
import json
import traceback
import sys
sys.path.append(r"D:\workspace\TradeX\ezMoney")
from http_request import build_http_request
from data_class import category_rank_class
from xtquant import xtdata
try:
    trade_date_df = ak.tool_trade_date_hist_sina()
    trade_date_list = trade_date_df["trade_date"].astype(str).tolist()
    trade_date_list.sort()
except:
    trade_date_list = []


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        return super(NpEncoder, self).default(obj)

def init_process():
    xtdata.connect(port=58611)

def get_current_date():
    """
    获取当前日期。

    返回:
        str: 当前日期的字符串表示，格式为"YYYY-MM-DD"。
    """
    return datetime.now().strftime("%Y-%m-%d")

def get_current_date_no_line():
    """
    获取当前日期。

    返回:
        str: 当前日期和时间的字符串表示，格式为"YYYYMMDD"。
    """
    return datetime.now().strftime("%Y%m%d")

def get_current_time():
    """
    获取当前时间。

    返回:
        str: 当前时间的字符串表示，格式为"HH:MM:SS"。
    """
    return datetime.now().strftime("%H:%M:%S")

def get_previous_date():
    """
    获取前一天的日期。

    返回:
        str: 前一天日期的字符串表示，格式为"YYYY-MM-DD"。
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def get_previous_date_no_line():
    """
    获取前一天的日期。

    返回:
        str: 前一天日期的字符串表示，格式为"YYYY-MM-DD"。
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

def get_day_of_week():
    """
    获取当前一周内的第几天。

    返回:
        int: 当前一周内的第几天，星期一为0，星期日为6。
    """
    return datetime.now().weekday()

def get_hour_of_day():
    """
    获取当前一天内的第几小时。

    返回:
        int: 当前一天内的第几小时，0到23。
    """
    return datetime.now().hour


def is_trading_day(current_date = get_current_date()):
    if '-' not in current_date:
        current_date = current_date[0:4] + '-' + current_date[4:6] + '-' + current_date[6:8]
    is_trade = current_date in trade_date_list
    if is_trade:
        return True, trade_date_list[trade_date_list.index(current_date) - 1]
    else:
        import datetime
        end_date_t = datetime.datetime.strptime(current_date, "%Y-%m-%d").date()
        while str(end_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
            end_date_t = end_date_t - datetime.timedelta(days=1)
        return False, str(end_date_t)


def is_trade_date(date_str):
    """
    判断给定日期是否为交易日。

    参数:
        date (str): 日期字符串，格式为"YYYY-MM-DD"。

    返回:
        bool: 如果是交易日，返回True；否则返回False。
    """
    # 创建A股交易日历
    shanghai_calendar = mcal.get_calendar('XSHG')
    current_date = pd.Timestamp(date_str).date()

    schedule = shanghai_calendar.schedule(start_date=current_date, end_date=current_date)

    return schedule.empty == False

def is_between_925_and_930():
    now = datetime.now()
    start_time = now.replace(hour=9, minute=25, second=38, microsecond=0)
    end_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return start_time <= now < end_time

def is_after_929():
    now = datetime.now()
    start_time = now.replace(hour=9, minute=28, second=0, microsecond=0)
    return now > start_time

def get_trade_dates_by_end(end_date, trade_days = 30):
    import datetime
    end_date_t = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    if str(end_date_t) != end_date:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD")
    # trade_date_df = ak.tool_trade_date_hist_sina()
    # trade_date_list = trade_date_df["trade_date"].astype(str).tolist()
    # trade_date_list.sort()
    while str(end_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
        end_date_t = end_date_t - datetime.timedelta(days=1)
    start_date_index = trade_date_list.index(str(end_date_t))- trade_days + 1
    return trade_date_list[start_date_index:start_date_index + trade_days]



def get_trade_dates(start_date, end_date, trade_days = 30):
    import datetime
    if not end_date:
        end_date = get_current_date()
    if not start_date:
        return get_trade_dates_by_end(end_date, trade_days)
    end_date_t = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    if str(end_date_t) != end_date:
        raise ValueError("end date日期格式错误，应为 YYYY-MM-DD")
    start_date_t = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    if str(start_date_t)!= start_date:
        raise ValueError("start date日期格式错误，应为 YYYY-MM-DD")
    # trade_date_df = ak.tool_trade_date_hist_sina()
    # trade_date_list = trade_date_df["trade_date"].astype(str).tolist()
    # trade_date_list.sort()
    while str(end_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
        end_date_t = end_date_t - datetime.timedelta(days=1)
    while str(start_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
        start_date_t = start_date_t + datetime.timedelta(days=1)
    start_date_index = trade_date_list.index(str(start_date_t))
    end_date_index = trade_date_list.index(str(end_date_t))
    if end_date_index < start_date_index:
        return []
    rslt =  trade_date_list[start_date_index:end_date_index + 1]
    if len(rslt) < trade_days:
        return rslt
    return rslt[-trade_days:]



def plot(df, column):
    
    # 设置中文字体
    mpl.rcParams['font.sans-serif'] = ['SimHei']  # 指定中文字体为 SimHei
    mpl.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    # 假设这是你的DataFrame，其中包含收益

    # 绘制收益曲线
    # 将日期列转换为日期类型
    # df['date'] = pd.to_datetime(df['date'])

    # # 设置日期列为索引
    # df.set_index('date', inplace=True)
    df.index = pd.to_datetime(df.index)
    # 绘制收益曲线
    plt.figure(figsize=(10, 6))  # 设置图表大小
    plt.plot(df.index, df[column], label='Return')
    plt.title('收益曲线')
    plt.xlabel('日期')
    plt.ylabel('收益率')
    plt.legend()  # 显示图例
    plt.grid(True)  # 显示网格线

    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    # plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=10))

    plt.show()




def caculate_returns(returns_df, row, extra_info=None, trade_frequcy = -1, trade_avg_days = -1, total_days = -1):
    r = {}
    cumulative_returns = (1 + returns_df[row]).cumprod()

    # 计算最大回撤
    cumulative_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()

    cumulative_returns_add = returns_df[row].cumsum()
    cumulative_max_add = cumulative_returns_add.cummax()
    drawdown_add = cumulative_returns_add - cumulative_max_add
    max_drawdown_add = drawdown_add.min()

    # 计算夏普比率
    risk_free_rate = 0.0  # 假设无风险利率为0
    sharpe_ratio = (returns_df[row].mean() - risk_free_rate) / returns_df[row].std()

    if 'sell_day' in returns_df.columns:
        mean_sell_day = returns_df['sell_day'].mean()
    else:
        mean_sell_day = -1
    # 计算总收益率
    total_return = cumulative_returns.iloc[-1] - 1

    # 计算波动率
    volatility = returns_df[row].std()

    # 计算总盈亏
    total_profit_loss = cumulative_returns.iloc[-1] - cumulative_returns.iloc[0]

    # 计算加和的收益
    sum_return = returns_df[row].sum()

    # 计算成功次数、胜率、平均盈利、平均亏损、最大盈利、最大亏损以及盈亏比
    profitable_trades = returns_df[row][returns_df[row] > 0].count()
    losing_trades = returns_df[row][returns_df[row] < 0].count()
    win_rate = profitable_trades / (profitable_trades + losing_trades) if (profitable_trades + losing_trades) > 0 else 0
    average_profit = returns_df[row][returns_df[row] > 0].mean() if profitable_trades > 0 else 0
    average_loss = returns_df[row][returns_df[row] < 0].mean() if losing_trades > 0 else 0
    max_profit = returns_df[row].max()
    max_loss = returns_df[row].min()
    total_trades = profitable_trades + losing_trades
    total_times = returns_df[row].count()
    trade_pct = total_times / total_trades
    profit_loss_ratio = average_profit / abs(average_loss) if average_loss != 0 else 0
    kelly_fraction = win_rate - ((1 - win_rate) / profit_loss_ratio) if profit_loss_ratio != 0 else 0
    return_per_day = total_return / total_times
    year_return = return_per_day * 240 / trade_frequcy if trade_frequcy > 0 else 0

    r['最大回撤'] =  max_drawdown
    r['加和的最大回撤'] =  max_drawdown_add
    r['夏普比率'] =  sharpe_ratio
    r['总收益率'] =  total_return
    r['波动率'] = volatility
    r['年化收益率'] = year_return
    r['总盈亏'] = total_profit_loss
    r['成功次数'] = profitable_trades
    r['失败次数'] = losing_trades
    r['总天数'] = total_times
    r['加和的收益'] = sum_return
    r['总交易次数'] = total_trades
    r['交易频率'] = trade_pct
    r['胜率'] = win_rate
    r['总天数'] = total_days
    r['自然日交易间隔'] = trade_avg_days
    r['平均盈利'] = average_profit
    r['平均亏损'] = average_loss
    r['最大盈利'] = max_profit
    r['最大亏损'] = max_loss
    r['盈亏比'] = profit_loss_ratio
    r['凯利公式最佳仓位'] = kelly_fraction
    r['平均卖天数'] = mean_sell_day
    r['止损止盈'] = extra_info
    

    return r



@lru_cache(maxsize=10000)
def get_first_tick_trade_amount(stock_code, datekey):
    import datetime
    import pandas as pd

    today = datetime.datetime.strptime(datekey, '%Y-%m-%d').date()

    time_0930 = datetime.time(9, 20, 0)

    dt_0930 = datetime.datetime.combine(today, time_0930)

    timestamp_0930 = dt_0930.timestamp()

    time_09305 = datetime.time(9, 26, 0)

    dt_09305 = datetime.datetime.combine(today, time_09305)

    timestamp_09305 = dt_09305.timestamp()

    tims = int(timestamp_0930*1000)

    tims5 = int(timestamp_09305*1000)
    import numpy as np
    n_data_key = datekey.replace('-', '')
    xtdata.download_history_data(stock_code, 'tick', n_data_key, n_data_key)
    all_tick_data = xtdata.get_market_data(stock_list=[stock_code], period='tick', start_time=n_data_key, end_time=n_data_key)
    if not all_tick_data or len(all_tick_data) == 0:
        print("all_tick_data is empty.")

    # 假设 all_tick_data['000759.SZ'] 是 numpy.void 数组
    if isinstance(all_tick_data[stock_code], np.ndarray) and all_tick_data[stock_code].dtype.type is np.void:
        df = pd.DataFrame(all_tick_data[stock_code].tolist(), columns=all_tick_data[stock_code].dtype.names)
    else:
        raise

    filtered_df = df[(df['time'] >= tims) & (df['time'] <= tims5)]

    # 按 time 列升序排序
    sorted_df = filtered_df.sort_values(by='time')

    # 取 time 最小的行
    min_time_row = sorted_df.tail(1)

    amount = min_time_row['amount']

    if len(amount) == 1:
        real_amount = amount.item()
    else:
        raise Exception(f"{stock_code}-{datekey}")

    return real_amount


hd_pct = 0.003

def group_filter_fx(group, filtered = True, fx_filtered = True, topn = 3, top_fx = 2, top_cx = 2, only_fx = False, enbale_industry= False, filter_amount = 0, all_stocks = None):
    if filter_amount > 0:
        masks = []
        first_tick_amounts = []  # 存储每行的 first_tick_amount
        
        # 遍历每一行并计算值
        for _, row in group.iterrows():
            if row['stock_code'].split('.')[0] not in all_stocks:
                masks.append(False)
                first_tick_amounts.append(0)
                continue
            stock_code = all_stocks[row['stock_code'].split('.')[0]]
            date_key = row['date_key']
                
            # 计算 first_tick_amount
            first_tick_amount = get_first_tick_trade_amount(stock_code, date_key)
            first_tick_amounts.append(first_tick_amount)  # 记录值
            if first_tick_amount > filter_amount:
                masks.append(True)
            else:
                print(f"过滤股票 {stock_code} 日期 {date_key} 过滤原因： first_tick_amount {first_tick_amount}")
                masks.append(False)
            # 生成过滤掩码
        
        # 将 first_tick_amount 添加到原始分组中
        group = group.copy()  # 避免 SettingWithCopyWarning
        group['first_tick_amount'] = first_tick_amounts
        
        # 应用过滤
        group = group[masks]
            
    if not filtered:
        valid_rows = group[(group['open_price'] > 0) & (group['next_day_open_price'] > 0) & (group['stock_rank'] <= topn) & (group['next_day_close_price'] > 0)]
        if len(valid_rows) > 0:
            valid_rows['return'] = valid_rows['next_day_open_price'] / valid_rows['open_price'] - 1
            valid_rows['real_return'] = valid_rows['return'] - hd_pct
            valid_rows['close_return'] = valid_rows['next_day_close_price'] / valid_rows['open_price'] - 1
            valid_rows['close_real_return'] = valid_rows['close_return'] - hd_pct
            avg_value = valid_rows['return'].mean()
            close_avg_value = valid_rows['close_return'].mean()
            rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
            if len(rank_one_row) > 0:
                # 将平均值赋给 rank 为 1 的行的指定列
                rank_one_row['return'] = avg_value
                rank_one_row['real_return'] = avg_value - hd_pct
                rank_one_row['close_return'] = close_avg_value
                rank_one_row['close_real_return'] = close_avg_value - hd_pct
                return rank_one_row
        else:
            rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
            if len(rank_one_row) > 0:
                rank_one_row['return'] = -10
                rank_one_row['real_return'] = -10
                rank_one_row['close_return'] = -10
                rank_one_row['close_real_return'] = -10
                return rank_one_row
    else:
        if fx_filtered:
            min_category_rank = group['max_block_category_rank'].min()
            
            industry_rank_one_row = group[group['max_industry_code_rank'] == 1].copy()
            if not industry_rank_one_row.empty and len(industry_rank_one_row) == 1 and enbale_industry:
                industry_rank_one_row['return'] = industry_rank_one_row['next_day_open_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['real_return'] = industry_rank_one_row['return'] - hd_pct
                industry_rank_one_row['close_return'] = industry_rank_one_row['next_day_close_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['close_real_return'] = industry_rank_one_row['close_return'] - hd_pct
                return industry_rank_one_row
            elif not industry_rank_one_row.empty and len(industry_rank_one_row) > 1 and enbale_industry:
                industry_rank_one_row = industry_rank_one_row[industry_rank_one_row['stock_rank'] == industry_rank_one_row['stock_rank'].min()]
                industry_rank_one_row['return'] = industry_rank_one_row['next_day_open_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['real_return'] = industry_rank_one_row['return'] - hd_pct
                industry_rank_one_row['close_return'] = industry_rank_one_row['next_day_close_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['close_real_return'] = industry_rank_one_row['close_return'] - hd_pct
                return industry_rank_one_row

            if min_category_rank > top_fx:
                if only_fx:
                    return group[group['max_block_category_rank'] < min_category_rank]
                rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
                if len(rank_one_row) > 0:
                    rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                    rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                    rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                    rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                    return rank_one_row
            else:
                category_filtered = group[(group['max_block_category_rank'] <= top_fx) & ((group['max_block_code_rank'] <= top_cx) | ((group['max_industry_code_rank'] <= top_cx) & (group['max_industry_code_rank'] > 0)))]
                if len(category_filtered) == 0:
                    if only_fx:
                        return group[group['max_block_category_rank'] < min_category_rank]
                    rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
                    if not rank_one_row.empty and len(rank_one_row) > 0:
                        rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                        rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                    return rank_one_row

                # result = category_filtered[category_filtered['max_block_code_rank'] == category_filtered['max_block_code_rank'].min()]

                result = category_filtered[category_filtered['stock_rank'] == category_filtered['stock_rank'].min()]
                if len(result) > 1:
                    result = result[result['stock_rank'] == result['stock_rank'].min()]
                result['return'] = result['next_day_open_price'] / result['open_price'] - 1
                result['real_return'] = result['return'] - hd_pct
                result['close_return'] = result['next_day_close_price'] / result['open_price'] - 1
                result['close_real_return'] = result['close_return'] - hd_pct
                return result
        else:
            rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
            if not rank_one_row.empty and len(rank_one_row) > 0:
                rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
            return rank_one_row



def group_filter(group, filtered = True, fx_filtered = True, topn = 3, top_fx = 2, top_cx = 2, only_fx = False, enbale_industry= False, filter_amount = 0, all_stocks = None):
    if filter_amount > 0:
        masks = []
        first_tick_amounts = []  # 存储每行的 first_tick_amount
        
        # 遍历每一行并计算值
        for _, row in group.iterrows():
            if row['stock_code'].split('.')[0] not in all_stocks:
                masks.append(False)
                first_tick_amounts.append(0)
                continue
            stock_code = all_stocks[row['stock_code'].split('.')[0]]
            date_key = row['date_key']
                
            # 计算 first_tick_amount
            first_tick_amount = get_first_tick_trade_amount(stock_code, date_key)
            first_tick_amounts.append(first_tick_amount)  # 记录值
            if first_tick_amount > filter_amount:
                masks.append(True)
            else:
                print(f"过滤股票 {stock_code} 日期 {date_key} 过滤原因： first_tick_amount {first_tick_amount}")
                masks.append(False)
            # 生成过滤掩码
        
        # 将 first_tick_amount 添加到原始分组中
        group = group.copy()  # 避免 SettingWithCopyWarning
        group['first_tick_amount'] = first_tick_amounts
        
        # 应用过滤
        group = group[masks]
    if not filtered:
        valid_rows = group[(group['open_price'] > 0) & (group['next_day_open_price'] > 0) & (group['stock_rank'] <= topn) & (group['next_day_close_price'] > 0)]
        if len(valid_rows) > 0:
            valid_rows['return'] = valid_rows['next_day_open_price'] / valid_rows['open_price'] - 1
            valid_rows['real_return'] = valid_rows['return'] - hd_pct
            valid_rows['close_return'] = valid_rows['next_day_close_price'] / valid_rows['open_price'] - 1
            valid_rows['close_real_return'] = valid_rows['close_return'] - hd_pct
            avg_value = valid_rows['return'].mean()
            close_avg_value = valid_rows['close_return'].mean()
            rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
            if len(rank_one_row) > 0:
                # 将平均值赋给 rank 为 1 的行的指定列
                rank_one_row['return'] = avg_value
                rank_one_row['real_return'] = avg_value - hd_pct
                rank_one_row['close_return'] = close_avg_value
                rank_one_row['close_real_return'] = close_avg_value - hd_pct
                return rank_one_row
        else:
            rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
            if len(rank_one_row) > 0:
                rank_one_row['return'] = -10
                rank_one_row['real_return'] = -10
                rank_one_row['close_return'] = -10
                rank_one_row['close_real_return'] = -10
                return rank_one_row
    else:
        if fx_filtered:
            min_category_rank = group['max_block_category_rank'].min()

            industry_rank_one_row = group[group['max_industry_code_rank'] == 1].copy()
            if not industry_rank_one_row.empty and len(industry_rank_one_row) == 1 and enbale_industry:
                industry_rank_one_row['return'] = industry_rank_one_row['next_day_open_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['real_return'] = industry_rank_one_row['return'] - hd_pct
                industry_rank_one_row['close_return'] = industry_rank_one_row['next_day_close_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['close_real_return'] = industry_rank_one_row['close_return'] - hd_pct
                return industry_rank_one_row
            elif not industry_rank_one_row.empty and len(industry_rank_one_row) > 1 and enbale_industry:
                industry_rank_one_row = industry_rank_one_row[industry_rank_one_row['stock_rank'] == industry_rank_one_row['stock_rank'].min()]
                industry_rank_one_row['return'] = industry_rank_one_row['next_day_open_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['real_return'] = industry_rank_one_row['return'] - hd_pct
                industry_rank_one_row['close_return'] = industry_rank_one_row['next_day_close_price'] / industry_rank_one_row['open_price'] - 1
                industry_rank_one_row['close_real_return'] = industry_rank_one_row['close_return'] - hd_pct
                return industry_rank_one_row
            
            if min_category_rank > top_fx:
                if only_fx:
                    return group[group['max_block_category_rank'] < min_category_rank]
                rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
                if len(rank_one_row) > 0:
                    rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                    rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                    rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                    rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                    return rank_one_row
            elif min_category_rank < 0:
                category_filtered = group[(group['max_block_category_rank'] > 0) & (group['max_block_category_rank'] <= top_fx) & (((group['max_block_code_rank'] <= top_cx) & (group['max_block_code_rank'] > 0)) | ((group['max_industry_code_rank'] <= top_cx) & (group['max_industry_code_rank'] > 0)))]
                if not category_filtered.empty and len(category_filtered) > 0:
                    category_filtered = category_filtered[category_filtered['stock_rank'] == category_filtered['stock_rank'].min()]
                    category_filtered['return'] = category_filtered['next_day_open_price'] / category_filtered['open_price'] - 1
                    category_filtered['real_return'] = category_filtered['return'] - hd_pct
                    category_filtered['close_return'] = category_filtered['next_day_close_price'] / category_filtered['open_price'] - 1
                    category_filtered['close_real_return'] = category_filtered['close_return'] - hd_pct
                    return category_filtered
                else:
                    rank_one_row = group[group['max_block_category_rank'] == min_category_rank]
                    if len(rank_one_row) > 0:
                        rank_one_row = rank_one_row[rank_one_row['stock_rank'] == rank_one_row['stock_rank'].min()].copy()
                        if not rank_one_row.empty and len(rank_one_row) > 0:
                            rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                            rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                            rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                            rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                            return rank_one_row
                    if only_fx:
                        return group[group['max_block_category_rank'] < min_category_rank]
                    rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
                    if not rank_one_row.empty and len(rank_one_row) > 0:
                        rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                        rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                        return rank_one_row
                    else:
                        raise Exception("No data.")
            else:
                result = group[(group['max_block_category_rank'] > 0) & (group['max_block_category_rank'] <= top_fx) & (((group['max_block_code_rank'] <= top_cx) & (group['max_block_code_rank'] > 0)) | ((group['max_industry_code_rank'] <= top_cx) & (group['max_industry_code_rank'] > 0)))]
                
                if result.empty or len(result) < 1:
                    if only_fx:
                        return group[group['max_block_category_rank'] < min_category_rank]
                    rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
                    if not rank_one_row.empty and len(rank_one_row) > 0:
                        rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                        rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                        return rank_one_row
                if len(result) > 1:
                    result = result[result['stock_rank'] == result['stock_rank'].min()]
                result['return'] = result['next_day_open_price'] / result['open_price'] - 1
                result['real_return'] = result['return'] - hd_pct
                result['close_return'] = result['next_day_close_price'] / result['open_price'] - 1
                result['close_real_return'] = result['close_return'] - hd_pct
                return result
        else:
            rank_one_row = group[group['stock_rank'] == group['stock_rank'].min()].copy()
            if not rank_one_row.empty and len(rank_one_row) > 0:
                rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
            return rank_one_row


# strategy_name = '低吸'

# sub_strategy_name = '低位N字低吸'

# max_stock_rank = 20


months = [ '202409', '202410', '202411', '202412', '202501', '202502', '202503', '202504', '202505', '202506', '202507', '202508']


# months = ['202501', '202502' ]

# 交易天数范围
trade_days_rang = [200, 25]
gaps = [0]
# 候选排名筛选
max_stock_ranks = [10, 5, 3]

# 方向前几

# 过滤函数
filter_funcs = [group_filter_fx]

# 计算的return
# return_names = ['r_return', 'r_close_return']

# block_rank_filter =  True
# rerank_category = True
except_is_ppps = [True]
except_is_tracks = [True, False]
# gap10_generate = [False, True]

filter_params = [
    {
        'filtered': True,
        'fx_filtered': False,
        'topn': 1,
        'top_fx': 2,
        'top_cx': 2,
        'only_fx': False,
        'enbale_industry': False,
        'filter_amount': [6000000, 8000000, 10000000]
    },
    {
        'filtered': True,
        'fx_filtered': True,
        'topn': 1,
        'top_fx': [1,2,101],
        'top_cx': [1,2,101],
        'only_fx': [True],
        'enbale_industry': [False],
        'filter_amount': [6000000, 8000000, 10000000]
    }
]

sell_use_opens = [True]
sell_days = [1,2,3,4]
zhisun_lines  = [0, -0.01, -0.02,-0.03,-0.04,-0.05,-0.06,-0.07,-0.08, -0.09, -0.10,-0.11,-0.12, -1]
zhiying_lines = [0, 0.01,0.02, 0.03, 0.04, 0.05, 0.06,0.07, 0.08, 0.09, 0.1, 2]


class ResultWriter:
    """批量结果写入器"""
    def __init__(self, output_path, batch_size=500):
        self.buffer = []
        self.output_path = output_path
        self.batch_size = batch_size
        self.lock_path = output_path + ".lock"
    
    def add(self, result):
        self.buffer.append(result)
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        if not self.buffer:
            return
        with FileLock(self.lock_path):
            with open(self.output_path, 'a', encoding='utf-8') as f:
                for item in self.buffer:
                    f.write(json.dumps(item, ensure_ascii=False, cls=NpEncoder) + '\n')
        self.buffer = []


def generate_filter_params(m):
    res = []
    filtered = m['filtered']
    fx_filtered = m['fx_filtered']
    topn = m['topn']
    top_fx = m['top_fx']
    top_cx = m['top_cx']
    only_fx = m['only_fx']
    enbale_industry = m['enbale_industry']
    filter_amount = m['filter_amount']

    if isinstance(enbale_industry, list):
        for e_i in enbale_industry:
            if isinstance(top_fx, list) and isinstance(only_fx, list) and isinstance(top_cx, list):
                for fx in top_fx:
                    for cx in top_cx:
                        for of in only_fx:
                            for fa in filter_amount:
                                res.append({
                                    'filtered': filtered,
                                    'fx_filtered': fx_filtered,
                                    'topn': topn,
                                    'top_fx': fx,
                                    'top_cx': cx,
                                    'only_fx': of,
                                    'enbale_industry': e_i,
                                    'filter_amount': fa
                                })
            else:
                for fa in filter_amount:
                    res.append({
                        'filtered': filtered,
                        'fx_filtered': fx_filtered,
                        'topn': topn,
                        'top_fx': top_fx,
                        'top_cx': top_cx,
                        'only_fx': only_fx,
                        'enbale_industry': e_i,
                        'filter_amount': fa
                    })
    else:
        for fa in filter_amount:
            res.append({
                        'filtered': filtered,
                        'fx_filtered': fx_filtered,
                        'topn': topn,
                        'top_fx': top_fx,
                        'top_cx': top_cx,
                        'only_fx': only_fx,
                        'enbale_industry': enbale_industry,
                        'filter_amount': fa
                    })        
    return res

@lru_cache(maxsize=10240)
def get_real_open_price(stock_code, datekey):
    import datetime

    today = datetime.datetime.strptime(datekey, '%Y-%m-%d').date()

    time_0930 = datetime.time(9, 29, 0)

    dt_0930 = datetime.datetime.combine(today, time_0930)

    timestamp_0930 = dt_0930.timestamp()

    time_09305 = datetime.time(9, 30, 5)

    dt_09305 = datetime.datetime.combine(today, time_09305)

    timestamp_09305 = dt_09305.timestamp()

    tims = int(timestamp_0930*1000)

    tims5 = int(timestamp_09305*1000)
    import numpy as np
    n_data_key = datekey.replace('-', '')
    xtdata.download_history_data(stock_code, 'tick', n_data_key, n_data_key)
    all_tick_data = xtdata.get_market_data(stock_list=[stock_code], period='tick', start_time=n_data_key, end_time=n_data_key)
    if not all_tick_data:
        print('No all_tick_data available.')
    # 假设 all_tick_data['000759.SZ'] 是 numpy.void 数组
    if isinstance(all_tick_data[stock_code], np.ndarray) and all_tick_data[stock_code].dtype.type is np.void:
        df = pd.DataFrame(all_tick_data[stock_code].tolist(), columns=all_tick_data[stock_code].dtype.names)
    else:
        raise

    filtered_df = df[(df['time'] >= tims) & (df['time'] <= tims5)]

    # 按 time 列升序排序
    sorted_df = filtered_df.sort_values(by='time')

    # 取 time 最小的行
    min_time_row = sorted_df.head(1)

    last_price = min_time_row['lastPrice']

    # 检查 Series 是否只有一个元素
    if len(last_price) == 1:
        last_price_real = last_price.item()
    else:
        raise Exception(f"{stock_code}-{datekey}")

    return last_price_real

@lru_cache(maxsize=1024)
def get_ranked_category_infos(date_key, except_is_ppp = True, except_is_track = False, gap = 10):
    # build_http_request.check_user_alive()
    categoryRankList = category_rank_class.build_category_rank_sort_list(date_key)
    block_rank_list = []
    for item in categoryRankList:
        if item == None:
            continue
        if item.stockType == 'industry':
            isPpp = item.isPpp
            num = item.num
            numChange = item.numChange
            isTrack = item.isTrack
            stockCode = item.categoryCode
            r  = {
                'isPpp': isPpp,
                'num': num,
                'numChange': numChange,
                'isTrack': isTrack,
                'blockCode': stockCode
            }
            block_rank_list.append(r)
        if item.blockRankList == None:
            continue
        block_rank_list.extend(item.blockRankList)

    if except_is_ppp:
        block_rank_list = [item for item in block_rank_list if not item['isPpp']]
    if except_is_track:
        block_rank_list = [item for item in block_rank_list if not item['isTrack']]

    sorted_block_rank_list = sorted(block_rank_list, key=lambda x: (-x['num'], -x['numChange']))
    rank_dict = {}
    prev_num = None
    current_rank = 1

    for idx, item in enumerate(sorted_block_rank_list):
        code = item['blockCode']
        num = item['num']

        if idx == 0:
            # 第一个元素直接赋初始排名
            rank_dict[code] = current_rank
            prev_num = num
            continue

        delta = 0
        diff = prev_num - num

        # 判断差值规则
        if abs(diff) <= 0.0001:
            delta = 0
        else:
            if gap == 0:
                delta = 1
            else:
                if diff > gap:
                    delta = int(diff // gap) + 1
                else:
                    delta = 1
        current_rank += delta
        rank_dict[code] = current_rank
        prev_num = num
    return rank_dict


@lru_cache(maxsize=1024)
def get_ranked_new_category_infos(date_key, except_is_ppp = True, except_is_track = True, gap = 10):
    # build_http_request.check_user_alive()
    categoryRankList = category_rank_class.build_category_rank_sort_list(date_key)
    if except_is_ppp:
        categoryRankList = [item for item in categoryRankList if not item.isPpp]
    if except_is_track:
        categoryRankList = [item for item in categoryRankList if not item.isTrack]
    

    sorted_block_rank_list = sorted(categoryRankList, key=lambda x: (-x.num, -x.numChange))
    rank_dict = {}
    prev_num = None
    current_rank = 1

    for idx, item in enumerate(sorted_block_rank_list):
        code = item.categoryCode
        num = item.num

        if idx == 0:
            # 第一个元素直接赋初始排名
            rank_dict[code] = current_rank
            prev_num = num
            continue

        delta = 0
        diff = prev_num - num

        # 判断差值规则
        if abs(diff) <= 0.0001:
            delta = 0
        else:
            if gap == 0:
                delta = 1
            else:
                if diff > gap:
                    delta = int(diff // gap) + 1
                else:
                    delta = 1
        current_rank += delta
        rank_dict[code] = current_rank
        prev_num = num
    return rank_dict


@lru_cache(maxsize=10240)
def get_stock_open_close_price(auction_code, date, next_date):
    if '-' in date or '-' in next_date:
        n_date = date.replace('-', '')
        n_next_date = next_date.replace('-', '')
    xtdata.download_history_data(auction_code, period='1d', start_time=n_date, end_time=n_next_date, incrementally = None)
    x1dpdata = xtdata.get_local_data(field_list=[], stock_list=[auction_code], period='1d', start_time=n_date, end_time=n_next_date, count=-1,
               dividend_type='none', fill_data=True)
    df = x1dpdata[auction_code]
    length = len(df)
    if length != 1:
        return -1, -1, -1, -1
    x_data = df.loc[n_date: n_next_date]['open'].astype(float)
    x_data_close = df.loc[n_date: n_next_date]['close'].astype(float)
    start_price = x_data[n_date]
    end_price = x_data[n_next_date]
    close_price = x_data_close[n_date]
    n_close_price = x_data_close[n_next_date]
    return start_price, close_price, end_price, n_close_price




def process_strategy(strategy_name, sub_strategy_name, last_100_trade_days, output_dir):
    try:
        print(f"strategy_name: {strategy_name}, sub_strategy_name: {sub_strategy_name}")
        
        print ("consumer_to_subscribe_whole connect success")
        
        file_name = f"{strategy_name}_{sub_strategy_name}_{uuid.uuid4().hex[:8]}.jsonl"
        output_path = os.path.join(output_dir, file_name)
        writer = ResultWriter(output_path)
        # 创建文件锁
        # for i in range(0, len(months)):
        all_stocks = {}
        all_stocks_info = xtdata.get_stock_list_in_sector('沪深A股')
        for stock in all_stocks_info:
            if stock.startswith('60') or stock.startswith('00'):
                cde = stock.split('.')[0]
                all_stocks[cde] = stock

        combined_df = pd.DataFrame()
        conn = sqlite3.connect('D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db')
        for month in months[:]:
            db_name = 'strategy_data_aftermarket_%s' % month
            if sub_strategy_name != strategy_name: 
                query = "select * from %s where (strategy_name = '%s' and sub_strategy_name = '%s' and stock_rank <= %s) " % (db_name, strategy_name, sub_strategy_name, 20)
            else:
                query = "select * from %s where (strategy_name = '%s' and stock_rank <= %s) " % (db_name, strategy_name, 20)
            df = pd.read_sql_query(query, conn)
            df = df.dropna(axis=1, how='all')
            combined_df = pd.concat([combined_df, df], axis=0)
        conn.close()
        combined_df = combined_df.reset_index(drop=True)
        if len(combined_df) < 1:
            return

        combined_df = combined_df[(combined_df['open_price'] > 0) & (combined_df['next_day_open_price'] > 0) & (combined_df['next_day_close_price'] > 0)]
        if len(combined_df) < 1:
            return

        combined_df = combined_df.sort_values(by='date_key', ascending=False)
            
        for trade_days in trade_days_rang:

            print(len(combined_df))
            
            # 获取最近的 7 个不同的 date_key
            latest_trade_dates = combined_df['date_key'].unique()[:trade_days]

            # 筛选出最近 7 个 date_key 对应的行
            a_trade_df = combined_df[combined_df['date_key'].isin(latest_trade_dates)]

            if len(a_trade_df) < trade_days - 1:
                continue
            # 重置索引
            for gap in gaps:
                trade_df = a_trade_df.reset_index(drop=True)
                for except_is_ppp in except_is_ppps:
                    for except_is_track in except_is_tracks:
                        for idx, row in trade_df.iterrows():
                            block_category = row['block_category']
                            block_codes = row['block_codes']
                            industry_code = row['industry_code']
                            date_key = row['date_key']
                            ranked_block_dict = get_ranked_category_infos(date_key, gap = gap, except_is_ppp = except_is_ppp, except_is_track = except_is_track)
                            min_rank = 100
                            if not block_codes:
                                continue
                            else:
                                for block_code in block_codes.split(','):
                                    if block_code in ranked_block_dict:
                                        rank_this = ranked_block_dict[block_code]
                                        min_rank = min(min_rank, rank_this)
                            if not industry_code:
                                trade_df.loc[idx, 'max_block_code_rank'] = min_rank
                                continue
                            else:
                                i_min_rank = 100
                                for i_code in industry_code.split(','):
                                    if i_code in ranked_block_dict:
                                        rank_this = ranked_block_dict[i_code]
                                        min_rank = min(min_rank, rank_this)
                                        i_min_rank = min(i_min_rank, rank_this)
                                        trade_df.loc[idx, 'max_industry_code_rank'] = i_min_rank
                                trade_df.loc[idx, 'max_block_code_rank'] = min_rank
                        for idx, row in trade_df.iterrows():
                            block_category = row['block_category']
                            date_key = row['date_key']
                            ranked_category_dict = get_ranked_new_category_infos(date_key, gap = gap, except_is_ppp=except_is_ppp, except_is_track=except_is_track)
                            min_rank = 100
                            if not block_category:
                                continue
                            for block_code in block_category.split(','):
                                if block_code in ranked_category_dict:
                                    rank_this = ranked_category_dict[block_code]
                                    min_rank = min(min_rank, rank_this)
                            trade_df.loc[idx, 'max_block_category_rank'] = min_rank
                
                        for max_stock_rank in max_stock_ranks:
                            trade_df = trade_df[trade_df['stock_rank'] <= max_stock_rank]

                            for filter_fuc in filter_funcs:
                                for filter_param in filter_params:
                                    params_list = generate_filter_params(filter_param)
                                    for param_dict in params_list:
                                        start_time = time.time()
                                        import warnings
                                        df = None
                                        # 临时忽略 DeprecationWarning 警告
                                        param_dict['all_stocks'] = all_stocks
                                        with warnings.catch_warnings():
                                            warnings.filterwarnings("ignore", category=DeprecationWarning)
                                            df = trade_df.groupby(['date_key', 'strategy_name', 'sub_strategy_name']).apply(filter_fuc, **param_dict).reset_index(drop=True)
                                        end_time = time.time()
                                        elapsed_time = end_time - start_time
                                        print(f"filter 函数执行耗时: {elapsed_time} 秒 - {sub_strategy_name}")
                                        # df = df.drop(['block_category_info'], axis=1)
                                        # 将索引设置为 date_key 列
                                        if len(df) < 1:
                                            continue

                                        df = df[(df['open_price'] > 0) & (df['next_day_open_price'] > 0) & (df['next_day_close_price'] > 0)]
                                        df['real_open'] = -1.0

                                        for i in range(1, 11):
                                            df[f'close_{i}'] = -1.0
                                            df[f'low_{i}'] = -1.0
                                        
                                        for idx, row in df.iterrows():
                                            stock_code = row['stock_code']
                                            if stock_code.split('.')[0] not in all_stocks:
                                                df.loc[idx, 'real_open'] = -1.0
                                                continue
                                            stock_code = all_stocks[stock_code.split('.')[0]]
                                            date_key = row['date_key']
                                            n_data_key = date_key
                                            if '-' in n_data_key:
                                                n_data_key = n_data_key.replace('-', '')

                                            real_open_price = get_real_open_price(stock_code, date_key)
                                            df.loc[idx, 'real_open'] = real_open_price

                                        df = df[df['real_open'] > 0]
                                        
                                        n_last_100_trade_days = sorted(last_100_trade_days, reverse=False)
                                        for index, row in df.iterrows():
                                            stock_code = row['stock_code']
                                            date_key = row['date_key']
                                            stock_code = all_stocks[stock_code.split('.')[0]]
                                            date_key_index = n_last_100_trade_days.index(date_key)
                                            after_trade_days = n_last_100_trade_days[date_key_index+1:date_key_index+11]
                                            for idx, day in enumerate(after_trade_days):
                                                open_price, close_price, _, _ = get_stock_open_close_price(stock_code, day, day)
                                                if open_price > 0:
                                                    # with warnings.catch_warnings():
                                                    #     warnings.filterwarnings("ignore", category=FutureWarning)
                                                    df.loc[index, f'low_{idx+1}'] = open_price
                                                    df.loc[index, f'close_{idx+1}'] = close_price

                                        df['r_return'] = df['next_day_open_price']/df['real_open'] - 1
                                        df['r_return'] = df['r_return']-0.001
                                        df['r_close_return'] = df['next_day_close_price']/df['real_open'] - 1
                                        df['r_close_return'] = df['r_close_return']-0.001

                                        min_date_key = df['date_key'].min()

                                        if min_date_key not in last_100_trade_days:
                                            print(f'min_date_key: {min_date_key}')
                                            raise
                                        min_date_trade_days = last_100_trade_days.index(min_date_key) + 1

                                        trade_frequency = min_date_trade_days / len(df)


                                        import datetime
                                        if not isinstance(min_date_key, datetime.datetime):
                                            min_date_key = pd.to_datetime(min_date_key)

                                        # 获取当前日期
                                        current_date = datetime.datetime.now()
                                        time_interval = current_date - min_date_key
                                        first_trade_interval = time_interval.days

                                        trade_avg_days = first_trade_interval / len(df)

                                        df = df.set_index('date_key')
                                        # 对索引进行排序
                                        df = df.sort_index()

                                        max_rate = -100
                                        max_rate_info = ""

                                        max_rate_r = {}

                                        max_return = -100
                                        max_return_info = ""
                                        max_return_r = {}

                                        max_ykb = -100
                                        max_ykb_info = ""
                                        max_ykb_r = {}

                                        min_hc = -100
                                        min_hc_info = ""
                                        min_hc_r = {}
                                        
                                        codes_dict = df['stock_name'].to_dict()
                                        json_codes_data = json.dumps(codes_dict, ensure_ascii=False, indent=4, cls=NpEncoder)
                                        start_time = time.time()
                                        for sell_use_open in sell_use_opens:
                                            for sell_day in sell_days:
                                                for zhisun_line in zhisun_lines:
                                                    for zhiying_line in zhiying_lines:
                                                        extra_info = f'zhisun_{sell_day}_{zhisun_line}_{zhiying_line}_{sell_use_open}'
                                                        ndf = df.copy()
                                                        ndf = ndf[ndf['real_open'] > 0]
                                                        for date_key, row in ndf.iterrows():
                                                            real_open = row['real_open']
                                                            ndf.at[date_key, 'sy'] = -100.0
                                                            ndf.at[date_key,'sell_day'] = -1
                                                            for i in range(1, sell_day+1):
                                                                if sell_use_open:
                                                                    cs = row[f'low_{i}']
                                                                    if cs < 0:
                                                                        if i == 1:
                                                                            continue
                                                                        else:
                                                                            cs = row[f'low_{i-1}']
                                                                    if cs < 0:
                                                                        continue
                                                                    sy = cs / real_open - 1
                                                                    if sy < zhisun_line:
                                                                        ndf.at[date_key, 'sy'] = sy
                                                                        ndf.at[date_key,'sell_day'] = i
                                                                        break
                                                                    if sy > zhiying_line:
                                                                        ndf.at[date_key,'sy'] = sy
                                                                        ndf.at[date_key,'sell_day'] = i
                                                                        break

                                                                cs = row[f'close_{i}']
                                                                if cs < 0:
                                                                    if i == 1:
                                                                        continue
                                                                    else:
                                                                        cs = row[f'close_{i-1}']
                                                                if cs < 0:
                                                                    continue
                                                                if i == sell_day:
                                                                    cs = row[f'close_{i}']
                                                                    ndf.at[date_key,'sy'] = cs / real_open - 1
                                                                    ndf.at[date_key,'sell_day'] = i
                                                                    break
                                                                sy = cs / real_open - 1
                                                                if sy < zhisun_line:
                                                                    ndf.at[date_key, 'sy'] = sy
                                                                    ndf.at[date_key,'sell_day'] = i
                                                                    break
                                                                if sy > zhiying_line:
                                                                    ndf.at[date_key,'sy'] = sy
                                                                    ndf.at[date_key,'sell_day'] = i
                                                                    break
                                                        ndf = ndf[ndf['sy'] > -99]
                                                        if len(ndf) == 0:
                                                            continue
                                                        r= caculate_returns(ndf,'sy', extra_info=extra_info, trade_frequcy=trade_frequency, trade_avg_days=trade_avg_days, total_days=first_trade_interval)
                                                        if r['胜率'] > max_rate:
                                                            max_rate_info = extra_info
                                                            max_rate = max(max_rate, r['胜率'])
                                                            max_rate_r = r.copy()
                                                            max_rate_r['开盘卖'] = sell_use_open
                                                            max_rate_r['交易日候选数'] = max_stock_rank
                                                            max_rate_r['交易策略'] =  strategy_name
                                                            max_rate_r['交易子策略'] =  sub_strategy_name
                                                            max_rate_r['交易明细'] =  json_codes_data
                                                            max_rate_r['最近交易日数'] = trade_days

                                                            if 'all_stocks' in param_dict:
                                                                del param_dict['all_stocks']
                                                            max_rate_r['过滤参数'] = json.dumps(param_dict, ensure_ascii=False, indent=4, cls=NpEncoder)
                                                            if param_dict['filtered'] and param_dict['fx_filtered'] and param_dict['only_fx']:
                                                                max_rate_r['强方向过滤'] = 1
                                                            else:
                                                                max_rate_r['强方向过滤'] = 0

                                                            max_rate_r['except_is_ppp'] = except_is_ppp
                                                            max_rate_r['except_is_track'] = except_is_track
                                                        if r['加和的收益'] > max_return:
                                                            max_return_info = extra_info
                                                            max_return = max(max_return, r['加和的收益'])
                                                            max_return_r = r.copy()
                                                            max_return_r['开盘卖'] = sell_use_open
                                                            max_return_r['交易日候选数'] = max_stock_rank
                                                            max_return_r['交易策略'] =  strategy_name
                                                            max_return_r['交易子策略'] =  sub_strategy_name
                                                            max_return_r['交易明细'] =  json_codes_data
                                                            max_return_r['最近交易日数'] = trade_days

                                                            if 'all_stocks' in param_dict:
                                                                del param_dict['all_stocks']
                                                            max_return_r['过滤参数'] = json.dumps(param_dict, ensure_ascii=False, indent=4, cls=NpEncoder)
                                                            if param_dict['filtered'] and param_dict['fx_filtered'] and param_dict['only_fx']:
                                                                max_return_r['强方向过滤'] = 1
                                                            else:
                                                                max_return_r['强方向过滤'] = 0

                                                            max_return_r['except_is_ppp'] = except_is_ppp
                                                            max_return_r['except_is_track'] = except_is_track

                                                        if r['夏普比率'] > max_ykb:
                                                            max_ykb_info = extra_info
                                                            max_ykb = max(max_ykb, r['夏普比率'])
                                                            max_ykb_r = r.copy()
                                                            max_ykb_r['开盘卖'] = sell_use_open
                                                            max_ykb_r['交易日候选数'] = max_stock_rank
                                                            max_ykb_r['交易策略'] =  strategy_name
                                                            max_ykb_r['交易子策略'] =  sub_strategy_name
                                                            max_ykb_r['交易明细'] =  json_codes_data
                                                            max_ykb_r['最近交易日数'] = trade_days

                                                            if 'all_stocks' in param_dict:
                                                                del param_dict['all_stocks']
                                                            max_ykb_r['过滤参数'] = json.dumps(param_dict, ensure_ascii=False, indent=4, cls=NpEncoder)
                                                            if param_dict['filtered'] and param_dict['fx_filtered'] and param_dict['only_fx']:
                                                                max_ykb_r['强方向过滤'] = 1
                                                            else:
                                                                max_ykb_r['强方向过滤'] = 0

                                                            max_ykb_r['except_is_ppp'] = except_is_ppp
                                                            max_ykb_r['except_is_track'] = except_is_track
                                                        if r['加和的最大回撤'] > min_hc:
                                                            min_hc_info = extra_info
                                                            min_hc = max(min_hc, r['加和的最大回撤'])
                                                            min_hc_r = r.copy()
                                                            min_hc_r['开盘卖'] = sell_use_open
                                                            min_hc_r['交易日候选数'] = max_stock_rank
                                                            min_hc_r['交易策略'] =  strategy_name
                                                            min_hc_r['交易子策略'] =  sub_strategy_name
                                                            min_hc_r['交易明细'] =  json_codes_data
                                                            min_hc_r['最近交易日数'] = trade_days

                                                            if 'all_stocks' in param_dict:
                                                                del param_dict['all_stocks']
                                                            min_hc_r['过滤参数'] = json.dumps(param_dict, ensure_ascii=False, indent=4, cls=NpEncoder)
                                                            if param_dict['filtered'] and param_dict['fx_filtered'] and param_dict['only_fx']:
                                                                min_hc_r['强方向过滤'] = 1
                                                            else:
                                                                min_hc_r['强方向过滤'] = 0

                                                            min_hc_r['except_is_ppp'] = except_is_ppp
                                                            min_hc_r['except_is_track'] = except_is_track

                                        writer.add(max_rate_r)
                                        writer.add(max_return_r)
                                        writer.add(max_ykb_r)
                                        writer.add(min_hc_r)
                                        end_time = time.time()
                                        elapsed_time = end_time - start_time
                                        print(f"卖出搜索函数执行耗时: {elapsed_time} 秒 - {sub_strategy_name}")
                                        print(f"add writer once. {strategy_name}-{sub_strategy_name}")
                                                
                                    gc.collect()


        writer.flush()
    except Exception as e:
        print(f"Error processing strategy: {strategy_name}, sub_strategy_name: {sub_strategy_name}")
        print(e)
        traceback.print_exc()
        stack_trace = traceback.format_exc()
        print(stack_trace)

if __name__ == '__main__':

    from xtquant import xtdatacenter as xtdc
    xtdc.set_token("26e6009f4de3bfb2ae4b89763f255300e96d6912")

    print('xtdc.init')
    xtdc.init() # 初始化行情模块，加载合约数据，会需要大约十几秒的时间
    print('done')
    listen_addr = xtdc.listen(port = 58611)
    print(f'done, listen_addr:{listen_addr}')

    import yaml
    file_name = r'D:\workspace\TradeX\ezMoney\roll_back.yml'
    with open(file_name, 'r',  encoding='utf-8') as file:
        config = yaml.safe_load(file)
        if config is None or 'configs' not in config:
            print("Config No data Error.")

    configs = config['configs']
    m = {}
    cur_day = datetime.now().strftime("%Y-%m-%d")

    
    
    filter_strategy_names = []
    total_args = 'Strategy-'
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == 'a':
                # filter_strategy_names.extend(['低吸', 'xiao_cao_1j2db_1', 'xiao_cao_1j2db', 'xiao_cao_dwyxdx','xiao_cao_dwdx_a'])
                filter_strategy_names.extend(['低吸'])
                total_args = total_args + '低吸'
            elif arg == 'b':
                filter_strategy_names.append('追涨')
                total_args = total_args + '追涨'
            elif arg == 'c':
                filter_strategy_names.append('接力')
                total_args = total_args + '接力'
            else:
                continue
        else:
            print("No arguments provided.")
    
    if not filter_strategy_names:
        # total_args = 'total'
        filter_strategy_names = ['低吸', '追涨', '接力']
    
    # filter_sub_strategy_names = ['低位高强低吸', '低位孕线低吸', '放宽低吸前3', '高强低吸', '高强中低开低吸', '高位高强中低开低吸', '连断低吸', '绿盘低吸', '低位低吸', '中位低吸', '中位断板低吸', '中位高强中低开低吸', '低位中强追涨', '小高开追涨', '中位孕线低吸', 'N', '孕线']

    # filter_sub_strategy_names = []
    for config in configs:
       strategy_name=config['strategy_name']
       sub_tasks = config['sub_tasks']
       if not sub_tasks:
           m[strategy_name] = [strategy_name]
           continue
       for sub_task in sub_tasks:
            sub_strategy_name = sub_task['name']
            if sub_strategy_name:
                # if sub_strategy_name not in filter_sub_strategy_names:
                    # continue
                if strategy_name in m:
                    m[strategy_name].append(sub_strategy_name)
                else:
                    m[strategy_name] = []
                    m[strategy_name].append(sub_strategy_name)

    last_100_trade_days = get_trade_dates_by_end(get_current_date(), 250)
    last_100_trade_days.sort(reverse=True)

    print("last_100_trade_days = ", last_100_trade_days)

    l_days = len(last_100_trade_days)

   
    import concurrent.futures

    # ... existing code ...

    from concurrent.futures import ProcessPoolExecutor
    # from multiprocessing import Manager

    # 创建一个可在进程间共享的列表
    # manager = Manager()
    # results = manager.list()
    build_http_request.check_user_alive()
    
    output_dir = f'D:\\workspace\\TradeX\\ezMoney\\evaluater\\eval\\eval_{cur_day}\\{total_args}\\'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with ProcessPoolExecutor(max_workers=10, initializer=init_process) as executor:
        futures = []
        for strategy_name, sub_strategy_names in m.items():
            if strategy_name not in filter_strategy_names:
                continue
            for sub_strategy_name in sub_strategy_names:
                future = executor.submit(process_strategy, strategy_name, sub_strategy_name, last_100_trade_days, output_dir)
                print(f'add task {strategy_name} - {sub_strategy_name}')
                futures.append(future)

        # 等待所有任务完成
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred: {e}")

    # ... existing code ...
    import json
    all_results = []
    for file in os.listdir(output_dir):
        if file.endswith('.jsonl'):
            with open(os.path.join(output_dir, file), 'r', encoding='utf-8') as f:
                for line in f:
                    all_results.append(json.loads(line))
    
    sve_df = pd.DataFrame(all_results)        

    sve_df = sve_df.drop_duplicates(subset=['交易策略', '交易子策略', '交易明细', '最近交易日数', '强方向过滤', '交易日候选数', '过滤参数'], keep='last')
    column_order = ['交易策略', '交易子策略', '交易明细', '最近交易日数', '开盘卖', '止损止盈', '强方向过滤', '交易日候选数','except_is_ppp', 'except_is_track', '平均卖天数', '过滤参数', '最大回撤','加和的最大回撤', '夏普比率', '总收益率', '波动率', '年化收益率', '总盈亏','加和的收益','成功次数','失败次数', '总天数','总交易次数','交易频率','自然日交易间隔','胜率','平均盈利','平均亏损','最大盈利','最大亏损','盈亏比','凯利公式最佳仓位']
    sve_df = sve_df[column_order]

    # 假设 df 已经定义
    # 按照 交易策略、交易子策略、最近交易日数 进行分组
    grouped = sve_df.groupby(['交易策略', '交易子策略', '最近交易日数'])

    for rg in [(0 , 1.5), (1.5, 3), (3, 5), (5,7), (7,10), (10, 50)]:
        for sd in [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]:
            min_freq, max_freq = rg
            min_sd, max_sd = sd
            # 筛选出交易频率在指定范围内的数据
            filtered_df = grouped.apply(lambda x: x[(x['自然日交易间隔'] > min_freq) & (x['自然日交易间隔'] <= max_freq)]).reset_index(drop=True)
            # 过滤平均卖出天数在指定范围内的数据
            filtered_df = filtered_df[(filtered_df['平均卖天数'] >= min_sd) & (filtered_df['平均卖天数'] < max_sd)]
            # 重置索引
            filtered_df = filtered_df.reset_index(drop=True)

            max_return = filtered_df.groupby(['交易策略', '交易子策略', '最近交易日数']).apply(lambda x: x.nlargest(2, '总收益率')).reset_index(drop=True)
            max_return = max_return.sort_values(by='总收益率', ascending=False)
            
            min_drawdown = filtered_df.groupby(['交易策略', '交易子策略', '最近交易日数']).apply(lambda x: x.nlargest(2, '最大回撤')).reset_index(drop=True)
            min_drawdown = min_drawdown.sort_values(by='最大回撤', ascending=False)

            max_win_rate = filtered_df.groupby(['交易策略', '交易子策略', '最近交易日数']).apply(lambda x: x.nlargest(2, '胜率')).reset_index(drop=True)
            max_win_rate = max_win_rate.sort_values(by='胜率', ascending=False)

            max_ykb = filtered_df.groupby(['交易策略', '交易子策略', '最近交易日数']).apply(lambda x: x.nlargest(2, '夏普比率')).reset_index(drop=True)
            max_ykb = max_ykb.sort_values(by='夏普比率', ascending=False)

            dir_path = os.path.dirname(f'D:\\workspace\\TradeX\\ezMoney\\evaluater\\eval_results\\{cur_day}\\sell_day_{max_sd}\\freq_{max_freq}\\{total_args}\\')

            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            # sve_df.to_excel(f'{dir_path}\\eval_results.xlsx')

            for dayns in trade_days_rang:
                with pd.ExcelWriter(f'{dir_path}\\result_sheets_{dayns}.xlsx') as writer:
                    
                    sv_max_return = max_return[(max_return['最近交易日数'] == dayns)].reset_index(drop=True)
                    sv_max_return = sv_max_return.sort_values(by='总收益率', ascending=False)
                    sv_max_return.to_excel(writer, sheet_name=f'max_return')
                    
                    sv_max_return = min_drawdown[(min_drawdown['最近交易日数'] == dayns)].reset_index(drop=True)
                    sv_max_return = sv_max_return.sort_values(by='最大回撤', ascending=False)
                    sv_max_return.to_excel(writer, sheet_name=f'min_drawdown')

                    sv_max_return = max_win_rate[(max_win_rate['最近交易日数'] == dayns)].reset_index(drop=True)
                    sv_max_return = sv_max_return.sort_values(by='胜率', ascending=False)
                    sv_max_return.to_excel(writer, sheet_name=f'max_win_rate')

                    sv_max_return = max_ykb[(max_ykb['最近交易日数'] == dayns)].reset_index(drop=True)
                    sv_max_return = sv_max_return.sort_values(by='夏普比率', ascending=False)
                    sv_max_return.to_excel(writer, sheet_name=f'max_ykb')



            max_return.to_excel(f'{dir_path}\\max_return_results.xlsx')
            min_drawdown.to_excel(f'{dir_path}\\min_drawdown_results.xlsx')
            max_win_rate.to_excel(f'{dir_path}\\max_win_rate_results.xlsx')
            max_ykb.to_excel(f'{dir_path}\\max_ykb_results.xlsx')