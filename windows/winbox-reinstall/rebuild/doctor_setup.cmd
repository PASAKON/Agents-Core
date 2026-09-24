@echo off
rem doctor_setup.cmd — put the Machine Contract doctor on winbox (ADR 0031, IRON §58). Idempotent; run over ssh:
rem     ssh winbox "cmd /c C:\mooniex\rebuild\doctor_setup.cmd"
rem 1. sparse, shallow clone of Agents-Core at C:\mooniex\Agents\Core (tools/ config/ state/ scripts/ lib/ only —
rem    the doctor needs config\machine-contract.yaml + tools\machine_doctor.py and writes state\machine-*.json)
rem 2. PyYAML for the `py -3` launcher the task XML uses
rem 3. the weekly task MachineContractDoctor (Mon 04:00, account passg, interactive token) from the captured XML
rem 4. one snapshot + check so the first run happens in front of a human, not in a task log
set CORE=C:\mooniex\Agents\Core
if not exist %CORE%\.git git clone -q --depth 1 --filter=blob:none --sparse git@github.com:PASAKON/Agents-Core.git %CORE%
git -C %CORE% sparse-checkout set tools config state scripts lib
git -C %CORE% pull -q --ff-only origin main
echo --- clone
git -C %CORE% log --oneline -1
dir /B %CORE%
echo --- pyyaml
py -3 -m pip install -q pyyaml >nul 2>&1
py -3 -c "import yaml, sys; print('yaml', yaml.__version__, 'python', sys.version.split()[0])"
echo --- task
schtasks /Query /TN MachineContractDoctor >nul 2>&1 || schtasks /Create /XML C:\mooniex\rebuild\tasks\MachineContractDoctor.xml /TN MachineContractDoctor /F
schtasks /Query /TN MachineContractDoctor /FO LIST | findstr /I "TaskName Status Next"
echo --- doctor snapshot
py -3 %CORE%\tools\machine_doctor.py --machine winbox snapshot
echo --- doctor check
py -3 %CORE%\tools\machine_doctor.py --machine winbox check
echo doctor-check-rc=%ERRORLEVEL%
