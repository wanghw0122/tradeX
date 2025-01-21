import multiprocessing
import os
from re import A
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

import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time

# 设置环境变量
import threading
import queue
from multiprocessing import Queue
global q
q = Queue(10)

global task_queue

global error_time, cancel_time
error_time = 0
cancel_time = 0

path = r'D:\qmt\userdata_mini'  # QMT客户端路径
acc_id = '8886660057'
# 创建QMTTrader实例
qmt_trader = QMTTrader(path, acc_id)

def get_target_codes(retry_times=3):
    if retry_times <= 0:
        return None
    auction_codes = []
    try:
        items = sm.run_strategys()
        for _, arr in items.items():
            for item in arr:
                if item == None:
                    continue
                auction_codes.append(item.split('.')[0])
    except Exception as e:
        logger.error(f"An error occurred in get_target_codes: {e}")
        auction_codes = get_target_codes(retry_times-1)
    return auction_codes


def strategy_schedule_job():
    try:    
        is_trade, _ = date.is_trading_day()
        if not is_trade:
            logger.info("[producer] 非交易日，不执行策略.")
            end_task("code_schedule_job")
            return
        if not date.is_between_925_and_930():
            logger.info("[producer] 非交易时间，不执行策略.")
            return
        auction_codes = get_target_codes()
        if auction_codes == None or len(auction_codes) == 0:
            logger.info("[producer] 未获取到目标股票，等待重新执行策略...")
            return
        length = len(auction_codes)
        logger.info(f"[producer] 获取到目标股票: {auction_codes}")
        pct = 0.4
        each_money_pct = pct / length
        for code in auction_codes:
            q.put((code, each_money_pct))
        end_task("code_schedule_job")
    except Exception as e:
        error_time = error_time + 1
        if error_time > 120:
            end_task("code_schedule_job")
        logger.error(f"[producer] 执行任务出现错误 {error_time}次: {e}")

def consumer_to_buy(q):
    _, cash, _, _, _ = qmt_trader.get_account_info()
    if cash == None:
        logger.error("get_account_info error!")
        raise
    logger.info(f"[consumer] get account info total can used cash: {cash}")
    while True:
        try:
            data = q.get()
            logger.info(f"[consumer] Consumed: {data}")
            if (type(data) == tuple):
                c_cash = cash * data[1]
                qmt_trader.buy_quickly(data[0], c_cash, sync=True)
            elif type(data) == str and data == 'end':
                break
            else:
                raise
        except Exception as e:
            logger.error(f"[consumer] 执行任务出现错误: {e}")

def is_before_930_30():
    now = datetime.datetime.now()
    target_time = now.replace(hour=9, minute=30, second=30, microsecond=0)
    return now < target_time

def is_after_932():
    now = datetime.datetime.now()
    target_time = now.replace(hour=9, minute=32, second=0, microsecond=0)
    return now > target_time

def cancel_orders():
    if is_before_930_30():
        logger.info("未到取消时间，不取消订单")
        return
    cancel_result = qmt_trader.cancel_active_orders()
    logger.info(f"取消所有未成交的订单 {cancel_result}")
    cacel_time = cancel_time + 1
    if cacel_time > 5:
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



if __name__ == "__main__":

    consumer_thread = multiprocessing.Process(target=consumer_to_buy, args=(q,))
    consumer_thread.start()

    scheduler = BackgroundScheduler()
    # 每隔5秒执行一次 job_func 方法
    scheduler.add_job(strategy_schedule_job, 'interval', seconds=5, id="code_schedule_job")

    scheduler.add_job(cancel_orders, 'interval', seconds=3, id="code_cancel_job")

    # 在 2025-01-21 22:08:01 ~ 2025-01-21 22:09:00 之间, 每隔5秒执行一次 job_func 方法
    # scheduler.add_job(strategy_schedule_job, 'interval', seconds=5, start_date='2025-01-21 22:12:01', end_date='2025-01-21 22:13:00', args=['World!'])

    # 启动调度器
    scheduler.start()

    # 保持程序运行，以便调度器可以执行任务
    try:
        while True:
            if is_after_932():
                print("达到最大执行时间，退出程序")
                scheduler.shutdown()
                break
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        # 关闭调度器
        scheduler.shutdown()


    q.join()
    consumer_thread.join()
    

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