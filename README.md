# 网络设备配置检查工具

用于对网络设备配置文件（.log）进行自动化合规检查，生成 Excel 报告。

## 功能

1. **配置检查** — 对 read/config/ 目录下的 .log 配置文件，按设备类型逐项检查合规项
2. **在线检查** — 通过 SSH/Telnet 登录设备，读取配置并实时检查
3. **命令下发** — 批量登录设备下发配置命令
4. **版本补丁对照** — 采集版本/补丁号，与本地 Excel 对照表比对

## 项目结构

```
mywork_script/
├── main.py                 # 入口，功能菜单
├── cfgCheck.py             # 离线配置文件检查（合规性审计）
├── checkConfig.py          # 在线配置检查
├── compare_configs.py      # 配置比对工具
├── sendCmd.py              # 命令下发
├── mergeExcel.py           # 巡检报告汇总
├── config/
│   ├── __init__.py
│   └── check_items.py      # 检查项名称 & 设备类型配置表
├── interface/
│   ├── connection.py       # 交换机登录、Excel 处理
│   ├── public_env.py       # 全局变量、日志、线程池
│   ├── bitFunctions.py     # 网段计算
│   └── splitSubnet.py
├── log/                    # 运行日志
├── read/
│   ├── config/             # 离线配置文件 (.log)
│   ├── config_intended/    # 预期配置（用于比对）
│   ├── template/           # 配置模板
│   ├── 版本补丁.xlsx       # 版本补丁推荐对照表
│   ├── keyWords.txt        # 在线检查关键字
│   ├── ignore_rules.yaml   # 配置比对忽略规则
│   └── devices_ip.xlsx     # 设备 IP 清单
└── data/                   # 输出目录（Excel 报告）
```
## 运行

```bash
cd mywork_script
.venv/bin/python main.py
```

菜单：
- 1 — 在线配置检查
- 2 — 离线配置文件检查（主要功能）
- 3 — 下发配置
- 4 — 配置下发验证（比对原始 .cfg vs 采集 .log）