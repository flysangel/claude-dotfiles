# E2E driver for Windows. It uninstalls Git from the machine, so it only runs on a CI runner.
# Contract: specs/004-ci-e2e-tests/contracts/e2e-driver.md
param(
    [string]$BareRepo = '',
    [string]$SetupUrl = ''
)

$ErrorActionPreference = 'Continue'
$environment = if ($SetupUrl) { 'windows-public' } else { 'windows' }
$email = '12345+e2e@users.noreply.github.com'
$clone = Join-Path $env:USERPROFILE 'claude-dotfiles'
$claudeDir = Join-Path $env:USERPROFILE '.claude'
$recordFile = Join-Path $env:USERPROFILE '.config\claude-dotfiles\setup.json'
$localBin = Join-Path $env:USERPROFILE '.local\bin'
$setupScript = Join-Path $PSScriptRoot '..\..\tools\setup.ps1'
$script:broken = ''
$script:failed = 0
$script:output = ''
$retryable = 'cannot download|winget failed'

function Report($stage, $status, $detail) {
    Write-Output "E2E $environment $stage $status $detail"
    if ($status -eq 'FAIL') {
        $script:failed = 1
        $script:broken = $stage
    }
}

function Test-Tool($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Invoke-Setup([string[]]$options) {
    $source = if ($SetupUrl) { "(irm '$SetupUrl')" } else { "(Get-Content -Raw -LiteralPath '$setupScript')" }
    $command = "& ([scriptblock]::Create($source)) $($options -join ' ')"
    $lines = & powershell -NoProfile -ExecutionPolicy Bypass -Command $command 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $script:output = $lines -join "`n"
    $lines | ForEach-Object { Write-Output $_ }
    return $code
}

function Update-DriverPath {
    $env:PATH = (@($env:PATH, $localBin, (Join-Path $env:ProgramFiles 'Git\cmd')) -join ';')
}

function Get-ManagedHash {
    Get-ChildItem -LiteralPath $claudeDir -Recurse -File -Force |
        Where-Object { $_.FullName -match '\\\.claude\\(CLAUDE\.md$|rules\\|skills\\|\.dotfiles\\)' } |
        Sort-Object FullName |
        ForEach-Object { "$($_.FullName) $((Get-FileHash -LiteralPath $_.FullName).Hash)" }
}

function Get-CloneHash {
    Get-ChildItem -LiteralPath $clone -Recurse -File -Force |
        Where-Object { $_.FullName -notmatch '\\\.git\\|__pycache__' } |
        Sort-Object FullName |
        ForEach-Object { "$($_.FullName) $((Get-FileHash -LiteralPath $_.FullName).Hash)" }
}

function Enable-Winget {
    if (Test-Tool 'winget') { return $true }
    try {
        Install-PackageProvider -Name NuGet -Force -Scope AllUsers | Out-Null
        Install-Module -Name Microsoft.WinGet.Client -Force -Scope AllUsers -Repository PSGallery
        Import-Module Microsoft.WinGet.Client
        Repair-WinGetPackageManager -Latest -Force -AllUsers | Out-Null
    } catch {
        Write-Output "winget could not be installed: $_"
    }
    $env:PATH = "$env:PATH;$env:LOCALAPPDATA\Microsoft\WindowsApps"
    return (Test-Tool 'winget')
}

function Remove-ExistingTools($removeGit) {
    if ($removeGit) {
        $uninstaller = Join-Path $env:ProgramFiles 'Git\unins000.exe'
        if (Test-Path -LiteralPath $uninstaller) {
            Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT', '/NORESTART' -Wait
        }
    }
    $names = if ($removeGit) { 'git.exe', 'uv.exe', 'claude.exe' } else { 'uv.exe', 'claude.exe' }
    $kept = $env:PATH -split ';' | Where-Object {
        $directory = $_
        $directory -and -not ($names | Where-Object { Test-Path -LiteralPath (Join-Path $directory $_) })
    }
    $env:PATH = $kept -join ';'
}

function Stage-Setup {
    foreach ($attempt in 1, 2) {
        if ((Invoke-Setup @()) -eq 0) { break }
        $failure = ($script:output -split "`n" | Where-Object { $_ -match $retryable } | Select-Object -First 1)
        if (-not $failure) {
            Report 'setup' 'FAIL' 'the setup failed, see the output above'
            return
        }
        if ($attempt -eq 2) {
            Report 'setup' 'FAIL' "download failed after a retry: $failure"
            return
        }
    }
    Update-DriverPath
    foreach ($tool in 'uv', 'git', 'claude') {
        if (-not (Test-Tool $tool)) {
            Report 'setup' 'FAIL' "$tool is not available after the setup"
            return
        }
    }
    $record = Get-Content -Raw -LiteralPath $recordFile
    $expected = if ($script:wingetAvailable) { 'uv', 'git', 'claude' } else { 'uv', 'claude' }
    foreach ($tool in $expected) {
        if ($record -notmatch """$tool""") {
            Report 'setup' 'FAIL' "$tool was already there, so this run did not install it"
            return
        }
    }
    Push-Location -LiteralPath $clone
    $state = (& uv run tools/dotfiles.py status 2>$null | Select-Object -First 1)
    Pop-Location
    if ($state -ne 'clean') {
        Report 'setup' 'FAIL' "deployment status is $state"
        return
    }
    if ($script:wingetAvailable) {
        Report 'setup-git-install' 'PASS' 'winget installed git'
    }
    Report 'setup' 'PASS' 'tools available and deployment clean'
}

function Stage-Rerun {
    $before = (Get-ManagedHash) + (Get-CloneHash) -join "`n"
    if ((Invoke-Setup @()) -ne 0) {
        Report 'rerun' 'FAIL' 'the second run failed'
        return
    }
    $after = (Get-ManagedHash) + (Get-CloneHash) -join "`n"
    if ($before -ne $after) {
        Report 'rerun' 'FAIL' 'the second run changed files'
        return
    }
    Report 'rerun' 'PASS' 'nothing changed'
}

function Stage-Dev {
    if ((Invoke-Setup @('-Dev', '-Email', "'$email'")) -ne 0) {
        Report 'dev' 'FAIL' 'dev setup failed'
        return
    }
    Push-Location -LiteralPath $clone
    $state = (& uv run tools/repo_guard.py --status 2>$null | Select-Object -First 1)
    Pop-Location
    if ($state -ne 'enabled') {
        Report 'dev' 'FAIL' "commit guard is $state"
        return
    }
    & git config --global --get user.email | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Report 'dev' 'FAIL' 'the global email was changed'
        return
    }
    & git -C $clone config user.name 'E2E Tester'
    Add-Content -LiteralPath (Join-Path $clone 'README.md') -Value '# e2e'
    & git -C $clone add README.md
    & git -C $clone commit -q -m 'test: e2e commit'
    if ($LASTEXITCODE -ne 0) {
        Report 'dev' 'FAIL' 'a real commit failed'
        return
    }
    Report 'dev' 'PASS' 'guard enabled and a real commit worked'
}

function Stage-Remove {
    & uv run (Join-Path $clone 'tools\machine_setup.py') remove
    if ($LASTEXITCODE -ne 0) {
        Report 'remove' 'FAIL' 'remove failed'
        return
    }
    $main = (Get-Content -Raw -LiteralPath (Join-Path $claudeDir 'CLAUDE.md')).Trim()
    $rule = (Get-Content -Raw -LiteralPath (Join-Path $claudeDir 'rules\machine.md')).Trim()
    if ($main -ne 'mine' -or $rule -ne 'local') {
        Report 'remove' 'FAIL' 'the original files did not come back'
        return
    }
    if (Test-Path -LiteralPath (Join-Path $clone '.git\hooks\pre-commit')) {
        Report 'remove' 'FAIL' 'the hook is still installed'
        return
    }
    if (Test-Path -LiteralPath $recordFile) {
        Report 'remove' 'FAIL' 'the setup record is still there'
        return
    }
    if (-not (Test-Path -LiteralPath $clone) -or -not (Test-Tool 'uv')) {
        Report 'remove' 'FAIL' 'the clone or the tools were removed'
        return
    }
    Report 'remove' 'PASS' 'original files back, tools and clone kept'
}

function Stage-Refuse {
    $plain = Join-Path $env:USERPROFILE 'not-this-repo'
    $marker = Join-Path $env:USERPROFILE 'refuse-marker'
    New-Item -ItemType Directory -Force -Path (Join-Path $plain 'tools') | Out-Null
    $program = "open(r'$marker', 'w').close()"
    Set-Content -LiteralPath (Join-Path $plain 'tools\machine_setup.py') -Value $program
    if ((Invoke-Setup @('-Dir', "'$plain'")) -eq 0) {
        Report 'refuse' 'FAIL' 'the setup accepted a directory that is not this repo'
        return
    }
    if (Test-Path -LiteralPath $marker) {
        Report 'refuse' 'FAIL' 'code inside the directory ran'
        return
    }
    Report 'refuse' 'PASS' 'stopped without running anything'
}

if ($BareRepo) { $env:CLAUDE_DOTFILES_REPO = $BareRepo }

Write-Output '::group::prepare'
$script:wingetAvailable = Enable-Winget
Remove-ExistingTools $script:wingetAvailable
Write-Output '::endgroup::'

if (-not $script:wingetAvailable) {
    Report 'setup-git-install' 'UNVERIFIED' 'no winget on this machine'
}
$visible = @('uv', 'claude') + $(if ($script:wingetAvailable) { @('git') } else { @() }) | Where-Object { Test-Tool $_ }
if ($visible) {
    Report 'setup' 'FAIL' "could not hide existing tools: $($visible -join ',')"
}

New-Item -ItemType Directory -Force -Path (Join-Path $claudeDir 'rules') | Out-Null
Set-Content -LiteralPath (Join-Path $claudeDir 'CLAUDE.md') -Value 'mine'
Set-Content -LiteralPath (Join-Path $claudeDir 'rules\machine.md') -Value 'local'

$stages = @{ setup = 'Stage-Setup'; rerun = 'Stage-Rerun'; dev = 'Stage-Dev'; remove = 'Stage-Remove'; refuse = 'Stage-Refuse' }
foreach ($stage in 'setup', 'rerun', 'dev', 'remove', 'refuse') {
    if ($script:broken) {
        Report $stage 'FAIL' 'previous stage failed'
        continue
    }
    Write-Output "::group::$stage"
    & $stages[$stage]
    Write-Output '::endgroup::'
}
exit $script:failed
