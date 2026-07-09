# 企信查 更新日志

## v1.2.0（2026-07-09）

### 🔧 修复
- **修复 APP 安装后闪退问题**：移除 ProfileScreen 中的 `self.manager.remove_widget(self)` 调用（正在显示的 Screen 不能被 ScreenManager 移除，会导致 Kivy 崩溃），改为 `clear_widgets()` + `_build_ui()` 安全重建 UI
- **修复 font_name=None 导致崩溃**：当字体文件不存在时，`CuteButton`/`CuteInput` 的 `font_name` 会被设为 None，导致 Button 初始化异常。新增 `_font_kw()` 安全函数，仅在字体文件存在时才设置 `font_name`

### 📐 布局自适应
- **所有弹窗自适应屏幕尺寸**：信息弹窗、确认弹窗、编辑弹窗、首次启动弹窗等，全部改为 `size_hint=(None, None)` + 动态计算 `size`，根据 `Window.width/height` 自动适配不同手机屏幕
- **所有 Label 文字自适应宽度**：使用 `text_size` + `bind(width)` 让文字自动换行，不会溢出或截断
- **搜索页/关注页/对比页空状态**：添加空状态引导提示，界面不再显示空白

### 🎨 UI 改进
- **蓝系配色方案**：全局统一为蓝色系配色，视觉风格一致
- **底部 4Tab 导航栏**：搜索、关注、对比、设置四个 Tab 页，安全触摸事件处理
- **设置页列表式布局**：ProfileScreen 改为清晰的列表式设置项
- **独立配置页**：ApiConfigScreen 和 CustomConfigScreen 作为独立 Screen，配置更清晰
- **新增 `edit_popup()` 组件**：单字段编辑弹窗，复用性强

### 📦 构建
- **构建模式改为 debug**：`buildozer android release` 只生成 AAB（无法直接安装），改回 `buildozer android debug` 确保 APK 可直接安装到手机
- **APK 文件名去除 debug 标记**：构建后自动重命名，去掉 `-debug` 后缀
- **Release 自动附带更新描述**：从 CHANGELOG.md 读取对应版本说明，自动写入 GitHub Release

---

## v1.1.0（2026-07-08）

### 初始版本
- 企业搜索、关注、对比基本功能
- 基础 UI 布局
