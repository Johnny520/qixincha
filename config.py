# -*- coding: utf-8 -*-
"""API 密钥与全局配置。key 由 App 设置页写入，未填写时走免 key 兜底源。
v1.3.0 - 修复 Android 路径写入问题，使用可写目录。
"""
import os
import json


def _writable_dir():
    """返回可写目录。Android 上使用 ANDROID_PRIVATE，桌面使用 __file__ 所在目录。"""
    # Android: Buildozer 设置 ANDROID_PRIVATE 为 app 可写数据目录
    android_dir = os.environ.get("ANDROID_PRIVATE")
    if android_dir and os.path.isdir(android_dir):
        return android_dir
    # 桌面/开发环境：使用 __file__ 所在目录
    base = os.path.dirname(os.path.abspath(__file__))
    # 测试目录是否可写
    try:
        test_path = os.path.join(base, ".write_test")
        with open(test_path, "w") as f:
            f.write("ok")
        os.remove(test_path)
        return base
    except Exception:
        # __file__ 目录不可写，使用用户 home 目录
        home = os.path.expanduser("~")
        app_dir = os.path.join(home, ".qixincha")
        os.makedirs(app_dir, exist_ok=True)
        return app_dir


_WDIR = _writable_dir()
CONFIG_PATH = os.path.join(_WDIR, "config.json")

DEFAULT_CONFIG = {
    # 在 App 设置页填入你在各免费平台注册的 key
    "apibyte_key": "",        # https://www.apibyte.cn  （工商基础，免费注册）
    "xxapi_key": "",          # https://xxapi.cn        （股东/变更，免费注册）
    "jisuapi_key": "",        # https://www.jisuapi.com （工商/股东/变更/高管，字段极全，免费注册）
    "juhe_key": "",           # https://apis.juhe.cn    （对外投资等，注册后送额度）
    "tianyancha_key": "",     # 天眼查开放平台 https://openapi.tianyancha.com （分支等，需申请）
    "qcc_key": "",            # 企查查开放平台 https://openapi.qcc.com （全维度，需企业认证）
    "custom_apis": [],        # 自定义源列表：[{name, url, key, header, mapping}]
    "timeout": 12,            # 单次请求超时(秒)
    "cache_days": 3,          # 本地缓存有效期(天)
    "enable_scrape": True,    # 无 key 时是否启用免费网页抓取兜底（能爬才爬）
    "follow_list": [],        # 关注（收藏）企业名称列表
}


def load_config():
    try:
        if not os.path.exists(CONFIG_PATH):
            save_config(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # Android 可写目录问题已通过 _writable_dir() 修复，这里只是兜底


def set_key(name, value):
    cfg = load_config()
    cfg[name] = value
    save_config(cfg)
    return cfg


def reset_config():
    """把 config.json 重写为 DEFAULT_CONFIG 并回读校验。

    成功返回 True；任何异常（写入失败 / 回读非 dict）返回 False，
    此时调用方应回退到内存字典（不抛出）。供 auto_repair / run_repair 使用。
    """
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(dict(DEFAULT_CONFIG), f, ensure_ascii=False, indent=2)
        # 回读校验
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            reloaded = json.load(f)
        if not isinstance(reloaded, dict):
            return False
        return True
    except Exception:
        return False


# ── 关注（收藏）企业列表 ──
def get_follow_list():
    """返回关注企业名称列表（list[str]），任何异常返回空列表。"""
    try:
        cfg = load_config()
        lst = cfg.get("follow_list", [])
        if not isinstance(lst, list):
            return []
        return [str(x) for x in lst if x]
    except Exception:
        return []


def set_follow_list(lst):
    """覆盖写入关注列表，返回是否成功。"""
    try:
        cfg = load_config()
        cfg["follow_list"] = list(lst)
        save_config(cfg)
        return True
    except Exception:
        return False


def toggle_follow(name):
    """切换关注状态：已关注则取消，未关注则添加。

    返回切换后的状态：True=已关注，False=已取消（异常时返回 False）。
    """
    try:
        name = str(name).strip()
        if not name:
            return False
        lst = get_follow_list()
        if name in lst:
            lst.remove(name)
            now = False
        else:
            lst.append(name)
            now = True
        set_follow_list(lst)
        return now
    except Exception:
        return False


def is_followed(name):
    """是否已关注该企业。"""
    try:
        return str(name).strip() in get_follow_list()
    except Exception:
        return False
