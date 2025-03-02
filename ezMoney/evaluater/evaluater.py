import multiprocessing
import os
from re import A
from tkinter import E
from typing import ItemsView
from venv import logger

from py import log
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
from xtquant import xttrader
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import pandas_market_calendars as mcal
import pandas as pd
import akshare as ak

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.dates as mdates

import sqlite3

from datetime import datetime, timedelta
from arrow import get
import pandas_market_calendars as mcal
import pandas as pd
import pandas_market_calendars as mcal
import akshare as ak


try:
    trade_date_df = ak.tool_trade_date_hist_sina()
    trade_date_list = trade_date_df["trade_date"].astype(str).tolist()
    trade_date_list.sort()
except:
    trade_date_list = []


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




def caculate_returns(returns_df, row, _print = False, trade_frequcy = -1, trade_avg_days = -1, total_days = -1):
    r = {}
    cumulative_returns = (1 + returns_df[row]).cumprod()

    # 计算最大回撤
    cumulative_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()

    # 计算夏普比率
    risk_free_rate = 0.0  # 假设无风险利率为0
    sharpe_ratio = (returns_df[row].mean() - risk_free_rate) / returns_df[row].std()

    # 计算总收益率
    total_return = cumulative_returns.iloc[-1] - 1

    # 计算波动率
    volatility = returns_df[row].std()

    # 计算总盈亏
    total_profit_loss = cumulative_returns.iloc[-1] - cumulative_returns.iloc[0]

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
    profit_loss_ratio = average_profit / abs(average_loss) if average_loss != 0 else 0
    kelly_fraction = win_rate - ((1 - win_rate) / profit_loss_ratio) if profit_loss_ratio != 0 else 0
    return_per_day = total_return / total_times
    year_return = return_per_day * 240 / trade_frequcy if trade_frequcy > 0 else 0

    r['最大回撤'] =  max_drawdown
    r['夏普比率'] =  sharpe_ratio
    r['总收益率'] =  total_return
    r['波动率'] = volatility
    r['年化收益率'] = year_return
    r['总盈亏'] = total_profit_loss
    r['成功次数'] = profitable_trades
    r['失败次数'] = losing_trades
    r['总天数'] = total_days
    r['总交易次数'] = total_trades
    r['交易频率'] = trade_frequcy
    r['自然日交易间隔'] = trade_avg_days
    r['胜率'] = win_rate
    r['平均盈利'] = average_profit
    r['平均亏损'] = average_loss
    r['最大盈利'] = max_profit
    r['最大亏损'] = max_loss
    r['盈亏比'] = profit_loss_ratio
    r['凯利公式最佳仓位'] = kelly_fraction
    if _print:
        print(f"最大回撤: {max_drawdown:.2%}")
        print(f"夏普比率: {sharpe_ratio:.2f}")
        print(f"总收益率: {total_return:.2%}")
        print(f"年化收益率: {year_return:.2%}")
        print(f"波动率: {volatility:.2%}")
        print(f"总盈亏: {total_profit_loss:.2%}")
        print(f"成功次数: {profitable_trades}")
        print(f"失败次数: {losing_trades}")
        print(f"总天数: {total_times}")
        print(f"总交易次数: {total_trades}")
        print(f"交易频率: {trade_frequcy:.2%}")
        print(f"胜率: {win_rate:.2%}")
        print(f"平均盈利: {average_profit:.2%}")
        print(f"平均亏损: {average_loss:.2%}")
        print(f"最大盈利: {max_profit:.2%}")
        print(f"最大亏损: {max_loss:.2%}")
        print(f"盈亏比: {profit_loss_ratio:.2f}")
        print(f"凯利公式最佳仓位: {kelly_fraction:.2%}")

    return r

hd_pct = 0.003

def group_filter_fx(group, filtered = True, fx_filtered = True, topn = 3, top_fx = 2, top_cx = 2, only_fx = False, enbale_industry= False):
    if not filtered:
        valid_rows = group[(group['open_price'] > 0) & (group['next_day_open_price'] > 0) & (group['stock_rank'] <= topn) & (group['next_day_close_price'] > 0)]
        if len(valid_rows) > 0:
            valid_rows['return'] = valid_rows['next_day_open_price'] / valid_rows['open_price'] - 1
            valid_rows['real_return'] = valid_rows['return'] - hd_pct
            valid_rows['close_return'] = valid_rows['next_day_close_price'] / valid_rows['open_price'] - 1
            valid_rows['close_real_return'] = valid_rows['close_return'] - hd_pct
            avg_value = valid_rows['return'].mean()
            close_avg_value = valid_rows['close_return'].mean()
            rank_one_row = group[group['stock_rank'] == 1].copy()
            if len(rank_one_row) > 0:
                # 将平均值赋给 rank 为 1 的行的指定列
                rank_one_row['return'] = avg_value
                rank_one_row['real_return'] = avg_value - hd_pct
                rank_one_row['close_return'] = close_avg_value
                rank_one_row['close_real_return'] = close_avg_value - hd_pct
                return rank_one_row
        else:
            rank_one_row = group[group['stock_rank'] == 1].copy()
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
                rank_one_row = group[group['stock_rank'] == 1].copy()
                if len(rank_one_row) > 0:
                    rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                    rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                    rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                    rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                    return rank_one_row
            else:
                category_filtered = group[(group['max_block_category_rank'] <= top_fx) & ((group['max_block_code_rank'] <= top_cx) | (group['max_industry_code_rank'] <= top_cx))]
                if len(category_filtered) == 0:
                    if only_fx:
                        return group[group['max_block_category_rank'] < min_category_rank]
                    rank_one_row = group[group['stock_rank'] == 1].copy()
                    if not rank_one_row.empty and len(rank_one_row) > 0:
                        rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                        rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                        rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
                    return rank_one_row

                result = category_filtered[category_filtered['max_block_code_rank'] == category_filtered['max_block_code_rank'].min()]
                if len(result) > 1:
                    result = result[result['stock_rank'] == result['stock_rank'].min()]
                result['return'] = result['next_day_open_price'] / result['open_price'] - 1
                result['real_return'] = result['return'] - hd_pct
                result['close_return'] = result['next_day_close_price'] / result['open_price'] - 1
                result['close_real_return'] = result['close_return'] - hd_pct
                return result
        else:
            rank_one_row = group[group['stock_rank'] == 1].copy()
            if not rank_one_row.empty and len(rank_one_row) > 0:
                rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
            return rank_one_row



def group_filter(group, filtered = True, fx_filtered = True, topn = 3, top_fx = 2, top_cx = 2, only_fx = False, enbale_industry= False):
    if not filtered:
        valid_rows = group[(group['open_price'] > 0) & (group['next_day_open_price'] > 0) & (group['stock_rank'] <= topn) & (group['next_day_close_price'] > 0)]
        if len(valid_rows) > 0:
            valid_rows['return'] = valid_rows['next_day_open_price'] / valid_rows['open_price'] - 1
            valid_rows['real_return'] = valid_rows['return'] - hd_pct
            valid_rows['close_return'] = valid_rows['next_day_close_price'] / valid_rows['open_price'] - 1
            valid_rows['close_real_return'] = valid_rows['close_return'] - hd_pct
            avg_value = valid_rows['return'].mean()
            close_avg_value = valid_rows['close_return'].mean()
            rank_one_row = group[group['stock_rank'] == 1].copy()
            if len(rank_one_row) > 0:
                # 将平均值赋给 rank 为 1 的行的指定列
                rank_one_row['return'] = avg_value
                rank_one_row['real_return'] = avg_value - hd_pct
                rank_one_row['close_return'] = close_avg_value
                rank_one_row['close_real_return'] = close_avg_value - hd_pct
                return rank_one_row
        else:
            rank_one_row = group[group['stock_rank'] == 1].copy()
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
                rank_one_row = group[group['stock_rank'] == 1].copy()
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
                    rank_one_row = group[group['stock_rank'] == 1].copy()
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
                    rank_one_row = group[group['stock_rank'] == 1].copy()
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
            rank_one_row = group[group['stock_rank'] == 1].copy()
            if not rank_one_row.empty and len(rank_one_row) > 0:
                rank_one_row['return'] = rank_one_row['next_day_open_price'] / rank_one_row['open_price'] - 1
                rank_one_row['real_return'] = rank_one_row['return'] - hd_pct
                rank_one_row['close_return'] = rank_one_row['next_day_close_price'] / rank_one_row['open_price'] - 1
                rank_one_row['close_real_return'] = rank_one_row['close_return'] - hd_pct
            return rank_one_row


# strategy_name = '低吸'

# sub_strategy_name = '低位N字低吸'

max_stock_rank = 20


months = [ '202409', '202410', '202411', '202412', '202501', '202502' ]

# months = ['202501', '202502' ]

# 交易天数范围
trade_days_rang = [3, 5, 7, 10, 15, 20, 30, 50]

# 候选排名筛选
max_stock_ranks = [10, 5, 3, 2]

# 方向前几

# 过滤函数
filter_funcs = [group_filter_fx, group_filter]

# 计算的return
return_names = ['close_real_return', 'real_return']


filter_params = [
    {
        'filtered': False,
        'fx_filtered': True,
        'topn': [2,3,4],
        'top_fx': 1,
        'top_cx': 2,
        'only_fx': False,
        'enbale_industry': False
    },
    {
        'filtered': True,
        'fx_filtered': False,
        'topn': 1,
        'top_fx': 2,
        'top_cx': 2,
        'only_fx': False,
        'enbale_industry': False
    },
    {
        'filtered': True,
        'fx_filtered': True,
        'topn': 1,
        'top_fx': [1,2,3,4],
        'top_cx': [1,2,3,4],
        'only_fx': [False, True],
        'enbale_industry': [False, True]
    }
]


def generate_filter_params(m):
    res = []
    filtered = m['filtered']
    fx_filtered = m['fx_filtered']
    topn = m['topn']
    top_fx = m['top_fx']
    top_cx = m['top_cx']
    only_fx = m['only_fx']
    enbale_industry = m['enbale_industry']
    if isinstance(topn, list):
        for n in topn:
            res.append({
                'filtered': filtered,
                'fx_filtered': fx_filtered,
                'topn': n,
                'top_fx': top_fx,
                'top_cx': top_cx,
                'only_fx': only_fx,
                'enbale_industry': enbale_industry
            })

    elif isinstance(enbale_industry, list):
        for e_i in enbale_industry:
            if isinstance(top_fx, list) and isinstance(only_fx, list) and isinstance(top_cx, list):
                for fx in top_fx:
                    for cx in top_cx:
                        for of in only_fx:
                            res.append({
                                'filtered': filtered,
                                'fx_filtered': fx_filtered,
                                'topn': topn,
                                'top_fx': fx,
                                'top_cx': cx,
                                'only_fx': of,
                                'enbale_industry': e_i
                            })
            else:
                res.append({
                    'filtered': filtered,
                    'fx_filtered': fx_filtered,
                    'topn': topn,
                    'top_fx': top_fx,
                    'top_cx': top_cx,
                    'only_fx': only_fx,
                    'enbale_industry': e_i
                })
    else:
        res.append(m)
        
    return res

if __name__ == '__main__':

    import yaml
    file_name = r'D:\workspace\TradeX\ezMoney\roll_back.yml'
    with open(file_name, 'r',  encoding='utf-8') as file:
        config = yaml.safe_load(file)
        if config is None or 'configs' not in config:
            print("Config No data Error.")

    configs = config['configs']
    cur_day = get_current_date()
    m = {}

    for config in configs:
       strategy_name=config['strategy_name']
       sub_tasks = config['sub_tasks']
       if not sub_tasks:
           m[strategy_name] = [strategy_name]
           continue
       for sub_task in sub_tasks:
            sub_strategy_name = sub_task['name']
            if sub_strategy_name:
                if strategy_name in m:
                    m[strategy_name].append(sub_strategy_name)
                else:
                    m[strategy_name] = []
                    m[strategy_name].append(sub_strategy_name)

    last_100_trade_days = get_trade_dates_by_end(get_current_date(), 200)
    last_100_trade_days.sort(reverse=True)

    print("last_100_trade_days = ", last_100_trade_days)

    l_days = len(last_100_trade_days)

    results = []

    for strategy_name, sub_strategy_names in m.items():
        for sub_strategy_name in sub_strategy_names:
            # if sub_strategy_name != '中位低吸':
            #     continue
            print(f"strategy_name: {strategy_name}, sub_strategy_name: {sub_strategy_name}")
            # for i in range(0, len(months)):

            combined_df = pd.DataFrame()
            for month in months[:]:
                conn = sqlite3.connect('D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db')
                db_name = 'strategy_data_aftermarket_%s' % month
                if sub_strategy_name != strategy_name: 
                    query = "select * from %s where (strategy_name = '%s' and sub_strategy_name = '%s' and stock_rank <= %s) " % (db_name, strategy_name, sub_strategy_name, 20)
                else:
                    query = "select * from %s where (strategy_name = '%s' and stock_rank <= %s) " % (db_name, strategy_name, 20)
                df = pd.read_sql_query(query, conn)
                combined_df = pd.concat([combined_df, df], axis=0)
            combined_df = combined_df.reset_index(drop=True)
            if len(combined_df) < 1:
                continue

            combined_df = combined_df[(combined_df['open_price'] > 0) & (combined_df['next_day_open_price'] > 0) & (combined_df['next_day_close_price'] > 0)]
            if len(combined_df) < 1:
                continue

            combined_df = combined_df.sort_values(by='date_key', ascending=False)
                
            for trade_days in trade_days_rang:

                print(len(combined_df))
                
                # 获取最近的 7 个不同的 date_key
                latest_trade_dates = combined_df['date_key'].unique()[:trade_days]

                # 筛选出最近 7 个 date_key 对应的行
                trade_df = combined_df[combined_df['date_key'].isin(latest_trade_dates)]

                if len(trade_df) < trade_days - 1:
                    continue
                # 重置索引
                trade_df = trade_df.reset_index(drop=True)

                for max_stock_rank in max_stock_ranks:
                    trade_df = trade_df[trade_df['stock_rank'] <= max_stock_rank]

                    for filter_fuc in filter_funcs:
                        for filter_param in filter_params:
                            params_list = generate_filter_params(filter_param)
                            for param_dict in params_list:
                                import warnings
                                df = None
                                # 临时忽略 DeprecationWarning 警告
                                with warnings.catch_warnings():
                                    warnings.filterwarnings("ignore", category=DeprecationWarning)
                                    df = trade_df.groupby(['date_key', 'strategy_name', 'sub_strategy_name']).apply(filter_fuc, **param_dict).reset_index(drop=True)
                               
                                # df = df.drop(['block_category_info'], axis=1)
                                # 将索引设置为 date_key 列
                                if len(df) < 1:
                                    continue

                                df = df[(df['open_price'] > 0) & (df['next_day_open_price'] > 0) & (df['next_day_close_price'] > 0)]
                                
                                
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
                                import json

                                for return_name in return_names:
                                    r = caculate_returns(df, return_name, _print=False, trade_frequcy=trade_frequency, trade_avg_days=trade_avg_days, total_days=first_trade_interval)
                                    codes_dict = df['stock_name'].to_dict()
                                    json_codes_data = json.dumps(codes_dict, ensure_ascii=False, indent=4)

                                    
                                    r['交易策略'] =  strategy_name
                                    r['交易子策略'] =  sub_strategy_name
                                    r['交易明细'] =  json_codes_data
                                    r['最近交易日数'] = trade_days
                                    r['交易日候选数'] = max_stock_rank
                                    r['过滤函数'] =  '空方向优先' if filter_fuc == group_filter_fx else '方向优先'
                                    r['过滤参数'] = json.dumps(param_dict, ensure_ascii=False, indent=4)
                                    r['收益计算方式'] = return_name
                                    if param_dict['filtered'] and param_dict['fx_filtered'] and param_dict['only_fx']:
                                        r['强方向过滤'] = 1
                                    else:
                                        r['强方向过滤'] = 0
                                    results.append(r)
                                    
    sve_df = pd.DataFrame(results)
    column_order = ['交易策略', '交易子策略', '交易明细', '最近交易日数', '强方向过滤', '收益计算方式', '交易日候选数', '过滤函数', '过滤参数', '最大回撤', '夏普比率', '总收益率', '波动率', '年化收益率', '总盈亏','成功次数','失败次数', '总天数','总交易次数','交易频率','自然日交易间隔','胜率','平均盈利','平均亏损','最大盈利','最大亏损','盈亏比','凯利公式最佳仓位']
    sve_df = sve_df[column_order]

    dir_path = os.path.dirname(f'D:\\workspace\\TradeX\\ezMoney\\evaluater\\eval\\')

    # 假设 df 已经定义
    # 按照 交易策略、交易子策略、最近交易日数 进行分组
    grouped = sve_df.groupby(['交易策略', '交易子策略', '最近交易日数', '收益计算方式'])

    # 筛选出总收益率最大且交易频率 <= 3 的数据
    max_return = grouped.apply(lambda x: x[x['交易频率'] <= 5].nlargest(1, '总收益率')).reset_index(drop=True)
    max_return = max_return.sort_values(by='总收益率', ascending=False)

    # 筛选出回撤最小且交易频率 <= 3 的数据
    min_drawdown = grouped.apply(lambda x: x[x['交易频率'] <= 5].nlargest(1, '最大回撤')).reset_index(drop=True)
    min_drawdown = min_drawdown.sort_values(by='最大回撤', ascending=False)

    # 筛选出胜率最高且交易频率 <= 3 的数据
    max_win_rate = grouped.apply(lambda x: x[x['交易频率'] <= 3].nlargest(1, '胜率')).reset_index(drop=True)
    max_win_rate = max_win_rate.sort_values(by='胜率', ascending=False)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    sve_df.to_excel(f'{dir_path}\\eval_results.xlsx')

    for dayns in trade_days_rang:
        for return_type in return_names:
            excel_file_name = f'{return_type}_max_return_{dayns}.xlsx'
            sv_max_return = max_return[(max_return['最近交易日数'] == dayns) & (max_return['收益计算方式'] == return_type)].reset_index(drop=True)
            sv_max_return = sv_max_return.sort_values(by='总收益率', ascending=False)
            sv_max_return.to_excel(f'{dir_path}\\{excel_file_name}')
    
    for dayns in trade_days_rang:
        for return_type in return_names:
            excel_file_name = f'{return_type}_min_drawdown_{dayns}.xlsx'
            sv_max_return = min_drawdown[(min_drawdown['最近交易日数'] == dayns) & (min_drawdown['收益计算方式'] == return_type)].reset_index(drop=True)
            sv_max_return = sv_max_return.sort_values(by='最大回撤', ascending=False)
            sv_max_return.to_excel(f'{dir_path}\\{excel_file_name}')

    for dayns in trade_days_rang:
        for return_type in return_names:
            excel_file_name = f'{return_type}_max_win_rate_{dayns}.xlsx'
            sv_max_return = max_win_rate[(max_win_rate['最近交易日数'] == dayns) & (max_win_rate['收益计算方式'] == return_type)].reset_index(drop=True)
            sv_max_return = sv_max_return.sort_values(by='胜率', ascending=False)
            sv_max_return.to_excel(f'{dir_path}\\{excel_file_name}')


    max_return.to_excel(f'{dir_path}\\max_return_results.xlsx')
    min_drawdown.to_excel(f'{dir_path}\\min_drawdown_results.xlsx')
    max_win_rate.to_excel(f'{dir_path}\\max_win_rate_results.xlsx')