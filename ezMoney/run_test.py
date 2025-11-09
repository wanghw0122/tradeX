from trade.qmtTrade import *
from sqlite_processor.mysqlite import *
import multiprocessing
from multiprocessing import Queue
q = Queue()
from date_utils import *
from data_class.xiao_cao_environment_second_line_v2 import *
from http_request import build_http_request

from common import factors

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

    # print(factors.get_n_days_data_batch(['603131.SH', '002054.SZ'], '2025-06-08', 7))
    print(build_http_request.check_user_alive())
    print(build_http_request.get_teacher_stock(tradeDate="2025-08-27"))
    # x =  build_http_request.sort_v2(40, date="2025-08-27")
    # print(','.join(x))

    # print(build_http_request.get_code_by_xiao_cao_block(tradeDate="2025-08-27", exponentCodeList = ['9G0127']))

    # print(build_http_request.system_time())
    
    # with SQLiteManager(db_name) as manager:
    #    print(manager.query_limit_up_records_by_date('2025-06-08'))
        # manager.insert_data("strategy_budget",{'strategy_name':'追涨-中位小高开起爆',
        #                                   'budget':30000,
        #                                   'origin_budget': 30000})

        # manager.update_data("strategy_budget",{
        #                                   'origin_budget': 30000,
        #                                   'budget': 30000}, {'strategy_name':'低吸-绿盘低吸'})
        # manager.update_budget("xiao_cao_1j2db",10000)
    