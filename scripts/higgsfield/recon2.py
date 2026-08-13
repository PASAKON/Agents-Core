#!/usr/bin/env python3
"""Recon round 2 (logged in): map Resolution/Duration/Ratio dropdowns, set 720p, read Generate cost.
READ-mostly. Does NOT generate. Run: .venv/bin/python scripts/higgsfield/recon2.py
"""
import json
import sys
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"


def dump_options(page):
    return page.evaluate(
        """() => {
          const out = [];
          const sel = '[role=option], [role=menuitemradio], [role=radio], [data-radix-collection-item]';
          document.querySelectorAll(sel).forEach(n => {
            const r = n.getBoundingClientRect();
            if (r.width && r.height)
              out.push({txt:(n.innerText||'').trim().slice(0,60),
                        aria:n.getAttribute('aria-label')||null,
                        data:n.getAttribute('data-value')||null,
                        cls:(n.className||'').toString().slice(0,80)});
          });
          return out;
        }"""
    )


def click_option_containing(page, substr):
    return page.evaluate(
        """(t) => {
          const cands = document.querySelectorAll('[role=option],[role=menuitemradio],[data-radix-collection-item],button');
          for (const n of cands) {
            const r = n.getBoundingClientRect();
            const txt = (n.innerText||'').trim();
            if (r.width && r.height && txt.includes(t)) { n.click(); return txt; }
          }
          return null;
        }""",
        substr,
    )


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "higgsfield.ai" in pg.url), None)
        if page is None:
            print("NO_HIGGSFIELD_TAB")
            sys.exit(1)
        print("TAB:", page.url)
        try:
            page.bring_to_front()
        except Exception:
            pass

        login_btn = page.query_selector(".hfnav-auth-login")
        print("LOGIN_BUTTON_PRESENT:", bool(login_btn))

        def gen_text():
            el = page.query_selector("button[type=submit]")
            try:
                return (el.inner_text() if el else "").replace("\n", " / ")
            except Exception:
                return None

        print("GENERATE_TEXT_NOW:", gen_text())

        for label in ["Resolution", "Duration", "Ratio"]:
            print(f"=== open {label} ===")
            try:
                page.locator(f'button[aria-label="{label}"]').first.click()
                page.wait_for_timeout(800)
                opts = dump_options(page)
                print(json.dumps(opts, ensure_ascii=False, indent=2))
            except Exception as e:
                print("ERR", label, repr(e))
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)

        # set 720p
        print("=== set 720p ===")
        try:
            page.locator('button[aria-label="Resolution"]').first.click()
            page.wait_for_timeout(800)
            res = click_option_containing(page, "720")
            print("CLICKED_OPTION:", res)
            page.wait_for_timeout(600)
        except Exception as e:
            print("SET_720_ERR:", repr(e))
        try:
            print("RESOLUTION_NOW:", page.locator('button[aria-label="Resolution"]').first.inner_text())
        except Exception as e:
            print("RES_READ_ERR:", repr(e))
        print("GENERATE_TEXT_AFTER_720:", gen_text())


if __name__ == "__main__":
    main()
