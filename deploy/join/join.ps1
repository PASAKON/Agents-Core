# join.ps1 - make this Windows machine a MoonieX org node (Org Mesh W4.3).
# ASCII only, PowerShell 5.1 compatible. Run it in an ELEVATED PowerShell (Run as administrator).
#
#   $env:ORG_JOIN_TOKEN = '<t>'; $env:ORG_JOIN_HOST = '<name>'
#   iwr -UseBasicParsing https://<hub>/org-join/join.ps1 | iex
#
# or, with the same arguments as join.sh (the token then shows in this window's history):
#
#   & ([scriptblock]::Create((iwr -UseBasicParsing https://<hub>/org-join/join.ps1).Content)) --token <t> --host <name> [--hq-root <path>]
#
# Arguments (the --name form and the -Name form both work)
#   --token <t>      the one-time token from `hq_join mint` (or $env:ORG_JOIN_TOKEN)
#   --host <name>    this machine's node name, the one the token was minted for ($env:ORG_JOIN_HOST)
#   --hq-root <p>    where the HQ folder goes (default: %USERPROFILE%\MoonieXHQ)
#   --hub <url>      the hub, https://<hub>. Default: the hub this script was fetched from
#   --dry-run        print every step, change nothing, contact nothing
#
# The nine steps, in order (same as join.sh). Each is safe to repeat.
#   1 check the arguments             6 wait for the hub to seal this node's identity to its key
#   2 install what is missing         7 clone Agents-Core over the deploy key, build the venv
#   3 make the node's keys            8 open the sealed identity, save it, write node.yaml
#   4 accept: hand the hub the token  9 probe
#   5 join the tailnet
#
# No secret is typed, written to disk by this script, or put on the command line of a process
# that lives longer than a moment. The node's identity is age-decrypted and handed to
# infisical_setup.py by ONE python process over pipes; PowerShell never holds the plaintext.

# Continue, not Stop: Windows PowerShell 5.1 turns a native program's stderr into a terminating
# error under Stop (age-keygen prints its public key there). Cmdlets that matter say
# -ErrorAction Stop themselves, and every native call checks $LASTEXITCODE.
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$script:Total = 9
$script:HubDefault = '@@ORG_JOIN_HUB@@'
$script:DryRun = $false
$script:PollS = 15
$script:PollMaxS = 900
$script:GhRepoSsh = 'git@github.com:PASAKON/Agents-Core.git'
$script:Py = ''
$script:PyPre = @()
$script:AgePub = ''
$script:DeployPub = ''
$script:TsKey = ''
$script:Cipher = ''

function Say($msg) { Write-Host ('    ' + $msg) }
function Step($n, $msg) { Write-Host ''; Write-Host ('[{0}/{1}] {2}' -f $n, $script:Total, $msg) }
function Die($msg) { throw ('join: ' + $msg) }

function Test-Have($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Update-PathFromRegistry {
    $m = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $u = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = $m + ';' + $u
}

# ---------------------------------------------------------------- 1: arguments

function Read-Args($argList) {
    $o = @{ Token = ''; Host = ''; HqRoot = ''; Hub = ''; DryRun = $false }
    $i = 0
    while ($i -lt $argList.Count) {
        $a = [string]$argList[$i]
        $name = $a
        $val = $null
        if ($a -match '^(--?[A-Za-z-]+)=(.*)$') { $name = $Matches[1]; $val = $Matches[2] }
        $key = $name.TrimStart('-').ToLower()
        if ($key -eq 'dry-run' -or $key -eq 'dryrun') {
            $o.DryRun = $true
        } elseif (@('token', 'host', 'hq-root', 'hqroot', 'hub') -contains $key) {
            if ($null -eq $val) {
                if ($i + 1 -ge $argList.Count) { Die ('--' + $key + ' needs a value') }
                $i++
                $val = [string]$argList[$i]
            }
            if ($key -eq 'token') { $o.Token = $val }
            elseif ($key -eq 'host') { $o.Host = $val }
            elseif ($key -eq 'hub') { $o.Hub = $val }
            else { $o.HqRoot = $val }
        } else {
            Die ('unknown argument starting ' + $name.Substring(0, [Math]::Min(6, $name.Length)) + ' (see the header of this script)')
        }
        $i++
    }
    return $o
}

function Initialize-Args($o) {
    $script:DryRun = [bool]$o.DryRun
    $script:Token = $o.Token
    if ((-not $script:Token) -and $env:ORG_JOIN_TOKEN) { $script:Token = $env:ORG_JOIN_TOKEN }
    Remove-Item Env:ORG_JOIN_TOKEN -ErrorAction SilentlyContinue   # do not hand it to every child process
    $script:HostName = $o.Host
    if ((-not $script:HostName) -and $env:ORG_JOIN_HOST) { $script:HostName = $env:ORG_JOIN_HOST }
    $script:HqRoot = $o.HqRoot
    if ((-not $script:HqRoot) -and $env:ORG_JOIN_HQ_ROOT) { $script:HqRoot = $env:ORG_JOIN_HQ_ROOT }
    $script:Hub = $o.Hub
    if ((-not $script:Hub) -and $env:ORG_JOIN_HUB) { $script:Hub = $env:ORG_JOIN_HUB }

    if (-not $script:Token) { Die 'no token: pass --token <t> or set $env:ORG_JOIN_TOKEN' }
    if ($script:Token -cnotmatch '^hqj_[A-Za-z0-9_-]{43}$') { Die 'the token is not in the expected shape (hqj_ and 43 more characters); copy it again' }
    if (-not $script:HostName) { Die 'no --host <name>' }
    if ($script:HostName -cnotmatch '^[a-z][a-z0-9-]{1,30}[a-z0-9]$') { Die "--host must be 3-32 characters: a-z, 0-9, '-', starting with a letter, not ending in '-'" }
    if (-not $script:HqRoot) { $script:HqRoot = Join-Path $env:USERPROFILE 'MoonieXHQ' }
    if ($script:HqRoot -notmatch '^[A-Za-z]:[\\/].+') { Die '--hq-root must be an absolute path such as C:\Users\you\MoonieXHQ' }
    $script:HqRoot = $script:HqRoot.TrimEnd('\', '/')
    if (-not $script:Hub) { $script:Hub = $script:HubDefault }
    if ((-not $script:Hub) -or $script:Hub.StartsWith('@@')) { Die 'no hub URL: this copy was not fetched from the hub. Pass --hub https://<hub>' }
    $h = $script:Hub.TrimEnd('/')
    if ($h.EndsWith('/org-join')) { $h = $h.Substring(0, $h.Length - 9) }
    $script:Hub = $h + '/org-join'
    if ($script:Hub -notmatch '^https?://[A-Za-z0-9.-]+(:[0-9]+)?/org-join$') { Die '--hub must look like https://<hub>' }

    $script:ConfDir = Join-Path $env:USERPROFILE '.config\mooniex'
    $script:SshDir = Join-Path $env:USERPROFILE '.ssh'
    $script:AgeId = Join-Path $script:ConfDir 'age-identity.txt'
    $script:DeployKey = Join-Path $script:ConfDir 'deploy_key'
    $script:DispatchKey = Join-Path $script:SshDir 'org_dispatch'   # the path lib/mesh.py reads
    $script:Core = Join-Path (Join-Path $script:HqRoot 'Agents') 'Core'
}

function Show-Banner {
    Step 1 'check the arguments'
    Say ('host ' + $script:HostName + ' (windows), hub ' + $script:Hub)
    Say ('HQ root ' + $script:HqRoot + '  (checkout: ' + $script:Core + ')')
    Say ('keys go under ' + $script:ConfDir + ' (age identity, deploy key) and ' + $script:SshDir + ' (dispatch key)')
    Say 'ELEVATION NEEDED for three steps: installing packages (2), tailscale up (5), saving the'
    Say "node's identity under C:\ProgramData\Infisical (8)."
    if (Test-Admin) {
        Say 'This window is elevated: fine.'
    } elseif ($script:DryRun) {
        Say 'WARNING: this window is NOT elevated; a real run would stop here. Use "Run as administrator".'
    } else {
        Die 'this window is not elevated. Close it, open PowerShell with "Run as administrator", and run the same command again'
    }
    if ($script:DryRun) { Say 'DRY RUN: every step below is printed, nothing is changed, nothing is contacted' }
}

# ---------------------------------------------------------------- 2: install

function Find-Python {
    foreach ($c in @('python', 'py')) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if ($cmd.Source -like '*\WindowsApps\*') { continue }   # the Store stub prints nothing and exits 9009
        $pre = @()
        if ($c -eq 'py') { $pre = @('-3') }
        $out = & $cmd.Source @pre -c 'import sys; print(1 if sys.version_info >= (3, 11) else 0)' 2>$null
        if ($LASTEXITCODE -eq 0 -and ([string]$out).Trim() -eq '1') {
            $script:Py = $cmd.Source
            $script:PyPre = $pre
            return $true
        }
    }
    return $false
}

function Get-NodeMajor {
    if (-not (Test-Have 'node')) { return 0 }
    $v = [string](& node --version 2>$null)
    if ($v -match '^v(\d+)\.') { return [int]$Matches[1] }
    return 0
}

function Install-Winget($id, $what) {
    Say ('$ winget install -e --id ' + $id + '   (' + $what + ')')
    if ($script:DryRun) { return }
    & winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { Die ('winget install ' + $id + ' failed (exit ' + $LASTEXITCODE + ')') }
    Update-PathFromRegistry
}

function Install-Missing {
    Step 2 'install what is missing (git, python 3.11+, node 22, age, tailscale, claude)'
    if (-not (Test-Have 'winget')) {
        if ($script:DryRun) { Say 'WARNING: winget is not installed; a real run would stop here' }
        else { Die 'winget is not installed: install "App Installer" from the Microsoft Store, then run the same command again' }
    }
    Update-PathFromRegistry
    if (Test-Have 'git') { Say 'git: present' } else { Install-Winget 'Git.Git' 'git' }
    if (Find-Python) {
        Say ('python: present (' + $script:Py + ')')
    } else {
        Install-Winget 'Python.Python.3.12' 'python 3.12'
        if ((-not $script:DryRun) -and (-not (Find-Python))) { Die 'python 3.11 or newer is not on PATH after the install; open a new elevated window and run the same command again' }
    }
    if ((Get-NodeMajor) -ge 22) {
        Say ('node ' + (& node --version) + ': present')
    } else {
        Install-Winget 'OpenJS.NodeJS.LTS' 'node, current LTS'
        if ((-not $script:DryRun) -and ((Get-NodeMajor) -lt 22)) { Die 'node 22 or newer is not on PATH after the install; open a new elevated window and run the same command again' }
    }
    if ((Test-Have 'age') -and (Test-Have 'age-keygen')) { Say 'age: present' } else { Install-Winget 'FiloSottile.age' 'age' }
    if (Test-Have 'tailscale') { Say 'tailscale: present' } else { Install-Winget 'Tailscale.Tailscale' 'tailscale' }
    if (Test-Have 'claude') {
        Say 'claude: present'
    } else {
        Say '$ npm install -g @anthropic-ai/claude-code'
        if (-not $script:DryRun) {
            & npm install -g '@anthropic-ai/claude-code'
            if ($LASTEXITCODE -ne 0) { Die 'npm install -g @anthropic-ai/claude-code failed' }
        }
    }
    if ((-not $script:Py) -and $script:DryRun) { $script:Py = 'python'; $script:PyPre = @() }
}

function Find-SshKeygen {
    $c = Get-Command 'ssh-keygen' -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in @("$env:ProgramFiles\Git\usr\bin\ssh-keygen.exe", "$env:SystemRoot\System32\OpenSSH\ssh-keygen.exe")) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    Die 'ssh-keygen not found: turn on "OpenSSH Client" under Optional features, or reinstall Git for Windows, then run the same command again'
}

# ---------------------------------------------------------------- 3: keys

function Set-PrivateAcl($path) {
    # The Windows form of 0600: only this user. icacls prints a summary line; discard it.
    $null = & icacls $path /inheritance:r /grant:r ($env:USERNAME + ':F') 2>&1
    if ($LASTEXITCODE -ne 0) { Die ('could not restrict access to ' + $path) }
}

function New-Keys {
    Step 3 "make the node's keys (kept if they already exist), private to this user"
    Say ('age identity    ' + $script:AgeId)
    Say ('deploy key      ' + $script:DeployKey + ' (ssh ed25519, read-only on GitHub once the hub registers it)')
    Say ('dispatch key    ' + $script:DispatchKey + ' (ssh ed25519, what lib/mesh.py uses to call other nodes)')
    if ($script:DryRun) {
        Say 'would create whichever of the three is missing; only the public halves are ever shown'
        $script:AgePub = 'age1<the public half of the identity>'
        return
    }
    New-Item -ItemType Directory -Force -Path $script:ConfDir, $script:SshDir -ErrorAction Stop | Out-Null
    if (-not (Test-Path -LiteralPath $script:AgeId)) {
        $null = & age-keygen -o $script:AgeId 2>&1
        if ($LASTEXITCODE -ne 0) { Die 'age-keygen failed' }
    }
    Set-PrivateAcl $script:AgeId
    $pub = & age-keygen -y $script:AgeId 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $pub) { Die ('could not read the age recipient from ' + $script:AgeId) }
    $script:AgePub = ([string]$pub).Trim()
    $kg = Find-SshKeygen
    $specs = @(
        @($script:DeployKey, ('org-node:' + $script:HostName)),
        @($script:DispatchKey, ('org_dispatch-' + $script:HostName))
    )
    foreach ($spec in $specs) {
        if (-not (Test-Path -LiteralPath $spec[0])) {
            # '""' is the empty passphrase: Windows PowerShell 5.1 drops a bare empty argument.
            $null = & $kg -q -t ed25519 -N '""' -C $spec[1] -f $spec[0] 2>&1
            if ($LASTEXITCODE -ne 0) { Die ('ssh-keygen failed for ' + $spec[0]) }
        }
        Set-PrivateAcl $spec[0]
    }
    $script:DeployPub = (Get-Content -LiteralPath ($script:DeployKey + '.pub') -Raw -ErrorAction Stop).Trim()
    Say 'keys ready'
}

# ---------------------------------------------------------------- hub calls

# Send-Hub <route> <hashtable>. Returns @{ Code; Body } and does not throw on an HTTP error
# (Code 0 = the hub was not reachable). The token travels in the request body, under TLS,
# never in the URL or a header.
function Send-Hub($route, $obj) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $json = $obj | ConvertTo-Json -Compress
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Method Post -Uri ($script:Hub + '/' + $route) `
            -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($json)) `
            -TimeoutSec 30 -ErrorAction Stop
        return @{ Code = [int]$r.StatusCode; Body = [string]$r.Content }
    } catch [System.Net.WebException] {
        $resp = $_.Exception.Response
        if ($null -eq $resp) { return @{ Code = 0; Body = '' } }
        $text = ''
        try { $text = (New-Object IO.StreamReader($resp.GetResponseStream())).ReadToEnd() } catch { $text = '' }
        return @{ Code = [int]$resp.StatusCode; Body = $text }
    } catch {
        return @{ Code = 0; Body = '' }
    }
}

function Get-JsonField($body, $name) {
    try {
        $v = ($body | ConvertFrom-Json).$name
        if ($v -is [string]) { return $v }
    } catch { }
    return ''
}

function Send-Sealed { return (Send-Hub 'sealed' @{ host = $script:HostName; token = $script:Token }) }

# ---------------------------------------------------------------- 4: accept

function Send-Accept {
    Step 4 "accept: give the hub the token and this node's public keys"
    Say ('POST ' + $script:Hub + '/accept  (host, os, hq_root, age recipient, deploy public key; the token is in the body)')
    if ($script:DryRun) {
        Say "a used token is refused; step 6's answer then tells 'already joined' from 'wrong token'"
        return
    }
    $r = Send-Hub 'accept' @{ token = $script:Token; host = $script:HostName; os = 'windows'; hq_root = $script:HqRoot; pubkey = $script:AgePub; deploy_pubkey = $script:DeployPub }
    if ($r.Code -eq 200) {
        Say ('accepted: the hub now lists ' + $script:HostName + ' as pending_identity')
        $script:TsKey = Get-JsonField $r.Body 'tailscale_authkey'
    } elseif ($r.Code -eq 400) {
        Die ('the hub refused the request: ' + (Get-JsonField $r.Body 'message'))
    } elseif ($r.Code -eq 403) {
        # Used, expired, wrong host or unknown all look the same. The sealed call tells
        # "this token already joined this host" (200/202) from "never valid" (403).
        $s = Send-Sealed
        if ($s.Code -eq 200 -or $s.Code -eq 202) { Say 'already joined with this token: continuing with the steps that are left' }
        else { Die 'the hub refused this token: it is unknown, already used for another machine, expired (15 min), or minted for a different host name. Ask for a new one.' }
    } elseif ($r.Code -eq 409) {
        Die ('the hub already has a node called ' + $script:HostName + '. Pick another name, or leave the old one first')
    } elseif ($r.Code -eq 429) {
        Die 'the hub is rate limiting this address: wait a minute and run the same command again'
    } elseif ($r.Code -eq 0) {
        Die ('could not reach the hub at ' + $script:Hub)
    } else {
        Die ('unexpected answer from the hub: HTTP ' + $r.Code)
    }
}

# ---------------------------------------------------------------- 5: tailnet

function Test-OnTailnet {
    if (-not (Test-Have 'tailscale')) { return $false }
    $null = & tailscale ip -4 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Join-Tailnet {
    Step 5 'join the tailnet (tag:org-node), or confirm this machine is already on it'
    if ($script:DryRun) {
        Say ('if the hub sent a pre-auth key: tailscale up --auth-key <key from the hub> --hostname ' + $script:HostName + ' --advertise-tags=tag:org-node')
        Say 'else the machine must already be on the tailnet; if it is not, this step stops with instructions'
        return
    }
    if (Test-OnTailnet) {
        Say ('already on the tailnet as ' + ((& tailscale ip -4) | Select-Object -First 1))
    } elseif ($script:TsKey) {
        # Single use and short lived; `up` returns in seconds. It has to be an argument.
        & tailscale up --auth-key $script:TsKey --hostname $script:HostName --advertise-tags=tag:org-node
        if ($LASTEXITCODE -ne 0) { Die ('tailscale up failed. The key was single use: join the tailnet by hand (tailscale up --hostname ' + $script:HostName + '), then run this command again') }
        Say 'joined the tailnet'
    } else {
        Die ('this machine is not on the tailnet and the hub sent no Tailscale key (it has none configured yet). Join it yourself with:  tailscale up --hostname ' + $script:HostName + '  and run this command again')
    }
    $script:TsKey = ''
}

# ---------------------------------------------------------------- 6: wait for the sealed identity

function Wait-Sealed {
    Step 6 ("wait for the hub to seal this node's identity (polls every " + $script:PollS + ' s, up to ' + [int]($script:PollMaxS / 60) + ' min)')
    Say ('POST ' + $script:Hub + '/sealed  -> pending until the Mac provisions it, then the age ciphertext')
    Say ('the ciphertext is held in memory only; only the identity in ' + $script:AgeId + ' can open it')
    if ($script:DryRun) { return }
    $waited = 0
    while ($true) {
        $r = Send-Sealed
        if ($r.Code -eq 200) {
            $script:Cipher = Get-JsonField $r.Body 'ciphertext'
            if (-not $script:Cipher) { Die 'the hub said ready but sent no ciphertext' }
            Say 'sealed identity received'
            return
        } elseif ($r.Code -eq 202) {
            Say ('pending (' + $waited + ' s)')
        } elseif ($r.Code -eq 403) {
            Die 'the hub will not release the sealed identity for this token (expired after 24 h, or the node left). Ask for a new token'
        } elseif ($r.Code -eq 429) {
            Say 'rate limited, waiting'
        } elseif ($r.Code -eq 0) {
            Say 'hub not reachable, retrying'
        } else {
            Say ('hub answered HTTP ' + $r.Code + ', retrying')
        }
        if ($waited -ge $script:PollMaxS) { Die ('gave up after ' + [int]($script:PollMaxS / 60) + ' min: the hub did not provision ' + $script:HostName + '. Run the same command again to keep waiting') }
        Start-Sleep -Seconds $script:PollS
        $waited += $script:PollS
    }
}

# ---------------------------------------------------------------- 7: clone + venv

function Get-GitSshCommand {
    $k = $script:DeployKey -replace '\\', '/'
    $kh = ($script:ConfDir -replace '\\', '/') + '/known_hosts'
    return ('ssh -i "' + $k + '" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="' + $kh + '"')
}

function Copy-Core {
    Step 7 'clone Agents-Core over the deploy key, build the venv'
    Say ($script:GhRepoSsh + ' -> ' + $script:Core + '  (GIT_SSH_COMMAND: the deploy key only, nothing from ~\.ssh)')
    Say ('then: python -m venv ' + $script:Core + '\.venv and pip install -r requirements.txt')
    if ($script:DryRun) { return }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $script:Core) -ErrorAction Stop | Out-Null
    $env:GIT_SSH_COMMAND = Get-GitSshCommand
    try {
        if (Test-Path -LiteralPath (Join-Path $script:Core '.git')) {
            Say 'already cloned: updating'
            & git -C $script:Core pull --ff-only
            if ($LASTEXITCODE -ne 0) { Die ('git pull failed in ' + $script:Core) }
        } else {
            & git clone $script:GhRepoSsh $script:Core
            if ($LASTEXITCODE -ne 0) { Die "git clone failed. If it says 'Permission denied (publickey)', the hub registered no deploy key for this node" }
        }
    } finally {
        Remove-Item Env:GIT_SSH_COMMAND -ErrorAction SilentlyContinue
    }
    $venvPy = Join-Path $script:Core '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPy)) {
        & $script:Py @($script:PyPre) -m venv (Join-Path $script:Core '.venv')
        if ($LASTEXITCODE -ne 0) { Die 'python -m venv failed' }
    }
    & $venvPy -m pip install -q -r (Join-Path $script:Core 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { Die 'pip install -r requirements.txt failed' }
}

# ---------------------------------------------------------------- 8: identity + node.yaml

# One python process does age -d, the JSON parse and the hand-off to `save`, all over pipes.
# PowerShell pipelines re-encode and add CRLF, which would corrupt a secret, so none is used.
# The ciphertext (harmless by design: only this node's age key opens it) comes in an env var.
$script:SaveHelper = @'
import json, os, subprocess, sys
age_id, setup, host, py = sys.argv[1:5]
cipher = os.environ.pop("ORG_JOIN_CIPHER", "")
if not cipher:
    sys.exit("no ciphertext")
dec = subprocess.run(["age", "-d", "-i", age_id], input=cipher.encode("ascii"), capture_output=True)
if dec.returncode != 0:
    sys.exit("age could not open the sealed identity")
try:
    d = json.loads(dec.stdout)
    pair = (d["client_id"] + "\n" + d["client_secret"] + "\n").encode("utf-8")
except Exception:
    sys.exit("the sealed identity is not in the expected shape")
save = subprocess.run([py, setup, "save", host, "--stdin"], input=pair, capture_output=True)
sys.stdout.write(save.stdout.decode("utf-8", "replace"))
if save.returncode != 0:
    sys.stderr.write(save.stderr.decode("utf-8", "replace")[:500])
    sys.exit(save.returncode)
'@

function ConvertTo-YamlScalar($s) { return ("'" + ($s -replace "'", "''") + "'") }

function Write-NodeYaml {
    $f = Join-Path $script:ConfDir 'node.yaml'
    if (Test-Path -LiteralPath $f) {
        $have = Get-Content -LiteralPath $f -Raw -ErrorAction Stop
        if ($have -notmatch ("(?m)^host: '?" + [regex]::Escape($script:HostName) + "'?\s*$")) { Die ($f + ' already names another host; remove it if this machine really is ' + $script:HostName) }
    }
    $lines = @(
        ('host: ' + (ConvertTo-YamlScalar $script:HostName)),
        'os: windows',
        ('hq_root: ' + (ConvertTo-YamlScalar $script:HqRoot))
    )
    # No-BOM UTF-8: a BOM breaks the YAML loader.
    [IO.File]::WriteAllLines(($f + '.tmp'), $lines, (New-Object Text.UTF8Encoding($false)))
    Move-Item -Force -LiteralPath ($f + '.tmp') -Destination $f -ErrorAction Stop
}

function Save-Identity {
    Step 8 'open the sealed identity, save it under ProgramData\Infisical, write node.yaml'
    Say ('age -d -i ' + $script:AgeId + ' | (json: client_id, client_secret) | python tools\infisical_setup.py save ' + $script:HostName + ' --stdin')
    Say 'the plaintext only ever flows through pipes inside one python process'
    Say ('node.yaml: host, os, hq_root -> ' + $script:ConfDir + '\node.yaml (where lib/config.py reads it)')
    if ($script:DryRun) { return }
    $venvPy = Join-Path $script:Core '.venv\Scripts\python.exe'
    $env:ORG_JOIN_CIPHER = $script:Cipher
    try {
        & $venvPy -c $script:SaveHelper $script:AgeId (Join-Path $script:Core 'tools\infisical_setup.py') $script:HostName $venvPy
        if ($LASTEXITCODE -ne 0) { Die "could not save the node's identity (the decrypt, the parse or the Infisical login failed; nothing was stored)" }
    } finally {
        Remove-Item Env:ORG_JOIN_CIPHER -ErrorAction SilentlyContinue
    }
    $script:Cipher = ''
    Write-NodeYaml
}

# ---------------------------------------------------------------- 9: probe

function Invoke-Probe {
    Step 9 'probe: measure this node through its own identity'
    Say ('python tools\infisical_setup.py run Agents-Core prod --as ' + $script:HostName + ' -- .venv\Scripts\python.exe -m tools.node_dispatch probe')
    if ($script:DryRun) { return }
    $venvPy = Join-Path $script:Core '.venv\Scripts\python.exe'
    Push-Location $script:Core
    try {
        $env:ORG_HOST = $script:HostName
        $out = & $venvPy (Join-Path $script:Core 'tools\infisical_setup.py') run Agents-Core prod --as $script:HostName -- $venvPy -m tools.node_dispatch probe 2>$null
    } finally {
        Remove-Item Env:ORG_HOST -ErrorAction SilentlyContinue
        Pop-Location
    }
    $last = @($out | Where-Object { ([string]$_).Trim() }) | Select-Object -Last 1
    try { $d = [string]$last | ConvertFrom-Json } catch { Die 'joined and identity saved, but the probe gave no JSON answer' }
    if ($d.ok) {
        Say ('probe: ok host=' + $d.result.host + ' os=' + $d.result.os + ' free_gb=' + $d.result.free_gb)
    } else {
        $e = [string]$d.error
        Die ('joined and identity saved, but the probe FAILED: ' + $e.Substring(0, [Math]::Min(300, $e.Length)))
    }
}

# ---------------------------------------------------------------- main

function Join-OrgNode($argList) {
    $o = Read-Args $argList
    Initialize-Args $o
    Show-Banner
    Install-Missing
    New-Keys
    Send-Accept
    Join-Tailnet
    Wait-Sealed
    Copy-Core
    Save-Identity
    Invoke-Probe
    Write-Host ''
    if ($script:DryRun) { Write-Host 'join: dry run finished. Nothing was changed.'; return }
    Write-Host ('join: ' + $script:HostName + ' is a node.')
    Say ('dispatch public key (for the ssh mesh, W2.8): ' + $script:DispatchKey + '.pub')
    Say 'claude: nothing to sign in to here. The node reads CLAUDE_CODE_OAUTH_TOKEN at run time through'
    Say ('  infisical_setup.py run Agents-Core prod --as ' + $script:HostName + ' -- <command>   (once the CEO has put it there)')
}

try {
    Join-OrgNode $args
} catch {
    $m = [string]$_.Exception.Message
    if (-not $m.StartsWith('join: ')) { $m = 'join: ' + $m }
    Write-Host ''
    Write-Host $m -ForegroundColor Red
    # Under `iex` an exit would close the operator's window, so only a real script file exits.
    if ($MyInvocation.MyCommand.CommandType -eq 'ExternalScript') { exit 1 }
}
