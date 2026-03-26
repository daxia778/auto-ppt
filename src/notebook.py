"""
NotebookLM 自动化模块
负责导航、创建 Notebook、发送 Prompt 和抓取回复。
"""
import asyncio
from playwright.async_api import Page, TimeoutError

class NotebookError(Exception):
    pass

class NotebookManager:
    """管理 NotebookLM 页面交互"""

    def __init__(self, page: Page, config: dict):
        self.page = page
        self.config = config.get("notebooklm", {})
        self.timeout = self.config.get("timeout", 120000)
        self.response_timeout = self.config.get("response_timeout", 180000)

    async def create_new_notebook(self):
        """点击创建新的 Notebook"""
        print("[Notebook] 准备创建新 Notebook...")
        try:
            # 兼容中英文界面的通用选择器
            # 寻找“新建笔记本”或“New notebook”或带加号的卡片
            new_btn_selectors = [
                "text='新建笔记本'",
                "text='New notebook'",
                "div[role='button']:has-text('New notebook')",
                ".create-notebook-button" # fallback class, 需要实际运行时确认
            ]
            
            clicked = False
            for selector in new_btn_selectors:
                try:
                    # 设置较短超时快速试探
                    btn = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    if btn:
                        await btn.click()
                        clicked = True
                        break
                except TimeoutError:
                    continue
            
            if not clicked:
                # 终极 fallback，可能 UI 改版了，尝试找所有 button 靠猜测（不推荐长期用）
                print("[Notebook] 警告：未找到标准的新建按钮，尝试 fallback 点击第一个看起来像新建的按钮")
                buttons = await self.page.query_selector_all("div[role='button']")
                if buttons:
                    await buttons[0].click() # 通常第一个主要按钮是新建
                else:
                    raise NotebookError("无法找到创建 Notebook 的按钮，可能 Google 更新了 UI。")

            print("[Notebook] 已点击新建。")
            await self.page.wait_for_timeout(3000) # 等待页面加载

        except Exception as e:
            raise NotebookError(f"创建 Notebook 失败: {str(e)}")

    async def add_source(self, text_content: str):
        """
        添加默认文本素材（MVP 阶段简化的输入方式）。
        实际项目中可扩展为上传 PDF/URL。
        """
        print("[Notebook] 添加素材内容...")
        # 1. 点击添加来源 (Add source)
        try:
            add_source_btns = [
                "text='粘贴文本'",
                "text='Copied text'",
                "button:has-text('Copied text')"
            ]
            
            clicked = False
            for selector in add_source_btns:
                try:
                    btn = await self.page.wait_for_selector(selector, timeout=5000)
                    if btn:
                        await btn.click()
                        clicked = True
                        break
                except TimeoutError:
                    continue

            if not clicked:
                # 可能是因为新建 Notebook 会直接弹出来源抽屉
                pass

            # 2. 找到文本输入框并输入
            # 这里依赖 role=textbox
            textbox = await self.page.wait_for_selector("textarea, [role='textbox']", timeout=10000)
            await textbox.fill(text_content)
            
            # 3. 点击插入 (Insert)
            insert_btns = ["text='插入'", "text='Insert'"]
            for selector in insert_btns:
                 try:
                    btn = await self.page.wait_for_selector(selector, timeout=3000)
                    if btn:
                        await btn.click()
                        break
                 except TimeoutError:
                     continue
            
            print("[Notebook] 素材添加完成，等待处理...")
            # 给平台一些时间处理素材
            await self.page.wait_for_timeout(5000)

        except Exception as e:
            print(f"[Notebook] 添加素材遇到问题 (可能是 UI 差异)，尝试继续执行: {str(e)}")


    async def send_prompt_and_get_response(self, prompt: str) -> str:
        """发送 Prompt 给 NotebookLM，等待并提取回复"""
        print(f"[Notebook] 发送 Prompt...")
        
        try:
            # 1. 找到聊天输入框 — 尝试多种选择器兼容不同 UI 版本
            chat_input_selectors = [
                "textarea[placeholder*='提示']",
                "textarea[placeholder*='Type']",
                "textarea[placeholder*='type']",
                "textarea[placeholder*='Ask']",
                "textarea[placeholder*='输入']",
                "textarea[placeholder*='发送']",
                "textarea[aria-label*='chat']",
                "textarea[aria-label*='Chat']",
                "textarea[aria-label*='prompt']",
                "textarea[aria-label*='Prompt']",
                "[contenteditable='true'][role='textbox']",
                "[contenteditable='true'][aria-label*='chat']",
                "[contenteditable='true'][aria-label*='Chat']",
                "div[role='textbox']",
                "textarea",  # 最宽泛的 fallback
            ]
            
            chat_input = None
            for selector in chat_input_selectors:
                try:
                    el = await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                    if el:
                        chat_input = el
                        print(f"[Notebook] 找到输入框 (选择器: {selector})")
                        break
                except TimeoutError:
                    continue
            
            if not chat_input:
                # 终极 fallback: 用 JS 在 DOM 中搜索
                print("[Notebook] 标准选择器均未命中，尝试 JS fallback 搜索输入框...")
                js_handle = await self.page.evaluate_handle('''() => {
                    // 先找 textarea
                    const ta = document.querySelector('textarea');
                    if (ta) return ta;
                    // 再找 contenteditable
                    const ce = document.querySelector('[contenteditable="true"]');
                    if (ce) return ce;
                    // 再找 role=textbox
                    const tb = document.querySelector('[role="textbox"]');
                    if (tb) return tb;
                    return null;
                }''')
                
                chat_input = js_handle.as_element()
                
                if not chat_input:
                    raise NotebookError("无法找到聊天输入框，NotebookLM UI 可能已更新")
                print("[Notebook] 通过 JS fallback 找到输入框")
            
            await chat_input.fill(prompt)
            
            # 2. 发送 (回车)
            await chat_input.press("Enter")
            print("[Notebook] Prompt 已发送，等待 AI 生成回复 (可能需要 30-60 秒)...")

            # 3. 等待回复完成 — 轮询检测页面内容长度稳定
            # NotebookLM 使用流式传输，networkidle 永远不会触发
            # 动画元素(闪烁光标/时间戳)导致精确文本比对永远不匹配
            # 改用：比较文本长度差值，连续 3 次长度变化 < 20 则认为生成完毕
            await self.page.wait_for_timeout(8000)  # 先等 8 秒让生成启动和动画出来
            
            print("[Notebook] 正在等待 AI 生成完成 (内容长度稳定检测)...")
            prev_len = 0
            stable_count = 0
            max_wait_ms = self.response_timeout
            elapsed = 0
            poll_interval = 5000  # 每 5 秒检查一次
            length_tolerance = 20  # 允许的长度波动 (动画/时间戳导致的微小变动)
            
            while elapsed < max_wait_ms:
                current_text = await self.page.inner_text("body")
                current_len = len(current_text)
                
                if prev_len > 100 and abs(current_len - prev_len) < length_tolerance:
                    stable_count += 1
                    if stable_count >= 3:
                        print(f"[Notebook] 内容已稳定 (长度: {current_len} 字符)，认为生成完毕")
                        break
                else:
                    stable_count = 0
                    
                prev_len = current_len
                await self.page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                
                if elapsed % 15000 == 0:
                    print(f"[Notebook] 已等待 {elapsed/1000:.0f} 秒，当前长度 {current_len}，仍在变化...")
            
            # 4. 提取最新的一条回复
            response_selectors = [
                "div[role='log'] > div",
                ".message-bubble",
                ".response-container",
                "div[data-message-author-role='assistant']",
                ".chat-message:last-child",
            ]
            
            elements = None
            for sel in response_selectors:
                found = await self.page.query_selector_all(sel)
                if found:
                    elements = found
                    break
            
            if not elements:
                # Fallback: 抽取整个页面的主体内容，交给 parser 去除杂质
                print("[Notebook] 未找到标准聊天气泡选择器，抓取页面主体。")
                body_text = await self.page.inner_text("body")
                return body_text

            # 获取最后一个气泡（通常是最新回复）
            last_msg = elements[-1]
            content = await last_msg.inner_text()
            
            print("[Notebook] 成功获取回复！")
            return content

        except Exception as e:
            raise NotebookError(f"交互失败: {str(e)}")

    def _log_progress(self, msg: str):
        """统一的进度日志打印"""
        print(f"[Studio] {msg}")

    async def generate_studio_presentation(self):
        """在 Studio 面板点击生成演示文稿"""
        self._log_progress("\n准备生成演示文稿...")
        try:
            # 首先确保 Studio 面板可见 — 可能需要先点击 Studio 标签页
            studio_tab_selectors = [
                "button:has-text('Studio')",
                "div[role='tab']:has-text('Studio')",
                "a:has-text('Studio')",
                "button:has-text('studio')",
                "mat-tab-label:has-text('Studio')",
                "button:has-text('Studio 指南')",
            ]
            
            for tab_selector in studio_tab_selectors:
                try:
                    tab = await self.page.wait_for_selector(tab_selector, timeout=3000, state="visible")
                    if tab:
                        await tab.click()
                        self._log_progress("已点击 Studio 标签页")
                        await self.page.wait_for_timeout(2000)
                        break
                except TimeoutError:
                    continue
            
            # 找到 Studio 面板中的"演示文稿"按钮
            presentation_btn_selectors = [
                "button[aria-label='演示文稿']",
                "button[aria-label='Presentation']",
                "mat-card:has-text('演示文稿')",
                "mat-card:has-text('Presentation')",
                "div[role='button']:has-text('演示文稿')",
                "div[role='button']:has-text('Presentation')",
            ]
            
            clicked = False
            for selector in presentation_btn_selectors:
                try:
                    btn = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    if btn:
                        await btn.scroll_into_view_if_needed()
                        await btn.click()
                        clicked = True
                        self._log_progress("已点击「演示文稿」按钮，触发生成指令")
                        break
                except TimeoutError:
                    continue
            
            if not clicked:
                # JS fallback: 搜索所有可点击元素中包含"演示文稿"或"Presentation"的
                self._log_progress("标准选择器未命中，尝试 JS fallback...")
                found = await self.page.evaluate('''() => {
                    const allElements = document.querySelectorAll('button, [role="button"], mat-card, a');
                    for (const el of allElements) {
                        const text = el.textContent || '';
                        if (text.includes('演示文稿') || text.includes('Presentation')) {
                            el.scrollIntoView();
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                if found:
                    clicked = True
                    self._log_progress("通过 JS fallback 点击了演示文稿按钮")
                    
            if not clicked:
                raise NotebookError("无法在 Studio 面板找到「演示文稿」按钮")
            
            # 处理可能的“确认生成”对话框
            try:
                confirm_btns = [
                    "button:has-text('生成')", 
                    "button:has-text('确认')",
                    "button:has-text('Generate')",
                    "button:has-text('Confirm')"
                ]
                for c_selector in confirm_btns:
                    confirm_btn = await self.page.query_selector(c_selector)
                    if confirm_btn and await confirm_btn.is_visible():
                        await confirm_btn.click()
                        self._log_progress("已点击弹窗的确认生成按钮")
                        break
            except Exception:
                pass # 没有弹窗是正常的
                
        except Exception as e:
            raise NotebookError(f"触发演示文稿生成失败: {str(e)}")

    async def wait_for_presentation_ready(self) -> bool:
        """等待演示文稿生成完成 (可能需要 1-3 分钟)"""
        self._log_progress("等待 AI 生成 PPT，这通常需要 1-2 分钟，请耐心等待...")
        
        # 从配置中获取超时时间
        studio_config = self.config.get("studio", {}) if isinstance(self.config, dict) else {}
        timeout_ms = studio_config.get("generation_timeout", 180000)
        poll_interval = studio_config.get("poll_interval", 3000)
        
        more_options_selector = "button[aria-label='更多选项'], button[aria-label='More options']"
        
        self._log_progress(f"最大等待时间: {timeout_ms/1000} 秒")
        
        elapsed = 0
        last_log_time = 0
        
        try:
            # 手动轮询以便打印进度
            while elapsed < timeout_ms:
                # 检查按钮是否出现
                btn_visible = await self.page.evaluate(
                    f"!!document.querySelector(\"{more_options_selector}\")"
                )
                
                if btn_visible:
                    self._log_progress("[OK] 演示文稿生成完毕！")
                    await self.page.wait_for_timeout(3000) # 等待动画动画稳定
                    return True
                
                # 每隔 10 秒打印一次进度日志，避免刷屏
                if elapsed - last_log_time >= 10000:
                    self._log_progress(f"已等待 {elapsed/1000} 秒，正在持续生成中...")
                    last_log_time = elapsed
                    
                await self.page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                
            self._log_progress("[FAIL] 等待生成超时。")
            return False
            
        except Exception as e:
            self._log_progress(f"[ERROR] 检查生成状态时出错: {str(e)}")
            return False

    async def download_presentation(self, dest_dir: str = "./output") -> str:
        """打开菜单并点击下载 PowerPoint"""
        self._log_progress("准备下载 PPTX 文件...")
        import os
        try:
            # 1. 点击“更多选项” (⋯) 按钮
            more_options_selector = "button[aria-label='更多选项'], button[aria-label='More options']"
            more_btn = await self.page.wait_for_selector(more_options_selector, timeout=5000, state="visible")
            
            if not more_btn:
                raise NotebookError("未找到生成的演示文稿的操作菜单")
                
            await more_btn.hover()
            await more_btn.click()
            self._log_progress("已打开操作菜单")
            
            # 等待菜单渲染
            await self.page.wait_for_timeout(1500)
            
            # 2. 找到并点击 "下载 PowerPoint (.pptx)" 选项
            download_selectors = [
                "button[role='menuitem']:has-text('PowerPoint')",
                "button[role='menuitem']:has-text('.pptx')",
                ".mat-mdc-menu-item:has-text('PowerPoint')"
            ]
            
            studio_config = self.config.get("studio", {}) if isinstance(self.config, dict) else {}
            download_wait = studio_config.get("download_wait", 30000)
            
            # 准备接管下载事件
            async with self.page.expect_download(timeout=download_wait) as download_info:
                clicked = False
                for selector in download_selectors:
                    try:
                        menu_item = await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                        if menu_item:
                            await menu_item.click()
                            clicked = True
                            self._log_progress("已点击下载 PowerPoint 按钮")
                            break
                    except TimeoutError:
                        continue
                
                if not clicked:
                    # Fallback
                    await self.page.evaluate('''() => {
                        const items = Array.from(document.querySelectorAll('[role="menuitem"], .mat-mdc-menu-item'));
                        const pptItem = items.find(el => el.textContent.includes('PowerPoint') || el.textContent.includes('pptx'));
                        if (pptItem) pptItem.click();
                    }''')
                    
            download = await download_info.value
            
            suggested_filename = download.suggested_filename
            self._log_progress(f"检测到下载任务: {suggested_filename}")
            
            # 直接使用 download.save_as 保存到最终绝对路径，这比拷贝临时文件更稳
            os.makedirs(dest_dir, exist_ok=True)
            final_path = os.path.abspath(os.path.join(dest_dir, suggested_filename))
            
            # 这一步会等待文件完全写入盘
            await download.save_as(final_path)
            
            self._log_progress(f"[OK] 文件已保存至: {final_path}")
            return final_path
            
        except TimeoutError:
             raise NotebookError("下载超时：服务器未能及时响应或网络断开")
        except Exception as e:
            raise NotebookError(f"下载 PPT 失败: {str(e)}")
