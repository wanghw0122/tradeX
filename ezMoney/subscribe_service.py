from multiprocessing import Process, Queue, get_context
import threading
import time
import datetime
from typing import Dict, List, Callable, Any, Set
from enum import Enum
import queue
from logger import logger

# 定义订阅任务类型
class SubscriptionTaskType(Enum):
    TICK_DATA = "tick_data"  # 实时行情数据订阅
    MIN_COST_MONITOR = "min_cost_monitor"  # 最低成本监控订阅
    MORNING_MONITOR = "morning_monitor"  # 早盘监控订阅

class UnifiedSubscriptionService:
    def __init__(self, selected_port: int):
        self.selected_port = selected_port
        
        # 使用队列进行进程间通信
        self.data_queue = Queue()  # 用于接收订阅数据的队列
        self.command_queue = Queue()  # 用于接收命令的队列
        self.subscription_update_queue = Queue()  # 用于更新订阅信息的队列
        
        self.is_running = False
        self.subscription_process = None
        self.consumer_thread = None
        
        # 跟踪各任务类型的订阅准备状态
        self.task_ready_status = {
            SubscriptionTaskType.TICK_DATA: False,
            SubscriptionTaskType.MIN_COST_MONITOR: False,
            SubscriptionTaskType.MORNING_MONITOR: False
        }
        
        # 各任务类型对应的股票代码集合
        self.task_stocks = {
            SubscriptionTaskType.TICK_DATA: set(),
            SubscriptionTaskType.MIN_COST_MONITOR: set(),
            SubscriptionTaskType.MORNING_MONITOR: set()
        }
        self.has_subscribed = False
        
        # 主进程中的回调函数映射
        self.local_callbacks = {}
        self.subscribed_stocks = set()  # 本地维护的订阅股票列表
    
    def mark_task_ready(self, task_type: SubscriptionTaskType, stock_codes: List[str] = None):
        """标记任务已准备好，并添加对应的股票代码"""
        self.task_ready_status[task_type] = True
        
        if stock_codes:
            self.task_stocks[task_type].update(stock_codes)
            
        # 检查是否所有任务都已准备好
        if all(self.task_ready_status.values()) and not self.has_subscribed:
            self._start_subscription()
            self.has_subscribed = True
    
    def _start_subscription(self):
        """开始订阅所有股票"""
        # 合并所有任务的股票代码
        all_stocks = set()
        for stocks in self.task_stocks.values():
            all_stocks.update(stocks)
            
        if all_stocks:
            # 更新本地的订阅股票集合
            self.subscribed_stocks.update(all_stocks)
            
            # 发送订阅命令
            self.command_queue.put(('subscribe', list(all_stocks)))
            logger.info(f"所有任务已准备好，开始订阅股票: {list(all_stocks)}")
        
    def start(self):
        """启动订阅服务"""
        self.is_running = True
        
        # 使用spawn上下文创建进程，避免序列化问题
        ctx = get_context('spawn')
        
        # 启动订阅进程
        self.subscription_process = ctx.Process(
            target=self._run_subscription_service,
            args=(self.selected_port, self.data_queue, self.command_queue)
        )
        self.subscription_process.start()
        
        # 启动数据消费线程
        self.consumer_thread = threading.Thread(target=self._run_data_consumer)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()
        
        logger.info("统一订阅服务已启动")
        
    def stop(self):
        """停止订阅服务"""
        self.is_running = False
        
        # 停止订阅进程
        if self.subscription_process:
            self.command_queue.put(('stop', None))
            self.subscription_process.join(timeout=10)
            if self.subscription_process.is_alive():
                self.subscription_process.terminate()
            self.subscription_process = None
            
        # 停止消费线程
        if self.consumer_thread and self.consumer_thread.is_alive():
            # 放入一个特殊消息来停止消费线程
            self.data_queue.put({'__stop__': True})
            self.consumer_thread.join(timeout=5)
            
        logger.info("统一订阅服务已停止")
        
    def subscribe(self, stock_codes: List[str], callback: Callable[[Dict], None] = None, name: str = None):
        """订阅股票代码"""
        if not stock_codes:
            return
        logger.info(f"订阅股票代码: {stock_codes} - {name}")
        # 在主进程中存储回调函数
        if callback:
            for code in stock_codes:
                if code not in self.local_callbacks:
                    self.local_callbacks[code] = []
                self.local_callbacks[code].append(callback)
        
        # 更新本地的订阅股票集合
        self.subscribed_stocks.update(stock_codes)
        
        # 发送订阅命令
        # self.command_queue.put(('subscribe', stock_codes))
            
    def unsubscribe(self, stock_codes: List[str], callback: Callable[[Dict], None] = None):
        """取消订阅股票代码"""
        for code in stock_codes:
            # 从主进程的回调函数列表中移除
            if code in self.local_callbacks and callback:
                if callback in self.local_callbacks[code]:
                    self.local_callbacks[code].remove(callback)
                if not self.local_callbacks[code]:
                    del self.local_callbacks[code]
        
        # 从本地订阅集合中移除
        for code in stock_codes:
            if code in self.subscribed_stocks:
                self.subscribed_stocks.remove(code)
        
        # 发送取消订阅命令
        self.command_queue.put(('unsubscribe', stock_codes))
        
    @staticmethod
    def _run_subscription_service(selected_port: int, data_queue: Queue, command_queue: Queue):
        """运行订阅服务的进程函数 - 只负责订阅和数据收集"""
        # 在子进程中导入xtdata
        from xtquant import xtdata
        xtdata.connect(port=selected_port)
        logger.info("统一订阅服务连接成功")
        
        # 在子进程中维护本地的订阅股票列表
        local_subscribed_stocks = set()
        subscription_id = None
        
        # 简单的数据收集回调函数
        def on_data(data_dict):
            """数据收集回调函数，只负责将数据放入队列"""
            try:
                data_dict = UnifiedSubscriptionService._change_data_dict(data_dict)
                data_queue.put(data_dict)
            except Exception as e:
                logger.error(f"数据放入队列错误: {e}")
        
        # 主循环
        is_running = True
        while is_running:
            try:
                # 检查命令
                if not command_queue.empty():
                    try:
                        command, data = command_queue.get_nowait()
                    except queue.Empty:
                        continue
                    
                    if command == 'subscribe' and data:
                        # 添加新股票到本地订阅列表
                        new_stocks = [code for code in data if code not in local_subscribed_stocks]
                        local_subscribed_stocks.update(new_stocks)
                        
                        # 重新订阅所有股票
                        if subscription_id is not None:
                            xtdata.unsubscribe_quote(subscription_id)
                        
                        if local_subscribed_stocks:
                            subscription_id = xtdata.subscribe_whole_quote(list(local_subscribed_stocks), callback=on_data)
                            logger.info(f"订阅股票更新: {list(local_subscribed_stocks)}")
                        
                    elif command == 'unsubscribe' and data:
                        # 从本地订阅列表中移除股票
                        for code in data:
                            if code in local_subscribed_stocks:
                                local_subscribed_stocks.remove(code)
                        
                        # 重新订阅所有股票
                        if subscription_id is not None:
                            xtdata.unsubscribe_quote(subscription_id)
                        
                        if local_subscribed_stocks:
                            subscription_id = xtdata.subscribe_whole_quote(list(local_subscribed_stocks), callback=on_data)
                            logger.info(f"订阅股票更新: {list(local_subscribed_stocks)}")
                        else:
                            subscription_id = None
                            
                    elif command == 'stop':
                        break
                
                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"订阅服务错误: {e}")
                time.sleep(1)  # 出错后等待一段时间再继续
        
        # 清理工作
        if subscription_id is not None:
            xtdata.unsubscribe_quote(subscription_id)
            
        logger.info("统一订阅服务进程结束")
    
    def _run_data_consumer(self):
        """运行数据消费线程 - 负责处理数据和调用回调函数"""
        logger.info("数据消费线程启动")
        
        while self.is_running:
            try:
                # 从队列获取数据
                data_dict = self.data_queue.get(timeout=1.0)
                
                # 检查是否是停止信号
                if isinstance(data_dict, dict) and '__stop__' in data_dict:
                    break
                
                # 分发数据到各个回调函数
                for stock_code, data in data_dict.items():
                    if stock_code in self.local_callbacks:
                        for callback in self.local_callbacks[stock_code]:
                            logger.info(f"[run_data_consumer] 调用回调函数: {callback}")
                            try:
                                callback(data)
                            except Exception as e:
                                logger.error(f"回调函数执行错误: {e}")
                                
            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"数据消费错误: {e}")
                time.sleep(1)  # 出错后等待一段时间再继续
                
        logger.info("数据消费线程结束")
    
    @staticmethod
    def _change_data_dict(data_dict: Dict):
        """转换数据格式"""
        new_data_dict = {}
        if not data_dict:
            return new_data_dict
        for stock_code, data in data_dict.items():
            new_data_dict[stock_code] = UnifiedSubscriptionService._change_data(stock_code, data)
        return new_data_dict

    @staticmethod
    def _change_data(stock, data: Dict):
        """转换数据格式"""
        def calculate_seconds_difference(specified_time):
                current_time = datetime.datetime.now().timestamp()
                time_difference =  current_time - (specified_time / 1000)
                return time_difference
                
        m = {}
        time = data['time']
        diff = calculate_seconds_difference(time)
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


        m['time'] = time
        m['diff'] = diff
        m['lastPrice'] = lastPrice
        m['open'] = open
        m['high'] = high
        m['low'] = low
        m['lastClose'] = lastClose
        m['volume'] = volume
        m['amount'] = amount
        m['pvolume'] = pvolume
        m['askPrice'] = askPrice
        m['bidPrice'] = bidPrice
        m['askVol'] = askVol
        m['bidVol'] = bidVol

        m['stock'] = stock
        logger.info(f'[change_data_success] 时间戳：{time}, 股票代码：{stock}, 当前价格：{lastPrice}, 延迟：{diff}, 总成交额：{amount}, 总成交量：{volume}, open - {open}, high - {high}, low - {low}, lastClose - {lastClose}, volume - {volume}, amount - {amount}, pvolume - {pvolume}, askPrice - {askPrice}, bidPrice - {bidPrice}, askVol - {askVol}, bidVol - {bidVol}')

        return m