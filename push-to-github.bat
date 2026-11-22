@echo off
setlocal enabledelayedexpansion
title Push EcomInsights to GitHub

echo ========================================================
echo   EcomInsights - One-Click Git Repository Uploader
echo ========================================================
echo.

:: Detect git.exe
where git >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "GIT_CMD=git"
) else if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
    set "GIT_CMD=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
) else (
    echo [ERROR] Git was not found on your system.
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/3] Checking current repository status...
"%GIT_CMD%" status --short

echo.
echo [2/3] Remote GitHub repository:
echo Default: https://github.com/mskaraguppi123-afk/EcomInsights.git
echo.
set "REPO_URL="
set /p REPO_URL="Enter repository URL [Press Enter to use default]: "
if "%REPO_URL%"=="" set "REPO_URL=https://github.com/mskaraguppi123-afk/EcomInsights.git"

echo.
echo [3/3] Setting remote origin and pushing to GitHub...
"%GIT_CMD%" remote remove origin >nul 2>&1
"%GIT_CMD%" remote add origin %REPO_URL%
"%GIT_CMD%" branch -M main

echo.
echo Pushing branch 'main' to %REPO_URL%...
"%GIT_CMD%" push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   SUCCESS! All files and commits uploaded to GitHub!
    echo ========================================================
) else (
    echo.
    echo [NOTE] If GitHub asked for a password, use a GitHub Personal Access Token (PAT):
    echo        https://github.com/settings/tokens
)

echo.
pause
