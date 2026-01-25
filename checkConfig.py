#!/usr/bin/python3
# -*- coding: utf-8 -*-
from interface import deviceControl_auto, ping_check, get_value, revData_error, readTxt
import re


def infoDeal(data):  # 数据处理 返回list
    data_local = data
    result_dic = {}
    result = []
    readInfo = readTxt('read/Keywords.txt')  # 读取匹配关键字
    for i in readInfo:
        cell = i.split(',')
        result_dic.update({cell[1]: ''})
    revInfo = revData_error(data_local['dis current-configuration'])  # 判断是否有命令执行错误
    if revInfo == 'NULL':
        for info in readInfo:
            keywords = info.split(',')
            configStr = re.search(r'%s' % keywords[0], data_local['dis current-configuration'], re.IGNORECASE)
            if configStr:
                if keywords[2] == '0':
                    checkRes = '多余\'%s\':%s\n' % (keywords[1], keywords[0])
                    result_dic.update({keywords[1]: result_dic[keywords[1]] + checkRes})
            else:
                if keywords[2] == '1':
                    checkRes = '缺少\'%s\':%s\n' % (keywords[1], keywords[0])
                    result_dic.update({keywords[1]: result_dic[keywords[1]] + checkRes})
        else:
            for key in result_dic:
                if result_dic[key] == '':
                    result_dic.update({key: '无不合规项'})
    else:
        result.append(revInfo)
    for key in result_dic:  # 转换到list
        result.append(result_dic[key])
    return result


def deviceCheck(arg=[]):  # 配置检查
    device_ip = arg[2]
    device_user = arg[0]
    device_pass = arg[1]
    des_local = arg[3]
    logger = get_value('logger')
    conn = deviceControl_auto(device_ip, device_user, device_pass)  # 登陆
    cmd = ['dis current-configuration']  # 命令
    result = [device_ip, des_local]
    pingDelay = ping_check(device_ip)[0]  # ping检测
    result.append(pingDelay)
    try:  # 登录检查
        resData = conn.sendCmd_auto(cmd)
        logger.get_log().info('%s 登陆成功' % (device_ip))
        result.append(resData['loginWay'])  # 登录方式
        try:  # 处理数据检查
            result.extend(infoDeal(resData))
            logger.get_log().info('%s 数据处理成功' % (device_ip))
        except Exception as e:
            result.append('数据处理失败 %s' % (e))
            logger.get_log().info('%s 数据处理失败 %s' % (device_ip, e))
    except Exception as e:
        logger.get_log().error('%s 登陆失败 %s' % (device_ip, e))
        result.append('login fail')
    logger.get_log().info('%s 执行完成' % device_ip)
    return result


if __name__ == '__main__':
    infoDeal({'dis current-configuration': '123'})
    # c = {}
    # print(type(c.get('i')))
