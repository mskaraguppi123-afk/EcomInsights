# EcomInsights - One-Click Git Repository Uploader
$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  EcomInsights - One-Click Git Repository Uploader      " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

# Detect Git
$gitCmd = "git"
if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    $fallbackGit = "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
    if (Test-Path $fallbackGit) {
        $gitCmd = $fallbackGit
    } else {
        Write-Host "Git is not installed or not in PATH." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "[1/3] Current Git Status:" -ForegroundColor Yellow
& $gitCmd status --short

Write-Host ""
Write-Host "[2/3] Enter your remote repository URL (from GitHub / GitLab / Bitbucket):" -ForegroundColor Yellow
Write-Host "Example: https://github.com/YOUR_USERNAME/EcomInsights.git" -ForegroundColor DarkGray
$repoUrl = Read-Host "Repository URL"

if ([string]::IsNullOrWhiteSpace($repoUrl)) {
    Write-Host "No URL provided. Exiting." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[3/3] Configuring remote 'origin' and pushing 'main' branch..." -ForegroundColor Yellow

try {
    & $gitCmd remote remove origin 2>$null
} catch {}

& $gitCmd remote add origin $repoUrl.Trim()
& $gitCmd branch -M main

Write-Host "Pushing to $repoUrl..." -ForegroundColor Cyan
& $gitCmd push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "  SUCCESS! Your repository is now live on GitHub!      " -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Push failed or requires credentials." -ForegroundColor Red
    Write-Host "If prompted for password by GitHub, use a Personal Access Token (PAT):" -ForegroundColor Yellow
    Write-Host "  https://github.com/settings/tokens" -ForegroundColor White
}

Read-Host "Press Enter to exit"
