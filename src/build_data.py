# -*- coding: utf-8 -*-

"""
Skills Catalog Parser & HTML Generator
Parses markdown documentation and generates structured JSON data.
Usage: python build_data.py <path_to_markdown_file>
"""



import os

import sys

import re

import json



def parse_skills(summary_path=None, local_skills_dir=None):
    if not summary_path:
        if len(sys.argv) > 1:
            summary_path = sys.argv[1]
        else:
            summary_path = os.environ.get("ANTIGRAVITY_SKILLS_DOC", "")

    if not local_skills_dir:
        local_skills_dir = os.environ.get("ANTIGRAVITY_SKILLS_DIR", os.path.expanduser(r"~\.gemini\skills"))
    
    local_skills_set = set(os.listdir(local_skills_dir)) if os.path.exists(local_skills_dir) else set()

    if not summary_path or not os.path.exists(summary_path):
        print("Notice: No markdown summary file specified or found. Provide file path via argument: python build_data.py <file.md>")
        return {"categories": [], "skills": [], "total_skills": 0}

    with open(summary_path, "r", encoding="utf-8") as f:

        lines = f.readlines()



    category_map = {

        "AI长上下文处理": ("🧠 AI 长上下文工程", "处理超长上下文与深层模块设计的工程规范"),

        "💻 核心编程语言 (Language Pros)": ("💻 核心编程语言", "针对主流语言的高阶专家人设与性能调优"),

        "🏗 项目架构与代码梳理 (Project Architecture & Codebase Breakdown)": ("🏗 项目架构与代码梳理", "深层模块拆分、契约先行与架构梳理规范"),

        "🎨 前端与 UI 框架 (Frontend & UI)": ("🎨 前端与 UI 框架", "React, Next.js, Tailwind, Shadcn 等前端最佳实践"),

        "⚙️ 后端、架构与数据库 (Backend & Architecture)": ("⚙️ 后端与数据库", "主流后端框架、微服务架构与数据库选型指导"),

        "🚀 大厂架构与高并发实战 (Enterprise Architecture & High Concurrency)": ("🚀 大厂高并发实战", "高并发实战、分布式锁、缓存防击穿与事务隔离"),

        "☁️ 云计算、DevOps 与运维 (Cloud & DevOps)": ("☁️ 云计算与 DevOps", "K8s, 云资源编排, CI/CD 与 Docker 构建优化"),

        "🛡️ 网络安全与审计 (Security & Auditing)": ("🛡️ 网络安全与审计", "白盒代码扫描、渗透测试流程与合规性审查"),

        "🧠 AI 与大模型工程 (AI & LLM Engineering)": ("🤖 AI 与大模型工程", "Prompt工程, RAG检索增强, 大模型底层原理与架构"),

        "🔍 代码检查与架构审计 (Code Review & Architecture Audit)": ("🔍 代码检查与审计", "代码盲审, Pre-push 静态扫描与功能闭环校验"),

        "📦 项目管理与开发工程 (Project Management & SDLC)": ("📦 项目管理与工程", "自主开发模式, SDLC 管理与子 Agent 协同"),

        "🧠 AI 记忆与认知 Harness (AI Memory & Cognitive Harness)": ("🧠 AI 记忆与认知", "防止 AI 长期衰退与长对话漂移的认知支架"),

        "📈 SEO、营销与产品 (SEO & Product)": ("📈 SEO 营销与产品", "技术 SEO, 文案心理学与产品经理工具包"),

        "📊 办公与效率自动化 (Office & Productivity Automation)": ("📊 办公与效率自动化", "PPTX, Word, Excel, Google Slides 等办公自动化"),

        "🎬 现代演示文稿制作 (Modern Presentation & PPT Skills)": ("🎬 现代演示与 PPT", "电子杂志感、Reveal.js 与专业演示文稿构建"),

        "📊 数据可视化与科研绘图 (Data Visualization & Scientific Plotting)": ("📊 数据可视化与绘图", "学术论文级高清科研绘图、时频域分析与科学计算"),

        "📈 量化、金融与股市研究 (Quant & Finance Research)": ("💰 量化与金融股市", "量化回测, 期权异动, 基本面研究与风险指标建模"),

    }



    current_cat_display = "⚡ 通用规范与工作流"

    current_cat_desc = "日常通用开发辅助、清理与交接流程规范"

    

    entries = []



    for line in lines:

        line_str = line.strip()

        if not line_str:

            continue

        

        # Check header

        if line_str.startswith("#"):

            h = line_str.lstrip("#").strip()

            if h and "终极指南" not in h:

                if h in category_map:

                    current_cat_display, current_cat_desc = category_map[h]

                else:

                    current_cat_display = h

                    current_cat_desc = f"{h} 领域相关技能集合"

            continue

        

        if "@" not in line_str:

            continue



        # Special case: line 161 '@fpga  @systemverilog'

        if "@fpga" in line_str and "@systemverilog" in line_str:

            cat_hw = "🔌 硬件与底层系统"

            entries.append({

                "name": "fpga",

                "category": cat_hw,

                "description": "FPGA 开发指南，涵盖 Vivado、SystemVerilog、时序收敛与 AXI 接口优化。",

                "installed": "fpga" in local_skills_set

            })

            entries.append({

                "name": "systemverilog",

                "category": cat_hw,

                "description": "SystemVerilog 硬件开发与 ASIC/FPGA 验证、时序优化及模块化设计规范。",

                "installed": "systemverilog" in local_skills_set

            })

            continue



        # Special case: planetscale/database-skills@mysql

        if "planetscale/database-skills@mysql" in line_str:

            desc = line_str.split(":", 1)[1].strip() if ":" in line_str else "PlanetScale 海量 MySQL 平台技能"

            entries.append({

                "name": "planetscale/database-skills@mysql",

                "category": current_cat_display,

                "description": desc,

                "installed": "planetscale/database-skills@mysql" in local_skills_set

            })

            continue



        # General line parsing:

        desc = ""

        prefix = line_str

        m_col = re.search(r"[:：]", line_str)

        if m_col:

            prefix = line_str[:m_col.start()].strip()

            desc = line_str[m_col.end():].strip()

        else:

            m_inline = re.search(r"(@[a-zA-Z0-9_\-\./]+)\s*([\u4e00-\u9fa5].*)", line_str)

            if m_inline:

                prefix = m_inline.group(1)

                desc = m_inline.group(2).strip()



        skills_in_prefix = re.findall(r"@([a-zA-Z0-9_\-\./]+)", prefix)

        clean_desc = re.sub(r"@[a-zA-Z0-9_\-\./]+", "", desc).strip(" :：-—")

        if not clean_desc:

            clean_desc = desc



        for s in skills_in_prefix:

            s = s.strip()

            if not s:

                continue

            entries.append({

                "name": s,

                "category": current_cat_display,

                "description": clean_desc if clean_desc else f"{s} 专家级辅助技能",

                "installed": s in local_skills_set

            })



    unique_entries = []

    seen = set()

    for e in entries:

        key = (e["name"], e["category"])

        if key not in seen:

            seen.add(key)

            unique_entries.append(e)



    categories = []

    seen_cats = set()

    for e in unique_entries:

        cat = e["category"]

        if cat not in seen_cats:

            seen_cats.add(cat)

            categories.append(cat)



    return {

        "categories": categories,

        "total_skills": len(unique_entries),

        "skills": unique_entries

    }



def generate_html(data):

    json_str = json.dumps(data, ensure_ascii=False)

    

    html = f"""<!DOCTYPE html>

<html lang="zh-CN">

<head>

  <meta charset="UTF-8">

  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>Antigravity Skill 快捷插入器</title>

  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>

  <style>

    :root {{

      --background: #0f172a;

      --card: #1e293b;

      --border: #334155;

      --foreground: #f8fafc;

      --muted-foreground: #94a3b8;

      --primary: #38bdf8;

      --primary-foreground: #0f172a;

      --accent: #22c55e;

    }}

    .light {{

      --background: #f8fafc;

      --card: #ffffff;

      --border: #e2e8f0;

      --foreground: #0f172a;

      --muted-foreground: #64748b;

      --primary: #0284c7;

      --primary-foreground: #ffffff;

      --accent: #16a34a;

    }}

    /* Custom scrollbars */

    ::-webkit-scrollbar {{

      width: 6px;

      height: 6px;

    }}

    ::-webkit-scrollbar-track {{

      background: transparent;

    }}

    ::-webkit-scrollbar-thumb {{

      background: rgba(148, 163, 184, 0.25);

      border-radius: 9999px;

    }}

    ::-webkit-scrollbar-thumb:hover {{

      background: rgba(148, 163, 184, 0.5);

    }}

  </style>

</head>

<body class="bg-transparent text-[var(--foreground)] antialiased p-3 sm:p-5 text-sm selection:bg-[var(--primary)] selection:text-[var(--primary-foreground)]">



  <!-- Main Container Card -->

  <div class="max-w-6xl mx-auto bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-2xl shadow-xl flex flex-col overflow-hidden backdrop-blur-md">

    

    <!-- Top Header -->

    <div class="px-5 py-4 border-b border-[var(--border)] flex flex-wrap items-center justify-between gap-3 bg-[var(--card)]/90 sticky top-0 z-30">

      <div class="flex items-center gap-3">

        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-md">

          ⚡

        </div>

        <div>

          <h1 class="text-base sm:text-lg font-bold flex items-center gap-2">

            Antigravity Skill 一键插入面板

            <span id="stat-badge" class="text-xs px-2 py-0.5 rounded-full bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30 font-medium">

              127 个技能

            </span>

          </h1>

          <p class="text-xs text-[var(--muted-foreground)]">

            点击卡片或按钮即可复制 @技能 并在对话框直接 Ctrl+V 插入

          </p>

        </div>

      </div>



      <!-- Quick Action Controls -->

      <div class="flex items-center gap-2">

        <div class="flex items-center bg-[var(--background)] border border-[var(--border)] rounded-lg p-1 text-xs">

          <label class="text-[var(--muted-foreground)] px-2">模板模式:</label>

          <select id="template-select" class="bg-transparent text-[var(--foreground)] focus:outline-none cursor-pointer">

            <option value="raw">纯 @skill 标签</option>

            <option value="task">带任务指令 (@skill 请帮我分析...)</option>

            <option value="audit">带审计指令 (@skill 请按规范审查...)</option>

          </select>

        </div>



        <button id="btn-sync-info" onclick="toggleHelpModal()" class="px-2.5 py-1 text-xs rounded-lg border border-[var(--border)] hover:bg-[var(--border)]/40 transition-colors" title="使用说明">

          ℹ️ 说明

        </button>

      </div>

    </div>



    <!-- Search & Filter Bar -->

    <div class="px-5 py-3 border-b border-[var(--border)] bg-[var(--card)]/60 flex flex-wrap items-center justify-between gap-3">

      <!-- Search Input -->

      <div class="relative flex-1 min-w-[240px]">

        <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[var(--muted-foreground)]">

          🔍

        </span>

        <input 

          id="search-input" 

          type="text" 

          placeholder="搜索技能名称、描述、功能关键词 (例如 python, 架构, ppt, 安全)..." 

          class="w-full pl-9 pr-8 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-[var(--primary)] text-[var(--foreground)] placeholder-[var(--muted-foreground)]"

          oninput="handleSearch()"

        />

        <button id="clear-search" onclick="clearSearch()" class="absolute inset-y-0 right-0 pr-3 flex items-center text-[var(--muted-foreground)] hover:text-[var(--foreground)] hidden">

          ✕

        </button>

      </div>



      <!-- Sorting & Filter Controls -->

      <div class="flex items-center gap-2 flex-wrap text-xs">

        <div class="flex items-center gap-1.5 bg-[var(--background)] px-2.5 py-1.5 rounded-xl border border-[var(--border)]">

          <span class="text-[var(--muted-foreground)]">总体排序:</span>

          <select id="sort-select" onchange="handleSortChange()" class="bg-transparent text-[var(--foreground)] focus:outline-none cursor-pointer font-medium">

            <option value="default">默认分类顺序</option>

            <option value="name-asc">技能名称 (A → Z)</option>

            <option value="name-desc">技能名称 (Z → A)</option>

            <option value="desc-len">描述详尽程度 (多 → 少)</option>

          </select>

        </div>



        <button 

          id="filter-installed-btn" 

          onclick="toggleInstalledFilter()" 

          class="px-2.5 py-1.5 rounded-xl border border-[var(--border)] hover:bg-[var(--border)]/40 transition-colors flex items-center gap-1"

        >

          <span id="filter-installed-icon">⚪</span> 仅本地已装

        </button>

      </div>

    </div>



    <!-- Category Tabs Filter (分类区) -->

    <div class="px-5 py-2.5 border-b border-[var(--border)] bg-[var(--background)]/40 overflow-x-auto flex items-center gap-1.5 no-scrollbar">

      <button 

        onclick="selectCategory('ALL')" 

        id="cat-tab-ALL"

        class="cat-tab px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm"

      >

        🌟 全部 (<span id="count-all">127</span>)

      </button>

      <div id="category-tabs-container" class="flex items-center gap-1.5">

        <!-- Rendered dynamically -->

      </div>

    </div>



    <!-- Content Area: Skill Cards Grid -->

    <div class="p-5 overflow-y-auto max-h-[580px]" id="cards-container">

      <!-- Cards rendered dynamically -->

    </div>



    <!-- Sticky Bottom Bar for Multi-Select Batch Copy -->

    <div id="batch-action-bar" class="hidden px-5 py-3 border-t border-[var(--border)] bg-gradient-to-r from-sky-950/80 to-indigo-950/80 backdrop-blur-md flex items-center justify-between gap-3 text-xs z-20">

      <div class="flex items-center gap-2">

        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>

        <span class="font-medium text-white">已选择 <span id="batch-count" class="font-bold text-sky-300">0</span> 个技能:</span>

        <div id="batch-tags-preview" class="flex items-center gap-1 overflow-x-auto max-w-md text-sky-200 text-2xs truncate"></div>

      </div>

      <div class="flex items-center gap-2">

        <button onclick="clearBatchSelection()" class="px-3 py-1.5 rounded-lg border border-white/20 text-white/80 hover:bg-white/10 transition-colors">

          清空

        </button>

        <button onclick="copyBatchSkills()" class="px-4 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-900 font-bold shadow-lg transition-all flex items-center gap-1.5">

          📋 一键复制所选技能

        </button>

      </div>

    </div>



    <!-- Toast Notification -->

    <div id="toast" class="fixed bottom-6 right-6 z-50 transform translate-y-12 opacity-0 pointer-events-none transition-all duration-300 bg-slate-900/95 text-white border border-sky-500/40 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs sm:text-sm">

      <span class="text-base text-emerald-400">✓</span>

      <span id="toast-msg">已复制到剪贴板！</span>

    </div>



    <!-- Help Modal -->

    <div id="help-modal" class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 hidden">

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">

        <button onclick="toggleHelpModal()" class="absolute top-4 right-4 text-[var(--muted-foreground)] hover:text-[var(--foreground)] text-lg">✕</button>

        <h3 class="text-base font-bold mb-3 flex items-center gap-2">

          📖 Antigravity Skill 插件使用手册

        </h3>

        <div class="text-xs space-y-2.5 text-[var(--muted-foreground)] leading-relaxed">

          <p><strong class="text-[var(--foreground)]">1. 一键插入原理：</strong>根据你的系统规则协议，对话中输入 <code class="text-sky-400">@技能名称</code> 即可自动读取该技能的 SKILL.md。点击面板中任一卡片的「复制/插入」按钮，即可瞬间将指令写入系统剪贴板，你只需在对话框按 <kbd class="px-1.5 py-0.5 rounded bg-[var(--border)] font-mono text-[var(--foreground)]">Ctrl+V</kbd> 即可发送！</p>

          <p><strong class="text-[var(--foreground)]">2. 多选组合调用：</strong>勾选卡片上的复选框，可以在底部工具栏看到选中的所有技能。点击「一键复制所选技能」，就能一次性插入多个技能（如 <code class="text-sky-400">@python-pro @code-reviewer</code>），实现复合专家人设协作！</p>

          <p><strong class="text-[var(--foreground)]">3. 模板模式：</strong>右上角可切换“纯标签”、“带任务指令”或“带代码审计指令”，复制时会自动补全提示词骨架，省去手打繁琐提示词。</p>

          <p><strong class="text-[var(--foreground)]">4. 分类区与排序：</strong>顶部胶囊栏可按19大领域精准分类，右侧排序下拉菜单支持 A-Z 名称排序与详尽度排序，支持全字段模糊搜索。</p>

        </div>

        <div class="mt-5 text-right">

          <button onclick="toggleHelpModal()" class="px-4 py-1.5 rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)] text-xs font-semibold">我知道了</button>

        </div>

      </div>

    </div>



  </div>



  <script>

    // Embedded catalog data

    const CATALOG = {json_str};



    let activeCategory = "ALL";

    let searchQuery = "";

    let sortMode = "default";

    let filterInstalledOnly = false;

    let selectedSkills = new Set();



    // Init

    window.addEventListener("DOMContentLoaded", () => {{

      renderCategoryTabs();

      renderCards();

    }});



    function renderCategoryTabs() {{

      const container = document.getElementById("category-tabs-container");

      container.innerHTML = "";

      

      CATALOG.categories.forEach(cat => {{

        const count = CATALOG.skills.filter(s => s.category === cat).length;

        const btn = document.createElement("button");

        btn.id = `cat-tab-${{encodeURIComponent(cat)}}`;

        btn.className = "cat-tab px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--border)]/40 text-[var(--muted-foreground)]";

        btn.innerHTML = `${{cat}} <span class="text-2xs opacity-75 font-normal">(${{count}})</span>`;

        btn.onclick = () => selectCategory(cat);

        container.appendChild(btn);

      }});



      document.getElementById("count-all").textContent = CATALOG.total_skills;

    }}



    function selectCategory(cat) {{

      activeCategory = cat;

      document.querySelectorAll(".cat-tab").forEach(tab => {{

        tab.className = "cat-tab px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--border)]/40 text-[var(--muted-foreground)]";

      }});



      if (cat === "ALL") {{

        const allTab = document.getElementById("cat-tab-ALL");

        allTab.className = "cat-tab px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm";

      }} else {{

        const targetTab = document.getElementById(`cat-tab-${{encodeURIComponent(cat)}}`);

        if (targetTab) {{

          targetTab.className = "cat-tab px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm";

        }}

      }}



      renderCards();

    }}



    function handleSearch() {{

      const val = document.getElementById("search-input").value.trim().toLowerCase();

      searchQuery = val;

      const clearBtn = document.getElementById("clear-search");

      if (val) {{

        clearBtn.classList.remove("hidden");

      }} else {{

        clearBtn.classList.add("hidden");

      }}

      renderCards();

    }}



    function clearSearch() {{

      document.getElementById("search-input").value = "";

      searchQuery = "";

      document.getElementById("clear-search").classList.add("hidden");

      renderCards();

    }}



    function handleSortChange() {{

      sortMode = document.getElementById("sort-select").value;

      renderCards();

    }}



    function toggleInstalledFilter() {{

      filterInstalledOnly = !filterInstalledOnly;

      const icon = document.getElementById("filter-installed-icon");

      const btn = document.getElementById("filter-installed-btn");

      if (filterInstalledOnly) {{

        icon.textContent = "🟢";

        btn.classList.add("bg-[var(--primary)]/15", "border-[var(--primary)]/50", "text-[var(--primary)]");

      }} else {{

        icon.textContent = "⚪";

        btn.classList.remove("bg-[var(--primary)]/15", "border-[var(--primary)]/50", "text-[var(--primary)]");

      }}

      renderCards();

    }}



    function getFilteredSkills() {{

      let list = [...CATALOG.skills];



      // Category filter

      if (activeCategory !== "ALL") {{

        list = list.filter(s => s.category === activeCategory);

      }}



      // Installed filter

      if (filterInstalledOnly) {{

        list = list.filter(s => s.installed);

      }}



      // Search query

      if (searchQuery) {{

        list = list.filter(s => {{

          return s.name.toLowerCase().includes(searchQuery) ||

                 s.description.toLowerCase().includes(searchQuery) ||

                 s.category.toLowerCase().includes(searchQuery);

        }});

      }}



      // Sorting

      if (sortMode === "name-asc") {{

        list.sort((a, b) => a.name.localeCompare(b.name));

      }} else if (sortMode === "name-desc") {{

        list.sort((a, b) => b.name.localeCompare(a.name));

      }} else if (sortMode === "desc-len") {{

        list.sort((a, b) => b.description.length - a.description.length);

      }}



      return list;

    }}



    function renderCards() {{

      const container = document.getElementById("cards-container");

      const filtered = getFilteredSkills();



      document.getElementById("stat-badge").textContent = `${{filtered.length}} / ${{CATALOG.total_skills}} 个技能`;



      if (filtered.length === 0) {{

        container.innerHTML = `

          <div class="py-16 text-center text-[var(--muted-foreground)]">

            <div class="text-4xl mb-2">🔍</div>

            <p class="font-medium text-sm">未找到匹配的 Skill</p>

            <p class="text-xs mt-1">请尝试清除搜索词或切换分类选项</p>

          </div>

        `;

        return;

      }}



      // If viewing ALL and sorted by default, group by Category

      if (activeCategory === "ALL" && sortMode === "default" && !searchQuery) {{

        let html = "";

        CATALOG.categories.forEach(cat => {{

          const catSkills = filtered.filter(s => s.category === cat);

          if (catSkills.length === 0) return;



          html += `

            <div class="mb-6">

              <div class="flex items-center gap-2 mb-3 pb-1 border-b border-[var(--border)]/60">

                <h3 class="text-sm font-bold text-[var(--foreground)] flex items-center gap-1.5">

                  ${{cat}}

                  <span class="text-2xs px-2 py-0.5 rounded-full bg-[var(--border)] text-[var(--muted-foreground)] font-normal">

                    ${{catSkills.length}}

                  </span>

                </h3>

              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">

                ${{catSkills.map(s => renderCardHtml(s)).join("")}}

              </div>

            </div>

          `;

        }});

        container.innerHTML = html;

      }} else {{

        // Flat grid view

        container.innerHTML = `

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">

            ${{filtered.map(s => renderCardHtml(s)).join("")}}

          </div>

        `;

      }}

    }}



    function renderCardHtml(skill) {{

      const isChecked = selectedSkills.has(skill.name);

      const isLocal = skill.installed;



      return `

        <div class="group relative bg-[var(--background)]/60 hover:bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)]/60 rounded-xl p-3.5 flex flex-col justify-between transition-all duration-200 shadow-sm hover:shadow-md">

          

          <div>

            <!-- Card Header: Checkbox + Name + Badges -->

            <div class="flex items-start justify-between gap-2 mb-2">

              <div class="flex items-center gap-2 min-w-0">

                <input 

                  type="checkbox" 

                  ${{isChecked ? "checked" : ""}} 

                  onchange="toggleSkillSelection('${{skill.name}}', event)"

                  class="rounded border-[var(--border)] text-[var(--primary)] focus:ring-0 cursor-pointer h-4 w-4 mt-0.5"

                  title="多选组合"

                />

                <span class="font-mono font-semibold text-xs sm:text-sm text-sky-400 group-hover:text-sky-300 truncate" title="@${{skill.name}}">

                  @${{skill.name}}

                </span>

              </div>

              

              <div class="flex items-center gap-1 flex-shrink-0">

                ${{isLocal 

                  ? `<span class="text-2xs px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-0.5" title="本地已就绪">✓ 本地</span>`

                  : `<span class="text-2xs px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400/80 border border-amber-500/20" title="未在本地目录">线上</span>`

                }}

              </div>

            </div>



            <!-- Category tag -->

            <div class="mb-2">

              <span class="text-2xs px-2 py-0.5 rounded-md bg-[var(--border)]/50 text-[var(--muted-foreground)]">

                ${{skill.category}}

              </span>

            </div>



            <!-- Description -->

            <p class="text-xs text-[var(--muted-foreground)] leading-relaxed line-clamp-3 mb-3" title="${{skill.description}}">

              ${{skill.description}}

            </p>

          </div>



          <!-- Bottom Button: 1-Click Insert/Copy -->

          <div class="pt-2 border-t border-[var(--border)]/40 flex items-center justify-between gap-2 mt-auto">

            <button 

              id="copy-btn-${{skill.name.replace(/[^a-zA-Z0-9]/g, '_')}}"

              onclick="copySingleSkill('${{skill.name}}', this)" 

              class="w-full py-1.5 px-3 rounded-lg bg-[var(--primary)]/10 hover:bg-[var(--primary)] text-[var(--primary)] hover:text-[var(--primary-foreground)] border border-[var(--primary)]/30 hover:border-transparent text-xs font-medium transition-all duration-150 flex items-center justify-center gap-1.5"

            >

              <span>📋</span>

              <span>一键插入 / 复制</span>

            </button>

          </div>



        </div>

      `;

    }}



    function getFormattedText(skillName) {{

      const template = document.getElementById("template-select").value;

      if (template === "task") {{

        return `@${{skillName}} 请帮我处理以下任务：\\n\\n[请在此输入具体需求]`;

      }} else if (template === "audit") {{

        return `@${{skillName}} 请严格按照此技能的最佳实践与设计规范，对以下代码/架构进行客观审查与找错：\\n\\n[请在此输入代码或设计]`;

      }}

      return `@${{skillName}} `;

    }}



    function copySingleSkill(skillName, btnElem) {{

      const textToCopy = getFormattedText(skillName);

      

      navigator.clipboard.writeText(textToCopy).then(() => {{

        // Visual button feedback

        const originalContent = btnElem.innerHTML;

        btnElem.innerHTML = `<span>✓</span><span>已复制！Ctrl+V 发送</span>`;

        btnElem.className = "w-full py-1.5 px-3 rounded-lg bg-emerald-500 text-slate-950 font-bold border border-emerald-400 text-xs transition-all flex items-center justify-center gap-1.5 shadow-sm";

        

        showToast(`已复制 "@${{skillName}}"，直接在对话框按 Ctrl+V 即可发送！`);



        setTimeout(() => {{

          btnElem.innerHTML = originalContent;

          btnElem.className = "w-full py-1.5 px-3 rounded-lg bg-[var(--primary)]/10 hover:bg-[var(--primary)] text-[var(--primary)] hover:text-[var(--primary-foreground)] border border-[var(--primary)]/30 hover:border-transparent text-xs font-medium transition-all duration-150 flex items-center justify-center gap-1.5";

        }}, 2000);

      }}).catch(err => {{

        console.error("Clipboard error:", err);

        fallbackCopy(textToCopy);

      }});

    }}



    function toggleSkillSelection(skillName, e) {{

      if (e.target.checked) {{

        selectedSkills.add(skillName);

      }} else {{

        selectedSkills.delete(skillName);

      }}

      updateBatchBar();

    }}



    function updateBatchBar() {{

      const bar = document.getElementById("batch-action-bar");

      const countElem = document.getElementById("batch-count");

      const preview = document.getElementById("batch-tags-preview");



      if (selectedSkills.size > 0) {{

        bar.classList.remove("hidden");

        countElem.textContent = selectedSkills.size;

        preview.innerHTML = Array.from(selectedSkills).map(s => `@${{s}}`).join(" ");

      }} else {{

        bar.classList.add("hidden");

      }}

    }}



    function clearBatchSelection() {{

      selectedSkills.clear();

      updateBatchBar();

      renderCards();

    }}



    function copyBatchSkills() {{

      if (selectedSkills.size === 0) return;

      const template = document.getElementById("template-select").value;

      const skillsStr = Array.from(selectedSkills).map(s => `@${{s}}`).join(" ");

      

      let textToCopy = skillsStr + " ";

      if (template === "task") {{

        textToCopy = `${{skillsStr}} 请协同处理以下任务：\\n\\n[请在此输入具体需求]`;

      }} else if (template === "audit") {{

        textToCopy = `${{skillsStr}} 请按照相关技能规范联合审查以下代码：\\n\\n[请在此输入内容]`;

      }}



      navigator.clipboard.writeText(textToCopy).then(() => {{

        showToast(`已复制组合技能 (${{selectedSkills.size}}个)：${{skillsStr}}，按 Ctrl+V 粘贴！`);

      }}).catch(err => {{

        fallbackCopy(textToCopy);

      }});

    }}



    function fallbackCopy(text) {{

      const ta = document.createElement("textarea");

      ta.value = text;

      ta.style.position = "fixed";

      ta.style.opacity = "0";

      document.body.appendChild(ta);

      ta.select();

      try {{

        document.execCommand("copy");

        showToast(`已复制到剪贴板！在输入框按 Ctrl+V 粘贴发送`);

      }} catch (e) {{

        alert("复制失败，请手动选择复制: " + text);

      }}

      document.body.removeChild(ta);

    }}



    function showToast(msg) {{

      const toast = document.getElementById("toast");

      const msgElem = document.getElementById("toast-msg");

      msgElem.textContent = msg;

      toast.classList.remove("opacity-0", "pointer-events-none", "translate-y-12");

      toast.classList.add("opacity-100", "translate-y-0");



      setTimeout(() => {{

        toast.classList.remove("opacity-100", "translate-y-0");

        toast.classList.add("opacity-0", "pointer-events-none", "translate-y-12");

      }}, 3000);

    }}



    function toggleHelpModal() {{

      const m = document.getElementById("help-modal");

      m.classList.toggle("hidden");

    }}

  </script>

</body>

</html>

"""

    return html



if __name__ == "__main__":

    data = parse_skills()

    

    src_dir = os.path.dirname(__file__)

    out_json = os.path.join(src_dir, "skills_data.json")

    with open(out_json, "w", encoding="utf-8") as f:

        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Generated {out_json} successfully with {data['total_skills']} skills in {len(data['categories'])} categories.")



    html_content = generate_html(data)

    out_html = os.path.join(src_dir, "skill_picker_widget.html")

    with open(out_html, "w", encoding="utf-8") as f:

        f.write(html_content)

    print(f"Generated {out_html} successfully.")

