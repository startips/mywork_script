#!/usr/bin/python3
# -*- coding: utf-8 -*-
from interface import deviceControl_auto, ping_check, get_value
import time


def deviceSend(arg=[]):  # 配置检查
    device_ip = arg[2]
    device_user = arg[0]
    device_pass = arg[1]
    des_local = arg[3]
    if ',' in arg[4]:  # 命令
        cmds = arg[4].split(',')
    else:
        cmds = [arg[4]]
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
            logger.get_log().info('%s 回显:\n' % (device_ip))
            cmd_result = {}
            with open('data/%s_%s.log' % (device_ip, des_local), 'w', encoding='utf-8') as f:
                for resKey, value in resData.items():  # 回显日志
                    if resKey != 'loginWay':
                        f.write('%s\n' % (value))
                        logger.get_log().info('命令:%s\n回显结果:%s\n' % (resKey, value))
                        cmd_result[resKey] = checkError(value)
            cmd_result = "\n".join(f"{k}:{v}" for k, v in cmd_result.items())
            result.append(cmd_result)  # 下发结果显示
            logger.get_log().info('%s 命令下发完成,结果汇总：%s' % (device_ip, cmd_result))
        except Exception as e:
            result.append('数据处理异常 %s' % (e))
            logger.get_log().info('%s 数据处理异常 %s' % (device_ip, e))
    except Exception as e:
        logger.get_log().error('%s 登陆失败 %s' % (device_ip, e))
        result.append('login fail')
    logger.get_log().info('%s 执行完成' % device_ip)
    return result


def checkError(dataTxt):  # 命令报错识别
    errorCode = ['Error: Unrecognized command found']
    for error in errorCode:
        if error in dataTxt:
            return '失败'
    return '成功'


if __name__ == '__main__':
    pass
