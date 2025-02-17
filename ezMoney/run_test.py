from trade.qmtTrade import *
from sqlite_processor.mysqlite import *
import multiprocessing
from multiprocessing import Queue
q = Queue()

# class MyClass:
#     def __init__(self):
#         self.orders_dict = {}
#     def get_value(self):
#         return self.orders_dict
#     def set_value(self, key, value):
#         self.orders_dict[key] = value

# class MyManager(BaseManager):
#     pass

# class V():
#     def __init__(self, obj):
#         self.obj = obj
# MyManager.register('MyClass', MyClass)

# def worker(obj):
#     obj.set_value("1", 1)
#     print(f"子进程值: {obj.get_value()}")
    # ... 已有代码 ...

def get_cancelled_orders(qmt_trader):
    """
    查询已撤回的订单
    :param qmt_trader: QMTTrader 实例
    :return: 已撤回订单列表
    """
    # 获取所有订单
    all_orders = qmt_trader.get_all_orders()
    # 筛选出已撤回的订单
   
    return all_orders

# ... 已有代码 ...

if __name__ == "__main__":
    path = r'D:\qmt\userdata_mini'  # QMT客户端路径
    acc_id = '8886660057'
    # 创建QMTTrader实例
    logger.info("开始初始化QMT....")

    qmt_trader = QMTTrader(path, acc_id)
    qmt_trader.callback.set_qmt(qmt_trader)
    # ... 已有代码 ...

    cancel_orders = []
    success_orders = []
    # 查询已撤回的订单
    cancelled_orders = get_cancelled_orders(qmt_trader)
    for order, order_info in cancelled_orders.items():
        if order_info['order_status'] == xtconstant.ORDER_CANCELED:
            cancel_orders.append(order_info)
        elif order_info['order_status'] == xtconstant.ORDER_SUCCEEDED:
            success_orders.append(order_info)
        else:
            print(f"unknown {order_info}")

    print(f"已撤回的订单: {cancel_orders}")


    # ... 已有代码 ...
