#!/usr/bin/python3
# -*- coding: utf-8 -*-
from interface import excel, logg, autoThreadingPool, init, set_value, get_value, readTxt
import platform, time
from alive_progress import alive_bar
import os


# import encodings.idna  # 解决python3.9 LookupError: unknown encoding: idna socket.gethostbyname(destination)
# pyinstaller打包后出错 python3.10已解决这个bug

def funcAction(user, passwd, fileName, logName, func, worker=30):  # 主模块
    global Rlock_local, logger, bar  # 锁，日志，进度条
    with alive_bar(title='Progress', bar='filling', spinner='waves2', unknown='wait', manual=True) as bar:  # 进度条
        init()  # 初始化全局变量
        set_value('logger', logg(logName, 'log/%s' % logName))
        set_value('bar', bar)
        file = fileName  # 读取文件名
        file_dir = 'read/%s' % file
        read = excel(file_dir)
        logger = get_value('logger')
        bar = get_value('bar')
        logger.get_log().info('当前运行环境:%s %s %s' % (platform.system(), platform.version(), platform.machine()))
        bar(0.05)
        try:
            read_info = read.excel_read()
            logger.get_log().info('读取 \'%s\' 成功,数量:%d' % (file, len(read_info)))
        except Exception as e:
            logger.get_log().error('读取 \'%s\' 失败:%s' % (file, e))
            bar(1)
            return
        bar(0.06)
        username = user
        password = passwd
        bar(0.07)
        for readCell in read_info:
            readCell.insert(0, password)
            readCell.insert(0, username)
        bar(0.1)
        logger.get_log().info('%s 载入线程...' % func.__name__)
        my_poll = autoThreadingPool(int(worker))
        result = my_poll(func, read_info)
        logger.get_log().info('线程结束,准备写入本地...')
        bar(1)
        return result


def funcAction1(fileName, logName, func, worker=30):  # 主模块
    global Rlock_local, logger, bar  # 锁，日志，进度条
    with alive_bar(title='Progress', bar='filling', spinner='waves2', unknown='wait', manual=True) as bar:  # 进度条
        init()  # 初始化全局变量
        set_value('logger', logg(logName, 'log/%s' % logName))
        set_value('bar', bar)
        logger = get_value('logger')
        bar = get_value('bar')
        file_dir = 'read/config'
        all_items = os.listdir(file_dir)
        read_info = []
        for item in all_items:
            read_info.append('read/config/%s'%item)
        # print(read_info)
        logger.get_log().info('当前运行环境:%s %s %s' % (platform.system(), platform.version(), platform.machine()))
        bar(0.1)
        logger.get_log().info('%s 载入线程...' % func.__name__)
        my_poll = autoThreadingPool(int(worker))
        result = my_poll(func, read_info)
        logger.get_log().info('线程结束,准备写入本地...')
        bar(1)
        return result


def writeToExcel(filename, title, data):  # 写入数据到excel
    filename_local = 'data/%s' % filename
    title_local = title
    data_local = data
    write_info = excel(filename_local)
    try:
        write_info.excel_write(title_local, data_local)
        basename = write_info.save_file()
        logger.get_log().info('文件 %s 写入完成,保存至data目录下' % basename)
    except Exception as e:
        logger.get_log().error('文件写入失败,%s' % e)


def writeToTXT(data):  # 写入数据到TXT
    data_local = data
    timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    try:
        for data_unit in data_local:
            with open('data/%s_%s_%s.log' % (data_unit[0], data_unit[1], timeNow), 'w') as f:
                f.write(data_unit[2])
    except Exception as e:
        logger.get_log().error('文件写入失败,%s %s' % (e, Exception))
        return
    logger.get_log().info('文件写入完成,保存至data目录下')


def platform_select():  # 判断当前运行环境
    username = ''
    password = ''
    worker = 60
    if 'Windows' in platform.system():
        from interface import passwdinput
        username = input('用户:')
        password = passwdinput('密码:')
    elif 'Linux' in platform.system():
        import sys
        username, password, worker = sys.argv[1], sys.argv[2], sys.argv[4]
    else:
        print(platform.system(), platform.version(), platform.machine())
        print('当前运行环境不支持')
    return username, password, worker


def start_action():  # windows功能入口
    print('release:v1.8.2')
    print(
        '程序功能如下：\n'
        '1.登陆配置检查（根据keyWords.txt里的关键字）\n'
        '2.已获得配置文件检查\n')
        # '3.下发配置\n'
        # '4.获取所有配置（current-configuration）\n'
        # '5.zabbix监控项导入\n'
        # '6.配置采集（根据keyWords.txt里的正则表达式匹配）')
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
            data = funcAction(username, password, fileName, savename, deviceCheck, worker)
            writeToExcel(savename, title, data)
            break
        if functionSelect == '2':  # 配置比对
            fileName = 'devices_ip.xlsx'
            title = ['IP']  # 保存的sheet标题
            readInfo = readTxt('read/keyWords.txt')  # 读取匹配关键字用作title
            for i in readInfo:  # 更新title
                if i.split(',')[1] not in title:
                    title.append(i.split(',')[1])
            savename = 'compareResult'
            print('1).需要比对的read\devices_ip.xlsx\n'
                  '2).确认检查关键字已填入read\keyWords.txt\n'
                  '3).输入账户,密码')
            from cfgCheck import deviceCheck
            data = funcAction1(fileName, savename, deviceCheck, 10)
            writeToExcel(savename, title, data)
            break
        else:
            print('输入错误请重新输入')


def spidertest(args):
    n = 0
    while True:
        n += 1
        print(n)
        time.sleep(1)


if __name__ == '__main__':
    start_action()
# 打包命令pyinstaller -F -i images\favicon.ico .\main.py -n win_x64_main  --collect-all grapheme --clean
