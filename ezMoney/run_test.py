from multiprocessing import Process
from multiprocessing.managers import BaseManager
from trade.qmtTrade import *
from sqlite_processor.mysqlite import *

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
    
    create_strategy_table("202502")
    # with SQLiteManager(db_name) as manager:
    #    manager.insert_data("strategy_data_premarket_202502", insert_dict)

    # with SQLiteManager(db_name) as manager:
    #    manager.update_data("strategy_data_premarket_202502", update_dict, condition_dict)
    # with SQLiteManager(db_name) as manager:
    #    manager.delete_data("strategy_data_premarket_202502", delete_dict)
    insert_list = [
        {"date_key": "20250209", "strategy_name": "SampleStrategy", "sub_strategy_name": "SubSample", "stock_code": "600004", "stock_name": "SampleStock"},
        {"date_key": "20250209", "strategy_name": "SampleStrategy", "sub_strategy_name": "SubSample", "stock_code": "600002", "stock_name": "SampleStock2"},
        {"date_key": "20250210", "strategy_name": "SampleStrategy", "sub_strategy_name": "SubSample", "stock_code": "600003", "stock_name": "SampleStock3"}
    ]

    delete_list = [
        {"date_key": "20250209", "strategy_name": "SampleStrategy", "sub_strategy_name": "SubSample", "stock_code": "600004", "stock_name": "SampleStock"},
        {"date_key": "20250209", "strategy_name": "SampleStrategy", "sub_strategy_name": "SubSample", "stock_code": "600002", "stock_name": "SampleStock2"},
        {"date_key": "20250210", "strategy_name": "SampleStrategy", "sub_strategy_name": "SubSample", "stock_code": "600003", "stock_name": "SampleStock3"}
    ]


    with SQLiteManager(db_name) as manager:
        manager.batch_delete_data("strategy_data_premarket_202502", delete_list)

