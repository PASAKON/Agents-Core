@echo off
rem The CEO's "use PC" button on the winbox desktop (Agents-Core windows/desktop/).
rem Locks the screen: no agent touches it until the "done" button is pressed.
rem Keep this file pure ASCII: cmd.exe reads a batch file in the OEM code page,
rem and Thai bytes in here break it. The Thai lives in the file NAME and in
rem ceo_button.ps1 (UTF-8 with a BOM). No pause: the message box is the answer.
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\mooniex\pclease\ceo_button.ps1" -Mode on
