@echo off
rem The CEO's "done" button on the winbox desktop (Agents-Core windows/desktop/).
rem Lifts the lock and puts Cookie Run back if it was running before.
rem Keep this file pure ASCII: cmd.exe reads a batch file in the OEM code page,
rem and Thai bytes in here break it. The Thai lives in the file NAME and in
rem ceo_button.ps1 (UTF-8 with a BOM). No pause: the message box is the answer.
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\mooniex\pclease\ceo_button.ps1" -Mode off
