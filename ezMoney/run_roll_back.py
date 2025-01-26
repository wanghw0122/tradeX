import multiprocessing
import os
from re import A, X, sub
from typing import ItemsView

from py import log
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

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
import traceback
# 设置环境变量
import threading
import queue
from multiprocessing import Queue

import pandas_market_calendars as mcal
import pandas as pd
import datetime
from common.constants import *

import yaml


def get_target_codes(strategy_names, date=date.get_current_date(), sub_task = None, params = {}, retry_times=3, call_back = None):
    if not strategy_names or len(strategy_names) == 0:
        return None, 0.3
    if retry_times <= 0:
        return None, 0.3
    auction_codes = []
    position = 0.3
    try:
        items = sm.run_strategys(strategy_names, current_date=date, sub_task = sub_task, params = params)
        if call_back:
            call_back(items)
        if items == None:
            return None, 0.3
        if len(items) == 0:
            return None, 0.3
        if 'xiao_cao_env' in items:
            xiaocao_envs = items['xiao_cao_env'][0]
            position = get_position(xiaocao_envs)
        for strategy_name in strategy_names:
            if strategy_name not in items:
                logger.error(f"策略{strategy_name}未在回测结果中找到...")
                continue
            arr = items[strategy_name]
            if type(arr)!= list:
                continue
            for item in arr:
                if item == None:
                    continue
                auction_codes.append(item.split('.')[0])
    except Exception as e:
        logger.error(f"An error occurred in get_target_codes: {e}", exc_info=True)
        traceback.print_exc()
        return get_target_codes(strategy_names, date, sub_task, params, retry_times-1, call_back=call_back)
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

def run(strategy_name, date, next_date, rslt, code_map, sub_task = None, params = {}):
    def call_back(items):
        if 'code' not in params:
            return
        code = params['code']
        if 'xiao_mods_info' not in items or not items['xiao_mods_info']:
            logger.error (f"策略{code}在{date}的回测结果中未找到xiao_mods_info...")
            raise
        block_dict, _ = items['xiao_mods_info']
        if block_dict and len(block_dict) > 0:
            block = block_dict[code]
            if not block:
                if 'trendScore' not in rslt:
                    rslt['trendScore'] = [0.0]
                else:
                    rslt['trendScore'].append(0.0)
                if 'shortLineScore' not in rslt:
                    rslt['shortLineScore'] = [0.0]
                else:
                    rslt['shortLineScore'].append(0.0)
                if 'shortLineScoreChange' not in rslt:
                    rslt['shortLineScoreChange'] = [0.0]
                else:
                    rslt['shortLineScoreChange'].append(0.0)
                return
            trendScore = block.trendScore
            shortLineScore = block.shortLineScore
            shortLineScoreChange = block.shortLineScoreChange
            if 'trendScore' not in rslt:
                rslt['trendScore'] = [trendScore]
            else:
                rslt['trendScore'].append(trendScore)
            if 'shortLineScore' not in rslt:
                rslt['shortLineScore'] = [shortLineScore]
            else:
                rslt['shortLineScore'].append(shortLineScore)
            if 'shortLineScoreChange' not in rslt:
                rslt['shortLineScoreChange'] = [shortLineScoreChange]
            else:
                rslt['shortLineScoreChange'].append(shortLineScoreChange)
            logger.info(f"策略{code}在{date}的回测结果中找到block_dict, trendScore={trendScore}, shortLineScore={shortLineScore}, shortLineScoreChange={shortLineScoreChange}")
        else:
            logger.error(f"策略{code}在{date}的回测结果中未找到block_dict...")
            raise
    auction_codes, position = get_target_codes(strategy_names= [strategy_name], date = date, sub_task = sub_task, params = params, call_back=call_back)
    if not auction_codes or len(auction_codes) == 0:
        logger.info(f"未获取到日期{current_date}的目标股票... 等待继续执行")
        rslt['date'].append(current_date)
        rslt['code'].append('')
        rslt['strategy_name'].append(strategy_name)
        if sub_task:
            rslt['sub_strategy_name'].append(sub_task)
        else:
            rslt['sub_strategy_name'].append('')
        rslt['return'].append(0.0)
        rslt['max_return'].append(0.0)
        rslt['first_return'].append(0.0)
        rslt['top2_return'].append(0.0)
        rslt['top3_return'].append(0.0)
        rslt['position'].append(position)
        rslt['codes_num'].append(0)
    else:
        rslt['date'].append(current_date)
        rslt['code'].append(','.join(auction_codes))
        rslt['strategy_name'].append(strategy_name)
        if sub_task:
            rslt['sub_strategy_name'].append(sub_task)
        else:
            rslt['sub_strategy_name'].append('')
        rslt['position'].append(position)
        rslt['codes_num'].append(len(auction_codes))
        cnum = len(auction_codes)
        is_first = True
        max_return = -1
        avg_return = 0
        top2_return = 0
        top2_cnt = 0
        top3_cnt = 0
        top3_return = 0
        index = 0
        for code in auction_codes:
            if code not in code_map:
                logger.error(f"股票{code}不在全市场股票字典中...")
                continue
            rcode = code_map[code]
            result = compute_return(rcode, current_date, next_date)
            if index < 2:
                top2_return = top2_return + result
                top2_cnt = top2_cnt + 1
            if index < 3:
                top3_return = top3_return + result
                top3_cnt = top3_cnt + 1
            avg_return = avg_return + result
        
            max_return = max(max_return, result)
            if is_first:
                rslt['first_return'].append(result)
                is_first = False
            index = index + 1
        if top2_cnt == 0:
            rslt['top2_return'].append(0.0)
        else:
            rslt['top2_return'].append(top2_return/top2_cnt)
        if top3_cnt == 0:
            rslt['top3_return'].append(0.0)
        else:
            rslt['top3_return'].append(top3_return/top3_cnt)
        rslt['return'].append(avg_return/cnum)
        rslt['max_return'].append(max_return)

def save_rslt(rslt, save_path, save_mod, nums = 300):
    if 'w' == save_mod:
        return
    if len(rslt['date']) < nums:
        return
    logger.info(f"开始追加保存回测结果到{save_path}... 保存模式为{save_mod} 数量为{len(rslt['date'])}")
    df = pd.DataFrame(rslt)
    df.to_csv(save_path, index=False, mode=save_mod, header=not os.path.exists(save_path))
    logger.info(f"结果已保存")
    for k, _ in rslt.items():
        rslt[k].clear()

if __name__ == "__main__":

    file_name = r'D:\workspace\TradeX\ezMoney\roll_back.yml'

    with open(file_name, 'r',  encoding='utf-8') as file:
        config = yaml.safe_load(file)
        if config is None or 'configs' not in config:
            logger.error("Config No data Error.")

    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    configs = config['configs']

    if configs is None or len(configs) == 0:
        logger.error("Config No data Error.")

    for config in configs:
        config['save_path'] = config['save_path'].format(strategy_name=config['strategy_name'], current_date=current_date)
    
    logger.info(f"回测配置：{configs}")
    logger.info(f"计划回测策略: {[cfg['strategy_name'] for cfg in configs]}, 共{len(configs)}个")
    logger.info(f"开始回测...")

    i = 1
    for cfg in configs:
        start = cfg['start']
        end = cfg['end']
        max_num = cfg['max_num']
        save_path = cfg['save_path']
        strategy_name = cfg['strategy_name']
        save_mod = cfg['save_mod']
        saved = cfg['saved']
        valid = cfg['valid']
        sub_tasks = cfg['sub_tasks']

        if not strategy_name or len(strategy_name) == 0:
            logger.error(f"策略名称为空...")
            raise

        if not valid:
            logger.info(f"策略{strategy_name}已失效， 跳过...")
            continue
        
        logger.info(f"开始回测策略-{i}：{strategy_name}")
        
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        code_map = {}
        for stock in all_stocks:
            if stock.startswith('60') or stock.startswith('00'):
                code = stock.split('.')[0]
                code_map[code] = stock
        logger.info(f"构建全市场股票字典完毕。 共{len(code_map)}个")

        trade_days = date.get_trade_dates(start_date=start, end_date=end, trade_days=max_num)

        rslt = {}
        dates = []
        codes = []
        strategy_names = []
        sub_strategy_names = []
        returns = []
        max_returns = []
        first_returns = []
        top2_returns = []
        top3_returns = []
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

        dates.clear()
        rslt['date'] = dates
        rslt['code'] = codes
        rslt['strategy_name'] = strategy_names
        rslt['sub_strategy_name'] = sub_strategy_names
        rslt['return'] = returns
        rslt['max_return'] = max_returns
        rslt['first_return'] = first_returns
        rslt['top2_return'] = top2_returns
        rslt['top3_return'] = top3_returns
        rslt['position'] = positions
        rslt['codes_num'] = codes_nums

        for current_date, next_date in roll_back_dates:
            logger.info(f"开始回测日期：{current_date}...")
            task_count = 1
            if sub_tasks and len(sub_tasks) > 0:
                for sub_task in sub_tasks:
                    sub_task_name = sub_task['name']
                    sub_task_params = sub_task['params']
                    if not sub_task_name or len(sub_task_name) == 0:
                        logger.error(f"子任务名称为空...")
                        continue
                    code = sub_task_params['code']
                    if not code or len(code) == 0:
                        logger.error(f"子任务参数code为空...")
                        continue
                    if mods_name_to_code_dict[sub_task_name] != code:
                        logger.error(f"子任务 {sub_task_name} 参数code错误， 应该为{mods_name_to_code_dict[sub_task_name]}， 实际为{code}")
                        raise
                    logger.info(f"开始回测 {strategy_name} 的子任务{task_count}：{sub_task_name}...")
                    task_count = task_count + 1
                    run(strategy_name, current_date, next_date, rslt, code_map, sub_task = sub_task_name, params = sub_task_params)
                    if saved:
                        save_rslt(rslt, save_path, save_mod)
            else:
                run(strategy_name, current_date, next_date, rslt, code_map)

            # time.sleep(1)
        i = i + 1
        df = pd.DataFrame(rslt)
        if saved:
            df.to_csv(save_path, index=False, mode=save_mod, header=not os.path.exists(save_path))
            logger.info(f"回测完毕， 结果已保存到{save_path}")
        else:
            logger.info(f"回测完毕， 结果未保存")
