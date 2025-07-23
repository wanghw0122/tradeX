import os

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
        all_data = manager.query_data_dict(table_name, condition_dict={'date_key': date_key, 'buy0_or_sell1': 0}, columns="*")
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
        order_id_to_order_infos_dict = {}

        for data in all_data:
            id = int(data['id'])
            order_id = int(data['order_id'])
            strategy_name = data['strategy_name']
            sub_strategy_name = data['sub_strategy_name']
            order_type = data['order_type']
            if order_type == 1:
                continue
            order_volume = int(data['order_volume'])
            if order_id not in order_id_to_order_infos_dict:
                order_id_to_order_infos_dict[order_id] = []
            order_id_to_order_infos_dict[order_id].append({
                'id': id,
                'strategy_name': strategy_name,
                'sub_strategy_name': sub_strategy_name,
                'order_volume': order_volume,
            })
        order_id_to_sorted_order_infos_dict = {}
        
        for order_id, order_infos in order_id_to_order_infos_dict.items():
            if not order_infos:
                logger.error(f"Error order_id - {order_id} 没有数据， 跳过更新")
                continue
            if order_id not in all_trades:
                logger.error(f"Error order_id - {order_id} 没有数据， 跳过更新")
                continue
            sorted_order_infos = sorted(order_infos, key=lambda x: x['id'])
            order_id_to_sorted_order_infos_dict[order_id] = sorted_order_infos

        for order_id, sorted_order_infos in order_id_to_sorted_order_infos_dict.items():
            if not sorted_order_infos:
                logger.error(f"Error order_id - {order_id} 没有数据， 跳过更新")
                continue
            trade_info = all_trades[order_id]
            order_status = trade_info['order_status']
            # order_status == xtconstant.ORDER_PART_SUCC
            traded_volume = trade_info['traded_volume']
            traded_price = trade_info['traded_price']
            total_volume = traded_volume
            if total_volume <= 0:
                logger.error(f"Error order_id - {order_id} 没有成交， 跳过更新")
            for order_info in sorted_order_infos:
                id = order_info['id']
                strategy_name = order_info['strategy_name']
                sub_strategy_name = order_info['sub_strategy_name']
                order_volume = order_info['order_volume']
                if order_volume <= 0:
                    continue
                if total_volume >= order_volume:
                    total_volume = total_volume - order_volume
                    manager.update_data(table_name, {'trade_result': order_status, 'trade_volume': order_volume, 'trade_price': traded_price, 'trade_amount': order_volume * traded_price, 'left_volume': order_volume}, {'id': id})
                elif total_volume > 0:
                    manager.update_data(table_name, {'trade_result': order_status, 'trade_volume': total_volume, 'trade_price': traded_price, 'trade_amount': total_volume * traded_price, 'left_volume': total_volume}, {'id': id})
                    total_volume = 0
                else:
                    break
            