import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os

URL = "https://wpadmin.ldjzmr.top"

# ===== selectors =====
LOGIN_USERNAME_SEL = 'input[name="username"]'
LOGIN_PASSWORD_SEL = 'input[name="password"]'
LOGIN_BUTTON_SEL   = 'button:has-text("登錄")'
LOGGED_IN_MARK_SEL = 'text=退出登录'

MERCHANT_MENU_SEL    = 'li.el-menu-item:has-text("商戶管理")'
ADD_MERCHANT_BTN_SEL = 'span:has-text("新增商户")'

# 表單欄位（placeholder）(保留著，但我們主要用 label 來填)
SEL_NAME      = 'input[placeholder="請輸入商户名稱"]'
SEL_SHARE1    = 'input[placeholder="請輸入分成比例"]'
SEL_SHARE2_X  = '(//input[@placeholder="請輸入分成比例"])[2]'
SEL_MIN_WASH  = 'input[placeholder="請輸入最低洗分金額"]'
SEL_PHONE     = 'input[placeholder="請輸入聯繫人電話"]'
SEL_LOGIN_ACC = 'input[placeholder="请设置登錄账號"]'
SEL_LOGIN_PW  = 'input[placeholder="请设置登錄密碼"]'

# 先跳過
SEL_REGION_IN = 'input[placeholder="请选择商户地域"]'
SEL_BAC1_X    = '(//input[@placeholder="請選擇需要開啓的百家"])[1]'
SEL_BAC2_X    = '(//input[@placeholder="請選擇需要開啓的百家"])[2]'

# ===== JSON 緩存 =====
CACHE_FILE = "merchant_cache.json"


def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # 檔案壞掉/格式錯就當沒緩存
        return {}


def save_cache(data: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class MerchantTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("商戶新增小幫手")
        self.geometry("720x620")

        self._build_ui()

        # 啟動時載入緩存
        self.load_cache_to_ui()

        # 關閉視窗也存一次
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        # --- 帳密區 ---
        cred = ttk.LabelFrame(frm, text="登入資訊", padding=10)
        cred.pack(fill="x")

        self.var_user = tk.StringVar(value="")
        self.var_pass = tk.StringVar(value="")

        ttk.Label(cred, text="帳號").grid(row=0, column=0, sticky="w")
        ttk.Entry(cred, textvariable=self.var_user, width=28).grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(cred, text="密碼").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(cred, textvariable=self.var_pass, show="*", width=28).grid(row=0, column=3, sticky="w", padx=6)

        # --- 新增商戶欄位 ---
        fields = ttk.LabelFrame(frm, text="新增商戶欄位（先跳過：地域/百家）", padding=10)
        fields.pack(fill="x", pady=(10, 0))

        self.var_name      = tk.StringVar(value="")
        self.var_share     = tk.StringVar(value="")
        self.var_single    = tk.StringVar(value="")
        self.var_minwash   = tk.StringVar(value="")
        self.var_phone     = tk.StringVar(value="")
        self.var_loginacc  = tk.StringVar(value="")
        self.var_loginpw   = tk.StringVar(value="")

        row = 0
        ttk.Label(fields, text="商户名稱").grid(row=row, column=0, sticky="w")
        ttk.Entry(fields, textvariable=self.var_name, width=32).grid(row=row, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(fields, text="分成比例(%)").grid(row=row, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(fields, textvariable=self.var_share, width=20).grid(row=row, column=3, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Label(fields, text="單次開分金額").grid(row=row, column=0, sticky="w")
        ttk.Entry(fields, textvariable=self.var_single, width=32).grid(row=row, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(fields, text="最低洗分金額").grid(row=row, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(fields, textvariable=self.var_minwash, width=20).grid(row=row, column=3, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Label(fields, text="聯繫人電話").grid(row=row, column=0, sticky="w")
        ttk.Entry(fields, textvariable=self.var_phone, width=32).grid(row=row, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(fields, text="登錄账號").grid(row=row, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(fields, textvariable=self.var_loginacc, width=20).grid(row=row, column=3, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Label(fields, text="登錄密碼").grid(row=row, column=0, sticky="w")
        ttk.Entry(fields, textvariable=self.var_loginpw, show="*", width=32).grid(row=row, column=1, sticky="w", padx=6, pady=3)

        # --- 控制按鈕 ---
        ctrl = ttk.Frame(frm)
        ctrl.pack(fill="x", pady=(10, 0))

        self.btn_start = ttk.Button(ctrl, text="開始（開網站→登入→商戶管理→新增→填表）", command=self.on_start)
        self.btn_start.pack(side="left")

        self.btn_clear = ttk.Button(ctrl, text="清空Log", command=lambda: self.log.delete("1.0", "end"))
        self.btn_clear.pack(side="left", padx=8)

        # --- Log ---
        logbox = ttk.LabelFrame(frm, text="Log", padding=10)
        logbox.pack(fill="both", expand=True, pady=(10, 0))
        self.log = ScrolledText(logbox, height=14)
        self.log.pack(fill="both", expand=True)

    def write_log(self, msg: str):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    # ===== 緩存：UI <-> JSON =====
    def collect_ui_data(self) -> dict:
        return {
            "username": self.var_user.get().strip(),
            "password": self.var_pass.get().strip(),
            "name": self.var_name.get().strip(),
            "share": self.var_share.get().strip(),
            "single": self.var_single.get().strip(),
            "minwash": self.var_minwash.get().strip(),
            "phone": self.var_phone.get().strip(),
            "loginacc": self.var_loginacc.get().strip(),
            "loginpw": self.var_loginpw.get().strip(),
        }

    def load_cache_to_ui(self):
        data = load_cache()
        self.var_user.set(data.get("username", ""))
        self.var_pass.set(data.get("password", ""))
        self.var_name.set(data.get("name", ""))
        self.var_share.set(data.get("share", ""))
        self.var_single.set(data.get("single", ""))
        self.var_minwash.set(data.get("minwash", ""))
        self.var_phone.set(data.get("phone", ""))
        self.var_loginacc.set(data.get("loginacc", ""))
        self.var_loginpw.set(data.get("loginpw", ""))
        if data:
            self.write_log("📂 已載入 merchant_cache.json")
        else:
            self.write_log("📂 尚無緩存檔（第一次使用）")

    def save_ui_to_cache(self):
        data = self.collect_ui_data()
        save_cache(data)
        self.write_log("💾 已寫入 merchant_cache.json")

    def on_close(self):
        try:
            self.save_ui_to_cache()
        finally:
            self.destroy()

    def on_start(self):
        self.btn_start.config(state="disabled")

        # 按開始先存一次（避免你填完還沒關就閃退）
        self.save_ui_to_cache()

        t = threading.Thread(target=self.run_automation, daemon=True)
        t.start()

    def run_automation(self):
        try:
            data = self.collect_ui_data()
            user = data["username"]
            pw   = data["password"]

            payload = {
                "name": data["name"],
                "share": data["share"],
                "single": data["single"],
                "minwash": data["minwash"],
                "phone": data["phone"],
                "loginacc": data["loginacc"],
                "loginpw": data["loginpw"],
            }

            def fill_by_label(page, label_text: str, value: str):
                row = page.locator(
                    f'xpath=//div[contains(@class,"el-form-item")]'
                    f'[.//label[contains(normalize-space(.), "{label_text}")]]'
                ).first
                inp = row.locator('input.el-input__inner').first
                inp.fill(value)

            self.write_log("🚀 開始啟動 Playwright")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()

                self.write_log(f"🌐 開啟網站：{URL}")
                page.goto(URL, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)

                # --- 登入 ---
                if page.locator(LOGIN_USERNAME_SEL).count() > 0:
                    self.write_log("🔐 偵測到登入頁，填入帳密並登入")
                    if not user or not pw:
                        raise RuntimeError("目前在登入頁，但你的帳號或密碼是空的")

                    page.fill(LOGIN_USERNAME_SEL, user)
                    page.fill(LOGIN_PASSWORD_SEL, pw)
                    page.click(LOGIN_BUTTON_SEL)

                    self.write_log("⏳ 等待跳轉後，強制刷新（模擬F5）")
                    page.wait_for_timeout(3000)
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                else:
                    self.write_log("✅ 看起來不是登入頁（可能已登入）")

                # --- 進商戶管理 ---
                self.write_log("➡️ 點：商戶管理")
                page.click(MERCHANT_MENU_SEL)
                page.wait_for_selector("div.el-table", timeout=10000)

                # --- 點新增商戶 ---
                self.write_log("➡️ 點：+ 新增商户")
                page.click(ADD_MERCHANT_BTN_SEL)

                # 等彈窗出現
                page.wait_for_selector('text=新增商户', timeout=10000)
                self.write_log("✅ 已進入新增商戶表單")

                # 先抓「新增商戶」彈窗（用標題定位）
                dlg = page.locator('.el-dialog:has-text("新增商户")').first

                def dlg_fill(placeholder: str, value: str):
                    dlg.locator(f'input[placeholder="{placeholder}"]').first.fill(value)

                dlg_fill("請輸入商户名稱", payload["name"])
                dlg_fill("請輸入分成比例", payload["share"])
                dlg_fill("請輸入單次開分金額", payload["single"])
                dlg_fill("請輸入最低洗分金額", payload["minwash"])
                dlg_fill("請輸入聯繫人電話", payload["phone"])
                dlg_fill("请设置登錄账號", payload["loginacc"])
                dlg_fill("请设置登錄密碼", payload["loginpw"])


                self.write_log("🧾 已填入你在軟體輸入的欄位")
                self.write_log("🟡 已跳過：商戶地域、百家（你說先不做）")
                self.write_log("🟢 現在停在畫面上，給你手動檢查與按確定/送出")

        except Exception as e:
            self.write_log(f"❌ 發生錯誤：{e}")
            messagebox.showerror("錯誤", str(e))
        finally:
            self.btn_start.config(state="normal")


if __name__ == "__main__":
    app = MerchantTool()
    app.mainloop()
