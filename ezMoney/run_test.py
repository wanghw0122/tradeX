from trade.qmtTrade import *
from sqlite_processor.mysqlite import *
import multiprocessing
from multiprocessing import Queue
q = Queue()
from date_utils import *
from data_class.xiao_cao_environment_second_line_v2 import *

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

    x,y = build_xiaocao_mod_dict_all()
    print(x)
    print(y)
    
    # with SQLiteManager(db_name) as manager:
    #     manager.insert_data("strategy_budget",{'strategy_name':'追涨-中位小高开起爆',
    #                                       'budget':30000,
    #                                       'origin_budget': 30000})

        # manager.update_data("strategy_budget",{
        #                                   'origin_budget': 30000,
        #                                   'budget': 30000}, {'strategy_name':'低吸-绿盘低吸'})
        # manager.update_budget("xiao_cao_1j2db",10000)
       