#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
检查项 & 设备类型配置 — 从 read/check_items.yaml 加载

导出（与原 check_items.py 接口一致）：
    CHECK_ITEM_NAMES      — 检查项名称元组
    DEVICE_TYPE_CONFIGS   — {类型名: {检查项: 0/1}}
    DEVICE_TYPE_PATTERNS  — ((compiled_regex, 类型名), ...)
"""

import os
import sys
import yaml

# ============================================================
# 加载 YAML（兼容 PyInstaller 打包）
# ============================================================

if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.join(os.path.dirname(__file__), '..')

_yaml_path = os.path.join(_base_dir, 'read', 'check_items.yaml')

with open(_yaml_path, 'r', encoding='utf-8') as _f:
    _data = yaml.safe_load(_f)

# ============================================================
# CHECK_ITEM_NAMES — 检查项名称元组（固定顺序）
# ============================================================

CHECK_ITEM_NAMES = tuple(_data['check_items'])


# ============================================================
# 工厂函数：根据启用项列表生成完整 0/1 字典
# ============================================================

def _make_check_option(*enabled_items):
    enabled = set(enabled_items)
    return {name: (1 if name in enabled else 0) for name in CHECK_ITEM_NAMES}


# ============================================================
# DEVICE_TYPE_CONFIGS — {类型名: {检查项: 0/1}}
# ============================================================

DEVICE_TYPE_CONFIGS = {
    type_name: _make_check_option(*items)
    for type_name, items in _data['device_types'].items()
}


# ============================================================
# DEVICE_TYPE_PATTERNS — ((regex_string, 类型名), ...)
# ============================================================

DEVICE_TYPE_PATTERNS = tuple(
    (pattern, type_name)
    for pattern, type_name in _data['device_patterns']
)


# ============================================================
# CABLE_CHECK_CONFIG — 线路检查排除规则
# ============================================================

CABLE_CHECK_CONFIG = _data.get('cable_check', {})
