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
from sqlite_processor.mysqlite import *

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
        if items == None:
            return None, 0.3
        if len(items) == 0:
            return None, 0.3
        if call_back:
            call_back(items)
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
                if type(item) == str:
                    auction_codes.append(item.split('.')[0])
                else:
                    auction_codes.append(item.code.split('.')[0])
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
        return 0.0
    x_data = df.loc[n_date: n_next_date]['open'].astype(float)
    start_price = x_data[n_date]
    end_price = x_data[n_next_date]
    result = (end_price - start_price) / start_price
    logger.info(f"股票{auction_code}在{date}的收益为{result}， 开始价格为{start_price}, 结束价格为{end_price}")
    return result

def get_stock_open_close_price(auction_code, date, next_date):
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
        return -1, -1, -1, -1
    x_data = df.loc[n_date: n_next_date]['open'].astype(float)
    x_data_close = df.loc[n_date: n_next_date]['close'].astype(float)
    start_price = x_data[n_date]
    end_price = x_data[n_next_date]
    close_price = x_data_close[n_date]
    n_close_price = x_data_close[n_next_date]
    return start_price, close_price, end_price, n_close_price

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


def run_once(strategy_name, date, next_date, rslt, code_map, sub_task = None, params = {}):
    def call_back(items, r = rslt):
        import json
        if strategy_name not in items:
            return
        category_dict = {}
        block_dict = {}
        mods_dict = {}
        env_info = {}
        if 'xiaocao_category_info' in items:
            xiaocao_category_infos = items['xiaocao_category_info']
            if xiaocao_category_infos:
                block_list = [] 
                index = 1
                for info in xiaocao_category_infos:
                    if info == None:
                        continue
                    categoryCode= info.categoryCode
                    if not categoryCode:
                        continue
                    categoryName = info.name
                    num = info.num if info.num != None else -1000
                    prePctChangeRate = info.prePctChangeRate
                    numChange = info.numChange
                    stockType = info.stockType
                    blockRankList = info.blockRankList
                    category_dict[categoryCode] = {}
                    category_dict[categoryCode]['categoryCode'] = categoryCode
                    category_dict[categoryCode]['categoryName'] = categoryName
                    category_dict[categoryCode]['num'] = num
                    category_dict[categoryCode]['prePctChangeRate'] = prePctChangeRate
                    category_dict[categoryCode]['numChange'] = numChange
                    category_dict[categoryCode]['blocks'] = []
                    if stockType and stockType == 'industry':
                        category_dict[categoryCode]['industry'] = 1
                        block_list.append((categoryCode, num, prePctChangeRate, numChange))
                        category_dict[categoryCode]['blocks'].append(categoryCode)
                    else:
                        category_dict[categoryCode]['industry'] = 0
                    category_dict[categoryCode]['rank'] = index
                    
                    if blockRankList and len(blockRankList) > 0:
                        for block in blockRankList:
                            if block == None:
                                continue
                            blockCode = block['blockCode']
                            if not blockCode:
                                continue
                            category_dict[categoryCode]['blocks'].append(blockCode)
                            num = block['num']
                            prePctChangeRate = block['prePctChangeRate']
                            numChange = block['numChange']
                            block_list.append((blockCode, num, prePctChangeRate, numChange))
                    index = index + 1
                block_list.sort(key=lambda x: x[1], reverse=True)
                index = 1
                for block in block_list:
                    blockCode = block[0]
                    num = block[1]
                    prePctChangeRate = block[2]
                    numChange = block[3]
                    block_dict[blockCode] = {}
                    block_dict[blockCode]['blockCode'] = blockCode
                    block_dict[blockCode]['num'] = num
                    block_dict[blockCode]['prePctChangeRate'] = prePctChangeRate
                    block_dict[blockCode]['numChange'] = numChange
                    block_dict[blockCode]['rank'] = index
                    index = index + 1
                for _, info in category_dict.items():
                    if 'blocks' not in info:
                        continue
                    blocks = info['blocks']
                    if not blocks:
                        continue
                    block_code_dict = {}
                    for block in blocks:
                        block_code_dict[block] = {}
                        block_code_dict[block].update(block_dict[block])
                    info['block_dict'] = block_code_dict
        if 'xiao_mods_info' in items and 'code' in params:
            code = params['code']
            mod_dict, mod_name_dict = items['xiao_mods_info']
            mods = []
            for code, info in mod_dict.items():
                if code not in mod_name_dict:
                    continue
                mod_name = mod_name_dict[code]
                mods.append(info)
                mods_dict[code] = {}
                mods_dict[code]['mod_name'] = mod_name
                mods_dict[code]['mod_code'] = code
                mods_dict[code]['mod_short_line_score'] = info.shortLineScore
                mods_dict[code]['mod_short_line_score_change'] = info.shortLineScoreChange
                mods_dict[code]['mod_trend_score'] = info.trendScore
                mods_dict[code]['mod_trend_score_change'] = info.trendScoreChange
            mods.sort(key=lambda x: x.shortLineScore, reverse=True)
            index = 1
            for mod in mods: 
                code = mod.code
                if code not in mods_dict:
                    continue
                mods_dict[code]['mod_short_line_rank'] = index
                index = index + 1
            mods.sort(key=lambda x: x.trendScore, reverse=True)
            index = 1
            for mod in mods:
                code = mod.code
                if code not in mods_dict:
                    continue
                mods_dict[code]['mod_trend_rank'] = index
                index = index + 1
        if 'xiao_cao_env' in items:
            xiaocao_envs = items['xiao_cao_env'][0]
            if xiaocao_envs:
                for code, info in xiaocao_envs.items():
                    env_info[code] = {}
                    env_info[code]['realShortLineScore'] = info.realShortLineScore
                    env_info[code]['realTrendScore'] = info.realTrendScore
                    env_info[code]['preRealShortLineScore'] = info.preRealShortLineScore
                    env_info[code]['preRealTrendScore'] = info.preRealTrendScore
                    env_info[code]['shortLineScore'] = info.shortLineScore
                    env_info[code]['trendScore'] = info.trendScore
                    env_info[code]['preShortLineScore'] = info.preShortLineScore
                    env_info[code]['preTrendScore'] = info.preTrendScore
                    env_info[code]['shortLineScoreChange'] = info.shortLineScoreChange
                    env_info[code]['trendScoreChange'] = info.trendScoreChange
                    env_info[code]['realShortLineScoreChange'] = info.realShortLineScoreChange
                    env_info[code]['realTrendScoreChange'] = info.realTrendScoreChange
        arr = items[strategy_name]
        if type(arr)!= list:
            return
        if not arr:
            return
        ranker = 1
        for item in arr:
            if item == None:
                continue
            stock_code = item.code
            if not stock_code:
                continue
            stock_name = item.codeName
            blockCategoryCodeList = item.blockCategoryCodeList
            blockCodeList = item.blockCodeList
            industryBlockCodeList = item.industryBlockCodeList
            is_bottom = item.isBottom
            is_broken_plate = item.isBrokenPlate
            is_down_broken = item.isDownBroken
            is_fall = item.isFall
            is_first_down_broken = item.isFirstDownBroken
            is_first_up_broken = item.isFirstUpBroken
            is_gestation_line = item.isGestationLine
            is_half = item.isHalf
            is_high = item.isHigh
            is_highest = item.isHighest
            is_long_shadow = item.isLongShadow
            is_low = item.isLow
            is_medium = item.isMedium
            is_meso = item.isMeso
            is_plummet = item.isPlummet
            is_pre_st = item.isPreSt
            is_small_high_open = item.isSmallHighOpen
            is_up_broken = item.isUpBroken
            is_weak = item.isWeak
            first_limit_up_days = item.firstLimitUpDays
            jsjl = item.jsjl
            cjs = item.cjs
            xcjw = item.xcjw
            jssb = item.jssb
            open_pct_rate = item.openPctChangeRate

            xcjw_v2 = item.xcjwV2
            jssb_v2 = item.jssbV2
            cjs_v2 = item.cjsV2
            is_strength_high = item.isStrengthHigh
            is_strength_middle = item.isStrengthMiddle
            is_strength_low = item.isStrengthLow
            is_strength_increase = item.isStrengthIncrease
            is_strength_reduct = item.isStrengthReduct
            short_line_score = item.shortLineScore
            short_line_score_change = item.shortLineScoreChange
            jsjl_block = item.jsjlBlock
            jssb_block = item.jssbBlock
            cjs_block = item.cjsBlock
            direction_cjs_v2 = item.directionCjsV2
            circulation_market_value = item.circulationMarketValue
            cgyk = item.cgyk
            htyk = item.htyk
            cgyk_value = item.cgykValue
            htyk_value = item.htykValue
            is_middle_high_open = item.isMiddleHighOpen
            is_large_high_open = item.isLargeHighOpen
            is_small_low_open = item.isSmallLowOpen
            is_middle_low_open = item.isMiddleLowOpen
            is_large_low_open = item.isLargeLowOpen
            strong_limit_up_days = item.strongLimitUpDays
            trend_group = item.trendGroup
            trend_back = item.trendBack
            trend_start = item.trendStart
            trend_group_10 = item.trendGroup10
            limitup_gene = item.limitupGene
            main_start = item.mainStart
            main_frequent = item.mainFrequent

            d = {}
            d['date_key'] = date
            d['stock_rank'] = ranker
            d['strategy_name'] = strategy_name
            if sub_task:
                d['sub_strategy_name'] = sub_task
            else:
                d['sub_strategy_name'] = ''
            d['stock_code'] = stock_code
            d['stock_name'] = stock_name
            if blockCategoryCodeList and len(blockCategoryCodeList) > 0:
                d['block_category'] = ','.join(blockCategoryCodeList)
                min_rank = 100
                for category in blockCategoryCodeList:
                    if category not in category_dict:
                        continue
                    info = category_dict[category]
                    assert info['categoryCode'] == category
                    info_rank = info['rank']
                    min_rank = min(min_rank, info_rank)
                d['max_block_category_rank'] = min_rank
            if blockCodeList and len(blockCodeList) > 0:
                d['block_codes'] = ','.join(blockCodeList)
                min_rank = 100
                for block in blockCodeList:
                    if block not in block_dict:
                        continue
                    info = block_dict[block]
                    assert info['blockCode'] == block
                    info_rank = info['rank']
                    min_rank = min(min_rank, info_rank)
                d['max_block_code_rank'] = min_rank
            if industryBlockCodeList and len(industryBlockCodeList) > 0:
                d['industry_code'] = ','.join(industryBlockCodeList)
                min_rank = 100
                for code in industryBlockCodeList:
                    if code in category_dict:
                        info = category_dict[code]
                        assert info['categoryCode'] == code
                        info_rank = info['rank']
                        min_rank = min(min_rank, info_rank)
                    if code in block_dict:
                        info = block_dict[code]
                        assert info['blockCode'] == code
                        info_rank = info['rank']
                        min_rank = min(min_rank, info_rank)
                d['max_industry_code_rank'] = min_rank
            if category_dict:
                d['block_category_info'] = json.dumps(category_dict, ensure_ascii=False)
            
            if is_bottom:
                d['is_bottom'] = 1
            if is_broken_plate:
                d['is_broken_plate'] = 1
            if is_down_broken:
                d['is_down_broken'] = 1
            if is_fall:
                d['is_fall'] = 1
            if is_first_down_broken:
                d['is_first_down_broken'] = 1
            if is_first_up_broken:
                d['is_first_up_broken'] = 1
            if is_gestation_line:
                d['is_gestation_line'] = 1
            if is_half:
                d['is_half'] = 1
            if is_high:
                d['is_high'] = 1
            if is_highest:
                d['is_highest'] = 1
            if is_long_shadow:
                d['is_long_shadow'] = 1
            if is_low:
                d['is_low'] = 1
            if is_medium:
                d['is_medium'] = 1
            if is_meso:
                d['is_meso'] = 1
            if is_plummet:
                d['is_plummet'] = 1
            if is_pre_st:
                d['is_pre_st'] = 1
            if is_small_high_open:
                d['is_small_high_open'] = 1
            if is_up_broken:
                d['is_up_broken'] = 1
            if is_weak:
                d['is_weak'] = 1
            if first_limit_up_days != None:
                d['first_limit_up_days'] = first_limit_up_days
            if jsjl != None:
                d['jsjl'] = jsjl
            if cjs!= None:
                d['cjs'] = cjs
            if xcjw!= None:
                d['xcjw'] = xcjw
            if jssb!= None:
                d['jssb'] = jssb
            if open_pct_rate != None:
                d['open_pct_rate'] = open_pct_rate

            # float 和 str 类型处理
            if xcjw_v2 != None:
                d['xcjw_v2'] = xcjw_v2
            if jssb_v2 != None:
                d['jssb_v2'] = jssb_v2
            if cjs_v2 != None:
                d['cjs_v2'] = cjs_v2
            if short_line_score != None:
                d['short_line_score'] = short_line_score
            if short_line_score_change != None:
                d['short_line_score_change'] = short_line_score_change
            if jsjl_block != None:
                d['jsjl_block'] = jsjl_block
            if jssb_block != None:
                d['jssb_block'] = jssb_block
            if cjs_block != None:
                d['cjs_block'] = cjs_block
            if direction_cjs_v2 != None:
                d['direction_cjs_v2'] = direction_cjs_v2
            if circulation_market_value != None:
                d['circulation_market_value'] = circulation_market_value
            if cgyk != None:
                d['cgyk'] = cgyk
            if htyk != None:
                d['htyk'] = htyk
            if cgyk_value != None:
                d['cgyk_value'] = cgyk_value
            if htyk_value != None:
                d['htyk_value'] = htyk_value
            if strong_limit_up_days != None:
                d['strong_limit_up_days'] = strong_limit_up_days
            
            # bool 类型处理
            if is_strength_high:
                d['is_strength_high'] = 1
            if is_strength_middle:
                d['is_strength_middle'] = 1
            if is_strength_low:
                d['is_strength_low'] = 1
            if is_strength_increase:
                d['is_strength_increase'] = 1
            if is_strength_reduct:
                d['is_strength_reduct'] = 1
            if is_middle_high_open:
                d['is_middle_high_open'] = 1
            if is_large_high_open:
                d['is_large_high_open'] = 1
            if is_small_low_open:
                d['is_small_low_open'] = 1
            if is_middle_low_open:
                d['is_middle_low_open'] = 1
            if is_large_low_open:
                d['is_large_low_open'] = 1
            if trend_group:
                d['trend_group'] = 1
            if trend_back:
                d['trend_back'] = 1
            if trend_start:
                d['trend_start'] = 1
            if trend_group_10:
                d['trend_group_10'] = 1
            if limitup_gene:
                d['limitup_gene'] = 1
            if main_start:
                d['main_start'] = 1
            if main_frequent:
                d['main_frequent'] = 1


            if 'code' in params:
                code = params['code']
                if code in mods_dict:
                    d['mod_code'] = mods_dict[code]['mod_code']
                    d['mod_name'] = mods_dict[code]['mod_name']
                    d['mod_short_line_score'] = mods_dict[code]['mod_short_line_score']
                    d['mod_short_line_score_change'] = mods_dict[code]['mod_short_line_score_change']
                    d['mod_short_line_rank'] = mods_dict[code]['mod_short_line_rank']
                    d['mod_trend_score'] = mods_dict[code]['mod_trend_score']
                    d['mod_trend_score_change'] = mods_dict[code]['mod_trend_score_change']
                    d['mod_trend_rank'] = mods_dict[code]['mod_trend_rank']

            if env_info:
                d['env_json_info'] = json.dumps(env_info, ensure_ascii=False)
            if next_date:
                if '.' in stock_code:
                    real_code = stock_code.split('.')[0]
                else:
                    real_code = stock_code
                if real_code in code_map:
                    real_code = code_map[real_code]
                else:
                    logger.error(f"股票代码{real_code}不在全市场股票字典中...")
                    continue
                open,close,next_open,next_close = get_stock_open_close_price(real_code, date, next_date)
                d['open_price'] = open
                d['close_price'] = close
                d['next_day_open_price'] = next_open
                d['next_day_close_price'] = next_close
            logger.info(f"run strategy-{strategy_name} sub_task-{sub_task} date-{date} result: {d}")
            r.append(d)
            ranker = ranker + 1
    get_target_codes(strategy_names= [strategy_name], date = date, sub_task = sub_task, params = params, call_back=call_back)


def run(strategy_name, date, next_date, rslt, code_map, sub_task = None, params = {}):
    if not next_date:
        return
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
        logger.info(f"未获取到日期{date}的目标股票... 等待继续执行")
        rslt['date'].append(date)
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
        rslt['date'].append(date)
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
            result = compute_return(rcode, date, next_date)
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

def save_rslt_to_db(datekey, rslt,  strategy_name, pre = False, sub_task = None):
    if not rslt:
        return
    logger.info(f"开始保存{strategy_name} - {sub_task}回测结果到数据库... 数量为{len(rslt)} 日期为{datekey}")
    n_datekey = datekey
    if '-' in n_datekey:
        n_datekey = n_datekey.replace('-', '')
    n_datekey = n_datekey[:6]
    if sub_task:
        strategy = strategy_name + '-' + sub_task
    else:
        strategy = strategy_name
    if pre:
        prefix = 'strategy_data_premarket_'
    else:
        prefix = 'strategy_data_aftermarket_'
    with SQLiteManager(db_name) as manager: 
        create_strategy_table(prefix = prefix, specified_date = n_datekey)
        manager.batch_insert_data_by_date(datekey, rslt, prefix=prefix, strategy=strategy)

def run_roll_back(once_daily = False, pre = False):
    file_name = r'D:\workspace\TradeX\ezMoney\roll_back.yml'
    with open(file_name, 'r',  encoding='utf-8') as file:
        config = yaml.safe_load(file)
        if config is None or 'configs' not in config:
            logger.error("Config No data Error.")

    current_date = datetime.now().strftime('%Y-%m-%d')
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
        save_type = cfg['save_type']

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
            # if stock.startswith('60') or stock.startswith('00'):
            code = stock.split('.')[0]
            code_map[code] = stock
        logger.info(f"构建全市场股票字典完毕。 共{len(code_map)}个")


        if once_daily:
            today = date.get_current_date()
            # today = "2025-10-31"
            is_trade, pre_date = date.is_trading_day(today)
            if is_trade:
                if pre:
                    trade_days = [today]
                else:
                    trade_days = [pre_date, today]
            else:
                logger.info("today is not trading day. daily task end.")
                return
        else:
            trade_days = date.get_trade_dates(start_date=start, end_date=end, trade_days=max_num)

        if not trade_days:
            logger.error(f"trade_days error {trade_days}")
            continue

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

        roll_back_dates.append((dates[-1], ""))
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
        db_list = []
        for current_date, next_date in roll_back_dates:
            logger.info(f"开始回测日期：{current_date}... next-{next_date}")
            task_count = 1
            if sub_tasks and len(sub_tasks) > 0:
                for sub_task in sub_tasks:
                    sub_task_name = sub_task['name']
                    sub_task_params = sub_task['params']
                    if not sub_task_name or len(sub_task_name) == 0:
                        logger.error(f"子任务名称为空...")
                        continue
                    # if sub_task_name != '绿盘低吸前3':
                    #     continue
                    code = sub_task_params['code']
                    if not code or len(code) == 0:
                        logger.error(f"子任务参数code为空...")
                        continue
                    if mods_name_to_code_dict[sub_task_name] != code:
                        logger.error(f"子任务 {sub_task_name} 参数code错误， 应该为{mods_name_to_code_dict[sub_task_name]}， 实际为{code}")
                        raise
                    logger.info(f"开始回测 {strategy_name} 的子任务{task_count}：{sub_task_name}...")
                    task_count = task_count + 1
                    if save_type == 'csv':
                        run(strategy_name, current_date, next_date, rslt, code_map, sub_task = sub_task_name, params = sub_task_params)
                    elif save_type == 'db':
                        run_once(strategy_name, current_date, next_date, db_list, code_map, sub_task = sub_task_name, params = sub_task_params)
                        
                    if saved and save_type == 'csv':
                        save_rslt(rslt, save_path, save_mod)
                    elif saved and save_type == 'db':
                        save_rslt_to_db(current_date, db_list, strategy_name, pre = pre, sub_task = sub_task_name)
                        db_list.clear()
            else:
                if 'params' in cfg:
                    params = cfg['params']
                    if save_type == 'csv':
                        run(strategy_name, current_date, next_date, rslt, code_map, params=params)
                    elif save_type == 'db':
                        run_once(strategy_name, current_date, next_date, db_list, code_map, params=params)
                else:
                    if save_type == 'csv':
                        run(strategy_name, current_date, next_date, rslt, code_map)
                    elif save_type == 'db':
                        run_once(strategy_name, current_date, next_date, db_list, code_map)
                if saved and save_type == 'db':
                    save_rslt_to_db(current_date, db_list, strategy_name, pre = pre)
                    db_list.clear()
            # time.sleep(1)
        i = i + 1
        df = pd.DataFrame(rslt)
        if save_type == 'csv':
            if saved:
                df.to_csv(save_path, index=False, mode=save_mod, header=not os.path.exists(save_path))
                logger.info(f"回测完毕， 结果已保存到{save_path}")
            else:
                logger.info(f"回测完毕， 结果未保存")
        else:
            logger.info(f"回测完毕.")
if __name__ == "__main__":
    run_roll_back()
    
