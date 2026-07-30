#!/usr/bin/env python3
"""
自动化：网络设备配置生成 Web 平台（NiceGUI）
流程：连接 L2TP VPN → 打开页面 → 配置生成 → 上传 Excel → 勾选 ZIP
      → 开始生成 → 识别日志框报错 → 无错才下载 ZIP → 解压到 read/config_intended

用法:
  python generate_config_web.py /path/to/params.xlsx
  python generate_config_web.py /path/to/params.xlsx --vpn 配置服务器
  python generate_config_web.py /path/to/params.xlsx --no-vpn   # 不连/不关 VPN
  python generate_config_web.py /path/to/params.xlsx --headed --slow 200

下载默认目录: /Users/shadowx/Documents/招行/配置生成/原始配置
文件名: Excel文件名_YYYYMMDD.zip（如 网络设备参数_20260714.zip），重名覆盖
下载成功后默认解压到: read/config_intended（同名覆盖）
任务结束后会询问是否断开 L2TP（--no-vpn 时不连也不问）
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)

DEFAULT_URL = "http://192.168.30.5:8081/"
DEFAULT_TIMEOUT_MS = 60_000
# 页面打开单独更长（VPN 下 NiceGUI 首屏慢）
PAGE_GOTO_TIMEOUT_MS = 120_000
DEFAULT_GEN_TIMEOUT = 60
# 系统自带 L2TP 服务名（scutil --nc list / 网络设置里可见）
DEFAULT_VPN_NAME = "配置服务器"
VPN_CONNECT_TIMEOUT = 45
DOWNLOAD_TIMEOUT_MS = 90_000
# 下载默认目录与命名：配置+日期，如 配置20260710.zip
DEFAULT_OUT_DIR = Path("/Users/shadowx/Documents/招行/配置生成/原始配置")
# 下载 ZIP 后解压目标（功能4 比对用的预期配置目录）
DEFAULT_EXTRACT_DIR = Path(
    "/Users/shadowx/PycharmProjects/mywork_script/read/config_intended"
)

# 运行日志框 / 通知里视为失败
HARD_ERROR = re.compile(
    r"\[ERROR\]|生成失败|执行失败|任务执行失败|处理失败|报错|"
    r"Traceback|Exception:|Error:|FAILED",
    re.IGNORECASE,
)
# 运行日志框里视为成功
SUCCESS_PATTERNS = re.compile(
    r"(生成完成|全部完成|配置生成完成|任务完成|SUCCESS|已成功生成|"
    r"配置文件已打包为zip|已打包为zip)",
    re.IGNORECASE,
)
# 勾了 ZIP 时，必须等到打包完成才能下载
ZIP_READY_PATTERNS = re.compile(
    r"(配置文件已打包为zip|已打包为zip|\.zip)",
    re.IGNORECASE,
)
# 任务已启动的信号（日志框开始有内容）
STARTED_PATTERNS = re.compile(
    r"(开始生成配置|执行参数|正在处理文件|源文件:|任务已启动)",
    re.IGNORECASE,
)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="配置生成平台自动化（上传 Excel → 下载 ZIP）")
    p.add_argument("excel", type=Path, help="要上传的 Excel 参数文件路径")
    p.add_argument("--url", default=DEFAULT_URL, help=f"平台地址（默认 {DEFAULT_URL}）")
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"ZIP 下载目录（默认 {DEFAULT_OUT_DIR}）；文件名为 Excel文件名_YYYYMMDD.zip，重名覆盖",
    )
    p.add_argument(
        "--extract-dir",
        type=Path,
        default=DEFAULT_EXTRACT_DIR,
        help=f"下载后解压目录（默认 {DEFAULT_EXTRACT_DIR}）；同名覆盖",
    )
    p.add_argument(
        "--no-extract",
        action="store_true",
        help="下载后不解压",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_GEN_TIMEOUT,
        help=f"等待生成完成的最长时间，秒（默认 {DEFAULT_GEN_TIMEOUT}）",
    )
    p.add_argument(
        "--vpn",
        default=DEFAULT_VPN_NAME,
        help=f"访问内网前要连接的系统 L2TP 名称（默认 {DEFAULT_VPN_NAME}）",
    )
    p.add_argument(
        "--no-vpn",
        action="store_true",
        help="跳过 VPN 检查/连接（已手动连上时可用）",
    )
    p.add_argument("--headed", action="store_true", help="有界面运行（默认无头）")
    p.add_argument("--slow", type=int, default=0, help="每步延迟毫秒（如 --slow 300）")
    return p.parse_args()


def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def vpn_status(name: str) -> str:
    """返回 Connected / Connecting / Disconnected / Unknown。"""
    r = _run(["scutil", "--nc", "status", name])
    line = (r.stdout or "").splitlines()[0].strip() if r.stdout else ""
    if not line:
        return "Unknown"
    # 第一行一般是 Connected / Disconnected / Connecting
    return line.split()[0] if line else "Unknown"


def vpn_is_connected(name: str) -> bool:
    return vpn_status(name).lower() == "connected"


def start_vpn(name: str) -> None:
    """
    连接 macOS 系统 L2TP。
    优先 networksetup（对「配置服务器」更稳），再试 scutil。
    """
    print(f"[vpn] 正在连接 L2TP「{name}」…")
    # networksetup 对 PPP/L2TP 服务名有效
    r1 = _run(["networksetup", "-connectpppoeservice", name])
    if r1.returncode != 0:
        r2 = _run(["scutil", "--nc", "start", name])
        if r2.returncode != 0:
            err = (r1.stderr or r1.stdout or "") + (r2.stderr or r2.stdout or "")
            raise RuntimeError(f"无法启动 VPN「{name}」: {err.strip() or 'unknown error'}")


def stop_vpn(name: str, timeout_s: int = 20) -> None:
    """断开 L2TP；成功/失败后都尽量等到 Disconnected。"""
    if not vpn_is_connected(name):
        print(f"[vpn] 「{name}」已是断开状态，无需关闭")
        return

    print(f"[vpn] 正在断开 L2TP「{name}」…")
    # disconnectpppoeservice 对 L2TP 有效；scutil stop 作兜底
    _run(["networksetup", "-disconnectpppoeservice", name])
    if vpn_is_connected(name):
        _run(["scutil", "--nc", "stop", name])

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = vpn_status(name)
        if st.lower() == "disconnected":
            print(f"[vpn] 已断开: {name}")
            return
        time.sleep(0.5)

    print(f"[vpn] 警告: 等待断开超时，当前状态={vpn_status(name)}", file=sys.stderr)


def confirm_stop_vpn(name: str) -> bool:
    """
    任务结束后询问是否断开 VPN。
    回车/Y=关，n=保留；非交互（无 TTY）默认关。
    """
    if not sys.stdin.isatty():
        print(f"[vpn] 非交互环境，默认断开「{name}」")
        return True
    try:
        ans = input(f"[vpn] 任务结束，是否关闭 VPN「{name}」？[Y/n] ").strip().lower()
    except EOFError:
        return True
    return ans in ("", "y", "yes", "是")


def wait_vpn_connected(name: str, timeout_s: int = VPN_CONNECT_TIMEOUT) -> None:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        st = vpn_status(name)
        if st != last:
            print(f"[vpn] 状态: {st}")
            last = st
        if st.lower() == "connected":
            print(f"[vpn] 已连接: {name}")
            return
        time.sleep(1)
    raise RuntimeError(
        f"VPN「{name}」在 {timeout_s}s 内未连上（当前: {vpn_status(name)}）。"
        "请在「系统设置 → 网络 → VPN」确认账号/共享密钥，或手动连接后再试。"
    )


def url_reachable(url: str, timeout_s: float = 5.0) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout_s)
        return True
    except Exception:
        try:
            # 有的环境只允许 HEAD/GET 部分失败，再试一次忽略证书等
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=timeout_s)
            return True
        except Exception:
            return False


def ensure_vpn(name: str, target_url: str) -> None:
    """
    打开页面前确保 L2TP 已连接，并能访问目标 URL。
    """
    if vpn_is_connected(name):
        print(f"[vpn] 已处于连接状态: {name}")
    else:
        start_vpn(name)
        wait_vpn_connected(name)

    # 给路由一点时间
    time.sleep(1)

    if url_reachable(target_url):
        print(f"[vpn] 目标可达: {target_url}")
        return

    # 已显示 Connected 但访问不通：再拉一次 VPN
    print(f"[vpn] 已连接但仍无法访问 {target_url}，尝试重连…")
    _run(["scutil", "--nc", "stop", name])
    time.sleep(2)
    start_vpn(name)
    wait_vpn_connected(name)
    time.sleep(2)

    if not url_reachable(target_url, timeout_s=8):
        raise RuntimeError(
            f"VPN「{name}」已连接，但仍无法打开 {target_url}。"
            "请检查服务是否在线，或 VPN 路由是否包含 192.168.30.0/24。"
        )
    print(f"[vpn] 重连后目标可达: {target_url}")


def wait_for_shell(page) -> None:
    page.get_by_text("配置生成", exact=True).first.wait_for(state="visible")
    page.wait_for_timeout(2000)


def open_config_tab(page) -> None:
    """只点顶部 Tab，避免侧栏把主区点空。"""
    start_btn = page.get_by_text("开始生成", exact=True)
    for attempt in range(1, 8):
        tab = page.locator('[role="tab"]').filter(has_text="配置生成")
        if tab.count():
            tab.first.click(force=True)
        else:
            page.locator(".q-tab").filter(has_text="配置生成").first.click(force=True)
        try:
            start_btn.first.wait_for(state="visible", timeout=4000)
            if start_btn.first.is_visible():
                print(f"[ok] 已进入配置生成页 (attempt={attempt})")
                return
        except PlaywrightTimeout:
            page.wait_for_timeout(600)
    raise RuntimeError("多次点击「配置生成」后仍看不到「开始生成」按钮")


def ensure_panel(page) -> None:
    try:
        if page.get_by_text("开始生成", exact=True).first.is_visible():
            return
    except PlaywrightError:
        pass
    open_config_tab(page)


def upload_excel(page, excel: Path) -> None:
    ensure_panel(page)
    file_input = page.locator('input[type="file"]')
    file_input.first.wait_for(state="attached", timeout=DEFAULT_TIMEOUT_MS)
    file_input.first.set_input_files(str(excel))
    page.get_by_text(excel.name, exact=False).first.wait_for(
        state="visible", timeout=20_000
    )
    page.wait_for_timeout(800)

    if page.locator(".q-checkbox").filter(has_text="ZIP文件下载").count() == 0:
        print("[warn] 上传后面板异常，重新打开并再次上传…")
        open_config_tab(page)
        page.locator('input[type="file"]').first.set_input_files(str(excel))
        page.get_by_text(excel.name, exact=False).first.wait_for(
            state="visible", timeout=20_000
        )
        page.wait_for_timeout(800)

    print(f"[ok] 已上传: {excel.name}")


def _zip_checkbox_on(page) -> bool:
    """判断 ZIP 勾选是否为开（看 inner--truthy / aria / 外层 class）。"""
    cb = page.locator(".q-checkbox").filter(has_text="ZIP文件下载").first
    try:
        inner = cb.locator(".q-checkbox__inner")
        icls = (inner.get_attribute("class") if inner.count() else "") or ""
        if "q-checkbox__inner--truthy" in icls:
            return True
        if "q-checkbox__inner--falsy" in icls:
            return False
        aria = cb.get_attribute("aria-checked")
        if aria == "true":
            return True
        if aria == "false":
            return False
        cls = cb.get_attribute("class") or ""
        return "q-checkbox--truthy" in cls
    except PlaywrightError:
        return False


def ensure_zip_checkbox(page) -> None:
    """
    勾选 ZIP文件下载。
    注意：每次 click 会翻转状态，只能在「关」时点一次，绝不可连点。
    用 get_by_text 点击可正确发出 args:["true"] 到服务端。
    """
    ensure_panel(page)
    cb = page.locator(".q-checkbox").filter(has_text="ZIP文件下载").first
    cb.wait_for(state="visible", timeout=15_000)

    if _zip_checkbox_on(page):
        print("[ok] ZIP文件下载 已是勾选状态")
        return

    # 只点一次 label 文案（实测最稳）
    page.get_by_text("ZIP文件下载", exact=True).click()
    page.wait_for_timeout(600)

    # 等 UI / 服务端回写
    for _ in range(10):
        if _zip_checkbox_on(page):
            print("[ok] 已勾选 ZIP文件下载")
            return
        page.wait_for_timeout(200)

    # UI class 可能不回写，但 WS 已发 true；再点一次风险是变成 false
    # 用 inner 的 falsy 再确认一次，仅当明确仍为 falsy 才再点
    inner = cb.locator(".q-checkbox__inner")
    icls = (inner.get_attribute("class") if inner.count() else "") or ""
    if "q-checkbox__inner--falsy" in icls:
        print("[warn] 首次勾选未生效，再点一次…")
        page.get_by_text("ZIP文件下载", exact=True).click()
        page.wait_for_timeout(600)

    print("[ok] 已发送 ZIP文件下载=开（生成日志里应出现 标志设置为: True）")

def read_log_box(page) -> str:
    """读取「运行日志」上方/中间的日志框（.nicegui-log）。这是判错主依据。"""
    log = page.locator(".nicegui-log")
    if log.count() == 0:
        return ""
    try:
        return log.first.inner_text(timeout=2000)
    except PlaywrightError:
        return ""


def read_progress_text(page) -> str:
    """读取生成进度文案，如 0% / 100%。"""
    try:
        body = page.locator("body").inner_text(timeout=2000)
        m = re.search(r"生成进度\s*(\d{1,3})\s*%", body)
        if m:
            return f"{m.group(1)}%"
        # 独立百分比节点
        el = page.locator("text=/^\\d{1,3}%$/")
        if el.count():
            return el.last.inner_text(timeout=500).strip()
    except PlaywrightError:
        pass
    return ""


def read_save_location(page) -> str:
    """读取「配置文件保存位置」一行。"""
    try:
        loc = page.get_by_text("配置文件保存位置", exact=False)
        if loc.count():
            return loc.first.inner_text(timeout=1000).strip()
    except PlaywrightError:
        pass
    return ""


def read_notifications(page) -> list[str]:
    """读取右下/底部 toast 通知（上传成功、任务启动、失败等）。"""
    msgs: list[str] = []
    try:
        notes = page.locator(".q-notification")
        n = min(notes.count(), 5)
        for i in range(n):
            t = notes.nth(i).inner_text(timeout=500).strip()
            # 去掉 material icon 名
            t = re.sub(
                r"\b(check_circle|info|error|warning|cancel)\b",
                "",
                t,
                flags=re.I,
            ).strip()
            if t:
                msgs.append(t)
    except PlaywrightError:
        pass
    return msgs


def read_status_panel(page) -> dict:
    """
    汇总「生成后上方/中部框」状态，用于判断成败。
    - log: 运行日志框（最重要）
    - progress: 进度百分比
    - save_location: 配置保存位置
    - notifications: 弹窗通知
    """
    return {
        "log": read_log_box(page),
        "progress": read_progress_text(page),
        "save_location": read_save_location(page),
        "notifications": read_notifications(page),
    }


def progress_percent(page) -> int | None:
    text = read_progress_text(page)
    m = re.match(r"(\d{1,3})", text or "")
    if m:
        return int(m.group(1))
    return None


def extract_error_lines(log: str) -> str:
    err_lines = [
        ln
        for ln in log.splitlines()
        if re.search(r"ERROR|失败|Exception|Traceback|Error:", ln, re.I)
    ]
    return "\n".join(err_lines[-10:]) if err_lines else log[-800:]


def panel_has_error(status: dict) -> str | None:
    """
    识别上方框/日志/通知是否报错。
    返回错误摘要；无错返回 None。
    """
    log = status.get("log") or ""
    if HARD_ERROR.search(log):
        return extract_error_lines(log)

    for n in status.get("notifications") or []:
        if HARD_ERROR.search(n) or re.search(r"失败|错误", n):
            # 排除「文件上传成功」等
            if "成功" in n and "失败" not in n:
                continue
            return n

    return None


def panel_is_success(status: dict, require_zip: bool = True) -> bool:
    """
    无报错前提下判定成功。
    勾选 ZIP 下载时：必须看到「配置文件已打包为zip」，仅进度 100% 不够
    （否则下载按钮点了也没有文件）。
    """
    if panel_has_error(status):
        return False
    log = status.get("log") or ""

    # 若日志明确写了 ZIP=False，不算可下载成功
    if re.search(r"ZIP文件下载标志设置为:\s*False", log):
        # 仍可能生成了 cfg，但不能走下载 zip
        if require_zip:
            return False

    if require_zip:
        return bool(ZIP_READY_PATTERNS.search(log))

    if SUCCESS_PATTERNS.search(log):
        return True
    pct = progress_percent_from_status(status)
    if pct == 100 and ("收集到" in log or "配置文件已保存到" in log):
        return True
    loc = status.get("save_location") or ""
    if loc and "未生成" not in loc and "配置文件保存位置" in loc:
        path_part = re.sub(r"配置文件保存位置\s*[:：]?\s*", "", loc).strip()
        path_part = path_part.lstrip("📁").strip()
        if path_part and path_part != "未生成":
            return True
    return False

def progress_percent_from_status(status: dict) -> int | None:
    text = status.get("progress") or ""
    m = re.match(r"(\d{1,3})", text)
    return int(m.group(1)) if m else None


def format_status_snapshot(status: dict) -> str:
    """打印给人看的状态摘要。"""
    lines = [
        f"  进度: {status.get('progress') or '?'}",
        f"  保存位置: {status.get('save_location') or '(无)'}",
    ]
    notes = status.get("notifications") or []
    if notes:
        lines.append(f"  通知: {' | '.join(notes)}")
    log = (status.get("log") or "").strip()
    if log:
        # 只展示末尾若干行，避免刷屏
        tail = "\n".join(log.splitlines()[-12:])
        lines.append("  --- 运行日志框 ---")
        for ln in tail.splitlines():
            lines.append(f"  | {ln}")
    else:
        lines.append("  运行日志框: (空)")
    return "\n".join(lines)


def wait_generation(
    page, timeout_s: int, require_zip: bool = True
) -> tuple[bool, str, dict]:
    """
    点击「开始生成」之后：持续识别上方/日志框内容。
    返回 (success, message, last_status)。
    报错时 success=False，调用方不得再点「下载ZIP」。
    require_zip=True 时必须等到「配置文件已打包为zip」（超时无报错则强行进入下一步导出）。
    """
    deadline = time.time() + timeout_s
    last_status: dict = {}
    last_log_len = -1
    saw_start = False
    saw_zip_false = False
    stable_ok = 0
    start_time = time.time()
    last_heartbeat = start_time

    print("[info] 开始识别运行日志框 / 进度 / 通知…")
    if require_zip:
        print("[info] 已要求 ZIP：将等待日志出现「配置文件已打包为zip」或超时后直接尝试导出")

    while time.time() < deadline:
        status = read_status_panel(page)
        last_status = status
        log = status.get("log") or ""
        pct = progress_percent_from_status(status)

        # 日志有更新时打印
        if len(log) != last_log_len:
            last_log_len = len(log)
            print("[status] 日志框有更新:")
            print(format_status_snapshot(status))
            last_heartbeat = time.time()
        else:
            # 日志无更新时，每 15 秒打印心跳日志
            now = time.time()
            if now - last_heartbeat >= 15:
                elapsed = int(now - start_time)
                print(f"[info] 等待日志输出/打包中… (已等待 {elapsed}s / 超时上限 {timeout_s}s)")
                last_heartbeat = now

        if STARTED_PATTERNS.search(log) or any(
            "已启动" in n for n in (status.get("notifications") or [])
        ):
            saw_start = True

        if re.search(r"ZIP文件下载标志设置为:\s*False", log):
            saw_zip_false = True
            if require_zip:
                return (
                    False,
                    "运行日志显示「ZIP文件下载标志设置为: False」。"
                    "勾选未生效或被连点关闭，无法下载 ZIP。请重试。",
                    status,
                )

        # 1) 优先：日志框 / 通知里出现错误 → 失败，禁止下载
        err = panel_has_error(status)
        if err:
            return (
                False,
                f"运行日志框检测到报错（进度={pct if pct is not None else '?'}%）\n{err}",
                status,
            )

        # 2) 成功
        if panel_is_success(status, require_zip=require_zip):
            stable_ok += 1
            if stable_ok >= 2:
                msg = f"生成成功（进度={pct}%）"
                if require_zip:
                    msg += "，ZIP 已打包"
                return True, msg, status
        else:
            stable_ok = 0

        page.wait_for_timeout(1000)

    # --- 超时后的判断逻辑 ---
    err = panel_has_error(last_status)
    if err:
        snap = format_status_snapshot(last_status)
        return (
            False,
            f"等待超时（{timeout_s}s）且日志框检测到报错\n{err}\n{snap}",
            last_status,
        )

    # 无明确报错：即使超时也直接执行下一步导出 ZIP
    snap = format_status_snapshot(last_status)
    print(f"[warn] 等待日志超时（{timeout_s}s），但未检测到报错，直接执行下一步导出 ZIP")
    return (
        True,
        f"等待超时（{timeout_s}s），日志无报错，直接执行下一步导出 ZIP\n{snap}",
        last_status,
    )


def download_button_ready(page) -> bool:
    """下载 ZIP 按钮是否可点（报错时通常仍显示但不应点；再加一层保险）。"""
    btn = page.get_by_role("button", name=re.compile(r"下载\s*ZIP", re.I))
    if btn.count() == 0:
        return False
    try:
        if not btn.first.is_visible() or not btn.first.is_enabled():
            return False
        # disabled 属性 / aria
        disabled = btn.first.get_attribute("disabled")
        aria = btn.first.get_attribute("aria-disabled")
        if disabled is not None or aria == "true":
            return False
        cls = btn.first.get_attribute("class") or ""
        if "disabled" in cls:
            return False
        return True
    except PlaywrightError:
        return False


def download_zip(
    page, out_dir: Path, excel_name: str = "", allow_no_zip_pattern: bool = True
) -> Path:
    """
    点击「下载ZIP」。
    - 若 allow_no_zip_pattern=True（默认），即使日志中未明确出现「配置文件已打包为zip」，只要无报错也尝试点击下载。
    """
    status = read_status_panel(page)
    err = panel_has_error(status)
    if err:
        raise RuntimeError(f"下载前日志框出现报错，取消下载:\n{err}")

    if not ZIP_READY_PATTERNS.search(status.get("log") or ""):
        if not allow_no_zip_pattern:
            raise RuntimeError(
                "日志中未见「配置文件已打包为zip」，取消下载。"
                "请确认已勾选 ZIP文件下载 且生成已完成。"
            )
        else:
            print("[warn] 日志中未见「配置文件已打包为zip」，但因无报错，直接尝试点击「下载ZIP」…")

    btn = page.locator(".q-btn").filter(has_text=re.compile(r"下载\s*ZIP", re.I))
    if btn.count() == 0:
        btn = page.get_by_role("button", name=re.compile(r"下载\s*ZIP", re.I))
    if btn.count() == 0:
        raise RuntimeError("找不到「下载ZIP」按钮")

    # 滚到底部确保按钮在视口
    try:
        btn.first.scroll_into_view_if_needed()
    except PlaywrightError:
        pass

    print("[info] 点击「下载ZIP」，等待浏览器下载事件…")
    with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as dl_info:
        btn.first.click()
    download = dl_info.value

    try:
        tmp = download.path()
        if tmp:
            print(f"[info] 临时下载路径: {tmp}")
    except PlaywrightError:
        pass

    # 命名：Excel文件名+日期，如 网络设备参数_20260714.zip；重名直接覆盖
    date_str = time.strftime("%Y%m%d")
    stem = Path(excel_name).stem if excel_name else "配置"
    dest = out_dir / f"{stem}_{date_str}.zip"
    out_dir.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
        print(f"[info] 已删除同名文件，将覆盖: {dest.name}")

    download.save_as(str(dest))
    if not dest.is_file() or dest.stat().st_size <= 0:
        raise RuntimeError(f"下载文件无效: {dest}")
    print(f"[ok] ZIP 大小: {dest.stat().st_size} bytes")
    print(f"[ok] 已保存为: {dest}")
    return dest


def extract_zip(zip_path: Path, extract_dir: Path) -> list[Path]:
    """
    将 ZIP 解压到 extract_dir。
    - 扁平成员（xxx.cfg）直接落到目标目录
    - 带目录的成员保留相对路径
    - 同名覆盖；拒绝 zip-slip（跳出目标目录）
    返回写出的文件路径列表。
    """
    if not zip_path.is_file():
        raise RuntimeError(f"ZIP 不存在: {zip_path}")

    extract_dir = extract_dir.expanduser().resolve()
    extract_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            # 跳过目录项
            if not name or name.endswith("/"):
                continue
            # 去掉 zip 内前导 ./ 与绝对路径感
            rel = Path(name)
            if rel.is_absolute() or ".." in rel.parts:
                raise RuntimeError(f"ZIP 含非法路径，拒绝解压: {name}")

            dest = (extract_dir / rel).resolve()
            try:
                dest.relative_to(extract_dir)
            except ValueError as e:
                raise RuntimeError(f"ZIP 路径越界，拒绝解压: {name}") from e

            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, open(dest, "wb") as out:
                out.write(src.read())
            written.append(dest)
            print(f"[ok] 解压: {dest.name} -> {dest}")

    if not written:
        raise RuntimeError(f"ZIP 内无文件可解压: {zip_path}")
    print(f"[ok] 共解压 {len(written)} 个文件到 {extract_dir}")
    return written


def open_page(page, url: str) -> None:
    """VPN 下页面加载可能很慢，分策略打开。"""
    last_err: Exception | None = None
    for attempt, wait_until in enumerate(("commit", "domcontentloaded", "load"), start=1):
        try:
            print(f"[info] page.goto attempt={attempt} wait_until={wait_until}")
            page.goto(url, wait_until=wait_until, timeout=PAGE_GOTO_TIMEOUT_MS)
            wait_for_shell(page)
            return
        except Exception as e:
            last_err = e
            print(f"[warn] goto 失败 ({wait_until}): {e}")
            page.wait_for_timeout(1500)
    raise RuntimeError(f"打开页面失败: {last_err}")
def main() -> int:
    args = parse_args()
    excel = args.excel.expanduser().resolve()
    out_dir = args.out.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not excel.is_file():
        print(f"[err] Excel 不存在: {excel}", file=sys.stderr)
        return 2

    print(f"[info] URL   = {args.url}")
    print(f"[info] Excel = {excel}")
    print(f"[info] 下载目录 = {out_dir}")
    extract_dir = args.extract_dir.expanduser().resolve()
    if args.no_extract:
        print("[info] 解压 = 跳过 (--no-extract)")
    else:
        print(f"[info] 解压目录 = {extract_dir}")

    manage_vpn = not args.no_vpn
    exit_code = 1

    try:
        # 1/8) 先连系统 L2TP，否则 192.168.30.5 不可达
        if manage_vpn:
            print(f"[1/8] 检查/连接 VPN「{args.vpn}」…")
            try:
                ensure_vpn(args.vpn, args.url)
            except Exception as e:
                print(f"[err] VPN: {e}", file=sys.stderr)
                return 3
        else:
            print("[1/8] 已指定 --no-vpn，跳过连接与断开 VPN")

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(
                    headless=not args.headed,
                    slow_mo=args.slow or 0,
                    channel="chrome",
                )
                print("[info] 浏览器 = Chrome")
            except Exception:
                browser = p.chromium.launch(
                    headless=not args.headed,
                    slow_mo=args.slow or 0,
                )
                print("[info] 浏览器 = Chromium")

            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT_MS)

            try:
                print("[2/8] 打开页面…")
                open_page(page, args.url)

                print("[3/8] 进入「配置生成」…")
                open_config_tab(page)

                print("[4/8] 上传 Excel 并勾选 ZIP…")
                upload_excel(page, excel)
                ensure_zip_checkbox(page)

                print("[5/8] 点击「开始生成」…")
                ensure_panel(page)
                page.get_by_role("button", name=re.compile(r"^开始生成$")).click()
                page.wait_for_timeout(1000)

                print("[6/8] 识别运行日志框：等打包完成 / 判错…")
                ok, msg, status = wait_generation(page, args.timeout, require_zip=True)
                print(f"[{'ok' if ok else 'err'}] {msg.splitlines()[0]}")
                if not ok:
                    print("[err] 生成失败或 ZIP 未就绪，跳过「下载ZIP」", file=sys.stderr)
                    print(msg, file=sys.stderr)
                    print("[status] 最终面板状态:", file=sys.stderr)
                    print(format_status_snapshot(status), file=sys.stderr)
                    if re.search(
                        r"ZIP文件下载标志设置为:\s*False", status.get("log") or ""
                    ):
                        print(
                            "[err] 服务端记录 ZIP=False：勾选可能被连点关掉了",
                            file=sys.stderr,
                        )
                    shot = out_dir / f"generate_config_error_{int(time.time())}.png"
                    page.screenshot(path=str(shot), full_page=True)
                    print(f"[info] 截图: {shot}", file=sys.stderr)
                    exit_code = 1
                else:
                    print("[7/8] 日志已确认 ZIP 打包完成，点击「下载ZIP」…")
                    dest = download_zip(page, out_dir, excel.name)
                    print(f"[done] 已保存: {dest}")
                    if args.no_extract:
                        print("[8/8] 已指定 --no-extract，跳过解压")
                        exit_code = 0
                    else:
                        print(f"[8/8] 解压 ZIP → {extract_dir} …")
                        files = extract_zip(dest, extract_dir)
                        print(f"[done] 已解压 {len(files)} 个文件")
                        exit_code = 0

            except Exception as e:
                print(f"[err] {type(e).__name__}: {e}", file=sys.stderr)
                try:
                    shot = out_dir / f"generate_config_error_{int(time.time())}.png"
                    page.screenshot(path=str(shot), full_page=True)
                    print(f"[info] 截图: {shot}", file=sys.stderr)
                except Exception:
                    pass
                exit_code = 1
            finally:
                context.close()
                browser.close()
    finally:
        # 任务结束询问是否断开 L2TP（--no-vpn 不碰）
        if manage_vpn:
            if confirm_stop_vpn(args.vpn):
                print(f"[vpn] 关闭 VPN「{args.vpn}」…")
                try:
                    stop_vpn(args.vpn)
                except Exception as e:
                    print(f"[vpn] 断开时出错: {e}", file=sys.stderr)
            else:
                print(f"[vpn] 按选择保留 VPN「{args.vpn}」连接")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
