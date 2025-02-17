from trade.qmtTrade import *
from sqlite_processor.mysqlite import *
import multiprocessing
from multiprocessing import Queue
q = Queue()

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
    qmt_trader.init_order_context()
    qmt_trader.orders_dict['123'] = '123'
    qmt_trader.cancel_orders.append('123')
    print(qmt_trader.cancel_orders)
    while qmt_trader.cancel_orders:
        del qmt_trader.cancel_orders[0]
    print(qmt_trader.cancel_orders)