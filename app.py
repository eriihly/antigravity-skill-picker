# -*- coding: utf-8 -*-
"""
Antigravity Skill Studio - Desktop Application
Integrated Context Token Monitor + Skill Manager + Zero-CDN Offline UI + Frameless Window
+ Local Skill Importer + Findskill Auto-Download & Monitor
"""

import os
import sys
import json
import glob
import re
import sqlite3
import socket
import threading
import subprocess
import webbrowser
import shutil
import zipfile
import base64
import time
import tempfile
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import yaml
except ImportError:
    yaml = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "skills_config.json")
DEFAULT_DATA_PATH = os.path.join(APP_DIR, "src", "skills_data.json")
HTML_PATH = os.path.join(APP_DIR, "src", "app.html")

BRAIN_DIR = os.path.expanduser(r"~\.gemini\antigravity\brain")
DB_PATH = os.path.expanduser(r"~\.gemini\antigravity\conversation_summaries.db")
# ==========================================
# 1. Token Estimation Logic (仅供参考·上限未公开)
# ==========================================
# 【核心机制与免责说明】
# 1. 本计算方式基于纯文本离线启发式估算（CJK 汉字 * 1.3 + 非 CJK 单词与符号 * 1.05 + 预设 Prompt 估算）。
# 2. 估算数据仅供开发者监测会话长度变化趋势与防范长对话认知漂移参考，并非 Gemini 官方 Tokenizer 精确分词。
# 3. FIXED_MAX_TOKENS = 1_000_000 仅作为健康度可视化的标尺参考基准；实际上 Gemini / Antigravity 
#    底层模型的实际有效最大上下文窗口视具体模型版本、压缩调度机制而定，具体确切上限并未公开固定。
FIXED_MAX_TOKENS = 1_000_000
SYSTEM_PROMPT_ESTIMATE = 7000

GEMINI_SKILLS_DIR = os.path.expanduser(r"~\.gemini\skills")
DOWNLOADS_DIR = os.path.expanduser(r"~\Downloads")

def estimate_tokens(text: str) -> int:
    """启发式估算文本 Token 数（仅供参考）"""
    if not text:
        return 0
    cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))
    non_cjk = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', '', text)
    tokens_non_cjk = len(re.findall(r'\w+|[^\w\s]', non_cjk))
    return int(cjk * 1.3 + tokens_non_cjk * 1.05)


_LAST_LOG_STAT = None
_LAST_TOKEN_CACHE = None


def get_token_info():
    """Reads latest conversation from brain logs and calculates real-time tokens"""
    global _LAST_LOG_STAT, _LAST_TOKEN_CACHE
    db_map = {}
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT conversation_id, title FROM conversation_summaries")
            for cid, title in cur.fetchall():
                db_map[cid] = title or "未命名会话"
            conn.close()
        except Exception:
            pass

    pattern = os.path.join(BRAIN_DIR, "*", ".system_generated", "logs", "transcript_full.jsonl")
    files = glob.glob(pattern)
    if not files:
        return {
            "conversation_id": "none",
            "title": "未检测到活跃会话",
            "tokens": 0,
            "k_val": "0.0k",
            "percentage": "0.0%",
            "pct_num": 0.0,
            "level": "green",
            "desc": "黄金区间 (< 150k)",
            "color": "#10B981"
        }

    latest = max(files, key=lambda p: os.path.getmtime(p))
    cid = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(latest))))
    title = db_map.get(cid, f"会话 {cid[:8]}")

    try:
        cur_stat = (latest, os.path.getmtime(latest), os.path.getsize(latest))
        if _LAST_LOG_STAT == cur_stat and _LAST_TOKEN_CACHE is not None:
            res = dict(_LAST_TOKEN_CACHE)
            res["title"] = title
            return res
    except Exception:
        cur_stat = None

    content_chunks = []
    try:
        with open(latest, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    c = data.get("content", "")
                    if isinstance(c, str):
                        content_chunks.append(c)
                    if "thinking" in data and isinstance(data["thinking"], str):
                        content_chunks.append(data["thinking"])
                    if "tool_calls" in data:
                        content_chunks.append(json.dumps(data["tool_calls"], ensure_ascii=False))
                except Exception:
                    content_chunks.append(line)
    except Exception as e:
        print(f"Log read error: {e}")

    dialogue_tokens = estimate_tokens("".join(content_chunks))
    total_tokens = dialogue_tokens + SYSTEM_PROMPT_ESTIMATE
    pct = min(100.0, (total_tokens / FIXED_MAX_TOKENS) * 100.0)

    if total_tokens < 150_000:
        level, desc, color = "green", "黄金区间 (< 150k)", "#10B981"
    elif total_tokens < 300_000:
        level, desc, color = "yellow", "累积区间 (150k ~ 300k)", "#F59E0B"
    else:
        level, desc, color = "red", "警戒区间 (> 300k)", "#EF4444"

    res = {
        "conversation_id": cid,
        "title": title,
        "tokens": total_tokens,
        "k_val": f"{total_tokens / 1000.0:.1f}k",
        "percentage": f"{pct:.1f}%",
        "pct_num": round(pct, 2),
        "level": level,
        "desc": desc,
        "color": color
    }
    _LAST_LOG_STAT = cur_stat
    _LAST_TOKEN_CACHE = res
    return res



# ==========================================
# 2. In-Memory Fast Cache & Data Management
# ==========================================
_CACHED_APP_DATA = None
_CACHED_TOKEN_INFO = None


def get_cached_token_info():
    global _CACHED_TOKEN_INFO
    if _CACHED_TOKEN_INFO is None:
        _CACHED_TOKEN_INFO = get_token_info()
    return _CACHED_TOKEN_INFO


def _token_background_poller():
    global _CACHED_TOKEN_INFO
    while True:
        try:
            _CACHED_TOKEN_INFO = get_token_info()
        except Exception:
            pass
        time.sleep(2)


_CONFIG_LOCK = threading.Lock()


def load_app_data(force_reload=False):
    global _CACHED_APP_DATA
    with _CONFIG_LOCK:
        if _CACHED_APP_DATA is not None and not force_reload:
            return _CACHED_APP_DATA

        if not os.path.exists(CONFIG_PATH):
            example_cfg = os.path.join(APP_DIR, "skills_config.example.json")
            if os.path.exists(example_cfg):
                try:
                    shutil.copyfile(example_cfg, CONFIG_PATH)
                except Exception:
                    pass

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if "favorites" not in d:
                        d["favorites"] = []
                    _CACHED_APP_DATA = d
                    return _CACHED_APP_DATA
            except Exception:
                pass

        if os.path.exists(DEFAULT_DATA_PATH):
            try:
                with open(DEFAULT_DATA_PATH, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    d["favorites"] = []
                    _CACHED_APP_DATA = d
                    return _CACHED_APP_DATA
            except Exception:
                pass

        _CACHED_APP_DATA = {"categories": [], "skills": [], "favorites": []}
        return _CACHED_APP_DATA


def save_app_data(data):
    global _CACHED_APP_DATA
    with _CONFIG_LOCK:
        _CACHED_APP_DATA = data
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True, "已保存"
        except Exception as e:
            return False, str(e)
# ==========================================
# 3. Skill Metadata Parsing & Installation Engine
# ==========================================
def extract_frontmatter(content: str):
    """Extracts name, description, category from YAML frontmatter in markdown content."""
    content = (content or "").lstrip("\ufeff")
    m = re.search(r'^---\s*\r?\n(.*?)\r?\n---', content, re.DOTALL)
    name, desc, category = "", "", ""
    if m:
        fm_text = m.group(1)
        if yaml:
            try:
                data = yaml.safe_load(fm_text)
                if isinstance(data, dict):
                    name = str(data.get("name") or "").strip()
                    desc = str(data.get("description") or "").strip()
                    category = str(data.get("category") or "").strip()
            except Exception:
                pass
        if not name:
            nm = re.search(r'^name:\s*["\']?(.*?)["\']?\s*$', fm_text, re.MULTILINE)
            if nm:
                name = nm.group(1).strip()
        if not desc:
            dm = re.search(r'^description:\s*(.*?)(?=\n[a-zA-Z0-9_\-]+:|\Z)', fm_text, re.MULTILINE | re.DOTALL)
            if dm:
                desc = ' '.join(dm.group(1).split()).strip('"\'')
        if not category:
            cm = re.search(r'^category:\s*["\']?(.*?)["\']?\s*$', fm_text, re.MULTILINE)
            if cm:
                category = cm.group(1).strip()
    return name, desc, category


def parse_markdown_metadata(content: str, fallback_name: str = ""):
    content = (content or "").lstrip("\ufeff")
    name, desc, cat = extract_frontmatter(content)
    if not name:
        hm = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if hm:
            name = hm.group(1).strip()
        else:
            name = fallback_name
    # Keep alphanumeric, hyphen, underscore, dot, and Chinese/CJK characters, sanitize path-illegal chars
    sanitized = re.sub(r'[/\\:*?"<>|\r\n\t]', '-', name).strip('-. ')
    sanitized = re.sub(r'\s+', '-', sanitized).lower()
    if sanitized:
        name = sanitized
    else:
        name = re.sub(r'[/\\:*?"<>|\r\n\t\s]', '-', (fallback_name or "custom-skill")).strip('-. ').lower() or "custom-skill"

    if not desc:
        clean_body = re.sub(r'^---\s*.*?---\s*', '', content, flags=re.DOTALL)
        # Scan non-empty lines for the first paragraph/line that is not a markdown header
        for line in clean_body.splitlines():
            line_str = line.strip()
            if line_str and not line_str.startswith('#'):
                desc = ' '.join(line_str.split())[:220]
                break
    if not desc:
        desc = f"{name} 专家级辅助技能"
    return name, desc, cat
def register_skill_in_config(name: str, category: str, description: str, installed: bool = True):
    """Registers a skill in skills_config.json and updates cache."""
    data = load_app_data()
    cat = (category or "").strip() or "⚡ 通用规范与工作流"

    if cat not in data.get("categories", []):
        data.setdefault("categories", []).append(cat)

    skills_list = data.setdefault("skills", [])
    existing = next((s for s in skills_list if s.get("name") == name), None)

    if existing:
        existing["installed"] = installed
        if description and description.strip():
            existing["description"] = description.strip()
        if category and category.strip():
            existing["category"] = cat
    else:
        new_skill = {
            "name": name,
            "category": cat,
            "description": description.strip() if description else f"{name} 专家技能",
            "installed": installed
        }
        skills_list.insert(0, new_skill)

    data["total_skills"] = len(skills_list)
    save_app_data(data)
    return {
        "name": name,
        "category": cat,
        "description": description or f"{name} 专家技能",
        "installed": installed
    }


def is_safe_rel_path(base_dir: str, rel_path: str) -> bool:
    """Ensure relative path does not escape base directory (prevent Zip Slip)"""
    dest = os.path.abspath(os.path.join(base_dir, rel_path))
    base = os.path.abspath(base_dir)
    return dest.startswith(base + os.sep) or dest == base


def install_skill_from_zip(zip_path: str, default_category: str = None):
    """Extracts a zip file, installs it to ~/.gemini/skills, and registers it."""
    if not os.path.exists(zip_path):
        return False, None, "压缩包不存在"

    os.makedirs(GEMINI_SKILLS_DIR, exist_ok=True)
    installed_skills = []

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            # 1. Look for SKILL.md files
            skill_mds = [n for n in namelist if os.path.basename(n).lower() == "skill.md"]

            if skill_mds:
                for smd in skill_mds:
                    content = zf.read(smd).decode("utf-8", errors="ignore")
                    base_dir = os.path.dirname(smd)
                    fallback = os.path.basename(base_dir) if base_dir else os.path.splitext(os.path.basename(zip_path))[0]
                    name, desc, cat = parse_markdown_metadata(content, fallback_name=fallback)
                    final_cat = (default_category or "").strip() or cat or "⚡ 通用规范与工作流"

                    target_dir = os.path.join(GEMINI_SKILLS_DIR, name)
                    os.makedirs(target_dir, exist_ok=True)

                    prefix = (base_dir + "/") if base_dir else ""
                    for member in namelist:
                        if member.startswith(prefix) and not member.endswith("/"):
                            rel = member[len(prefix):].replace("/", os.sep)
                            if not is_safe_rel_path(target_dir, rel):
                                continue  # Block Zip Slip attempts
                            target_file = os.path.join(target_dir, rel)
                            os.makedirs(os.path.dirname(target_file), exist_ok=True)
                            with open(target_file, "wb") as out_f:
                                out_f.write(zf.read(member))

                    skill_obj = register_skill_in_config(name, final_cat, desc, installed=True)
                    installed_skills.append(skill_obj)
            else:
                # 2. General markdown archive - MUST contain at least one valid .md file to qualify as a skill!
                md_files = [n for n in namelist if n.lower().endswith(".md") and not os.path.basename(n).startswith(".")]
                if not md_files:
                    return False, None, "压缩包中未检测到有效技能说明文件 (.md 或 SKILL.md)"

                fallback = os.path.splitext(os.path.basename(zip_path))[0]
                main_md = min(md_files, key=lambda x: len(x))
                content = zf.read(main_md).decode("utf-8", errors="ignore")
                name, desc, cat = parse_markdown_metadata(content, fallback_name=fallback)

                final_cat = (default_category or "").strip() or cat or "⚡ 通用规范与工作流"
                target_dir = os.path.join(GEMINI_SKILLS_DIR, name)
                os.makedirs(target_dir, exist_ok=True)

                for member in namelist:
                    if not member.endswith("/"):
                        rel = member.replace("/", os.sep)
                        if not is_safe_rel_path(target_dir, rel):
                            continue
                        target_file = os.path.join(target_dir, rel)
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        with open(target_file, "wb") as out_f:
                            out_f.write(zf.read(member))

                smd_path = os.path.join(target_dir, "SKILL.md")
                if not os.path.exists(smd_path):
                    with open(smd_path, "w", encoding="utf-8") as smd_f:
                        smd_f.write(f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n\n{desc}\n")

                skill_obj = register_skill_in_config(name, final_cat, desc, installed=True)
                installed_skills.append(skill_obj)

        if installed_skills:
            return True, installed_skills[0], f"成功解压并安装 {len(installed_skills)} 个技能"
        return False, None, "压缩包中未检测到有效技能文件"
    except Exception as e:
        return False, None, f"解压安装异常: {e}"
def install_skill_from_folder(folder_path: str, default_category: str = None):
    """Installs a skill from a local folder."""
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return False, None, "文件夹路径无效"

    fallback_name = os.path.basename(os.path.normpath(folder_path))
    skill_md = os.path.join(folder_path, "SKILL.md")
    content = ""

    if os.path.exists(skill_md):
        try:
            with open(skill_md, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            pass
    else:
        # Search for any markdown file
        for f in os.listdir(folder_path):
            if f.lower().endswith(".md"):
                try:
                    with open(os.path.join(folder_path, f), "r", encoding="utf-8", errors="ignore") as mf:
                        content = mf.read()
                        break
                except Exception:
                    pass

    name, desc, cat = parse_markdown_metadata(content, fallback_name=fallback_name)
    final_cat = (default_category or "").strip() or cat or "⚡ 通用规范与工作流"

    os.makedirs(GEMINI_SKILLS_DIR, exist_ok=True)
    target_dir = os.path.join(GEMINI_SKILLS_DIR, name)

    # Copy files if source is not already inside the target directory
    if os.path.abspath(folder_path) != os.path.abspath(target_dir):
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            shutil.copytree(folder_path, target_dir)
        except Exception as e:
            return False, None, f"复制技能目录失败: {e}"

    # Ensure SKILL.md exists
    smd_path = os.path.join(target_dir, "SKILL.md")
    if not os.path.exists(smd_path):
        try:
            with open(smd_path, "w", encoding="utf-8") as f:
                f.write(f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n\n{desc}\n")
        except Exception:
            pass

    skill_obj = register_skill_in_config(name, final_cat, desc, installed=True)
    return True, skill_obj, f"成功导入本地技能 @{name}"


def install_skill_from_file(file_path: str, default_category: str = None):
    """Installs a skill from a single .md file."""
    if not os.path.exists(file_path):
        return False, None, "文件不存在"

    fallback_name = os.path.splitext(os.path.basename(file_path))[0]
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return False, None, f"读取文件失败: {e}"

    name, desc, cat = parse_markdown_metadata(content, fallback_name=fallback_name)
    final_cat = (default_category or "").strip() or cat or "⚡ 通用规范与工作流"

    os.makedirs(GEMINI_SKILLS_DIR, exist_ok=True)
    target_dir = os.path.join(GEMINI_SKILLS_DIR, name)
    os.makedirs(target_dir, exist_ok=True)

    target_md = os.path.join(target_dir, "SKILL.md")
    try:
        with open(target_md, "w", encoding="utf-8") as f:
            if not content.startswith("---"):
                f.write(f"---\nname: {name}\ndescription: {desc}\n---\n\n" + content)
            else:
                f.write(content)
    except Exception as e:
        return False, None, f"写入技能文件失败: {e}"

    skill_obj = register_skill_in_config(name, final_cat, desc, installed=True)
    return True, skill_obj, f"成功导入技能文件 @{name}"


def install_skill_from_path(path: str, default_category: str = None):
    """Unified dispatcher to install from folder, zip, or md."""
    if not path or not os.path.exists(path):
        return False, None, f"路径不存在: {path}"

    if os.path.isdir(path):
        return install_skill_from_folder(path, default_category)

    lower = path.lower()
    if lower.endswith(".zip"):
        return install_skill_from_zip(path, default_category)
    elif lower.endswith(".md"):
        return install_skill_from_file(path, default_category)
    else:
        return False, None, "仅支持导入文件夹、.zip 压缩包或 .md 技能文件"


def scan_unregistered_local_skills():
    """Scans ~/.gemini/skills for directories not currently in skills_config.json."""
    if not os.path.exists(GEMINI_SKILLS_DIR):
        return []

    data = load_app_data()
    cfg_names = set(s.get("name") for s in data.get("skills", []))
    unregistered = []

    try:
        for item in os.listdir(GEMINI_SKILLS_DIR):
            item_path = os.path.join(GEMINI_SKILLS_DIR, item)
            if os.path.isdir(item_path) and not item.startswith("."):
                skill_md = os.path.join(item_path, "SKILL.md")
                name = item
                desc = ""
                cat = "⚡ 通用规范与工作流"
                if os.path.exists(skill_md):
                    try:
                        with open(skill_md, "r", encoding="utf-8", errors="ignore") as mf:
                            c = mf.read(4096)
                            n, d, c_cat = parse_markdown_metadata(c, fallback_name=item)
                            if n: name = n
                            if d: desc = d
                            if c_cat: cat = c_cat
                    except Exception:
                        pass
                else:
                    for f in os.listdir(item_path):
                        if f.lower().endswith(".md"):
                            try:
                                with open(os.path.join(item_path, f), "r", encoding="utf-8", errors="ignore") as mf:
                                    c = mf.read(4096)
                                    n, d, c_cat = parse_markdown_metadata(c, fallback_name=item)
                                    if n: name = n
                                    if d: desc = d
                                    if c_cat: cat = c_cat
                                    break
                            except Exception:
                                pass

                # Crucial fix: Neither folder name nor parsed skill name should be in cfg_names
                if item in cfg_names or name in cfg_names:
                    continue

                if not desc:
                    desc = f"{item} 本地已装技能"
                unregistered.append({
                    "name": name,
                    "folder_name": item,
                    "description": desc,
                    "category": cat,
                    "path": item_path
                })
    except Exception as e:
        print(f"[Studio] Scan unregistered error: {e}")

    return unregistered


def import_unregistered_skills(names: list, category: str = None):
    """Batch registers existing local skills in ~/.gemini/skills to skills_config.json."""
    if not names:
        return False, 0, "未选择任何技能"

    unreg_items = scan_unregistered_local_skills()
    unreg_by_name = {u["name"]: u for u in unreg_items}
    unreg_by_folder = {u["folder_name"]: u for u in unreg_items}
    count = 0

    for name in names:
        item = unreg_by_name.get(name) or unreg_by_folder.get(name)
        if item:
            cat = (category or "").strip() or item.get("category") or "⚡ 通用规范与工作流"
            register_skill_in_config(item["name"], cat, item.get("description", ""), installed=True)
            count += 1
        else:
            # Fallback direct check on folder or name
            for candidate in [name, os.path.join(GEMINI_SKILLS_DIR, name)]:
                p = candidate if os.path.isabs(candidate) else os.path.join(GEMINI_SKILLS_DIR, candidate)
                if os.path.exists(p) and os.path.isdir(p):
                    install_skill_from_folder(p, category)
                    count += 1
                    break

    return True, count, f"已成功收录 {count} 个本地技能"
def get_recent_downloads(limit: int = 10):
    """Returns recently modified .zip or .md files in the user Downloads folder."""
    if not os.path.exists(DOWNLOADS_DIR):
        return []

    recent = []
    try:
        for f in os.listdir(DOWNLOADS_DIR):
            fpath = os.path.join(DOWNLOADS_DIR, f)
            if not os.path.isfile(fpath):
                continue
            lower = f.lower()
            if not (lower.endswith(".zip") or lower.endswith(".md")):
                continue
            if lower.endswith((".crdownload", ".tmp", ".part")) or f.startswith(("~$", ".")):
                continue

            try:
                mtime = os.path.getmtime(fpath)
                size_kb = round(os.path.getsize(fpath) / 1024.0, 1)
                recent.append({
                    "filename": f,
                    "path": fpath,
                    "size_kb": size_kb,
                    "mtime": mtime,
                    "mtime_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
                    "type": "zip" if lower.endswith(".zip") else "md"
                })
            except Exception:
                pass

        recent.sort(key=lambda x: x["mtime"], reverse=True)
        return recent[:limit]
    except Exception:
        return []


# ==========================================
# 4. Downloads Folder Background Watcher & Findskill Bridge
# ==========================================
_DOWNLOAD_WATCH_ACTIVE = False
_DOWNLOAD_WATCH_START_TIME = 0.0
_PROCESSED_DOWNLOAD_FILES = set()
_RECENT_AUTO_IMPORTS = []
_IMPORT_LOCK = threading.Lock()


def open_findskill_website():
    """Opens findskill (skills.sh) in default browser and enables auto-watcher."""
    global _DOWNLOAD_WATCH_ACTIVE, _DOWNLOAD_WATCH_START_TIME
    _DOWNLOAD_WATCH_ACTIVE = True
    _DOWNLOAD_WATCH_START_TIME = time.time() - 5.0

    target_url = "https://skills.sh"
    try:
        webbrowser.open(target_url)
    except Exception as e:
        print(f"[Studio] webbrowser open error: {e}")

    return {
        "success": True,
        "url": target_url,
        "downloads_dir": DOWNLOADS_DIR,
        "watching": True
    }


def _download_watcher_loop():
    """Background worker continuously checking Downloads folder when active."""
    global _DOWNLOAD_WATCH_ACTIVE, _DOWNLOAD_WATCH_START_TIME, _PROCESSED_DOWNLOAD_FILES, _RECENT_AUTO_IMPORTS
    while True:
        try:
            if _DOWNLOAD_WATCH_ACTIVE and os.path.exists(DOWNLOADS_DIR):
                for fname in os.listdir(DOWNLOADS_DIR):
                    fpath = os.path.join(DOWNLOADS_DIR, fname)
                    if fname.startswith((".", "~$", "tmp")) or fname.endswith((".crdownload", ".tmp", ".part", ".download")):
                        continue
                    if fpath in _PROCESSED_DOWNLOAD_FILES:
                        continue
                    try:
                        mtime = max(os.path.getmtime(fpath), os.path.getctime(fpath))
                    except Exception:
                        continue
                    if mtime < _DOWNLOAD_WATCH_START_TIME:
                        continue

                    is_zip = fname.lower().endswith(".zip")
                    is_md = fname.lower().endswith(".md")
                    is_dir = os.path.isdir(fpath)

                    if is_zip or is_md or is_dir:
                        # Ensure write completion: verify size > 0 and file can be opened
                        if not is_dir:
                            try:
                                if os.path.getsize(fpath) == 0:
                                    continue
                                with open(fpath, "rb") as test_f:
                                    test_f.seek(0, 2)
                            except Exception:
                                continue

                        ok, skill_obj, msg = install_skill_from_path(fpath, default_category="⚡ 通用规范与工作流")
                        # Always record in processed files so failing non-skills don't spin in high-CPU loop
                        _PROCESSED_DOWNLOAD_FILES.add(fpath)
                        if ok and skill_obj:
                            with _IMPORT_LOCK:
                                _RECENT_AUTO_IMPORTS.append(skill_obj)
                            print(f"[Studio] 自动导入下载技能成功: @{skill_obj['name']} ({msg})")
        except Exception:
            pass
        time.sleep(1.5)


def install_online_skill(target: str, category: str = None):
    """Installs an online skill using npx skills add or direct repository download."""
    target = target.strip()
    if not target:
        return False, None, "未指定技能标识或地址"

    clean_pkg = re.sub(r'^https?://skills\.sh/', '', target)
    clean_pkg = re.sub(r'^https?://github\.com/', '', clean_pkg).strip('/')

    # 1. Try npx skills add if available
    try:
        print(f"[Studio] 正在尝试通过 npx skills add 安装: {clean_pkg}")
        cmd = ["npx", "skills", "add", clean_pkg, "-g", "-y"]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        
        # Verify npx actually succeeded with exit code 0
        if res.returncode == 0:
            unreg = scan_unregistered_local_skills()
            if unreg:
                matched = next((u for u in unreg if u["name"] in clean_pkg or clean_pkg.endswith(u["name"])), unreg[0])
                cat = (category or "").strip() or matched.get("category") or "⚡ 通用规范与工作流"
                register_skill_in_config(matched["name"], cat, matched.get("description", ""), installed=True)
                return True, matched, f"成功通过 npx 安装 @{matched['name']}"
            else:
                pkg_leaf = clean_pkg.split('/')[-1].split('@')[0]
                return True, {"name": pkg_leaf}, f"成功通过 npx 安装 @{pkg_leaf}"
        else:
            print(f"[Studio] npx skills add 返回非零退出码: {res.returncode}, 切换至 GitHub 直接拉取...")
    except Exception as e:
        print(f"[Studio] npx install error ({e})，切换至 GitHub 直接拉取...")

    # 2. Try direct GitHub ZIP archive download
    temp_zip = None
    try:
        repo_m = re.search(r'([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)', clean_pkg)
        if not repo_m:
            return False, None, "未能识别 GitHub 仓库格式 (请提供 owner/repo 或完整链接)"
        owner, repo = repo_m.group(1), repo_m.group(2).split("@")[0]

        temp_zip = os.path.join(tempfile.gettempdir(), f"{owner}_{repo}_{int(time.time())}_temp.zip")
        downloaded = False

        for branch in ["main", "master"]:
            zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
            try:
                req = urllib.request.Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(temp_zip, "wb") as out_f:
                    out_f.write(resp.read())
                downloaded = True
                break
            except Exception:
                continue

        if not downloaded:
            return False, None, f"无法从 GitHub 下载仓库 {owner}/{repo} (未找到 main/master 分支或网络不可达)"

        ok, skill_obj, msg = install_skill_from_zip(temp_zip, default_category=category)
        if ok:
            return True, skill_obj, f"已在线下载并安装: @{skill_obj['name']}"
        else:
            return False, None, msg
    except Exception as e:
        return False, None, f"在线下载安装失败: {e}"
    finally:
        if temp_zip and os.path.exists(temp_zip):
            try: os.remove(temp_zip)
            except Exception: pass

    return False, None, "未能成功安装该技能，请检查名称或网络连接"
# ==========================================
# 5. Lightweight Local HTTP Server & API
# ==========================================
class StudioApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(APP_DIR, "src"), **kwargs)

    def _read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                return json.loads(body.decode("utf-8"))
        except Exception:
            pass
        return {}

    def do_GET(self):
        clean_path = self.path.split("?")[0]
        if clean_path in ["", "/", "/index.html"]:
            self.path = "/app.html"
            return super().do_GET()

        if clean_path == "/api/token":
            info = get_cached_token_info()
            self._send_json(info)
            return

        if clean_path == "/api/data":
            data = load_app_data()
            self._send_json(data)
            return

        if clean_path == "/api/scan-unregistered":
            items = scan_unregistered_local_skills()
            self._send_json({"items": items, "total": len(items)})
            return

        if clean_path == "/api/check-auto-imports":
            global _RECENT_AUTO_IMPORTS, _DOWNLOAD_WATCH_ACTIVE
            with _IMPORT_LOCK:
                items = list(_RECENT_AUTO_IMPORTS)
                _RECENT_AUTO_IMPORTS.clear()
            self._send_json({
                "items": items,
                "watching": _DOWNLOAD_WATCH_ACTIVE,
                "downloads_dir": DOWNLOADS_DIR
            })
            return

        if clean_path == "/api/recent-downloads":
            items = get_recent_downloads(limit=10)
            self._send_json({"items": items})
            return

        return super().do_GET()

    def do_POST(self):
        clean_path = self.path.split("?")[0]

        if clean_path == "/api/save":
            body = self._read_json_body()
            try:
                ok, msg = save_app_data(body)
                self._send_json({"success": ok, "message": msg})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, status=400)
            return

        if clean_path == "/api/reset":
            if os.path.exists(DEFAULT_DATA_PATH):
                with open(DEFAULT_DATA_PATH, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    d["favorites"] = []
                save_app_data(d)
                self._send_json({"success": True, "data": d})
            else:
                self._send_json({"success": False, "message": "找不到基准数据"}, status=404)
            return

        if clean_path == "/api/open-findskill":
            res = open_findskill_website()
            self._send_json(res)
            return

        if clean_path == "/api/import-local-path":
            body = self._read_json_body()
            path = body.get("path", "").strip()
            cat = body.get("category")
            ok, skill_obj, msg = install_skill_from_path(path, default_category=cat)
            self._send_json({"success": ok, "skill": skill_obj, "message": msg, "data": load_app_data()})
            return

        if clean_path == "/api/import-unregistered":
            body = self._read_json_body()
            names = body.get("names", [])
            cat = body.get("category")
            ok, count, msg = import_unregistered_skills(names, category=cat)
            self._send_json({"success": ok, "imported_count": count, "message": msg, "data": load_app_data()})
            return

        if clean_path == "/api/upload-skill":
            body = self._read_json_body()
            fname = os.path.basename(body.get("filename", "uploaded_skill.zip"))
            b64_data = body.get("base64", "")
            cat = body.get("category")
            if not b64_data:
                self._send_json({"success": False, "message": "未接收到文件数据"}, status=400)
                return

            try:
                raw_bytes = base64.b64decode(b64_data)
                temp_dest = os.path.join(tempfile.gettempdir(), fname)
                with open(temp_dest, "wb") as tf:
                    tf.write(raw_bytes)
                ok, skill_obj, msg = install_skill_from_path(temp_dest, default_category=cat)
                try: os.remove(temp_dest)
                except Exception: pass
                self._send_json({"success": ok, "skill": skill_obj, "message": msg, "data": load_app_data()})
            except Exception as e:
                self._send_json({"success": False, "message": f"处理上传文件失败: {e}"}, status=500)
            return

        if clean_path == "/api/install-online":
            body = self._read_json_body()
            target = body.get("target", "").strip()
            cat = body.get("category")
            ok, skill_obj, msg = install_online_skill(target, category=cat)
            self._send_json({"success": ok, "skill": skill_obj, "message": msg, "data": load_app_data()})
            return

        if clean_path == "/api/pick-folder":
            path = None
            if _GLOBAL_WINDOW_API:
                path = _GLOBAL_WINDOW_API.pick_local_folder()
            self._send_json({"path": path})
            return

        if clean_path == "/api/pick-file":
            path = None
            if _GLOBAL_WINDOW_API:
                path = _GLOBAL_WINDOW_API.pick_local_file()
            self._send_json({"path": path})
            return

        if clean_path in ["/api/update-skill-desc", "/api/update-skill-description"]:
            body = self._read_json_body()
            name = (body.get("name") or "").strip()
            desc = (body.get("description") or body.get("desc") or "").strip()
            if not name:
                self._send_json({"success": False, "message": "未提供技能名称"}, status=400)
                return
            if not desc:
                self._send_json({"success": False, "message": "描述内容不能为空"}, status=400)
                return
            data = load_app_data()
            skill = next((s for s in data.get("skills", []) if s.get("name") == name), None)
            if not skill:
                self._send_json({"success": False, "message": f"未找到技能 @{name}"}, status=404)
                return
            skill["description"] = desc
            ok, msg = save_app_data(data)
            self._send_json({"success": ok, "message": msg, "skill": skill})
            return

        self.send_error(404)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port):
    load_app_data(force_reload=True)
    get_cached_token_info()

    t_poller = threading.Thread(target=_token_background_poller, daemon=True)
    t_poller.start()

    t_watcher = threading.Thread(target=_download_watcher_loop, daemon=True)
    t_watcher.start()

    server = ThreadingHTTPServer(("127.0.0.1", port), StudioApiHandler)
    try:
        server.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ==========================================
# 6. JS Window Controls Bridge
# ==========================================
import ctypes
user32 = ctypes.windll.user32
_ACTIVE_DESKTOP_WINDOW = None
_GLOBAL_WINDOW_API = None


class StudioWindowApi:
    """
    Exposed to JS as window.pywebview.api.
    CRITICAL: Never attach the Window object as an instance attribute (self._window)
    """
    def __init__(self):
        self._is_mini = False
        self._is_maximized = False
        self._prev_width = 1280
        self._prev_height = 850

    def pick_local_folder(self):
        global _ACTIVE_DESKTOP_WINDOW
        if _ACTIVE_DESKTOP_WINDOW:
            try:
                import webview
                res = _ACTIVE_DESKTOP_WINDOW.create_file_dialog(webview.FOLDER_DIALOG)
                if res and len(res) > 0:
                    return res[0]
            except Exception as e:
                print(f"[Studio] pick_local_folder error: {e}")
        return None

    def pick_local_file(self):
        global _ACTIVE_DESKTOP_WINDOW
        if _ACTIVE_DESKTOP_WINDOW:
            try:
                import webview
                file_types = ('Skill Files (*.zip;*.md)', 'All files (*.*)')
                res = _ACTIVE_DESKTOP_WINDOW.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
                if res and len(res) > 0:
                    return res[0]
            except Exception as e:
                print(f"[Studio] pick_local_file error: {e}")
        return None

    def enter_mini_mode(self):
        global _ACTIVE_DESKTOP_WINDOW
        if _ACTIVE_DESKTOP_WINDOW and not self._is_mini:
            try:
                if hasattr(_ACTIVE_DESKTOP_WINDOW, 'native') and _ACTIVE_DESKTOP_WINDOW.native:
                    hwnd = _ACTIVE_DESKTOP_WINDOW.native.Handle.ToInt64()
                    if user32.IsZoomed(hwnd):
                        _ACTIVE_DESKTOP_WINDOW.restore()
                        self._is_maximized = False
                        time.sleep(0.05)
            except Exception:
                pass

            try:
                curr_w = _ACTIVE_DESKTOP_WINDOW.width
                curr_h = _ACTIVE_DESKTOP_WINDOW.height
                if curr_w > 550 and curr_h > 250:
                    self._prev_width = curr_w
                    self._prev_height = curr_h
            except Exception:
                pass

            self._is_mini = True
            try:
                _ACTIVE_DESKTOP_WINDOW.resize(500, 125)
                _ACTIVE_DESKTOP_WINDOW.on_top = True
            except Exception as e:
                print(f"[Studio] resize mini error: {e}")

            try:
                _ACTIVE_DESKTOP_WINDOW.evaluate_js("setMiniMode(true)")
            except Exception:
                pass
            return True
        return False

    def exit_mini_mode(self):
        global _ACTIVE_DESKTOP_WINDOW
        if _ACTIVE_DESKTOP_WINDOW and self._is_mini:
            self._is_mini = False
            target_w = max(850, self._prev_width or 1280)
            target_h = max(600, self._prev_height or 850)
            try:
                _ACTIVE_DESKTOP_WINDOW.resize(target_w, target_h)
                _ACTIVE_DESKTOP_WINDOW.on_top = False
            except Exception as e:
                print(f"[Studio] resize restore error: {e}")

            try:
                _ACTIVE_DESKTOP_WINDOW.evaluate_js("setMiniMode(false)")
            except Exception:
                pass
            return True
        return False

    def toggle_mini_mode(self):
        if self._is_mini:
            return self.exit_mini_mode()
        return self.enter_mini_mode()

    def minimize(self):
        global _ACTIVE_DESKTOP_WINDOW
        if _ACTIVE_DESKTOP_WINDOW:
            try:
                _ACTIVE_DESKTOP_WINDOW.minimize()
                return True
            except Exception as e:
                print(f"[Studio] minimize error: {e}")
                try:
                    if hasattr(_ACTIVE_DESKTOP_WINDOW, 'native') and _ACTIVE_DESKTOP_WINDOW.native:
                        hwnd = _ACTIVE_DESKTOP_WINDOW.native.Handle.ToInt64()
                        user32.ShowWindow(hwnd, 6)
                        return True
                except Exception:
                    pass
        return False

    def maximize(self):
        global _ACTIVE_DESKTOP_WINDOW
        if _ACTIVE_DESKTOP_WINDOW:
            if self._is_mini:
                return self.exit_mini_mode()
            if self._is_maximized:
                _ACTIVE_DESKTOP_WINDOW.restore()
                self._is_maximized = False
            else:
                _ACTIVE_DESKTOP_WINDOW.maximize()
                self._is_maximized = True

    def close(self):
        global _ACTIVE_DESKTOP_WINDOW
        if _ACTIVE_DESKTOP_WINDOW:
            _ACTIVE_DESKTOP_WINDOW.destroy()


# ==========================================
# 7. Dual-Engine Desktop App Launcher
# ==========================================
def launch_desktop_app(url, port):
    global _ACTIVE_DESKTOP_WINDOW, _GLOBAL_WINDOW_API
    window_title = "Antigravity Skill Studio"
    window_api = StudioWindowApi()
    _GLOBAL_WINDOW_API = window_api

    # 1. Try pywebview frameless window
    try:
        import webview
        webview.settings['DRAG_REGION_SELECTOR'] = '.titlebar-drag-handle'
        webview.settings['DRAG_REGION_DIRECT_TARGET_ONLY'] = False
        print(f"[Studio] 正在启动纯白无边框桌面窗口: {url}")
        window = webview.create_window(
            title=window_title,
            url=url,
            js_api=window_api,
            width=1280,
            height=850,
            min_size=(320, 90),
            frameless=True,
            easy_drag=False,
            text_select=True,
            zoomable=True
        )
        _ACTIVE_DESKTOP_WINDOW = window
        webview.start()
        return
    except Exception as e:
        print(f"[Studio] pywebview 启动异常 ({e})，切换至 Edge 原生应用模式...")

    # 2. Try Edge App Mode
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
    ]
    edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)

    if edge_exe:
        print(f"[Studio] 正在通过 Edge 原生应用模式启动...")
        cmd = [edge_exe, f"--app={url}", "--window-size=1280,850"]
        p = subprocess.Popen(cmd)
        p.wait()
        return

    # 3. Fallback to default browser
    print(f"[Studio] 正在浏览器中打开: {url}")
    webbrowser.open(url)
    while True:
        time.sleep(1)


def main():
    if not os.path.exists(DEFAULT_DATA_PATH):
        build_script = os.path.join(APP_DIR, "src", "build_data.py")
        if os.path.exists(build_script):
            subprocess.run([sys.executable, build_script], check=True)

    port = find_free_port()
    start_server(port)
    app_url = f"http://127.0.0.1:{port}/?v={int(time.time())}"

    print(f"==================================================")
    print(f"  Antigravity Skill Studio 已启动 (纯白免配置离线引擎)")
    print(f"  服务地址: {app_url}")
    print(f"==================================================")

    launch_desktop_app(app_url, port)


if __name__ == "__main__":
    main()
