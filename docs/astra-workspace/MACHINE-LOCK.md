# One machine, one driver

Astra and the Claude operator both drive the same Windows box. Two agents moving the
mouse at once corrupts both sessions and can fire things nobody intended.

**The lock is a file on the Windows machine:** `C:\mooniex\MACHINE-LOCK.txt`

- Before driving: read it. If it names somebody else, **wait — do not proceed.**
- Taking control: write one line — who you are, what you are doing, the time.
- Finishing: **empty the file.** Leaving it held blocks everyone.

If the file names a holder whose work has clearly finished, do not assume and do not
clear it yourself — report it to the CTO and let a human or the CTO release it.

**Planned order of work:** Astra designs the look (holds the machine) → hands the
recipe over and releases → the Claude operator applies it across the film (holds the
machine) → CTO reviews → repeat only if needed.

They are never both working. If Astra's session runs long enough that this becomes a
real bottleneck, the fallback is to move the repetitive half to the Mac — that is the
CEO's call, not an agent's.
