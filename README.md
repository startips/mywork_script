# 🔧 NetOps Tools

> 网络运维自动化工具集 —— 让繁琐的配置检查和数据处理变得轻松高效

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)

---

## ✨ 项目亮点

- **🎯 一键批量操作** —— 支持多线程并发，告别重复劳动
- **📊 智能报表生成** —— 自动输出 Excel 报告，高亮显示异常项
- **🔍 灵活配置检查** —— YAML 驱动的检查规则，轻松扩展
- **📦 模块化设计** —— 公共模块复用，代码整洁易维护

---

## 📋 功能概览

### 🔧 工具一：网络设备配置检查（`main.py`）

| 功能 | 说明 | 适用场景 |
|------|------|----------|
| 在线配置检查 | SSH/Telnet 登录设备，按关键字匹配检查 | 日常巡检、安全审计 |
| 离线配置检查 | 对采集配置逐项合规审计（13项 + 线路检查） | 配置备份分析 |
| 下发配置 | 批量登录设备下发命令 | 批量配置变更 |
| 配置下发验证比对 | 预期配置 vs 采集配置差异分析 | 变更后验证 |
| 离线关键字配置检查 | 对 `read/config` 下的采集配置文件按关键字匹配检查 | 离线配置合规比对 |

**在线检查流程：**
```
读取设备清单 → Ping 检测 → SSH/Telnet 登录
→ 执行 display current-configuration → 关键字匹配
→ 生成 Excel 报告（自动高亮异常）
```

### 📊 工具二：巡检数据处理（`mergeExcel.py`）

| 功能 | 说明 | 适用场景 |
|------|------|----------|
| 提取 Excel 并分片压缩 | 从巡检报告 ZIP 中提取目标 Excel | 报告归档 |
| 汇总原始数据 | 将各设备原始数据合并到总表 | 数据汇总分析 |
| 提取配置文件 | 从 ZIP 中提取配置文件并统一命名 | 配置备份管理 |
| 合并巡检资产数据 | 多维度资产数据合并（版本/SN/登录状态等） | 资产盘点 |

**数据处理流程：**
```
读取巡检报告 ZIP → 智能解压（编码自动修正）
→ 多线程并发处理 → 生成汇总报表
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- macOS / Linux / Windows

### 安装

```bash
# 克隆仓库
git clone https://github.com/startips/netops-tools.git
cd netops-tools

# 安装依赖
pip install -r requirements-mac.txt
```

### 运行

```bash
# 网络设备配置检查
python main.py

# 巡检数据处理
python mergeExcel.py
```

**💡 小技巧：** 巡检数据处理支持多选，输入 `134` 会依次执行功能1、3、4

---

## ⚙️ 配置文件

### `check_items.yaml` - 检查项配置

```yaml
check_items:        # 检查项列表
device_types:       # 各设备类型启用的检查项
device_patterns:    # 设备名匹配规则
cable_check:        # 线路检查排除规则
```

### `keyWords.txt` - 关键字规则

格式：`正则表达式,显示名称,检查类型`

| 检查类型 | 说明 |
|----------|------|
| `0` | 不应存在（匹配到则报"多余"） |
| `1` | 应存在（未匹配则报"缺少"） |

```bash
# 示例
telnet server disable,关闭Telnet,0
ntp server source-interface all disable,关闭NTP,1
```

---

## 📝 使用示例

### 场景1：批量设备配置合规检查

```bash
# 1. 准备设备清单 (devices_ip.xlsx)
# 2. 配置检查关键字 (keyWords.txt)
# 3. 运行检查
python main.py
# 选择功能 1 → 在线关键字检查
# 选择功能 2 → 离线状态检查
# 选择功能 5 → 离线关键字检查
```

### 场景2：巡检报告数据汇总

```bash
# 1. 将巡检报告 ZIP 放入 source_dir
# 2. 运行数据处理
python mergeExcel.py
# 输入 134 → 执行功能 1、3、4
```

---

## 🔧 核心模块特性

### Excel 处理 (`excel_handler.py`)

- ✅ 多 Sheet 写入，每个 Sheet 独立控制高亮
- ✅ 支持按序号或名称读取 Sheet
- ✅ 自动时间戳命名
- ✅ 高亮开关（默认关闭）

### 线程池 (`thread_pool.py`)

- ✅ 按提交顺序返回结果
- ✅ 异常任务保留位置（返回 None）
- ✅ 支持进度条回调
- ✅ 多次调用自动重置

---

## 🐛 常见问题

**Q: 为什么连接设备失败？**
- 检查 Ping 是否可达
- 确认 SSH/Telnet 端口和凭证
- 查看日志文件排查详情

**Q: Excel 编码乱码？**
- 工具已自动处理 cp437 → gbk 编码转换
- 如遇特殊编码，检查源文件格式

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

<p align="center">
  <i>如果觉得有用，别忘了点个 ⭐ 支持一下！</i>
</p>
