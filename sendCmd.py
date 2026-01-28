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
        pass
    else:
        result.append(revInfo)
    for key in result_dic:  # 转换到list
        result.append(result_dic[key])
    return result


def deviceSend(arg=[]):  # 配置检查
    device_ip = arg[2]
    device_user = arg[0]
    device_pass = arg[1]
    des_local = arg[3]
    cmds = arg[4]  # 命令
    logger = get_value('logger')
    conn = deviceControl_auto(device_ip, device_user, device_pass)  # 登陆
    logger.get_log().info('%s 登陆成功' % (device_ip))
    result = [device_ip, des_local]
    pingDelay = ping_check(device_ip)[0]  # ping检测
    result.append(pingDelay)
    try:  # 登录检查
        resData = conn.sendCmd_auto(cmds)
        result.append(resData['loginWay'])  # 登录方式
        try:  # 处理数据检查
            result.extend(infoDeal(resData))
            logger.get_log().info('%s 命令下发成功' % (device_ip))
        except Exception as e:
            result.append('下发失败 %s' % (e))
            logger.get_log().info('%s 下发失败 %s' % (device_ip, e))
    except Exception as e:
        logger.get_log().error('%s 登陆失败 %s' % (device_ip, e))
        result.append('login fail')
    logger.get_log().info('%s 执行完成' % device_ip)
    return result


if __name__ == '__main__':
    pass
