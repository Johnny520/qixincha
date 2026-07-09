# -*- coding: utf-8 -*-
"""极简缓存，按 (source, key) 存 JSON，过期自动失效。
v1.3.0 - 修复 Android 路径 + sqlite3 不可用时自动降级为 dict 缓存。
"""
import os
import json
import time

# ── 可写目录（与 config.py 共用逻辑）──
def _writable_dir():
    android_dir = os.environ.get("ANDROID_PRIVATE")
    if android_dir and os.path.isdir(android_dir):
        return android_dir
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        test_path = os.path.join(base, ".write_test")
        with open(test_path, "w") as f:
            f.write("ok")
        os.remove(test_path)
        return base
    except Exception:
        home = os.path.expanduser("~")
        app_dir = os.path.join(home, ".qixincha")
        os.makedirs(app_dir, exist_ok=True)
        return app_dir


_WDIR = _writable_dir()
DB_PATH = os.path.join(_WDIR, "cache.db")

# 缓存损坏标志位：get()/set() 捕获到 sqlite 异常时置 True，
# clear_all() 成功清空后复位 False。供 repair 模块检测。
broken = False

# ── sqlite3 延迟导入：Android 上可能不可用 ──
_sqlite3 = None
_SQLITE_OK = False

try:
    import sqlite3 as _sqlite3_mod
    _sqlite3 = _sqlite3_mod
    # 测试 sqlite3 是否真正可用（能连接并建表）
    _test_conn = _sqlite3.connect(":memory:")
    _test_conn.execute("CREATE TABLE IF NOT EXISTS t (k TEXT)")
    _test_conn.close()
    _SQLITE_OK = True
except Exception:
    _SQLITE_OK = False


# ── SQLite 缓存（首选）──
def _conn():
    if not _SQLITE_OK:
        return None
    conn = _sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS kv "
        "(k TEXT PRIMARY KEY, v TEXT, ts REAL)"
    )
    return conn


# ── dict 内存缓存（sqlite3 不可用时的降级方案）──
_MEM_CACHE = {}


def get(k, max_age_days=3):
    try:
        if _SQLITE_OK:
            try:
                conn = _conn()
                if conn:
                    row = conn.execute("SELECT v, ts FROM kv WHERE k=?", (k,)).fetchone()
                    conn.close()
                    if not row:
                        return None
                    v, ts = row
                    if (time.time() - ts) > max_age_days * 86400:
                        return None
                    return json.loads(v)
            except Exception:
                # sqlite 读取异常 → 标记缓存损坏
                global broken
                broken = True
        # 降级到内存缓存
        entry = _MEM_CACHE.get(k)
        if not entry:
            return None
        v, ts = entry
        if (time.time() - ts) > max_age_days * 86400:
            _MEM_CACHE.pop(k, None)
            return None
        return v
    except Exception:
        return None


def set(k, v, max_age_days=3):
    try:
        if _SQLITE_OK:
            try:
                conn = _conn()
                if conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO kv VALUES (?,?,?)",
                        (k, json.dumps(v, ensure_ascii=False), time.time()),
                    )
                    conn.commit()
                    conn.close()
                    return
            except Exception:
                # sqlite 写入异常 → 标记缓存损坏
                global broken
                broken = True
        # 降级到内存缓存
        _MEM_CACHE[k] = (v, time.time())
    except Exception:
        # 再降级：直接存内存
        _MEM_CACHE[k] = (v, time.time())


def cache_key(source, ident):
    return f"{source}:{ident}"


def size():
    """返回缓存条目数（sqlite 或内存降级缓存）。异常时返回内存缓存长度。"""
    try:
        if _SQLITE_OK:
            conn = _conn()
            if conn:
                n = conn.execute("SELECT COUNT(*) FROM kv").fetchone()[0]
                conn.close()
                return int(n)
        return len(_MEM_CACHE)
    except Exception:
        return len(_MEM_CACHE)


def clear_all():
    """清空全部本地缓存。成功后复位 broken=False。"""
    global broken
    try:
        if _SQLITE_OK:
            conn = _conn()
            if conn:
                conn.execute("DELETE FROM kv")
                conn.commit()
                conn.close()
        _MEM_CACHE.clear()
        broken = False
    except Exception:
        _MEM_CACHE.clear()
        broken = True
