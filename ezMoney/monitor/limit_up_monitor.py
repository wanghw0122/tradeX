from common import constants
from sqlite_processor.mysqlite import SQLiteManager
import threading
import queue
from date_utils import date
import datetime
from logger import strategy_logger as logger
import time
from xtquant import xtconstant
import traceback

def calculate_seconds_difference(specified_time):
    current_time = datetime.datetime.now().timestamp()
    time_difference =  current_time - (specified_time / 1000)
    return time_difference


monitor_table = 'limit_up_strategy_info'


from collections import deque

class SmoothFilter:
    def __init__(self, window_size=10):
        self.window = deque(maxlen=window_size)  # 滑动窗口
        self.smoothed_value = 0
        
    def update(self, new_value):
        self.window.append(new_value)
        self.smoothed_value = sum(self.window)/len(self.window)
        return self.smoothed_value



def is_before_1000():
    now = datetime.datetime.now()
    target_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
    return now < target_time

def is_before_1030():
    now = datetime.datetime.now()
    target_time = now.replace(hour=10, minute=30, second=0, microsecond=0)
    return now < target_time

def is_before_1200():
    now = datetime.datetime.now()
    target_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
    return now < target_time

class LimitUpStockMonitor(object):
    def __init__(self, stock_code, stock_name, row_ids = [], qmt_trader = None):
        # self.config = {}
        self.monitor_configs = {}
        # self.config['step_tick_gap'] = 5
        self.stock_code = stock_code
        self.stock_name = stock_name
        if qmt_trader != None:
            self.qmt_trader = qmt_trader
        self.open_status = -1
        self.end = False
        # 均价
        self.avg_price = 0
        # 当前价
        self.current_price = 0
        # 平滑当前价
        self.smooth_current_price = 0
        # 平滑过滤器
        self.smooth_price_filter = SmoothFilter(window_size=2)
        self.limited_up_history = []
        self.limit_up_before = False
        # 涨停最大封单量
        self.max_limit_up_vol = -1
        # 开盘价
        self.open_price = 0
        # 昨天收盘价
        self.last_close_price = 0
        # 当前步数
        self.current_tick_steps = -1
        # 当前天内涨幅
        self.current_open_increase = 0
        # 当天涨幅
        self.current_increase = 0
        # 当天最高价
        self.current_max_price = 0
        # 当天最低价
        self.current_min_price = 0
        # 当天天内最高涨幅
        self.current_max_open_increase = -1
        # 当天天内最低涨幅
        self.current_min_open_increase = -1
        # 当天最高涨幅
        self.current_max_increase = -1
        # 当天最低涨幅
        self.current_min_increase = -1
        # 涨停标记
        self.limit_up_status = False
        # 跌停标记
        self.limit_down_status = False

        self.limited_up = False
        # 当天涨停价
        self.limit_up_price = -1
        # 当天跌停价
        self.limit_down_price = -1

        self.limit_up_tick_times = -1

        self.one_minute_up_speed = -1
        self.half_minute_up_speed = -1
        self.one_minute_increase = 0

        self.limit_up_stock_status = constants.LimitUpStockStatus.UNKNOWN
        # 价格列表
        self.price_list = []
        self.smooth_price_list = []
        self.avg_price_list = []
        self.increase_list = []

        self.limit_up_stock_status_list = []

        self.order_id_to_row_ids = {}
        self.row_id_to_order_ids = {}

        self.row_id_status = {}
        self.row_ids = []
        self.row_ids.extend(row_ids)

        self.bq = queue.Queue()
        self.row_id_to_monitor_data = {}

        self.limit_up_str_type = '00000000000'
        self.order_id_miss_times = {}


        with SQLiteManager(constants.db_path) as db:
            if row_ids:
                for row_id in row_ids:
                    query_data_lists = db.query_data_dict(monitor_table, condition_dict= {'id': row_id})
                    if not query_data_lists:
                        logger.error(f"query_data_lists null. {stock_code}-{stock_name}")
                        continue
                    for query_data in query_data_lists:
                        row_id = query_data['id']
                        strategy_name = query_data['strategy_name']
                        sub_strategy_name = query_data['sub_strategy_name']
                        c_status = query_data['c_status']
                        q_order_ids = query_data['order_ids']
                        if c_status == 1 and q_order_ids:
                            for oid in q_order_ids.split(','):
                                ioid = int(oid)
                                if ioid in self.order_id_to_row_ids:
                                    self.order_id_to_row_ids[ioid].append(row_id)
                                else:
                                    self.order_id_to_row_ids[ioid] = [row_id]
                        self.row_id_status[row_id] = constants.get_row_id_status(c_status)

                        self.row_id_to_monitor_data[row_id] = query_data
        # 打印日志
        logger.info(f"队列 bq 当前大小: {self.bq.qsize()}")
        logger.info(f"row_id 到监控数据的映射: {self.row_id_to_monitor_data}")

        self.start_monitor()
        self.monitor_orders_running = False
        self.monitor_orders_thread = None
        self.start_monitor_orders()
    
    def update_limit_up_str_type(self, touched = False, has_op = False, limited = True):
        if limited:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 0, '1')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 0, '0')
        if is_before_1200():
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 1, '1')
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 2, '0')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 1, '0')
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 2, '1')
        if self.current_increase > 0.0985 and self.one_minute_increase > 0.008:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 3, '1')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 3, '0')
        if not has_op:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 4, '1')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 4, '0')
        if self.limit_up_before and self.one_minute_increase > 0.008:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 5, '1')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 5, '0')

        if is_before_1000():
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 8, '1')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 8, '0')

        if is_before_1030():
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 9, '1')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 9, '0')

        if touched:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 10, '1')
        else:
            self.limit_up_str_type = constants.modify_string_slice(self.limit_up_str_type, 10, '0')
        logger.info(f"[打板]update_limit_up_str_type {self.limit_up_str_type} {self.stock_code} {self.stock_name}")


    def max_increase_one_minute(self):
        if not self.increase_list:
            self.one_minute_increase = 0
            return
        min_increase = self.increase_list[0]
        if len(self.increase_list) < 20:
            min_increase = min(self.increase_list)
        else:
            min_increase = min(self.increase_list[-20:])

        self.one_minute_increase = self.current_increase - min_increase

    def start_monitor(self):
        logger.info(f"start limit up monitor {self.stock_code} {self.stock_name}")
        self.thread = threading.Thread(target=self.monitor)
        self.thread.setDaemon(True)
        self.thread.start()
        return self.thread
    

    def stop_monitor(self):
        logger.info(f"stop monitor {self.stock_code} {self.stock_name}")
        self.thread.join()

    def add_monitor_data(self, row_ids):
        logger.info(f"[打板]开始执行 add_monitor_data 方法，传入的 row_ids: {row_ids}")
        with SQLiteManager(constants.db_path) as db:
            if row_ids:
                for row_id in row_ids:
                    logger.info(f"[打板]开始查询 row_id 为 {row_id} 的数据")
                    query_data_lists = db.query_data_dict(monitor_table, condition_dict= {'id': row_id})
                    if not query_data_lists:
                        logger.error(f"[打板]query_data_lists null. {self.stock_code}-{self.stock_name}，row_id: {row_id}")
                        continue
                    logger.info(f"[打板]成功查询到 row_id 为 {row_id} 的数据，数据数量: {len(query_data_lists)}")
                    for query_data in query_data_lists:
                        row_id = query_data['id']
                        strategy_name = query_data['strategy_name']
                        sub_strategy_name = query_data['sub_strategy_name']
                        c_status = query_data['c_status']
                        q_order_ids = query_data['order_ids']
                        logger.info(f"[打板]处理 row_id 为 {row_id} 的数据，strategy_name: {strategy_name}，sub_strategy_name: {sub_strategy_name}，c_status: {c_status}，q_order_ids: {q_order_ids}")
                        if c_status == 1 and q_order_ids:
                            for oid in q_order_ids.split(','):
                                ioid = int(oid)
                                if ioid in self.order_id_to_row_ids:
                                    self.order_id_to_row_ids[ioid].append(row_id)
                                    logger.info(f"[打板]order_id {ioid} 已存在，将 row_id {row_id} 添加到对应的列表中")
                                else:
                                    self.order_id_to_row_ids[ioid] = [row_id]
                                    logger.info(f"[打板]order_id {ioid} 不存在，创建新列表并添加 row_id {row_id}")
                        self.row_id_status[row_id] = constants.get_row_id_status(c_status)
                        logger.info(f"[打板]更新 row_id {row_id} 的状态为 {self.row_id_status[row_id]}")

                        self.row_id_to_monitor_data[row_id] = query_data
                        logger.info(f"[打板]更新后 {self.row_id_to_monitor_data} 的数据")
                        logger.info(f"[打板]更新 row_id {row_id} 的监控数据")
            else:
                logger.info("[打板]传入的 row_ids 为空，不执行查询操作")
        logger.info("[打板]add_monitor_data 方法执行结束")


    def send_orders(self):
        mdata = self.row_id_to_monitor_data.copy()
        match_datas = []
        fnally_match_datas = []
        total_budgets = 0
        for row_id, data in mdata.items():
            if row_id in self.row_id_status:
                r_status = self.row_id_status[row_id]
                if r_status == constants.RowIdStatus.UNPROCESSED or r_status == constants.RowIdStatus.CANCELLED:
                    match_datas.append(data)
            else:
                match_datas.append(data)
                self.row_id_status[row_id] = constants.RowIdStatus.UNPROCESSED
        if not match_datas:
            return
        for data in match_datas:
            row_id = data['id']
            strategy_name = data['strategy_name']
            sub_strategy_name = data['sub_strategy_name']
            hit_type = data['hit_type']
            hit_types = []
            if ',' in hit_type:
                hit_types.extend(hit_type.split(','))
            else:
                hit_types.append(hit_type)

            matched = constants.match_binary_string(self.limit_up_str_type, hit_types)
            if matched:
                fnally_match_datas.append(data)
        if not fnally_match_datas:
            return
        for data in fnally_match_datas:
            row_id = data['id']
            strategy_name = data['strategy_name']
            sub_strategy_name = data['sub_strategy_name']
            budget = data['budget']
            total_budgets = total_budgets + budget
        
        if total_budgets <= 0:
            return
        total_budgets = min(total_budgets, 5000)
        order_pirce = self.limit_up_price
        if order_pirce <= 0:
            order_pirce = self.current_price
        order_volume = total_budgets / order_pirce // 100
        order_volume = int(order_volume)
        if order_volume <= 0:
            return
        order_id = self.qmt_trader.buy_immediate(self.stock_code, order_volume * 100, order_pirce)
        if order_id > 0:
            logger.info(f"[打板]成功下单购买股票，股票代码: {self.stock_code}, 股票名称: {self.stock_name}, 下单价格: {order_pirce:.2f}, 下单数量: {order_volume * 100}, 订单 ID: {order_id}")
            for data in fnally_match_datas:
                row_id = data['id']
                self.row_id_status[row_id] = constants.RowIdStatus.PLACED
                if row_id in self.row_id_to_order_ids:
                    self.row_id_to_order_ids[row_id].append(order_id)
                else:
                    self.row_id_to_order_ids[row_id] = [order_id]
                if order_id in self.order_id_to_row_ids:
                    self.order_id_to_row_ids[order_id].append(row_id)
                else:
                    self.order_id_to_row_ids[order_id] = [row_id]


    def start_monitor_orders(self):
        logger.info(f"start limit up orders monitor {self.stock_code} {self.stock_name}")
        if not self.monitor_orders_running:
            self.monitor_orders_running = True
            self.monitor_orders_thread = threading.Thread(target=self._monitor_orders_loop)
            self.monitor_orders_thread.setDaemon(True)
            self.monitor_orders_thread.start()

    def stop_monitor_orders(self):
        if self.monitor_orders_running:
            self.monitor_orders_running = False
            if self.monitor_orders_thread:
                self.monitor_orders_thread.join()

    def _monitor_orders_loop(self):
        while self.monitor_orders_running:
            self._monitor_orders()
            time.sleep(3)

    def _monitor_orders(self):
        if not hasattr(self, 'qmt_trader') or self.qmt_trader is None:
            logger.error("qmt_trader 未初始化，无法查询订单状态")
            return
        
        order_id_list = list(self.order_id_to_row_ids.keys())
        if not order_id_list:
            # logger.error(f"查询不到订单继续loop. {self.stock_code} - {self.stock_name}")
            return
        else:
            logger.info(f"查询到订单继续loop. {self.stock_code} - {self.stock_name} - {order_id_list} - {self.order_id_to_row_ids}")


        order_infos = self.qmt_trader.get_all_orders(filter_order_ids = order_id_list)
        if order_infos:
            logger.info(f"查询到订单信息. {self.stock_code} - {self.stock_name} - {order_infos}")
        else:
            logger.error(f"查询不到订单信息. {self.stock_code} - {self.stock_name} - {order_id_list}")

        for order_id in order_id_list:
            if order_id not in order_infos:
                if order_id in self.order_id_miss_times:
                    self.order_id_miss_times[order_id] = self.order_id_miss_times[order_id] + 1
                    if self.order_id_miss_times[order_id] > 120 and order_id in self.order_id_to_row_ids:
                        logger.error(f"订单超时未成交 删除记录. {self.stock_code} - {self.stock_name} - {order_id}")
                        del self.order_id_to_row_ids[order_id]
                else:
                    self.order_id_miss_times[order_id] = 1
        
        for order_id, info in order_infos.items():
            try:
                order_status = info['order_status']
                if order_status == xtconstant.ORDER_SUCCEEDED:
                    new_status = constants.RowIdStatus.BOUGHT
                elif order_status == xtconstant.ORDER_JUNK or order_status == xtconstant.ORDER_CANCELED or order_status == xtconstant.ORDER_PART_CANCEL:
                    new_status = constants.RowIdStatus.CANCELLED
                else:
                    new_status = constants.RowIdStatus.PLACED
                row_ids = self.order_id_to_row_ids[order_id]
                with SQLiteManager(constants.db_path) as db:
                    for row_id in row_ids:
                        if row_id in self.row_id_status:
                            self.row_id_status[row_id] = new_status
                            logger.info(f"更新 row_id {row_id} 的状态为 {new_status}")
                        else:
                            self.row_id_status[row_id] = new_status
                            logger.warning(f"row_id {row_id} 不在 row_id_status 中，无法更新状态")
                        
                        update_dict = {}
                        condition_dict = {'id': row_id}
                        if new_status ==  constants.RowIdStatus.BOUGHT:
                            update_dict['success'] = 1
                            update_dict['c_status'] = 2
                            update_dict['order_ids'] = str(order_id)
                        elif new_status == constants.RowIdStatus.CANCELLED or new_status == constants.RowIdStatus.UNPROCESSED:
                            update_dict['success'] = 0
                            update_dict['c_status'] = 0
                        elif new_status == constants.RowIdStatus.PLACED:
                            update_dict['success'] = 0
                            update_dict['c_status'] = 1
                            update_dict['order_ids'] = str(order_id)
                        
                        # 打印更新前的日志
                        logger.info(f"[打板]即将更新表 {monitor_table} 中 id 为 {row_id} 的记录，更新内容: {update_dict}")
                        db.update_data(monitor_table, update_dict=update_dict, condition_dict=condition_dict)
                        # 打印更新后的日志
                        logger.info(f"[打板]已成功更新表 {monitor_table} 中 id 为 {row_id} 的记录，更新内容: {update_dict}")
            except Exception as e:
                 logger.error(f"处理订单 {order_id} 时发生错误: {str(e)}")
        

    # ... 已有代码 ...
    
    def monitor(self):
        while True:
            try:
                data = self.bq.get()
                if data is None:
                    continue
                # m = {}
                time = data['time']
                diff = calculate_seconds_difference(time)
                if diff > 10:
                    logger.error(f"time diff > 10s. {diff} {time} {self.stock_code} {self.stock_name}")
                    continue

                lastPrice = data['lastPrice']
                open = data['open']
                high = data['high']
                low = data['low']
                lastClose = data['lastClose']
                volume = data['volume']
                amount = data['amount']
                pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
                askPrice = data['askPrice']
                bidPrice = data['bidPrice']
                askVol = data['askVol']
                bidVol = data['bidVol']
                if self.open_status == -1:
                    self.open_status = constants.OpenStatus.DOWN_OPEN if open <= lastClose else constants.OpenStatus.UP_OPEN
                if amount <= 0 or volume <= 0:
                    logger.error(f"amount <= 0. {amount} {time} {self.stock_code} {self.stock_name}")
                    continue
                if lastPrice <= 0:
                    logger.error(f"lastPrice <= 0. {lastPrice} {time} {self.stock_code} {self.stock_name}")
                    continue
                
                # 均价
                self.avg_price = amount / volume / 100
                self.avg_price_list.append(self.avg_price)
                # 当前价
                self.current_price = lastPrice
                self.price_list.append(self.current_price)
                self.smooth_current_price = self.smooth_price_filter.update(self.current_price)
                self.smooth_price_list.append(self.smooth_current_price)
                # 开盘价
                self.open_price = open
                # 昨天收盘价
                self.last_close_price = lastClose
                # 当前步数
                self.current_tick_steps = self.current_tick_steps + 1
                # 当前天内涨幅
                self.current_open_increase = (self.current_price - self.open_price) / self.open_price
                # 当天涨幅
                self.current_increase = (self.current_price - self.last_close_price) / self.last_close_price
                self.increase_list.append(self.current_increase)

                # 当天最高价
                self.current_max_price = max(self.current_max_price, high)
                # 当天最低价
                self.current_min_price = min(self.current_min_price, low)
                # 当天天内最高涨幅
                self.current_max_open_increase = (self.current_max_price - self.open_price) / self.open_price
                # 当天天内最低涨幅
                self.current_min_open_increase = (self.current_min_price - self.open_price) / self.open_price
                # 当天最高涨幅
                self.current_max_increase = (self.current_max_price - self.last_close_price) / self.last_close_price
                # 当天最低涨幅
                self.current_min_increase = (self.current_min_price - self.last_close_price) / self.last_close_price

                self.max_increase_one_minute()

                logger.info(
                    f"股票代码： {self.stock_code}, 股票名称： {self.stock_name}, "
                    f"均价: {self.avg_price:.2f}, 当前价: {self.current_price:.2f}, 开盘价: {self.open_price:.2f}, "
                    f"昨天收盘价: {self.last_close_price:.2f}, 当前步数: {self.current_tick_steps}, "
                    f"当前天内涨幅: {self.current_open_increase:.2%}, 当天涨幅: {self.current_increase:.2%}, "
                    f"当天最高价: {self.current_max_price:.2f}, 当天最低价: {self.current_min_price:.2f}, "
                    f"当天天内最高涨幅: {self.current_max_open_increase:.2%}, 当天天内最低涨幅: {self.current_min_open_increase:.2%}, "
                    f"当天最高涨幅: {self.current_max_increase:.2%}, 当天最低涨幅: {self.current_min_increase:.2%}"
                )

                if self.limit_up_price < 0 or self.limit_down_price < 0:
                    limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price, stock_code=self.stock_code)
                    self.limit_up_price = limit_up_price_0
                    self.limit_down_price = limit_down_price_0
                
                if abs(self.current_price - self.limit_up_price) < 0.01:
                    self.limited_up_history.append(1)
                else:
                    self.limited_up_history.append(0)

                self.limit_up_before = self.have_limited_up()

                if self.limit_up_stock_status == constants.LimitUpStockStatus.UNKNOWN:
                    
                    if abs(self.current_price - self.limit_up_price) < 0.01:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.LIMIT_UP
                        self.limited_up = True
                        if not askPrice or not askVol:
                            self.limit_up_stock_status = constants.LimitUpStockStatus.CLOSE_LIMIT_UP
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                    elif abs(self.current_price - self.limit_down_price) < 0.01:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.LIMIT_DOWN
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                    # if abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                    #     self.limit_up_stock_status = constants.LimitUpStockStatus.SMOOTH_LIMIT_UP
                    #     self.limit_up = True
                    #     if not askPrice or not askVol:
                    #         self.limit_up_stock_status = constants.LimitUpStockStatus.CLOSE_LIMIT_UP
                    # elif abs(self.smooth_current_price - self.limit_down_price) < 0.0033:
                    #     self.limit_up_stock_status = constants.LimitUpStockStatus.SMOOTH_LIMIT_DOWN
                    
                    if abs(self.current_price - self.limit_up_price) >= 0.01:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.UNLIMITED
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                    self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                    continue
                elif self.limit_up_stock_status == constants.LimitUpStockStatus.UNLIMITED:
                    if self.current_increase > 0.0985 and abs(self.current_price - self.limit_up_price) >= 0.01:
                        touched = False
                        if self.limit_up_stock_status_list and self.limit_up_stock_status_list[-1] == constants.LimitUpStockStatus.TOUCH_LIMIT_UP:
                            touched = True
                        self.update_limit_up_str_type(touched=touched, has_op=False, limited=False)
                        self.limited_up = False
                        self.send_orders()
                    # 未涨停到涨停 意味着首次涨停，判断是否有对手盘
                    if abs(self.current_price - self.limit_up_price) < 0.01 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.TOUCH_LIMIT_UP
                        touched = False
                        has_op = False
                        if not askPrice or not askVol:
                            has_op = False
                        else:
                            ask1_price = askPrice[0]
                            ask1_vol = askVol[0]
                            if ask1_price > 0 and ask1_vol > 0:
                                has_op = True
                        if self.limit_up_stock_status_list and self.limit_up_stock_status_list[-1] == constants.LimitUpStockStatus.TOUCH_LIMIT_UP:
                            touched = True
                        self.update_limit_up_str_type(touched=touched, has_op=has_op)
                        self.limited_up = True
                        self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志

                        self.send_orders()
                        continue
                    else:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.UNLIMITED
                        self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                        continue
                elif self.limit_up_stock_status == constants.LimitUpStockStatus.TOUCH_LIMIT_UP:
                    if self.current_increase > 0.0985 and abs(self.current_price - self.limit_up_price) >= 0.01:
                        touched = False
                        if self.limit_up_stock_status_list and self.limit_up_stock_status_list[-1] == constants.LimitUpStockStatus.TOUCH_LIMIT_UP:
                            touched = True
                        self.update_limit_up_str_type(touched=touched, has_op=False, limited=False)
                        self.limited_up = False
                        self.send_orders()

                    # 涨停到涨停
                    if abs(self.current_price - self.limit_up_price) < 0.01 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.LIMIT_UP
                        touched = True
                        has_op = False
                        if not askPrice or not askVol:
                            has_op = False
                        else:
                            ask1_price = askPrice[0]
                            ask1_vol = askVol[0]
                            if ask1_price > 0 and ask1_vol > 0:
                                has_op = True
                        if not has_op:
                            self.limit_up_stock_status = constants.LimitUpStockStatus.CLOSE_LIMIT_UP
                        self.update_limit_up_str_type(touched=touched, has_op=has_op)
                        self.limited_up = True
                        self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                        self.send_orders()
                        continue
                    else:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.UNLIMITED
                        self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                        continue
                elif self.limit_up_stock_status == constants.LimitUpStockStatus.LIMIT_UP:
                    if self.current_increase > 0.0985 and abs(self.current_price - self.limit_up_price) >= 0.01:
                        touched = False
                        if self.limit_up_stock_status_list and self.limit_up_stock_status_list[-1] == constants.LimitUpStockStatus.TOUCH_LIMIT_UP:
                            touched = True
                        self.update_limit_up_str_type(touched=touched, has_op=False, limited=False)
                        self.limited_up = False
                        self.send_orders()
                    # 涨停未封
                    if abs(self.current_price - self.limit_up_price) < 0.01 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.LIMIT_UP
                        touched = False
                        has_op = False
                        if not askPrice or not askVol:
                            has_op = False
                        else:
                            ask1_price = askPrice[0]
                            ask1_vol = askVol[0]
                            if ask1_price > 0 and ask1_vol > 0:
                                has_op = True
                        if not has_op:
                            self.limit_up_stock_status = constants.LimitUpStockStatus.CLOSE_LIMIT_UP
                            self.update_limit_up_str_type(touched=touched, has_op=has_op)
                            self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                            self.limited_up = True
                            self.send_orders()
                            logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                            continue
                        else:
                            self.limit_up_stock_status = constants.LimitUpStockStatus.LIMIT_UP
                            self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                            self.limited_up = True
                            logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                            continue
                    else:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.UNLIMITED
                        self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                        continue
                elif self.limit_up_stock_status == constants.LimitUpStockStatus.CLOSE_LIMIT_UP:
                    if self.current_increase > 0.0985 and abs(self.current_price - self.limit_up_price) >= 0.01:
                        touched = False
                        if self.limit_up_stock_status_list and self.limit_up_stock_status_list[-1] == constants.LimitUpStockStatus.TOUCH_LIMIT_UP:
                            touched = True
                        self.update_limit_up_str_type(touched=touched, has_op=False, limited=False)
                        self.limited_up = False
                        self.send_orders()
                    # 涨停封
                    if abs(self.current_price - self.limit_up_price) < 0.01 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.LIMIT_UP
                        touched = False
                        has_op = False
                        if not askPrice or not askVol:
                            has_op = False
                        else:
                            ask1_price = askPrice[0]
                            ask1_vol = askVol[0]
                            if ask1_price > 0 and ask1_vol > 0:
                                has_op = True
                        if not has_op:
                            self.limit_up_stock_status = constants.LimitUpStockStatus.CLOSE_LIMIT_UP
                        self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                        self.limited_up = True
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                        continue
                    else:
                        self.limit_up_stock_status = constants.LimitUpStockStatus.UNLIMITED
                        self.limit_up_stock_status_list.append(self.limit_up_stock_status)
                        logger.info(f"股票状态更新为: {self.limit_up_stock_status}")  # 添加核心日志
                        continue
            except Exception as e:
                stack_trace = traceback.format_exc()
                logger.error(f"发生异常: {str(e)}\n堆栈信息:\n{stack_trace}")
                logger.error(f"Error processing data: {e}")

    def consume(self, data):
        if self.end:
            return
        logger.info(f"{self.stock_code} {self.stock_name} 监控器接收到数据 {data}")
        self.bq.put(data)


    def have_limited_up(self):
        sum_value = sum(self.limited_up_history[:-10]) if len(self.limited_up_history) > 10 else 0
        return sum_value > 2
