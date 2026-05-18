#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
配置检查项定义模块

使用方法：
    from config.check_items import DEVICE_TYPE_CONFIGS, DEVICE_TYPE_PATTERNS
    config = DEVICE_TYPE_CONFIGS['Spine']  # 获取 Spine 类型的检查项配置
    config['版本']  # => 1

新增/修改配置的方式：
    - 增检查项：CHECK_ITEM_NAMES 加名字 + 要检查的设备类型里加一行
    - 增设备类型：一个 _make_check_option() 调用 + 注册到两个导出表
"""

# ============================================================
# 所有检查项名称（固定顺序，与各设备类型的 0/1 值一一对应）
# 顺序与原有 returntype() 中列出的顺序一致
# ============================================================
CHECK_ITEM_NAMES = (
    '版本',                    # 交换机版本号
    '补丁',                    # 补丁版本
    '多余文件检查',             # flash中多余文件(.cc .pat .cfg)
    '硬件状态检查',             # 硬件在线/异常状态
    '未关闭端口',               # 是否存在down状态的端口未shutdown
    'bgp邻居状态',              # BGP邻居数量及状态
    'feature-software状态',     # 特性软件包激活状态
    '失败命令配置检查',          # 配置回滚的失败命令数量
    '设备Esn',                 # 设备ESN序列号
    '关闭FTP配置',              # 是否关闭FTP服务
    'mlag状态',                # M-LAG心跳/主备状态
    'mlag配置',                # DFS-group/M-LAG配置完整性
    '大路由配置',               # system resource large-route
    'NTP配置',                 # NTP服务器源接口关闭
    '全局vlan配置',             # vlan batch配置
    'mac飘移配置',              # MAC飘移检测配置
    'STP配置',                 # STP/RSTP基础配置
    'arp冲突配置',              # ARP冲突检测
    'telnet关闭配置',           # 关闭Telnet服务
    'vpn实例配置',              # OOB/DAD VPN实例
    'aaa配置',                 # AAA认证/授权/计费配置
    'BGP配置',                 # BGP邻居/路由策略
    'snmp配置',                # SNMP Agent配置
    'LLDP配置',                # LLDP使能
    'ssh配置',                 # SSH服务端/客户端加密配置
    'cmd权限配置',              # command-privilege命令权限
    'user-interface配置',      # VTY/CON口登录配置
    'hash配置',                # 负载均衡ECMP hash模式
    '带外接口配置',             # MEth带外管理接口
    'loopback配置',            # LoopBack1接口
    'peerlink配置',            # peer-link (Eth-Trunk100)
    'DAD配置',                 # DAD检测链路 (Eth-Trunk101)
    'monitor-link配置',        # monitor-link联动组
    '告警检查',                # display alarm active 活跃告警统计
)


def _make_check_option(*enabled_items):
    """
    生成完整的 checkOption 字典。

    工厂函数：传入所有 value=1 的检查项名称（可变参数），
    自动生成包含全部 34 项的完整字典，未传入的项默认为 0（不检查）。

    参数：
        enabled_items: 需要开启检查的项名称（与 CHECK_ITEM_NAMES 中的名字一致）

    返回：
        dict, e.g. {'版本': 1, '补丁': 1, 'mlag状态': 0, ...}

    用法示例：
        _make_check_option('版本', '补丁', 'NTP配置', 'ssh配置')
    """
    enabled = set(enabled_items)
    return {name: (1 if name in enabled else 0) for name in CHECK_ITEM_NAMES}


# ============================================================
# 设备类型配置表
# 每类设备只需列出 value=1（需要检查）的项，其余自动为 0（不检查/不涉及）
# 这样新增/修改设备类型时，只需增删项名称，一目了然
# ============================================================

# --- Spine (脊柱交换机) ---
# 匹配规则: 设备名包含 -S_(A|B|C|D)
SPINE_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'BGP配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    'loopback配置',
    '告警检查',
)

# --- Leaf (叶交换机) ---
# 匹配规则: 设备名包含 -LF\d+_(A|B|C|D)
LEAF_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    'mlag状态',
    'mlag配置',
    '大路由配置',
    'NTP配置',
    '全局vlan配置',
    'mac飘移配置',
    'STP配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'BGP配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    '带外接口配置',
    'peerlink配置',
    'DAD配置',
    'monitor-link配置',
    '告警检查',
)

# --- Slf (Super Leaf) ---
# 匹配规则: 设备名包含 -SLF\d+_(A|B|C|D)
SLF_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    'mlag状态',
    'mlag配置',
    '大路由配置',
    'NTP配置',
    '全局vlan配置',
    'mac飘移配置',
    'STP配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    '带外接口配置',
    'loopback配置',
    'peerlink配置',
    'DAD配置',
    'monitor-link配置',
    '告警检查',
)

# --- La (Leaf A系列?) ---
# 匹配规则: 设备名包含 -LA\d+_(A|B|C|D)
LA_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    'mlag状态',
    'mlag配置',
    '大路由配置',
    'NTP配置',
    '全局vlan配置',
    'mac飘移配置',
    'STP配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    '带外接口配置',
    'monitor-link配置',
    '告警检查',
)

# --- Pl (Police?) ---
# 匹配规则: 设备名包含 -PL_(A|B|C|D)
PL_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    '告警检查',
)

# --- Podlc ---
# 匹配规则: 设备名包含 -PODLC_(A|B|C|D)
PODLC_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    '告警检查',
)

# --- Gwlc (Gateway Leaf?) ---
# 匹配规则: 设备名包含 -GWLC_(A|B|C|D)
GWLC_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    '告警检查',
)

# --- Agg (汇聚交换机) ---
# 匹配规则: 设备名包含 -AGG_(A|B|C|D)
AGG_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    '告警检查',
)

# --- Nfvl (NFV Leaf?) ---
# 匹配规则: 设备名包含 -NFVL\d*_(A|B|C|D)
NFVL_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    '全局vlan配置',
    'mac飘移配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    '告警检查',
)

# --- Nfvw (NFV WAN?) ---
# 匹配规则: 设备名包含 -NFVW\d*_(A|B|C|D)
NFVW_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    '全局vlan配置',
    'mac飘移配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    '告警检查',
)

# --- Wc (WAC) ---
# 匹配规则: 设备名包含 -WC_(A|B|C|D)
WC_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    'hash配置',
    '带外接口配置',
    '告警检查',
)

# --- Fw (防火墙) ---
# 匹配规则: 设备名包含 -FW\d*_(A|B|C|D)
FW_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    'NTP配置',
    'mac飘移配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    '带外接口配置',
    '告警检查',
)

# --- S0 (Super Spine?) ---
# 匹配规则: 设备名包含 -SS_(A|B|C|D)
S0_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    '带外接口配置',
    'loopback配置',
    '告警检查',
)

# --- Other (未匹配到的其他类型) ---
# 当设备名不匹配任何已知类型时的兜底配置
OTHER_CONFIG = _make_check_option(
    '版本',
    '补丁',
    '多余文件检查',
    '硬件状态检查',
    '未关闭端口',
    'bgp邻居状态',
    'feature-software状态',
    '失败命令配置检查',
    '设备Esn',
    '关闭FTP配置',
    '大路由配置',
    'NTP配置',
    '全局vlan配置',
    'mac飘移配置',
    'STP配置',
    'arp冲突配置',
    'telnet关闭配置',
    'vpn实例配置',
    'aaa配置',
    'BGP配置',
    'snmp配置',
    'LLDP配置',
    'ssh配置',
    'cmd权限配置',
    'user-interface配置',
    '带外接口配置',
    'loopback配置',
    '告警检查',
)

# ============================================================
# 导出字典：类型名 -> 配置
# ============================================================
DEVICE_TYPE_CONFIGS = {
    'Spine': SPINE_CONFIG,
    'Leaf':  LEAF_CONFIG,
    'Slf':   SLF_CONFIG,
    'La':    LA_CONFIG,
    'Pl':    PL_CONFIG,
    'Podlc': PODLC_CONFIG,
    'Gwlc':  GWLC_CONFIG,
    'Agg':   AGG_CONFIG,
    'Nfvl':  NFVL_CONFIG,
    'Nfvw':  NFVW_CONFIG,
    'Wc':    WC_CONFIG,
    'Fw':    FW_CONFIG,
    'S0':    S0_CONFIG,
    'Other': OTHER_CONFIG,
}

# ============================================================
# 设备类型匹配模式（按优先级从高到低排列）
# 每个元素为 (regex_pattern, type_name)
# 用于 returntype() 中按顺序匹配设备名
# ============================================================
DEVICE_TYPE_PATTERNS = (
    (r'-S_(A|B|C|D)',      'Spine'),
    (r'-LF\d+_(A|B|C|D)',  'Leaf'),
    (r'-SLF\d+_(A|B|C|D)', 'Slf'),
    (r'-LA\d+_(A|B|C|D)',  'La'),
    (r'-PL_(A|B|C|D)',     'Pl'),
    (r'-PODLC_(A|B|C|D)',  'Podlc'),
    (r'-GWLC_(A|B|C|D)',   'Gwlc'),
    (r'-AGG_(A|B|C|D)',    'Agg'),
    (r'-NFVL\d*_(A|B|C|D)','Nfvl'),
    (r'-NFVW\d*_(A|B|C|D)','Nfvw'),
    (r'-WC_(A|B|C|D)',     'Wc'),
    (r'-FW\d*_(A|B|C|D)',  'Fw'),
    (r'-SS_(A|B|C|D)',     'S0'),
)
