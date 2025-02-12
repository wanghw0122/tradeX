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

import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
from run_roll_back import *

# 设置环境变量
from multiprocessing import Queue
global q
global qq
q = Queue(10)
qq = Queue(10)
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

do_test = False

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


strategies = {
    "低吸": {
        "低位孕线低吸": {
            "code": "9G0086",
            "returnNum": 1
        },
        "低位N字低吸": {
            "code": "9G0080",
            "returnNum": 1
        }
    },
    "xiao_cao_dwdx_a": {},
    "xiao_cao_dwndx": {},
    "xiao_cao_dwyxdx": {}
}



def get_target_return_keys_dict(starategies_dict = strategies):
    target_return_keys_dict = {}
    for strategy_name, sub_task_dict in starategies_dict.items():
        if not sub_task_dict or len(sub_task_dict) == 0:
            target_return_keys_dict[strategy_name] = strategy_name
        else:
            for sub_task_name, _ in sub_task_dict.items():
                target_return_keys_dict[strategy_name + '-' + sub_task_name] = strategy_name
    return target_return_keys_dict

def get_target_codes_by_all_strategies(retry_times=3):
    rslt_dct = {}
    if retry_times <= 0:
        return None
    try:
        items = sm.run_all_strategys(strategies_dict=strategies)
        rkeys = get_target_return_keys_dict(strategies)
        if rkeys == None or len(rkeys) == 0:
            return None
        if items == None:
            return None
        if len(items) == 0:
            return None
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
                rslt_dct[key] = (auction_codes, position)
            else:
                rslt_dct[key] = ([], 0.0)
    except Exception as e:
        logger.error(f"An error occurred in get_target_codes: {e}", exc_info=True)
        return get_target_codes_by_all_strategies(retry_times-1)
    return rslt_dct


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


def merge_result(rslt):
    if type(rslt) is not dict:
        logger.error(f"merge result type error{type(rslt)}")
        return {}
    if len(rslt) == 0:
        return {}
    code_to_position = {}
    ll = len(rslt)
    for key, value in rslt.items():
        logger.info(f"策略{key}, 成功得到结果 {value}.")
        codes = value[0]
        code_len = len(codes)
        if code_len <= 0:
            continue
        position = value[1]
        for code in codes:
            if code in code_to_position:
                code_to_position[code] = code_to_position[code] + position / code_len / ll
            else:
                code_to_position[code] = position / code_len / ll
    return code_to_position



def strategy_schedule_job():
    try:    
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
        rslt = get_target_codes_by_all_strategies()
        if not rslt or len(rslt) == 0:
            logger.info("[producer] 未获取到目标股票，等待重新执行策略...")
            cached_auction_infos.append({})
            return
        m_rslt = merge_result(rslt)
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
                    min_position = total_position / (l + 1)
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

def consumer_to_subscribe(qq):
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



def consumer_to_subscribe_whole(qq):
    subscribe_ids = []
    subscribe_codes = []
    whole_tick_info_dict= {}
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
                    def on_data(res, stocks=subscribe_codes, info_dict = whole_tick_info_dict):
                        # logger.info(f"[subscribe] on_data: {data}")
                        for stock in stocks:
                            info = info_dict[stock]
                            times = info['times']
                            cost_diff = info['cost_diff']
                            price_list = info['price_list']
                            avg_price_list = info['avg_price_list']
                            total_amount = info['total_amount']
                            total_volume = info['total_volume']

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

                            total_amount = total_amount + amount
                            total_volume = total_volume + pvolume

                            info['total_amount'] = total_amount
                            info['total_volume'] = total_volume
                            times.append(time)
                            cost_diff.append(diff)
                            cur_avg_price = total_amount / total_volume
                            price_list.append(lastPrice)
                            avg_price_list.append(cur_avg_price)
                            logger.info(f'时间戳：{time}, 股票代码：{stock}, 当前价格：{lastPrice}, 延迟：{diff},  平均价格：{cur_avg_price}，总成交额：{total_amount}, 总成交量：{total_volume}, open - {open}, high - {high}, low - {low}, lastClose - {lastClose}, volume - {volume}, amount - {amount}, pvolume - {pvolume}, askPrice - {askPrice}, bidPrice - {bidPrice}, askVol - {askVol}, bidVol - {bidVol}')

                    id = xtdata.subscribe_whole_quote(subscribe_codes, callback=on_data) # 设置count = -1来取到当天所有
                    if id < 0:
                        logger.error(f"[subscribe] subscribe_quote error: {subscribe_codes}")
                        continue
                    else:
                        logger.info(f"[subscribe] subscribe_quote success: {subscribe_codes}")
                        scribed = True
                        subscribe_ids.append(id)
                        for code in subscribe_codes:
                            whole_tick_info_dict[code] = {'total_amount': 0, 'total_volume': 0, 'price_list': [], 'avg_price_list': [], 'cost_diff': [], 'times': []}
                elif data == 'end':
                    if whole_tick_info_dict:
                        import json
                        file_path = "tick_" + str(datetime.datetime.now().strftime("%Y-%m-%d")) + ".json"
                        with open(file_path, 'w', encoding='utf-8') as file:
                            json.dump(whole_tick_info_dict, file, ensure_ascii=False, indent=4)
                    for id in subscribe_ids:
                        xtdata.unsubscribe_quote(id)
                    break
            else:
                continue
        except KeyboardInterrupt:
            if not whole_tick_info_dict:
                break
            file_path = "tick_snapshot_" + str(datetime.datetime.now().strftime("%Y-%m-%d")) + ".json"
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(whole_tick_info_dict, file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"[subscribe] 执行任务出现错误: {e}")



def is_before_930_30():
    now = datetime.datetime.now()
    target_time = now.replace(hour=9, minute=30, second=30, microsecond=0)
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
    if not is_trade:
        logger.info("[cancel_orders] 非交易日，不执行策略.")
        remove_job("code_cancel_job")
        return
    if is_before_930_30():
        logger.info("未到取消时间，不取消订单")
        return
    cancel_result = qmt_trader.cancel_active_orders()
    if cancel_result:
        order_logger.info(f"取消所有未成交的订单: {cancel_result}")
    logger.info(f"取消所有未成交的订单 {cancel_result}")
    cancel_time = cancel_time + 1
    if cancel_time > 5:
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



if __name__ == "__main__":
    qmt_trader.init_order_context()
    consumer_thread = multiprocessing.Process(target=consumer_to_buy, args=(q, qmt_trader.orders_dict, qmt_trader.orders))
    # subscribe_thread = multiprocessing.Process(target=consumer_to_subscribe, args=(qq,))
    subscribe_thread = multiprocessing.Process(target=consumer_to_subscribe_whole, args=(qq,))
    consumer_thread.start()
    subscribe_thread.start()
    cached_auction_infos.clear()

    scheduler = BackgroundScheduler()
    # 每隔5秒执行一次 job_func 方法
    scheduler.add_job(strategy_schedule_job, 'interval', seconds=4, id="code_schedule_job")

    # scheduler.add_job(cancel_orders, 'interval', seconds=4, id="code_cancel_job")

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
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        # 关闭调度器
        scheduler.shutdown()
    
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