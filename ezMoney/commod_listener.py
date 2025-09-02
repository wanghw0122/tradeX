import time
import threading
import win32pipe
import win32file
import pywintypes
import datetime
from xtquant import xtconstant
import traceback

def is_before_930():
    now = datetime.datetime.now()
    target_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return now < target_time

class NamedPipeServer:
    """命名管道服务器类，用于接收和处理交易指令"""
    
    def __init__(self, qmt_trader=None, buy_queue=None, rebuy_queue=None):
        """
        初始化命名管道服务器
        
        Args:
            qmt_trader: QMT交易接口实例 (预留参数)
            blockqueue: 阻塞队列实例 (预留参数)
        """
        self.qmt_trader = qmt_trader
        self.buy_queue = buy_queue
        self.rebuy_queue = rebuy_queue
        self.running = False
        self.pipe_thread = None
        self.pipe_name = r'\\.\pipe\StockTradingPipe'
    
    def start_server(self):
        """启动命名管道服务器"""
        self.running = True
        self.pipe_thread = threading.Thread(target=self._named_pipe_server, daemon=True)
        self.pipe_thread.start()
        print("股票交易程序已启动...")
        return True
    
    def stop_server(self):
        """停止命名管道服务器"""
        self.running = False
        if self.pipe_thread and self.pipe_thread.is_alive():
            # 创建一个客户端连接来唤醒服务器循环
            try:
                client = win32file.CreateFile(
                    self.pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0, None,
                    win32file.OPEN_EXISTING,
                    0, None
                )
                win32file.WriteFile(client, "exit".encode('utf-8'))
                win32file.CloseHandle(client)
            except:
                pass
        print("命名管道服务器已停止")
    
    def _named_pipe_server(self):
        """内部方法：创建命名管道服务器"""
        while self.running:
            try:
                # 创建命名管道
                pipe = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    1, 65536, 65536, 0, None
                )
                
                print(f"命名管道服务器已启动，等待连接... (管道: {self.pipe_name})")
                
                # 等待客户端连接
                win32pipe.ConnectNamedPipe(pipe, None)
                print("客户端已连接")
                
                try:
                    while self.running:
                        try:
                            # 读取消息
                            result, data = win32file.ReadFile(pipe, 65536)
                            if result == 0:
                                message = data.decode('utf-8').strip()
                                print(f"收到指令: {message}")
                                
                                # 处理指令
                                response = self._process_command(message)
                                
                                # 发送响应
                                win32file.WriteFile(pipe, response.encode('utf-8'))
                                
                                # 如果是退出命令，则退出循环
                                if message.lower() == "exit":
                                    break
                        except pywintypes.error as e:
                            if e.winerror == 109:  # 管道已结束
                                print("客户端断开连接")
                                break
                            elif e.winerror == 232:  # 管道已关闭
                                print("管道已关闭")
                                break
                            else:
                                print(f"读取错误: {e}")
                                break
                except Exception as e:
                    print(f"处理客户端时发生错误: {e}")
                    stack_trace = traceback.format_exc()
                    print(stack_trace)

                finally:
                    # 断开连接并关闭管道
                    try:
                        win32pipe.DisconnectNamedPipe(pipe)
                    except:
                        pass
                    win32file.CloseHandle(pipe)
                    
            except Exception as e:
                if self.running:  # 只在服务器仍在运行时打印错误
                    print(f"服务器错误: {e}")
                time.sleep(1)  # 出错后等待一秒再重试
    
    def _process_command(self, command):
        """
        内部方法：处理交易指令
        
        Args:
            command: 收到的指令字符串
            
        Returns:
            str: 处理结果响应
        """
        parts = command.split()
        if not parts:
            return "错误: 无效指令\n"
        
        action = parts[0].lower()
        
        # 这里可以添加使用qmt_trader和blockqueue的实际交易逻辑
        if action == "buy" or action == "b":
            if len(parts) < 2:
                return "错误: buy指令需要参数: buy [股票代码] [金额] [价格]\n"
            stock = parts[1]
            if len(parts) == 2:
                return self._process_buy(stock, 0, 0, 1, 0)
            amount = float(parts[2])
            if amount < 0:
                return "错误: 金额不能小于0\n"
            
            if len(parts) == 4:
                price = float(parts[3])
            else:
                price = 0
            if price < 0:
                return "错误: 价格不能小于0\n"

            if amount <= 1:
                return self._process_buy(stock, 0, 0, amount, price)
            else:
                return self._process_buy(stock, amount, 0, 1, price)
        elif action == "bv" or action == "buyvolume":
            if len(parts) < 2:
                return "错误: buy指令需要参数: buy [股票代码] [金额] [价格]\n"
            stock = parts[1]
            if len(parts) == 2:
                return self._process_buy(stock, 0, 0, 1, 0)
            volume = float(parts[2])
            if volume < 0:
                return "错误: 金额不能小于0\n"
            
            if len(parts) == 4:
                price = float(parts[3])
            else:
                price = 0
            if price < 0:
                return "错误: 价格不能小于0\n"

            if volume <= 1:
                return self._process_buy(stock, 0, 0, volume, price)
            else:
                return self._process_buy(stock, 0, volume, 1, price)
        elif action == "sell" or action == "s":
            if len(parts) < 2:
                return "错误: sell指令需要参数: sell [股票代码] [数量] [类型] \n"
            stock = parts[1]
            if len(parts) == 2:
                return self._process_sell(stock, 0, 0, 1, 1)
            amount = float(parts[2])
            if amount < 0:
                return "错误: 金额不能小于0\n"
            if len(parts) == 4:
                sell_type = int(parts[3])
            else:
                sell_type = 1
            if amount <= 1:
                return self._process_sell(stock, 0, 0, sell_type, amount)
            else:
                return self._process_sell(stock, 0, amount, 1, 1)
        elif action == "sv" or action == "sellvolume":
            if len(parts) < 2:
                return "错误: sell指令需要参数: sell [股票代码] [数量] [类型] \n"
            stock = parts[1]
            if len(parts) == 2:
                return self._process_sell(stock, 0, 0, 1, 1)
            volume = float(parts[2])
            if volume < 0:
                return "错误: 金额不能小于0\n"
            if len(parts) == 4:
                sell_type = int(parts[3])
            else:
                sell_type = 1
            if volume <= 1:
                return self._process_sell(stock, 0, 0, sell_type, volume)
            else:
                return self._process_sell(stock, volume, 0, 1, 1)
        elif action == "cancel" or action == "c":
            self.qmt_trader.cancel_active_orders()
            return "成功: 取消所有订单\n"
        elif action == "exit":
            return "退出程序\n"
        
        else:
            return f"错误: 未知指令 '{action}'\n"

    def _process_buy(self, stock_code, amount = 0, volume = 0, position = 1, price = 0):
        if not stock_code:
            return "错误: 股票代码不能为空\n"
        if '.' not in stock_code:
            stock_code = self.qmt_trader.all_stocks[stock_code]
        if not stock_code:
            return "错误: 股票代码不存在\n"
        num_code = stock_code.split('.')[0]
        if is_before_930():
            bid_info = {}
            code_info = '强更强:第一|' + num_code
            if position == 0:
                return "错误: position错误\n"
            buffers = [0.018]
            mark_info = '强更强:第一'
            bid_info[code_info] = (code_info, position, buffers, mark_info)
            self.rebuy_queue.put((num_code, position))
            self.buy_queue.put(bid_info)
            return "成功: 下单\n"
        else:
            if amount > 0:
                if price > 0:
                    buy_volume = int(amount / price // 100 * 100)
                    order_id =  self.qmt_trader.buy_immediate(stock_code, buy_volume, price)
                    if order_id > 0:
                        return "成功: 下单\n"
                    else:
                        return "错误: 下单失败\n"
                else:
                    if 'SH' in stock_code:
                        order_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL
                    else:
                        order_type = xtconstant.MARKET_SZ_CONVERT_5_CANCEL
                    order_id = self.qmt_trader.buy_quickly(stock_code, amount, order_type = order_type)
                    if not order_id:
                        return "错误: 下单失败\n"
                    if order_id and order_id > 0:
                        return "成功: 下单\n"
                    else:
                        return "错误: 下单失败\n"
            elif volume > 0:
                if price > 0:
                    buy_volume = int(volume // 100 * 100)
                    order_id =  self.qmt_trader.buy_immediate(stock_code, buy_volume, price)
                    if order_id > 0:
                        return "成功: 下单\n"
                    else:
                        return "错误: 下单失败\n"
                else:
                    if 'SH' in stock_code:
                        order_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL
                    else:
                        order_type = xtconstant.MARKET_SZ_CONVERT_5_CANCEL
                    order_id = self.qmt_trader.buy_immediate_market_order(stock_code, volume, order_type = order_type)
                    if order_id > 0:
                        return "成功: 下单\n"
                    else:
                        return "错误: 下单失败\n"
                    
        return "错误: 下单时间错误\n"

    def _process_sell(self, stock_code, volume = 0, amount = 0, sell_type = 1, position = 1):
        if not stock_code:
            return "错误: 股票代码不能为空\n"
        if '.' not in stock_code:
            stock_code = self.qmt_trader.all_stocks[stock_code]
        if not stock_code:
            return "错误: 股票代码不存在\n"
        if sell_type == 1:
            if 'SH' in stock_code:
                order_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL
            else:
                order_type = xtconstant.MARKET_SZ_CONVERT_5_CANCEL
        else:
            order_type = xtconstant.FIX_PRICE
        order_id = self.qmt_trader.sell_quickly(stock_code, '', volume, amount = amount, order_type = order_type, position = position)
        if order_id > 0:
            return f"成功: 下单 {order_id}\n"
        else:
            return f"错误: 下单失败 {order_id}\n"        

# 使用示例
if __name__ == "__main__":
    # 安装所需库: pip install pywin32
    
    # 创建服务器实例，传入预留参数
    server = NamedPipeServer(qmt_trader=None, blockqueue=None)
    
    # 启动服务器
    server.start_server()
    
    # 主程序继续执行其他任务
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("程序正在停止...")
        server.stop_server()