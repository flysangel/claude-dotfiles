# One-line setup for Windows: install missing tools, get the repo, then hand over to machine_setup.py.
# Contract: specs/003-license-oneline-setup/contracts/setup-cli.md
#
# This usually runs through iex inside the user's window, so failures use throw: leaving the session
# would close that window. Official installers run in a child process for the same reason. The file
# stays ASCII because Windows PowerShell 5.1 misreads UTF-8 without a BOM.
param(
    [string]$Dir = '',
    [switch]$Dev,
    [string]$Email = '',
    [switch]$Force
)

& {
    $ErrorActionPreference = 'Continue'
    $installed = New-Object System.Collections.ArrayList
    $separator = [IO.Path]::PathSeparator

    function Say($message) {
        Write-Host "==> $message"
    }

    function Fail($message) {
        $text = "setup failed: $message"
        if ($installed.Count -gt 0) {
            $text += " Tools installed in this run: $($installed -join ',')."
        }
        throw $text
    }

    function Test-Tool($name) {
        return [bool](Get-Command $name -ErrorAction SilentlyContinue)
    }

    function Assert-Version($tool, $need) {
        if (-not (Test-Tool $tool)) { return }
        $output = (& $tool --version 2>$null) -join ' '
        if ($output -notmatch '(\d+)\.(\d+)(\.(\d+))?') {
            Fail "version check: cannot read the version of $tool, $need or newer is required."
        }
        $have = [version]"$($Matches[1]).$($Matches[2]).$(if ($Matches[4]) { $Matches[4] } else { '0' })"
        if ($have -lt [version]$need) {
            Fail "version check: $tool $have is too old, $need or newer is required. Upgrade it and run this again."
        }
    }

    function Update-ToolPath {
        # Installers only change the path for shells opened later. Keep what this process already has.
        $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
        $user = [Environment]::GetEnvironmentVariable('Path', 'User')
        $env:PATH = (@($env:PATH, $machine, $user, $localBin) | Where-Object { $_ }) -join $separator
    }

    function Install-Git {
        $manual = 'install Git for Windows from https://git-scm.com/downloads/win and run this again'
        if (-not (Test-Tool 'winget')) {
            Fail "installing git: winget is not available, $manual."
        }
        Say 'Installing git (Windows may ask for permission)'
        & winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Fail "installing git: winget failed, $manual."
        }
        Update-ToolPath
        if (-not (Test-Tool 'git')) {
            Fail 'installing git: installed, but git is not on PATH. Open a new terminal and run this again.'
        }
        [void]$installed.Add('git')
    }

    function Install-Official($label, $tool, $url, $docs) {
        Say "Installing $label"
        $command = "`$ErrorActionPreference = 'Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm '$url' | iex"
        & powershell -NoProfile -ExecutionPolicy Bypass -Command $command
        if ($LASTEXITCODE -ne 0) {
            Fail "installing ${label}: the official installer failed or could not be downloaded. Check the network and run this again, or see $docs"
        }
        Update-ToolPath
        if (-not (Test-Tool $tool)) {
            Fail "installing ${label}: installed, but $tool is not on PATH. Open a new terminal and run this again."
        }
        [void]$installed.Add($tool)
    }

    function Get-NormalizedOrigin($url) {
        $url = $url.TrimEnd('/')
        if ($url.EndsWith('.git')) { $url = $url.Substring(0, $url.Length - 4) }
        $url = $url.TrimEnd('/')
        if ($url -match '^(https?|ssh)://') {
            return (($url -replace '^[A-Za-z]+://', '') -replace '^[^/@]*@', '').ToLowerInvariant()
        }
        if ($url -match '^[^/\\@]+@[^/\\:]+:') {
            return (($url -replace '^[^@]+@', '') -replace ':', '/').ToLowerInvariant()
        }
        return $url
    }

    function Confirm-Clone($path, $source) {
        # Nothing inside the directory may run until it is known to be this repo.
        $top = & git -C $path rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -ne 0) {
            Fail "getting the repo: $path exists and is not a git repo. Use -Dir to choose another location."
        }
        $here = (Resolve-Path -LiteralPath $path).ProviderPath -replace '\\', '/'
        if (($top -replace '\\', '/') -ne $here) {
            Fail "getting the repo: $path is inside another git repo. Use -Dir to choose another location."
        }
        $origin = & git -C $path remote get-url origin 2>$null
        if ($LASTEXITCODE -ne 0) {
            Fail "getting the repo: $path has no origin. Use -Dir to choose another location."
        }
        if ((Get-NormalizedOrigin $origin) -ne (Get-NormalizedOrigin $source)) {
            Fail "getting the repo: the origin of $path is not $source. Use -Dir to choose another location."
        }
    }

    if ($env:OS -ne 'Windows_NT') {
        Fail 'system check: tools/setup.ps1 supports Windows only. On Linux use tools/setup.sh; macOS is not supported.'
    }

    $source = if ($env:CLAUDE_DOTFILES_REPO) { $env:CLAUDE_DOTFILES_REPO } else { 'https://github.com/flysangel/claude-dotfiles.git' }
    $localBin = Join-Path (Join-Path $env:USERPROFILE '.local') 'bin'

    # Tools from an earlier run may be here even if this shell has not picked them up yet.
    $env:PATH = "$env:PATH$separator$localBin"

    Assert-Version 'git' '2.20.0'
    Assert-Version 'uv' '0.4.0'

    if (-not (Test-Tool 'git')) { Install-Git }
    if (-not (Test-Tool 'uv')) {
        Install-Official 'uv' 'uv' 'https://astral.sh/uv/install.ps1' 'https://docs.astral.sh/uv/getting-started/installation/'
    }
    if (-not (Test-Tool 'claude')) {
        Install-Official 'Claude Code' 'claude' 'https://claude.ai/install.ps1' 'https://code.claude.com/docs/en/setup'
    }

    $clone = if ($Dir) { $Dir } else { Join-Path $env:USERPROFILE 'claude-dotfiles' }
    if (-not [IO.Path]::IsPathRooted($clone)) {
        $clone = Join-Path (Get-Location).ProviderPath $clone
    }
    if (Test-Path -LiteralPath $clone) {
        Confirm-Clone $clone $source
    } else {
        Say "Cloning into $clone"
        $previousPrompt = $env:GIT_TERMINAL_PROMPT
        $env:GIT_TERMINAL_PROMPT = '0'
        & git clone --quiet $source $clone
        $cloned = $LASTEXITCODE
        $env:GIT_TERMINAL_PROMPT = $previousPrompt
        if ($cloned -ne 0) {
            Fail "getting the repo: cannot clone $source. If it is private, clone it yourself and run tools/setup.ps1 -Dir <clone>."
        }
    }

    $options = @()
    if ($Dev) { $options += '--dev' }
    if ($Email) { $options += @('--email', $Email) }
    if ($Force) { $options += '--force' }
    if ($installed.Count -gt 0) { $options += @('--installed', ($installed -join ',')) }

    Say "Running the setup in $clone"
    Push-Location -LiteralPath $clone
    try {
        & uv run (Join-Path (Join-Path $clone 'tools') 'machine_setup.py') install @options
        $result = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($result -ne 0) {
        throw "setup failed: see the message above (code $result)."
    }
}
