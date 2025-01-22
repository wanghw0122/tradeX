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
from data_class.xiao_cao_environment_second_line_v2 import *
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



if __name__ == "__main__":

   items = sm.run_strategys()

   print (items)