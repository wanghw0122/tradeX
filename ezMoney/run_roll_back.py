import multiprocessing
import os
from re import A, X
from typing import ItemsView

from py import log
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
# from http_request import build_http_request
# from http_request import http_context
# from data_class import *
from strategy.strategy import sm
from logger import catch, logger
from trade.qmtTrade import *
from xtquant import xttrader
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
from date_utils import date
from apscheduler.schedulers.background import BackgroundScheduler
import time

# 设置环境变量
import threading
import queue
from multiprocessing import Queue

import pandas_market_calendars as mcal
import pandas as pd
import datetime


def get_target_codes(retry_times=3, date=date.get_current_date()):
    if retry_times <= 0:
        return None
    auction_codes = []
    position = 0.3
    try:
        items = sm.run_strategys(date)
        if items == None:
            return None
        if len(items) == 0:
            return None
        if 'xiao_cao_env' in items:
            xiaocao_envs = items['xiao_cao_env'][0]
            position = get_position(xiaocao_envs)
        for _, arr in items.items():
            if type(arr) != list:
                continue
            for item in arr:
                if item == None:
                    continue
                auction_codes.append(item.split('.')[0])
    except Exception as e:
        logger.error(f"An error occurred in get_target_codes: {e}")
        auction_codes = get_target_codes(retry_times-1, date)
    return auction_codes, position

def compute_return(auction_code, date, next_date):
    logger.info(f"开始计算股票{auction_code}在{date}的收益...")
    logger.info(f"开始下载股票{auction_code}在{date}的历史数据...")
    if '-' in date or '-' in next_date:
        n_date = date.replace('-', '')
        n_next_date = next_date.replace('-', '')
    xtdata.download_history_data(auction_code, period='1d', start_time=n_date, end_time=n_next_date, incrementally = None)
    x1dpdata = xtdata.get_local_data(field_list=[], stock_list=[auction_code], period='1d', start_time=n_date, end_time=n_next_date, count=-1,
               dividend_type='none', fill_data=True)
    df = x1dpdata[auction_code]
    length = len(df)
    if length != 2:
        logger.error(f"股票{auction_code}在{date}, {next_date}的历史数据长度不为2，长度为{length}")
        raise
    x_data = df.loc[n_date: n_next_date]['open'].astype(float)
    start_price = x_data[n_date]
    end_price = x_data[n_next_date]
    result = (end_price - start_price) / start_price
    logger.info(f"股票{auction_code}在{date}的收益为{result}， 开始价格为{start_price}, 结束价格为{end_price}")
    return result

def get_position(xiaocao_envs):
    if xiaocao_envs == None or len(xiaocao_envs) == 0:
        return 0.3
    env_10cm_qs = xiaocao_envs['9A0001']
    env_10cm_cd = xiaocao_envs['9B0001']
    env_10cm_qp = xiaocao_envs['9C0001']
    positions = (0.3, 0.4, 0.3)
    lifts = []
    try:
        for env in [env_10cm_qs, env_10cm_cd, env_10cm_qp]:
            if env == None:
                continue
            cur_lift = 0.0
            realShortLineScore = env.realShortLineScore
            realTrendScore = env.realTrendScore
            preRealShortLineScore = env.preRealShortLineScore
            preRealTrendScore = env.preRealTrendScore
            liftShortScore = realShortLineScore - preRealShortLineScore
            liftTrendScore = realTrendScore - preRealTrendScore
            if realShortLineScore and realShortLineScore > 0:
                cur_lift = cur_lift + (0.01 * realShortLineScore)
            if realTrendScore and realTrendScore > 0:
                cur_lift = cur_lift + (0.007 * realTrendScore)
            if liftShortScore and liftShortScore > 0:
                cur_lift = cur_lift + 0.004 * liftShortScore
            if liftTrendScore and liftTrendScore > 0:
                cur_lift = cur_lift + 0.002 * liftTrendScore
            lifts.append(cur_lift)
    except Exception as e:
        logger.error(f"An error occurred in get_position: {e}")
    if len(lifts) != 3:
        return 0.3
    lift = lifts[0] * positions[0]  + lifts[1] * positions[1] + lifts[2] * positions[2]
    return max(min(0.3 + lift, 1.0), 0.3)

if __name__ == "__main__":

    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    code_map = {}
    for stock in all_stocks:
        if stock.startswith('60') or stock.startswith('00'):
            code = stock.split('.')[0]
            code_map[code] = stock
    logger.info(f"构建全市场股票字典完毕。 共{len(code_map)}个")

    trade_days = date.get_trade_dates(date.get_current_date(), 101)

    rslt = {}
    dates = []
    codes = []
    names = []
    returns = []
    max_returns = []
    first_returns = []
    positions = []
    codes_nums = []

    for d in trade_days:
        dates.append(d)
    logger.info(f"开始回测日期：{dates} 总数量：{len(dates)-1}.")

    
    roll_back_dates = [(dates[i], dates[i+1]) for i in range(len(dates)-1)]
    dates.pop(-1)
    if len(roll_back_dates) != len(dates):
        logger.error(f"回测日期生成失败， 回测日期长度为{len(roll_back_dates)}, 应该为{len(dates)-1}")
        raise
    
    rslt['date'] = dates
    rslt['code'] = codes
    rslt['name'] = names
    rslt['return'] = returns
    rslt['max_return'] = max_returns
    rslt['first_return'] = first_returns
    rslt['position'] = positions
    rslt['codes_num'] = codes_nums

    for current_date, next_date in roll_back_dates:
        logger.info(f"开始回测日期：{current_date}...")
        auction_codes, position = get_target_codes(date = current_date)
        if auction_codes == None or len(auction_codes) == 0:
            logger.info(f"未获取到日期{current_date}的目标股票... 等待继续执行")
            codes.append('')
            names.append('low')
            returns.append(0.0)
            max_returns.append(0.0)
            first_returns.append(0.0)
            positions.append(position)
            codes_nums.append(0)
        else:
            codes.append(','.join(auction_codes))
            names.append('low')
            positions.append(position)
            codes_nums.append(len(auction_codes))
            cnum = len(auction_codes)
            is_first = True
            max_return = -1
            avg_return = 0
            i = 0
            for code in auction_codes:
                if code not in code_map:
                    logger.error(f"股票{code}不在全市场股票字典中...")
                    raise
                rcode = code_map[code]
                result = compute_return(rcode, current_date, next_date)
                avg_return = avg_return + result
                i = i + 1
               
                max_return = max(max_return, result)
                if is_first:
                    first_returns.append(result)
                    is_first = False
            returns.append(result)
            max_returns.append(max_return)

        time.sleep(5)

    df = pd.DataFrame(rslt)
    df.to_csv('roll_back.csv', index=False)
    logger.info(f"回测完毕， 结果已保存到roll_back.csv")