from http_request import build_http_request
from data_class import *

import json

import logging

# 创建一个日志记录器
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)  # 设置日志级别

# 创建一个文件处理器，将日志记录到文件
file_handler = logging.FileHandler('running.log')
file_handler.setLevel(logging.DEBUG)  # 设置文件处理器的日志级别

# 创建一个控制台处理器，将日志输出到控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # 设置控制台处理器的日志级别

# 创建一个格式化器，定义日志的输出格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 将格式化器添加到处理器
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 将处理器添加到日志记录器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# d = industry_block_rank.build_industry_block_rank_dict(date = "2025-01-10")

# d = build_http_request.dynamic_index(date = "2025-01-10")

# d = dynamic_index.build_block_environment_index_list(date = "2025-01-10")

# d = build_http_request.xiao_cao_environment_second_line_v2(codes=['9A0001','9A0002','9A0003','9B0001','9B0002','9B0003','9C0001'], date="2025-01-10")

d, s = xiao_cao_environment_second_line_v2.build_xiaocao_environment_second_line_v2_dict_all(date="2025-01-10")
print(d)
print(s)


# category_rank_class.main()
# print(json.dumps(build_http_request.block_category_rank(date = "2025-01-10")))