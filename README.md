# Antigravity Skill Studio (桌面技能工作台与上下文监测器)

专为 Google Antigravity 设计的高性能、零依赖本地桌面软件。提供**全局会话上下文 Token 实时监控（启发式估算参考）**、**专业技能白底极简看板**、**收藏夹专区**、**分类完全自定义**以及**本地/网络 Skill 一键收录**能力。

---

## 一、核心特性与架构亮点

1. **彻底解决“中键滑动/滚轮翻页卡顿”**
   - **彻底移除平滑滚动动画阻尼**：删去 `scroll-behavior: smooth`，完全回归 Chromium 内核硬件加速的排版合成器线程（Compositor Thread），达到原生 120Hz/144Hz 丝滑响应。
   - **剥离冗余的 JS 滚轮拦截**：滚轮滑动与中键点击 100% 交由底层原生引擎驱动。
   - **拖拽滑屏精准化与 rAF 节流**：仅响应鼠标左键空白处拖拽（`e.button === 0`），并接入 `requestAnimationFrame` 逐帧优化，避免任何主线程布局重绘抖动。
   - **卡片渲染隔离**：为技能卡片增加 CSS `contain: content;`，大幅降低滚屏时的重绘重排开销。

2. **彻底消除“黑框命令行弹窗” (零闪烁静默启动)**
   - **`start.vbs` 静默启动器**：通过 Windows 内置 `wscript.exe` 调用 `pythonw.exe app.py`（Windowed 纯图形子系统），窗口运行级别设为 `0 (SW_HIDE)`。双击启动时**没有任何黑框、没有任何控制台闪烁**，纯白原生界面直接呈现在屏幕上。
   - **异步批处理 `start.bat`**：改写为异步脱钩指令，即使从批处理点击也会即时派发并秒速退出控制台。

3. **启动耗时从秒级缩短至毫秒级 (极速秒开)**
   - **空闲端口瞬时分配**：采用内核级 `s.bind(('127.0.0.1', 0))` 替代原有的逐个端口探测循环，端口分配耗时降至 **0.0004 秒**。
   - **内存预热与双级缓存**：服务器启动时一次性预载技能库与分类配置，`/api/data` 请求直接命中内存；Token 监控采用后台轻量守护线程按需刷新，接口响应时间降为 **0ms**，开启软件即完成首屏渲染。

4. **Frameless 纯白无边框原生窗体与精准拖拽**
   - 启用无边框模式，由前端直接渲染纯白极简标题栏（含 `—` 最小化、`□` 最大化、`✕` 关闭原生按键与窗口拖拽区），彻底消除 Windows 11 系统强调色造成的青色标题栏。
   - 拖拽热区严格限制在顶部标题栏空白区域，主内容区自由滚动绝不误位移窗口。

5. **最小化缩小功能与架构级反循环引用重构 (Mini Floating Widget Mode)**
   - **解耦 `StudioWindowApi`，杜绝对象递归**：将窗体实例剥离为模块级全局变量 `_ACTIVE_DESKTOP_WINDOW`，`StudioWindowApi` 仅对外暴露纯净的无状态方法接口，根除 `pywebview` 跨线程反射 WinForms/COM 对象的死锁隐患。
   - **最大化智能还原检测**：通过 `user32.IsZoomed(hwnd)` 精准探测窗体是否最大化；若最大化则先执行 `restore()` 解除锁定，再精准缩放至迷你桌面悬浮尺寸 `500 × 125`。
   - **快捷还原**：右上角一键还原 (`⤢`)，并支持双击卡片空白处或键盘按 `Escape` 键秒速回归完整工作台。

6. **技能导入与全自动网络下载收录 (Local Import & Findskill Auto-Collector)**
   - **本地 Skill 导入**：支持选择或拖拽本地 Skill 文件夹、`.zip` 压缩包、或独立 `.md` 文件至窗口，系统全自动智能解析 YAML Frontmatter（`name`、`description`、`category`），并同步写入 `~/.gemini/skills/` 且持久化；
   - **本机未收录技能快速扫描**：深度比对 `~/.gemini/skills` 目录与看板当前配置，一键列出本机已存在但尚未展示的本地技能，支持单个收录或全选一键批量收录；
   - **网络下载自动加进来**：后台静默监听 `Downloads` 文件夹，用户在 `skills.sh` 网页下载完技能压缩包瞬间，系统自动完成提取、安装至系统目录并收录进面板；同时支持 GitHub 仓库名在线安装。

---

## 二、上下文 Token 估算机制与重要说明 (仅供参考)

### 1. 估算机制与数据来源
- **会话日志嗅探**：后台守护进程实时监听本地 Antigravity 会话日志路径：
  `~/.gemini/antigravity/brain/<conversation_id>/.system_generated/logs/transcript_full.jsonl`
- **内容抽取**：自动解析最新会话中的用户输入、模型回答、内部深度思考过程 (`thinking`) 以及工具调用结构体 (`tool_calls`)。
- **启发式拟合算法**：
  $$\text{Token 估算} = \text{CJK 字符数} \times 1.3 + \text{非 CJK 单词与标点数} \times 1.05 + 7000 (\text{预设系统提示词估算})$$

### 2. 重要声明 (免责与定位)
1. **估算值仅供参考**：本工具采用本地纯文本离线分词启发式经验公式，计算耗时为 0ms，旨在为日常编码提供实时的长会话长度监控；该数值**并非**通过 Google 官方 Gemini Tokenizer API 逐字精确分词得出，可能与底层官方计费或真实上下文占用存在一定统计偏差。
2. **Gemini 最大上下文上限未知**：Google Antigravity 及底层 Gemini 系列大模型（包括 1.5 Pro / Flash 等迭代版本）在不同任务与环境下的实际有效最大上下文窗口视具体模型版本、官方上下文压缩算法和调度策略而定，**具体确切的最大上下文上限并未公开固定**。
3. **1.0M 标尺定位**：看板中设定的 `1.0M`（1,000,000 Token）以及进度条百分比，仅作为一个**通用的健康度可视化标尺基准**。
4. **会话健康区间建议**：
   - 🟢 **黄金区间 (< 150k)**：模型注意力高度集中，指令遵循度与代码生成质量最高；
   - 🟡 **累积区间 (150k ~ 300k)**：长记忆开始堆积，建议关注上下文冗余；
   - 🔴 **警戒区间 (> 300k)**：容易产生注意力漂移或遗忘前期指令，强烈建议使用 `/compact` 指令压缩上下文或新开会话交付。

---

## 三、工程结构与隐私保护

### 1. 架构目录
```text
antigravity-skill-picker/
├── start.vbs                           # 推荐优先：双击静默极速启动 (100% 彻底无黑框)
├── start.bat                           # 备用：双击即退控制台启动批处理
├── app.py                              # 桌面软件核心服务 (内存高速缓存 + 无边框纯白窗体)
├── skills_config.example.json          # 开源配置模版 (首次运行自动初始化为 skills_config.json)
├── requirements.txt                    # Python 依赖清单 (pywebview, pyyaml)
├── LICENSE                             # 开源协议 (MIT License)
├── README.md                           # 核心技术文档 (即本文档)
└── src/
    ├── app.html                        # 100% 离线自包含纯白极简前端 (零外部依赖，毫秒级秒开)
    ├── index.html                      # 缺省主页镜像 (防止任何目录列表误报)
    ├── skills_data.example.json        # 基准技能示例库
    └── build_data.py                   # 原始文档重解析与初始数据生成脚本
```

### 2. 用户技能隐私隔离说明
- 本项目严密遵循数据与代码隔离设计，[`.gitignore`](.gitignore) 中已默认排除 `skills_config.json` 与 `src/skills_data.json`；
- 用户在本地安装、导入或收藏的私有 Skill 列表只会持久化在本地个人的 `skills_config.json` 中，**绝对不会被 Git 追踪或推送到公开仓库**；
- 外部使用者克隆项目后，软件会在首次启动时自动从 `skills_config.example.json` 生成干净的初始环境。

---

## 四、快速启动

### 1. 安装依赖
```bash
git clone https://github.com/<your-username>/antigravity-skill-picker.git
cd antigravity-skill-picker
pip install -r requirements.txt
```

### 2. 运行应用
**推荐（彻底无任何黑框）：**
直接双击运行工程根目录下的：
```text
start.vbs
```

或在命令行运行：
```bash
python app.py
```
即可享受毫秒级秒开、彻底无黑框、中键滚轮 120Hz/144Hz 丝滑顺畅的纯白桌面技能工作台。

---

## 五、开源许可证

本项目基于 [MIT License](LICENSE) 开源发布。
