"""Wrapper: reuse tools/chatgpt_images.py but drive ONLY our own background tab.
Opens a tab with CDP Target.createTarget(background=true); never bring_to_front;
never touches another tab. Closes our tab at the end (finally)."""
import sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "tools"))
import chatgpt_images as ci

class BgBrowser(ci.ChatGPTBrowser):
    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        before = {id(p) for p in ctx.pages}
        bs = self._browser.new_browser_cdp_session()
        res = bs.send("Target.createTarget", {"url": "https://chatgpt.com/", "background": True})
        self.target_id = res["targetId"]
        page = None
        for _ in range(40):
            for p in ctx.pages:
                try:
                    s = ctx.new_cdp_session(p)
                    tid = s.send("Target.getTargetInfo")["targetInfo"]["targetId"]
                    s.detach()
                except Exception:
                    continue
                if tid == self.target_id:
                    page = p
            if page: break
            time.sleep(0.5)
        if not page:
            raise RuntimeError("own background tab not found")
        self.page = page
        self.bs = bs
        return page

    def close(self):
        try:
            self.bs.send("Target.closeTarget", {"targetId": self.target_id})
        except Exception:
            pass
        super().close()

ci.ChatGPTBrowser = BgBrowser
if __name__ == "__main__":
    sys.exit(ci.main())
