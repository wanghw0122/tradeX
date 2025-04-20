from common import constants
from sqlite_processor.mysqlite import SQLiteManager
import threading
import queue
from date_utils import date
import datetime
from logger import strategy_logger as logger

def calculate_seconds_difference(specified_time):
    current_time = datetime.datetime.now().timestamp()
    time_difference =  current_time - (specified_time / 1000)
    return time_difference


monitor_table = 'monitor_data'
monitor_config_table = "strategy_monitor_config"

class StockMonitor(object):
    def __init__(self, stock_code, stock_name, qmt_trader):
        # self.config = {}
        self.monitor_configs = {}
        # self.config['step_tick_gap'] = 5
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.qmt_trader = qmt_trader
        self.open_status = -1
        # 均价
        self.avg_price = 0
        # 当前价
        self.current_price = 0
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
        # 当天涨停价
        self.limit_up_price = -1
        # 当天跌停价
        self.limit_down_price = -1

        self.limit_up_tick_times = -1
        # 已经卖出rowid
        self.selled_row_ids = []
        # 准备卖出的rowid
        self.to_sell_row_ids = []
        # 剩余未卖出
        self.left_row_ids = []

        self.bq = queue.Queue()
        self.row_id_to_monitor_data = {}

        self.monitor_type_to_row_ids = {}

        self.running_monitor_status = {}
        self.running_monitor_stock_status = {}

        self.running_monitor_down_status = {}

        self.running_monitor_observe_steps = {}

        with SQLiteManager(constants.db_path) as db:
            self.query_data_lists = db.query_data_dict(monitor_table, condition_dict= {'date_key': date.get_current_date(), 'stock_code': stock_code, 'monitor_status': 1})
            if not self.query_data_lists:
                logger.error(f"query_data_lists null. {stock_code}-{stock_name}")
            for query_data in self.query_data_lists:
                row_id = query_data['id']
                strategy_name = query_data['strategy_name']
                sub_strategy_name = query_data['sub_strategy_name']
                if row_id not in self.left_row_ids:
                    self.left_row_ids.append(row_id)
                if strategy_name not in self.running_monitor_status:
                    self.running_monitor_status[strategy_name] = constants.StockStatus.COLD_START
                if strategy_name not in self.running_monitor_stock_status:
                    self.running_monitor_stock_status[strategy_name] = constants.StockStatus.UNKNOWN
                if strategy_name not in self.running_monitor_observe_steps:
                    self.running_monitor_observe_steps[strategy_name] = 0
                if strategy_name not in self.running_monitor_down_status:
                    self.running_monitor_down_status[strategy_name] = False
                self.row_id_to_monitor_data[row_id] = query_data
                monitor_type = query_data['monitor_type']
                monitor_config = db.query_data_dict(monitor_config_table, condition_dict= {'strategy_name': strategy_name})
                if not monitor_config:
                    logger.error(f"monitor_config null. {strategy_name}")
                    continue
                monitor_config = monitor_config[0]
                self.monitor_configs[strategy_name] = monitor_config
                # if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                #     pass
                if monitor_type not in self.monitor_type_to_row_ids:
                    self.monitor_type_to_row_ids[monitor_type] = [row_id]
                else:
                    self.monitor_type_to_row_ids[monitor_type].append(row_id)
        
        self.start_monitor()
        

        # self.config = config
        # self.db_name = config['db_name']
        # self.table_name = config['table_name']
    def start_monitor(self):
        logger.info(f"start monitor {self.stock_code} {self.stock_name}")
        self.thread = threading.Thread(target=self.monitor)
        self.thread.start()
        return self.thread
    

    def stop_monitor(self):
        logger.info(f"stop monitor {self.stock_code} {self.stock_name}")
        self.thread.join()
    
    def monitor(self):
        while True:
            if not self.left_row_ids:
                logger.error(f"{self.stock_code}-{self.stock_name} 没有需要监控的卖出任务")
                break
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
                self.open_status = constants.OpenStatus.DOWN_OPEN if open < lastClose else constants.OpenStatus.UP_OPEN if open > lastClose else constants.OpenStatus.FLAT_OPEN
            if amount <= 0 or volume <= 0:
                logger.error(f"amount <= 0. {amount} {time} {self.stock_code} {self.stock_name}")
                continue
            if lastPrice <= 0:
                logger.error(f"lastPrice <= 0. {lastPrice} {time} {self.stock_code} {self.stock_name}")
                continue
            
            # 均价
            self.avg_price = amount / volume / 100
            # 当前价
            self.current_price = lastPrice
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

            if self.limit_up_price < 0 or self.limit_down_price < 0:
                limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price)
                self.limit_up_price = limit_up_price_0
                self.limit_down_price = limit_down_price_0

            if self.limit_up_price > 0 and abs(self.current_price - self.limit_up_price) < 0.01:
                if self.limit_up_status:
                    self.limit_up_tick_times = self.limit_up_tick_times + 1
                    if self.limit_up_tick_times > 10:
                        if not bidPrice or not bidVol:
                            self.sell_all(price = self.current_price)
                            continue
                        buy1_price = bidPrice[0]
                        buy1_vol = bidVol[0]
                        if abs(buy1_price - self.limit_up_price) >= 0.01:
                            self.sell_all(price = buy1_price)
                            continue
                        # 封单金额过小 卖
                        if buy1_price * buy1_vol * 100 < 8000000:
                            self.sell_all(price = buy1_price)
                            continue
                else:
                    self.limit_up_tick_times = 0
                    self.limit_up_status = True
            elif self.limit_up_price > 0 and abs(self.current_price - self.limit_up_price) >= 0.01:
                self.limit_up_tick_times = -1
                if self.limit_up_status:
                    # 涨停炸板卖
                    if not bidPrice or not bidVol:
                        self.sell_all(price = self.current_price)
                    else:
                        self.sell_all(price = bidPrice[0])
                    self.limit_up_status = False
                    continue
                self.limit_up_status = False

            if self.limit_down_price > 0 and abs(self.current_price - self.limit_down_price) < 0.01:
                self.limit_down_status = True
            else:
                self.limit_down_status = False
            
            if self.limit_up_status:
                continue

            current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
            
            for monitor_type, row_ids in self.monitor_type_to_row_ids.items():
                if not row_ids:
                    continue
                if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']
                        monitor_config = self.monitor_configs[strategy_name]
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        cold_start_steps = monitor_config['cold_start_steps']
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        stop_profit_open_hc_pct = monitor_config['stop_profit_open_hc_pct']
                        stop_profit_pct = monitor_config['stop_profit_pct']
                        dynamic_hc_stop_profit_thres = monitor_config['dynamic_hc_stop_profit_thres']
                        static_hc_stop_profit_pct = monitor_config['static_hc_stop_profit_pct']
                        last_close_price_hc_pct = monitor_config['last_close_price_hc_pct']
                        dynamic_zs_line = -1
                        static_zs_line = -1
                        if dynamic_hc_stop_profit_thres > 0:
                            dynamic_zs_line = (1 - ((10 - self.current_max_increase * 100) * dynamic_hc_stop_profit_thres) / 100) * self.current_max_price
                            dynamic_zs_line = max(dynamic_zs_line, limit_down_price)
                            dynamic_zs_line = min(dynamic_zs_line, limit_up_price)
                            if abs(dynamic_zs_line - self.current_max_increase) < 0.01:
                                dynamic_zs_line = self.current_max_increase - 0.01
                            
                        if static_hc_stop_profit_pct > 0 and static_hc_stop_profit_pct < 1:
                            static_zs_line = self.current_max_price * (1 - static_hc_stop_profit_pct)

                        logger.info(f"dynamic_or_static_zs_line: {dynamic_zs_line} {static_zs_line} {self.current_max_increase} {self.current_max_price} {self.current_price}")

                        open_hc_line = self.open_price * (1 + stop_profit_open_hc_pct)
                        stop_profit_line = trade_price * (1 + stop_profit_pct)

                        zs_line = max(open_hc_line, stop_profit_line, limit_down_price)

                        if self.current_tick_steps < cold_start_steps:
                            continue
                        elif self.current_tick_steps == cold_start_steps:
                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                
                            elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                            
                            if self.current_price <= self.avg_price:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                            else:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                            
                            self.running_monitor_down_status[strategy_name] = False
                            self.running_monitor_observe_steps[strategy_name] = 0

                        elif self.current_tick_steps > cold_start_steps:
                            if self.current_tick_steps % per_step_tick_gap == 0:
                                if self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_LOW_AVG_DOWN:
                                    if abs(self.current_price - zs_line) < 0.01:
                                        logger.info(f"stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                        self.add_to_sell(row_id=row_id)
                                        continue
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if abs(self.current_price - zs_line) < 0.01:
                                            logger.info(f"stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price:
                                            if self.current_tick_steps >= max_abserve_tick_steps:
                                                logger.info(f"max abserve sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if self.running_monitor_down_status[strategy_name]:
                                                self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                    logger.info(f"cross down sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            pass
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if abs(self.current_price - zs_line) < 0.01:
                                            logger.info(f"stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0

                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_HIGH_AVG_UP:
                                    if abs(self.current_price - zs_line) < 0.01:
                                        logger.info(f"stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                        self.add_to_sell(row_id=row_id)
                                        continue
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <= self.avg_price:
                                            if self.current_tick_steps >= max_abserve_tick_steps:
                                                logger.info(f"max abserve sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if self.running_monitor_down_status[strategy_name]:
                                                self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                    logger.info(f"cross down sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_LOW_AVG_DOWN:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"max abserve sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                                if self.running_monitor_down_status[strategy_name]:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"cross down sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_price <= self.open_price:
                                                    logger.info(f"down open price sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_HIGH_AVG_UP:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"max abserve sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                                if self.running_monitor_down_status[strategy_name]:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"cross down sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_price <= self.open_price:
                                                    logger.info(f"down open price sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                            else:
                                # 获取当前时间
                                now = datetime.datetime.now().time()
                                # 定义目标时间
                                target_time = datetime.time(11, 25)
                                if now > target_time:
                                    self.add_to_sell(row_id=row_id)
                    
                elif monitor_type == constants.STOP_LOSS_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']
                        monitor_config = self.monitor_configs[strategy_name]
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        cold_start_steps = monitor_config['cold_start_steps']
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        
                        dynamic_hc_stop_profit_thres = monitor_config['dynamic_hc_stop_profit_thres']
                        static_hc_stop_profit_pct = monitor_config['static_hc_stop_profit_pct']
                        last_close_price_hc_pct = monitor_config['last_close_price_hc_pct']
                        dynamic_zs_line = -1
                        static_zs_line = -1
                        if dynamic_hc_stop_profit_thres > 0:
                            dynamic_zs_line = (1 - ((10 - self.current_max_increase * 100) * dynamic_hc_stop_profit_thres) / 100) * self.current_max_price
                            dynamic_zs_line = max(dynamic_zs_line, limit_down_price)
                            dynamic_zs_line = min(dynamic_zs_line, limit_up_price)
                            if abs(dynamic_zs_line - self.current_max_increase) < 0.01:
                                dynamic_zs_line = self.current_max_increase - 0.01
                            
                        if static_hc_stop_profit_pct > 0 and static_hc_stop_profit_pct < 1:
                            static_zs_line = self.current_max_price * (1 - static_hc_stop_profit_pct)

                        logger.info(f"dynamic_or_static_zs_line: {dynamic_zs_line} {static_zs_line} {self.current_max_increase} {self.current_max_price} {self.current_price}")

                        if self.current_tick_steps < cold_start_steps:
                            continue
                        elif self.current_tick_steps == cold_start_steps:
                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                
                            elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                            
                            if self.current_price <= self.avg_price:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                            else:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                            
                            if self.current_price <= self.open_price:
                                # 直接割
                                logger.info(f"stop loss sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                self.add_to_sell(row_id=row_id)
                                continue

                            self.running_monitor_down_status[strategy_name] = False
                            self.running_monitor_observe_steps[strategy_name] = 0

                        elif self.current_tick_steps > cold_start_steps:
                            if self.current_tick_steps % per_step_tick_gap == 0:
                                if self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_LOW_AVG_DOWN:
                                    if self.current_price <= self.open_price:
                                        # 直接割
                                        logger.info(f"stop loss sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                        self.add_to_sell(row_id=row_id)
                                        continue
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0

                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_HIGH_AVG_UP:
                                    if self.current_price <= self.open_price:
                                        # 直接割
                                        logger.info(f"stop loss sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                        self.add_to_sell(row_id=row_id)
                                        continue
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <= self.avg_price:
                                            if self.current_tick_steps >= max_abserve_tick_steps:
                                                logger.info(f"max abserve sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if self.running_monitor_down_status[strategy_name]:
                                                self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                    logger.info(f"cross down sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP

                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_LOW_AVG_DOWN:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"max abserve sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                                if self.running_monitor_down_status[strategy_name]:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"cross down sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_price <= self.open_price:
                                                    logger.info(f"down open price sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_HIGH_AVG_UP:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"down close sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"max abserve sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                                if self.running_monitor_down_status[strategy_name]:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"cross down sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_price <= self.open_price:
                                                    logger.info(f"down open price sell. {self.stock_code} {self.stock_name} {strategy_name} {zs_line} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                            else:
                                # 获取当前时间
                                now = datetime.datetime.now().time()
                                # 定义目标时间
                                target_time = datetime.time(11, 25)
                                if now > target_time:
                                    self.add_to_sell(row_id=row_id)
                                pass
                elif monitor_type ==  constants.LAST_TRADE_DAY_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']
                        monitor_config = self.monitor_configs[strategy_name]
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        cold_start_steps = monitor_config['cold_start_steps']
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        last_day_sell_thres = monitor_config['monitor_config']
                        max_thres_line = self.current_max_price * (1 - 0.005)
                        if self.current_increase > last_day_sell_thres and self.current_price < max_thres_line:
                            self.add_to_sell(row_id=row_id)
                            continue
                        # 获取当前时间
                        now = datetime.datetime.now().time()
                        # 定义目标时间
                        target_time = datetime.time(11, 25)
                        if now > target_time:
                            self.add_to_sell(row_id=row_id)
                            
            if not bidPrice or not bidVol:
                self.sell_all_row_ids(price = self.current_price)
            else:
                self.sell_all_row_ids(price = bidPrice[0])


    def consume(self, data):
        logger.info(f"{self.stock_code} {self.stock_name} 监控器接收到数据 {data}")
        self.bq.put(data)

    def sell(self, price, volume):
        pass

    def add_to_sell(self, row_id):
        if row_id not in self.to_sell_row_ids:
            self.to_sell_row_ids.append(row_id)


    def sell_all_row_ids(self, price):
        all_volume = 0
        extra_infos = []
        for row_id in self.to_sell_row_ids:
            if row_id in self.left_row_ids:
                self.left_row_ids.remove(row_id)
            if row_id not in self.row_id_to_monitor_data:
                continue
            data_dict = self.row_id_to_monitor_data[row_id]
            strategy_name = data_dict['strategy_name']
            trade_price = data_dict['trade_price']
            limit_down_price = data_dict['limit_down_price']
            limit_up_price = data_dict['limit_up_price']
            left_volume = data_dict['left_volume']
            origin_row_id = data_dict['origin_row_id']
            current_trade_days = data_dict['current_trade_days']
            monitor_type = data_dict['monitor_type']
            if left_volume <= 0:
                continue
            if row_id in self.selled_row_ids:
                continue
            all_volume = all_volume + left_volume
            self.selled_row_ids.append(row_id)
            extra_infos.append((self.stock_code, left_volume, trade_price, origin_row_id, strategy_name, current_trade_days,'max_days', left_volume))
        self.to_sell_row_ids.clear()
        if all_volume > 0:
            self.qmt_trader.sell_quickly(self.stock_code, self.stock_name, all_volume, order_remark= "sell_all",  buffer=0, extra_infos = extra_infos, up_sell=True, s_price = price)


    def sell_all(self, price):
        all_volume = 0
        extra_infos = []
        for row_id, data_dict in self.row_id_to_monitor_data.items():
            if row_id in self.left_row_ids:
                self.left_row_ids.remove(row_id)
            strategy_name = data_dict['strategy_name']
            trade_price = data_dict['trade_price']
            limit_down_price = data_dict['limit_down_price']
            limit_up_price = data_dict['limit_up_price']
            left_volume = data_dict['left_volume']
            origin_row_id = data_dict['origin_row_id']
            current_trade_days = data_dict['current_trade_days']
            monitor_type = data_dict['monitor_type']
            if left_volume <= 0:
                continue
            if row_id in self.selled_row_ids:
                continue
            all_volume = all_volume + left_volume
            self.selled_row_ids.append(row_id)
            extra_infos.append((self.stock_code, left_volume, trade_price, origin_row_id, strategy_name, current_trade_days,'max_days', left_volume))
        if all_volume > 0:
            self.qmt_trader.sell_quickly(self.stock_code, self.stock_name, all_volume, order_remark= "sell_all",  buffer=0, extra_infos = extra_infos, up_sell=True, s_price = price)


        # (stock_code, left_volume, trade_price, row_id, strategy_name, trade_day, reason, all_volume)