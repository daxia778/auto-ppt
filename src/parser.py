"""
解析模块
将 NotebookLM 输出的 Markdown 文本解析为结构化的 Slide 数据结构。
"""
import re
from typing import List, Dict

class ParserError(Exception):
    pass

class ContentParser:
    """解析 Markdown 格式的 PPT 内容"""

    def __init__(self):
         pass

    def parse_markdown(self, text: str) -> List[Dict]:
        """
        解析 NotebookLM 回复的文本。
        支持多种格式变体：
        - 带/不带 ## 的页面标记 (如 "## 第1页" 或 "第1页")
        - 带/不带 ** 的字段标记 (如 "**标题**:" 或 "标题:")
        - 带/不带 - 的列表项 (如 "- 要点" 或 "* 要点" 或纯行)
        - 备注可能内联在最后一个要点行末尾
        """
        print("[Parser] 开始解析内容...")
        slides = []
        
        # 0. 清理：去掉 NotebookLM 常见的尾部说明文字
        clean_text = re.split(r'\n-{3,}\n|\n这是基于', text)[0]
        
        # 1. 按照页面标记切分内容
        # 支持: "## 第1页" / "第1页" / "## Page 1" / "Page 1"
        pages_raw = re.split(r'\n(?:#{1,3}\s+)?(?:第\d+页|Page\s*\d+)', clean_text)
        
        # 第一部分通常是开场白，跳过
        if len(pages_raw) > 1:
            pages_raw = pages_raw[1:]
        elif "标题" in clean_text and "要点" in clean_text:
            pages_raw = [clean_text]
        else:
             print("[Parser] 警告: 未检测到分页标记")
             pages_raw = [clean_text]

        for idx, page_content in enumerate(pages_raw):
            if not page_content.strip():
                continue

            slide_data = {
                "title": f"Slide {idx + 1}",
                "bullets": [],
                "notes": ""
            }

            # 提取备注 (先提取, 以便后续从要点中剥离)
            notes_match = re.search(r'(?:\*\*)?备注(?:\*\*)?[：:]\s*(.+)', page_content)
            if notes_match:
                slide_data["notes"] = notes_match.group(1).strip()

            # 提取标题 (可能后面跟 "要点:" 在同一行)
            title_match = re.search(r'(?:\*\*)?标题(?:\*\*)?[：:]\s*(.+)', page_content)
            if title_match:
                title_text = title_match.group(1).strip()
                title_text = re.sub(r'\s*(?:\*\*)?要点(?:\*\*)?[：:]\s*$', '', title_text).strip()
                slide_data["title"] = title_text

            # 提取要点区域: 从 "要点:" 到 "备注:" 或内容结尾
            bullets_section_match = re.search(
                r'(?:\*\*)?要点(?:\*\*)?[：:](.*?)(?=(?:\*\*)?备注(?:\*\*)?[：:]|\Z)',
                page_content, re.DOTALL
            )
            
            if bullets_section_match:
                bullets_text = bullets_section_match.group(1)
                # 尝试找带标记的列表项: "- xxx" 或 "* xxx" 或 "• xxx"
                bullets = re.findall(r'^[\-\*\u2022]\s+(.+)', bullets_text, re.MULTILINE)
                if not bullets:
                    # 没有列表标记，按行切分
                    lines = [line.strip() for line in bullets_text.split('\n') if line.strip()]
                    lines = [l for l in lines if not re.match(r'(?:\*\*)?备注(?:\*\*)?[：:]', l)]
                    bullets = lines
                
                # 最后一个要点可能内联了 "备注:" 部分
                if bullets:
                    last = bullets[-1]
                    notes_inline = re.search(r'\s*(?:\*\*)?备注(?:\*\*)?[：:]\s*(.+)', last)
                    if notes_inline:
                        bullets[-1] = re.sub(r'\s*(?:\*\*)?备注(?:\*\*)?[：:].*', '', last).strip()
                        if not slide_data["notes"]:
                            slide_data["notes"] = notes_inline.group(1).strip()
                
                slide_data["bullets"] = [b.strip() for b in bullets if b.strip()]
            
            slides.append(slide_data)
            
        print(f"[Parser] 成功解析出 {len(slides)} 页。")
        return slides
