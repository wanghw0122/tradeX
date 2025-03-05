import os

from py import log
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from logger import logger
from trade.qmtTrade import *
from date_utils import date
from apscheduler.schedulers.background import BackgroundScheduler

from common.constants import *
from sqlite_processor.mysqlite import *


path = r'D:\qmt\userdata_mini'  # QMT客户端路径
acc_id = '8886660057'
# 创建QMTTrader实例
logger.info("开始初始化QMT....")

qmt_trader = QMTTrader(path, acc_id)
qmt_trader.callback.set_qmt(qmt_trader)


db_name = r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'
table_name = 'trade_data'

if __name__ == "__main__":
    is_trade_day, pre_date = date.is_trading_day()
    if not is_trade_day:
        logger.info(f"非交易日， 跳过卖出操作")
        exit(0)
    # date_key = date.get_current_date()
    budgets_dict = {}
    with SQLiteManager(db_name) as manager: 
        all_data = manager.query_data_dict(table_name, condition_dict={'date_key': pre_date, 'strategy_name': 'xiao_cao_1j2db'}, columns="*")
        filter_codes = []
        if not all_data:
            logger.info(f"交易数据 日期-{pre_date} 没有数据， 跳过更新")
        else:
            for data in all_data:
                filter_codes.append(data['stock_code'])

        qmt_trader.sell_all_holdings(filter_codes = filter_codes)
            