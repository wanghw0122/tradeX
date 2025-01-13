import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
from http_request import build_http_request
from http_request import http_context
from data_class import *
from strategy.strategy import *
import json
from logger import logger

# 设置环境变量


# d = industry_block_rank.build_industry_block_rank_dict(date = "2025-01-10")

# d = build_http_request.dynamic_index(date = "2025-01-10")

# d = dynamic_index.build_block_environment_index_list(date = "2025-01-10")

# d = build_http_request.xiao_cao_environment_second_line_v2(codes=['9A0001','9A0002','9A0003','9B0001','9B0002','9B0003','9C0001'], date="2025-01-10")

sys_time = http_context['system_time']

print(sys_time())
# d, s = xiao_cao_environment_second_line_v2.build_xiaocao_environment_second_line_v2_dict_all(date="2025-01-10")

# category_rank_class.main()
# print(json.dumps(build_http_request.block_category_rank(date = "2025-01-10")))