# -*- coding: utf-8 -*-
"""免 key 网页抓取兜底层。

设计原则（对齐用户要求「能爬虫的都爬，不能爬的就不爬」）：
- 只做 best-effort 的公开网页提取，任一源失败 / 反爬 / 需登录都安全跳过；
- 绝不让抓取异常冒泡到主流程，保证 App 永远可用；
- 默认走「搜索引擎公开结果摘要」提取基础工商字段，无需任何 key。

如需接入更多稳定的免费公开源，在本文件追加函数并注册到 _SOURCES 即可，
data_sources 会自动复用。
"""
import re
import requests
from urllib.parse import quote

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

TIMEOUT = 12


def _get(url, params=None, timeout=TIMEOUT):
    h = dict(HEADERS)
    return requests.get(url, params=params, headers=h, timeout=timeout)


def _strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html or "")


# 字段提取正则：匹配「关键词 + 分隔符 + 值」，必须带分隔符（冒号或空白），
# 避免把「法定代表人注册资本」这类粘连文本误判为字段值。
_DELIM = r"(?:[：:]\s*|\s{1,6})"
_PATTERNS = {
    "legal_person":   r"(?:法定代表人|法人代表|法人)" + _DELIM + r"([\u4e00-\u9fa5·•]{2,20})",
    "reg_capital":    r"(?:注册资本|注册资金|认缴资本)" + _DELIM +
                      r"([0-9]+(?:\.[0-9]+)?\s*(?:万|亿)?\s*(?:元|人民币)?)",
    "reg_status":     r"(?:登记状态|经营状态|企业状态)" + _DELIM + r"([\u4e00-\u9fa5]{2,10})",
    "establish_time": r"(?:成立日期|成立时间|注册日期)" + _DELIM +
                      r"([0-9]{4}\s*[-/年.\s]\s*[0-9]{1,2}\s*[-/月.\s]\s*[0-9]{1,2}\s*日?)",
    "credit_code":    r"(?:统一社会信用代码|信用代码|税号)" + _DELIM + r"([0-9A-Z]{18})",
    "reg_location":   r"(?:注册地址|住所|总部地址)" + _DELIM +
                      r"([\u4e00-\u9fa5A-Za-z0-9号室栋层路东西南北-]{4,40})",
    "business_scope": r"(?:经营范围)" + _DELIM +
                      r"([\u4e00-\u9fa5A-Za-z0-9，,、；;（）()×·\-\s]{6,200})",
    "org_type":       r"(?:企业类型|公司类型|机构类型)" + _DELIM + r"([\u4e00-\u9fa5()（）]{2,20})",
}


# 明显的非数据串（UI 文案 / 字段名本身），命中则丢弃该字段，避免污染结果
_BLACK = ["搜索", "验证码", "登录", "注册", "法定代表人", "注册资本", "经营范围",
          "成立日期", "统一社会信用代码", "登记状态", "企业类型", "注册地址",
          "经营状态", "认缴资本", "信用代码", "登记机关", "核准日期"]


def _extract(text):
    out = {}
    for field, pat in _PATTERNS.items():
        m = re.search(pat, text)
        if not m:
            continue
        val = m.group(1).strip()
        # 丢弃明显是字段名 / UI 文案的串，以及过短 / 过长的异常值
        if not val or len(val) < 2 or len(val) > 60:
            continue
        if any(b in val for b in _BLACK):
            continue
        out[field] = val
    return out or None


def scrape_bing(name):
    """通过搜索引擎公开摘要提取基础工商信息（免 key 兜底主路径）。"""
    try:
        q = f"{name} 法定代表人 注册资本 统一社会信用代码 成立日期 经营范围"
        r = _get("https://www.bing.com/search", params={"q": q, "setlang": "zh-CN"})
        text = _strip_tags(r.text)
        return _extract(text[:8000])
    except Exception:
        return None


def scrape_88cha(name):
    """尝试 88查 免费页面；若该源不可用 / 反爬则安全返回 None。"""
    try:
        r = _get("https://www.88cha.com/search?key=" + quote(name))
        if r.status_code != 200:
            return None
        text = _strip_tags(r.text)
        return _extract(text[:8000])
    except Exception:
        return None


# 注册的爬虫源（按顺序尝试，任一成功即返回）
_SOURCES = [scrape_88cha, scrape_bing]


def scrape_basic(name):
    """聚合多个免费爬虫源，返回归一化 basic 或 None。"""
    for fn in _SOURCES:
        try:
            d = fn(name)
            if d:
                d["name"] = d.get("name") or name
                return d
        except Exception:
            continue
    return None


def scrape_search(name):
    """免 key 搜索：从公开结果里 best-effort 提取可能的企业名列表。"""
    try:
        r = _get("https://www.bing.com/search", params={"q": name + " 企业 公司"})
        text = _strip_tags(r.text)
        raw = re.findall(
            r"([\u4e00-\u9fa5]{1,12}(?:公司|集团|企业|厂|银行|医院|大学|学院|研究院|有限公司))",
            text)
        # 过滤掉句子片段（以常见述谓词开头 / 含标点等）
        _BAD_START = ("是一家", "通过", "助力", "全称", "这家", "该", "是", "一家", "主要")
        seen, out = set(), []
        for n in raw:
            n = n.strip()
            if n in seen or not (4 <= len(n) <= 20):
                continue
            if n.startswith(_BAD_START) or ("，" in n or "。" in n or "、" in n):
                continue
            seen.add(n)
            out.append(n)
            if len(out) >= 10:
                break
        return out
    except Exception:
        return []


if __name__ == "__main__":
    print("scrape_basic(腾讯):", scrape_basic("腾讯"))
    print("scrape_search(腾讯):", scrape_search("腾讯"))
