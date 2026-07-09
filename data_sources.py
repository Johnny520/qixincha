# -*- coding: utf-8 -*-
"""
多源企业数据适配层。
优先使用免费 API（用户填 key），全部失败走免 key 兜底（88查网页解析）。
支持「自定义 API」：用户可自行接入任意官网申请的接口。
所有函数返回统一结构，便于 UI 直接渲染。
"""
import json
import requests
from urllib.parse import urlencode
from config import load_config
from cache import get, cache_key, set as cset
from scraper import scrape_basic, scrape_search

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
    )
}

# ---------- 归一化 basic 字段 ----------
# name, credit_code, legal_person, reg_capital, reg_status, establish_time,
# reg_location, business_scope, category, org_type, city, district, province,
# email, phone, website, history_name, insure_num, reg_organ, approval_date, is_listed
# shareholders: [{name, ratio, amount}]
# changes:     [{item, time, before, after}]
# key_persons: [{name, position}]
# investments: [{name, ratio, amount}]
# branches:    [{name}]


def _cfg():
    return load_config()


def _get(url, params=None, headers=None, timeout=12):
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    return requests.get(url, params=params, headers=h, timeout=timeout)


# ============ 源1: apibyte 工商基础 ============
def _apibyte_basic(name, key):
    base = "https://api.apibyte.cn/companyinfo"
    try:
        r = _get(base, params={"keyword": name},
                 headers={"Authorization": f"Bearer {key}"},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if j.get("code") != 200:
            return None
        d = j.get("data", {})
        return {
            "name": d.get("company_name"),
            "credit_code": d.get("credit_code"),
            "legal_person": d.get("legal_person"),
            "reg_capital": d.get("reg_capital"),
            "reg_status": d.get("reg_status"),
            "establish_time": d.get("establish_time"),
            "reg_location": d.get("reg_location"),
            "business_scope": d.get("business_scope"),
            "category": d.get("category"),
            "org_type": d.get("org_type"),
            "city": d.get("city"),
            "district": d.get("district"),
            "email": d.get("email"),
            "phone": d.get("phone"),
        }
    except Exception:
        return None


# ============ 源2: jisuapi 工商基础（字段极全） ============
def _jisuapi_basic(name, key):
    try:
        r = _get("https://api.jisuapi.com/enterprise/query",
                 params={"company": name, "appkey": key},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if str(j.get("status")) != "0":
            return None
        d = j.get("result", {})
        if isinstance(d, list):
            d = d[0] if d else {}
        if not d:
            return None
        return {
            "name": d.get("name"),
            "credit_code": d.get("creditno"),
            "legal_person": d.get("legalperson"),
            "reg_capital": d.get("regcapitalcn") or d.get("regcapital"),
            "reg_status": d.get("status"),
            "establish_time": d.get("regdate") or d.get("startdate"),
            "reg_location": d.get("regaddress"),
            "business_scope": d.get("scope"),
            "category": d.get("nicname"),
            "org_type": d.get("type"),
            "city": d.get("city"),
            "district": d.get("district"),
            "province": d.get("province"),
            "email": d.get("email"),
            "phone": d.get("tel"),
            "website": d.get("website"),
            "history_name": d.get("historyname"),
            "insure_num": d.get("insurenum"),
            "reg_organ": d.get("regorgan"),
            "approval_date": d.get("approvaldate"),
            "is_listed": d.get("islisted"),
        }
    except Exception:
        return None


def _jisuapi_shareholders(name, key):
    try:
        r = _get("https://api.jisuapi.com/enterprise/shareholder",
                 params={"company": name, "appkey": key},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if str(j.get("status")) != "0":
            return None
        d = j.get("result", {})
        items = d.get("list", d.get("shareholders", [])) if isinstance(d, dict) else (d or [])
        out = []
        for it in (items or []):
            out.append({
                "name": it.get("name") or it.get("shareholder") or it.get("shareholdername"),
                "ratio": it.get("ratio") or it.get("percent") or it.get("stockratio"),
                "amount": it.get("amount") or it.get("subamount") or it.get("subamount"),
            })
        return out
    except Exception:
        return None


def _jisuapi_changes(name, key):
    try:
        r = _get("https://api.jisuapi.com/enterprise/change",
                 params={"company": name, "appkey": key},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if str(j.get("status")) != "0":
            return None
        d = j.get("result", {})
        items = d.get("list", []) if isinstance(d, dict) else (d or [])
        out = []
        for it in (items or []):
            out.append({
                "item": it.get("item") or it.get("changetype") or it.get("changeitem"),
                "time": it.get("date") or it.get("changedate") or it.get("time"),
                "before": it.get("before") or it.get("beforecontent"),
                "after": it.get("after") or it.get("aftercontent"),
            })
        return out
    except Exception:
        return None


def _jisuapi_key_persons(name, key):
    # jisuapi 文档称接口含「股东高管信息」；endpoint 为推测，以平台为准
    try:
        r = _get("https://api.jisuapi.com/enterprise/executive",
                 params={"company": name, "appkey": key},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if str(j.get("status")) != "0":
            return None
        d = j.get("result", {})
        items = d.get("list", d.get("executives", d.get("managers", []))) \
            if isinstance(d, dict) else (d or [])
        out = []
        for it in (items or []):
            out.append({
                "name": it.get("name") or it.get("executivename") or it.get("managername"),
                "position": it.get("position") or it.get("title") or it.get("job"),
            })
        return out
    except Exception:
        return None


# ============ 源3: xxapi 变更 / 股东 ============
def _xxapi_changes(name, key):
    try:
        r = _get("https://v2.xxapi.cn/api/Changeinfo",
                 params={"keyword": name, "pageNum": 1, "pageSize": 50},
                 headers={"Authorization": f"Bearer {key}"},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if j.get("code") != 200:
            return None
        items = j.get("data", {}).get("items", [])
        return [{
            "item": it.get("changeItem"),
            "time": it.get("changeTime"),
            "before": it.get("contentBefore"),
            "after": it.get("contentAfter"),
        } for it in items]
    except Exception:
        return None


def _xxapi_shareholders(name, key):
    try:
        r = _get("https://v2.xxapi.cn/api/TYHolder",
                 params={"keyword": name},
                 headers={"Authorization": f"Bearer {key}"},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if j.get("code") != 200:
            return None
        items = j.get("data", {}).get("items", j.get("data", []))
        if isinstance(items, dict):
            items = items.get("list", [])
        out = []
        for it in (items or []):
            out.append({
                "name": it.get("shareholderName") or it.get("name"),
                "ratio": it.get("ratio") or it.get("percent"),
                "amount": it.get("amount") or it.get("subAmount"),
            })
        return out
    except Exception:
        return None


# ============ 源4: 聚合数据 对外投资 ============
def _juhe_investments(name, key):
    try:
        r = _get("https://apis.juhe.cn/out_investment/query",
                 params={"company": name, "key": key},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if str(j.get("error_code")) != "0":
            return None
        d = j.get("result", {})
        items = d.get("list", d.get("investment", [])) if isinstance(d, dict) else (d or [])
        out = []
        for it in (items or []):
            out.append({
                "name": it.get("company") or it.get("name") or it.get("investedcompany"),
                "ratio": it.get("percent") or it.get("ratio") or it.get("regpercent"),
                "amount": it.get("amount") or it.get("regamount"),
            })
        return out
    except Exception:
        return None


# ============ 源5: 天眼查开放平台 分支机构 ============
def _tianyancha_branches(name, key):
    try:
        r = _get("http://open.api.tianyancha.com/services/open/824",
                 params={"companyName": name, "access_token": key},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if j.get("error_code") not in (None, 0, "0"):
            return None
        d = j.get("result", {})
        items = d.get("branchList", d.get("items", [])) if isinstance(d, dict) else (d or [])
        return [{"name": it.get("branchName") or it.get("name")} for it in (items or [])]
    except Exception:
        return None


# ============ 源6: 聚合数据 全维度（同一 juhe_key 复用） ============
# 按聚合数据「企业类」接口常见结构推测，以官网文档为准；
# 任一接口失败 / 无 key 时均安全返回 None，不影响其他模块渲染。
def _juhe_list(name, key, path):
    try:
        r = _get(f"https://apis.juhe.cn/{path}",
                 params={"company": name, "key": key},
                 timeout=_cfg().get("timeout", 12))
        j = r.json()
        if str(j.get("error_code")) != "0":
            return None
        d = j.get("result", {})
        items = d.get("list", d.get("items", [])) if isinstance(d, dict) else (d or [])
        return items if isinstance(items, list) else []
    except Exception:
        return None


# 全维度注册表：(模块key, 中文标题, 聚合数据路径, 展示字段优先级)
# 新增维度只需在此追加一行，详情页 / 数据源横幅会自动生效。
JUHE_DIMENSIONS = [
    ("abnormal",      "经营异常",     "abnormal/query",     ["inDate", "date", "inReason", "reason", "content"]),
    ("penalty",       "行政处罚",     "penalty/query",      ["penaltyDate", "date", "penaltyType", "penaltyContent", "content"]),
    ("serious",       "严重违法",     "serious/illegal",    ["inDate", "date", "inReason", "reason"]),
    ("dishonest",     "失信被执行人", "dishonest/query",    ["caseCode", "caseNo", "court", "publishDate"]),
    ("equity",        "股权出质",     "equity/pledge",      ["pledgor", "pledgee", "amount", "regDate"]),
    ("mortgage",      "动产抵押",     "mortgage/query",     ["mortgagor", "amount", "regDate", "status"]),
    ("license",       "行政许可",     "license/query",      ["licenseName", "licenseCode", "type", "endDate"]),
    ("tax",           "税收违法",     "tax/violation",      ["caseName", "amount", "date", "taxDepartment"]),
    ("owe_tax",       "欠税公告",     "owe/tax",            ["company", "amount", "taxDepartment", "date"]),
    ("lawsuit",       "司法案件",     "lawsuit/query",      ["caseNo", "caseName", "reason", "court", "date"]),
    ("court_notice",  "法院公告",     "court/notice",       ["noticeType", "noticeCode", "court", "publishDate"]),
    ("court_doc",     "裁判文书",     "court/doc",          ["caseNo", "caseName", "reason", "court", "date"]),
    ("court",         "开庭公告",     "court/opening",      ["sessions", "date", "court", "caseReason", "reason"]),
    ("trademark",     "商标信息",     "trademark/query",    ["tmName", "name", "regNo", "tmStatus", "status"]),
    ("patent",        "专利信息",     "patent/query",       ["patentName", "name", "patentType", "type"]),
    ("copyright",     "著作权",       "copyright/query",    ["name", "regNo", "type", "endDate"]),
    ("software",      "软件著作权",   "software/copyright", ["name", "regNo", "type", "endDate"]),
    ("icp",           "网站备案",     "icp/query",          ["domain", "siteName", "license", "type"]),
    ("bid",           "招投标",       "bid/query",          ["title", "type", "date", "agency"]),
    ("bond",          "债券信息",     "bond/query",         ["bondName", "bondCode", "amount", "date"]),
    ("job",           "招聘信息",     "job/query",          ["title", "salary", "city", "publishDate"]),
    ("news",          "新闻舆情",     "news/query",         ["title", "source", "date", "url"]),
    ("wechat",        "微信公众号",   "wechat/public",      ["name", "wxId", "qrCode"]),
    ("annual",        "企业年报",     "annual/report",      ["reportYear", "year", "publishDate"]),
    ("financing",     "融资历程",     "financing/query",    ["round", "amount", "date", "investors"]),
    ("competitor",    "竞品信息",     "competitor/query",   ["name", "field"]),
    ("product",       "产品信息",     "product/query",      ["name", "category"]),
    ("import_export", "进出口信用",   "credit/import",      ["type", "code", "date"]),
    ("land",          "购地信息",     "land/query",         ["location", "area", "amount", "date"]),
    ("qualification", "资质证书",     "qualification/query", ["name", "code", "type", "endDate"]),
    ("random_check",  "双随机抽查",   "check/random",       ["checkDate", "checkOrg", "result"]),
]


def _juhe_dim(name, key, path, fields):
    items = _juhe_list(name, key, path)
    if not items:
        return None
    out = []
    for it in items:
        if not isinstance(it, dict):
            out.append(str(it))
            continue
        parts = [str(it[f]) for f in fields if it.get(f)]
        out.append("  ".join(parts).strip() if parts else
                   " | ".join(str(v) for v in list(it.values())[:4] if v))
    return out


# ============ 自定义 API（用户自助接入任意官网接口） ============
def _json_path(obj, path):
    cur = obj
    for p in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur


def _apply_mapping(obj, mapping):
    return {k: _json_path(obj, v) for k, v in mapping.items()}


def _guess_basic(j):
    d = j
    if isinstance(d, dict):
        for k in ("result", "data", "d"):
            if isinstance(d.get(k), dict):
                d = d[k]
                break
    cand = {
        "name": ["company_name", "name", "companyName", "enterprise_name"],
        "credit_code": ["credit_code", "creditcode", "creditno", "unified_code", "tyshxydm"],
        "legal_person": ["legal_person", "legalperson", "legal", "frname"],
        "reg_capital": ["reg_capital", "regcapital", "regcapitalcn", "registcapi", "capital"],
        "reg_status": ["reg_status", "status", "enterprise_status"],
        "establish_time": ["establish_time", "establishtime", "regdate", "startdate", "esdate"],
        "reg_location": ["reg_location", "reglocation", "regaddress", "address", "dom"],
        "business_scope": ["business_scope", "scope", "businessscope"],
        "category": ["category", "industry", "nicname", "industry_name"],
        "org_type": ["org_type", "type", "company_type", "enttype"],
        "city": ["city"], "district": ["district"], "email": ["email"],
        "phone": ["phone", "tel", "telephone"], "website": ["website", "web"],
    }
    out = {}
    for f, names in cand.items():
        for n in names:
            v = _json_path(d, n)
            if v:
                out[f] = v
                break
    return out or None


def _custom_basic(custom, name):
    try:
        url = custom.get("url", "").replace("{kw}", name)
        key = custom.get("key", "")
        header = custom.get("header", "")
        headers = dict(HEADERS)
        if header:
            h = header.replace("{key}", key)
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()
        elif key:
            sep = "&" if "?" in url else "?"
            url = url + sep + urlencode({"key": key})
        r = _get(url, headers=headers, timeout=_cfg().get("timeout", 12))
        j = r.json()
        mapping = custom.get("mapping")
        if isinstance(mapping, str):
            try:
                mapping = json.loads(mapping)
            except Exception:
                mapping = None
        if mapping and isinstance(mapping, dict):
            return _apply_mapping(j, mapping)
        return _guess_basic(j)
    except Exception:
        return None


# ============ 兜底: 免费网页抓取（免 key，能爬才爬） ============
def _fallback_88cha(name):
    # 兜底：免 key 网页抓取。enable_scrape 关闭或全源失败时返回 None。
    if not _cfg().get("enable_scrape", True):
        return None
    return scrape_basic(name)


# ============ 统一对外接口 ============
def search_company(keyword):
    cfg = _cfg()
    ck = cache_key("search", keyword)
    cached = get(ck, cfg.get("cache_days", 3))
    if cached is not None:
        return cached
    results = []
    b = None
    if cfg.get("jisuapi_key"):
        b = _jisuapi_basic(keyword, cfg["jisuapi_key"])
    if not b and cfg.get("apibyte_key"):
        b = _apibyte_basic(keyword, cfg["apibyte_key"])
    for c in (cfg.get("custom_apis") or []):
        if b:
            break
        b = _custom_basic(c, keyword)
    if b and b.get("name"):
        results.append({"name": b["name"], "credit_code": b.get("credit_code")})
    # 无 key 兜底：免费网页抓取（best-effort）
    if not results and cfg.get("enable_scrape", True):
        names = scrape_search(keyword)
        results = [{"name": n} for n in names] or [{"name": keyword}]
    cset(ck, results, cfg.get("cache_days", 3))
    return results


def get_company_detail(name):
    cfg = _cfg()
    ck = cache_key("detail", name)
    cached = get(ck, cfg.get("cache_days", 3))
    if cached is not None:
        return cached

    basic = shareholders = changes = key_persons = investments = branches = None
    dims = {}
    ms = {}
    used = set()

    # 工商基础
    if cfg.get("jisuapi_key"):
        basic = _jisuapi_basic(name, cfg["jisuapi_key"])
        if basic:
            ms["basic"], used = "jisuapi", used | {"jisuapi"}
    if not basic and cfg.get("apibyte_key"):
        basic = _apibyte_basic(name, cfg["apibyte_key"])
        if basic:
            ms["basic"], used = "apibyte", used | {"apibyte"}
    for c in (cfg.get("custom_apis") or []):
        if basic:
            break
        b = _custom_basic(c, name)
        if b:
            basic = b
            ms["basic"] = f"自定义:{c.get('name', '?')}"
            used.add(f"自定义:{c.get('name', '?')}")
    if not basic:
        basic = _fallback_88cha(name)
        if basic:
            ms["basic"], used = "免费爬虫(兜底)", used | {"免费爬虫"}

    # 股东
    if cfg.get("xxapi_key"):
        sh = _xxapi_shareholders(name, cfg["xxapi_key"])
        if sh is not None:
            shareholders, ms["shareholders"], used = sh, "xxapi(股东)", used | {"xxapi"}
    if (shareholders is None or not shareholders) and cfg.get("jisuapi_key"):
        sh = _jisuapi_shareholders(name, cfg["jisuapi_key"])
        if sh:
            shareholders, ms["shareholders"], used = sh, "jisuapi(股东)", used | {"jisuapi"}
    if shareholders is None:
        shareholders = []

    # 变更
    if cfg.get("xxapi_key"):
        ch = _xxapi_changes(name, cfg["xxapi_key"])
        if ch is not None:
            changes, ms["changes"], used = ch, "xxapi(变更)", used | {"xxapi"}
    if (changes is None or not changes) and cfg.get("jisuapi_key"):
        ch = _jisuapi_changes(name, cfg["jisuapi_key"])
        if ch:
            changes, ms["changes"], used = ch, "jisuapi(变更)", used | {"jisuapi"}
    if changes is None:
        changes = []

    # 主要人员
    if cfg.get("jisuapi_key"):
        kp = _jisuapi_key_persons(name, cfg["jisuapi_key"])
        if kp:
            key_persons, ms["key_persons"], used = kp, "jisuapi(高管)", used | {"jisuapi"}
    if key_persons is None:
        key_persons = []

    # 对外投资
    if cfg.get("juhe_key"):
        inv = _juhe_investments(name, cfg["juhe_key"])
        if inv:
            investments, ms["investments"], used = inv, "聚合数据(对外投资)", used | {"聚合数据"}
    if investments is None:
        investments = []

    # 分支机构
    if cfg.get("tianyancha_key"):
        br = _tianyancha_branches(name, cfg["tianyancha_key"])
        if br:
            branches, ms["branches"], used = br, "天眼查开放(分支)", used | {"天眼查开放"}
    if branches is None:
        branches = []

    # 聚合数据全维度（同一 juhe_key 复用；注册表见 JUHE_DIMENSIONS）
    if cfg.get("juhe_key"):
        for key, title, path, fields in JUHE_DIMENSIONS:
            rows = _juhe_dim(name, cfg["juhe_key"], path, fields)
            if rows:
                dims[key] = rows
                ms[key] = f"聚合数据({title})"
                used.add("聚合数据")

    detail = {
        "basic": basic,
        "shareholders": shareholders,
        "changes": changes,
        "key_persons": key_persons,
        "investments": investments,
        "branches": branches,
        "dims": dims,
        "sources": sorted(used),
        "module_sources": ms,
    }
    cset(ck, detail, cfg.get("cache_days", 3))
    return detail


if __name__ == "__main__":
    print(json.dumps(get_company_detail("腾讯"), ensure_ascii=False, indent=2))
