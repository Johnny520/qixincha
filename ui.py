# -*- coding: utf-8 -*-
"""企信查 · 蓝系 UI 主题与可复用组件。

参照天眼查风格，集中管理蓝系调色板、圆角卡片 / 按钮 / 输入框，
以及通用弹窗。所有弹窗、文字均自适应屏幕宽度，不会截断。
"""
import os

from kivy.graphics import Color, RoundedRectangle, Line
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex

BASE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(BASE, "fonts", "NotoSansSC.ttf")
if not os.path.exists(FONT):
    FONT = None

# ── 蓝系调色板（天眼查风格）──
PALETTE = {
    "bg":        "#F0F4F8",
    "card":      "#FFFFFF",
    "primary":   "#3B82F6",
    "primary_d": "#1D4ED8",
    "mint":      "#10B981",
    "lavender":  "#8B5CF6",
    "sky":       "#60A5FA",
    "sun":       "#F59E0B",
    "text":      "#1F2937",
    "sub":       "#6B7280",
    "danger":    "#EF4444",
    "line":      "#E5E7EB",
    "chip":      "#DBEAFE",
    "nav_bg":    "#FFFFFF",
    "nav_on":    "#3B82F6",
    "nav_off":   "#9CA3AF",
}


def C(hexstr):
    """hex 字符串 -> Kivy rgba 元组。"""
    return get_color_from_hex(hexstr)


def _darker(rgba, f=0.88):
    return [max(0.0, c * f) for c in rgba[:3]] + [rgba[3]]


def _font_kw(**kw):
    """安全地设置 font_name：只有字体存在时才指定。"""
    if FONT:
        kw["font_name"] = FONT
    return kw


class _Round:
    """为任意 Widget 叠加一个圆角矩形背景（及可选描边）。"""

    def _setup_round(self, bg, radius=20, border=None, border_w=1.5):
        self._r_bg = list(bg)
        self._r_radius = radius
        self._r_border = border
        self._r_border_w = border_w
        with self.canvas.before:
            self._r_color = Color(*bg)
            self._r_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[radius])
            if border is not None:
                self._r_lcolor = Color(*border)
                self._r_line = Line(
                    rounded_rectangle=(self.pos[0], self.pos[1],
                                       self.size[0], self.size[1], radius),
                    width=border_w)
        self.bind(pos=self._r_redraw, size=self._r_redraw)

    def _r_redraw(self, *a):
        self._r_rect.pos = self.pos
        self._r_rect.size = self.size
        if self._r_border is not None:
            self._r_line.rounded_rectangle = (
                self.pos[0], self.pos[1],
                self.size[0], self.size[1], self._r_radius)


class CuteButton(_Round, Button):
    """圆角按钮，按下有轻微变深反馈。font_name 安全处理。"""

    def __init__(self, bg=None, radius=22, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("color", C("#FFFFFF"))
        kw.setdefault("bold", True)
        fkw = _font_kw(**kw)
        super().__init__(**fkw)
        base = bg or C(PALETTE["primary"])
        self._base_bg = base
        self._setup_round(base, radius)
        self.bind(on_press=lambda *a: setattr(self._r_color, "rgba", _darker(self._base_bg)))
        self.bind(on_release=lambda *a: setattr(self._r_color, "rgba", self._base_bg))

    def set_base(self, color):
        """运行时切换底色。"""
        self._base_bg = color
        self._r_color.rgba = color


class CuteCard(_Round, BoxLayout):
    """圆角卡片容器，默认白底浅灰描边。"""

    def __init__(self, bg=None, radius=20, border=None, border_w=1.5, **kw):
        kw.setdefault("orientation", "vertical")
        super().__init__(**kw)
        self._setup_round(
            bg or C(PALETTE["card"]), radius,
            border if border is not None else C(PALETTE["line"]), border_w)


class CuteInput(_Round, TextInput):
    """圆角输入框，font_name 安全处理。"""

    def __init__(self, radius=16, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("foreground_color", C(PALETTE["text"]))
        kw.setdefault("hint_text_color", C(PALETTE["sub"]))
        kw.setdefault("cursor_color", C(PALETTE["primary_d"]))
        kw.setdefault("padding", [12, 9, 12, 9])
        fkw = _font_kw(**kw)
        super().__init__(**fkw)
        self._setup_round(C("#FFFFFF"), radius,
                          border=C(PALETTE["line"]), border_w=1.5)


class CuteLabel(_Round, Label):
    """可选圆角底的小标签 / 徽标。"""

    def __init__(self, bg=None, radius=14, **kw):
        fkw = _font_kw(**kw)
        kw = fkw
        kw.setdefault("color", C(PALETTE["text"]))
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "top")
        super().__init__(**kw)
        if bg is not None:
            self._setup_round(bg, radius)


# ── 自适应弹窗 ──
# 弹窗宽度 = 屏幕宽度 * 0.92，不会超出屏幕
def info_popup(title, text, btn_text="知道了", on_close=None, emoji="ℹ️"):
    """通用滚动信息弹窗，自适应屏幕宽度。"""
    pw = max(Window.width * 0.92, 280)
    ph = max(Window.height * 0.78, 400)
    lay = BoxLayout(orientation="vertical", spacing=10, padding=14)
    sv = ScrollView(size_hint=(1, 1))
    lbl = Label(**_font_kw(text=text, font_size=14, color=C(PALETTE["text"]),
                            halign="left", valign="top", size_hint_y=None))
    lbl.bind(texture_size=lambda i, s: setattr(i, "height", s[1] + 4))
    # 文字宽度跟随弹窗内容区宽度（自适应）
    sv.bind(width=lambda i, w: setattr(lbl, "text_size", (w - 20, None)))
    sv.add_widget(lbl)
    lay.add_widget(sv)
    btn = CuteButton(text=btn_text, bg=C(PALETTE["primary"]),
                     size_hint_y=None, height=48)
    lay.add_widget(btn)
    popup = Popup(title=f"{emoji}  {title}", content=lay,
                  size_hint=(None, None), size=(pw, ph),
                  auto_dismiss=False, **_font_kw(title_color=C(PALETTE["text"])),
                  background_color=C(PALETTE["bg"]))
    popup.separator_color = C(PALETTE["line"])

    def _close(*a):
        popup.dismiss()
        if on_close:
            on_close()

    btn.bind(on_press=_close)
    popup.open()
    return popup


def confirm_popup(title, text, yes_text="确定", no_text="取消",
                  on_yes=None, emoji="❓"):
    """确认弹窗（两个按钮），自适应屏幕。"""
    pw = max(Window.width * 0.88, 260)
    ph = max(Window.height * 0.55, 320)
    lay = BoxLayout(orientation="vertical", spacing=10, padding=14)
    body = Label(**_font_kw(text=text, font_size=14, color=C(PALETTE["text"]),
                            halign="left", valign="top", size_hint_y=1))
    # 文字宽度跟随弹窗内容区
    lay.bind(width=lambda i, w: setattr(body, "text_size", (w - 28, None)))
    lay.add_widget(body)
    row = BoxLayout(size_hint_y=None, height=48, spacing=10)
    no = CuteButton(text=no_text, bg=C(PALETTE["sub"]))
    yes = CuteButton(text=yes_text, bg=C(PALETTE["danger"]))
    row.add_widget(no)
    row.add_widget(yes)
    lay.add_widget(row)
    popup = Popup(title=f"{emoji}  {title}", content=lay,
                  size_hint=(None, None), size=(pw, ph),
                  auto_dismiss=False, **_font_kw(title_color=C(PALETTE["text"])),
                  background_color=C(PALETTE["bg"]))

    def _no(*a):
        popup.dismiss()

    def _yes(*a):
        popup.dismiss()
        if on_yes:
            on_yes()

    no.bind(on_press=_no)
    yes.bind(on_press=_yes)
    popup.open()
    return popup


def edit_popup(title, cur_value, on_save, input_type="text"):
    """编辑单个字段的弹窗，自适应屏幕。"""
    pw = max(Window.width * 0.85, 240)
    ph = max(Window.height * 0.35, 220)
    lay = BoxLayout(orientation="vertical", spacing=12, padding=14)
    inp = CuteInput(text=cur_value, multiline=False, size_hint_y=None, height=46)
    if input_type == "number":
        inp.input_type = "number"
    lay.add_widget(inp)
    btn_row = BoxLayout(size_hint_y=None, height=46, spacing=10)
    cancel = CuteButton(text="取消", bg=C(PALETTE["sub"]), radius=14)
    save_btn = CuteButton(text="保存", bg=C(PALETTE["primary"]), radius=14)
    btn_row.add_widget(cancel)
    btn_row.add_widget(save_btn)
    lay.add_widget(btn_row)
    popup = Popup(title=title, content=lay,
                  size_hint=(None, None), size=(pw, ph),
                  auto_dismiss=False, **_font_kw(title_color=C(PALETTE["text"])),
                  background_color=C(PALETTE["bg"]))
    popup.separator_color = C(PALETTE["line"])

    def _cancel(*a):
        popup.dismiss()

    def _save(*a):
        v = inp.text.strip()
        popup.dismiss()
        on_save(v)

    cancel.bind(on_press=_cancel)
    save_btn.bind(on_press=_save)
    popup.open()
    return popup
