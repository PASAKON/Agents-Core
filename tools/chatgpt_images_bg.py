#!/usr/bin/env python3
"""tools/chatgpt_images.py on a SHARED signed-in Chrome, from a BACKGROUND tab.

The stock runner takes pages[0] and calls bring_to_front(), which hijacks whatever a peer session
or the CEO has open in that Chrome (winbox 9224, reached from the Mac over the 9264 tunnel). This
wrapper opens its own tab with Target.createTarget {background: true}, never raises it, and closes
only that tab when it finishes. Same arguments as chatgpt_images.py.

    python3 tools/chatgpt_images_bg.py --json plates.json --out <dir> --cdp-url http://127.0.0.1:9264

JSON brief: [{"name", "prompt", "attach"?, "continue"?}]. "continue": "<earlier name>" edits inside
that image's chat, so a second picture keeps the first one's face or object (used for the Old Telling
lyre, 2026-10-09). Origin: CMO session cmo-f76492bf; the earlier gpt_bg.py wrapper was lost in a scratchpad.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import tools.chatgpt_images as ci  # noqa: E402


class BgBrowser(ci.ChatGPTBrowser):
    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        bsess = self._browser.new_browser_cdp_session()
        with ctx.expect_page() as info:
            bsess.send("Target.createTarget", {"url": "about:blank", "background": True})
        self.page = info.value
        self._own = self.page
        return self.page

    def close(self):
        try:
            self._own.close()
        except Exception:
            pass
        super().close()


ci.ChatGPTBrowser = BgBrowser

if __name__ == "__main__":
    sys.exit(ci.main())
