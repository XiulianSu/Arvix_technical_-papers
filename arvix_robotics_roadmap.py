import arxiv
import requests
import os
import time
import json
import re

# === 1. 配置区域 ===
KEYWORDS = [
    '"Humanoid Robot" AND "Reinforcement Learning"',
    '"Embodied AI" AND "Transformer"',
    '"Vision-Language-Action"',
    '"Sim-to-Real" AND "Humanoid"',
    '"Robot Manipulation" AND "Foundation Model"'
]

SAVE_DIR = r"/Users/xiuliansu/Documents/大四上学期/01 学业布局和职业规划/0104 行业研报与论文/Humanoid_Brain_Papers"
HISTORY_FILE = os.path.join(SAVE_DIR, "download_history.json")

# === 代理设置 (如果你在用 VPN，请确保这里设置正确，否则注释掉) ===
# os.environ['http_proxy'] = "http://127.0.0.1:7890"
# os.environ['https_proxy'] = "http://127.0.0.1:7890"

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# === 2. 核心工具函数 ===
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try: return set(json.load(f))
            except: return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(history_set), f, indent=2)

def get_chinese_blog_search_links(title):
    return {
        "机器之心": f"https://www.jiqizhixin.com/search?q={title}",
        "新智元": f"https://weixin.sogou.com/weixin?type=2&query=新智元 {title}"
    }

# === [核心修复] 自定义强力下载函数 ===
def download_file_robust(url, filepath, retries=3):
    """替代库自带的下载，使用 requests 库，更稳定"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 既然已经拿到 url (通常是 /abs/), 我们要转换成 PDF 链接
    # arxiv 库给的 pdf_url 属性通常是 http://arxiv.org/pdf/xxxx.xxxxxv1
    if "abs" in url:
        url = url.replace("abs", "pdf")
    
    # 确保 URL 以 .pdf 结尾 (虽然 ArXiv 有时不需要，但加上更保险)
    if not url.endswith(".pdf"):
        url += ".pdf"

    for i in range(retries):
        try:
            # timeout=60秒，stream=True 允许大文件
            response = requests.get(url, headers=headers, stream=True, timeout=60)
            response.raise_for_status() # 检查 404/403/429
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True # 下载成功
            
        except Exception as e:
            print(f"      ⚠️ 下载中断 (尝试 {i+1}/{retries}): {e}")
            if "429" in str(e):
                print("      🛑 触发429限流，强制休息 60 秒...")
                time.sleep(60)
            else:
                time.sleep(5)
            
            # 如果是最后一次重试还失败，删除可能损坏的文件
            if i == retries - 1 and os.path.exists(filepath):
                os.remove(filepath)
                
    return False

# === 3. 主逻辑 ===
def scrape_arxiv_papers(max_results=10):
    downloaded_ids = load_history()
    client = arxiv.Client(page_size=10, delay_seconds=3.0, num_retries=3)
    
    print(f"🚀 开始搜索 (强力下载模式)...")
    
    for query in KEYWORDS:
        print(f"\n🔍 搜索: {query}")
        try:
            search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.SubmittedDate)
            
            # 使用列表转换，防止生成器超时
            results = list(client.results(search))
            
            for result in results:
                try:
                    if result.published.year < 2023: continue
                    
                    paper_id = result.entry_id.split('/')[-1]
                    if paper_id in downloaded_ids: continue

                    safe_title = "".join([c for c in result.title if c.isalnum() or c in " ._-"]).strip()[:150]
                    pdf_path = os.path.join(SAVE_DIR, f"{safe_title}.pdf")
                    info_path = os.path.join(SAVE_DIR, f"{safe_title}_info.txt")

                    if os.path.exists(pdf_path):
                        downloaded_ids.add(paper_id)
                        continue

                    print(f"   ⬇️ 下载: {safe_title[:40]}...")
                    
                    # === 使用自定义下载函数 ===
                    # result.pdf_url 是 ArXiv 库提供的 PDF 链接
                    success = download_file_robust(result.pdf_url, pdf_path)
                    
                    if success:
                        print(f"      ✅ 完成")
                        blog_links = get_chinese_blog_search_links(result.title)
                        info_content = f"Title: {result.title}\nID: {paper_id}\nSummary:\n{result.summary}\n\n机器之心: {blog_links['机器之心']}\n新智元: {blog_links['新智元']}"
                        with open(info_path, "w", encoding="utf-8") as f: f.write(info_content)
                        
                        downloaded_ids.add(paper_id)
                        save_history(downloaded_ids)
                        time.sleep(5) # 乖乖休息
                    else:
                        print(f"      ❌ 下载最终失败，跳过。")

                except Exception as e:
                    print(f"   ⚠️ 处理单篇出错: {e}")

        except Exception as e:
             print(f"⚠️ 搜索出错 (可能是429): {e}")
             time.sleep(20)

    print(f"\n✨ 任务结束")

if __name__ == "__main__":
    scrape_arxiv_papers(max_results=10)