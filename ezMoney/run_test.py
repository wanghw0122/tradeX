from multiprocessing import Process
from multiprocessing.managers import BaseManager

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
    with MyManager() as manager:
        shared_obj = manager.MyClass()
        print(f"主进程值: {shared_obj.get_value()}")
        v = V(shared_obj)
        p = Process(target=worker, args=(shared_obj,))
        p.start()
        p.join()
        print(f"主进程值: {v.obj.get_value()}")