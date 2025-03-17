from trade.qmtTrade import *
from sqlite_processor.mysqlite import *
import multiprocessing
from multiprocessing import Queue
q = Queue()
from date_utils import *

path = r'D:\qmt\userdata_mini'  # QMT客户端路径
acc_id = '8886660057'
# 创建QMTTrader实例
logger.info("开始初始化QMT....")

qmt_trader = QMTTrader(path, acc_id)
qmt_trader.callback.set_qmt(qmt_trader)
# ... 已有代码 ...

def consumer_to_rebuy(d, q):
    print("开始执行...")
    while True:
        x = q.get()
        print(f"x:{x}")
        print(f"d: {d}")
        if x == 'end':
            break
    # 从数据库中获取待处理的订单
       
    print("执行完成...")
if __name__ == "__main__":
    # 创建调度器
    # qmt_trader.init_order_context()
    # # qmt_trader.orders_dict['123'] = '123'
    # # qmt_trader.cancel_orders.append('123')
    # # print(qmt_trader.cancel_orders)
    # # while qmt_trader.cancel_orders:
    # #     del qmt_trader.cancel_orders[0]
    # # print(qmt_trader.cancel_orders)
    # ls = qmt_trader.query_stock_trades()
    # for trade in ls:
    #     stock_code = trade.stock_code
    #     order_id = trade.order_id
    #     traded_price = trade.traded_price
    #     traded_volume = trade.traded_volume
    #     trade_time = trade.traded_time
    #     order_type = trade.order_type
    #     traded_amount = trade.traded_amount
    #     print(f"股票代码: {stock_code}, 订单ID: {order_id}, 成交价格: {traded_price},成交金额: {traded_amount}, 成交数量: {traded_volume}, 成交时间: {trade_time}, 交易类型: {order_type}")
    with SQLiteManager(db_name) as manager:
        # manager.insert_data("strategy_budget",{'strategy_name':'追涨-小高开追涨',
        #                                   'budget':30000,
        #                                   'origin_budget': 30000})

        manager.update_data("strategy_budget",{
                                          'origin_budget': 30000,
                                          'budget': 30000}, {'strategy_name':'低吸-中位断板低吸'})
        # manager.update_budget("xiao_cao_1j2db",10000)
       