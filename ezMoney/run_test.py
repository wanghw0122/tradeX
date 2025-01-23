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
    position = 0.3
    try:
        items = sm.run_strategys(date.get_current_date())
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
        auction_codes = get_target_codes(retry_times-1)
    return auction_codes, position


def get_position(xiaocao_envs):
    if xiaocao_envs == None:
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
   codes, position = get_target_codes()
   print(codes, position)