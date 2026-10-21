# Antigravity Skill Studio

一个专为 Google Antigravity 设计的本地技能（Skill）看板与上下文 Token 监测桌面应用。

---

## 这个工具是干什么的？

在日常使用 Google Antigravity 辅助编程或多 Agent 协作时，我们经常需要加载不同的专家技能（Skills），同时关注长对话的上下文长度防止模型注意力漂移。本工具提供以下核心能力：

1. **技能检索与快速调用**
   - 集中展示你已配置的各类 Agent Skills（按语言、架构、前端、安全等分类）；
   - 支持实时关键词搜索与收藏夹置顶；
   - 点击技能卡片即可直接复制调用指令（如 `@python-pro`），直接粘贴到 Antigravity 对话中使用。

2. **用户自选技能文件夹与导入收录**
   - **完全由用户自主指定技能存放目录**：默认使用系统的 `~/.gemini/skills/`，但也支持在界面中自由选择、切换或配置为你电脑上的任意文件夹；
   - **多种导入方式**：支持选择或拖拽本地 Skill 文件夹、Markdown 规范文件或 Zip 压缩包，自动提取技能元数据并保存；
   - **本地待收录扫描**：一键扫描指定技能目录，快速收录尚未加入面板的本地技能。

3. **上下文 Token 实时监测（仅供参考）**
   - 监听本地活跃会话日志，实时离线估算当前对话已产生的 Token 数量与健康区间；
   - 提醒开发者适时使用 `/compact` 压缩上下文或新开会话，防止模型认知漂移。

4. **桌面迷你悬浮窗**
   - 可一键将窗口缩小为轻量悬浮条置顶在屏幕角落，方便边写代码边查看 Token 消耗与随时调取技能。

---

## 上下文 Token 估算机制与说明 (仅供参考)

### 1. 估算机制
- **数据来源**：后台读取本地 Antigravity 活跃会话日志 `transcript_full.jsonl`，抽取对话交互中的纯文本内容（包含用户输入、模型回答、思考过程及工具调用数据）；
- **启发式经验算法**：
  $$\text{Token 估算} = \text{CJK 字符数} \times 1.3 + \text{非 CJK 单词与标点数} \times 1.05 + 7000 (\text{预设系统提示词})$$

### 2. 重要声明
- **仅供参考**：该算法为本地纯文本离线分词经验公式，计算耗时为 0ms，旨在为日常编码提供实时的长会话长度趋势把控；该数值**并非**通过 Google 官方 Gemini Tokenizer API 逐字精确编码计算得出，可能与底层官方计费或真实上下文占用存在一定统计偏差；
- **Gemini 最大上下文上限未知**：Google Antigravity 及底层 Gemini 系列大模型（包括 1.5 Pro / Flash 等版本）在不同任务与环境下的实际有效最大上下文窗口视具体模型版本、官方上下文压缩算法和调度策略而定，**具体确切的最大上下文物理上限并未向客户端公开或固定**；
- **1.0M 标尺定位**：看板中设定的 `1.0M`（1,000,000 Token）以及进度条百分比，仅作为一个**通用的健康度可视化标尺基准**（黄金区间 <150k、累积区间 150k~300k、警戒区间 >300k），用于提醒开发者防范注意力漂移，并不代表任何官方硬性上下文上限。

---

## 快速开始

### 1. 安装依赖
```bash
git clone https://github.com/<your-username>/antigravity-skill-picker.git
cd antigravity-skill-picker
pip install -r requirements.txt
```

### 2. 运行应用
- **Windows 用户**：直接双击运行根目录下的 `start.vbs`（静默启动）或 `start.bat`；
- **命令行运行**：执行 `python app.py`。

### 3. 配置自己的技能文件夹
- 首次启动软件会自动加载默认配置；
- 点击右上角或导入界面的「选择其他文件夹」，即可指定你本机的技能存放路径（例如 `D:\my-skills` 或其他任意目录）；
- 你的个人配置（如自定义文件夹、导入的技能列表与收藏夹）仅保存在你本地的 `skills_config.json` 中，已被 `.gitignore` 排除，不会上传到 Git。

---

## 工程文件说明

```text
antigravity-skill-picker/
├── start.vbs                           # 桌面静默启动脚本
├── start.bat                           # 命令行启动脚本
├── app.py                              # 本地服务与桌面窗口逻辑
├── skills_config.example.json          # 开源配置模版 (首次运行自动生成本地 skills_config.json)
├── requirements.txt                    # Python 依赖清单
├── LICENSE                             # 开源协议 (MIT License)
├── README.md                           # 说明文档
└── src/
    ├── app.html                        # 纯白本地离线前端界面
    ├── build_data.py                   # 可选的 Markdown 目录数据重构建辅助脚本
    ├── index.html                      # 缺省服务页
    └── skills_data.example.json        # 纯净示例数据
```

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源发布。
