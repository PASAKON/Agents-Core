@echo off
rem The CEO's "use PC" button on the winbox desktop (Agents-Core windows/desktop/).
rem Locks the screen: no agent touches it until the "done" button is pressed.
rem Keep this file pure ASCII: cmd.exe reads a batch file in the OEM code page,
rem and Thai bytes in here break it. The Thai lives in the file NAME, in
rem ceo_button.ps1 (UTF-8 with a BOM), and in the base64 below. No pause: the
rem message box is the answer.
rem
rem No ceo_button.ps1 (not installed yet, or removed): say so in a box. Without
rem this the press flashed a console and did nothing, and he could not tell
rem whether the screen was locked. The message is UTF-16LE base64 so this file
rem stays ASCII; source in tests/test_pc_lease_ceo_hold.py.
if not exist "C:\mooniex\pclease\ceo_button.ps1" (
  powershell.exe -NoProfile -WindowStyle Hidden -EncodedCommand QQBkAGQALQBUAHkAcABlACAALQBBAHMAcwBlAG0AYgBsAHkATgBhAG0AZQAgAFMAeQBzAHQAZQBtAC4AVwBpAG4AZABvAHcAcwAuAEYAbwByAG0AcwA7ACAAJABvACAAPQAgAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABTAHkAcwB0AGUAbQAuAFcAaQBuAGQAbwB3AHMALgBGAG8AcgBtAHMALgBGAG8AcgBtADsAIAAkAG8ALgBUAG8AcABNAG8AcwB0ACAAPQAgACQAdAByAHUAZQA7ACAAWwB2AG8AaQBkAF0AWwBTAHkAcwB0AGUAbQAuAFcAaQBuAGQAbwB3AHMALgBGAG8AcgBtAHMALgBNAGUAcwBzAGEAZwBlAEIAbwB4AF0AOgA6AFMAaABvAHcAKAAkAG8ALAAgACcARA4hDkgOHg4aDkQOHw4lDkwOGw44DkgOIQ4gAEMAOgBcAG0AbwBvAG4AaQBlAHgAXABwAGMAbABlAGEAcwBlAFwAYwBlAG8AXwBiAHUAdAB0AG8AbgAuAHAAcwAxACAAQA4lDiIOIg4xDgcORA4hDkgORA4UDkkOFw4zDi0OMA5EDiMOCgABDiMOOA4TDjIOGg4tDgEOIABDAFQATwAgAEMOKw5JDhUONA4UDhUOMQ5JDgcOGw44DkgOIQ5DDisOIQ5IDicALAAgACcATQBvAG8AbgBpAGUAWAAnACwAIAAnAE8ASwAnACwAIAAnAFcAYQByAG4AaQBuAGcAJwApAA==
  exit /b 1
)
rem conhost, not the default terminal: on Windows 11 that can be Windows
rem Terminal, which ignores -WindowStyle Hidden and leaves a window over the
rem screen he is about to use. conhost honours it; /min covers the moment before.
start "" /min conhost.exe powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\mooniex\pclease\ceo_button.ps1" -Mode on
