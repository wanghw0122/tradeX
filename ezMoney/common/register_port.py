import os
import socket
import threading
import multiprocessing
from contextlib import closing

# ================= 端口管理器 =================
class PortManager:
    """端口分配与管理器"""
    _instance = None
    
    def __new__(cls, start_port=58611, max_attempts=20):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.start_port = start_port
            cls._instance.max_attempts = max_attempts
            cls._instance.allocated_port = multiprocessing.Value('i', 0)
            cls._instance.lock = multiprocessing.Lock()
        return cls._instance
    
    def find_free_port(self):
        """查找可用端口"""
        with self.lock:
            if self.allocated_port.value != 0:
                return self.allocated_port.value
                
            for port in range(self.start_port, self.start_port + self.max_attempts):
                try:
                    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                        s.bind(('', port))
                    return port
                except OSError:
                    continue
            raise OSError(f"未能在 {self.start_port}-{self.start_port+self.max_attempts} 范围内找到空闲端口")
    
    def allocate_port(self):
        """分配端口并标记为已使用"""
        with self.lock:
            if self.allocated_port.value == 0:
                port = self.find_free_port()
                self.allocated_port.value = port
            return self.allocated_port.value
    
    def get_port(self):
        """获取已分配的端口"""
        with self.lock:
            return self.allocated_port.value

# ================= 服务注册中心 =================
class ServiceRegistry:
    """服务注册与发现中心"""
    def __init__(self):
        self.port = 0
        self.lock = threading.Lock()
        self.registry_file = "port_registry.txt"
    
    def register_port(self, port):
        """注册端口到文件"""
        with self.lock:
            self.port = port
            with open(self.registry_file, 'w') as f:
                f.write(str(port))
    
    def discover_port(self):
        """从文件发现端口"""
        with self.lock:
            if self.port > 0:
                return self.port
            
            try:
                if os.path.exists(self.registry_file):
                    with open(self.registry_file, 'r') as f:
                        port = int(f.read().strip())
                        if port > 0:
                            self.port = port
                            return port
            except:
                pass
            return 0

# ================= 修改后的主程序 =================
def main_program():
    # 初始化端口管理器
    port_manager = PortManager()
    
    # 初始化服务注册中心
    service_registry = ServiceRegistry()
    
    # 尝试发现已注册端口
    discovered_port = service_registry.discover_port()
    
    if discovered_port > 0:
        print(f"发现已注册端口: {discovered_port}")
        port = discovered_port
    else:
        # 分配新端口
        port = port_manager.allocate_port()
        print(f"分配新端口: {port}")
        # 注册端口
        service_registry.register_port(port)

if __name__ == '__main__':
    main_program()


    
