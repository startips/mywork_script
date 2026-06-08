#!/usr/bin/python3
# -*- coding: utf-8 -*-
import getpass
import logging
import platform
import time
import os
import sys
from alive_progress import alive_bar
from interface import excel, autoThreadingPool, readTxt
from interface.log_config import setup_logging

logger = logging.getLogger(__name__)

# 基础路径（兼容 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))


# import encodings.idna  # 解决python3.9 LookupError: unknown encoding: idna socket.gethostbyname(destination)
# pyinstaller打包后出错 python3.10已解决这个bug

def funcAction(func, logName, data=None, user='', passwd='', fileName='', worker=30):  # 统一执行入口
    with alive_bar(title='Progress', bar='filling', spinner='waves2', unknown='wait', manual=True,
                   enrich_print=False) as bar:
        setup_logging(logName, log_dir=os.path.join(_base_dir, 'log'))
        logger.info('当前运行环境:%s %s %s' % (platform.system(), platform.version(), platform.machine()))

        if fileName:
            # 在线模式：从 Excel 读取 + 注入凭据
            file_dir = os.path.join(_base_dir, 'read', fileName)
            read = excel(file_dir)
            bar(0.05)
            try:
                read_info = read.excel_read()
                logger.info('读取 \'%s\' 成功,数量:%d' % (fileName, len(read_info)))
            except Exception as e:
                logger.error('读取 \'%s\' 失败:%s' % (fileName, e))
                bar(1)
                return
            bar(0.06)
            for readCell in read_info:
                readCell.insert(0, passwd)
                readCell.insert(0, user)
            task_data = read_info
            bar(0.1)
        else:
            # 离线模式：直接使用传入数据
            task_data = data or []
            bar(0.1)

        logger.info('%s 载入线程...' % func.__name__)
        my_poll = autoThreadingPool(int(worker), bar=bar)
        result = my_poll(func, task_data)
        logger.info('线程结束,准备写入本地...')
        bar(1)
        return result


def oringinDataFormat():  # 原始数据分类
    file_dir = os.path.join(_base_dir, 'read', 'config')
    all_items = [item for item in os.listdir(file_dir) if not item.startswith('.')]  # 去掉.开头的文件
    read_info = []  # 结果
    for item in all_items:
        name = item.replace('.txt', '').replace('.log', '')
        read_info.append({'name': name, 'filename': item})
    return read_info


def writeToExcel(filename, title, data):  # 写入数据到excel
    filename_local = os.path.join(_base_dir, 'data', filename)
    title_local = title
    data_local = data
    write_info = excel(filename_local)
    try:
        write_info.excel_write(title_local, data_local)
        basename = write_info.save_file()
        logger.info('文件 %s 写入完成,保存至data目录下' % basename)
    except Exception as e:
        logger.error('文件写入失败,%s' % e)


def writeToTXT(data):  # 写入数据到TXT
    data_local = data
    timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    try:
        for data_unit in data_local:
            filepath = os.path.join(_base_dir, 'data', '%s_%s_%s.log' % (data_unit[0], data_unit[1], timeNow))
            with open(filepath, 'w') as f:
                f.write(data_unit[2])
    except Exception as e:
        logger.error('文件写入失败,%s %s' % (e, Exception))
        return
    logger.info('文件写入完成,保存至data目录下')


def platform_select():  # 判断当前运行环境
    username = ''
    password = ''
    worker = os.cpu_count()
    platformStr = platform.system()
    if 'Windows' in platformStr:
        from interface import passwdinput
        username = input('用户:')
        password = passwdinput('密码:')
    elif 'Linux' in platformStr:
        import sys
        username, password = sys.argv[1], sys.argv[2]
    elif 'Darwin' in platformStr:
        username = input('用户:')
        password = getpass.getpass('password:')
    else:
        print(platformStr, platform.version(), platform.machine())
        print('当前运行环境不支持')
    return username, password, worker


def start_action():  # windows功能入口
    print('release:v1.11.1')
    print(
        '程序功能如下：\n'
        '1.在线配置检查（根据keyWords.txt里的关键字）\n'
        '2.采集配置文件状态检查\n'
        '3.下发配置\n'
        '4.配置下发验证比对（预期 vs 采集）')
    while True:
        if 'Linux' in platform.system():
            import sys
            functionSelect = sys.argv[3]
        else:
            functionSelect = input('请选择执行的功能(输入数字):')
        if functionSelect == '1':
            fileName = 'devices_ip.xlsx'
            title = ['IP', 'Description', 'PingStatus(ms)', 'accessMode']  # 保存的sheet标题
            readInfo = readTxt('read/keyWords.txt')  # 读取匹配关键字用作title
            for i in readInfo:  # 更新title
                if i.split(',')[1] not in title:
                    title.append(i.split(',')[1])
            savename = 'checkConfig'
            print('1).确认IP等信息已填入read\devices_ip.xlsx\n'
                  '2).确认检查关键字已填入read\keyWords.txt\n'
                  '3).输入账户,密码')
            from checkConfig import deviceCheck
            username, password, worker = platform_select()
            data = funcAction(deviceCheck, savename, fileName=fileName,
                              user=username, passwd=password, worker=worker)
            writeToExcel(savename, title, data)
            break
        if functionSelect == '2':  # 配置检查+状态采集
            from cfgCheck import deviceCheck, get_check_title
            title = get_check_title()
            savename = '状态检查结果'
            data = funcAction(deviceCheck, savename, data=oringinDataFormat(), worker=10)
            writeToExcel(savename, title, data)
            break
        if functionSelect == '3':
            fileName = 'devices_ip.xlsx'
            title = ['IP', 'Description', 'PingStatus(ms)', 'accessMode', 'result']  # 保存的sheet标题
            savename = 'sendCmd'
            print('1).确认IP等信息已填入read\devices_ip.xlsx\n'
                  '3).输入账户,密码')
            from sendCmd import deviceSend
            username, password, worker = platform_select()
            data = funcAction(deviceSend, savename, fileName=fileName,
                              user=username, passwd=password, worker=worker)
            writeToExcel(savename, title, data)
            break
        if functionSelect == '4':
            from compare_configs import main as compare_main
            compare_main()
            break
        else:
            print('输入错误请重新输入')


if __name__ == '__main__':
    start_action()
    # oringinDataFormat()
# 打包命令pyinstaller -F -i images\favicon.ico .\main.py -n win_x64_main --collect-all grapheme --clean
