#!/usr/bin/python3
# -*- coding: utf-8 -*-
from interface import deviceControl_auto, ping_check, get_value
import time


def deviceSend(arg=[]):  # 配置检查
    device_ip = arg[2]
    device_user = arg[0]
    device_pass = arg[1]
    des_local = arg[3]
    if ',' in arg[4]:#命令
        cmds = arg[4].split(',')
    else:
        cmds = [arg[4]]
    # print(cmds)
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
            # timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
            with open('data/%s_%s.log' % (device_ip, des_local), 'a', encoding='utf-8') as f:  # 命令回显集中存成.log文件
                for resKey, value in resData.items():  # 回显日志
                    if resKey != 'loginWay':
                        f.write('%s\n%s\n' % (resKey, value))
                        logger.get_log().info('命令:%s\n回显结果:%s\n' % (resKey, value))
            result.append('下发成功')
            logger.get_log().info('%s 命令下发完成' % (device_ip))
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
