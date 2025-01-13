from dataclasses import dataclass
import logging
from typing import List
import json

from date_utils.date import *
from matplotlib import category
from http_request import build_http_request
from logger import logger

@dataclass
class BlockRank:
    tradeDate: str
    blockCode: str
    dataType: int
    industryType: int
    num: float
    directionNum: float
    numChange: float
    prePctChangeRate: float
    isTrack: bool
    isPpp: bool

@dataclass
class CategoryRank:
    tradeDate: str
    categoryCode: str
    categoryType: int
    num: float
    directionNum: float
    numChange: float
    prePctChangeRate: float
    isTrack: bool
    isPpp: bool
    name: str
    stockType: str
    industryType: str
    blockRankList: List[BlockRank]

def object_hook(d):
    if 'blockRankList' not in d:
        d['blockRankList'] = []
    return CategoryRank(**d)



def build_category_rank_dict(date = get_current_date()):
    rslt = build_http_request.block_category_rank(date = date)
    categoryDict = {}
    if rslt == None:
        return categoryDict
    if 'result' not in rslt:
        logger.error("block_category_rank no result.")
        return categoryDict
    if 'localCategoryRankList' in rslt['result']:
        localCategoryRankList = rslt['result']['localCategoryRankList']

    for item in localCategoryRankList:
        curItem = CategoryRank(**item)
        categoryDict[curItem.categoryCode] = curItem
    return categoryDict


def build_category_rank_list(date = get_current_date()):
    rslt = build_http_request.block_category_rank(date = date)
    categoryRankList = []
    if rslt == None:
        return categoryRankList
    if 'localCategoryRankList' in rslt['result']:
        localCategoryRankList = rslt['result']['localCategoryRankList']

    for item in localCategoryRankList:
        curItem = CategoryRank(**item)
        categoryRankList.append(curItem)
    return categoryRankList


def build_category_rank_sort_list(date = get_current_date()):
    rslt = build_http_request.block_category_rank(date = date)
    categoryRankList = []
    if rslt == None:
        return categoryRankList
    if 'localCategoryRankList' in rslt['result']:
        localCategoryRankList = rslt['result']['localCategoryRankList']

    for item in localCategoryRankList:
        curItem = CategoryRank(**item)
        categoryRankList.append(curItem)

    categoryRankList.sort(key=lambda x: x.num, reverse=True)
    return categoryRankList


def build_block_rank_list(date = get_current_date()):
    category_rank_list =  build_category_rank_list(date)
    block_rank_list = []
    rslt = []
    for item in category_rank_list:
        if item == None:
            continue
        if item.blockRankList == None:
            continue
        block_rank_list.extend(item.blockRankList)
    for item in block_rank_list:
        if item == None:
            continue
        block = BlockRank(**item)
        rslt.append(block)
    return rslt


def build_block_rank_dict(date = get_current_date()):
    block_rank_list =  build_block_rank_list(date)
    block_rank_dict = {}
    for item in block_rank_list:
        block_rank_dict[item.blockCode] = item
    return block_rank_dict


def build_block_rank_sort_list(date = get_current_date()):
    block_rank_list =  build_block_rank_list(date)
    block_rank_list.sort(key=lambda x: x.num, reverse=True)
    return block_rank_list


def build_block_rank_to_category_rank_dict(date = get_current_date()):
    category_rank_list = build_category_rank_sort_list(date)
    rslt = {}
    for item in category_rank_list:
        if item.blockRankList != None:
            for block in item.blockRankList:
                if 'blockCode' in block:
                    if block['blockCode'] in rslt:
                        logger.error("blockCode already exists. blockCode: " + block['blockCode'] + " categoryCode: " + item.categoryCode + " categoryName: " + item.name)
                    rslt[block['blockCode']] = item.categoryCode
    return rslt
    