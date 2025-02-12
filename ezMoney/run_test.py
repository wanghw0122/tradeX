from multiprocessing import Process
from multiprocessing.managers import BaseManager
from trade.qmtTrade import *

class MyClass:
    def __init__(self):
        self.orders_dict = {}
    def get_value(self):
        return self.orders_dict
    def set_value(self, key, value):
        self.orders_dict[key] = value

class MyManager(BaseManager):
    pass

class V():
    def __init__(self, obj):
        self.obj = obj
MyManager.register('MyClass', MyClass)

def worker(obj):
    obj.set_value("1", 1)
    print(f"子进程值: {obj.get_value()}")

if __name__ == '__main__':
    # with MyManager() as manager:
    #     shared_obj = manager.MyClass()
    #     print(f"主进程值: {shared_obj.get_value()}")
    #     v = V(shared_obj)
    #     p = Process(target=worker, args=(shared_obj,))
    #     p.start()
    #     p.join()
    #     print(f"主进程值: {v.obj.get_value()}")
    path = r'D:\qmt\userdata_mini'  # QMT客户端路径
    
    acc_id = '8886660057'

    # 创建QMTTrader实例
    qmt_trader = QMTTrader(path, acc_id)

    print("download")
    xtdata.download_history_data('603496.SH', '1d', start_time='', end_time='20250211')

    # 买入股票
    order_id = qmt_trader.buy_quickly('603496.SH', 1000, sync=False)
    print(f"买入委托ID: {order_id}")

    

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

    qmt_trader.set_running()
