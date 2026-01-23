import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import re
#           dlg.locator('button:has-text("取消")').click()  這個要改確定
# ===== URLs =====
URL_ADMIN = "https://wpadmin.ldjzmr.top"              # 總站（新增商戶用）
URL_MERCHANT = "https://wpbrand.ldjzmr.top"      # 商戶後台（建角色用）

# ===== selectors: admin login =====
LOGIN_USERNAME_SEL = 'input[name="username"]'
LOGIN_PASSWORD_SEL = 'input[name="password"]'
LOGIN_BUTTON_SEL   = 'button:has-text("登錄")'
LOGGED_IN_MARK_SEL = 'text=退出登录'

# ===== selectors: admin merchant management =====
MERCHANT_MENU_SEL    = 'li.el-menu-item:has-text("商戶管理")'
ADD_MERCHANT_BTN_SEL = 'span:has-text("新增商户")'

# ===== 新增商戶表單（彈窗內 placeholder）=====
PH_NAME      = "請輸入商户名稱"
PH_SHARE     = "請輸入分成比例"
PH_SINGLE    = "請輸入單次開分金額"
PH_MINWASH   = "請輸入最低洗分金額"
PH_PHONE     = "請輸入聯繫人電話"
PH_LOGINACC  = "请设置登錄账號"
PH_LOGINPW   = "请设置登錄密碼"

# ===== 商戶後台：系統設置/角色/新增角色 =====
SYS_MENU_TEXT = "系統設置"
ROLE_TEXT     = "角色"
ADD_ROLE_TEXT = "新增角色"
ROLE_DIALOG_TEXT = "新增角色"

# 權限樹：展開「財務帳單」，勾「上下分交班中心」
FIN_NODE_TEXT  ="財務賬單"
SHIFT_NODE_TEXT = "上下分交班中心"

# ===== cache =====
CACHE_FILE = "merchant_cache.json"


def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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
        self.load_cache_to_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ===== UI =====
    def _build_ui(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        # --- 帳密區（總站） ---
        cred = ttk.LabelFrame(frm, text="登入資訊（總站）", padding=10)
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
        self.var_loginacc  = tk.StringVar(value="")   # ✅ 商戶登入帳號
        self.var_loginpw   = tk.StringVar(value="")   # ✅ 商戶登入密碼

        # --- 機台機器碼（01~N） ---
        mc = ttk.LabelFrame(frm, text="機台機器碼（由上往下 01~N）", padding=10)
        mc.pack(fill="x", pady=(10, 0))

        self.var_machine_count = tk.IntVar(value=1)
        ttk.Label(mc, text="機台數量").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(mc, from_=1, to=20, textvariable=self.var_machine_count, width=6).grid(row=0, column=1, sticky="w", padx=6)

        self.btn_build_codes = ttk.Button(mc, text="生成 01~N 欄位", command=self.build_machine_code_rows)
        self.btn_build_codes.grid(row=0, column=2, sticky="w", padx=6)

        # 放動態欄位的容器
        self.machine_codes_frame = ttk.Frame(mc)
        self.machine_codes_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        self.machine_code_vars = []  # 存每一台的 StringVar
        self.build_machine_code_rows()  # 啟動先生成一次

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

        ttk.Label(fields, text="登錄账號（商戶）").grid(row=row, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(fields, textvariable=self.var_loginacc, width=20).grid(row=row, column=3, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Label(fields, text="登錄密碼（商戶）").grid(row=row, column=0, sticky="w")
        ttk.Entry(fields, textvariable=self.var_loginpw, show="*", width=32).grid(row=row, column=1, sticky="w", padx=6, pady=3)

        # --- 控制按鈕 ---
        ctrl = ttk.Frame(frm)
        ctrl.pack(fill="x", pady=(10, 0))

        self.btn_start = ttk.Button(ctrl, text="開始（總站：登入→商戶管理→新增→填表）", command=self.on_start)
        self.btn_start.pack(side="left")

        self.btn_open_merchant = ttk.Button(ctrl, text="開商戶站（建立角色）", command=self.on_open_merchant_site)
        self.btn_open_merchant.pack(side="left", padx=8)

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

    # ===== cache: UI <-> JSON =====
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
        self.write_log("📂 已載入 merchant_cache.json" if data else "📂 尚無緩存檔（第一次使用）")

    def save_ui_to_cache(self):
        save_cache(self.collect_ui_data())
        self.write_log("💾 已寫入 merchant_cache.json")

    def on_close(self):
        try:
            self.save_ui_to_cache()
        finally:
            self.destroy()

    # ===== btn 1: admin flow =====
    def on_start(self):
        self.btn_start.config(state="disabled")
        self.save_ui_to_cache()
        threading.Thread(target=self.run_automation, daemon=True).start()

    def build_machine_code_rows(self):
        # 清空舊的
        for w in self.machine_codes_frame.winfo_children():
            w.destroy()
        self.machine_code_vars.clear()

        n = int(self.var_machine_count.get() or 1)
        for i in range(1, n + 1):
            v = tk.StringVar(value="")
            self.machine_code_vars.append(v)

            ttk.Label(self.machine_codes_frame, text=f"{i:02d}號台 機器碼").grid(row=i-1, column=0, sticky="w")
            ttk.Entry(self.machine_codes_frame, textvariable=v, width=48).grid(row=i-1, column=1, sticky="w", padx=6, pady=2)
    def strip_tail_digits(self, s: str) -> str:
        return re.sub(r"\d+$", "", (s or "").strip())

    def acc_with_seq(self, base: str, i: int) -> str:
        return f"{base}{i:02d}"


    def get_machine_codes(self):
        # 回傳 list，index 0 對應 01號台
        return [v.get().strip() for v in self.machine_code_vars]


    def run_automation(self):
        try:
            data = self.collect_ui_data()
            user = data["username"]
            pw   = data["password"]
            if not user or not pw:
                raise RuntimeError("總站帳號/密碼未填")

            payload = {
                "name": data["name"],
                "share": data["share"],
                "single": data["single"],
                "minwash": data["minwash"],
                "phone": data["phone"],
                "loginacc": data["loginacc"],
                "loginpw": data["loginpw"],
            }

            self.write_log("🚀 啟動 Playwright（總站）")
            play = sync_playwright().start()
            browser = play.chromium.launch(headless=False)
            page = browser.new_page()

            self.write_log(f"🌐 開啟總站：{URL_ADMIN}")
            page.goto(URL_ADMIN, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            # login
            if page.locator(LOGIN_USERNAME_SEL).count() > 0:
                self.write_log("🔐 登入總站")
                page.fill(LOGIN_USERNAME_SEL, user)
                page.fill(LOGIN_PASSWORD_SEL, pw)
                page.click(LOGIN_BUTTON_SEL)
                page.wait_for_timeout(3000)
                page.reload(wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
            else:
                self.write_log("✅ 可能已登入（總站）")

            # merchant menu
            self.write_log("➡️ 點：商戶管理")
            page.click(MERCHANT_MENU_SEL)
            page.wait_for_selector("div.el-table", timeout=10000)

            # add merchant
            self.write_log("➡️ 點：新增商户")
            page.click(ADD_MERCHANT_BTN_SEL)
            page.wait_for_selector('text=新增商户', timeout=10000)

            dlg = page.locator('.el-dialog:has-text("新增商户")').first

            def dlg_fill(ph: str, value: str):
                dlg.locator(f'input[placeholder="{ph}"]').first.fill(value)

            dlg_fill(PH_NAME, payload["name"])
            dlg_fill(PH_SHARE, payload["share"])
            dlg_fill(PH_SINGLE, payload["single"])
            dlg_fill(PH_MINWASH, payload["minwash"])
            dlg_fill(PH_PHONE, payload["phone"])
            dlg_fill(PH_LOGINACC, payload["loginacc"])
            dlg_fill(PH_LOGINPW, payload["loginpw"])

            self.write_log("🧾 已填入新增商戶欄位（停在畫面，給你手動按確定）")

        except Exception as e:
            self.write_log(f"❌ 發生錯誤：{e}")
            messagebox.showerror("錯誤", str(e))
        finally:
            self.btn_start.config(state="normal")

    # ===== btn 2: merchant backend role flow =====
    def on_open_merchant_site(self):
        self.btn_open_merchant.config(state="disabled")
        self.save_ui_to_cache()
        threading.Thread(target=self.run_open_merchant_site, daemon=True).start()
    def to_zh_num(self, n: int) -> str:
        # 1~99：一、二、三... 十、十一、十二... 二十、二十一...
        digits = ["零","一","二","三","四","五","六","七","八","九"]
        if n <= 0 or n >= 100:
            raise ValueError("目前只支援 1~99")

        if n < 10:
            return digits[n]
        if n == 10:
            return "十"
        if n < 20:
            return "十" + digits[n % 10]  # 11~19
        tens = n // 10
        ones = n % 10
        if ones == 0:
            return digits[tens] + "十"     # 20,30...
        return digits[tens] + "十" + digits[ones]  # 21~99

    def run_open_merchant_site(self):
        try:
            self.write_log("🚀 啟動 Playwright（商戶後台：建角色）")
            play = sync_playwright().start()
            browser = play.chromium.launch(headless=False)
            page = browser.new_page()

            self.write_log(f"🌐 開啟商戶後台：{URL_MERCHANT}")
            page.goto(URL_MERCHANT, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            # ===== 商戶後台登入 =====
            data = self.collect_ui_data()
            m_user = data["loginacc"]
            m_pw   = data["loginpw"]

            if not m_user or not m_pw:
                raise RuntimeError("商戶登入帳號/密碼未填")

            # selectors（商戶站常見寫法，多 selector 容錯）
            M_LOGIN_USER_SEL = 'input[name="username"], input[name="account"], input[placeholder*="账号"], input[placeholder*="帳號"]'
            M_LOGIN_PW_SEL   = 'input[name="password"], input[placeholder*="密码"], input[placeholder*="密碼"]'
            M_LOGIN_BTN_SEL  = 'button:has-text("登錄"), button:has-text("登录"), button:has-text("登入")'
            M_LOGGED_SEL     = 'text=退出, text=登出, text=退出登录, text=退出登錄'

            if page.locator(M_LOGIN_USER_SEL).count() > 0:
                self.write_log("🔐 偵測到商戶登入頁，填入商戶帳密")

                page.locator(M_LOGIN_USER_SEL).first.fill(m_user)
                page.locator(M_LOGIN_PW_SEL).first.fill(m_pw)
                page.locator(M_LOGIN_BTN_SEL).first.click()

                page.wait_for_timeout(2500)
                page.reload(wait_until="domcontentloaded")
                page.wait_for_timeout(1500)

                if page.locator(M_LOGGED_SEL).count() > 0:
                    self.write_log("✅ 商戶後台登入成功")
                else:
                    self.write_log("🟡 未偵測到登出標記，可能版面不同或還在載入")
            else:
                self.write_log("🟡 未偵測到商戶登入頁（可能已登入）")

            self.write_log("➡️ 系統設置")
            page.click(f'span:has-text("{SYS_MENU_TEXT}")')
            page.wait_for_timeout(800)

            self.write_log("➡️ 角色")
            page.click(f'li.el-menu-item span:has-text("{ROLE_TEXT}")')
            page.wait_for_timeout(1000)

            self.write_log("➡️ 新增角色")
            page.click(f'span:has-text("{ADD_ROLE_TEXT}")')
            page.wait_for_timeout(1000)

            dlg = page.locator(f'.el-dialog:has-text("{ROLE_DIALOG_TEXT}")').first

            self.write_log("✏️ 輸入角色名稱：子商戶")
            dlg.locator('input[placeholder="角色名稱"]').first.fill("子商戶")
            page.wait_for_timeout(300)

            self.write_log("▶ 展開：財務賬單")
            dlg.locator(
                '.el-tree-node__content:has(.el-tree-node__label:has-text("財務賬單")) .el-tree-node__expand-icon'
            ).first.click()
            page.wait_for_timeout(500)

            # 等「上下分交班中心」真的出現
            page.wait_for_selector(
                '.el-dialog:has-text("新增角色") .el-tree-node__label:has-text("上下分交班中心")',
                timeout=8000
            )

            self.write_log("☑ 勾選：上下分交班中心")
            dlg.locator(
                '.el-tree-node__content:has(.el-tree-node__label:has-text("上下分交班中心")) span.el-checkbox__inner'
            ).first.click()
            page.wait_for_timeout(500)
            self.write_log("🟡 已完成（先不按確定，停在畫面）")
            dlg.locator('button:has-text("取消")').click()

            self.write_log("➡️ 機器管理")
            page.click('span:has-text("機器管理")')
            page.wait_for_timeout(800)

            self.write_log("➡️ 机器列表")
            page.click('span:has-text("机器列表")')
            page.wait_for_timeout(800)
            
            data = self.collect_ui_data()
            merchant_name = data["name"].strip()
            m_acc = data["loginacc"].strip()
            m_pw  = data["loginpw"].strip()

            codes = self.get_machine_codes()
            n = len(codes)

            base_acc = self.strip_tail_digits(m_acc)  # 去掉尾巴數字

            for i in range(1, n + 1):
                seq = f"{i:02d}"
                machine_name = f"{merchant_name}{self.to_zh_num(i)}號台"
                machine_no   = machine_name
                machine_acc  = self.acc_with_seq(base_acc, i)
                machine_pw   = m_pw
                machine_code = codes[i-1]  # 你在 UI 填的第 i 行

                self.write_log(f"🧾 第{seq}台：開啟新增機器並填表")
                # 這裡假設你已經在機器列表頁，點「新增機器」開彈窗
                page.click('span:has-text("新增機器")')
                page.wait_for_timeout(800)

                dlg2 = page.locator('.el-dialog:has-text("新增機器")').first

                # 填必填
                dlg2.locator('input[placeholder="請輸入機器名稱"]').first.fill(machine_name)
                dlg2.locator('input[placeholder="請輸入機器编號"]').first.fill(machine_no)
                dlg2.locator('input[placeholder="請輸入機器碼"]').first.fill(machine_code)

                # 1) 先點機器碼那格（用你原本的 selector 就好）
                code_ipt = dlg2.locator('input[placeholder="請輸入機器碼"]').first
                code_ipt.click()
                code_ipt.press("Control+A")
                code_ipt.type(str(machine_code), delay=30)

                # 2) Tab 4 次（用 page.keyboard，不依賴 locator）
                for _ in range(4):
                    page.keyboard.press("Tab")
                    page.wait_for_timeout(120)

                # 3) 再用 placeholder 填帳密（先試這個，最省事）
                def force_set_input(locator, value: str):
                    locator.wait_for(state="visible", timeout=10000)
                    locator.scroll_into_view_if_needed()
                    locator.evaluate(
                        """(el, v) => {
                            el.focus();
                            el.value = v;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            el.blur();
                        }""",
                        str(value),
                    )

                # 帳密
                acc_ipt = dlg2.locator('input[placeholder="請輸入機器登錄賬號"]:visible').last
                pw_ipt  = dlg2.locator('input[placeholder="請輸入機器登錄密碼"]:visible').last

                force_set_input(acc_ipt, machine_acc)
                force_set_input(pw_ipt, machine_pw)



                self.write_log(f"🟡 第{seq}台已填好：請你手動按『確認』(我不自動按)")
                # 你手動按確認後，彈窗會關掉，程式才做下一台
                page.wait_for_selector('.el-dialog:has-text("新增機器")', state="detached", timeout=600000)

        except Exception as e:
            self.write_log(f"❌ 發生錯誤：{e}")
            messagebox.showerror("錯誤", str(e))
        finally:
            self.btn_open_merchant.config(state="normal")
    def dlg_fill_by_label(dlg, label_text: str, value: str):
        # 找到含有該 label 的表單列
        row = dlg.locator(
            f'xpath=//div[contains(@class,"el-form-item")]'
            f'[.//label[contains(normalize-space(.), "{label_text}")]]'
        ).first
        # 找該列裡的 input 填值
        row.locator('input').first.fill(value)



if __name__ == "__main__":
    app = MerchantTool()

    app.mainloop()
