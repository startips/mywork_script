#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
compare_configs.py - 网络设备配置下发验证比对工具

功能：
  将原始配置（.cfg）与局点采集的配置（.log）进行对比，
  检测"我配了但局点没刷上去"的差异，过滤三类假阳性差异后输出报告。

使用方式：
  1. 将你出的 .cfg 原始配置文件放入 read/config_intended/
  2. 局点采集的 .log 文件放 read/config/
  3. 运行: python3 compare_configs.py
  4. 报告输出到 log/ 目录

工作流程：
  文件匹配 → 截取配置段 → 告警检查 → 三层过滤 → 逐行比对 → 出报告
"""

import os
import re
import glob
from datetime import datetime

# ============================================================
# 全局路径配置（根据需要修改这里）
# ============================================================
CFG_DIR = os.path.join(os.path.dirname(__file__), 'read', 'config_intended')
LOG_DIR = os.path.join(os.path.dirname(__file__), 'read', 'config')
REPORT_DIR = os.path.join(os.path.dirname(__file__), 'data')
IGNORE_RULES_FILE = os.path.join(os.path.dirname(__file__), 'read', 'ignore_rules.yaml')

# ============================================================
# 第一层过滤：硬编码噪音行（始终启用，不参与任何比对）
# 2026-05-18：噪音规则已统一迁移到 ignore_rules.yaml 的 noise 节
# 代码中不再保留硬编码列表
# ============================================================
HARDCODED_NOISE_PATTERNS = [
    # 保留极少的"一定不能参与比对"的边界行
    r'^return$',  # 配置段边界标记
]


def _load_ignore_rules():
    """
    加载 ignore_rules.yaml 中的过滤规则。

    规则文件分两部分：
      ignore_missing — .cfg 里有但 .log 里没有时，不报"缺失"
      ignore_extra   — .log 里有但 .cfg 里没有时，不报"多余"

    每条规则支持两种格式：
      1. 简单字符串（旧格式）：对所有设备生效
         "undo private-4-byte-as enable"

      2. 字典（新格式）：带型号/版本约束条件
         - pattern: "lldp enable"
           models: ["S5731"]           # 可选：仅匹配的型号
           versions: ["V200R024.*"]    # 可选：仅匹配的版本（正则）

    返回：
        dict: {
            'ignore_missing': [解析后的规则字典列表],
            'ignore_extra':   [解析后的规则字典列表],
            'noise':          [解析后的规则字典列表],
        }
        每条规则字典：{'pattern': 正则字符串, 'models': [型号列表]或None, 'versions': [版本模式]或None}
        文件不存在或解析失败时返回空规则。
    """
    result = {'ignore_missing': [], 'ignore_extra': [], 'noise': []}
    if not os.path.exists(IGNORE_RULES_FILE):
        return result

    def _parse_rules(raw_list):
        """将 YAML 原始列表解析为统一格式的规则字典列表"""
        parsed = []
        for item in raw_list:
            if isinstance(item, str):
                # 旧格式：简单字符串 → 转为 dict，无约束
                parsed.append({
                    'pattern': item,
                    'models': None,
                    'versions': None
                })
            elif isinstance(item, dict):
                # 新格式：字典带约束
                parsed.append({
                    'pattern': item.get('pattern', ''),
                    'models': item.get('models'),
                    'versions': item.get('versions')
                })
        return parsed

    try:
        import yaml
        with open(IGNORE_RULES_FILE, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
        if rules:
            result['ignore_missing'] = _parse_rules(rules.get('ignore_missing', []))
            result['ignore_extra'] = _parse_rules(rules.get('ignore_extra', []))
            result['noise'] = _parse_rules(rules.get('noise', []))
    except Exception as e:
        print(f"[WARN] 加载 ignore_rules.yaml 失败: {e}")
    return result


def _normalize_password(line):
    """
    密码归一化：将密码/密文替换为统一占位符 <PASSWORD>。

    华为交换机在不同场景下密码格式不同：
    - .cfg 里可能是明文
    - .log 里是加密串 $1c$... 或 %^%#...#%^%

    如果不归一化，同一个配置会因为密码值不同而被当成差异。

    参数：
        line: 原始配置行

    返回：
        str — 密码被替换为 <PASSWORD> 的行
    """
    # 匹配各种密码字段：password cipher / irreversible-cipher / %^%# 等
    line = re.sub(
        r'(password (?:cipher|irreversible-cipher|simple))\s+\S+',
        r'\1 <PASSWORD>',
        line
    )
    # snmp community read/write cipher
    line = re.sub(
        r'(snmp-agent community (?:read|write) cipher)\s+\S+',
        r'\1 <PASSWORD>',
        line
    )
    # authentication-mode hmac-sha256 password 或 set authentication password cipher
    line = re.sub(
        r'(set authentication password cipher)\s+\S+',
        r'\1 <PASSWORD>',
        line
    )
    line = re.sub(
        r'(authentication-mode\s+\S+\s+password)\s+\S+',
        r'\1 <PASSWORD>',
        line
    )
    return line


# SSH 密码套件/算法列表的前缀集合
# 这些配置行后面的算法列表在 .cfg 和 .log 中顺序可能不同，
# 需要做无序集合比较（排序后比对）而不是逐行逐串比对。
_SET_COMPARABLE_PREFIXES = [
    'ssh server cipher', 'ssh client cipher',
    'ssh server hmac', 'ssh client hmac',
    'ssh server key-exchange', 'ssh client key-exchange',
    'ssh server publickey', 'ssh server dh-exchange',
]


def _normalize_set_line(line):
    """
    对密码套件类配置行进行集合归一化。

    SSH 密码套件（如 ssh server cipher AES256-CBC AES128-CBC）的算法顺序
    在 .cfg 和 .log 中可能不同。将算法列表按字母排序后，相同的集合
    会产生相同的字符串，从而被正确匹配。

    参数：
        line: 配置行文本

    返回：
        str — 算法列表已排序后的行（非密码套件行原样返回）
    """
    line_lower = line.lower().strip()
    for prefix in _SET_COMPARABLE_PREFIXES:
        if line_lower.startswith(prefix):
            # 提取算法部分：去掉前缀，取后面的所有单词
            algo_part = line[len(prefix):].strip()
            algorithms = sorted(algo_part.split())
            return prefix + ' ' + ' '.join(algorithms)
    return line


def _is_noise(line, noise_patterns):
    """
    判断某一行是否为噪音行（不应参与比对的自动生成行）。

    参数：
        line: 配置行文本（已去除首尾空白）
        noise_patterns: 噪音正则表达式列表

    返回：
        bool — True 表示是噪音，应忽略
    """
    for pattern in noise_patterns:
        if re.match(pattern, line, re.IGNORECASE):
            return True
    return False


def _is_ignored(line, ignore_rules, device_info=None):
    """
    判断某一行是否匹配忽略规则（支持型号/版本约束）。

    参数：
        line: 配置行文本
        ignore_rules: 规则字典列表，每条含 pattern/models/versions
        device_info: 设备信息 dict，含 model 和 version（可选，为 None 时不检查约束）

    返回：
        bool — True 表示应忽略
    """
    for rule in ignore_rules:
        # 先检查 pattern 是否匹配行内容
        if not re.search(rule['pattern'], line, re.IGNORECASE):
            continue

        # pattern 匹配了，再检查约束条件
        # 如果 device_info 为 None，表示无设备信息，跳过约束检查（后向兼容）
        if device_info is not None:
            # 检查型号约束：如果 rule 指定了 models，当前设备型号必须匹配
            if rule['models']:
                if not device_info.get('model'):
                    continue  # 没型号信息，不应用此规则
                if not any(re.search(m, device_info['model'], re.IGNORECASE)
                           for m in rule['models']):
                    continue  # 型号不匹配

            # 检查版本约束：如果 rule 指定了 versions，当前版本必须匹配
            if rule['versions']:
                if not device_info.get('version'):
                    continue  # 没版本信息，不应用此规则
                if not any(re.search(v, device_info['version'], re.IGNORECASE)
                           for v in rule['versions']):
                    continue  # 版本不匹配

        # 所有约束都通过 → 此规则生效
        return True

    return False


def _strip_ip_prefix(filename):
    """
    去掉 .log 文件名开头的 IP 前缀。

    局点采集的文件名格式：IP_设备名.log（如 12.255.190.206_SZBL1D4FC01U31-DCN-DC1_BMC-ACC.log）
    原始配置文件名格式：设备名.cfg（如 SZBL1D4FC01U31-DCN-DC1_BMC-ACC.cfg）

    只有去掉 IP 前缀后才能配对。

    参数：
        filename: 原始文件名（含扩展名）

    返回：
        str — 去掉 IP 前缀后的文件名（保留扩展名）
    """
    # 匹配开头是 IP 地址（xxx.xxx.xxx.xxx_）的模式
    m = re.match(r'^\d+\.\d+\.\d+\.\d+_(.+)$', filename)
    if m:
        return m.group(1)
    return filename


def _extract_device_info(text):
    """
    从配置文件文本中提取设备型号和 VRP 版本号。

    提取规则与 cfgCheck.py 保持一致：
      - 型号：   r'HUAWEI (\S+) (?:Routing Switch)?\s*uptime is'
      - 版本：   r'Version \S+ \((\S+ \S+)\)'

    参数：
        text: 配置文件完整文本（.cfg 或 .log 均可）

    返回：
        dict: {
            'model': 设备型号（如 'S5731-S48T4X'）或 None,
            'version': 版本号全串（如 'S5731 V200R024C00SPC500'）或 None
        }
    """
    info = {'model': None, 'version': None}

    # 提取设备型号（同 cfgCheck.py._get_device_model）
    # 示例：HUAWEI S5731-S48T4X Routing Switch uptime is ...
    #        HUAWEI CE8860-4C-EI uptime is ...
    m = re.search(r'HUAWEI (\S+) (?:Routing Switch)?\s*uptime is', text, re.IGNORECASE)
    if m:
        info['model'] = m.group(1)

    # 提取版本号（同 cfgCheck.py._check_version）
    # 示例：Version 5.170 (S5731 V200R024C00SPC500)
    #        Version 8.191 (CE8860EI V200R019C10SPC800)
    match_list = re.findall(r'Version \S+ \(\S+ (\S+)\)', text)
    if match_list:
        info['version'] = match_list[0]
    else:
        # 兜底：从 .cfg 文件头注释提取（格式：!Software Version V200R024C00SPC500）
        m = re.search(r'Software\s+Version\s+(\S+)', text)
        if m:
            info['version'] = m.group(1)

    return info


def _extract_config_section(log_lines):
    """
    从 .log 文件中提取 display current-configuration 的输出部分。

    .log 文件包含多个命令的输出，只有 current-configuration 部分
    是完整的配置，其他（display interface brief, display version 等）
    不应该参与配置比对。

    提取规则：
      从包含 "display current-configuration" 的行下一行开始，
      到第一次独立出现的 "return" 行结束。

    注意：
      - 有些设备采集命令带 "| no" 后缀（如 display current-configuration | no）
      - 部分配置内部（如 route-policy）也有 "return" 关键字，但不会是独立一行
      - 所以要匹配的是 "return" 单独一行，而非包含 return 的行

    参数：
        log_lines: .log 文件的所有行（字符串列表）

    返回：
        list[str] — 配置段文本行，不含首尾空行
    """
    lines = [line.rstrip('\r\n') for line in log_lines]
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # 找到 display current-configuration 命令行的位置（可能有 | no 后缀）
        if stripped.startswith('display current-configuration'):
            start_idx = i + 1  # 从命令的下一行开始
        # 找到独立的 return 行（不是配置内部的 return）
        # 注意：有些 .log 文件在 return 后还有第二段有 "return" 关键字，
        # 所以必须找第一次出现的独立 return 行
        if stripped == 'return' and start_idx is not None:
            end_idx = i
            break

    if start_idx is None:
        return []
    if end_idx is None or end_idx <= start_idx:
        # 没找到 return，试试下一对
        # 或者 return 在 start 之前（跨段了）
        end_idx = len(lines)

    config = lines[start_idx:end_idx]
    # 去掉首尾空行
    while config and config[0].strip() == '':
        config = config[1:]
    while config and config[-1].strip() == '':
        config = config[:-1]
    return config


def _clean_line(line):
    """
    清洗单行配置：去首尾空白 + 密码归一化。

    参数：
        line: 原始配置行

    返回：
        str — 清洗后的行
    """
    line = line.strip()
    line = _normalize_password(line)
    return line


def _is_relevant_line(line):
    """
    判断一行是否是"有意义"的配置行（不是空行、分隔符、注释行）。

    参数：
        line: 配置行

    返回：
        bool — True 表示是有效配置行
    """
    if not line:
        return False
    if line == '#':
        return False
    if line.startswith('!'):
        return False
    return True


def _compare_configs(cfg_lines, log_lines, rules, device_info=None):
    """
    核心比对逻辑：逐行比对原始配置 vs 采集配置。

    流程：
      1. 两边都清洗（去空白、归一化密码）
      2. 去掉噪音行（硬编码模式）
      3. 去掉规则匹配的行
         - ignore_missing 模式在两边都过滤（配了不回显的命令，两边都不参与比对）
         - ignore_extra 模式只在 log 侧过滤（设备自动生成的，不报多余）
      4. 大小写归一化后逐行匹配
      5. .cfg 有但 .log 没有 → "缺失"（重点关注）
      6. .log 有但 .cfg 没有 → "多余"（辅助参考）

    参数：
        cfg_lines: .cfg 文件的所有行
        log_lines: .log 文件中提取的配置段
        rules: ignore_rules.yaml 解析结果
        device_info: 设备信息 dict，用于按型号/版本过滤规则（可选）

    返回：
        tuple: (missing_items, extra_items)
            missing_items: [(行号, 内容), ...] — cfg 缺了这些
            extra_items:   [(行号, 内容), ...] — log 多了这些
    """
    # 第一轮：清洗 + 过滤
    cleaned_cfg = []
    for i, line in enumerate(cfg_lines):
        cl = _clean_line(line)
        if not _is_relevant_line(cl):
            continue
        # noise 在两边都过滤（自动生成的噪音，不参与比对）
        if _is_ignored(cl, rules.get('noise', []), device_info):
            continue
        # ignore_missing 在两边都过滤（这些命令不可靠参与比对）
        if _is_ignored(cl, rules.get('ignore_missing', []), device_info):
            continue
        # 对密码套件类配置做集合归一化（排序算法列表）
        cl = _normalize_set_line(cl)
        cleaned_cfg.append((i + 1, cl))

    cleaned_log = []
    for i, line in enumerate(log_lines):
        cl = _clean_line(line)
        if not _is_relevant_line(cl):
            continue
        # noise 在两边都过滤（自动生成的噪音，不参与比对）
        if _is_ignored(cl, rules.get('noise', []), device_info):
            continue
        # ignore_missing 在 log 侧也过滤（两边都不参与比对）
        if _is_ignored(cl, rules.get('ignore_missing', []), device_info):
            continue
        # ignore_extra 只在 log 侧过滤（这些是设备自动生成，不报多余）
        if _is_ignored(cl, rules.get('ignore_extra', []), device_info):
            continue
        # 对密码套件类配置做集合归一化（排序算法列表）
        cl = _normalize_set_line(cl)
        cleaned_log.append((i + 1, cl))

    # 建立 log 行的大小写归一化哈希表（用于快速查找）
    # key: 全小写的行内容, value: [原始行列表]
    log_lower_map = {}
    for lineno, line in cleaned_log:
        key = line.lower()
        log_lower_map.setdefault(key, []).append((lineno, line))
    # 比对：.cfg 有的，看看 .log 有没有（大小写不敏感）
    missing = []
    for lineno, line in cleaned_cfg:
        key = line.lower()
        if key not in log_lower_map:
            missing.append((lineno, line))
        else:
            # 匹配到的从 log_map 中移除，避免同一个 log 行匹配多个 cfg 行
            # 但只在完全匹配时才移除（防误伤）
            if log_lower_map[key]:
                log_lower_map[key].pop(0)
                if not log_lower_map[key]:
                    del log_lower_map[key]

    # log 剩余的行就是"多余"的
    extra = []
    for key, entries in log_lower_map.items():
        for lineno, line in entries:
            extra.append((lineno, line))

    return missing, extra


def _get_device_name(filepath):
    """
    从文件路径中提取设备名（去掉扩展名和 IP 前缀）。

    参数：
        filepath: 文件路径

    返回：
        str — 设备名
    """
    basename = os.path.basename(filepath)
    name, _ = os.path.splitext(basename)
    # 如果是 .log 文件，去掉 IP 前缀
    name = _strip_ip_prefix(name + '.')  # hack: 加后缀让正则匹配
    name = name[:-1]  # 去掉加上的后缀
    return name


def main():
    """
    主函数：执行完整的配置比对流程。

    流程：
      1. 加载 ignore_rules.yaml
      2. 扫描 config_intended/ 获取 .cfg 文件列表
      3. 扫描 config/ 获取 .log 文件列表
      4. 建立 设备名→文件 的映射
      5. 逐个设备执行比对
      6. 生成报告
    """
    print("=" * 60)
    print("  网络设备配置下发验证比对工具")
    print("=" * 60)

    # 加载规则
    rules = _load_ignore_rules()
    print(f"\n[INFO] 加载忽略规则: ignore_missing={len(rules['ignore_missing'])}条, ignore_extra={len(rules['ignore_extra'])}条, noise={len(rules['noise'])}条")

    # 扫描目录
    cfg_files = glob.glob(os.path.join(CFG_DIR, '*.cfg'))
    log_files = glob.glob(os.path.join(LOG_DIR, '*.log'))

    print(f"[INFO] 原始配置(.cfg): {len(cfg_files)} 个文件")
    print(f"[INFO] 采集配置(.log): {len(log_files)} 个文件")

    if not cfg_files:
        print(f"\n[ERROR] config_intended/ 目录下没有 .cfg 文件！")
        print(f"        请将你的原始配置文件放到: {CFG_DIR}")
        print(f"        文件命名格式: 设备名.cfg（如 SZBL1D4FC01U31-DCN-DC1_BMC-ACC.cfg）")
        return

    if not log_files:
        print(f"\n[ERROR] read/config/ 目录下没有 .log 文件！")
        return

    # 建立 设备名→文件路径 映射
    cfg_map = {}   # 设备名 → .cfg 路径
    for f in cfg_files:
        name = _get_device_name(f)
        cfg_map[name] = f

    log_map = {}   # 设备名 → .log 路径
    for f in log_files:
        name = _get_device_name(f)
        log_map[name] = f

    # 开始比对
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_lines = []
    total_devices = 0
    clean_devices = []
    diff_devices = []
    no_log_devices = []
    device_infos = {}  # 设备名 → device_info（型号+版本）

    report_lines.append("=" * 70)
    report_lines.append(f"  配置下发验证比对报告  {timestamp}")
    report_lines.append("=" * 70)
    report_lines.append("")
    report_lines.append(f"  原始配置目录: {CFG_DIR}")
    report_lines.append(f"  采集配置目录: {LOG_DIR}")
    report_lines.append(f"  忽略规则文件: {IGNORE_RULES_FILE}")
    report_lines.append("")

    # 遍历每个 .cfg 文件，找对应的 .log 做比对
    for idx, dev_name in enumerate(sorted(cfg_map.keys()), 1):
        total_devices += 1
        cfg_path = cfg_map[dev_name]

        if dev_name not in log_map:
            no_log_devices.append(dev_name)
            print(f"  [{idx}/{len(cfg_map)}] {dev_name} — ⚠ 未找到对应 .log 文件")
            continue

        log_path = log_map[dev_name]
        print(f"  [{idx}/{len(cfg_map)}] {dev_name} — 正在比对...", end='')

        # 读取 .cfg
        with open(cfg_path, 'r', encoding='utf-8', errors='replace') as f:
            cfg_lines = f.readlines()

        # 读取 .log
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            log_all_text = f.read()
            log_all_lines = log_all_text.split('\n')

        # 从 .log 中提取配置段
        log_config_lines = _extract_config_section(log_all_lines)
        if not log_config_lines:
            report_lines.append(f"\n  ⚠ {dev_name} — 未从 .log 中找到配置段")
            diff_devices.append(dev_name)
            continue

        # 从 .log 提取设备型号和版本（用于型号/版本差异化规则过滤）
        device_info = _extract_device_info(log_all_text)
        device_infos[dev_name] = device_info

        # 执行比对（传入 device_info 支持差异化规则）
        missing, extra = _compare_configs(cfg_lines, log_config_lines, rules, device_info)

        # 输出该设备的结果（仅屏幕提示，具体差异写报告）
        if not missing and not extra:
            clean_devices.append(dev_name)
            print(f"✅ 一致")
        else:
            diff_devices.append(dev_name)
            print(f"⚠ 有差异 (缺失{len(missing)}条, 多余{len(extra)}条)")
            report_lines.append(f"\n{'─' * 70}")
            # 设备名后附型号和版本
            model_str = device_info.get('model') or '未知型号'
            ver_str = device_info.get('version') or '未知版本'
            report_lines.append(f"  {dev_name}  [{model_str}]  [{ver_str}]")
            report_lines.append(f"{'─' * 70}")

            if missing:
                report_lines.append(f"  [缺失] .cfg 有配置但设备上没找到（共 {len(missing)} 条）:")
                for lineno, line in missing:
                    short = line if len(line) <= 100 else line[:97] + '...'
                    report_lines.append(f"    - (cfg第{lineno}行) {short}")

            if extra:
                report_lines.append(f"  [多余] 设备上有但 .cfg 里没有（共 {len(extra)} 条）:")
                for lineno, line in extra[:20]:  # 多余项最多显示20条
                    short = line if len(line) <= 100 else line[:97] + '...'
                    report_lines.append(f"    + (log第{lineno}行) {short}")
                if len(extra) > 20:
                    report_lines.append(f"    ... 还有 {len(extra) - 20} 条（已截断）")

    # ----- 汇总 -----
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("  汇总")
    report_lines.append("=" * 70)
    report_lines.append(f"  共检查 {total_devices} 台设备")
    report_lines.append(f"  完全一致:   {len(clean_devices)} 台 ✓")
    report_lines.append(f"  存在差异:   {len(diff_devices)} 台 ✗")
    report_lines.append(f"  未采集:     {len(no_log_devices)} 台 ⚠")

    if clean_devices:
        report_lines.append(f"\n  配置一致设备列表:")
        for d in clean_devices:
            info = device_infos.get(d, {})
            m = info.get('model') or ''
            v = info.get('version', '')[:30]  # 版本全串太长，截取后30字符
            report_lines.append(f"    ✓ {d}  [{m}]  [{v}]")

    if diff_devices:
        report_lines.append(f"\n  存在差异设备列表:")
        for d in diff_devices:
            info = device_infos.get(d, {})
            m = info.get('model') or ''
            v = info.get('version', '')[:30]
            report_lines.append(f"    ✗ {d}  [{m}]  [{v}]")

    if no_log_devices:
        report_lines.append(f"\n  未采集（仅有 .cfg 无对应 .log）: {len(no_log_devices)} 台")

    # 输出汇总到屏幕（具体差异内容见报告文件）
    print()
    print(f"  {'='*40}")
    print(f"  比对完成：共 {total_devices} 台设备")
    print(f"  完全一致 {len(clean_devices)} 台 | 存在差异 {len(diff_devices)} 台 | 未采集 {len(no_log_devices)} 台")
    print(f"  {'='*40}")

    # 写入文件
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_filename = os.path.join(REPORT_DIR, f'配置比对报告_{timestamp}.txt')

    # 清理旧报告（只保留最新的5份）
    old_reports = sorted(glob.glob(os.path.join(REPORT_DIR, '配置比对报告_*.txt')))
    while len(old_reports) > 5:
        os.remove(old_reports.pop(0))

    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\n[OK] 报告已保存: {report_filename}")


if __name__ == '__main__':
    main()
