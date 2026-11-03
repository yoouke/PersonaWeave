# Creates the requested public repository and uploads only tracked source files.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Run-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE)." }
}
foreach ($program in @('git', 'gh')) {
    if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
        throw "$program is required. Install Git for Windows and GitHub CLI from their official sources, then run again."
    }
}
& gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Run-Checked 'gh' @('auth', 'login', '--hostname', 'github.com', '--git-protocol', 'https', '--web')
}
$login = & gh api user --jq .login
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify GitHub account.' }
if ($login.Trim() -ne 'yoouke') { throw "Authenticated account is $login; expected yoouke. Switch your GitHub CLI account before publishing." }
$repo = 'yoouke/1'
if (-not (Test-Path .git)) {
    Run-Checked 'git' @('init', '-b', 'main')
}
# Add an explicit allowlist. Never include state, API keys or chat histories.
Run-Checked 'git' @('add', '.github', '.gitignore', 'LICENSE', 'README.md', 'docs', 'entry.py', 'personaweave', 'pyproject.toml', 'tests', 'packaging', 'Publish-to-GitHub.cmd')
& git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    Run-Checked 'git' @('-c', 'user.name=PersonaWeave contributors', '-c', 'user.email=contributors@personaweave.local', 'commit', '-m', 'Publish PersonaWeave desktop preview')
}
& gh repo view $repo --json name 2>$null
if ($LASTEXITCODE -ne 0) {
    Run-Checked 'gh' @('repo', 'create', $repo, '--public', '--description', 'PersonaWeave: local-first DIY AI persona desktop host with DSH and QQ')
}
$origin = & git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    Run-Checked 'git' @('remote', 'add', 'origin', 'https://github.com/yoouke/1.git')
} elseif ($origin -notmatch '^https://github.com/yoouke/1(?:\.git)?$' -and $origin -ne 'git@github.com:yoouke/1.git') {
    throw 'Existing remote points to a different repository. No changes pushed.'
}
Run-Checked 'gh' @('auth', 'setup-git')
# Never force push or replace unrelated remote history.
Run-Checked 'git' @('push', '-u', 'origin', 'HEAD:main')
Write-Host 'Source uploaded. GitHub Actions will build the Windows application.'
Run-Checked 'gh' @('run', 'list', '--repo', $repo, '--workflow', 'windows.yml', '--limit', '1')
Write-Host 'Open the repository Actions page to download PersonaWeave-Windows-x64 once the run succeeds.'
