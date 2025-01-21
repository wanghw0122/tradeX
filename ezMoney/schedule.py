import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time

i = 0
def job_func(text):
    print(text)
    print(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
    global i
    i = i + 1
    if i == 3:
        scheduler.remove_job("my_job")
        print("任务执行成功，已移除任务")

scheduler = BackgroundScheduler()
# 每隔5秒执行一次 job_func 方法
scheduler.add_job(job_func, 'interval', seconds=5, args=['Hello!'], id="my_job")
# 在 2025-01-21 22:08:01 ~ 2025-01-21 22:09:00 之间, 每隔5秒执行一次 job_func 方法
# scheduler.add_job(job_func, 'interval', seconds=5, start_date='2025-01-21 22:12:01', end_date='2025-01-21 22:13:00', args=['World!'])

# 启动调度器
scheduler.start()

start_time = datetime.datetime.now()

# 保持程序运行，以便调度器可以执行任务
try:
    while True:
        if (datetime.datetime.now() - start_time).total_seconds() > 30 * 60:
            print("达到最大执行时间，退出程序")
            scheduler.shutdown()
            break
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    # 关闭调度器
    scheduler.shutdown()
