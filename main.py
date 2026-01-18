from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os

URL = "https://wpadmin.ldjzmr.top"  # 改成你的網址

# 建議用環境變數放帳密，不要寫死在程式裡
USERNAME = os.getenv("SITE_USERNAME", "cai888  ")
PASSWORD = os.getenv("SITE_PASSWORD", "cai888")

# 你要改的地方：登入頁的元素 selector
LOGIN_USERNAME_SEL = 'input[name="username"]'   # 改成你網站的
LOGIN_PASSWORD_SEL = 'input[name="password"]'   # 改成你網站的
LOGIN_BUTTON_SEL   = 'button[type="submit"]'    # 改成你網站的

# 用來判斷「已登入」的元素 selector（例如：右上角帳號、登出按鈕、側欄某個固定項目）
LOGGED_IN_MARK_SEL = 'text=Logout'              # 改成你網站的（例如 "登出"）

def maybe_login(page):
    """
    如果看到登入欄位 -> 自動登入
    如果已登入 -> 直接略過
    """
    # 先快速看：是否已登入
    if page.locator(LOGGED_IN_MARK_SEL).first.is_visible():
        print("✅ 看起來已登入，略過登入流程")
        return

    # 再看：是否在登入介面（用 username 欄位是否存在/可見當判斷）
    try:
        page.wait_for_selector(LOGIN_USERNAME_SEL, timeout=2000)
    except PlaywrightTimeoutError:
        print("ℹ️ 沒看到登入欄位，也沒看到已登入標記。可能在載入中或頁面結構不同。")
        return

    # 看到登入欄位 -> 登入
    print("🔐 偵測到登入頁，開始自動登入...")
    page.fill(LOGIN_USERNAME_SEL, USERNAME)
    page.fill(LOGIN_PASSWORD_SEL, PASSWORD)
    page.click(LOGIN_BUTTON_SEL)

    # 等登入完成（以「已登入標記」出現為準）
    try:
        page.wait_for_selector(LOGGED_IN_MARK_SEL, timeout=10000)
        print("✅ 登入成功")
    except PlaywrightTimeoutError:
        print("⚠️ 登入後沒有看到已登入標記。")
        print("   可能原因：帳密錯 / 有 CAPTCHA / 有 2FA / selector 不對 / 登入後跳轉很慢")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded")

        # 有些站會自動跳轉登入或自動登入，給它一點時間穩定
        page.wait_for_timeout(1500)

        maybe_login(page)

        # ===== 這裡開始接你後續流程（例如點報表、填日期、下載 Excel）=====
        print("🚀 接下來你可以開始做後續自動化了")

        input("按 Enter 結束...")
        browser.close()

if __name__ == "__main__":
    main()
