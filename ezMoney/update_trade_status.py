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
    date_key = date.get_current_date()
    budgets_dict = {}
    with SQLiteManager(db_name) as manager: 
        all_data = manager.query_data_dict(table_name, condition_dict={'date_key': date_key}, columns="*")
        if not all_data:
            logger.info(f"交易数据 日期-{date_key} 没有数据， 跳过更新")
            exit(0)
        else:
            logger.info(f"交易数据 日期-{date_key} 有数据 {all_data}， 开始更新")

        # print(all_data)
        all_trades = qmt_trader.get_all_orders()
        if not all_trades:
            logger.info(f"QMT 没有数据， 跳过更新")
            exit(0)
        for data in all_data:
            id = data['id']
            order_id = int(data['order_id'])
            strategy_name = data['strategy_name']
            if order_id not in all_trades:
                logger.error(f"Error order_id - {order_id} 没有数据， 跳过更新")
                continue
            trade_info = all_trades[order_id]
            order_status = trade_info['order_status']
            # order_status == xtconstant.ORDER_PART_SUCC
            traded_volume = trade_info['traded_volume']
            traded_price = trade_info['traded_price']
            traded_amount = traded_volume * traded_price
            if strategy_name not in budgets_dict:
                budgets_dict[strategy_name] = - traded_amount
            else:  
                budgets_dict[strategy_name] = budgets_dict[strategy_name] - traded_amount
            manager.update_data(table_name, {'trade_result': order_status, 'trade_volume': traded_volume, 'trade_price': traded_price, 'trade_amount': traded_amount, 'left_volume': traded_volume}, {'id': id})
        # for strategy_name, increment in budgets_dict.items():
        #     logger.info(f"更新预算 strategy_name: {strategy_name}, increment: {increment}")
        #     manager.update_budget(strategy_name, increment)
            