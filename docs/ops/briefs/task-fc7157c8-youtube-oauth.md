# task-fc7157c8 · YouTube API one-time setup for ILAG Studio

This file is the full brief. The task row carries only a pointer here because
the winbox spawn command line has a 32,767-char limit (see GH issue).

JOB: finish a one-time Google OAuth setup so the CTO can post YouTube comment replies for the channel ILAG Studio through the YouTube API. You click. You never copy, read out, type or paste any code, token or post-redirect address. The CEO asked for this on 2026-09-23 because he cannot reach a terminal.

MACHINE: winbox. The Cookie Run bot farms this screen: take the lease first (skill winbox-pc-lease). Before giving it back, close every window and tab you opened.

BROWSER: Chrome, Default profile. Account 0 in it is pass.gob1@gmail.com, the account that manages ILAG Studio in YouTube Studio. Use that account throughout. Maximise the window before clicking in the Cloud console.

WHAT WE ALREADY KNOW
- Google Cloud project number 407008779435. The OAuth client id starts `407008779435-bb924j`. It is a Web application client and today it refuses http://localhost:8765/ (redirect_uri_mismatch, probed server-side).
- The CEO opened the consent link on his phone and saw "Make.com". We believe that is only the app name on this project's consent screen. Confirm in step 1.
- A catcher is already listening on http://localhost:8765/ on THIS machine. When consent completes, the tab shows "ILAG auth captured. You can close this tab." The CTO collects the code from the catcher; you do nothing with it.

STEPS
1. https://console.cloud.google.com/auth/branding?project=407008779435 (if that page does not exist: https://console.cloud.google.com/apis/credentials/consent?project=407008779435). Report as text: app name, user type (Internal/External), publishing status (Testing / In production), and if Testing whether pass.gob1@gmail.com is listed as a test user. Change nothing here.
2. https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=407008779435 . If the button says Enable, click it. Report: already enabled, or you enabled it.
3. https://console.cloud.google.com/apis/credentials?project=407008779435 . Open the OAuth 2.0 client whose id starts 407008779435-bb924j. Report its name and the Authorized redirect URIs already there. Add URI exactly `http://localhost:8765/` (with the trailing slash). Save. Touch no other field and no other client.
4. Wait 2 minutes. Open this link exactly, do not edit it:
https://accounts.google.com/o/oauth2/v2/auth?client_id=407008779435-bb924jo1bbgf7uh6edla5u06gpd0vrig.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A8765%2F&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.force-ssl&access_type=offline&prompt=consent&state=FapxhxSUBX478uVhVWii4w&code_challenge=n207bnT3vsrdwDMPXS66iY-CDg_83Vpi_ZMw2Q4QjDM&code_challenge_method=S256
   Choose pass.gob1@gmail.com. If a screen asks you to choose a channel or brand account, choose ILAG Studio and report every name it offered. If Google says the app is unverified: Advanced, then Go to (app name). Allow. Stop when the tab shows "ILAG auth captured".
   If it shows Error 400 redirect_uri_mismatch: wait 3 more minutes and open the same link once more. Still failing: stop and report.

STOP AND REPORT WITHOUT CLICKING if you see: any billing, payment or free-trial prompt; a request to create a project or a new client; a prompt to publish or verify the consent screen; a login challenge for a password or 2FA code (the CEO does those himself).

DO NOT: copy or read out the address after the redirect or any code; change the consent screen, other clients, other APIs or IAM; open YouTube Studio; verify anything the steps do not ask for.

BUDGET: 45 steps, 6 screenshots. Answer in text.

REPORT (REPORT.md): the facts from steps 1 to 4, the exact text on the last page, and whether the lease was returned with your windows closed.
