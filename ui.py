# -*- coding: utf-8 -*-
"""企信查 · 蓝系 UI 主题与可复用组件。

参照天眼查风格，集中管理蓝系调色板、圆角卡片 / 按钮 / 输入框，
底部导航栏、列表式设置行，以及通用弹窗，让所有界面保持一致。
"""
import os

from kivy.graphics import Color, RoundedRectangle, Line
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
    "bg":        "#F0F4F8",  # 整体背景：浅蓝灰
    "card":      "#FFFFFF",  # 卡片：纯白
    "primary":   "#3B82F6",  # 主色：蓝色
    "primary_d": "#1D4ED8",  # 主色深
    "mint":      "#10B981",  # 绿色
    "lavender":  "#8B5CF6",  # 紫色
    "sky":       "#60A5FA",  # 浅蓝
    "sun":       "#F59E0B",  # 黄色
    "text":      "#1F2937",  # 主文字：深灰
    "sub":       "#6B7280",  # 次要文字：灰
    "danger":    "#EF4444",  # 警示红
    "line":      "#E5E7EB",  # 描边/分割线
    "chip":      "#DBEAFE",  # 浅蓝标签底
    "nav_bg":    "#FFFFFF",  # 导航栏背景
    "nav_on":    "#3B82F6",  # 导航选中色
    "nav_off":   "#9CA3AF",  # 导航未选中色
}


def C(hexstr):
    """hex 字符串 -> Kivy rgba 元组。"""
    return get_color_from_hex(hexstr)


def _darker(rgba, f=0.88):
    return [max(0.0, c * f) for c in rgba[:3]] + [rgba[3]]


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
    """圆角按钮，按下有轻微变深反馈。"""

    def __init__(self, bg=None, radius=22, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("font_name", FONT)
        kw.setdefault("color", C("#FFFFFF"))
        kw.setdefault("bold", True)
        super().__init__(**kw)
        base = bg or C(PALETTE["primary"])
        self._base_bg = base
        self._setup_round(base, radius)
        self.bind(on_press=lambda *a: setattr(self._r_color, "rgba", _darker(self._base_bg)))
        self.bind(on_release=lambda *a: setattr(self._r_color, "rgba", self._base_bg))

    def set_base(self, color):
        """运行时切换底色（如开关状态）。"""
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
    """圆角输入框。"""

    def __init__(self, radius=16, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("font_name", FONT)
        kw.setdefault("foreground_color", C(PALETTE["text"]))
        kw.setdefault("hint_text_color", C(PALETTE["sub"]))
        kw.setdefault("cursor_color", C(PALETTE["primary_d"]))
        kw.setdefault("padding", [12, 9, 12, 9])
        super().__init__(**kw)
        self._setup_round(C("#FFFFFF"), radius,
                          border=C(PALETTE["line"]), border_w=1.5)


class CuteLabel(_Round, Label):
    """可选圆角底的小标签 / 徽标。"""

    def __init__(self, bg=None, radius=14, **kw):
        kw.setdefault("font_name", FONT)
        kw.setdefault("color", C(PALETTE["text"]))
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "top")
        super().__init__(**kw)
        if bg is not None:
            self._setup_round(bg, radius)


class NavTab(Button):
    """底部导航栏单个 Tab 按钮。"""

    def __init__(self, emoji, text, screen_name, is_active=False, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("font_name", FONT)
        super().__init__(**kw)
        self.screen_name = screen_name
        self.emoji = emoji
        self.text_label = text
        self._active = is_active
        self._update_look()

    def _update_look(self):
        if self._active:
            self.color = C(PALETTE["nav_on"])
            self.font_size = 18
            self.text = self.emoji
        else:
            self.color = C(PALETTE["nav_off"])
            self.font_size = 15
            self.text = self.emoji

    def set_active(self, val):
        self._active = val
        self._update_look()


class SettingRow(BoxLayout):
    """列表式设置行（左侧标签 + 右侧值/按钮），类似天眼查设置页。"""

    def __init__(self, title, subtitle="", right_text="", on_tap=None, **kw):
        kw.setdefault("orientation", "horizontal")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", 52)
        kw.setdefault("padding", [16, 6, 16, 6])
        super().__init__(**kw)
        # 左侧标题区
        left = BoxLayout(orientation="vertical", size_hint_x=0.65)
        t = Label(text=title, font_name=FONT, font_size=15,
                  color=C(PALETTE["text"]), halign="left", valign="middle",
                  size_hint_y=None, height=26)
        t.bind(texture_size=lambda i, s: setattr(i, "height", s[1]))
        # 绑定宽度确保文字不截断
        left.bind(width=lambda i, w: setattr(t, "text_size", (w, None)))
        left.add_widget(t)
        if subtitle:
            s = Label(text=subtitle, font_name=FONT, font_size=12,
                      color=C(PALETTE["sub"]), halign="left", valign="middle",
                      size_hint_y=None, height=20)
            s.bind(texture_size=lambda i, v: setattr(i, "height", v[1]))
            left.bind(width=lambda i, w: setattr(s, "text_size", (w, None)))
            left.add_widget(s)
        self.add_widget(left)
        # 右侧
        right = Label(text=right_text, font_name=FONT, font_size=13,
                      color=C(PALETTE["sub"]), halign="right", valign="middle",
                      size_hint_x=0.35)
        right.bind(texture_size=lambda i, v: None)
        self.add_widget(right)
        # 点击回调
        if on_tap:
            self.bind(on_touch_down=lambda inst, touch: (
                on_tap() if inst.collide_point(*touch.pos) else None))


def info_popup(title, text, btn_text="知道了", on_close=None, emoji="ℹ️"):
    """通用滚动信息弹窗。返回 popup 便于外部控制。"""
    lay = BoxLayout(orientation="vertical", spacing=10, padding=14)
    sv = ScrollView(size_hint=(1, 1))
    lbl = Label(text=text, font_name=FONT, font_size=14, color=C(PALETTE["text"]),
                halign="left", valign="top", size_hint_y=None)
    lbl.bind(texture_size=lambda i, s: setattr(i, "height", s[1]))
    sv.bind(width=lambda i, w: setattr(lbl, "text_size", (w - 20, None)))
    sv.add_widget(lbl)
    lay.add_widget(sv)
    btn = CuteButton(text=btn_text, bg=C(PALETTE["primary"]),
                     size_hint_y=None, height=48)
    lay.add_widget(btn)
    popup = Popup(title=f"{emoji}  {title}", content=lay, size_hint=(0.92, 0.86),
                  auto_dismiss=False, title_font=FONT,
                  title_color=C(PALETTE["text"]),
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
    """确认弹窗（两个按钮）。"""
    lay = BoxLayout(orientation="vertical", spacing=10, padding=14)
    body = Label(text=text, font_name=FONT, font_size=14, color=C(PALETTE["text"]),
                 halign="left", valign="top", size_hint_y=1)
    body.bind(texture_size=lambda i, s: setattr(i, "height", s[1]))
    lay.add_widget(body)
    row = BoxLayout(size_hint_y=None, height=48, spacing=10)
    no = CuteButton(text=no_text, bg=C(PALETTE["sub"]))
    yes = CuteButton(text=yes_text, bg=C(PALETTE["danger"]))
    row.add_widget(no)
    row.add_widget(yes)
    lay.add_widget(row)
    popup = Popup(title=f"{emoji}  {title}", content=lay, size_hint=(0.9, 0.6),
                  auto_dismiss=False, title_font=FONT,
                  title_color=C(PALETTE["text"]),
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
