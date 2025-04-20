import multiprocessing
import os



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
from common import constants
import pandas as pd

import datetime
# 设置环境变量
from multiprocessing import Queue

import threading
import queue

from sqlite_processor.mysqlite import SQLiteManager

from monitor.monitor import StockMonitor

threading_q = queue.Queue(100)

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
back_cash = 100000

global cached_auction_infos
cached_auction_infos = []

global default_position
default_position = 0.33

#################### 测试配置 ########################

do_test = False
buy = True
subscribe = True
test_date = "2025-04-16"
buy_total_coef = 0.75
sell_at_monning = True

use_threading_buyer = True
budget_from_db = True

monitor_sell = True

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
        "value": 0.22,
        "codes": [],
        "total_position": default_position
    },
    "sddx": {
        "name" : "sddx",
        "value": 0.0,
        "codes": [],
        "total_position": default_position
    },
    "zwdx": {
        "name" : "zwdx",
        "value": 0.0,
        "codes": [],
        "total_position": default_position
    },
    "zwdbdx": {
        "name" : "zwdbdx",
        "value": 0.0,
        "codes": [],
        "total_position": default_position
    },
    "ddx": {
        "name" : "ddx",
        "value": 0.22,
        "codes": [],
        "total_position": default_position
    },
    "db": {
        "name" : "db",
        "value": 0.11,
        "codes": [],
        "total_position": default_position
    },
     "ndx": {
        "name" : "ndx",
        "value": 0.22,
        "codes": [],
        "total_position": default_position
    },
    "zydx": {
        "name" : "zydx",
        "value": 0.22,
        "codes": [],
        "total_position": default_position
    }
}

strategies = {
    "低吸": {
        "sub_strategies": {
            # 长期玩 回撤不高 创建日期 2025-03-19
            "低位孕线低吸": {
                "code": "9G0086",
                "returnNum": 10,
                "budget": "ydx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'mark': '第一高频',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 3,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '高频',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                ]
            },
            # "连断低吸": {
            #     # 15日 交易低频 夏普高 有方向 最近强势 创建日期 2025-03-19
            #     "code": "9G0033",
            #     "returnNum": 2,
            #     "budget": "zwdbdx",
            #     'returnFullInfo': True,
            #     'filter_params': [
            #         {
            #         "filtered": True,
            #         "fx_filtered": True,
            #         "topn": 1,
            #         "top_fx": 2,
            #         "top_cx": 1,
            #         "only_fx": True,
            #         "enbale_industry": False,
            #         "empty_priority": False,
            #         'min_trade_amount': 8000000,
            #         'block_rank_filter': True,
            #         'gap': 0,
            #         'except_is_ppp': True,
            #         'except_is_track': False
            #         }
            #     ]
            # },
            # 交易频率2 15日最强
            # "放宽低吸前3": {
            #     # 15日 亮眼 有方向 最近强势 创建日期 2025-03-19
            #     "code": "9G0099",   
            #     "returnNum": 10,
            #     "budget": "ndx",
            #     'returnFullInfo': True,
            #     'filter_params': [
            #         {
            #         "filtered": True,
            #         "fx_filtered": True,
            #         "topn": 1,
            #         "top_fx": 2,
            #         "top_cx": 15,
            #         "only_fx": True,
            #         "enbale_industry": False,
            #         "empty_priority": False,
            #         "min_trade_amount": 10000000,
            #         'block_rank_filter': True,
            #         'gap': 0,
            #         'except_is_ppp': True,
            #         'except_is_track': True
            #         }
            #     ]
            # },
    
            # "中位断板低吸": {
            #     # 偏中长期，稳定收益 无方向
            #     "code": "9G0042",
            #     "returnNum": 10,
            #     "budget": "zwdbdx",
            #     'returnFullInfo': True,
            #     'filter_params': [
            #         # 中长期 上升趋势强 下降趋势弱， 创建日期 2025-03-19
            #         {
            #         'mark': '高频',
            #         'limit': 2,
            #         'filtered': True,
            #         'fx_filtered': True,
            #         'topn': 1,
            #         'top_fx': 1,
            #         'top_cx': 2,
            #         'only_fx': False,
            #         'enbale_industry': False,
            #         'empty_priority': True,
            #         'min_trade_amount': 9000000,
            #         'block_rank_filter': False,
            #         'gap': 0,
            #         'except_is_ppp': True,
            #         'except_is_track': True
            #         },
            #         # 最近方向表现不错， 夏普高 创建日期 2025-03-20 
            #         {
            #         'mark': '低频',
            #         'limit': 2,
            #         'filtered': True,
            #         'fx_filtered': True,
            #         'topn': 1,
            #         'top_fx': 1,
            #         'top_cx': 50,
            #         'only_fx': True,
            #         'enbale_industry': False,
            #         'empty_priority': True,
            #         'min_trade_amount': 6000000,
            #         'block_rank_filter': True,
            #         'gap': 0,
            #         'except_is_ppp': True,
            #         'except_is_track': True 
            #         }
            #     ]
            # },
            # "中位高强中低开低吸": {
            #     "code": "9G0155",
            #     "returnNum": 3,
            #     "budget": "zwdbdx",
            #     'returnFullInfo': True,
            #     'filter_params': [
            #         {
            #         'filtered': True,
            #         'fx_filtered': True,
            #         'topn': 1,
            #         'top_fx': 2,
            #         'top_cx': 2,
            #         'only_fx': True,
            #         'enbale_industry': False,
            #         'empty_priority': False,
            #         'min_trade_amount': 8000000,
            #         'block_rank_filter': True,
            #         'gap': 0,
            #         'except_is_ppp': True,
            #         'except_is_track': False
            #         }
            #     ]
            # },
            "中位孕线低吸": {
                "code": "9G0085",
                "returnNum": 3,
                "budget": "zwdbdx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 3,
                    'top_cx': 1,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            },
            "高强中低开低吸": {
                # 10日 高频 前2 有方向 最近强势 创建日期 2025-03-19
                "code": "9G0128",
                "returnNum": 10,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'mark': '第一高频',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 50,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },
                    {
                    'mark': '板块前2',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 2,
                    'top_cx': 50,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },
                    {
                    # 曲线完美
                    'mark': '方向前2',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 2,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },
                    {
                    # 曲线完美
                    'mark': '方向前1',
                    'limit': 5,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 1,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '强方向前2',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 2,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '方向板块前2',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 2,
                    'top_cx': 2,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },
                    {
                    'mark': '方向板块前1',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 1,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },
                    {
                    'mark': '方向板块前3',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 3,
                    'top_cx': 3,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    }
                ]
            },
            "高强低吸": {
                "code": "9G0103",
                "returnNum": 5,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 2,
                    'top_cx': 1,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': False,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            },
            "低位高强低吸": {
                "code": "9G0124",
                "returnNum": 10,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'mark': '第一高频',
                    'limit': 5,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    # 最近还行
                    'mark': '高频',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 3,
                    'top_cx': 50,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },
                    {
                    'mark': '中高频',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 2,
                    'top_cx': 50,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '中频',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 50,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '中低频',
                    'limit': 5,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 3,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '中低频2',
                    'limit': 5,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 2,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },
                    {
                    'mark': '中低频3',
                    'limit': 5,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 1,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': False
                    },

                    {
                    'mark': '高频2',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },

                    #  最近表现一般
                    # {
                    # 'mark': '高频3',
                    # 'limit': 5,
                    # 'filtered': True,
                    # 'fx_filtered': True,
                    # 'topn': 1,
                    # 'top_fx': 2,
                    # 'top_cx': 50,
                    # 'only_fx': True,
                    # 'enbale_industry': False,
                    # 'empty_priority': True,
                    # 'min_trade_amount': 6000000,
                    # 'block_rank_filter': True,
                    # 'gap': 0,
                    # 'except_is_ppp': True,
                    # 'except_is_track': True
                    # },
                    {
                    'mark': '中低频4',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 2,
                    'top_cx': 2,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 8000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '中低频5',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 50,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 8000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },

                    {
                    'mark': '高频3',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 2,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '高频4',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 2,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            },
            "低位高强中低开低吸": {
                # 30日 中频 前2 有方向 最近强势 创建日期 2025-03-20
                "code": "9G0164",
                "returnNum": 10,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'mark': '第一高频',
                    'limit': 5,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 2,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '第二高频',
                    'limit': 3,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 1,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 10000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            },
            "低位中强中低开低吸": {
                # 30日 中频 前2 有方向 最近强势 创建日期 2025-03-20
                "code": "9G0167",
                "returnNum": 5,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 2,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 7500000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            },
            "中强中低开低吸": {
                "code": "9G0131",
                "returnNum": 5,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'mark': '第一高频',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 8000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    },
                    {
                    'mark': '板块前二高频',
                    'limit': 2,
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 2,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 8000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            },
            "首红断低吸": {
                "code": "9G0008",
                "returnNum": 3,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 50,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 8000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            },
            "绿盘低吸": {
                "code": "9G0002",
                "returnNum": 5,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 1,
                    'only_fx': True,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 8000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            }

            # "中位低吸": {
            #     # 15日 中频 前2 有方向 胜率 60% 最近强势 创建日期 2025-03-20
            #     "code": "9G0026",
            #     "returnNum": 3,
            #     "budget": "ddx",
            #     'returnFullInfo': True,
            #     'filter_params': [
            #         {
            #         'filtered': True,
            #         'fx_filtered': True,
            #         'topn': 1,
            #         'top_fx': 3,
            #         'top_cx': 1,
            #         'only_fx': True,
            #         'enbale_industry': False,
            #         'empty_priority': True,
            #         'min_trade_amount': 8000000,
            #         'block_rank_filter': True,
            #         'gap': 0,
            #         'except_is_ppp': True,
            #         'except_is_track': False
            #         }
            #     ]
            # }
        }
    }
    # ,
    # "追涨": {
    #     "sub_strategies": {
    #         # 收益不错 有方向 最近强势 ，创建日期 2025-03-19
    #         "小高开追涨": {
    #             "code": "9G0019",
    #             "returnNum": 5,
    #             "budget": "ddx",
    #             'returnFullInfo': True,
    #             'filter_params': [
    #                 {
    #                 'filtered': True,
    #                 'fx_filtered': True,
    #                 'topn': 1,
    #                 'top_fx': 2,
    #                 'top_cx': 50,
    #                 'only_fx': True,
    #                 'enbale_industry': False,
    #                 'empty_priority': False,
    #                 'min_trade_amount': 10000000,
    #                 'block_rank_filter': True,
    #                 'gap': 0,
    #                 'except_is_ppp': True,
    #                 'except_is_track': False
    #                 }
    #             ]
    #         }
    #         # ,
    #         # "低位中强追涨": {
    #         #     "code": "9G0116",
    #         #     "returnNum": 2,
    #         #     "budget": "ddx",
    #         #     'returnFullInfo': True,
    #         #     'filter_params': [
    #         #         {
    #         #         'filtered': True,
    #         #         'fx_filtered': True,
    #         #         'topn': 1,
    #         #         'top_fx': 50,
    #         #         'top_cx': 50,
    #         #         'only_fx': True,
    #         #         'enbale_industry': False,
    #         #         'empty_priority': False,
    #         #         'min_trade_amount': 6000000,
    #         #         'block_rank_filter': True,
    #         #         'gap': 0,
    #         #         'except_is_ppp': True,
    #         #         'except_is_track': False
    #         #         }
    #         #     ]
    #         # }
    #     }
    # }
    ,
    "接力": {
        "sub_strategies": {
            "一进二弱转强": {
                "code": "9G0003",
                "returnNum": 3,
                "budget": "ddx",
                'returnFullInfo': True,
                'filter_params': [
                    {
                    'filtered': True,
                    'fx_filtered': True,
                    'topn': 1,
                    'top_fx': 50,
                    'top_cx': 2,
                    'only_fx': False,
                    'enbale_industry': False,
                    'empty_priority': True,
                    'min_trade_amount': 6000000,
                    'block_rank_filter': True,
                    'gap': 0,
                    'except_is_ppp': True,
                    'except_is_track': True
                    }
                ]
            }
          
        }
    }
}

strategies_to_buffer = {
    "xiao_cao_1j2db": [0.019],
    "xiao_cao_dwyxdx": [0.019],
    "低吸-低位孕线低吸": [0.019],
    "低吸-低位N字低吸": [0.019],
    "低吸-中位孕线低吸": [0.019],
    "低吸-首断低吸": [0.019],
    "低吸-中位低吸": [0.019],
    "低吸-中位断板低吸": [0.019],
    "低吸-中位断板低吸:低频": [0.019],
    "低吸-中位断板低吸:高频": [0.019],
    "低吸-中位高强中低开低吸": [0.019],
    "低吸-连断低吸": [0.019],
    "低吸-高强中低开低吸": [0.019],
    "低吸-低位高强低吸": [0.019],
    "低吸-高强低吸": [0.019],
    "低吸-放宽低吸前3": [0.019],
    "低吸-绿盘低吸": [0.019],
    "追涨-小高开追涨": [0.019],
    "追涨-低位中强追涨": [0.019],
    "低吸-低位低吸": [0.019],
    "追涨-断追涨": [0.019],
    "追涨-中位小高开起爆": [0.019],
    "低吸-低位高强中低开低吸": [0.019],
    "低吸-低位中强中低开低吸": [0.019],
    "低吸-中强中低开低吸": [0.019],
    "低吸-首红断低吸": [0.019],
    "接力-一进二弱转强": [0.019]
}

default_positions = {
    "低吸-低位孕线低吸": 0.25,
    "低吸-连断低吸": 0.2,
    "低吸-中位断板低吸": 0.1,
    "低吸-中位断板低吸:低频": 0.1,
    "低吸-中位断板低吸:高频": 0.1,
    "低吸-高强中低开低吸": 0.2,
    "低吸-中位高强中低开低吸": 0.2,
    "低吸-低位高强低吸": 0.2,
    "低吸-高强低吸": 0.2,
    "低吸-放宽低吸前3": 0.25,
    "追涨-小高开追涨": 0.2,
    "追涨-低位中强追涨": 0.2,
    "低吸-绿盘低吸": 0.25,
    "低吸-中位低吸": 0.25,
    "追涨-中位小高开起爆": 0.1,
    "低吸-中位孕线低吸": 0.25,
    "低吸-低位高强中低开低吸": 0.2,
    "低吸-低位中强中低开低吸": 0.2,
    "低吸-中强中低开低吸": 0.2,
    "低吸-首红断低吸": 0.25,
    "接力-一进二弱转强": 0.25
}

##########################strategy configs ################

codes_to_strategies = {}


def get_filter_params(strategy_name, strategies= strategies):
    if '-' in strategy_name:
        sub_strategy_name = strategy_name.split('-')[1]
        strategy_name = strategy_name.split('-')[0]
        sub_strategies = strategies[strategy_name]['sub_strategies']
        if sub_strategy_name in sub_strategies:
            return sub_strategies[sub_strategy_name]['filter_params']
        else:
            return {}
    else:
        return strategies[strategy_name]['filter_params']
    

class OfflineStockQuery:
    def __init__(self):
        self.database = None
        self.load_database()
    
    def load_database(self, filepath=r"D:\workspace\TradeX\ezMoney\sqlite_db\stock_database.csv"):
        """加载本地数据库"""
        try:
            self.database = pd.read_csv(filepath, dtype={'代码': str})
            self.database.set_index('代码', inplace=True)
        except FileNotFoundError:
            raise Exception("本地数据库文件不存在，请先运行生成程序")

    def get_stock_name(self, stock_code):
        """通过股票代码查询名称"""
        # 规范输入格式

        prefix = 'sh' if stock_code.startswith(('6', '9')) else 'sz'
        code = f"{prefix}{stock_code}"
        
        try:
            return self.database.loc[code, '名称']
        except KeyError:
            return ''  # 未找到对应代码


offlineStockQuery = OfflineStockQuery()

def time_str_between_925(time_str):
    if '-' in time_str:
        time_str = time_str.replace('-', '')
    time_obj = datetime.datetime.strptime(time_str, '%Y%m%d %H:%M:%S')
    start_time = time_obj.replace(hour=9, minute=20, second=0, microsecond=0)
    end_time = time_obj.replace(hour=9, minute=26, second=0, microsecond=0)
    is_between = start_time < time_obj < end_time
    return is_between

def time_between_925(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp)
    start_time = dt.replace(hour=9, minute=20, second=0, microsecond=0)
    end_time = dt.replace(hour=9, minute=26, second=0, microsecond=0)
    is_between = start_time < dt < end_time
    return is_between

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


def group_filter_fuc(candicates, code_to_index_dict,filtered = True, fx_filtered = False, topn = 2, top_fx = 2, top_cx = 2, only_fx = False, enbale_industry= False, empty_priority = False, min_trade_amount= 0):
    c_codes = [candicate.code for candicate in candicates]
    logger.info("group_filter_fuc candicates:{}".format(c_codes))
    codes = []

    if min_trade_amount > 0:
       
        logger.info("group_filter_fuc min_trade_amount:{}".format(min_trade_amount))
        r_codes = [qmt_trader.all_stocks[code.split('.')[0]] for code in c_codes]
        r_codes_dict = {code.split('.')[0] : code for code in c_codes}
        logger.info("group_filter_fuc r_codes:{}".format(r_codes))
        logger.info("group_filter_fuc r_codes_dict:{}".format(r_codes_dict))
        ful_ticks = xtdata.get_full_tick(r_codes)
        logger.info("group_filter_fuc ful_ticks:{}".format(ful_ticks))
        for code in r_codes:
            if do_test:
                real_amount = get_first_tick_trade_amount(code, test_date)
                if real_amount < min_trade_amount:
                    logger.info("group_filter_fuc code real_amount:{}".format(real_amount))
                    continue
                else:
                    codes.append(r_codes_dict[code.split('.')[0]])
                continue
            if code not in ful_ticks:
                logger.error("group_filter_fuc code not in ful_ticks:{}".format(code))
                codes.append(r_codes_dict[code.split('.')[0]])
                continue
            ful_tick = ful_ticks[code]
            logger.info("group_filter_fuc code ful_tick:{}".format(ful_tick))
            if 'timetag' in ful_tick:
                timestr = ful_tick['timetag']
                is_between = time_str_between_925(timestr)
            elif 'time' in ful_tick:
                timestamp = ful_tick['time'] / 1000
                is_between = time_between_925(timestamp)
            else:
                logger.error("group_filter_fuc code ful_tick not timetag or time:{}".format(code))
                codes.append(r_codes_dict[code.split('.')[0]])
                continue
            if is_between:
                logger.info("group_filter_fuc code is between:{}".format(code))
                amount = ful_tick['amount']
                logger.info("group_filter_fuc code amount:{}".format(amount))
                if amount < min_trade_amount:
                    logger.info("group_filter_fuc code amount is less than min_trade_amount:{}".format(code))
                    continue
            else:
                logger.info("group_filter_fuc code is not between:{}".format(code))
            codes.append(r_codes_dict[code.split('.')[0]])

    logger.info("group_filter_fuc filtered codes:{}".format(codes))
    if not codes:
        return []
    if not filtered:
        return codes[:topn]
    code_to_index_dict = {key: value for key, value in code_to_index_dict.items() if key in codes}
    if fx_filtered:
        min_category_rank = get_max_block_category_rank(code_to_index_dict)
        if enbale_industry:
            max_industry_code_rank_items = get_max_industry_code_rank_items_by_rank(code_to_index_dict, rank=1)
            if len(max_industry_code_rank_items) == 1:
                return max_industry_code_rank_items
            if len(max_industry_code_rank_items) > 1:
                for code in codes:
                    if code in max_industry_code_rank_items:
                        return [code]
                return codes[:1]
        if min_category_rank > top_fx:
            if only_fx:
                return []
            else:
                return codes[:1]
        elif min_category_rank < 0:
            if empty_priority:
                filter_category_codes = get_max_block_category_rank_rang(code_to_index_dict, rmax=top_fx)
                filter_block_codes = get_max_block_code_rank_rang(code_to_index_dict, rmax=top_cx)
                filter_industry_codes = get_max_industry_code_rank_rang(code_to_index_dict, rmin=0, rmax=top_cx)
                union_codes = set(filter_industry_codes).union(set(filter_block_codes))
                filter_codes = list(set(filter_category_codes).intersection(union_codes))
                if len(filter_codes) > 1:
                    # filter_codes = get_min_block_code_items_from_filter_codes(code_to_index_dict, filter_codes)
                    for code in codes:
                        if code in filter_codes:
                            return [code]
                    return filter_codes[:1]
                elif len(filter_codes) == 1:
                    return filter_codes
                else:
                    if only_fx:
                        return []
                    return codes[:1]
            else:
                filter_category_codes = get_max_block_category_rank_rang(code_to_index_dict,rmin=0, rmax=top_fx)
                filter_block_codes = get_max_block_code_rank_rang(code_to_index_dict,rmin=0, rmax=top_cx)
                filter_industry_codes = get_max_industry_code_rank_rang(code_to_index_dict, rmin=0, rmax=top_cx)
                union_codes = set(filter_industry_codes).union(set(filter_block_codes))
                filter_codes = list(set(filter_category_codes).intersection(union_codes))
                if len(filter_codes) >= 1:
                    
                    for code in codes:
                        if code in filter_codes:
                            return [code]
                    return filter_codes[:1]
                else:
                    block_category_rank_codes = get_max_block_category_rank_items_by_rank(code_to_index_dict, rank = min_category_rank)
                    if len(block_category_rank_codes) > 0:
                        for code in codes:
                            if code in block_category_rank_codes:
                                return [code]
                        return block_category_rank_codes[:1]
                    if only_fx:
                        return []
                    return codes[:1]
        else:
            if empty_priority:
                filter_category_codes = get_max_block_category_rank_rang(code_to_index_dict, rmax=top_fx)
                filter_block_codes = get_max_block_code_rank_rang(code_to_index_dict, rmax=top_cx)
                filter_industry_codes = get_max_industry_code_rank_rang(code_to_index_dict, rmin=0, rmax=top_cx)
                union_codes = set(filter_industry_codes).union(set(filter_block_codes))
                filter_codes = list(set(filter_category_codes).intersection(union_codes))
                if len(filter_codes) > 1:
                    # filter_codes = get_min_block_code_items_from_filter_codes(code_to_index_dict, filter_codes)
                    for code in codes:
                        if code in filter_codes:
                            return [code]
                    return filter_codes[:1]
                elif len(filter_codes) == 1:
                    return filter_codes
                else:
                    if only_fx:
                        return []
                    return codes[:1]
            else:
                filter_category_codes = get_max_block_category_rank_rang(code_to_index_dict,rmin=0, rmax=top_fx)
                filter_block_codes = get_max_block_code_rank_rang(code_to_index_dict,rmin=0, rmax=top_cx)
                filter_industry_codes = get_max_industry_code_rank_rang(code_to_index_dict, rmin=0, rmax=top_cx)
                union_codes = set(filter_industry_codes).union(set(filter_block_codes))
                filter_codes = list(set(filter_category_codes).intersection(union_codes))
                if len(filter_codes) >= 1:

                    for code in codes:
                        if code in filter_codes:
                            return [code]
                    return filter_codes[:1]
                else:
                    if only_fx:
                        return []
                    else:
                        return codes[:1]
    else:
        return codes[:1]
            
def get_max_block_category_rank_rang(code_to_index_dict, rmin = None, rmax = None):
    res = []
    for code, info in code_to_index_dict.items():
        if'max_block_category_rank' not in info:
            continue
        if rmin != None and info['max_block_category_rank'] < rmin:
            continue
        if rmax != None and info['max_block_category_rank'] > rmax:
            continue
        res.append(code)
    return res


def get_min_block_code_items_from_filter_codes(code_to_index_dict, filter_codes):
    res = []
    min_block_code = filter_codes[0]
    min_block_code_rank = code_to_index_dict[min_block_code]['max_block_code_rank']
    for code, info in code_to_index_dict.items():
        if'max_block_code_rank' not in info:
            continue
        if code not in filter_codes:
            continue
        if info['max_block_code_rank'] < min_block_code_rank:
            min_block_code_rank = info['max_block_code_rank']
    for code, info in code_to_index_dict.items():
        if'max_block_code_rank' not in info:
            continue
        if code not in filter_codes:
            continue
        if info['max_block_code_rank'] == min_block_code_rank:
            res.append(code)
    return res

def get_max_block_code_rank_rang(code_to_index_dict, rmin = None, rmax = None):
    res = []
    for code, info in code_to_index_dict.items():
        if'max_block_code_rank' not in info:
            continue
        if rmin!= None and info['max_block_code_rank'] < rmin:
            continue
        if rmax!= None and info['max_block_code_rank'] > rmax:
            continue
        res.append(code)
    return res


def get_max_industry_code_rank_rang(code_to_index_dict, rmin = None, rmax = None):
    res = []
    for code, info in code_to_index_dict.items():
        if'max_industry_code_rank' not in info:
            continue
        if rmin!= None and info['max_industry_code_rank'] < rmin:
            continue
        if rmax!= None and info['max_industry_code_rank'] > rmax:
            continue
        res.append(code)
    return res

def get_max_block_category_rank(code_to_index_dict):
    min_category_rank = 101
    for _, info in code_to_index_dict.items():
        if 'max_block_category_rank' not in info:
            continue
        min_category_rank = min(min_category_rank, info['max_block_category_rank'])
    return min_category_rank

def get_max_block_code_rank(code_to_index_dict):
    min_block_code_rank = 101
    for _, info in code_to_index_dict.items():
        if'max_block_code_rank' not in info:
            continue
        min_block_code_rank = min(min_block_code_rank, info['max_block_code_rank'])
    return min_block_code_rank

def get_max_industry_code_rank(code_to_index_dict):
    min_industry_code_rank = 101
    for _, info in code_to_index_dict.items():
        if'max_industry_code_rank' not in info:
            continue
        min_industry_code_rank = min(min_industry_code_rank, info['max_industry_code_rank'])
    return min_industry_code_rank


def get_max_block_category_rank_items_by_rank(code_to_index_dict, rank=1):
    res = []
    for code, info in code_to_index_dict.items():
        if'max_block_category_rank' not in info:
            continue
        if info['max_block_category_rank'] == rank:
            res.append(code)
    return res

def get_max_industry_code_rank_items_by_rank(code_to_index_dict, rank=1):
    res = []
    for code, info in code_to_index_dict.items():
        if'max_industry_code_rank' not in info:
            continue
        if info['max_industry_code_rank'] == rank:
            res.append(code)
    return res



def direction_filter_fuc(candicates, category_infos, params):
    res = []
    res_dict = {}
    if not candicates:
        return res_dict
    # if len(candicates) == 1:
    #     return [candicates[0].code]
    
    # if not params:
    #     logger.info("direction_filter_fuc params is empty")
    #     return [candicates[0].code]
    
    for c_param in params:
        fuc_params = {
        }
        
        if 'filtered' in c_param:
            filtered = c_param['filtered']
            fuc_params['filtered'] = filtered
        else:
            filtered = None
        if 'fx_filtered' in c_param:
            fx_filtered = c_param['fx_filtered']
            fuc_params['fx_filtered'] = fx_filtered
        else:
            fx_filtered = None
        if 'topn' in c_param:
            topn = c_param['topn']
            fuc_params['topn'] = topn
        else:
            topn = None
        if 'top_fx' in c_param:
            top_fx = c_param['top_fx']
            fuc_params['top_fx'] = top_fx
        else:
            top_fx = None
        if 'top_cx' in c_param:
            top_cx = c_param['top_cx']
            fuc_params['top_cx'] = top_cx
        else:
            top_cx = None
        if 'only_fx' in c_param:
            only_fx = c_param['only_fx']
            fuc_params['only_fx'] = only_fx
        else:
            only_fx = None
        if 'enbale_industry' in c_param:
            enbale_industry = c_param['enbale_industry']
            fuc_params['enbale_industry'] = enbale_industry
        else:
            enbale_industry = None
        if 'empty_priority' in c_param:
            empty_priority = c_param['empty_priority']
            fuc_params['empty_priority'] = empty_priority
        else:
            empty_priority = None
        if 'min_trade_amount' in c_param:
            min_trade_amount = c_param['min_trade_amount']
            fuc_params['min_trade_amount'] = min_trade_amount
        else:
            min_trade_amount = None

        if 'block_rank_filter' in c_param:
            block_rank_filter = c_param['block_rank_filter']
        else:
            block_rank_filter = False

        if 'gap' in c_param:
            gap = c_param['gap']
        else:
            gap = 0
        if 'except_is_ppp' in c_param:
            except_is_ppp = c_param['except_is_ppp']
        else:
            except_is_ppp = False
        if 'except_is_track' in c_param:
            except_is_track = c_param['except_is_track']
        else:
            except_is_track = False

        if not category_infos or len(category_infos) == 0:
            return [candicates[0].code]
        
        code_to_index_dict = {}

        category_dict = {}
        block_dict = {}    
        block_list = []
        rank_dict = {}
        index = 1
        for info in category_infos:
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
            isPpp = 1 if info.isPpp else 0
            isTrack = 1 if info.isTrack else 0
            category_dict[categoryCode] = {}
            category_dict[categoryCode]['categoryCode'] = categoryCode
            category_dict[categoryCode]['categoryName'] = categoryName
            category_dict[categoryCode]['num'] = num
            category_dict[categoryCode]['prePctChangeRate'] = prePctChangeRate
            category_dict[categoryCode]['numChange'] = numChange
            category_dict[categoryCode]['blocks'] = []
            if stockType and stockType == 'industry':
                category_dict[categoryCode]['industry'] = 1
                block_list.append((categoryCode, num, prePctChangeRate, numChange, isPpp, isTrack))
                category_dict[categoryCode]['blocks'].append(categoryCode)
            else:
                category_dict[categoryCode]['industry'] = 0
            
            
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
                    isPpp_b = 1 if block['isPpp'] else 0
                    isTrack_b = 1 if block['isTrack'] else 0
                    block_list.append((blockCode, num, prePctChangeRate, numChange, isPpp_b, isTrack_b))
            if except_is_track and isTrack == 1:
                category_dict[categoryCode]['rank'] = 101
                continue
            if except_is_ppp and isPpp == 1:
                category_dict[categoryCode]['rank'] = 101
                continue
            category_dict[categoryCode]['rank'] = index
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
        if block_rank_filter:
            if except_is_ppp:
                block_list = [block for block in block_list if block[4] == 0]
            if except_is_track:
                block_list = [block for block in block_list if block[5] == 0]
            block_list = sorted(block_list, key=lambda x: (-x[1], -x[3]))
            prev_num = None
            current_rank = 1
            for idx, item in enumerate(block_list):
                code = item[0]
                num = item[1]

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

        index = 0
        for item in candicates:
            code = item.code
            if not code:
                continue
            index = index + 1
            if code not in code_to_index_dict:
                logger.info("direction_filter_fuc code:{} not in code_to_index_dict".format(code))
                code_to_index_dict[code] = {}
                code_to_index_dict[code]['index'] = index
                code_to_index_dict[code]['max_block_category_rank'] = -1
                code_to_index_dict[code]['max_block_code_rank'] = -1
                code_to_index_dict[code]['max_industry_code_rank'] = -1
            else:
                raise
            
            blockCategoryCodeList = item.blockCategoryCodeList
            blockCodeList = item.blockCodeList
            industryBlockCodeList = item.industryBlockCodeList
            if blockCategoryCodeList and len(blockCategoryCodeList) > 0:
                min_rank = 100
                for category in blockCategoryCodeList:
                    if category not in category_dict:
                        continue
                    info = category_dict[category]
                    assert info['categoryCode'] == category
                    info_rank = info['rank']
                    min_rank = min(min_rank, info_rank)
                code_to_index_dict[code]['max_block_category_rank'] = min_rank

            if blockCodeList and len(blockCodeList) > 0:
                min_rank = 100
                for block in blockCodeList:
                    if block not in block_dict:
                        continue
                    info = block_dict[block]
                    assert info['blockCode'] == block
                    info_rank = info['rank']
                    min_rank = min(min_rank, info_rank)
                code_to_index_dict[code]['max_block_code_rank'] = min_rank
                
            
            if industryBlockCodeList and len(industryBlockCodeList) > 0:
                min_rank = 100
                for icode in industryBlockCodeList:
                    if icode in category_dict:
                        info = category_dict[icode]
                        assert info['categoryCode'] == icode
                        info_rank = info['rank']
                        min_rank = min(min_rank, info_rank)
                    if icode in block_dict:
                        info = block_dict[icode]
                        assert info['blockCode'] == icode
                        info_rank = info['rank']
                        min_rank = min(min_rank, info_rank)
                code_to_index_dict[code]['max_industry_code_rank'] = min_rank
            
            if block_rank_filter:
                min_rank_filter = 100
                if not blockCodeList:
                    continue
                else:
                    for block in blockCodeList:
                        if block not in rank_dict:
                            continue
                        rank_this = rank_dict[block]
                        min_rank_filter = min(min_rank_filter, rank_this)
                if not industryBlockCodeList:
                    code_to_index_dict[code]['max_block_code_rank'] = min_rank_filter
                    continue
                else:
                    i_min_rank_filter = 100
                    for i_code in industryBlockCodeList:
                        if i_code in rank_dict:
                            rank_this = rank_dict[i_code]
                            min_rank_filter = min(min_rank_filter, rank_this)
                            i_min_rank_filter = min(i_min_rank_filter, rank_this)
                            code_to_index_dict[code]['max_industry_code_rank'] = i_min_rank_filter
                code_to_index_dict[code]['max_block_code_rank'] = min_rank_filter

        # order_logger.info("direction_filter_fuc code_to_index_dict:{}".format(code_to_index_dict))
        c_res = group_filter_fuc(candicates, code_to_index_dict, **fuc_params)
        if c_res and len(c_res) > 0:
            apos = 1 / len(c_res)
            for c in c_res:
                if c:
                    res.append((c, apos))
    
    if not res:
        return {}
    
    for c, ppos in res:
        if c in res_dict:
            res_dict[c] = res_dict[c] + ppos
        else:
            res_dict[c] = ppos

    return res_dict


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

def set_position_to_budgets(position = 0, budgets_dict = budgets):
    for _, budget in budgets_dict.items():
        if not budget or len(budget) == 0:
            continue
        budget['total_position'] = position + default_position

def get_position_from_budgets(budgets_dict = budgets):
    rslt = {}
    r_rslt = {}
    for key, budget in budgets_dict.items():
        if not budget or len(budget) == 0:
            continue
        codes = budget['codes']
        value = budget['value']
        if not codes or len(codes) == 0:
            continue
        position = budget['total_position'] / len(codes)
        for code in codes:
            if code in rslt:
                v, arr = rslt[code]
                v = v + position * value
                if key not in arr:
                    arr.append(key)
                rslt[code] = (v, arr)
            else:
                rslt[code] = (position * value, [key])
    if rslt:
        for code, (v, arr) in rslt.items():
            if arr:
                arr.sort()
                r_rslt[code] = (v, ','.join(arr))
            else:
                r_rslt[code] = (v, 'unknown')

    return r_rslt

def get_target_return_keys_dict(starategies_dict = strategies):
    target_return_keys_dict = {}
    for strategy_name, strategy_dict in starategies_dict.items():
        if 'sub_strategies' not in strategy_dict or len(strategy_dict['sub_strategies']) == 0:
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
        if do_test:
            items = sm.run_all_strategys(strategies_dict=strategies, current_date=test_date)
        else:
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
            position = 0
            auction_codes = []
            auction_codes_dict = {}
            multi_configs = False
            multi_config_code_dict = {}
            if 'xiao_cao_env' in item:
                xiaocao_envs = item['xiao_cao_env'][0]
                position = get_position(xiaocao_envs)
                logger.info(f"xiaocao_envs_position: {position}")
            if name in item:
                real_item_list = item[name]
                if real_item_list == None:
                    continue
                real_item_dict = {}
                if 'xiaocao_category_info' in item:
                    xiaocao_category_infos = item['xiaocao_category_info']
                    params = get_filter_params(key)
                    if params and len(params) > 1:
                        multi_configs = True
                        for param in params:
                            limit = param['limit']
                            mark = param['mark']
                            multi_config_code_dict[key+':'+mark] = {}
                            item_dict = direction_filter_fuc(real_item_list[:limit], xiaocao_category_infos, params=[param])
                            
                            for code, pos in item_dict.items():
                                if not code or len(code) == 0 or pos <= 0:
                                    continue
                                multi_config_code_dict[key+':'+mark][code.split('.')[0]] = pos
                    else:
                        real_item_dict = direction_filter_fuc(real_item_list, xiaocao_category_infos, params=params)
                else:
                    if type(real_item_list[0]) != str:
                        real_item_list = [t.code for t in real_item_list]
                        lr = len(real_item_list)
                        
                        for code in real_item_list:
                            real_item_dict[code] = 1/lr
                if not multi_configs:
                    for code, pos in real_item_dict.items():
                        if not code or len(code) == 0 or pos <= 0:
                            continue
                        auction_codes.append(code.split('.')[0])
                        auction_codes_dict[code.split('.')[0]] = pos
            if multi_configs and len(multi_config_code_dict):
                rslt_dct.update(multi_config_code_dict)
            if not multi_configs:
                if len(auction_codes_dict):
                    rslt_dct[key] = auction_codes_dict
                else:
                    rslt_dct[key] = {}
        return rslt_dct, position
    except Exception as e:
        logger.error(f"An error occurred in get_target_codes: {e}", exc_info=True)
        return get_target_codes_by_all_strategies(retry_times-1)


def get_position(xiaocao_envs):
    if xiaocao_envs == None or len(xiaocao_envs) == 0:
        return 0
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
        return 0
    lift = lifts[0] * positions[0]  + lifts[1] * positions[1] + lifts[2] * positions[2]
    return lift


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



def merge_result_new(rslt, position):
    res = {}
    if type(rslt) is not dict:
        logger.error(f"merge result type error{type(rslt)}")
        return {}
    if len(rslt) == 0:
        return {}
    for key, codes_dict in rslt.items():
        logger.info(f"策略{key}, 成功得到结果 {codes_dict}.")
        code_len = len(codes_dict)
        if code_len <= 0:
            continue
        if key in default_positions:
            base_position = default_positions[key]
        else:
            base_position = 0
        real_position = max(min(base_position + position, 1), 0)
        avg_position = real_position / code_len
        for code, p in codes_dict.items():
            code_info = key + '|' + str(code)
            res[code_info] = (avg_position * p, key)
    
    return res



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
        m_rslt = merge_result_new(rslt, position)
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
                bid_info = {}
                for code_info, (position, mark_info) in m_rslt.items():
                    if code_info in final_results:
                        continue
                    code = code_info.split('|')[1]
                    code_strategy = code_info.split('|')[0]
                    
                    buffers = []
                    if ':' in code_strategy:
                        code_strategy = code_strategy.split(':')[0]
                    if code_strategy in strategies_to_buffer and len(strategies_to_buffer[code_strategy]) > 0:
                        logger.info(f"[producer] 股票 {code} 有策略{code_strategy} 有buffer {strategies_to_buffer[code_strategy]}")
                        buffers.extend(strategies_to_buffer[code_strategy])
                    buffers.sort()
                    
                    bid_info[code_info] = (code_info, position, buffers, mark_info)
                    qq.put((code, position))
                    final_results[code_info] = position
                    order_logger.info(f"发单准备买入股票 code - {code} , position - {position}.")
                if use_threading_buyer:
                    threading_q.put(bid_info)
                else:
                    q.put(bid_info)
                
    except Exception as e:
        error_time = error_time + 1
        if error_time > 20:
            end_task("code_schedule_job")
        logger.error(f"[producer] 执行任务出现错误 {error_time}次: {e}")


def consumer_to_buy(q, orders_dict, orders):

    def get_order_infos(order_id):
        i = 0
        order_infos = qmt_trader.get_all_orders(filter_order_ids = [order_id])
        while not order_infos and i < 10:
            time.sleep(1)
            order_infos = qmt_trader.get_all_orders(filter_order_ids = [order_id])
            i = i + 1
        return order_infos

    def reorder(order_id, k):
        if k >= 10:
            return
        order_infos = get_order_infos(order_id)
        if not order_infos:
            order_logger.error(f"reorder error no order_infos! order_id {order_id}")
            return
        order_status = order_infos[order_id]['order_status']
        if order_status != xtconstant.ORDER_JUNK:
            order_logger.info(f"reorder success order_id {order_id} order_status {order_status}")
            return
        order_logger.info(f"reorder order_id {order_id} status = 废单")
        order_id = qmt_trader.buy_immediate(code, buy_volume, buy_price - 0.01 * k * k, remark=order_remark)
        if order_id <= 0:
            order_id = qmt_trader.buy_immediate(code, buy_volume, buy_price - 0.01 * k * k, remark=order_remark)
            if order_id <= 0:
                order_id = qmt_trader.buy_immediate(code, buy_volume, buy_price - 0.01 * k * k, remark=order_remark)
        if order_id <= 0:
            order_logger.error(f"reorder error! order_id {order_id}")
            return
        reorder(order_id, k + 1)
    
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
                buffers = data[2]
                mark_info = data[3]
                code_info = data[0]
                strategy_name = code_info.split('|')[0]
                sub_strategy_name = ''
                if ':' in strategy_name:
                    sub_strategy_name = strategy_name.split(':')[1]
                    strategy_name = strategy_name.split(':')[0]
                with SQLiteManager(db_name) as manager:
                    if sub_strategy_name:
                        all_data = manager.query_data_dict("strategy_meta_info", condition_dict={'strategy_name': strategy_name,'strategy_status': 1, 'sub_strategy_name': sub_strategy_name}, columns="*")
                    else:
                        all_data = manager.query_data_dict("strategy_meta_info", condition_dict={'strategy_name': strategy_name, 'strategy_status': 1}, columns="*")
                    if not all_data:
                        order_logger.error(f"strategy_budget not found in db")
                        continue
                    total_assert = all_data[0]['budget']
                    multipy_position = all_data[0]['multipy_position']
                    max_budget = all_data[0]['max_budget']
                    min_budget = all_data[0]['min_budget']
                    total_assert = min(total_assert, max_budget)
                    total_assert = max(total_assert, min_budget)
                    if multipy_position > 0:
                        total_assert = total_assert * data[1]
                    c_cash = min(total_assert, cash)
                    code_id = code_info.split('|')[1]
                    strategy_name = code_info.split('|')[0]
                    order_id = qmt_trader.buy_quickly(code_id, c_cash, order_remark=strategy_name, sync=True, orders_dict=orders_dict, orders=orders, buffers=buffers)
                    if order_id < 0:
                        order_id = qmt_trader.buy_quickly(code_id, c_cash,  order_remark=strategy_name, sync=True, orders_dict=orders_dict, orders=orders, buffer=buffers)
                        if order_id < 0:
                            order_id = qmt_trader.buy_quickly(code_id, c_cash, order_remark=strategy_name, sync=True, orders_dict=orders_dict, orders=orders, buffer=buffers)
            elif type(data) == dict and len(data) > 0:
                code_to_order_info_dict = {}
                for code_info, (code_info, position, buffers, mark_info) in data.items():
                    strategy_name = code_info.split('|')[0]
                    sub_strategy_name = ''
                    if ':' in strategy_name:
                        sub_strategy_name = strategy_name.split(':')[1]
                        strategy_name = strategy_name.split(':')[0]
                    code = code_info.split('|')[1]
                    if code in qmt_trader.all_stocks:
                        code = qmt_trader.all_stocks[code]
                    with SQLiteManager(db_name) as manager:
                        if sub_strategy_name:
                            all_data = manager.query_data_dict("strategy_meta_info", condition_dict={'strategy_name': strategy_name,'strategy_status': 1,'sub_strategy_name': sub_strategy_name}, columns="*")
                        else:
                            all_data = manager.query_data_dict("strategy_meta_info", condition_dict={'strategy_name': strategy_name,'strategy_status': 1}, columns="*")
                        if not all_data:
                            order_logger.error(f"strategy_budget not found in db")
                            continue
                        total_assert = all_data[0]['budget']
                        multipy_position = all_data[0]['multipy_position']
                        max_budget = all_data[0]['max_budget']
                        min_budget = all_data[0]['min_budget']
                        total_assert = min(total_assert, max_budget)
                        total_assert = max(total_assert, min_budget)
                        if multipy_position > 0:
                            total_assert = total_assert * position
                        c_cash = min(total_assert, cash)
                        if buffers and len(buffers) > 0:
                            max_buffer = max(buffers)
                        else:
                            max_buffer = 0
                        if code in code_to_order_info_dict:
                            code_to_order_info_dict[code].append((c_cash, strategy_name, sub_strategy_name, max_buffer))
                        else:
                            code_to_order_info_dict[code] = [(c_cash, strategy_name, sub_strategy_name, max_buffer)]
                order_logger.info(f"code_to_order_info_dict: {code_to_order_info_dict}")
                code_to_buy_price_dict = {}
                code_to_order_volume_dict = {}
                code_to_total_buy_volume_dict = {}
                for code, order_info_list in code_to_order_info_dict.items():
                    buy_buffer= 0
                    buy_volume = 0
                    full_tick_info = qmt_trader.get_full_tick_info(code)
                    if not full_tick_info:
                        order_logger.error(f"get_full_tick_info error! no cache {full_tick_info}, code {code}")
                        continue
                    
                    for order_info in order_info_list:
                        c_cash = order_info[0]
                        strategy_name = order_info[1]
                        sub_strategy_name = order_info[2]
                        max_buffer = order_info[3]
                        buy_buffer = max(buy_buffer, max_buffer)
                        buy_vol = qmt_trader.get_stock_buy_vol(c_cash, full_tick_info)
                        if buy_vol <= 0:
                            order_logger.error(f"get_stock_buy_vol error! buy_vol {buy_vol}, code {code}")
                            continue
                        buy_volume = buy_volume + buy_vol
                        if code in code_to_order_volume_dict:
                            code_to_order_volume_dict[code].append((strategy_name, sub_strategy_name, buy_vol))
                        else:
                            code_to_order_volume_dict[code] = [(strategy_name, sub_strategy_name, buy_vol)]
                    code_to_buy_price_dict[code] = qmt_trader.get_stock_buy_price(full_tick_info, buy_buffer)
                    code_to_total_buy_volume_dict[code] = buy_volume

                for code, buy_volume in code_to_total_buy_volume_dict.items():
                    code_to_total_buy_volume_dict[code] = int(round(buy_volume // 100 * buy_total_coef)) * 100

                order_logger.info(f"code_to_buy_price_dict: {code_to_buy_price_dict}")
                order_logger.info(f"code_to_order_volume_dict: {code_to_order_volume_dict}")
                order_logger.info(f"code_to_total_buy_volume_dict: {code_to_total_buy_volume_dict}")

                for code, buy_volume in code_to_total_buy_volume_dict.items():
                    if code not in code_to_order_volume_dict or buy_volume <= 0:
                        order_logger.error(f"code not found in code_to_order_volume_dict")
                        continue
                    order_volume_infos = code_to_order_volume_dict[code]
                    if not order_volume_infos:
                        order_logger.error(f"order_volume_info not found in db")
                        continue
                    stock_name = offlineStockQuery.get_stock_name(code.split('.')[0])
                    if not stock_name:
                        stock_name = ''
                    order_remark_list = []
                    for order_volume_info in order_volume_infos:
                        strategy_name = order_volume_info[0]
                        if strategy_name not in order_remark_list:
                            order_remark_list.append(strategy_name)
                    order_remark =  ','.join(order_remark_list)
                    buy_price = code_to_buy_price_dict[code]
                    order_id = qmt_trader.buy_immediate(code, buy_volume, buy_price, remark=order_remark)
                    if order_id <= 0:
                        order_id = qmt_trader.buy_immediate(code, buy_volume, buy_price, remark=order_remark)
                        if order_id <= 0:
                            order_id = qmt_trader.buy_immediate(code, buy_volume, buy_price, remark=order_remark)
                    if order_id <= 0:
                        order_logger.error(f"委托失败，股票代码: {code} - {stock_name}, 委托价格: {buy_price}, 委托类型: {xtconstant.FIX_PRICE}, 委托数量: {buy_volume}, 委托ID: {order_id}")
                    else:
                        order_logger.info(f"委托成功，股票代码: {code} - {stock_name}, 委托价格: {buy_price}, 委托类型: {xtconstant.FIX_PRICE}, 委托数量: {buy_volume}, 委托ID: {order_id}")
    
                        order_logger.info(f"reorder order_id {order_id}")
                        reorder(order_id, 1)
                        
                        for order_volume_info in order_volume_infos:
                            strategy_name = order_volume_info[0]
                            sub_strategy_name = order_volume_info[1]
                            order_volume = order_volume_info[2]
                            stock_code = code
                            order_type = xtconstant.FIX_PRICE
                            volume = order_volume
                            new_price = buy_price
                            
                            try:
                                from date_utils import date
                                date_key = date.get_current_date()
                                table_name = 'trade_data'
                                
                                with SQLiteManager(r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db') as manager:
                                    if sub_strategy_name:
                                        manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id,'strategy_name': strategy_name, 'sub_strategy_name': sub_strategy_name, 'buy0_or_sell1': 0,'stock_code': stock_code,'order_type': order_type, 'order_price': new_price, 'order_volume': volume, 'stock_name': stock_name})
                                    else:
                                        manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id, 'strategy_name': strategy_name, 'buy0_or_sell1': 0, 'stock_code': stock_code ,'order_type': order_type, 'order_price': new_price, 'order_volume': volume, 'stock_name': stock_name})
                            except Exception as e:
                                logger.error(f"插入数据失败 {e}")
                                order_logger.error(f"插入数据失败 {e}")

                        if orders_dict != None:
                            orders_dict[order_id] = (code, buy_price, buy_volume, order_type, order_volume_infos, time.time(), True)
                        if orders != None:
                            orders.append(order_id)
                        
            elif type(data) == str and data == 'end':
                break
            else:
                raise
        except Exception as e:
            logger.error(f"[consumer] 执行任务出现错误: {e}")

def get_cancel_budgets(orders_dict, budgets_list):
    new_order_infos = {}
    if budgets_list and len(budgets_list) > 0:
        cached_budget_ids = [budget[1] for budget in budgets_list]
        new_order_infos = qmt_trader.get_all_orders(filter_order_ids = cached_budget_ids)
    cancel_order_infos_dict = qmt_trader.get_all_cancel_order_infos()
    if new_order_infos and len(new_order_infos) > 0:
        cancel_order_infos_dict.update(new_order_infos)
        budgets_list.clear()
    for order_id, order_info in cancel_order_infos_dict.items():
        if order_id in orders_dict:
            stock_code = order_info['stock_code']
            order_volume = order_info['order_volume']
            traded_volume = order_info['traded_volume']
            price = order_info['price']
            order_status = order_info['order_status']
            left_volume = order_volume - traded_volume
            left_budget = left_volume * price
            (d_stock_code, d_price, d_volume, order_type, order_remark, timer, buffered) =  orders_dict[order_id]
            if order_status == xtconstant.ORDER_SUCCEEDED:
                order_logger.info(f"[consumer_to_rebuy] 撤单已成 {order_id} {order_info}")
                continue
            budgets_list.append((stock_code, order_id, left_volume, left_budget, order_remark, buffered, order_status))
    return budgets_list


def consumer_to_rebuy(orders_dict, tick_queue = tick_q):

    time.sleep(0.1)

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
    budgets_list = []

    order_id_to_price_dict = {}
    
    budgets_list = get_cancel_budgets(orders_dict, budgets_list)

    for order_id , order_info in orders_dict.items():
        stock_code = order_info[0]
        price = order_info[1]
        volume = order_info[2]
        order_type = order_info[3]
        time_stamp = order_info[5]
        buffered = order_info[6]
        order_id_to_price_dict[order_id] = price
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
            if is_after_940():
                order_logger.error(f"[consumer_to_rebuy] 已过交易时间，结束任务")
                break
            data = tick_queue.get()
            order_logger.info(f"[consumer] Consumed: {data}")
            # update 撤单dict
            budgets_list = get_cancel_budgets(orders_dict, budgets_list)

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
                orders_to_rebuy = []
                for budget_info in budgets_list:
                    if budget_info[0] == stock_code:
                        orders_to_rebuy.append(budget_info)

                if not cur_uncomplete_orders and len(orders_to_rebuy) == 0:
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
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] < 1.5 * price_diff_pcts[-2] and price_diff_pcts[-2] < -0.0012:
                    is_over_fall = True
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] < 0 and price_diff_pcts[-2] < 0:
                    is_fall = True
                if len(price_diff_pcts) > 1 and price_diff_pcts[-1] > 1.5 * price_diff_pcts[-2] and price_diff_pcts[-2] > 0.0012:
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
                    if order_status_p == xtconstant.ORDER_SUCCEEDED or order_status_p == xtconstant.ORDER_PART_CANCEL or order_status_p == xtconstant.ORDER_CANCELED or order_status_p == xtconstant.ORDER_REPORTED_CANCEL or order_status_p == xtconstant.ORDER_PARTSUCC_CANCEL:
                        if order_id not in uncomplete_orders[stock_code]:
                            continue
                        uncomplete_orders[stock_code].remove(order_id)
                
                cur_uncomplete_orders = uncomplete_orders[stock_code]
                if not cur_uncomplete_orders and len(orders_to_rebuy) == 0:
                    order_logger.info(f"[consumer_to_rebuy] 无未完成订单，且无买入需求，跳过 {stock_code}.")
                    continue
                current_time = datetime.datetime.now().timestamp()
                time_difference =  current_time - (tick_time / 1000)
                if time_difference > 5 or diff > 5:
                    order_logger.error(f"[consumer_to_rebuy] 股票代码超时: {stock_code} curdiff - {time_difference} diff - {diff}")
                    continue
                
                def cancel_order_once(order_id, stock_order_statuses = stock_order_statuses):
                    status_q = stock_order_statuses[order_id]['order_status'] if order_id in stock_order_statuses else None
                    if status_q == None:
                        return
                    if  status_q == xtconstant.ORDER_PART_SUCC or status_q == xtconstant.ORDER_REPORTED or status_q == xtconstant.ORDER_WAIT_REPORTING or status_q == xtconstant.ORDER_UNREPORTED:
                        order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 准备撤单 orderid-{order_id} {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                        cancel_result = qmt_trader.cancel_order(order_id, sync=True)
                        if cancel_result == 0:
                            qmt_trader.add_cancel_order(order_id)

                if cur_uncomplete_orders and len(cur_uncomplete_orders) > 0:
                    for order_id in cur_uncomplete_orders:
                        if order_id not in order_id_to_price_dict:
                            continue
                        if order_id in stock_order_statuses and stock_order_statuses[order_id]['order_status'] == xtconstant.ORDER_JUNK:
                            qmt_trader.add_cancel_order(order_id)
                            continue
                        order_price = order_id_to_price_dict[order_id]
                        price_diff = lastPrice / order_price - 1
                        
                        if price_diff >=0 and price_diff <= 0.006:
                            if is_over_up or (is_cross_avg_up and up_steps > 1) or up_steps > 2:
                                order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格冲高 {price_diff}，有低买可撤低买 orderid-{order_id} {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                                cancel_order_once(order_id)
                            else:
                                order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格平稳 {price_diff}，等待成交 orderid-{order_id} {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                                continue
                        elif price_diff < 0 and price_diff >= -0.006:
                            order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格平稳 {price_diff}，等待成交 orderid-{order_id} {is_over_up}, {is_cross_avg_up}, {up_steps}.")
                            continue
                        elif price_diff > 0.006:
                            if is_over_fall or (is_cross_avg_down and fall_steps > 1) or fall_steps > 2:
                                order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格冲低 {price_diff}，等待成交 orderid-{order_id} {is_over_fall}, {is_cross_avg_down},{fall_steps}.")
                                continue
                            else:
                                cancel_order_once(order_id)
                                continue

                        elif price_diff < -0.006 and price_diff > -0.015:
                            if is_over_up or (is_cross_avg_up and up_steps > 1) or up_steps > 2:
                                order_logger.info(f"[consumer_to_rebuy] 股票代码: {stock_code} 价格低位冲高 {price_diff}，等待成交 orderid-{order_id} {is_over_fall}, {is_cross_avg_down},{fall_steps}.")
                                continue
                            else:
                                cancel_order_once(order_id)
                                continue
                        else:
                            cancel_order_once(order_id)
                            continue

                budgets_list = get_cancel_budgets(orders_dict, budgets_list)
                if not budgets_list:
                    continue
                orders_to_rebuy = []
                for budget_info in budgets_list:
                    if budget_info[0] == stock_code:
                        orders_to_rebuy.append(budget_info)
                if len(orders_to_rebuy) > 0:
                    index = len(orders_to_rebuy) - 1
                    while index >= 0:
                        c_order_id = -1
                        (s_code, o_id, left_volume, left_budget, order_remark, buffered, order_status_c) = orders_to_rebuy[index]

                        if left_volume <= 0:
                            budgets_list = [budget_info for budget_info in budgets_list if budget_info[1]!= o_id]
                            del orders_to_rebuy[index]
                            index = index - 1
                            continue
                        if order_status_c != xtconstant.ORDER_CANCELED and order_status_c != xtconstant.ORDER_PART_CANCEL and order_status_c != xtconstant.ORDER_JUNK:
                            index = index - 1
                            order_logger.info(f"[consumer_to_rebuy] 撤单状态不对 {order_status_c}")
                            continue

                        order_logger.info(f"[consumer_to_rebuy] 股票撤单，有买入量: {stock_code}  - {left_volume} ")
                        stock_name = offlineStockQuery.get_stock_name(stock_code.split('.')[0])
                        if not stock_name:
                            stock_name = ''
                        c_order_id = qmt_trader.rebuy(stock_code, stock_name, 0, left_volume, order_type=xtconstant.MARKET_PEER_PRICE_FIRST, order_volume_infos=order_remark, sync=True)
                        if c_order_id > 0:
                            budgets_list = [budget_info for budget_info in budgets_list if budget_info[1] != o_id]
                            del orders_to_rebuy[index]
                        index = index - 1
        except Exception as e:
            logger.error(f"[consumer] 执行任务出现错误: {e}")


def consumer_to_subscribe(qq):
    if not subscribe:
        return
    from xtquant import xtdata
    xtdata.connect(port=58611)
    subscribe_ids = []
    subscribed_codes = []
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
                if code in subscribed_codes:
                    logger.error(f"[subscribe] 股票代码已经订阅: {data}")
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
                    subscribed_codes.append(code)
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
    # from multiprocessing import Manager
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
                            pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
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

def is_after_1140():
    now = datetime.datetime.now()
    target_time = now.replace(hour=11, minute=40, second=0, microsecond=0)
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
    if use_threading_buyer:
        threading_q.put('end')
    else:
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


def update_trade_budgets():
    try:
        is_trade, pre_trade_date = date.is_trading_day()
        if not is_trade:
            logger.info("非交易日，不更新预算。")
            return
        with SQLiteManager(db_name) as manager: 
            all_trade_data_info = manager.query_data_dict("trade_data", condition_dict={'date_key': pre_trade_date}, columns="*")
            if not all_trade_data_info:
                logger.info(f"交易数据 日期-{pre_trade_date} 没有数据， 跳过更新")
                return
            all_trades = qmt_trader.query_stock_trades()
            if not all_trades:
                order_logger.info("无股票被出售")
                return
            
            trade_infos = {}

            for trade_data_info in all_trade_data_info:
                strategy_name = trade_data_info['strategy_name']
                sub_strategy_name = trade_data_info['sub_strategy_name']
                if sub_strategy_name:
                    strategy_name = strategy_name + "_" + sub_strategy_name
                stock_code = trade_data_info['stock_code']
                trade_price = trade_data_info['trade_price']
                trade_amout = trade_data_info['trade_amount']
                traded_volume = trade_data_info['trade_volume']
                if traded_volume > 0:
                    if stock_code not in trade_infos:
                        trade_infos[stock_code] = {}
                        trade_infos[stock_code][strategy_name] = traded_volume
                    else:
                        if strategy_name not in trade_infos[stock_code]:
                            trade_infos[stock_code][strategy_name] = traded_volume
                        else:
                            trade_infos[stock_code][strategy_name] = trade_infos[stock_code][strategy_name] + traded_volume
            
            def get_all_stocks():
                sell_stocks = {}
                all_trades = qmt_trader.query_stock_trades()
                for trade in all_trades:
                    stock_code = trade.stock_code
                    order_id = trade.order_id
                    traded_price = trade.traded_price
                    traded_volume = trade.traded_volume
                    trade_time = trade.traded_time
                    order_type = trade.order_type
                    traded_amount = trade.traded_amount
                    if order_type != xtconstant.STOCK_SELL:
                        logger.error(f"更新预算，遇到非卖出订单 {stock_code}")
                        continue
                    if stock_code in sell_stocks:
                        sell_stock_info = sell_stocks[stock_code]
                        amout = sell_stock_info[0]
                        volume = sell_stock_info[1]
                        sell_stocks[stock_code] = (amout + traded_amount, volume + traded_volume)
                    else:
                        sell_stocks[stock_code] = (traded_amount, traded_volume)
                
                    order_logger.info(f"股票出售 代码: {stock_code}, 订单ID: {order_id}, 成交价格: {traded_price},成交金额: {traded_amount}, 成交数量: {traded_volume}, 成交时间: {trade_time}, 交易类型: {order_type}")
                return sell_stocks
            
            trade_stocks_list = list(trade_infos.keys())
            i = 0
            while i < 5:
                if len(trade_stocks_list) == 0:
                    order_logger.info("所有股票计算出售完毕")
                    break
                else:
                    order_logger.info(f"剩余股票 {trade_stocks_list}")
                sell_stocks = get_all_stocks()
                for stock_code, sell_stock_info in sell_stocks.items():
                    amout = sell_stock_info[0]
                    volume = sell_stock_info[1]
                    if volume <= 0:
                        continue
                    avg_price = amout / volume
                    if stock_code in trade_stocks_list:
                        trade_stocks_list.remove(stock_code)
                        order_logger.info(f"更新预算 股票代码: {stock_code}")
                        for strategy_name, traded_volume in trade_infos[stock_code].items():
                            if volume >= traded_volume:
                                volume = volume - traded_volume
                                incument = traded_volume * avg_price
                                manager.update_budget(strategy_name, incument)
                                order_logger.info(f"更新预算 股票代码: {stock_code}, 策略名称: {strategy_name}, 增加金额: {incument}, 增加数量: {traded_volume}")
                            else:
                                if volume > 0:
                                    incument = volume * avg_price
                                    manager.update_budget(strategy_name, incument)
                                    volume = 0
                                    order_logger.info(f"更新预算 股票代码: {stock_code}, 策略名称: {strategy_name}, 增加金额: {incument}, 增加数量: {volume}")
                                else:
                                    break
                i = i + 1
                time.sleep(5)
    except Exception as e:
        order_logger.error(f"更新预算 出现错误: {e}")
        


def schedule_sell_stocks_everyday_at_925():
    if not sell_at_monning:
        return
    try:
        is_trade, pre_trade_date = date.is_trading_day()
        if not is_trade:
            logger.info("非交易日，不更新预算。")
            return
        last_10_trade_days = date.get_trade_dates_by_end(pre_trade_date, 10)

        if not last_10_trade_days:
            order_logger.info("获取最近10个交易日失败")
            return
        last_10_trade_days.sort()

        position_stocks =  qmt_trader.get_tradable_stocks()

        if not position_stocks:
            order_logger.info("无股票可出售 更新所有left volume 为0")
            with SQLiteManager(db_name) as manager:
                for trade_day in last_10_trade_days:
                    manager.update_data("trade_data", {"left_volume": 0}, {"date_key": trade_day})
            return
        
        order_logger.info(f"股票仓位数据： {position_stocks}")

        stock_to_trade_volume = {}
        days_strategy_to_stock_volume = {}

        for position_stock_info in position_stocks:
            if not position_stock_info:
                continue
            stock_code = position_stock_info['stock_code']
            stock_volume = position_stock_info['available_qty']
            if stock_volume > 0:
                stock_to_trade_volume[stock_code] = stock_volume

        order_logger.info(f"可出售股票详情：{stock_to_trade_volume}")
        
        for trade_day in last_10_trade_days:
            with SQLiteManager(db_name) as manager:
                trade_day_datas = manager.query_data_dict("trade_data", {"date_key": trade_day, "buy0_or_sell1": 0})
                trade_day_datas = [trade_day_data for trade_day_data in trade_day_datas if trade_day_data['left_volume'] > 0 and trade_day_data['stock_code'] in stock_to_trade_volume]
                if not trade_day_datas:
                    order_logger.info(f"无数据可出售 {trade_day}")
                    continue
                for trade_day_data in trade_day_datas:
                    strategy_name = trade_day_data['strategy_name']
                    sub_strategy_name = trade_day_data['sub_strategy_name']
                    if sub_strategy_name:
                        strategy_name = strategy_name + ":" + sub_strategy_name
                    stock_code = trade_day_data['stock_code']
                    left_volume = trade_day_data['left_volume']
                    trade_price = trade_day_data['trade_price']
                    order_id = trade_day_data['order_id']
                    row_id =  trade_day_data['id']
                    if trade_day not in days_strategy_to_stock_volume:
                        days_strategy_to_stock_volume[trade_day] = {}
                    if strategy_name not in days_strategy_to_stock_volume[trade_day]:
                        days_strategy_to_stock_volume[trade_day][strategy_name] = []
                    days_strategy_to_stock_volume[trade_day][strategy_name].append((stock_code, left_volume, trade_price, order_id, row_id))

        if not days_strategy_to_stock_volume:
            order_logger.info("无数据可出售")
            return

        strategy_meta_dict = {}
        with SQLiteManager(db_name) as manager:
            all_strategy_meta_infos = manager.query_data_dict("strategy_meta_info", condition_dict={'strategy_status': 1}, columns="*")
            if not all_strategy_meta_infos:
                order_logger.info(f"策略 没有数据， 跳过更新")
                return

            for strategy_meta_info in all_strategy_meta_infos:
                trade_at_open = strategy_meta_info['trade_at_open']
                if not trade_at_open:
                    continue
                strategy_name = strategy_meta_info['strategy_name']
                sub_strategy_name = strategy_meta_info['sub_strategy_name']
                if sub_strategy_name:
                    strategy_name = strategy_name + ":" + sub_strategy_name
                budget = strategy_meta_info['budget']
                stop_loss_pct = strategy_meta_info['stop_loss_pct']
                take_profit_pct = strategy_meta_info['take_profit_pct']
                max_trade_days = strategy_meta_info['max_trade_days']

                strategy_meta_dict[strategy_name] = {
                    'budget': budget,
                    'stop_loss_pct': stop_loss_pct,
                    'take_profit_pct': take_profit_pct,
                    'max_trade_days': max_trade_days
                }
        ll = len(last_10_trade_days)

        sells_candidates = []
        for idx, trade_day in enumerate(last_10_trade_days):
            gap_days = ll - idx
            if trade_day in days_strategy_to_stock_volume:
                for strategy_name, strategy_stock_volumes in days_strategy_to_stock_volume[trade_day].items():
                    if strategy_name not in strategy_meta_dict:
                        order_logger.info(f"策略 {strategy_name} 没有数据， 跳过更新")
                        continue
                    strategy_meta_info = strategy_meta_dict[strategy_name]
                    budget = strategy_meta_info['budget']
                    stop_loss_pct = strategy_meta_info['stop_loss_pct']
                    take_profit_pct = strategy_meta_info['take_profit_pct']
                    max_trade_days = strategy_meta_info['max_trade_days']
                    if gap_days > max_trade_days:
                        order_logger.info(f"策略 {strategy_name} 最大交易天数 {max_trade_days} 已超过 {gap_days} 天")
                        for strategy_stock_volume_info in strategy_stock_volumes:
                            stock_code = strategy_stock_volume_info[0]
                            left_volume = strategy_stock_volume_info[1]
                            trade_price = strategy_stock_volume_info[2]
                            order_id = strategy_stock_volume_info[3]
                            row_id = strategy_stock_volume_info[4]
                            sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day, 'max_days', row_id))
                    else:
                        for strategy_stock_volume_info in strategy_stock_volumes:
                            stock_code = strategy_stock_volume_info[0]
                            left_volume = strategy_stock_volume_info[1]
                            trade_price = strategy_stock_volume_info[2]
                            order_id = strategy_stock_volume_info[3]
                            row_id = strategy_stock_volume_info[4]
                            full_tick = xtdata.get_full_tick([stock_code])
        
                            if not full_tick or len(full_tick) == 0:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            elif stock_code not in full_tick:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            elif 'lastPrice' not in full_tick[stock_code]:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            elif 'lastClose' not in full_tick[stock_code]:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            
                            current_price = full_tick[stock_code]['lastPrice']
                            cur_profit = current_price / trade_price - 1
                            if cur_profit > take_profit_pct:
                                sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day,f'take_profit|{take_profit_pct}', row_id))
                            elif cur_profit < stop_loss_pct:
                                sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day,f'stop_loss|{stop_loss_pct}', row_id))
                            else:
                                continue
        
        sells_candidates = sorted(sells_candidates, key=lambda x: x[7], reverse=True)

        if not sells_candidates:
            order_logger.info("无数据可出售")
            return
        
        for sells_candidate in sells_candidates:
            logger.info(f"准备出售前数据 {sells_candidate}")
        
        logger.info(f"持仓所有可出售数据 {stock_to_trade_volume}")

        codes_to_sell_infos = {}

        codes_to_sell_volume = {}

        with SQLiteManager(db_name) as manager:
            for sells_candidate in sells_candidates:
                stock_code = sells_candidate[0]
                left_volume = sells_candidate[1]
                trade_price = sells_candidate[2]
                order_id = sells_candidate[3]
                strategy_name = sells_candidate[4]
                trade_day = sells_candidate[5]
                reason = sells_candidate[6]
                row_id = sells_candidate[7]

                if left_volume <= 0:
                    continue

                if stock_code not in stock_to_trade_volume:
                    order_logger.info(f"股票 {stock_code} 已被出售")
                    continue
                all_volume = stock_to_trade_volume[stock_code]
                if all_volume <= 0:
                    order_logger.info(f"股票 {stock_code} 已被出售")
                    manager.update_data("trade_data", {"left_volume": 0}, {"id": row_id})
                    continue
                if left_volume > all_volume:
                    order_logger.info(f"股票 {stock_code} 准备出售 {all_volume}")
                    manager.update_data("trade_data", {"left_volume": all_volume}, {"id": row_id})
                    if stock_code in codes_to_sell_volume:
                        codes_to_sell_volume[stock_code] = codes_to_sell_volume[stock_code] + all_volume
                    else:
                        codes_to_sell_volume[stock_code] = all_volume
                    if stock_code in codes_to_sell_infos:
                        codes_to_sell_infos[stock_code].append((stock_code, left_volume, trade_price, row_id, strategy_name, trade_day, reason, all_volume))
                    else:
                        codes_to_sell_infos[stock_code] = [(stock_code, left_volume, trade_price, row_id, strategy_name, trade_day, reason, all_volume)]
                    # oid = qmt_trader.sell_quickly(stock_code, all_volume, order_remark= strategy_name,  buffer=-0.002, extra_info = sells_candidate)
                    # if oid > 0:
                    stock_to_trade_volume[stock_code] = 0
                    continue
                if left_volume <= all_volume:
                    order_logger.info(f"股票 {stock_code} 准备出售 {left_volume}")
                    if stock_code in codes_to_sell_volume:
                        codes_to_sell_volume[stock_code] = codes_to_sell_volume[stock_code] + left_volume
                    else:
                        codes_to_sell_volume[stock_code] = left_volume
                    if stock_code in codes_to_sell_infos:
                        codes_to_sell_infos[stock_code].append((stock_code, left_volume, trade_price, row_id, strategy_name, trade_day, reason, left_volume))
                    else:
                        codes_to_sell_infos[stock_code] = [(stock_code, left_volume, trade_price, row_id, strategy_name, trade_day, reason, left_volume)]

                    # oid = qmt_trader.sell_quickly(stock_code, left_volume, order_remark= strategy_name,  buffer=-0.002, extra_info = sells_candidate)
                    # if oid > 0:
                    stock_to_trade_volume[stock_code] = stock_to_trade_volume[stock_code] - left_volume
                    continue
        logger.info(f"出售后 left volume {stock_to_trade_volume}")

        for code, sell_volume in codes_to_sell_volume.items():
            extra_infos = codes_to_sell_infos[code]
            stock_name = offlineStockQuery.get_stock_name(code.split('.')[0])
            if not stock_name:
                stock_name = ''
            qmt_trader.sell_quickly(code, stock_name, sell_volume, order_remark= "sell",  buffer=-0.0035, extra_infos = extra_infos, up_sell=True)

    except Exception as e:
        order_logger.error(f"早盘出售 出现错误: {e}")



def schedule_update_sell_stock_infos_everyday_at_925():
    if not sell_at_monning:
        return
    try:
        is_trade, pre_trade_date = date.is_trading_day()
        if not is_trade:
            logger.info("[update_sell_stocks]非交易日，不更新预算。")
            return
        last_10_trade_days = date.get_trade_dates_by_end(pre_trade_date, 10)

        if not last_10_trade_days:
            order_logger.info("[update_sell_stocks]获取最近10个交易日失败")
            return
        last_10_trade_days.sort()

        position_stocks =  qmt_trader.get_tradable_stocks()

        if not position_stocks:
            order_logger.info("[update_sell_stocks]无股票可出售 更新所有left volume 为0")
            with SQLiteManager(db_name) as manager:
                for trade_day in last_10_trade_days:
                    manager.update_data("trade_data", {"left_volume": 0}, {"date_key": trade_day})
            return
        
        order_logger.info(f"[update_sell_stocks]股票仓位数据： {position_stocks}")

        stock_to_trade_volume = {}
        days_strategy_to_stock_volume = {}

        for position_stock_info in position_stocks:
            if not position_stock_info:
                continue
            stock_code = position_stock_info['stock_code']
            stock_volume = position_stock_info['available_qty']
            if stock_volume > 0:
                stock_to_trade_volume[stock_code] = stock_volume

        order_logger.info(f"[update_sell_stocks]可出售股票详情：{stock_to_trade_volume}")
        
        for trade_day in last_10_trade_days:
            with SQLiteManager(db_name) as manager:
                trade_day_datas = manager.query_data_dict("trade_data", {"date_key": trade_day, "buy0_or_sell1": 0})
                trade_day_datas = [trade_day_data for trade_day_data in trade_day_datas if trade_day_data['left_volume'] > 0 and trade_day_data['stock_code'] in stock_to_trade_volume]
                if not trade_day_datas:
                    order_logger.info(f"[update_sell_stocks]无数据可出售 {trade_day}")
                    continue
                for trade_day_data in trade_day_datas:
                    strategy_name = trade_day_data['strategy_name']
                    sub_strategy_name = trade_day_data['sub_strategy_name']
                    if sub_strategy_name:
                        strategy_name = strategy_name + ":" + sub_strategy_name
                    stock_code = trade_day_data['stock_code']
                    left_volume = trade_day_data['left_volume']
                    trade_price = trade_day_data['trade_price']
                    order_id = trade_day_data['order_id']
                    row_id =  trade_day_data['id']
                    if trade_day not in days_strategy_to_stock_volume:
                        days_strategy_to_stock_volume[trade_day] = {}
                    if strategy_name not in days_strategy_to_stock_volume[trade_day]:
                        days_strategy_to_stock_volume[trade_day][strategy_name] = []
                    days_strategy_to_stock_volume[trade_day][strategy_name].append((stock_code, left_volume, trade_price, order_id, row_id))

        if not days_strategy_to_stock_volume:
            order_logger.info("[update_sell_stocks]无数据可出售")
            return

        strategy_meta_dict = {}
        with SQLiteManager(db_name) as manager:
            all_strategy_meta_infos = manager.query_data_dict("strategy_meta_info", condition_dict={'strategy_status': 1}, columns="*")
            if not all_strategy_meta_infos:
                order_logger.info(f"策略 没有数据， 跳过更新")
                return

            for strategy_meta_info in all_strategy_meta_infos:
                trade_at_open = strategy_meta_info['trade_at_open']
                if not trade_at_open:
                    continue
                strategy_name = strategy_meta_info['strategy_name']
                sub_strategy_name = strategy_meta_info['sub_strategy_name']
                if sub_strategy_name:
                    strategy_name = strategy_name + ":" + sub_strategy_name
                budget = strategy_meta_info['budget']
                stop_loss_pct = strategy_meta_info['stop_loss_pct']
                take_profit_pct = strategy_meta_info['take_profit_pct']
                max_trade_days = strategy_meta_info['max_trade_days']

                strategy_meta_dict[strategy_name] = {
                    'budget': budget,
                    'stop_loss_pct': stop_loss_pct,
                    'take_profit_pct': take_profit_pct,
                    'max_trade_days': max_trade_days
                }
        ll = len(last_10_trade_days)

        sells_candidates = []
        for idx, trade_day in enumerate(last_10_trade_days):
            gap_days = ll - idx
            if trade_day in days_strategy_to_stock_volume:
                for strategy_name, strategy_stock_volumes in days_strategy_to_stock_volume[trade_day].items():
                    if strategy_name not in strategy_meta_dict:
                        order_logger.info(f"[update_sell_stocks] 策略 {strategy_name} 没有数据， 跳过更新")
                        continue
                    strategy_meta_info = strategy_meta_dict[strategy_name]
                    budget = strategy_meta_info['budget']
                    stop_loss_pct = strategy_meta_info['stop_loss_pct']
                    take_profit_pct = strategy_meta_info['take_profit_pct']
                    max_trade_days = strategy_meta_info['max_trade_days']
                    
                    for strategy_stock_volume_info in strategy_stock_volumes:
                        stock_code = strategy_stock_volume_info[0]
                        left_volume = strategy_stock_volume_info[1]
                        trade_price = strategy_stock_volume_info[2]
                        order_id = strategy_stock_volume_info[3]
                        row_id = strategy_stock_volume_info[4]
                        full_tick = xtdata.get_full_tick([stock_code])
    
                        if not full_tick or len(full_tick) == 0:
                            order_logger.error(f"[update_sell_stocks] 获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                            continue
                        elif stock_code not in full_tick:
                            order_logger.error(f"[update_sell_stocks] 获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                            continue
                        elif 'lastPrice' not in full_tick[stock_code]:
                            order_logger.error(f"[update_sell_stocks] 获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                            continue
                        elif 'lastClose' not in full_tick[stock_code]:
                            order_logger.error(f"[update_sell_stocks] 获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                            continue
                        
                        current_price = full_tick[stock_code]['lastPrice']
                        last_close_price = full_tick[stock_code]['lastClose']
                        cur_profit = current_price / trade_price - 1
                        if cur_profit > take_profit_pct:
                            sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day,f'take_profit|{take_profit_pct}', row_id, cur_profit, current_price, last_close_price, gap_days, max_trade_days))
                        elif cur_profit < stop_loss_pct:
                            sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day,f'stop_loss|{stop_loss_pct}', row_id, cur_profit, current_price, last_close_price, gap_days, max_trade_days))
                        else:
                            if gap_days >= max_trade_days:
                                order_logger.info(f"[update_sell_stocks] 策略 {strategy_name} 最大交易天数 {max_trade_days} 已超过 {gap_days} 天")
                                sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day, 'max_days', row_id, cur_profit, current_price, last_close_price, gap_days, max_trade_days))
                                continue
                            else:
                                continue
        
        sells_candidates = sorted(sells_candidates, key=lambda x: x[7], reverse=True)

        if not sells_candidates:
            order_logger.info("[update_sell_stocks] 无数据可出售")
            return
        
        for sells_candidate in sells_candidates:
            logger.info(f"[update_sell_stocks] 准备出售前数据 {sells_candidate}")
        
        logger.info(f"[update_sell_stocks] 持仓所有可出售数据 {stock_to_trade_volume}")

        with SQLiteManager(db_name) as manager:
            for sells_candidate in sells_candidates:
                stock_code = sells_candidate[0]
                left_volume = sells_candidate[1]
                trade_price = sells_candidate[2]
                order_id = sells_candidate[3]
                strategy_name = sells_candidate[4]
                trade_day = sells_candidate[5]
                reason = sells_candidate[6]
                row_id = sells_candidate[7]
                cur_profit = sells_candidate[8]
                current_price = sells_candidate[9]
                last_close_price = sells_candidate[10]
                gap_days = sells_candidate[11]
                max_trade_days = sells_candidate[12]

                if left_volume <= 0:
                    continue

                if stock_code not in stock_to_trade_volume:
                    order_logger.info(f"[update_sell_stocks] 股票 {stock_code} 已被出售")
                    continue
                all_volume = stock_to_trade_volume[stock_code]
                if all_volume <= 0:
                    order_logger.info(f"[update_sell_stocks] 股票 {stock_code} 已被出售")
                    manager.update_data("trade_data", {"left_volume": 0}, {"id": row_id})
                    continue
                if left_volume > all_volume:
                    order_logger.info(f"[update_sell_stocks] 股票 {stock_code} 准备出售 {all_volume}")
                    manager.update_data("trade_data", {"left_volume": all_volume}, {"id": row_id})

                    
                    monitor_type = -1
                    if 'take_profit' in reason:
                        monitor_type = constants.STOP_PROFIT_TRADE_TYPE
                    elif 'stop_loss' in reason:
                        monitor_type = constants.STOP_LOSS_TRADE_TYPE
                    elif 'max_days' in reason:
                        monitor_type = constants.LAST_TRADE_DAY_TRADE_TYPE
                    if monitor_type == -1:
                        order_logger.error(f"[update_sell_stocks] 股票 {stock_code} 监控类型错误 {reason}")
                        continue

                    monitor_data_update_dict = {
                        "origin_order_id": order_id,
                        "origin_row_id": row_id,
                        "date_key": date.get_current_date(),
                        "strategy_name": strategy_name,
                        "stock_code": stock_code,
                        "trade_price": trade_price,
                        "trade_date": trade_day,
                        "profit_pct": cur_profit,
                        "left_volume": all_volume,
                        "open_price": current_price,
                        "last_close_price": last_close_price,
                        "current_price": current_price,
                        "monitor_type": monitor_type,
                        "max_trade_days": max_trade_days,
                        "current_trade_days": gap_days,
                        "monitor_status": 1
                    }
                    if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                        take_profit_pct = reason.split('|')[1]
                        take_profit_price = trade_price * (1 + float(take_profit_pct))
                        monitor_data_update_dict['take_profit_price'] = take_profit_price
                        monitor_data_update_dict['take_profit_pct'] = take_profit_pct
                    elif monitor_type == constants.STOP_LOSS_TRADE_TYPE:
                        stop_loss_pct = reason.split('|')[1]
                        stop_loss_price = trade_price * (1 + float(stop_loss_pct))
                        monitor_data_update_dict['stop_loss_price'] = stop_loss_price
                        monitor_data_update_dict['stop_loss_pct'] = stop_loss_pct
                    
                    limit_down_price, limit_up_price = constants.get_limit_price(float(last_close_price), stock_code= stock_code)

                    monitor_data_update_dict['limit_down_price'] = limit_down_price
                    monitor_data_update_dict['limit_up_price'] = limit_up_price

                    manager.insert_data("monitor_data", monitor_data_update_dict)
                    stock_to_trade_volume[stock_code] = 0
                    continue
                if left_volume <= all_volume:
                    order_logger.info(f"股票 {stock_code} 准备出售 {left_volume}")

                    monitor_type = -1
                    if 'take_profit' in reason:
                        monitor_type = constants.STOP_PROFIT_TRADE_TYPE
                    elif 'stop_loss' in reason:
                        monitor_type = constants.STOP_LOSS_TRADE_TYPE
                    elif 'max_days' in reason:
                        monitor_type = constants.LAST_TRADE_DAY_TRADE_TYPE
                    if monitor_type == -1:
                        order_logger.error(f"[update_sell_stocks] 股票 {stock_code} 监控类型错误 {reason}")
                        continue

                    monitor_data_update_dict = {
                        "origin_order_id": order_id,
                        "origin_row_id": row_id,
                        "date_key": date.get_current_date(),
                        "strategy_name": strategy_name,
                        "stock_code": stock_code,
                        "trade_price": trade_price,
                        "trade_date": trade_day,
                        "profit_pct": cur_profit,
                        "left_volume": left_volume,
                        "open_price": current_price,
                        "last_close_price": last_close_price,
                        "current_price": current_price,
                        "monitor_type": monitor_type,
                        "max_trade_days": max_trade_days,
                        "current_trade_days": gap_days,
                        "monitor_status": 1
                    }
                    if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                        take_profit_pct = reason.split('|')[1]
                        take_profit_price = trade_price * (1 + float(take_profit_pct))
                        monitor_data_update_dict['take_profit_price'] = take_profit_price
                        monitor_data_update_dict['take_profit_pct'] = take_profit_pct
                    elif monitor_type == constants.STOP_LOSS_TRADE_TYPE:
                        stop_loss_pct = reason.split('|')[1]
                        stop_loss_price = trade_price * (1 + float(stop_loss_pct))
                        monitor_data_update_dict['stop_loss_price'] = stop_loss_price
                        monitor_data_update_dict['stop_loss_pct'] = stop_loss_pct
                    
                    limit_down_price, limit_up_price = constants.get_limit_price(float(last_close_price), stock_code=stock_code)

                    monitor_data_update_dict['limit_down_price'] = limit_down_price
                    monitor_data_update_dict['limit_up_price'] = limit_up_price

                    manager.insert_data("monitor_data", monitor_data_update_dict)
                    stock_to_trade_volume[stock_code] = stock_to_trade_volume[stock_code] - left_volume
                    continue
        logger.info(f"出售后 left volume {stock_to_trade_volume}")

        # for code, sell_volume in codes_to_sell_volume.items():
        #     extra_infos = codes_to_sell_infos[code]
        #     stock_name = offlineStockQuery.get_stock_name(code.split('.')[0])
        #     if not stock_name:
        #         stock_name = ''
        #     qmt_trader.sell_quickly(code, stock_name, sell_volume, order_remark= "sell",  buffer=-0.0035, extra_infos = extra_infos, up_sell=True)

    except Exception as e:
        order_logger.error(f"早盘出售 出现错误: {e}")


def start_monitor_monning():
    if not sell_at_monning:
        return
    try:
        is_trade, pre_trade_date = date.is_trading_day()
        if not is_trade:
            strategy_logger.info("[start_monitor_monning] 非交易日，不更新预算。")
            return
        current_date = date.get_current_date()
        monitor_stock_codes = []
        code_to_monitor_dict = {}
        with SQLiteManager(db_name) as manager:
            query_data_results = manager.query_data_dict("monitor_data", condition_dict={'date_key': current_date, 'monitor_status': 1})
            if not query_data_results:
                strategy_logger.error("[start_monitor_monning] 无监听任务。")
                return
            for data_result in query_data_results:
                stock_code = data_result['stock_code']
                # stock_name = offlineStockQuery.get_stock_name(stock_code.split('.')[0])
                # if not stock_name:
                #     stock_name = ''
                if stock_code and stock_code not in monitor_stock_codes:
                    monitor_stock_codes.append(stock_code)
        
        if monitor_stock_codes:
            for stock_code in monitor_stock_codes:
                stock_name = offlineStockQuery.get_stock_name(stock_code.split('.')[0])
                if not stock_name:
                    stock_name = ''
                stock_monitor = StockMonitor(stock_code=stock_code, stock_name=stock_name, qmt_trader=qmt_trader)
                code_to_monitor_dict[stock_code] = stock_monitor
            
            def monitor_call_back(res, stocks=monitor_stock_codes, monitor_dict = code_to_monitor_dict):
                for stock in stocks:
                    if stock not in res:
                        continue
                    data = res[stock]
                    s_monitor = monitor_dict[stock]
                    s_monitor.consume(data)

            sid = xtdata.subscribe_whole_quote(monitor_stock_codes, callback=monitor_call_back)
            if sid < 0:
                strategy_logger.error(f"[start_monitor_monning] 订阅错误: {monitor_stock_codes}")
            else:
                logger.info(f"[start_monitor_monning] 订阅成功: {monitor_stock_codes}")
                

    except Exception as e:
        pass


if __name__ == "__main__":

    from xtquant import xtdatacenter as xtdc
    xtdc.set_token("26e6009f4de3bfb2ae4b89763f255300e96d6912")

    print('xtdc.init')
    xtdc.init() # 初始化行情模块，加载合约数据，会需要大约十几秒的时间
    print('done')

    print('xtdc.listen')

    addr_list = [
    '115.231.218.73:55310', 
    '115.231.218.79:55310', 
    '42.228.16.211:55300',
    '42.228.16.210:55300',
    '36.99.48.20:55300',
    '36.99.48.21:55300'
    ]
    xtdc.set_allow_optmize_address(addr_list)

    xtdc.set_kline_mirror_enabled(True) 
    
    listen_addr = xtdc.listen(port = 58611)
    print(f'done, listen_addr:{listen_addr}')

    xtdata.connect(port=listen_addr)

    print('-----连接上了------')
    print(xtdata.data_dir)

    servers = xtdata.get_quote_server_status()
    # print(servers)
    for k, v in servers.items():
        print(k, v)
    full_tick_info_dict = Manager().dict()

    qmt_trader.init_order_context(flag = use_threading_buyer)
    qmt_trader.start_sell_listener()
    if use_threading_buyer:
        consumer_thread = threading.Thread(target=consumer_to_buy, args=(threading_q, qmt_trader.orders_dict, qmt_trader.orders,))
    else:
        consumer_thread = multiprocessing.Process(target=consumer_to_buy, args=(q, qmt_trader.orders_dict, qmt_trader.orders))

    # subscribe_thread = multiprocessing.Process(target=consumer_to_subscribe, args=(qq,))
    # subscribe_thread = multiprocessing.Process(target=consumer_to_get_full_tik, args=(qq,full_tick_info_dict))

    subscribe_thread = multiprocessing.Process(target=consumer_to_subscribe_whole, args=(qq, full_tick_info_dict, tick_q))
    consumer_thread.start()
    subscribe_thread.start()
    cached_auction_infos.clear()

    scheduler = BackgroundScheduler()
    # 每隔5秒执行一次 job_func 方法
    scheduler.add_job(strategy_schedule_job, 'interval', seconds=3, id="code_schedule_job")

    # scheduler.add_job(cancel_orders, 'interval', seconds=5, id="code_cancel_job")

    scheduler.add_job(consumer_to_rebuy, 'cron', hour=9, minute=30, second=0, id="consumer_to_rebuy", args=[qmt_trader.orders_dict, tick_q])

    # scheduler.add_job(update_trade_budgets, 'cron', hour=9, minute=25, second=5, id="update_trade_budgets")

    scheduler.add_job(start_monitor_monning, 'cron', hour=9, minute=29, second=0, id="start_monitor_monning")

    if monitor_sell:
        scheduler.add_job(schedule_update_sell_stock_infos_everyday_at_925, 'cron', hour=9, minute=25, second=10, id="schedule_update_sell_stock_infos_everyday_at_925")
    else:
        scheduler.add_job(schedule_sell_stocks_everyday_at_925, 'cron', hour=9, minute=25, second=10, id="schedule_sell_stocks_everyday_at_925")

    # 在 2025-01-21 22:08:01 ~ 2025-01-21 22:09:00 之间, 每隔5秒执行一次 job_func 方法
    # scheduler.add_job(strategy_schedule_job, 'interval', seconds=5, start_date='2025-01-21 22:12:01', end_date='2025-01-21 22:13:00', args=['World!'])

    # 启动调度器
    scheduler.start()

    # 保持程序运行，以便调度器可以执行任务
    try:
        while True:
            if is_after_1140() and not do_test:
                logger.info("达到最大执行时间，退出程序")
                if use_threading_buyer:
                    threading_q.put('end')
                else:
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
    if not use_threading_buyer:
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