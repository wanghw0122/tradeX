from functools import total_ordering
import multiprocessing
import os
from typing import ItemsView

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
from strategy.strategy import sm
from logger import catch, logger, order_logger, strategy_logger, order_success_logger
from trade.qmtTrade import *
from xtquant import xtdata
from xtquant import xtconstant
from date_utils import date

from apscheduler.schedulers.background import BackgroundScheduler
import time
from run_roll_back import *

import datetime
# 设置环境变量
from multiprocessing import Queue
global q
global qq
q = Queue(10)
qq = Queue(10)
global tick_q

tick_q = Queue(10)

end_subscribe = True
start_subscribe = True

global task_queue
global error_time, cancel_time
error_time = 0
cancel_time = 0

global back_cash
back_cash = 200000

global cached_auction_infos
cached_auction_infos = []

global default_position
default_position = 0.33

#################### 测试配置 ########################

do_test = False
buy = True
subscribe = True

#################### 测试配置 ########################
global final_results
final_results = {}

path = r'D:\qmt\userdata_mini'  # QMT客户端路径
acc_id = '8886660057'
# 创建QMTTrader实例
logger.info("开始初始化QMT....")

qmt_trader = QMTTrader(path, acc_id)
qmt_trader.callback.set_qmt(qmt_trader)

# strategies = {
#     "低吸": {
#         "低位孕线低吸": {
#             "code": "9G0086",
#             "returnNum": 1
#         },
#         "低位N字低吸": {
#             "code": "9G0080",
#             "returnNum": 1
#         }
#     },
#     "接力":{
#         "首板打板": {
#             "code": "9G0038",
#             "returnNum": 1
#         },
#         "中高位连板打板": {
#             "code": "9G0009",
#             "returnNum": 1
#         }
#     },
#     "xiao_cao_dwdx_a": {},
#     "xiao_cao_dwndx": {},
#     "xiao_cao_dwyxdx": {}
# }


#####strategy configs #####################################

budgets = {
    "ydx": {
        "name" : "ydx",
        "value": 0.666,
        "codes": [],
        "total_position": default_position
    },
    "ndx": {
        "name" : "ndx",
        "value": 0.167,
        "codes": [],
        "total_position": default_position
    }
}

strategies = {
    "低吸": {
        "sub_strategies": {
            "低位孕线低吸": {
                "code": "9G0086",   
                "returnNum": 1,
                "budget": "ydx"
            },
            "低位N字低吸": {
                "code": "9G0080",
                "returnNum": 1,
                "budget": "ndx"
            }
        }
    },
    "xiao_cao_dwndx": {
        "sub_strategies": {},
        "budget": "ndx"
    },
    "xiao_cao_dwyxdx": {
        "sub_strategies": {},
        "budget": "ydx"
    }
}

##########################strategy configs ################


def set_strategy_codes_to_budgets(strategy_name, codes, strategies_dict = strategies, budgets_dict = budgets):
    if not strategy_name or len(strategy_name) == 0:
        return
    if not codes or len(codes) == 0:
        return
    if not strategies_dict or len(strategies_dict) == 0:
        return
    if not budgets_dict or len(budgets_dict) == 0:
        return
    if '-' in strategy_name:
        strategy = strategy_name.split('-')[0]
        sub_task_name = strategy_name.split('-')[1]
        if strategy not in strategies_dict:
            return
        if 'sub_strategies' not in strategies_dict[strategy]:
            return
        sub_stategies_dict = strategies_dict[strategy]['sub_strategies']
        if not sub_stategies_dict or len(sub_stategies_dict) == 0:
            logger.error(f"sub_stategies_dict not found in strategies_dict")
            return
        
        sub_task = sub_stategies_dict[sub_task_name]
        if not sub_task or len(sub_task) == 0:
            return
        if 'budget' not in sub_task:
            return
        budget_name = sub_task['budget']
        if budget_name not in budgets_dict:
            return
        budget = budgets_dict[budget_name]
        if not budget or len(budget) == 0:
            return
        for code in codes:
            if code in budget['codes']:
                continue
            budget['codes'].append(code)
    else:
        if strategy_name not in strategies_dict:
            return
        budget_name = strategies_dict[strategy_name]['budget']
        if budget_name not in budgets_dict:
            logger.error(f"budget {budget_name} not found in budgets_dict")
            return
        for code in codes:
            if code in budgets_dict[budget_name]['codes']:
                continue
            budgets_dict[budget_name]['codes'].append(code)

def set_position_to_budgets(position = default_position, budgets_dict = budgets):
    for _, budget in budgets_dict.items():
        if not budget or len(budget) == 0:
            continue
        budget['total_position'] = position

def get_position_from_budgets(budgets_dict = budgets):
    rslt = {}
    for _, budget in budgets_dict.items():
        if not budget or len(budget) == 0:
            continue
        codes = budget['codes']
        value = budget['value']
        if not codes or len(codes) == 0:
            continue
        position = budget['total_position'] / len(codes)
        for code in codes:
            rslt[code] = position * value
    return rslt

def get_target_return_keys_dict(starategies_dict = strategies):
    target_return_keys_dict = {}
    for strategy_name, strategy_dict in starategies_dict.items():
        if 'sub_strategies' not in strategy_dict:
            target_return_keys_dict[strategy_name] = strategy_name
        else:
            sub_task_dict = strategy_dict['sub_strategies']
            for sub_task_name, _ in sub_task_dict.items():
                target_return_keys_dict[strategy_name + '-' + sub_task_name] = strategy_name
    return target_return_keys_dict

def get_target_codes_by_all_strategies(retry_times=3):
    rslt_dct = {}
    if retry_times <= 0:
        return None, 0
    try:
        items = sm.run_all_strategys(strategies_dict=strategies)
        rkeys = get_target_return_keys_dict(strategies)
        if rkeys == None or len(rkeys) == 0:
            return None, 0
        if items == None:
            return None, 0
        if len(items) == 0:
            return None, 0
        for key, name in rkeys.items():
            if key not in items:
                continue
            item = items[key]
            if item == None:
                continue
            position = default_position
            auction_codes = []
            if 'xiao_cao_env' in item:
                xiaocao_envs = item['xiao_cao_env'][0]
                position = get_position(xiaocao_envs)
            if name in item:
                real_item_list = item[name]
                if real_item_list == None:
                    continue
                for code in real_item_list:
                    if not code or len(code) == 0:
                        continue
                    auction_codes.append(code.split('.')[0])
            if len(auction_codes):
                rslt_dct[key] = auction_codes
            else:
                rslt_dct[key] = []
        return rslt_dct, position
    except Exception as e:
        logger.error(f"An error occurred in get_target_codes: {e}", exc_info=True)
        return get_target_codes_by_all_strategies(retry_times-1)


def get_position(xiaocao_envs):
    if xiaocao_envs == None or len(xiaocao_envs) == 0:
        return default_position
    env_10cm_qs = xiaocao_envs['9A0001']
    env_10cm_cd = xiaocao_envs['9B0001']
    env_10cm_qp = xiaocao_envs['9C0001']
    positions = (0.25, 0.45, 0.3)
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
                cur_lift = cur_lift + (0.0047 * realShortLineScore)
            if realTrendScore and realTrendScore > 0:
                cur_lift = cur_lift + (0.0026 * realTrendScore)
            if liftShortScore and liftShortScore > 0:
                cur_lift = cur_lift + 0.0012 * liftShortScore
            if liftTrendScore and liftTrendScore > 0:
                cur_lift = cur_lift + 0.0007 * liftTrendScore
            lifts.append(cur_lift)
    except Exception as e:
        logger.error(f"An error occurred in get_position: {e}")
    if len(lifts) != 3:
        return default_position
    lift = lifts[0] * positions[0]  + lifts[1] * positions[1] + lifts[2] * positions[2]
    return max(min(default_position + lift, 1.0), default_position)


def merge_result(rslt, position):
    if type(rslt) is not dict:
        logger.error(f"merge result type error{type(rslt)}")
        return {}
    if len(rslt) == 0:
        return {}
    for key, codes in rslt.items():
        logger.info(f"策略{key}, 成功得到结果 {codes}.")
        code_len = len(codes)
        if code_len <= 0:
            continue
        set_strategy_codes_to_budgets(key, codes)
    set_position_to_budgets(position)
    
    return get_position_from_budgets()



def strategy_schedule_job():
    try:    
        if do_test and len(cached_auction_infos) > 3:
            end_task("code_schedule_job")
            return
        is_trade, _ = date.is_trading_day()
        if not is_trade and not do_test:
            logger.info("[producer] 非交易日，不执行策略.")
            end_task("code_schedule_job")
            return
        if not date.is_between_925_and_930() and not do_test:
            logger.info("[producer] 非交易时间，不执行策略.")
            return
        if date.is_after_929() and not do_test:
            logger.info("[producer] 已过交易时间，结束执行策略.")
            end_task("code_schedule_job")
            return
        rslt, position = get_target_codes_by_all_strategies() 
        if not rslt or len(rslt) == 0:
            logger.info("[producer] 未获取到目标股票，等待重新执行策略...")
            cached_auction_infos.append({})
            return
        m_rslt = merge_result(rslt, position)
        logger.info(f"[producer] 获取到目标股票 {m_rslt}.")
        cached_auction_infos.append(m_rslt)
        if len(cached_auction_infos) > 1:
            pre_rslt = cached_auction_infos[-1]
            pree_rslt = cached_auction_infos[-2]
            if pre_rslt == pree_rslt and m_rslt == pre_rslt:
                if m_rslt.keys() == final_results.keys():
                    return
                logger.info(f"[producer] 连续2次获取到相同的目标股票，且有增量购买... {m_rslt} - {final_results}")
                order_logger.info(f"[producer] 连续2次获取到相同的目标股票，且有增量购买... {m_rslt} - {final_results}")
                l = len(final_results)
                min_position = 0.0
                total_position = 0.0
                if l > 0:
                    for _, v in final_results.items():
                        total_position = total_position + v
                    min_position = total_position / l
                for code, position in m_rslt.items():
                    if code in final_results:
                        continue
                    position = max(min_position, position)
                    q.put((code, position))
                    qq.put((code, position))
                    final_results[code] = position
                    order_logger.info(f"发单准备买入股票 code - {code} , position - {position}.")
    except Exception as e:
        error_time = error_time + 1
        if error_time > 20:
            end_task("code_schedule_job")
        logger.error(f"[producer] 执行任务出现错误 {error_time}次: {e}")


def consumer_to_buy(q, orders_dict, orders):
    if not buy:
        return
    while True:
        try:
            data = q.get()
            logger.info(f"[consumer] Consumed: {data}")
            _, cash, _, _, total_assert = qmt_trader.get_account_info()
            if cash == None or cash <= 0:
                logger.error(f"get_account_info error! no cache {cash}")
                continue
            logger.info(f"[consumer] get account info total can used cash: {cash}")
            total_assert = total_assert - back_cash
            if (type(data) == tuple):
                c_cash = min(total_assert * data[1], cash)
                order_id = qmt_trader.buy_quickly(data[0], c_cash, order_remark='fixed', sync=True, orders_dict=orders_dict, orders=orders, buffer=0.003)
                if order_id < 0:
                     order_id = qmt_trader.buy_quickly(data[0], c_cash,  order_remark='fixed', sync=True, orders_dict=orders_dict, orders=orders, buffer=0.003)
                     if order_id < 0:
                        order_id = qmt_trader.buy_quickly(data[0], c_cash, order_remark='fixed', sync=True, orders_dict=orders_dict, orders=orders, buffer=0.003)
            elif type(data) == str and data == 'end':
                break
            else:
                raise
        except Exception as e:
            logger.error(f"[consumer] 执行任务出现错误: {e}")

def get_cancel_budgets(orders_dict, budgets_dict):
    cancel_order_infos_dict = qmt_trader.get_all_cancel_order_infos()
    for order_id, order_info in cancel_order_infos_dict.items():
        if order_id in orders_dict:
            stock_code = order_info['stock_code']
            order_volume = order_info['order_volume']
            traded_volume = order_info['traded_volume']
            price = order_info['price']
            left_volume = order_volume - traded_volume
            left_budget = left_volume * price
            if stock_code in budgets_dict:
                budgets_dict[stock_code] = (budgets_dict[stock_code][0] + left_volume, budgets_dict[stock_code][1] + left_budget)
            else:
                budgets_dict[stock_code] = (left_volume, left_budget)
    return budgets_dict


def consumer_to_rebuy(orders_dict, tick_queue = tick_q):

    if not orders_dict or len(orders_dict) == 0:
        logger.error(f"[consumer_to_rebuy] 无订单 {orders_dict}")
        return
    else:
        logger.info(f"[consumer_to_rebuy] 有订单 {orders_dict}")
    
    stock_statistics = {}
    # 股票对应的订单，不会动态更新
    stock_to_orders = {}
    # 股票对应未完成订单，会动态更新
    uncomplete_orders = {}
    budgets_dict = {}
    budgets_dict = get_cancel_budgets(orders_dict, budgets_dict)

    for order_id , order_info in orders_dict.items():
        stock_code = order_info[0]
        price = order_info[1]
        volume = order_info[2]
        order_type = order_info[3]
        order_remark = order_info[4]
        time_stamp = order_info[5]
        buffered = order_info[6]

        if stock_code in uncomplete_orders:
            uncomplete_orders[stock_code].append(order_id)
        else:
            uncomplete_orders[stock_code] = [order_id]
        
        if stock_code in stock_to_orders:
            stock_to_orders[stock_code].append(order_id)
        else:
            stock_to_orders[stock_code] = [order_id]
    
    # 需要监听的股票，会动态更新
    need_listen_stocks = list(stock_to_orders.keys())
    if not need_listen_stocks or len(need_listen_stocks) == 0:
        order_logger.error(f"[consumer_to_rebuy] 无需要监听的股票")
        return
    else:
        order_logger.info(f"[consumer_to_rebuy] 开始监听股票 {need_listen_stocks}")
    while True:
        try:
            if not need_listen_stocks or len(need_listen_stocks) == 0:
                order_logger.error(f"[consumer_to_rebuy] 无需要监听的股票 结束任务")
                break
            data = tick_queue.get()
            order_logger.info(f"[consumer] Consumed: {data}")
            # update 撤单dict
            budgets_dict = get_cancel_budgets(orders_dict, budgets_dict)

            if (type(data) == dict):
                tick_time = data['time']
                diff = data['diff']

                lastPrice = data['lastPrice']
                open = data['open']
                high = data['high']
                low = data['low']
                lastClose = data['lastClose']
                totalVolume = data['totalVolume']
                totalAmount = data['totalAmount']
                askPrice = data['askPrice']
                bidPrice = data['bidPrice']
                askVol = data['askVol']
                bidVol = data['bidVol']
                avgPrice = data['avgPrice']
                volume = data['volume']
                amount = data['amount']
                stock_code = data['stock']
                
                if stock_code not in stock_statistics:
                    stock_statistics[stock_code] = {}
                    stock_statistics[stock_code]['open'] = open
                    stock_statistics[stock_code]['high'] = high
                    stock_statistics[stock_code]['low'] = low
                    stock_statistics[stock_code]['lastClose'] = lastClose
                    stock_statistics[stock_code]['avgPrice'] = [avgPrice]
                    stock_statistics[stock_code]['lastPrice'] = [lastPrice]
                    stock_statistics[stock_code]['volume'] = [volume]
                    stock_statistics[stock_code]['amount'] = [amount]
                    stock_statistics[stock_code]['price_diff_pct'] = [lastPrice / open - 1]
                    stock_statistics[stock_code]['price_diff'] = [lastPrice - open]
                    stock_statistics[stock_code]['volume_diff'] = [0]
                else:
                    stock_statistics[stock_code]['open'] = open
                    stock_statistics[stock_code]['high'] = high
                    stock_statistics[stock_code]['low'] = low
                    stock_statistics[stock_code]['lastClose'] = lastClose
                    stock_statistics[stock_code]['avgPrice'].append(avgPrice)
                    stock_statistics[stock_code]['lastPrice'].append(lastPrice)
                    stock_statistics[stock_code]['volume'].append(volume)
                    stock_statistics[stock_code]['amount'].append(amount)

                    stock_statistics[stock_code]['price_diff_pct'].append(lastPrice / stock_statistics[stock_code]['lastPrice'][-2] - 1)
                    stock_statistics[stock_code]['price_diff'].append(lastPrice - stock_statistics[stock_code]['lastPrice'][-2])
                    stock_statistics[stock_code]['volume_diff'].append(volume - stock_statistics[stock_code]['volume'][-2])

                cur_uncomplete_orders =  uncomplete_orders[stock_code] if stock_code in uncomplete_orders else []
                if stock_code in budgets_dict:
                    buy_vol, buy_amount = budgets_dict[stock_code]
                else:
                    buy_vol, buy_amount = 0, 0

                if not cur_uncomplete_orders and buy_vol <= 0:
                    order_logger.info(f"[consumer_to_rebuy] 无未完成订单，且无买入需求，跳过 {stock_code}.")
                    if stock_code in need_listen_stocks:
                        need_listen_stocks.remove(stock_code)
                    continue
                
                price_diff_pcts = stock_statistics[stock_code]['price_diff_pct']
                avgPrices = stock_statistics[stock_code]['avgPrice']
                lastPrices = stock_statistics[stock_code]['lastPrice']

                if stock_code not in stock_to_orders or not stock_to_orders[stock_code]:
                    continue

                is_over_fall = False
                is_fall = False
                is_over_up = False
                is_up = False
                is_cross_avg_up = False
                is_cross_avg_down = False
                is_v = False
                is_a = False
                fall_steps = 0
                up_steps = 0
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] < 1.1 * price_diff_pcts[-2] and price_diff_pcts[-2] < -0.0012:
                    is_over_fall = True
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] < 0 and price_diff_pcts[-2] < 0:
                    is_fall = True
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] > 1.1 * price_diff_pcts[-2] and price_diff_pcts[-2] > 0.0012:
                    is_over_up = True
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] > 0 and  price_diff_pcts[-2] > 0:
                    is_up = True
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] > 0 and  price_diff_pcts[-2] < 0:
                    is_v = False
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] < 0 and  price_diff_pcts[-2] > 0:
                    is_a = True
                if len(lastPrices) > 1 and lastPrices[-1] > avgPrices[-1] and lastPrices[-2] < avgPrices[-2]:
                    is_cross_avg_up = True
                if len(lastPrices) > 1 and lastPrices[-1] < avgPrices[-1] and lastPrices[-2] > avgPrices[-2]:
                    is_cross_avg_down = True

                for pct in price_diff_pcts[::-1]:
                    if pct < 0:
                        fall_steps = fall_steps + 1
                    else:
                        break
                
                for pct in price_diff_pcts[::-1]:
                    if pct > 0:
                        up_steps = up_steps + 1
                    else:
                        break

                orders_status = qmt_trader.get_all_orders(filter_order_ids=list(orders_dict.keys()))
                stock_order_statuses = {}
                
                for order_id in stock_to_orders[stock_code]:
                    if order_id not in orders_status:
                        logger.error(f"[consumer_to_rebuy] 订单不存在: {order_id}")
                        continue
                    stock_order_statuses[order_id] = orders_status[order_id]
                
                for order_id, order_status_info in stock_order_statuses.items():
                    order_status_p = order_status_info['order_status']
                    if order_status_p == xtconstant.ORDER_SUCCEEDED or order_status_p == xtconstant.ORDER_PART_CANCEL or order_status_p == xtconstant.ORDER_CANCELED or order_status_p ==  xtconstant.ORDER_JUNK:
                        if order_id not in uncomplete_orders[stock_code]:
                            continue
                        uncomplete_orders[stock_code].remove(order_id)
                
                cur_uncomplete_orders = uncomplete_orders[stock_code]
                if not cur_uncomplete_orders and buy_vol <= 0:
                    order_logger.info(f"[consumer_to_rebuy] 无未完成订单，且无买入需求，跳过 {stock_code}.")
                    continue
                current_time = datetime.datetime.now().timestamp()
                time_difference =  current_time - (tick_time / 1000)
                if time_difference > 1.5 or diff > 1.5:
                    order_logger.error(f"[consumer_to_rebuy] 股票代码超时: {stock_code} curdiff - {time_difference} diff - {diff}")
                    continue
                
                price_diff = lastPrice / open - 1
                if -0.004 < price_diff and price_diff < 0.003:
                    
                    if stock_code in budgets_dict:
                        buy_vol, buy_amount = budgets_dict[stock_code]
                    if buy_vol > 0:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格波动，有买入量: {stock_code} price_diff - {price_diff} buy_vol - {buy_vol} buy_amount - {buy_amount}")
                        if is_over_fall or (is_cross_avg_down and fall_steps > 1) or fall_steps > 2:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格平稳 {price_diff}，有撤单，下跌跳过 {is_over_fall}, {is_cross_avg_down}, {fall_steps}.")
                            continue
                        c_order_id = -1
                        if is_over_up or (is_cross_avg_up and up_steps > 1) or up_steps > 2:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格平稳 {price_diff}，有撤单，上涨追买5 {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            if 'SH' in stock_code:
                                c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_SH_CONVERT_5_CANCEL, order_remark='rebuy_5', sync=True)
                            else:
                                c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_SZ_CONVERT_5_CANCEL, order_remark='rebuy_5', sync=True)
                        else:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格平稳 {price_diff}，有撤单，追买1 {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_PEER_PRICE_FIRST, order_remark='rebuy_1', sync=True)
                        if c_order_id > 0 and stock_code in budgets_dict:
                            buy_vol = 0
                            budgets_dict.pop(stock_code)
                    else:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格波动，无买入量: {stock_code} price_diff - {price_diff}")
                    continue
                elif -0.007 < price_diff and price_diff <= -0.004:
                    for order_id in cur_uncomplete_orders:
                        order_info = orders_dict[order_id]
                        buffered_t = order_info[6]
                        if buffered_t and not is_up and not is_over_up and not is_cross_avg_up and up_steps < 2:
                            status_q = stock_order_statuses[order_id]['order_status'] if order_id in stock_order_statuses else None
                            if status_q and (status_q == xtconstant.ORDER_PART_SUCC or status_q == xtconstant.ORDER_REPORTED or status_q == xtconstant.ORDER_WAIT_REPORTING):
                                order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格略低 {price_diff}，有高买可撤高买 orderid-{order_id} {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                                cancel_result = qmt_trader.cancel_order(order_id, sync=False)
                                if cancel_result > 0:
                                    time.sleep(0.05)
                    if is_over_fall or (is_cross_avg_down and fall_steps > 1) or fall_steps > 2:
                        order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格略低 {price_diff}，下跌跳过 {is_over_fall}, {is_cross_avg_down}, {fall_steps}.")
                        continue
                    c_order_id = -1
                    budgets_dict = get_cancel_budgets(orders_dict, budgets_dict)
                    if stock_code in budgets_dict:
                        buy_vol, buy_amount = budgets_dict[stock_code]
                    
                    if buy_vol > 0:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格略低，有买入量: {stock_code} price_diff - {price_diff} buy_vol - {buy_vol} buy_amount - {buy_amount}")
                        c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_PEER_PRICE_FIRST, order_remark='rebuy_1', sync=True)
                        if c_order_id > 0 and stock_code in budgets_dict:
                            budgets_dict.pop(stock_code)
                            buy_vol = 0
                    else:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格略低，无买入量: {stock_code} price_diff - {price_diff}")
                elif -0.007 >= price_diff and -0.01 < price_diff:
                    for order_id in cur_uncomplete_orders:
                        if not is_over_up and up_steps < 3 and not (is_cross_avg_up and up_steps > 1):
                            status_q = stock_order_statuses[order_id]['order_status'] if order_id in stock_order_statuses else None
                            if status_q and (status_q == xtconstant.ORDER_PART_SUCC or status_q == xtconstant.ORDER_REPORTED or status_q == xtconstant.ORDER_WAIT_REPORTING):
                                order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格稍低 {price_diff}，有高买可撤高买 orderid-{order_id} {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                                cancel_result = qmt_trader.cancel_order(order_id, sync=False)
                                if cancel_result > 0:
                                    time.sleep(0.05)
                    if is_over_fall or (is_cross_avg_down and fall_steps > 1) or fall_steps > 1:
                        order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格稍低 {price_diff}，有撤单，下跌跳过 {is_over_fall}, {is_cross_avg_down}, {fall_steps}.")
                        continue
                    budgets_dict = get_cancel_budgets(orders_dict, budgets_dict)
                    if stock_code in budgets_dict:
                        buy_vol,buy_amount = budgets_dict[stock_code]
                    c_order_id = -1
                    if buy_vol > 0:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格稍低，有买入量: {stock_code} price_diff - {price_diff} buy_vol - {buy_vol} buy_amount - {buy_amount}")
                        c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_PEER_PRICE_FIRST, order_remark='rebuy_1', sync=True)
                        if c_order_id > 0 and stock_code in budgets_dict:
                            budgets_dict.pop(stock_code)
                            buy_vol = 0
                    else:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格稍低，无买入量: {stock_code} price_diff - {price_diff}")
                elif price_diff <= -0.01:
                    for order_id in cur_uncomplete_orders:
                        status_q = stock_order_statuses[order_id]['order_status'] if order_id in stock_order_statuses else None
                        if status_q and (status_q == xtconstant.ORDER_PART_SUCC or status_q == xtconstant.ORDER_REPORTED or status_q == xtconstant.ORDER_WAIT_REPORTING):
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格很低 {price_diff}，有高买可撤高买 orderid-{order_id} {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            cancel_result = qmt_trader.cancel_order(order_id, sync=False)
                            if cancel_result > 0:
                                time.sleep(0.05)
                    if (is_over_fall and fall_steps > 3) or (is_cross_avg_down and fall_steps > 2) :
                        order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格很低 {price_diff}，有撤单，下跌跳过 {is_over_fall}, {is_cross_avg_down}, {fall_steps}.")
                        continue
                    budgets_dict = get_cancel_budgets(orders_dict, budgets_dict)
                    if stock_code in budgets_dict:
                        buy_vol,buy_amount = budgets_dict[stock_code]
                    c_order_id = -1
                    if buy_vol > 0:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格很低，有买入量: {stock_code} price_diff - {price_diff} buy_vol - {buy_vol} buy_amount - {buy_amount}")
                        c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_PEER_PRICE_FIRST, order_remark='rebuy_1', sync=True)
                        if c_order_id > 0 and stock_code in budgets_dict:
                            budgets_dict.pop(stock_code)
                            buy_vol = 0
                    else:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格很低，无买入量: {stock_code} price_diff - {price_diff}")
                elif price_diff >= 0.003 and price_diff < 0.006:
                    for order_id in cur_uncomplete_orders:
                        order_info = orders_dict[order_id]
                        buffered_t = order_info[6]
                        if not buffered_t and not (is_over_fall or (is_cross_avg_down and fall_steps > 1) or fall_steps > 2):
                            status_q = stock_order_statuses[order_id]['order_status'] if order_id in stock_order_statuses else None
                            if status_q and (status_q == xtconstant.ORDER_PART_SUCC or status_q == xtconstant.ORDER_REPORTED or status_q == xtconstant.ORDER_WAIT_REPORTING):
                                order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格略高 {price_diff}，有低买可撤低买 orderid-{order_id} {is_over_fall}, {is_cross_avg_down}, {fall_steps}.")
                                cancel_result = qmt_trader.cancel_order(order_id, sync=False)
                                if cancel_result > 0:
                                    time.sleep(0.05)
                    budgets_dict = get_cancel_budgets(orders_dict, budgets_dict)
                    if stock_code in budgets_dict:
                        buy_vol,buy_amount = budgets_dict[stock_code]
                    c_order_id = -1
                    if buy_vol > 0:
                        if is_over_up or (is_cross_avg_up and up_steps > 1) or up_steps > 2:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格略高 {price_diff}，有撤单，上涨追买5 {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            if 'SH' in stock_code:
                                c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_SH_CONVERT_5_CANCEL, order_remark='rebuy_5', sync=True)
                            else:
                                c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_SZ_CONVERT_5_CANCEL, order_remark='rebuy_5', sync=True)
                        else:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格略高 {price_diff}，有撤单，追买1 {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_PEER_PRICE_FIRST, order_remark='rebuy_1', sync=True)
                        if c_order_id > 0 and stock_code in budgets_dict:
                            budgets_dict.pop(stock_code)
                            buy_vol = 0
                    else:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格略高，无买入量: {stock_code} price_diff - {price_diff}")
                elif price_diff >= 0.006 and price_diff < 0.03:
                    for order_id in cur_uncomplete_orders:
                        status_q = stock_order_statuses[order_id]['order_status'] if order_id in stock_order_statuses else None
                        if status_q and (status_q == xtconstant.ORDER_PART_SUCC or status_q == xtconstant.ORDER_REPORTED or status_q == xtconstant.ORDER_WAIT_REPORTING):
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格高 {price_diff}，有低买可撤低买 orderid-{order_id} {is_over_fall}, {is_cross_avg_down}, {fall_steps}.")
                            cancel_result = qmt_trader.cancel_order(order_id, sync=False)
                            if cancel_result > 0:
                                time.sleep(0.05)
                    if (is_over_fall and fall_steps > 3) or (is_cross_avg_down and fall_steps > 2):
                        order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格高 {price_diff}，下跌跳过 {is_over_fall}, {is_cross_avg_down}, {fall_steps}.")
                        continue
                    c_order_id = -1
                    budgets_dict = get_cancel_budgets(orders_dict, budgets_dict)
                    if stock_code in budgets_dict:
                        buy_vol,buy_amount = budgets_dict[stock_code]
                    if buy_vol > 0:
                        if is_over_up or (is_cross_avg_up and up_steps > 1) or up_steps > 2:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格高 {price_diff}，有撤单，上涨追买5 {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            if 'SH' in stock_code:
                                c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_SH_CONVERT_5_CANCEL, order_remark='rebuy_5', sync=True)
                            else:
                                c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_SZ_CONVERT_5_CANCEL, order_remark='rebuy_5', sync=True)
                        else:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格高 {price_diff}，有撤单，追买1 {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            c_order_id = qmt_trader.buy(stock_code, 0, buy_vol, order_type=xtconstant.MARKET_PEER_PRICE_FIRST, order_remark='rebuy_1', sync=True)
                        if c_order_id > 0 and stock_code in budgets_dict:
                            budgets_dict.pop(stock_code)
                            buy_vol = 0
                    else:
                        order_logger.info(f"[consumer_to_rebuy] 股票价格高，无买入量: {stock_code} price_diff - {price_diff}")
                elif price_diff >= 0.03:
                    order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格过高 {price_diff}，跳过.")
                    continue
        except Exception as e:
            logger.error(f"[consumer] 执行任务出现错误: {e}")


def consumer_to_subscribe(qq):
    if not subscribe:
        return
    from xtquant import xtdata
    xtdata.connect(port=58611)
    subscribe_ids = []
    while True:
        try:
            data = qq.get()
            logger.info(f"[subscribe] Consumed: {data}")
            if (type(data) == tuple):
                code = data[0]
                code = qmt_trader.all_stocks[code]
                if not code:
                    logger.error(f"[subscribe] 股票代码不存在: {data}")
                    continue
                period = 'tick'
                def calculate_seconds_difference(specified_time):
                    current_time = datetime.datetime.now().timestamp()
                    time_difference =  current_time - (specified_time / 1000)
                    return time_difference
                def on_data(res, stock=code):
                    # logger.info(f"[subscribe] on_data: {data}")
                    diff = calculate_seconds_difference(res[stock][0]['time'])
                    if period != 'tick':
                        close_value = res[stock][0]['close']
                    else:
                        close_value = res[stock][0]['lastPrice']
                    logger.info(f'时间戳：{res[stock][0]["time"]}, 股票代码：{stock}, 当前价格：{close_value}, 延迟：{diff}')
                id = xtdata.subscribe_quote(code,period=period,count=1, callback=on_data) # 设置count = -1来取到当天所有
                if id < 0:
                    logger.error(f"[subscribe] subscribe_quote error: {data}")
                    continue
                else:
                    logger.info(f"[subscribe] subscribe_quote success: {data}")
                subscribe_ids.append(id)
            elif type(data) == str and data == 'end':
                for id in subscribe_ids:
                    xtdata.unsubscribe_quote(id)
                break
            else:
                continue
        except Exception as e:
            logger.error(f"[subscribe] 执行任务出现错误: {e}")



def consumer_to_subscribe_whole(qq, full_tick_info_dict, tick_q):
    if not subscribe:
        return
    from multiprocessing import Manager
    from xtquant import xtdata
    xtdata.connect(port=58611)
    print ("consumer_to_subscribe_whole connect success")
    subscribe_ids = []
    subscribe_codes = []
    scribed = False
    while True:
        try:
            data = qq.get()
            logger.info(f"[subscribe] Consumed: {data}")
            if (type(data) == tuple):
                code = data[0]
                code = qmt_trader.all_stocks[code]
                if not code:
                    logger.error(f"[subscribe] 股票代码不存在: {data}")
                    continue
                if code in subscribe_codes:
                    continue
                subscribe_codes.append(code)
                
            elif type(data) == str:
                if data == 'start':
                    if scribed:
                        continue
                    if len(subscribe_codes) == 0:
                        logger.error(f"[subscribe] 没有股票代码需要订阅，跳出: {subscribe_codes}")
                        continue
                    def calculate_seconds_difference(specified_time):
                        current_time = datetime.datetime.now().timestamp()
                        time_difference =  current_time - (specified_time / 1000)
                        return time_difference
                    def on_data(res, stocks=subscribe_codes, info_dict = full_tick_info_dict, tick_q = tick_q):
                        for stock in stocks:
                            if stock not in res:
                                continue
                            m = {}
                            data = res[stock]
                            time = data['time']
                            diff = calculate_seconds_difference(time)
                            lastPrice = data['lastPrice']
                            open = data['open']
                            high = data['high']
                            low = data['low']
                            lastClose = data['lastClose']
                            volume = data['volume']
                            amount = data['amount']
                            pvolume = data['pvolume']
                            askPrice = data['askPrice']
                            bidPrice = data['bidPrice']
                            askVol = data['askVol']
                            bidVol = data['bidVol']

                            
                            m['time'] = time
                            m['diff'] = diff
                            m['lastPrice'] = lastPrice
                            m['open'] = open
                            m['high'] = high
                            m['low'] = low
                            m['lastClose'] = lastClose
                            m['totalVolume'] = volume
                            m['totalAmount'] = amount
                            m['askPrice'] = askPrice
                            m['bidPrice'] = bidPrice
                            m['askVol'] = askVol
                            m['bidVol'] = bidVol
                            m['avgPrice'] = amount / pvolume

                            if stock in info_dict:
                                bf = info_dict[stock]
                                if bf:
                                    info  = bf[-1]
                                    info_volume = info['totalVolume']
                                    info_amount = info['totalAmount']
                                    if volume >= info_volume:
                                        m['volume'] = volume - info_volume
                                        m['amount'] = amount - info_amount
                                else:
                                    m['volume'] = volume
                                    m['amount'] = amount
                                bf.append(m)
                                info_dict[stock] = bf
                            else:
                                info_dict[stock] = [m]
                            m['stock'] = stock
                            tick_q.put(m)
                            logger.info(f'时间戳：{time}, 股票代码：{stock}, 当前价格：{lastPrice}, 延迟：{diff},  平均价格：{m["avgPrice"]}，总成交额：{amount}, 总成交量：{volume}, open - {open}, high - {high}, low - {low}, lastClose - {lastClose}, volume - {volume}, amount - {amount}, pvolume - {pvolume}, askPrice - {askPrice}, bidPrice - {bidPrice}, askVol - {askVol}, bidVol - {bidVol}')

                    for code in subscribe_codes:
                        full_tick_info_dict[code] = []
                    logger.info(f"初始化 info dict {full_tick_info_dict}")
                    id = xtdata.subscribe_whole_quote(subscribe_codes, callback=on_data) # 设置count = -1来取到当天所有
                    if id < 0:
                        logger.error(f"[subscribe] subscribe_quote error: {subscribe_codes}")
                        continue
                    else:
                        logger.info(f"[subscribe] subscribe_quote success: {subscribe_codes}")
                        scribed = True
                        subscribe_ids.append(id)
                        
                elif data == 'end':
                    if full_tick_info_dict:
                        import json
                        file_path = "tick_" + str(datetime.datetime.now().strftime("%Y-%m-%d")) + ".json"
                        with open(file_path, 'w', encoding='utf-8') as file:
                            json.dump(dict(full_tick_info_dict), file, ensure_ascii=False, indent=4)
                    for id in subscribe_ids:
                        xtdata.unsubscribe_quote(id)
                    break
            else:
                continue
        except KeyboardInterrupt:
            import json
            if not full_tick_info_dict:
                break
            logger.error(f"save info dict {full_tick_info_dict}")
            file_path = "tick_snapshot_" + str(datetime.datetime.now().strftime("%Y-%m-%d")) + ".json"
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(dict(full_tick_info_dict), file, ensure_ascii=False, indent=4)
            break
        except Exception as e:
            logger.error(f"[subscribe] 执行任务出现错误: {e}")
            break


def consumer_to_get_full_tik(qq, full_tick_info_dict):
    if not subscribe:
        return
    from xtquant import xtdata
    xtdata.connect(port=58611)
    subscribe_codes = []
    ticking = False
    while True:
        if ticking:
            start_time = time.time()
            def calculate_seconds_difference(specified_time):
                current_time = datetime.datetime.now().timestamp()
                time_difference =  current_time - (specified_time / 1000)
                return time_difference
            
            full_ticks = xtdata.get_full_tick(subscribe_codes)
            if full_ticks:
                for code, tick in full_ticks.items():
                    m = {}
                    tm = tick['time']
                    lastPrice = tick['lastPrice']
                    amount = tick['amount']
                    volume = tick['volume']
                    pvolume = tick['pvolume']
                    askPrice = tick['askPrice']
                    bidPrice = tick['bidPrice']
                    askVol = tick['askVol']
                    bidVol = tick['bidVol']
                    transactionNum = tick['transactionNum']
                    need_set = True
                    info = None
                    if code in full_tick_info_dict:
                        info_list = full_tick_info_dict[code]
                        if info_list:
                            info = info_list[-1]
                            if info['time'] == tm:
                                need_set = False
                    if need_set:
                        m['time'] = tm
                        dff = calculate_seconds_difference(tm)
                        m['lastPrice'] = lastPrice
                        m['amount'] = amount
                        m['volume'] = volume
                        m['pvolume'] = pvolume
                        if info:
                            m['totalAmount'] = info['totalAmount'] + amount
                            m['totalVolume'] = info['totalVolume'] + pvolume
                        else:
                            m['totalAmount'] = amount
                            m['totalVolume'] = pvolume
                        m['costDiff'] = dff
                        m['avgPrice'] = m['totalAmount'] / m['totalVolume']
                        m['askPrice'] = askPrice
                        m['bidPrice'] = bidPrice
                        m['askVol'] = askVol
                        m['bidVol'] = bidVol
                        m['transactionNum'] = transactionNum
                        if code in full_tick_info_dict:
                            bf = full_tick_info_dict[code]
                            bf.append(m)
                            full_tick_info_dict[code] = bf
                        else:
                            full_tick_info_dict[code] = [m]
                        logger.info(f'时间戳：{tm}, 股票代码：{code}, 当前价格：{lastPrice}, 延迟：{dff},  平均价格：{m["avgPrice"]}, 总成交额：{m["totalAmount"]}, 总成交量：{m["totalVolume"]}, askPrice - {askPrice}, bidPrice - {bidPrice}, askVol - {askVol}, bidVol - {bidVol}, transactionNum - {transactionNum}')
            end_time = time.time()
            execu_time = end_time - start_time
            if execu_time < 0.2:
                time.sleep(0.2 - execu_time)
            continue
        try:
            data = qq.get()
            logger.info(f"[subscribe] Consumed: {data}")
            if (type(data) == tuple):
                code = data[0]
                code = qmt_trader.all_stocks[code]
                if not code:
                    logger.error(f"[subscribe] 股票代码不存在: {data}")
                    continue
                if code in subscribe_codes:
                    continue
                subscribe_codes.append(code)
            elif type(data) == str:
                if data == 'start':
                    if len(subscribe_codes) == 0:
                        logger.error(f"[subscribe] 没有股票代码需要订阅，跳出: {subscribe_codes}")
                        break
                    ticking = True
            else:
                continue
        except Exception as e:
            logger.error(f"[subscribe] 执行任务出现错误: {e}")


def is_before_930_30():
    now = datetime.datetime.now()
    target_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return now < target_time

def is_after_932():
    now = datetime.datetime.now()
    target_time = now.replace(hour=9, minute=32, second=0, microsecond=0)
    return now > target_time

def is_after_940():
    now = datetime.datetime.now()
    target_time = now.replace(hour=9, minute=40, second=0, microsecond=0)
    return now > target_time


def cancel_orders():
    global cancel_time
    is_trade, _ = date.is_trading_day()
    if not is_trade and not do_test:
        logger.info("[cancel_orders] 非交易日，不执行策略.")
        remove_job("code_cancel_job")
        return
    if is_before_930_30() and not do_test:
        logger.info("未到取消时间，不取消订单")
        return
    cancel_result = qmt_trader.cancel_active_orders()
    if cancel_result:
        order_logger.info(f"取消所有未成交的订单: {cancel_result}")
    logger.info(f"取消所有未成交的订单 {cancel_result}")
    cancel_time = cancel_time + 1
    if cancel_time > 20:
        remove_job("code_cancel_job")


def sell_holdings():
    qmt_trader.sell_holdings()

def remove_job(name):
    try:
        scheduler.remove_job(name)
    except:
        pass


def end_task(name):
    logger.info(f"任务 {name} 执行结束")
    remove_job(name)
    q.put('end')
    if start_subscribe:
        qq.put('start')


def print_latest_tick(full_tick_info_dict):
    x = {}
    for code, info_list in full_tick_info_dict.items():
        if info_list:
            x[code] = info_list[-1]
            logger.info(f"最新的tick数据: {x}")
            x = {}


if __name__ == "__main__":

    from xtquant import xtdatacenter as xtdc
    xtdc.set_token("26e6009f4de3bfb2ae4b89763f255300e96d6912")

    print('xtdc.init')
    xtdc.init() # 初始化行情模块，加载合约数据，会需要大约十几秒的时间
    print('done')

    print('xtdc.listen')
    listen_addr = xtdc.listen(port = 58611)
    print(f'done, listen_addr:{listen_addr}')
    full_tick_info_dict = Manager().dict()

    qmt_trader.init_order_context()
    consumer_thread = multiprocessing.Process(target=consumer_to_buy, args=(q, qmt_trader.orders_dict, qmt_trader.orders))
    # subscribe_thread = multiprocessing.Process(target=consumer_to_subscribe, args=(qq,))
    # subscribe_thread = multiprocessing.Process(target=consumer_to_get_full_tik, args=(qq,full_tick_info_dict))

    subscribe_thread = multiprocessing.Process(target=consumer_to_subscribe_whole, args=(qq, full_tick_info_dict, tick_q))
    consumer_thread.start()
    subscribe_thread.start()
    cached_auction_infos.clear()

    scheduler = BackgroundScheduler()
    # 每隔5秒执行一次 job_func 方法
    scheduler.add_job(strategy_schedule_job, 'interval', seconds=5, id="code_schedule_job")

    # scheduler.add_job(cancel_orders, 'interval', seconds=5, id="code_cancel_job")

    scheduler.add_job(consumer_to_rebuy, 'cron', hour=9, minute=30, id="consumer_to_rebuy", args=[qmt_trader.orders_dict, tick_q])

    # 在 2025-01-21 22:08:01 ~ 2025-01-21 22:09:00 之间, 每隔5秒执行一次 job_func 方法
    # scheduler.add_job(strategy_schedule_job, 'interval', seconds=5, start_date='2025-01-21 22:12:01', end_date='2025-01-21 22:13:00', args=['World!'])

    # 启动调度器
    scheduler.start()

    # 保持程序运行，以便调度器可以执行任务
    try:
        while True:
            if is_after_940() and not do_test:
                logger.info("达到最大执行时间，退出程序")
                q.put('end')
                if end_subscribe:
                    qq.put('end')
                scheduler.shutdown()
                break
            time.sleep(3)
            print_latest_tick(full_tick_info_dict)
    except (KeyboardInterrupt, SystemExit):
        # 关闭调度器
        scheduler.shutdown()
    
    print(f"cancel infos: {qmt_trader.get_all_cancel_order_infos()}")
    q.close()
    q.join_thread()
    if end_subscribe:
        qq.close()
        qq.join_thread()
    consumer_thread.join()
    subscribe_thread.join()
    logger.info("Consumer thread joined.")
    logger.info("Subscribe thread joined.")  

    # # 卖出股票
    # order_id = qmt_trader.sell('600000.SH', 11.0, 50)
    # print(f"卖出委托ID: {order_id}")

    # # 撤单
    # cancel_result = qmt_trader.cancel_order(order_id)
    # print(f"撤单结果: {cancel_result}")

    # 获取账户信息
    # account_info = qmt_trader.get_account_info()
    # print(f"账户信息: {account_info}")

    # get_tradable_stocks = qmt_trader.get_tradable_stocks()
    # print(f"股票数据: {get_tradable_stocks}")

    # qmt_trader.set_running()