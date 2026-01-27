#!/usr/bin/python3
# -*- coding: utf-8 -*-
from interface import get_value, readTxt
import re


def infoFormat(data):  # 数据处理 返回list
    data_local = data
    result_dic = {}
    result = []
    ####正则区域
    matchVerinfo = re.findall(r'Version \S+ \(\S+ (\S+)\)', data_local)  # 版本
    matchPatInfo = re.findall(r'Patch Package Version \:(\S+)', data_local)  # 补丁
    verCount = len(re.findall(r'\d+\s+\S+\s+\S+\s+\S+\s\d+\s\d+\s\d+\:\d+\:\d+\s+\S+\.cc', data_local,
                              re.IGNORECASE))  # 统计文件数量
    patCount = len(re.findall(r'\d+\s+\S+\s+\S+\s+\S+\s\d+\s\d+\s\d+\:\d+\:\d+\s+\S+\.pat', data_local,
                              re.IGNORECASE))
    cfgCount = len(re.findall(r'\d+\s+\S+\s+\S+\s+\S+\s\d+\s\d+\s\d+\:\d+\:\d+\s+\S+\.cfg', data_local,
                              re.IGNORECASE))
    deviceInfo = re.search(r'Device status:[\s\S]*?<', data_local, re.IGNORECASE)  # 硬件状态信息
    matchDownPortInfo = re.findall(r'(?:100|25)GE\d+\/\d+\/\d+\s+(down|down\(ed\)|down\(b\))(?:\s+\S+){5}', data_local,
                                   re.IGNORECASE)  # 匹配未关闭端口
    bgpInfo = re.search(r'BGP local router ID[\s\S]*?<', data_local, re.IGNORECASE)  # bgp状态信息
    matchRecover = re.findall('The number of failed commands is (\d+)', data_local, re.IGNORECASE)  # 失败命令配置检查
    ####判断区域
    readInfo = readTxt('read/Keywords.txt')  # 读取匹配关键字
    for i in readInfo:
        cell = i.split(',')
        result_dic.update({cell[1]: ''})
    for info in readInfo:
        keywords = info.split(',')
        if keywords[2] == '3':  # 自定义模式
            match keywords[1]:
                case '版本':
                    if matchVerinfo:
                        verinfo = matchVerinfo[0]
                    else:
                        verinfo = '未匹配到'
                    result_dic.update({keywords[1]: verinfo})
                case '补丁':
                    if matchPatInfo:
                        patInfo = matchPatInfo[0]
                    else:
                        patInfo = '未匹配到'
                    result_dic.update({keywords[1]: patInfo})
                case '多余文件检查':
                    if verCount == 1 and patCount == 1 and cfgCount == 1:
                        allCount = '通过'
                    elif verCount == 0 and patCount == 0 and cfgCount == 0:
                        allCount = '未匹配到'
                    else:
                        allCount = 'cc:%d,pat:%d,cfg:%d' % (verCount, patCount, cfgCount)
                    result_dic.update({keywords[1]: allCount})
                case '硬件状态检查':
                    if deviceInfo:
                        statusStr = ['Offline', 'Unregistered', 'Abnormal']
                        checkDeviceRes = '通过'
                        for str in statusStr:
                            if str in deviceInfo.group():
                                checkDeviceRes = '未通过'
                    else:
                        checkDeviceRes = '未匹配到'
                    result_dic.update({keywords[1]: checkDeviceRes})
                case '未关闭端口':
                    if matchDownPortInfo:
                        result_dic.update({keywords[1]: len(matchDownPortInfo)})
                    else:
                        result_dic.update({keywords[1]: '通过'})
                case 'feature-software状态':
                    if matchVerinfo:
                        if 'V300' in matchVerinfo[0]:  # 判断V300版本
                            matchFertureInfo = re.findall(
                                '(:?PKG_PNF|AIFABRIC|TELEMETRY|WEAKEA)\s+\S+\.cc\s+active\s+\S+\s+\d{4}-\d{2}-\d{2}\s+\d{2}\:\d{2}\:\d{2}',
                                data_local, re.IGNORECASE)
                            if len(matchFertureInfo) == 4:
                                result_dic.update({keywords[1]: '通过'})
                            else:
                                result_dic.update({keywords[1]: '未通过'})
                        else:
                            result_dic.update({keywords[1]: '版本不涉及'})
                    else:
                        result_dic.update({keywords[1]: '未匹配到'})
                case 'bgp邻居状态':
                    if bgpInfo:
                        bgpNum = re.findall(r'Total number of peers\s+\:\s+(\d+)', bgpInfo.group(), re.IGNORECASE)[0]
                        normalBgpNum = len(
                            re.findall(r'\d+\.\d+\.\d+\.\d+(:?\s+\d+){5}\s\d{2}\:\d{2}\:\d{2}\s+Established',
                                       bgpInfo.group(),
                                       re.IGNORECASE))
                        result_dic.update({keywords[1]: '邻居数量:%s,正常邻居数量:%d' % (bgpNum, normalBgpNum)})
                    else:
                        result_dic.update({keywords[1]: '未匹配到'})
                case '失败命令配置检查':
                    if matchRecover:
                        if matchRecover[0] == '0':
                            result_dic.update({keywords[1]: '通过'})
                        else:
                            result_dic.update({keywords[1]: matchRecover[0]})
                    else:
                        result_dic.update({keywords[1]: '未匹配到'})
                case _:
                    pass
        else:  # 预配置keyWord模式
            configStr = re.search(r'%s' % keywords[0], data_local, re.IGNORECASE)
            if configStr:
                if keywords[2] == '0':
                    # checkRes = '多余\'%s\':%s\n' % (keywords[1], keywords[0])
                    # result_dic.update({keywords[1]: result_dic[keywords[1]] + '未通过'})
                    result_dic.update({keywords[1]: '未通过'})
                elif keywords[2] == '2':
                    result_dic.update({keywords[1]: result_dic[keywords[1]] + configStr.group()})
            else:
                if keywords[2] == '1':
                    # checkRes = '缺少\'%s\':%s\n' % (keywords[1], keywords[0])
                    # result_dic.update({keywords[1]: result_dic[keywords[1]] + '未通过'})
                    result_dic.update({keywords[1]: '未通过'})
                elif keywords[2] == '2':
                    result_dic.update({keywords[1]: result_dic[keywords[1]] + '未匹配到'})

    else:
        for key in result_dic:
            if result_dic[key] == '':
                result_dic.update({key: '通过'})
    for key in result_dic:  # 转换到list
        result.append(result_dic[key])
    return result


def deviceCheck(arg=[]):  # 根据文件名读取配置
    filename = arg
    logger = get_value('logger')
    logname = filename.replace('read/config/', '').replace('.txt', '').replace('.log', '')
    result = [logname]
    try:  # 登录检查
        with open(filename, 'r', encoding='utf-8') as f:
            data = f.read()
    except Exception as e:
        logger.get_log().error('%s 读取文件失败 %s' % (filename, e))
        result.append('read fail')
        return result
    result.extend(infoFormat(data))  # 数据处理
    logger.get_log().info('%s 执行完成' % filename)
    return result


if __name__ == '__main__':
    pass
    # c = {}
    # print(type(c.get('i')))
