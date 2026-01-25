#!/usr/bin/python3
# -*- coding: utf-8 -*-
from interface import get_value, readTxt
import re


def infoDeal(data):  # 数据处理 返回list
    data_local = data
    # print(type(data_local))
    result_dic = {}
    result = []
    readInfo = readTxt('read/Keywords.txt')  # 读取匹配关键字
    for i in readInfo:
        cell = i.split(',')
        result_dic.update({cell[1]: ''})
    for info in readInfo:
        keywords = info.split(',')
        configStr = re.search(r'%s' % keywords[0], data_local, re.IGNORECASE)
        if configStr:
            if keywords[2] == '0':
                checkRes = '多余\'%s\':%s\n' % (keywords[1], keywords[0])
                result_dic.update({keywords[1]: result_dic[keywords[1]] + checkRes})
            elif keywords[2] == '3':
                result_dic.update({keywords[1]: result_dic[keywords[1]] + configStr.group()})

        else:
            if keywords[2] == '1':
                checkRes = '缺少\'%s\':%s\n' % (keywords[1], keywords[0])
                result_dic.update({keywords[1]: result_dic[keywords[1]] + checkRes})
            elif keywords[2] == '3':
                result_dic.update({keywords[1]: result_dic[keywords[1]]+'未匹配出'})

    else:
        for key in result_dic:
            if result_dic[key] == '':
                result_dic.update({key: '检查通过'})
    for key in result_dic:  # 转换到list
        result.append(result_dic[key])
    return result


def deviceCheck(arg=[]):  # 根据文件名读取配置
    filename = arg
    logger = get_value('logger')
    logname = filename.replace('read/config/', '').replace('.txt', '').replace('.log', '')
    result = [logname]
    # print(filename)
    try:  # 登录检查
        with open(filename, 'r', encoding='utf-8') as f:
            data = f.read()
    except Exception as e:
        logger.get_log().error('%s 读取文件失败 %s' % (filename, e))
        result.append('read fail')
        return result
    result.extend(infoDeal(data))  # 数据处理
    logger.get_log().info('%s 执行完成' % filename)
    return result


if __name__ == '__main__':
    infoDeal({'dis current-configuration': '123'})
    # c = {}
    # print(type(c.get('i')))
