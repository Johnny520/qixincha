# -*- coding: utf-8 -*-
"""修复中心：对标 Flutter RepairService / Android RepairCenter。

涵盖网络 / 配置 / 缓存三类诊断 + 启动自动修复 + 手动一键修复。
核心原则：任何异常都不抛出（全部降级为 RepairResult），绝不因修复失败让 App 崩溃。
"""
import requests


# ── 安全导入底层模块（沿用 main.py 的防御性风格）──
try:
    import config
    _load_config = config.load_config
    _reset_config = config.reset_config
except Exception:
    config = None

    def _load_config():
        return {}

    def _reset_config():
        return False


try:
    import cache
    _cache_clear = cache.clear_all

    def _cache_broken():
        try:
            return bool(cache.broken)
        except Exception:
            return False

    _cache_size = cache.size
except Exception:
    cache = None

    def _cache_clear():
        pass

    def _cache_broken():
        return False

    def _cache_size():
        return 0


def _safe_broken():
    """安全地读取缓存损坏标志。"""
    try:
        return bool(_cache_broken())
    except Exception:
        return False


def _safe_size():
    """安全地读取缓存条目数。"""
    try:
        return int(_cache_size() or 0)
    except Exception:
        return 0


class RepairResult:
    """单项诊断 / 修复结果。

    name   : 项目名（如「网络连通性」「配置文件」「本地缓存」）
    ok     : 是否通过 / 修复成功
    detail : 人类可读说明
    fixed  : 本次是否真正执行了修复动作
    """

    def __init__(self, name, ok, detail, fixed=False):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.fixed = fixed

    def __repr__(self):
        mark = "✅" if self.ok else "⚠️"
        fix = "🔧" if self.fixed else ""
        return f"{mark}{fix} {self.name}：{self.detail}"

    def __str__(self):
        return self.__repr__()


class RepairService:
    """修复中心服务，提供检查 / 自动修复 / 一键修复。"""

    # ── 网络连通性检测 ──
    def check_network(self):
        try:
            r = requests.get(
                "https://www.bing.com",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8,
            )
            if r.status_code == 200:
                return RepairResult("网络连通性", True, "网络正常，可访问外网。")
            return RepairResult(
                "网络连通性", False,
                f"服务器返回 {r.status_code}，但可连通。")
        except Exception:
            return RepairResult(
                "网络连通性", False,
                "无法连接网络，请检查 Wi-Fi / 移动数据。")

    # ── 配置完整性检测 ──
    def check_config(self):
        try:
            cfg = _load_config()
            if not isinstance(cfg, dict):
                return RepairResult("配置文件", False, "配置读取失败：返回非 dict。")
            # 顺带验证关注列表可读取（对齐 Flutter/Android 的 getFollowList）
            try:
                if config is not None and hasattr(config, "get_follow_list"):
                    config.get_follow_list()
            except Exception:
                pass
            return RepairResult("配置文件", True, "配置读写正常。")
        except Exception as e:
            return RepairResult("配置文件", False, f"配置读取失败：{e}")

    # ── 缓存检测 ──
    def check_cache(self):
        try:
            if _safe_broken():
                return RepairResult("本地缓存", False, "缓存状态异常，建议清理。")
            return RepairResult(
                "本地缓存", True, f"缓存正常（当前 {_safe_size()} 条）。")
        except Exception as e:
            return RepairResult("本地缓存", False, f"缓存检测异常：{e}")

    # ── 启动 / 出错时静默自动修复 ──
    # 仅执行真正发生的修复，返回列表；任何异常都不抛出。
    def auto_repair(self):
        fixed = []
        # 1) 配置损坏 → 重置
        try:
            if not self.check_config().ok:
                ok = bool(_reset_config())
                fixed.append(RepairResult(
                    "配置文件", ok,
                    "检测到配置损坏，已重置为默认设置。" if ok else "配置重置失败。",
                    fixed=True))
        except Exception:
            pass
        # 2) 缓存损坏 或 条目数过多(>200) → 清理
        try:
            if _safe_broken() or _safe_size() > 200:
                _cache_clear()
                ok = not _safe_broken()
                fixed.append(RepairResult(
                    "本地缓存", ok,
                    "检测到缓存异常，已清理本地缓存。" if ok else "缓存清理失败。",
                    fixed=True))
        except Exception:
            pass
        return fixed

    # ── 手动一键修复：完整诊断 + 执行可修复项 ──
    def run_repair(self):
        report = []
        # 网络（仅诊断，不修复）
        try:
            report.append(self.check_network())
        except Exception:
            report.append(RepairResult("网络连通性", False, "网络检测异常。"))

        # 配置修复
        try:
            if not self.check_config().ok:
                ok = bool(_reset_config())
                report.append(RepairResult(
                    "配置文件", ok,
                    "已重置为默认设置。" if ok else "配置重置失败，请尝试重装。",
                    fixed=True))
            else:
                report.append(RepairResult("配置文件", True, "无需修复。"))
        except Exception as e:
            report.append(RepairResult("配置文件", False, f"配置修复异常：{e}"))

        # 缓存修复（损坏 或 条目数 > 200）
        try:
            if _safe_broken() or _safe_size() > 200:
                _cache_clear()
                ok = not _safe_broken()
                report.append(RepairResult(
                    "本地缓存", ok,
                    (f"已清理本地缓存（{_safe_size()} 条）。"
                     if ok else "缓存清理失败。"),
                    fixed=True))
            else:
                report.append(RepairResult("本地缓存", True, "无需修复。"))
        except Exception as e:
            report.append(RepairResult("本地缓存", False, f"缓存修复异常：{e}"))

        return report
