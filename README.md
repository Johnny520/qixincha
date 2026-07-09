# 企信查（包名 com.qxx.johnny）

类「天眼查」风格的企业工商信息查询 Android App（Kivy 实现），目标 **Android 12–16**。可爱风 UI（粉系圆角）。

> 说明：本项目是天眼查的**功能复刻学习作品**，使用自创名称与图标，不复制其商标 / Logo / UI 资源。数据来自公开 / 免费 API 与公开网页，请遵守各平台服务条款，仅用于个人学习研究。

## 已实现功能
- 🐾 **可爱风 UI**：粉系调色板、圆角卡片 / 按钮 / 输入框、Emoji 点缀，整体清爽软萌
- 🔍 企业名称搜索（结果以圆角卡片展示，点击进入详情）
- 🏢 工商基础信息：法定代表人、注册资本、成立日期、登记状态、统一社会信用代码、企业类型、行业、注册地址、经营范围、电话、邮箱、官网、曾用名、参保人数、登记机关、核准日期、是否上市等约 20 项
- 👥 股东信息（出资比例 / 金额）
- 📝 变更记录（变更事项 / 时间 / 前后内容）
- 🧑‍💼 主要人员 / 🌿 对外投资 / 🏬 分支机构（接入对应免费数据源后自动生效）
- 📚 全维度（聚合数据同一 key 复用，共约 30 项）：经营异常 / 行政处罚 / 严重违法 / 失信被执行人 / 股权出质 / 动产抵押 / 行政许可 / 税收违法 / 欠税公告 / 司法案件 / 法院公告 / 裁判文书 / 开庭公告 / 商标 / 专利 / 著作权 / 软件著作权 / 网站备案 / 招投标 / 债券 / 招聘 / 新闻舆情 / 微信公众号 / 企业年报 / 融资历程 / 竞品 / 产品 / 进出口信用 / 购地信息 / 资质证书 / 双随机抽查
- 🕷 **免 key 网页抓取兜底**：未配置任何 key 时，自动用公开搜索引擎摘要 best-effort 提取基础工商信息（能爬才爬，反爬 / 失败自动跳过，绝不阻塞主流程）
- ➕ 自定义数据源（自助接入任意官网接口，支持字段映射）
- 🛠 设置页：填各平台 API key、自定义数据源、清空本地缓存、请求超时与缓存天数、🕷 爬虫兜底开关、关于、用户协议 / 隐私政策 / 免责声明随时复看
- 📢 首次启动弹窗提示「数据来源与免责声明」，同意后写入本机，下次不再弹
- 💖 当前数据源横幅：详情页顶部显示本次命中的全部数据源，每个模块标题标注具体来源

## 数据来源（免费，需自行注册 key）
| 平台 | 用途 | key 方式 |
|------|------|---------|
| apibyte.cn | 工商基础信息 | 注册后 Bearer |
| xxapi.cn | 股东 / 变更记录 | 注册后 Bearer |
| jisuapi.com | 工商基础（字段极全）+ 股东 / 变更 / 高管（主要人员） | 注册后 appkey |
| juhe.cn | 对外投资 / 经营异常 / 行政处罚 / 失信被执行人 / 商标 / 专利 / 开庭公告（同一 key 复用） | 注册后 key 参数 |
| openapi.tianyancha.com | 分支机构（需申请） | access_token |
| openapi.qcc.com | 全维度（需企业认证） | 申请 ApiCode |
| 自定义 API | 任意官网申请的接口（工商基础优先） | 按接口填 |
| 🕷 免费网页抓取（兜底，免 key） | 无 key 时 best-effort 抓取公开摘要 | 无需配置，可在设置关闭 |

在 App 内「设置」页填入 key 即可。未填 key 时各模块显示空结构（App 仍可正常安装运行），并自动走网页抓取兜底。

## 当前数据源（让你知道用了哪个源）
详情页顶部「当前数据源」横幅，会列出本次查询实际命中的全部数据源；每个模块标题后的「源：xxx」标注该模块具体来自哪个接口。未命中任何源时提示去设置页配置。

## 自定义 API（自助接入任意官网接口）
若内置源用不了 / 查不到，可在「设置 → 自定义数据源」自行接入你在官网申请的接口，用于工商基础查询：
1. **名称**：给这个源起个名（如「我的源」）
2. **接口URL**：用 `{kw}` 占位企业名，例如 `https://我的接口.com/api?name={kw}`
3. **API Key**：你的 key
4. **请求头模板**：如 `Authorization: Bearer {key}`；留空则自动拼成 `?key=xxx` 查询参数
5. **字段映射JSON**（可选）：指定返回 JSON 到本 App 字段的映射，如 `{"name":"data.name","legal_person":"data.legal","reg_capital":"data.capital"}`；留空则自动猜测常见字段名
6. 点「保存自定义源」即可生效，查询时作为工商基础来源（优先级在 jisuapi / apibyte 之后）

## 🕷 免 key 网页抓取兜底
- 设计原则：**能爬的爬，不能爬的就不爬**。只做公开网页的 best-effort 提取，任一源失败 / 反爬 / 需登录都安全跳过，异常绝不冒泡到主流程。
- 默认路径：通过公开搜索引擎结果摘要正则提取「法定代表人 / 注册资本 / 成立日期 / 统一信用代码 / 经营范围」等字段（无需任何 key）。
- 可在「设置 → 缓存与高级 → 🕷 免费网页抓取兜底」一键开关。
- 如需接入更多稳定的免费公开源：在 `scraper.py` 追加函数并注册到 `_SOURCES` 即可，`data_sources` 会自动复用。

## 免责声明 / 用户协议 / 隐私政策
- **首次启动**：App 打开后会弹出「数据来源与免责声明」弹窗，需点「我已阅读并同意」方可使用；同意后标记写入本机 `config.json`，下次不再弹。
- **设置页复看**：进入「设置」最下方「协议与关于」可随时查看 用户协议 / 隐私政策 / 免责声明，并展示作者信息。
- **作者信息**：开发者 文强哥｜微信 Johnny19980924｜邮箱 1689969048@qq.com｜版权所有 © 2026。
- **隐私承诺**：不收集 / 不上传任何个人信息；API key 仅存本机 `config.json`；查询记录仅本机 SQLite 缓存。

## 打包出 APK
### 方式一：GitHub Actions 自动出包（推荐，拿永久直链）
> 原理：工程推到 GitHub 后，打一个 `v*` 标签即自动在云端用 buildozer 编译 APK，并发布到 Releases。Release 里的 APK 是**永久直链**（无签名 `t` 参数、不过期、不被截断），手机浏览器可直接下载安装，彻底规避 `missing parameter t`。

1. 在 GitHub 网页新建一个**空仓库**（不要勾选 README / .gitignore）。
2. 把本工程（含隐藏的 `.github/` 目录，已自带自动构建配置）推上去：
   ```bash
   cd qixincha
   git init -b main
   git add -A
   git commit -m "init"
   git remote add origin https://github.com/你的用户名/仓库名.git
   git push -u origin main
   ```
3. 打标签触发自动构建（手机可用 GitHub App / 网页操作，或电脑执行）：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. 进入仓库 **Actions** 页，等 `Build APK` 跑完（首次约 15–30 分钟，自动下载 Android SDK/NDK，请耐心等）。
5. 进入仓库 **Releases** 页，下载 `企信查-v1.0.0-...-debug.apk`，传到手机安装即可。
   - 该链接形如 `https://github.com/你的用户名/仓库名/releases/download/v1.0.0/xxx.apk`，**永久有效、无签名参数**，不会再出现 `missing parameter t`。
   - 想要源码 zip 的永久直链也可直接用：`https://github.com/你的用户名/仓库名/archive/refs/heads/main.zip`。

### 方式二：本地（Linux / macOS / WSL）
```bash
chmod +x build_apk.sh
./build_apk.sh
# APK 生成于 bin/ 目录
```

## 工程结构
```
qixincha/
├── main.py              # Kivy UI（搜索 / 详情 / 设置），可爱风
├── ui.py                # 可爱风 UI 主题与可复用组件（粉系调色板 / 圆角卡片按钮 / 弹窗）
├── data_sources.py      # 多源数据适配层（apibyte + xxapi + jisuapi + juhe + 天眼查 + 自定义 + 爬虫兜底）
├── scraper.py           # 免 key 网页抓取兜底（能爬才爬）
├── config.py / cache.py # 配置与本地缓存
├── legal.py             # 免责声明 / 用户协议 / 隐私政策 / 作者信息
├── fonts/NotoSansSC.ttf # 内置中文字体（避免方块字）
├── buildozer.spec       # 打包配置：minapi 31 / api 36（Android 12–16）
├── build_apk.sh         # 本地一键打包
├── .github/workflows/   # GitHub Actions 自动构建
└── requirements.txt
```

## 备注
- apibyte 的 endpoint 以平台实际文档为准，如需调整请改 `data_sources.py` 中的 `_apibyte_basic`。
- jisuapi 的 `shareholder` / `change` / `executive`（主要人员，按文档"含股东高管信息"推测）端点为按文档推测，若返回异常请在平台确认确切路径（改 `data_sources.py` 对应函数）。
- 聚合数据 `out_investment`（对外投资）、天眼查开放平台分支接口(824) 的返回字段为按常见结构推测，如有差异请改 `data_sources.py` 中 `_juhe_investments` / `_tianyancha_branches`。
- 自定义 API 的 endpoint / 返回结构以你申请的官方文档为准，用「字段映射JSON」字段对齐即可，无需改代码。
- 包名在 Android 规范下为小写：`com.qxx.johnny`。
- 聚合数据其余约 30 个维度（经营异常/行政处罚/商标/专利/司法/开庭/招聘/新闻等）的 endpoint 与返回字段为按常见结构推测，集中维护在 `data_sources.py` 的 `JUHE_DIMENSIONS` 注册表；如需增删维度或调整路径，只改这一处即可，详情页与数据源横幅会自动生效。
- 爬虫兜底字段为 best-effort 提取，准确性以公开网页实时内容为准，仅作无 key 时的补充。
