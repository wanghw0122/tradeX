from turtle import mode
from .category_rank_class import *
import logging

logger = logging.getLogger("my_logger")


def build_industry_block_rank_dict(date = get_current_date(), model = 0):
    rslt = build_http_request.industry_block_rank(date = date, model = model)
    if rslt == None:
        return {}
    if 'errcode' in rslt and rslt['errcode'] != None:
        logger.error("industry_block_rank error! errcode: " + rslt['errcode'])
    if 'result' not in rslt:
        logger.error("industry_block_rank no result.")
        return {}
    block_list = rslt['result']
    block_dict = {}
    for item in block_list:
        if 'blockCode' not in item:
            logger.error("industry_block_rank no blockCode.")
            continue
        block_dict[item['blockCode']] = BlockRank(**item)
    return block_dict