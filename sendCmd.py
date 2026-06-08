#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
import sys
import time
from interface import deviceControl_auto, ping_check

logger = logging.getLogger(__name__)

# 基础路径（兼容 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))


def deviceSend(arg=None):  # 配置下发
    if arg is None:
        arg = []
    device_ip = arg[2]
    device_user = arg[0]
    device_pass = arg[1]
    des_local = arg[3]
    if ',' in arg[4]:  # 命令
        cmds = arg[4].split(',')
    else:
        cmds = [arg[4]]

    conn = deviceControl_auto(device_ip, device_user, device_pass)
    result = [device_ip, des_local]
    total_start = time.time()

    logger.info('%s 开始执行 (%d条命令)' % (device_ip, len(cmds)))

    # ping检测
    try:
        t0 = time.time()
        pingDelay = ping_check(device_ip)[0]
        logger.info('%s | ping: %sms (耗时%.1fs)' % (device_ip, pingDelay, time.time() - t0))
    except (OSError, ValueError, IndexError) as e:
        logger.warning('%s | ping异常: %s' % (device_ip, e))
        pingDelay = 'timeout'
    result.append(pingDelay)

    # 登录
    try:
        t0 = time.time()
        resData = conn.sendCmd_auto(cmds)
        login_time = time.time() - t0
        login_way = resData['loginWay']
        logger.info('%s | %s连接成功 (耗时%.1fs)' % (device_ip, login_way, login_time))
        result.append(login_way)

        # 逐条执行命令
        cmd_result = {}
        success_count = 0
        fail_count = 0
        cmd_total = len([k for k in resData if k != 'loginWay'])

        for idx, (resKey, value) in enumerate(resData.items(), 1):
            if resKey == 'loginWay':
                continue
            check_res, err_detail = checkError(value)
            byte_len = len(value.encode('utf-8', errors='ignore'))

            if check_res == '成功':
                success_count += 1
                logger.info('%s | [%d/%d] %s → 成功 (回显%d字节)'
                            % (device_ip, idx, cmd_total, resKey, byte_len))
            else:
                fail_count += 1
                logger.warning('%s | [%d/%d] %s → 失败: %s'
                               % (device_ip, idx, cmd_total, resKey, err_detail))

            cmd_result[resKey] = check_res[0]

        # 写入日志文件
        try:
            filepath = os.path.join(_base_dir, 'data', '%s_%s.log' % (device_ip, des_local))
            with open(filepath, 'w', encoding='utf-8') as f:
                for resKey, value in resData.items():
                    if resKey != 'loginWay':
                        f.write('=== %s ===\n' % resKey)
                        f.write('%s\n\n' % value)
            logger.info('%s | 日志已保存: %s' % (device_ip, filepath))
        except OSError as e:
            logger.error('%s | 日志文件写入失败: %s' % (device_ip, e))

        # 汇总
        total_time = time.time() - total_start
        summary = "\n".join(f"{k}:{v}" for k, v in cmd_result.items())
        result.append(summary)
        logger.info('%s | 结果: 成功%d条, 失败%d条 (总耗时%.1fs)'
                    % (device_ip, success_count, fail_count, total_time))

    except RuntimeError as e:
        logger.error('%s | 登录失败 (SSH+Telnet均失败): %s' % (device_ip, e))
        result.append('login fail')

    logger.info('%s 执行完成' % device_ip)
    return result


def checkError(dataTxt):  # 命令报错识别
    errorCode = ['Error: Unrecognized command found']
    for error in errorCode:
        if error in dataTxt:
            # 提取错误行
            for line in dataTxt.split('\n'):
                if error in line:
                    return '失败', line.strip()[:100]
            return '失败', error
    return '成功', ''


if __name__ == '__main__':
    pass
