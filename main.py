# -*- coding: utf-8 -*-
"""企信查 - 天眼查风格企业信息查询 App (Kivy)。
蓝系配色 + 底部4Tab导航 + 列表式设置页 + 空状态引导 + 全自适应。
v1.3.0 - 修复闪退（安全导入 + Android可写路径 + 启动容错） + 全自适应 + Release描述
"""
import os
import sys
import threading
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label

# ── 安全导入：任何模块失败都不崩溃 ──
try:
    from config import load_config, set_key, save_config
except Exception as e:
    print(f"[企信查] config 导入失败: {e}")
    # 降级：内存配置
    _MEM_CFG = {"agreed_disclaimer": True, "enable_scrape": True, "timeout": 12, "cache_days": 3}
    def load_config():
        return dict(_MEM_CFG)
    def save_config(cfg):
        pass
    def set_key(name, value):
        _MEM_CFG[name] = value

try:
    from data_sources import search_company, get_company_detail, JUHE_DIMENSIONS
except Exception as e:
    print(f"[企信查] data_sources 导入失败: {e}")
    JUHE_DIMENSIONS = []
    def search_company(kw):
        return [{"name": kw}]
    def get_company_detail(name):
        return {"basic": {"name": name}, "shareholders": [], "changes": [],
                "key_persons": [], "investments": [], "branches": [],
                "dims": {}, "sources": ["离线模式"], "module_sources": {}}

try:
    import legal
except Exception as e:
    print(f"[企信查] legal 导入失败: {e}")
    legal = type("legal", (), {
        "AUTHOR": "开发者", "WECHAT": "", "EMAIL": "",
        "COPYRIGHT_YEAR": 2026,
        "DISCLAIMER": "本软件仅供学习研究使用。",
        "USER_AGREEMENT": "用户协议：仅供学习。",
        "PRIVACY_POLICY": "隐私政策：不收集个人信息。",
    })()

try:
    import ui
    from ui import (FONT, PALETTE, C, CuteButton, CuteCard, CuteInput,
                    CuteLabel, info_popup, confirm_popup, edit_popup, _font_kw)
except Exception as e:
    print(f"[企信查] ui 导入失败: {e}")
    # 降级：最简 UI 组件
    PALETTE = {
        "bg": "#F0F4F8", "card": "#FFFFFF", "primary": "#3B82F6",
        "primary_d": "#1D4ED8", "mint": "#10B981", "lavender": "#8B5CF6",
        "sky": "#60A5FA", "sun": "#F59E0B", "text": "#1F2937",
        "sub": "#6B7280", "danger": "#EF4444", "line": "#E5E7EB",
        "chip": "#DBEAFE", "nav_bg": "#FFFFFF", "nav_on": "#3B82F6",
        "nav_off": "#9CA3AF",
    }
    FONT = None
    from kivy.utils import get_color_from_hex
    def C(h):
        return get_color_from_hex(h)
    def _font_kw(**kw):
        return kw
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.popup import Popup
    CuteButton = Button
    CuteCard = BoxLayout
    CuteInput = TextInput
    CuteLabel = Label

    def info_popup(title, text, btn_text="知道了", on_close=None, emoji="ℹ️"):
        pw = max(Window.width * 0.92, 280)
        ph = max(Window.height * 0.78, 400)
        lay = BoxLayout(orientation="vertical", spacing=10, padding=14)
        lbl = Label(text=text, font_size=14, size_hint_y=None, halign="left", valign="top")
        lbl.bind(texture_size=lambda i, s: setattr(i, "height", s[1] + 4))
        sv = ScrollView()
        sv.add_widget(lbl)
        lay.add_widget(sv)
        btn = Button(text=btn_text, size_hint_y=None, height=48)
        lay.add_widget(btn)
        popup = Popup(title=f"{emoji}  {title}", content=lay,
                      size_hint=(None, None), size=(pw, ph), auto_dismiss=False)
        def _close(*a):
            popup.dismiss()
            if on_close:
                on_close()
        btn.bind(on_press=_close)
        popup.open()
        return popup

    def confirm_popup(title, text, yes_text="确定", no_text="取消", on_yes=None, emoji="❓"):
        pw = max(Window.width * 0.88, 260)
        ph = max(Window.height * 0.55, 320)
        lay = BoxLayout(orientation="vertical", spacing=10, padding=14)
        body = Label(text=text, font_size=14, halign="left", valign="top")
        lay.add_widget(body)
        row = BoxLayout(size_hint_y=None, height=48, spacing=10)
        no = Button(text=no_text)
        yes = Button(text=yes_text)
        row.add_widget(no)
        row.add_widget(yes)
        lay.add_widget(row)
        popup = Popup(title=f"{emoji}  {title}", content=lay,
                      size_hint=(None, None), size=(pw, ph), auto_dismiss=False)
        def _no(*a): popup.dismiss()
        def _yes(*a):
            popup.dismiss()
            if on_yes: on_yes()
        no.bind(on_press=_no)
        yes.bind(on_press=_yes)
        popup.open()
        return popup

    def edit_popup(title, cur_value, on_save, input_type="text"):
        pw = max(Window.width * 0.85, 240)
        ph = max(Window.height * 0.35, 220)
        lay = BoxLayout(orientation="vertical", spacing=12, padding=14)
        inp = TextInput(text=cur_value, multiline=False, size_hint_y=None, height=46)
        lay.add_widget(inp)
        btn_row = BoxLayout(size_hint_y=None, height=46, spacing=10)
        cancel = Button(text="取消")
        save_btn = Button(text="保存")
        btn_row.add_widget(cancel)
        btn_row.add_widget(save_btn)
        lay.add_widget(btn_row)
        popup = Popup(title=title, content=lay,
                      size_hint=(None, None), size=(pw, ph), auto_dismiss=False)
        def _cancel(*a): popup.dismiss()
        def _save(*a):
            v = inp.text.strip()
            popup.dismiss()
            on_save(v)
        cancel.bind(on_press=_cancel)
        save_btn.bind(on_press=_save)
        popup.open()
        return popup


# ── 修复中心（对标 Flutter RepairService / Android RepairCenter）──
try:
    from repair import RepairService, RepairResult
    _HAS_REPAIR = True
except Exception as e:
    print(f"[企信查] repair 导入失败: {e}")
    _HAS_REPAIR = False
    RepairService = None
    RepairResult = None


# ── 全局 ──
class TapCard(ButtonBehavior, CuteCard):
    """可点击圆角卡片（搜索结果项）。"""
    def __init__(self, **kw):
        super().__init__(**kw)


def lab(text, **kw):
    """创建自适应 Label：自动设置字体、颜色、对齐。"""
    kw.setdefault("color", C(PALETTE["text"]))
    kw.setdefault("halign", "left")
    kw.setdefault("valign", "top")
    fkw = _font_kw(**kw)
    return Label(text=text, **fkw)


EMOJI = {
    "basic": "🏢", "shareholders": "👥", "changes": "📝",
    "key_persons": "🧑‍💼", "investments": "🌿", "branches": "🏬",
    "abnormal": "⚠️", "penalty": "🚫", "serious": "❗", "dishonest": "👮",
    "equity": "💠", "mortgage": "🏦", "license": "📜", "tax": "💰",
    "owe_tax": "💸", "lawsuit": "⚖️", "court_notice": "📢",
    "court_doc": "📄", "court": "🕒", "trademark": "™️", "patent": "🔬",
    "copyright": "©️", "software": "💻", "icp": "🌐", "bid": "🔨",
    "bond": "📈", "job": "💼", "news": "📰", "wechat": "💬",
    "annual": "📅", "financing": "💵", "competitor": "🥊",
    "product": "🛍️", "import_export": "✈️", "land": "🌾",
    "qualification": "🏅", "random_check": "🔍",
}

HOT_KW = ["腾讯", "阿里巴巴", "华为", "字节跳动", "百度",
           "京东", "美团", "小米", "比亚迪", "中国平安"]

def _mark_agreed():
    set_key("agreed_disclaimer", True)


# ═══════════════════════════
#  搜索页 (Tab 1)
# ═══════════════════════════
class SearchScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "search"
        root = BoxLayout(orientation="vertical", padding=[8, 8, 8, 0], spacing=6)

        # ── 标题 ──
        hdr = BoxLayout(size_hint_y=None, height=48, padding=[12, 6])
        hdr.add_widget(lab("🔍 企信查", font_size=20, bold=True,
                           color=C(PALETTE["primary_d"]), halign="left", valign="middle"))
        hdr.add_widget(lab("企业信息查询", font_size=12,
                           color=C(PALETTE["sub"]), halign="right", valign="middle"))
        root.add_widget(hdr)

        # ── 搜索条 ──
        bar = BoxLayout(size_hint_y=None, height=50, spacing=8)
        self.inp = CuteInput(hint_text="输入企业名称，如：腾讯",
                             size_hint_x=0.7, multiline=False)
        self.inp.bind(on_text_validate=lambda x: self.do_search())
        sbtn = CuteButton(text="🔍", size_hint_x=0.3,
                          bg=C(PALETTE["primary"]), radius=14)
        sbtn.bind(on_press=lambda x: self.do_search())
        bar.add_widget(self.inp)
        bar.add_widget(sbtn)
        root.add_widget(bar)

        self.status = lab("", font_size=13, color=C(PALETTE["sub"]),
                          size_hint_y=None, height=20)
        root.add_widget(self.status)

        # ── ScrollView ──
        self.sv = ScrollView()
        self.results = BoxLayout(orientation="vertical", size_hint_y=None,
                                 spacing=8, padding=2)
        self.results.bind(minimum_height=self.results.setter("height"))
        self.sv.add_widget(self.results)
        root.add_widget(self.sv)

        # ── 空状态引导（热门搜索） ──
        self.empty_guide = BoxLayout(orientation="vertical", spacing=8, padding=[8, 6])
        guide_lbl = lab("💡 热门搜索", font_size=16, bold=True,
                        color=C(PALETTE["primary_d"]), halign="center", valign="middle",
                        size_hint_y=None, height=28)
        self.empty_guide.add_widget(guide_lbl)
        # 两行标签
        r1 = BoxLayout(spacing=6, size_hint_y=None, height=36)
        r2 = BoxLayout(spacing=6, size_hint_y=None, height=36)
        for i, kw in enumerate(HOT_KW):
            chip = CuteButton(text=kw, font_size=13,
                              bg=C(PALETTE["chip"]), radius=12,
                              color=C(PALETTE["primary_d"]))
            chip.bind(on_press=lambda x, k=kw: self._quick(k))
            if i < 5:
                r1.add_widget(chip)
            else:
                r2.add_widget(chip)
        self.empty_guide.add_widget(r1)
        self.empty_guide.add_widget(r2)
        tip = lab("搜索企业名即可查看工商/股东/变更等31维度信息",
                  font_size=12, color=C(PALETTE["sub"]), halign="center",
                  size_hint_y=None, height=20)
        tip.bind(width=lambda i, w: setattr(tip, "text_size", (w, None)))
        self.empty_guide.add_widget(tip)
        self.results.add_widget(self.empty_guide)
        self._guide_visible = True

        self.add_widget(root)

    def _quick(self, kw):
        self.inp.text = kw
        self.do_search()

    def do_search(self):
        kw = self.inp.text.strip()
        if not kw:
            return
        # 移除空状态引导（安全：只移一次，从 results 容器移除）
        if self._guide_visible:
            try:
                self.results.remove_widget(self.empty_guide)
            except Exception:
                pass
            self._guide_visible = False
        self.status.text = "🔄 查询中…"
        self.clear_results()
        threading.Thread(target=self._search, args=(kw,), daemon=True).start()

    def clear_results(self):
        self.results.clear_widgets()

    def _search(self, kw):
        try:
            items = search_company(kw)
            err = None
        except Exception as e:
            items, err = [], str(e)
        Clock.schedule_once(lambda dt: self._show(items, err))

    def _show(self, items, err):
        self.clear_results()
        if err:
            self.status.text = f"😢 错误：{err}"
            return
        if not items:
            self.status.text = "未找到结果。可在「我的」配置 API key。"
            return
        self.status.text = f"🎉 共 {len(items)} 条结果"
        for it in items:
            self.results.add_widget(self._card(it.get("name", ""), it.get("credit_code", "")))

    def _card(self, name, code):
        card = TapCard(padding=[14, 10], spacing=4, size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        n = lab(f"🏢 {name}", font_size=16, bold=True,
                size_hint_y=None, height=26)
        n.bind(width=lambda i, w: setattr(n, "text_size", (w, None)))
        card.add_widget(n)
        if code:
            c = lab(f"统一信用代码：{code}", font_size=13, color=C(PALETTE["sub"]),
                    size_hint_y=None, height=20)
            c.bind(width=lambda i, w: setattr(c, "text_size", (w, None)))
            card.add_widget(c)
        card.bind(on_press=lambda x: self.goto_detail(name))
        return card

    def goto_detail(self, name):
        try:
            self.manager.get_screen("detail").show(name)
            self.manager.current = "detail"
        except Exception:
            pass


# ═══════════════════════════
#  关注页 (Tab 2)
# ═══════════════════════════
class FollowScreen(Screen):
    MAX = 50

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "follow"
        root = BoxLayout(orientation="vertical", padding=[0, 10, 0, 0])
        # 标题栏
        hdr = BoxLayout(size_hint_y=None, height=46, padding=[16, 8])
        hdr.add_widget(lab("⭐ 关注企业", font_size=20, bold=True,
                           halign="left", valign="middle"))
        self.count_lbl = lab("0", font_size=13, color=C(PALETTE["sub"]),
                             halign="right", valign="middle")
        hdr.add_widget(self.count_lbl)
        root.add_widget(hdr)
        # 列表区
        self.sv = ScrollView()
        self.body = BoxLayout(orientation="vertical", size_hint_y=None,
                              spacing=8, padding=2)
        self.body.bind(minimum_height=self.body.setter("height"))
        self.sv.add_widget(self.body)
        root.add_widget(self.sv)
        self.add_widget(root)
        # 进入页面时刷新列表
        self.bind(on_enter=lambda *a: self._refresh())

    def _refresh(self):
        """从配置读取关注列表并渲染（进入/取消后都会调用）。"""
        try:
            from config import get_follow_list
            names = list(get_follow_list() or [])
        except Exception:
            names = []
        try:
            self.count_lbl.text = f"{len(names)}/{self.MAX}"
        except Exception:
            pass
        self.body.clear_widgets()
        if not names:
            self.body.add_widget(self._empty())
            return
        for name in names:
            try:
                self.body.add_widget(self._row_card(name))
            except Exception:
                pass

    def _empty(self):
        empty = BoxLayout(orientation="vertical", padding=[30, 30],
                          size_hint_y=None, spacing=8)
        empty.bind(minimum_height=empty.setter("height"))
        empty.add_widget(lab("⭐", font_size=48, halign="center", valign="middle",
                             color=C(PALETTE["sun"]), size_hint_y=None, height=64))
        empty.add_widget(lab("暂无关注企业", font_size=18, bold=True,
                             halign="center", size_hint_y=None, height=30))
        t2 = lab("在企业详情页点击收藏按钮，即可加入关注列表",
                 font_size=13, color=C(PALETTE["sub"]), halign="center",
                 size_hint_y=None, height=24)
        t2.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        empty.add_widget(t2)
        gbtn = CuteButton(text="🔍 去搜索企业", bg=C(PALETTE["primary"]),
                          size_hint=(0.6, None), height=44, radius=14)
        gbtn.bind(on_press=lambda x: setattr(self.manager, "current", "search"))
        empty.add_widget(gbtn)
        return empty

    def _row_card(self, name):
        card = CuteCard(padding=[12, 8], spacing=8, size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        row = BoxLayout(orientation="horizontal", size_hint_y=None,
                        height=44, spacing=8)
        # 左侧企业名（可点击进入详情）
        name_card = TapCard(padding=[2, 8], size_hint_x=0.68)
        nl = lab(f"🏢 {name}", font_size=15, bold=True,
                 size_hint_y=None, height=28)
        nl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        name_card.add_widget(nl)
        name_card.bind(on_press=lambda x: self._goto_detail(name))
        row.add_widget(name_card)
        # 右侧：取消关注（star 切换）
        star = CuteButton(text="⭐ 取消", bg=C(PALETTE["sun"]), radius=12,
                          size_hint_x=0.32, height=36)
        star.bind(on_press=lambda x: self._unfollow(name))
        row.add_widget(star)
        card.add_widget(row)
        return card

    def _unfollow(self, name):
        try:
            from config import toggle_follow
            toggle_follow(name)
        except Exception:
            pass
        self._refresh()

    def _goto_detail(self, name):
        try:
            self.manager.get_screen("detail").show(name)
            self.manager.current = "detail"
        except Exception:
            pass


# ═══════════════════════════
#  对比页 (Tab 3)
# ═══════════════════════════
class CompareScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "compare"
        root = BoxLayout(orientation="vertical", padding=[0, 10, 0, 0])
        hdr = BoxLayout(size_hint_y=None, height=46, padding=[16, 8])
        hdr.add_widget(lab("📊 企业对比", font_size=20, bold=True,
                           halign="left", valign="middle"))
        self.count_lbl = lab("A ↔ B", font_size=13, color=C(PALETTE["sub"]),
                             halign="right", valign="middle")
        hdr.add_widget(self.count_lbl)
        root.add_widget(hdr)
        self.sv = ScrollView()
        self.body = BoxLayout(orientation="vertical", size_hint_y=None,
                              spacing=10, padding=8)
        self.body.bind(minimum_height=self.body.setter("height"))
        self.sv.add_widget(self.body)
        root.add_widget(self.sv)
        self.add_widget(root)
        self.bind(on_enter=lambda *a: None)
        self._show_empty()

    # ── 空状态 / 输入区 ──
    def _show_empty(self):
        self.body.clear_widgets()
        inp_card = CuteCard(padding=[12, 10], spacing=8, size_hint_y=None)
        inp_card.bind(minimum_height=inp_card.setter("height"))
        inp_card.add_widget(lab("输入两家企业名称进行对比：",
                                font_size=14, color=C(PALETTE["text"]),
                                size_hint_y=None, height=22))
        self.a_inp = CuteInput(hint_text="企业 A 名称（如：腾讯）",
                               multiline=False, size_hint_y=None, height=40)
        self.b_inp = CuteInput(hint_text="企业 B 名称（如：阿里巴巴）",
                               multiline=False, size_hint_y=None, height=40)
        inp_card.add_widget(self.a_inp)
        inp_card.add_widget(self.b_inp)
        cmp_btn = CuteButton(text="🔍 开始对比", bg=C(PALETTE["primary"]),
                             size_hint_y=None, height=42, radius=14)
        cmp_btn.bind(on_press=lambda x: self._compare())
        inp_card.add_widget(cmp_btn)
        self.body.add_widget(inp_card)

        # 引导文案
        guide = BoxLayout(orientation="vertical", size_hint_y=None,
                          padding=[20, 10], spacing=4)
        guide.bind(minimum_height=guide.setter("height"))
        guide.add_widget(lab("📊", font_size=48, halign="center", valign="middle",
                             color=C(PALETTE["lavender"]), size_hint_y=None, height=64))
        guide.add_widget(lab("暂无对比数据", font_size=18, bold=True,
                             halign="center", size_hint_y=None, height=30))
        t2 = lab("输入两家企业名称，并排展示基本信息与扩展字段",
                 font_size=13, color=C(PALETTE["sub"]), halign="center",
                 size_hint_y=None, height=24)
        t2.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        guide.add_widget(t2)
        self.body.add_widget(guide)

    def _compare(self):
        na = (self.a_inp.text or "").strip()
        nb = (self.b_inp.text or "").strip()
        if not na or not nb:
            info_popup("提示", "请输入两家企业的名称。", emoji="ℹ️")
            return
        try:
            self.count_lbl.text = f"{na} ↔ {nb}"
        except Exception:
            pass
        self.body.clear_widgets()
        self.body.add_widget(lab("🔄 对比中…", color=C(PALETTE["sub"]),
                                  size_hint_y=None, height=30))
        threading.Thread(target=self._do_compare, args=(na, nb),
                         daemon=True).start()

    def _do_compare(self, na, nb):
        try:
            da = get_company_detail(na)
        except Exception:
            da = {"basic": {"name": na}, "dims": {}}
        try:
            db = get_company_detail(nb)
        except Exception:
            db = {"basic": {"name": nb}, "dims": {}}
        Clock.schedule_once(lambda dt: self._render_compare(da, db))

    def _render_compare(self, da, db):
        self.body.clear_widgets()
        # 宽屏（>600）并排，窄屏（手机）上下堆叠，均自适应
        if Window.width > 600:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, spacing=8)
            row.bind(minimum_height=row.setter("height"))
            row.add_widget(self._col_card(da, "A"))
            row.add_widget(self._col_card(db, "B"))
            self.body.add_widget(row)
        else:
            self.body.add_widget(self._col_card(da, "A"))
            self.body.add_widget(self._col_card(db, "B"))
        again = CuteButton(text="🔁 重新对比", bg=C(PALETTE["primary"]),
                           size_hint_y=None, height=42, radius=14)
        again.bind(on_press=lambda x: self._show_empty())
        self.body.add_widget(again)

    def _col_card(self, d, tag):
        d = d or {}
        card = CuteCard(padding=[12, 8], spacing=4, size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        b = d.get("basic") or {}
        name = b.get("name") or d.get("name") or "未知企业"
        title = f"{tag}. {name}"
        nl = lab(title, font_size=16, bold=True, size_hint_y=None)
        nl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 22)))
        card.bind(width=lambda i, w: setattr(nl, "text_size", (w - 24, None)))
        card.add_widget(nl)

        pairs = [
            ("法定代表人", b.get("legal_person")),
            ("注册资本", b.get("reg_capital")),
            ("成立日期", b.get("establish_time")),
            ("登记状态", b.get("reg_status")),
            ("统一信用代码", b.get("credit_code")),
            ("企业类型", b.get("org_type")),
            ("行业", b.get("category")),
            ("注册地址", b.get("reg_location")),
            ("经营范围", b.get("business_scope")),
            ("电话", b.get("phone")),
            ("邮箱", b.get("email")),
            ("官网", b.get("website")),
        ]
        for k, v in pairs:
            if v:
                vl = lab(f"{k}：{v}", font_size=13, size_hint_y=None)
                vl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 18)))
                card.bind(width=lambda i, w: setattr(vl, "text_size", (w - 24, None)))
                card.add_widget(vl)

        # 扩展字段（extra）：聚合维度
        dims = d.get("dims") or {}
        for key, title, _, _ in JUHE_DIMENSIONS:
            items = dims.get(key, []) or []
            if not items:
                continue
            hl = lab(f"· {title}", font_size=13, bold=True,
                     color=C(PALETTE["primary_d"]), size_hint_y=None)
            hl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 20)))
            card.bind(width=lambda i, w, lbl=hl: setattr(lbl, "text_size", (w - 24, None)))
            card.add_widget(hl)
            for it in items:
                rl = lab(f"   - {it}", font_size=12, color=C(PALETTE["sub"]),
                         size_hint_y=None)
                rl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 18)))
                card.bind(width=lambda i, w, lbl=rl: setattr(lbl, "text_size", (w - 24, None)))
                card.add_widget(rl)

        if not any(v for _, v in pairs) and not dims:
            card.add_widget(lab("暂无对比数据", font_size=13,
                                color=C(PALETTE["sub"]), size_hint_y=None, height=20))
        return card


# ═══════════════════════════
#  我的页 (Tab 4) - 列表式
# ═══════════════════════════
class ProfileScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "profile"
        self.scrape_on = bool(load_config().get("enable_scrape", True))
        self._fix_banner = None
        self._build_ui()
        self.bind(on_enter=self._on_enter_profile)

    def _build_ui(self):
        """构建UI，支持刷新时安全重建（不remove_widget）。"""
        # 清除旧内容
        self.clear_widgets()
        root = BoxLayout(orientation="vertical", padding=0, spacing=0)

        hdr = BoxLayout(size_hint_y=None, height=46, padding=[16, 8])
        hdr.add_widget(lab("👤 我的", font_size=20, bold=True,
                           halign="left", valign="middle"))
        root.add_widget(hdr)

        sv = ScrollView()
        inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=0,
                          padding=[0, 4])
        inner.bind(minimum_height=inner.setter("height"))

        cfg = load_config()
        W = inner.add_widget

        # ── 数据源配置 ──
        W(self._sec("📡  数据源配置"))
        W(self._row("API密钥管理", "配置6个免费数据源key", ">", self._go_api))
        W(self._row("自定义数据源", "接入你自己的API接口", ">", self._go_custom))
        scrape_txt = "开启" if self.scrape_on else "关闭"
        W(self._row("免费爬虫兜底", scrape_txt, ">", self._toggle_scrape))
        W(self._gap())

        # ── 缓存与高级 ──
        W(self._sec("🛠  缓存与高级"))
        W(self._row("清空本地缓存", "删除所有缓存数据", ">", self._clear_cache))
        W(self._row("请求超时", f"{cfg.get('timeout', 10)}秒", ">", self._edit_timeout))
        W(self._row("缓存有效期", f"{cfg.get('cache_days', 30)}天", ">", self._edit_cache_days))
        W(self._gap())

        # ── 修复中心（对标 Flutter settings_screen 的 _runRepair）──
        W(self._sec("🛠  修复中心"))
        W(self._row("一键诊断与修复", "网络/配置/缓存自检", ">", self._run_repair))
        W(self._gap())

        # ── 协议与关于 ──
        W(self._sec("📜  协议与关于"))
        W(self._row("关于企信查", "v1.3.0  com.qxx.johnny", ">", self._show_about))
        W(self._row("用户协议", "", ">", self._show_agreement))
        W(self._row("隐私政策", "", ">", self._show_privacy))
        W(self._row("免责声明", "数据来源说明", ">", self._show_disclaimer))
        W(self._gap())

        # ── 开发者 ──
        W(self._sec("👨‍💻  开发者"))
        W(self._row("开发者", legal.AUTHOR, ""))
        W(self._row("微信", legal.WECHAT, ""))
        W(self._row("邮箱", legal.EMAIL, ""))
        W(self._row("版权", f"© {legal.COPYRIGHT_YEAR} 企信查", ""))
        W(BoxLayout(size_hint_y=None, height=30))

        sv.add_widget(inner)
        root.add_widget(sv)
        self._root = root
        self.add_widget(root)

    # ── 行组件 ──
    def _sec(self, text):
        bl = BoxLayout(size_hint_y=None, height=36, padding=[16, 8])
        bl.add_widget(lab(text, font_size=14, bold=True,
                          color=C(PALETTE["primary_d"]), halign="left", valign="middle"))
        return bl

    def _gap(self):
        return BoxLayout(size_hint_y=None, height=10)

    def _row(self, title, sub="", right="", on_tap=None):
        bl = BoxLayout(orientation="horizontal", size_hint_y=None, height=50,
                       padding=[16, 6, 16, 6])
        # 左侧
        left = BoxLayout(orientation="vertical", size_hint_x=0.65)
        t = lab(title, font_size=15, halign="left", valign="middle",
                size_hint_y=None, height=24)
        t.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 20)))
        left.bind(width=lambda i, w: setattr(t, "text_size", (w, None)))
        left.add_widget(t)
        if sub:
            s = lab(sub, font_size=12, color=C(PALETTE["sub"]),
                    halign="left", valign="middle", size_hint_y=None, height=18)
            s.bind(texture_size=lambda i, v: setattr(i, "height", max(v[1], 16)))
            left.bind(width=lambda i, w: setattr(s, "text_size", (w, None)))
            left.add_widget(s)
        bl.add_widget(left)
        # 右侧
        r = lab(right, font_size=13, color=C(PALETTE["sub"]),
                halign="right", valign="middle", size_hint_x=0.35)
        bl.add_widget(r)
        # 点击（用 on_touch_up 命中判定，且不消费滚动事件，
        # 让外层 ScrollView 能正常滚动，避免误触导航）
        if on_tap:
            def _tap(inst, touch):
                if touch.is_mouse_scrolling:
                    return False
                if inst.collide_point(*touch.pos):
                    on_tap()
                return False  # 不消费触摸，允许 ScrollView 滚动
            bl.bind(on_touch_up=_tap)
        return bl

    # ── 操作（不再 remove_widget self！安全刷新） ──
    def _go_api(self):
        try:
            self.manager.current = "api_config"
        except Exception:
            pass

    def _go_custom(self):
        try:
            self.manager.current = "custom_config"
        except Exception:
            pass

    def _toggle_scrape(self):
        self.scrape_on = not self.scrape_on
        set_key("enable_scrape", self.scrape_on)
        # 安全刷新：直接重建UI（不remove_widget）
        self._build_ui()
        info_popup("爬虫兜底",
                   f"免费网页抓取兜底：{'开启 ✅' if self.scrape_on else '关闭 ❌'}",
                   emoji="🕷")

    def _edit_timeout(self):
        cur = str(load_config().get("timeout", 10))
        def _save(v):
            try:
                if v.isdigit():
                    set_key("timeout", int(v))
            except Exception:
                pass
            self._build_ui()
            info_popup("保存成功", f"✅ 请求超时已更新为 {v}秒", emoji="✅")
        edit_popup("请求超时(秒)", cur, _save, input_type="number")

    def _edit_cache_days(self):
        cur = str(load_config().get("cache_days", 30))
        def _save(v):
            try:
                if v.isdigit():
                    set_key("cache_days", int(v))
            except Exception:
                pass
            self._build_ui()
            info_popup("保存成功", f"✅ 缓存有效期已更新为 {v}天", emoji="✅")
        edit_popup("缓存有效期(天)", cur, _save, input_type="number")

    def _clear_cache(self):
        def _do():
            try:
                from cache import clear_all
                clear_all()
                info_popup("提示", "🧹 本地缓存已清空。", emoji="🧹")
            except Exception as e:
                info_popup("提示", f"清空失败：{e}", emoji="😢")
        confirm_popup("清空缓存", "确定要清空全部本地缓存吗？",
                      yes_text="确定清空", on_yes=_do, emoji="🧹")

    def _show_about(self):
        info_popup("关于企信查",
                   f"企信查 v1.3.0\n包名：com.qxx.johnny\n目标：Android 12–16\n\n"
                   f"类「天眼查」风格企业信息检索学习作品。\n\n"
                   f"开发者：{legal.AUTHOR}\n微信：{legal.WECHAT}\n"
                   f"邮箱：{legal.EMAIL}\n版权所有 © {legal.COPYRIGHT_YEAR}",
                   emoji="💡")

    def _show_agreement(self):
        info_popup("用户协议", legal.USER_AGREEMENT, emoji="📄")

    def _show_privacy(self):
        info_popup("隐私政策", legal.PRIVACY_POLICY, emoji="🔒")

    def _show_disclaimer(self):
        info_popup("免责声明", legal.DISCLAIMER, btn_text="我知道了", emoji="⚠️")

    # ── 启动自动修复提示（顶部 banner）──
    def _on_enter_profile(self, *a):
        """进入「我的」页时，若启动期有自动修复则显示提示 banner。"""
        try:
            old = getattr(self, "_fix_banner", None)
            if old is not None:
                try:
                    if old.parent is not None:
                        old.parent.remove_widget(old)
                except Exception:
                    pass
                self._fix_banner = None
            app = self.manager.app
            fixes = getattr(app, "startup_fixes", None) or []
            if fixes:
                banner = CuteButton(
                    text=f"🧰 本次启动已自动修复 {len(fixes)} 项（点击查看）",
                    bg=C(PALETTE["sun"]), radius=14, size_hint_y=None, height=40)
                banner.bind(on_press=lambda x: self._show_startup_fixes())
                # 插入到标题栏之后（root 的第二个子控件）
                self._root.add_widget(banner, index=1)
                self._fix_banner = banner
        except Exception:
            pass

    def _show_startup_fixes(self):
        fixes = []
        try:
            app = self.manager.app
            fixes = list(getattr(app, "startup_fixes", []) or [])
        except Exception:
            fixes = []
        if not fixes:
            info_popup("启动自动修复", "本次启动无需修复。", emoji="🧰")
            return
        lines = []
        for r in fixes:
            mark = "✅" if getattr(r, "ok", True) else "⚠️"
            lines.append(f"{mark} {r.name}：{r.detail}")
        info_popup("启动自动修复", "\n".join(lines), emoji="🧰")

    # ── 一键诊断与修复（对标 Flutter _runRepair/_showReport）──
    def _run_repair(self):
        svc = None
        try:
            app = self.manager.app
            svc = getattr(app, "_repair", None)
        except Exception:
            svc = None
        if svc is None and _HAS_REPAIR:
            try:
                svc = RepairService()
            except Exception:
                svc = None
        if svc is None:
            info_popup("修复中心", "修复服务当前不可用，请稍后重试。", emoji="⚠️")
            return

        wait_pop = info_popup("修复中心", "🔧 正在诊断与修复，请稍候…", emoji="🛠")

        def _work():
            try:
                report = svc.run_repair()
            except Exception as e:
                report = [RepairResult("修复中心", False, f"修复过程异常：{e}")]
            try:
                def _done(dt):
                    try:
                        if wait_pop:
                            wait_pop.dismiss()
                    except Exception:
                        pass
                    self._show_report(report)
                Clock.schedule_once(_done)
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    def _show_report(self, report):
        if not report:
            info_popup("修复报告", "未获取到诊断结果。", emoji="🛠")
            return
        lines = []
        for r in report:
            if r.fixed:
                mark = "🔧"  # 已执行修复
            else:
                mark = "✅" if r.ok else "⚠️"
            lines.append(f"{mark} {r.name}：{r.detail}")
        info_popup("修复报告", "\n".join(lines), emoji="🛠")


# ═══════════════════════════
#  API密钥配置页
# ═══════════════════════════
class ApiConfigScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "api_config"
        root = BoxLayout(orientation="vertical", padding=[0, 8, 0, 0])
        # 返回栏
        hdr = BoxLayout(size_hint_y=None, height=44, padding=[12, 6])
        back = CuteButton(text="←", bg=C(PALETTE["sub"]), size_hint_x=0.2,
                          height=36, radius=14)
        back.bind(on_press=lambda x: setattr(self.manager, "current", "profile"))
        hdr.add_widget(back)
        hdr.add_widget(lab("🔑 API密钥管理", font_size=18, bold=True,
                           halign="left", valign="middle"))
        root.add_widget(hdr)

        sv = ScrollView()
        inner = BoxLayout(orientation="vertical", size_hint_y=None,
                          padding=[12, 8], spacing=6)
        inner.bind(minimum_height=inner.setter("height"))

        # 说明（自适应宽度）
        tip = lab("在以下免费平台注册后填入 key：\n"
                  "· apibyte.cn（工商基础）\n"
                  "· xxapi.cn（股东/变更）\n"
                  "· jisuapi.com（字段极全）\n"
                  "· juhe.cn（31维度全）\n"
                  "· openapi.tianyancha.com（分支）\n"
                  "· openapi.qcc.com（全维度）",
                  font_size=13, color=C(PALETTE["sub"]), size_hint_y=None)
        tip.bind(texture_size=lambda i, s: setattr(i, "height", s[1] + 6))
        inner.bind(width=lambda i, w: setattr(tip, "text_size", (w - 24, None)))
        inner.add_widget(tip)

        cfg = load_config()
        self.fields = {}
        for label, key in [("apibyte key", "apibyte_key"),
                           ("xxapi key", "xxapi_key"),
                           ("jisuapi key", "jisuapi_key"),
                           ("聚合数据 key", "juhe_key"),
                           ("天眼查 key", "tianyancha_key"),
                           ("企查查 key", "qcc_key")]:
            lbl = lab(label, font_size=13, size_hint_y=None, height=18)
            lbl.bind(width=lambda i, w: setattr(lbl, "text_size", (w, None)))
            inner.add_widget(lbl)
            ti = CuteInput(text=cfg.get(key, ""), multiline=False,
                           size_hint_y=None, height=40)
            self.fields[key] = ti
            inner.add_widget(ti)

        save = CuteButton(text="💾 保存", bg=C(PALETTE["primary"]),
                          size_hint_y=None, height=44, radius=14)
        save.bind(on_press=lambda x: self._save())
        inner.add_widget(save)

        sv.add_widget(inner)
        root.add_widget(sv)
        self.add_widget(root)

    def _save(self):
        for key, ti in self.fields.items():
            set_key(key, ti.text.strip())
        info_popup("保存成功", "✅ API密钥已保存。", emoji="✅")
        try:
            self.manager.current = "profile"
        except Exception:
            pass


# ═══════════════════════════
#  自定义数据源配置页
# ═══════════════════════════
class CustomConfigScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "custom_config"
        root = BoxLayout(orientation="vertical", padding=[0, 8, 0, 0])
        hdr = BoxLayout(size_hint_y=None, height=44, padding=[12, 6])
        back = CuteButton(text="←", bg=C(PALETTE["sub"]), size_hint_x=0.2,
                          height=36, radius=14)
        back.bind(on_press=lambda x: setattr(self.manager, "current", "profile"))
        hdr.add_widget(back)
        hdr.add_widget(lab("➕ 自定义数据源", font_size=18, bold=True,
                           halign="left", valign="middle"))
        root.add_widget(hdr)

        sv = ScrollView()
        inner = BoxLayout(orientation="vertical", size_hint_y=None,
                          padding=[12, 8], spacing=6)
        inner.bind(minimum_height=inner.setter("height"))

        tip = lab("接入你自己的API接口，用于工商基础查询。",
                  font_size=13, color=C(PALETTE["sub"]),
                  size_hint_y=None, height=22)
        tip.bind(width=lambda i, w: setattr(tip, "text_size", (w - 24, None)))
        inner.add_widget(tip)

        cfg = load_config()
        cc = (cfg.get("custom_apis") or [{}])[0]
        self.cust = {}
        for clabel, ckey in [("名称", "name"),
                             ("接口URL（{kw}占位企业名）", "url"),
                             ("API Key", "key"),
                             ("请求头模板", "header"),
                             ("字段映射JSON", "mapping")]:
            lbl = lab(clabel, font_size=13, size_hint_y=None, height=18)
            lbl.bind(width=lambda i, w: setattr(lbl, "text_size", (w, None)))
            inner.add_widget(lbl)
            ti = CuteInput(text=str(cc.get(ckey, "")), multiline=False,
                           size_hint_y=None, height=40)
            self.cust[ckey] = ti
            inner.add_widget(ti)

        csave = CuteButton(text="💾 保存自定义源", bg=C(PALETTE["mint"]),
                           size_hint_y=None, height=44, radius=14)
        csave.bind(on_press=lambda x: self._save_custom())
        inner.add_widget(csave)

        sv.add_widget(inner)
        root.add_widget(sv)
        self.add_widget(root)

    def _save_custom(self):
        c = {k: self.cust[k].text.strip() for k in self.cust}
        if c.get("url"):
            cfg = load_config()
            cfg["custom_apis"] = [c]
            save_config(cfg)
        info_popup("保存成功", "✅ 自定义数据源已保存。", emoji="✅")
        try:
            self.manager.current = "profile"
        except Exception:
            pass


# ═══════════════════════════
#  企业详情页
# ═══════════════════════════
class DetailScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "detail"
        self.cur_name = ""
        self.root_layout = BoxLayout(orientation="vertical", padding=[0, 8, 0, 0])
        top = BoxLayout(size_hint_y=None, height=44, padding=[12, 6])
        back = CuteButton(text="← 返回", bg=C(PALETTE["sub"]),
                          size_hint_x=0.18, height=38, radius=14)
        back.bind(on_press=lambda x: setattr(self.manager, "current", "search"))
        title = lab("🔎 企业详情", font_size=17, bold=True,
                    color=C(PALETTE["primary_d"]), halign="center", valign="middle",
                    size_hint_x=0.5)
        top.add_widget(back)
        top.add_widget(title)
        # 收藏 / 取消收藏按钮
        self.star_btn = CuteButton(text="☆ 收藏", bg=C(PALETTE["sun"]),
                                   size_hint_x=0.32, height=38, radius=14)
        self.star_btn.bind(on_press=lambda x: self._toggle_follow())
        top.add_widget(self.star_btn)
        self.root_layout.add_widget(top)

        self.sv = ScrollView()
        self.body = BoxLayout(orientation="vertical", size_hint_y=None,
                              padding=[8, 4], spacing=8)
        self.body.bind(minimum_height=self.body.setter("height"))
        self.sv.add_widget(self.body)
        self.root_layout.add_widget(self.sv)
        self.add_widget(self.root_layout)

    def _update_star(self, followed):
        try:
            self.star_btn.text = "⭐ 已收藏" if followed else "☆ 收藏"
        except Exception:
            pass

    def _toggle_follow(self):
        name = (self.cur_name or "").strip()
        if not name:
            return
        try:
            from config import toggle_follow, is_followed
            toggle_follow(name)
            followed = is_followed(name)
        except Exception:
            followed = False
        self._update_star(followed)
        info_popup("收藏",
                   f"{'已加入关注 ⭐' if followed else '已取消收藏'}，{name}",
                   emoji="⭐")

    def show(self, name):
        self.cur_name = name
        try:
            from config import is_followed
            self._update_star(bool(is_followed(name)))
        except Exception:
            self._update_star(False)
        self.body.clear_widgets()
        self.body.add_widget(lab("🔄 加载中…", color=C(PALETTE["sub"]),
                                 size_hint_y=None, height=30))
        threading.Thread(target=self._load, args=(name,), daemon=True).start()

    def _load(self, name):
        try:
            d = get_company_detail(name)
            err = None
        except Exception as e:
            d, err = None, str(e)
        Clock.schedule_once(lambda dt: self._render(name, d, err))

    def _sec_card(self, key, title, rows, source=""):
        emoji = EMOJI.get(key, "📌")
        card = CuteCard(padding=[12, 8], spacing=4, size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        hdr = f"{title}   · 源：{source}" if source else title
        hl = lab(f"{emoji} {hdr}", font_size=15, bold=True,
                 color=C(PALETTE["primary_d"]), size_hint_y=None)
        hl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 22)))
        card.bind(width=lambda i, w: setattr(hl, "text_size", (w - 24, None)))
        card.add_widget(hl)
        if not rows:
            nl = lab("· 暂无数据", font_size=13, color=C(PALETTE["sub"]),
                     size_hint_y=None)
            nl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 18)))
            card.bind(width=lambda i, w: setattr(nl, "text_size", (w - 24, None)))
            card.add_widget(nl)
        for r in rows:
            rl = lab("· " + str(r), font_size=14, size_hint_y=None)
            rl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 18)))
            card.bind(width=lambda i, w: setattr(rl, "text_size", (w - 24, None)))
            card.add_widget(rl)
        self.body.add_widget(card)

    def _render(self, name, d, err):
        self.body.clear_widgets()
        if err:
            self.body.add_widget(lab(f"😢 加载失败：{err}",
                                     color=C(PALETTE["danger"]),
                                     size_hint_y=None, height=30))
            return
        if not d:
            self.body.add_widget(lab("😢 无数据",
                                     color=C(PALETTE["danger"]),
                                     size_hint_y=None, height=30))
            return
        # 数据源 banner
        src = d.get("sources") or []
        banner = "当前数据源：" + ("、".join(src) if src else "兜底网页抓取")
        bcard = CuteCard(bg=C(PALETTE["chip"]), border=C(PALETTE["primary"]),
                         padding=[10, 6], spacing=4, size_hint_y=None)
        bcard.bind(minimum_height=bcard.setter("height"))
        bl = lab("📡 " + banner, font_size=14, bold=True,
                 color=C(PALETTE["primary_d"]), size_hint_y=None)
        bl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 20)))
        bcard.bind(width=lambda i, w: setattr(bl, "text_size", (w - 20, None)))
        bcard.add_widget(bl)
        self.body.add_widget(bcard)

        # 基础信息
        b = d.get("basic") or {}
        card = CuteCard(padding=[12, 8], spacing=4, size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        nl = lab(b.get("name", name), font_size=18, bold=True, size_hint_y=None)
        nl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 24)))
        card.bind(width=lambda i, w: setattr(nl, "text_size", (w - 24, None)))
        card.add_widget(nl)

        pairs = [
            ("法定代表人", b.get("legal_person")),
            ("注册资本", b.get("reg_capital")),
            ("成立日期", b.get("establish_time")),
            ("登记状态", b.get("reg_status")),
            ("统一信用代码", b.get("credit_code")),
            ("企业类型", b.get("org_type")),
            ("行业", b.get("category")),
            ("注册地址", b.get("reg_location")),
            ("经营范围", b.get("business_scope")),
            ("省份", b.get("province")),
            ("曾用名", b.get("history_name")),
            ("登记机关", b.get("reg_organ")),
            ("核准日期", b.get("approval_date")),
            ("电话", b.get("phone")),
            ("邮箱", b.get("email")),
            ("官网", b.get("website")),
            ("参保人数", b.get("insure_num")),
            ("是否上市", b.get("is_listed")),
        ]
        for k, v in pairs:
            if v:
                vl = lab(f"{k}：{v}", font_size=14, size_hint_y=None)
                vl.bind(texture_size=lambda i, s: setattr(i, "height", max(s[1], 18)))
                card.bind(width=lambda i, w: setattr(vl, "text_size", (w - 24, None)))
                card.add_widget(vl)
        self.body.add_widget(card)

        ms = d.get("module_sources", {})
        self._sec_card("shareholders", "股东信息",
                       [f"{s.get('name')}（{s.get('ratio')}，{s.get('amount')}）"
                        for s in d.get("shareholders", [])], ms.get("shareholders", ""))
        self._sec_card("changes", "变更记录",
                       [f"{c.get('item')} @ {c.get('time')}" for c in d.get("changes", [])],
                       ms.get("changes", ""))
        self._sec_card("key_persons", "主要人员",
                       [f"{p.get('name')}（{p.get('position')}）"
                        for p in d.get("key_persons", [])], ms.get("key_persons", ""))
        self._sec_card("investments", "对外投资",
                       [f"{i.get('name')}（{i.get('ratio')}）"
                        for i in d.get("investments", [])], ms.get("investments", ""))
        self._sec_card("branches", "分支机构",
                       [br.get("name", "") for br in d.get("branches", [])],
                       ms.get("branches", ""))
        for key, title, _, _ in JUHE_DIMENSIONS:
            self._sec_card(key, title, d.get("dims", {}).get(key, []), ms.get(key, ""))


# ═══════════════════════════
#  底部导航栏 + App 入口
# ═══════════════════════════
TABS = [("🔍", "搜索", "search"),
        ("⭐", "关注", "follow"),
        ("📊", "对比", "compare"),
        ("👤", "我的", "profile")]

class QXApp(App):
    current_tab = "search"

    def build(self):
        # ── 启动自动修复（在构建 UI 前，绝不因修复失败而崩溃）──
        self._repair = None
        self.startup_fixes = []
        if _HAS_REPAIR:
            try:
                self._repair = RepairService()
                self.startup_fixes = list(self._repair.auto_repair() or [])
            except Exception as e:
                print(f"[企信查] 启动自动修复异常（已忽略）: {e}")
                self.startup_fixes = []

        # ── 全面容错：任何异常都不让 app 崩溃 ──
        try:
            return self._build_inner()
        except Exception as e:
            print(f"[企信查] 启动异常: {e}")
            traceback.print_exc()
            # 降级：显示最简错误界面（至少不会闪退）
            return self._fallback_screen(e)

    def _build_inner(self):
        Window.clearcolor = C(PALETTE["bg"])
        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.add_widget(SearchScreen())
        self.sm.add_widget(FollowScreen())
        self.sm.add_widget(CompareScreen())
        self.sm.add_widget(ProfileScreen())
        self.sm.add_widget(DetailScreen())
        self.sm.add_widget(ApiConfigScreen())
        self.sm.add_widget(CustomConfigScreen())

        # ── 根容器 ──
        root = BoxLayout(orientation="vertical")
        root.add_widget(self.sm)

        # ── 底部导航栏 ──
        nav = BoxLayout(size_hint_y=None, height=56, spacing=0, padding=[0, 0, 0, 2])
        with nav.canvas.before:
            Color(*C(PALETTE["nav_bg"]))
            self._nav_bg = Rectangle(pos=nav.pos, size=nav.size)
            Color(*C(PALETTE["line"]))
            self._nav_line = Rectangle(
                pos=(nav.pos[0], nav.pos[1] + nav.size[1] - 1),
                size=(nav.size[0], 1))
        nav.bind(pos=lambda i, p: setattr(self._nav_bg, "pos", p),
                 size=lambda i, s: setattr(self._nav_bg, "size", s))

        self.nav_tabs = []
        for emoji, text, sn in TABS:
            box = BoxLayout(orientation="vertical", spacing=2,
                            size_hint_x=0.25, padding=[0, 6, 0, 4])
            e_lbl = Label(**_font_kw(text=emoji, font_size=22),
                         color=C(PALETTE["nav_on"]) if sn == "search" else C(PALETTE["nav_off"]),
                         halign="center", valign="middle",
                         size_hint_y=None, height=28)
            t_lbl = Label(**_font_kw(text=text, font_size=11),
                         color=C(PALETTE["nav_on"]) if sn == "search" else C(PALETTE["nav_off"]),
                         halign="center", valign="middle",
                         size_hint_y=None, height=16)
            box.add_widget(e_lbl)
            box.add_widget(t_lbl)
            self.nav_tabs.append((sn, e_lbl, t_lbl))
            nav.add_widget(box)

        # 导航栏触摸事件（安全方式）
        def _nav_touch(inst, touch):
            if touch.is_mouse_scrolling:
                return False
            for sn, e_lbl, t_lbl in self.nav_tabs:
                if e_lbl.parent and e_lbl.parent.collide_point(*touch.pos):
                    self._switch(sn)
                    return True
            return False
        nav.bind(on_touch_down=_nav_touch)

        root.add_widget(nav)

        # 监听 Screen 切换
        self.sm.bind(current=self._on_screen)

        # 首次启动弹免责声明
        cfg = load_config()
        if not cfg.get("agreed_disclaimer"):
            Clock.schedule_once(lambda dt: info_popup(
                "数据来源与免责声明", legal.DISCLAIMER,
                btn_text="我已阅读并同意", emoji="📢",
                on_close=_mark_agreed), 0.5)
        return root

    def _fallback_screen(self, error):
        """启动失败时的降级界面——至少能显示，不会闪退。"""
        root = BoxLayout(orientation="vertical", padding=20, spacing=10)
        root.add_widget(Label(text="企信查", font_size=24, bold=True,
                              color=C(PALETTE["primary_d"]), halign="center"))
        root.add_widget(Label(text=f"启动遇到问题：\n{error}",
                              font_size=14, halign="center", valign="middle"))
        retry = Button(text="重新加载", size_hint_y=None, height=44)
        retry.bind(on_press=lambda x: self._retry())
        root.add_widget(retry)
        root.add_widget(Label(text="如持续异常，请联系开发者",
                              font_size=12, color=C(PALETTE["sub"]), halign="center"))
        return root

    def _retry(self):
        """重试启动：重建 self.root 本身，避免界面双重嵌套。"""
        try:
            old = self.root
            new_root = self._build_inner()
            self.root = new_root
            # 从窗口移除旧 root，再添加新 root
            if old is not None:
                try:
                    parent = old.parent
                    if parent is not None:
                        parent.remove_widget(old)
                    else:
                        Window.remove_widget(old)
                except Exception:
                    pass
            try:
                Window.add_widget(new_root)
            except Exception:
                pass
        except Exception as e:
            # 再次失败，重建最简错误界面并替换
            try:
                old = self.root
                if old is not None:
                    p = old.parent
                    if p is not None:
                        p.remove_widget(old)
                    else:
                        Window.remove_widget(old)
            except Exception:
                pass
            self.root = Label(
                text=f"重试仍失败：{e}\n\n请卸载重装或联系开发者\n微信：{legal.WECHAT}",
                font_size=14, halign="center")
            try:
                Window.add_widget(self.root)
            except Exception:
                pass

    def _switch(self, sn):
        if sn in ("search", "follow", "compare", "profile"):
            self.sm.current = sn
            self.current_tab = sn
            self._update_nav(sn)

    def _on_screen(self, sm, screen_name):
        tab_map = {"search": "search", "follow": "follow",
                   "compare": "compare", "profile": "profile",
                   "detail": "search", "api_config": "profile",
                   "custom_config": "profile"}
        active = tab_map.get(screen_name, "search")
        self._update_nav(active)

    def _update_nav(self, active):
        for sn, e_lbl, t_lbl in self.nav_tabs:
            if sn == active:
                e_lbl.color = C(PALETTE["nav_on"])
                t_lbl.color = C(PALETTE["nav_on"])
            else:
                e_lbl.color = C(PALETTE["nav_off"])
                t_lbl.color = C(PALETTE["nav_off"])


if __name__ == "__main__":
    QXApp().run()
