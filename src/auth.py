"""
认证模块 - 管理 Google 登录态
使用 Playwright 持久化上下文复用 Cookie，避免重复登录。
"""
import os
from playwright.async_api import async_playwright, BrowserContext, Page


class AuthManager:
    """管理 Playwright 浏览器的登录态"""

    NOTEBOOKLM_URL = "https://notebooklm.google.com/"

    def __init__(self, config: dict):
        self.user_data_dir = config.get("browser", {}).get("user_data_dir", "./chrome_profile")
        self.headless = config.get("browser", {}).get("headless", False)
        self.slow_mo = config.get("browser", {}).get("slow_mo", 500)
        self.download_dir = config.get("browser", {}).get("download_dir", "./output")
        self._playwright = None
        self._context: BrowserContext | None = None

    async def launch_browser(self) -> BrowserContext:
        """启动浏览器（持久化上下文），复用已保存的登录态。"""
        os.makedirs(self.user_data_dir, exist_ok=True)
        os.makedirs(self.download_dir, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=os.path.abspath(self.user_data_dir),
            headless=self.headless,
            slow_mo=self.slow_mo,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            accept_downloads=True,
            downloads_path=os.path.abspath(self.download_dir),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        print("[Auth] 浏览器已启动")
        print(f"[Auth] 下载目录: {os.path.abspath(self.download_dir)}")
        return self._context

    async def ensure_logged_in(self, page: Page) -> bool:
        """检查是否已登录 Google。未登录则引导用户手动登录。"""
        await page.goto(self.NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        current_url = page.url

        if "accounts.google.com" in current_url or "signin" in current_url.lower():
            print("\n" + "=" * 60)
            print("  [WARNING] 未检测到 Google 登录态")
            print("  请在弹出的浏览器窗口中手动登录 Google 账号")
            print("  登录完成后，程序将自动继续...")
            print("=" * 60 + "\n")

            try:
                await page.wait_for_url(
                    f"{self.NOTEBOOKLM_URL}**",
                    timeout=300000,  # 5 分钟等待登录
                )
                print("[Auth] [OK] 登录成功!")
                return True
            except Exception:
                print("[Auth] [FAIL] 登录超时，请重新运行程序")
                return False
        else:
            print("[Auth] [OK] 已检测到登录态，无需重新登录")
            return True

    async def login_only(self):
        """仅执行登录流程（首次设置用）。"""
        context = await self.launch_browser()
        page = context.pages[0] if context.pages else await context.new_page()

        logged_in = await self.ensure_logged_in(page)
        if logged_in:
            print("[Auth] 登录态已保存到:", os.path.abspath(self.user_data_dir))

        await page.wait_for_timeout(2000)
        await self.close()
        return logged_in

    async def close(self):
        """关闭浏览器"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        print("[Auth] 浏览器已关闭")
