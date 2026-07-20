@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not defined DRCLAW_LOG_LEVEL if defined QWENPAW_LOG_LEVEL set "DRCLAW_LOG_LEVEL=%QWENPAW_LOG_LEVEL%"
if not defined DRCLAW_LOG_LEVEL set "DRCLAW_LOG_LEVEL=debug"
set "DRCLAW_DESKTOP_DEBUG=1"
set "RUST_BACKTRACE=1"
if not defined WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS set "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222"

set "DRCLAW_DEBUG_DIR=%DRCLAW_WORKING_DIR%"
if not defined DRCLAW_DEBUG_DIR if defined QWENPAW_WORKING_DIR set "DRCLAW_DEBUG_DIR=%QWENPAW_WORKING_DIR%"
if not defined DRCLAW_DEBUG_DIR if defined COPAW_WORKING_DIR set "DRCLAW_DEBUG_DIR=%COPAW_WORKING_DIR%"
if not defined DRCLAW_DEBUG_DIR if exist "%USERPROFILE%\.copaw" set "DRCLAW_DEBUG_DIR=%USERPROFILE%\.copaw"
if not defined DRCLAW_DEBUG_DIR if exist "%USERPROFILE%\.qwenpaw" set "DRCLAW_DEBUG_DIR=%USERPROFILE%\.qwenpaw"
if not defined DRCLAW_DEBUG_DIR set "DRCLAW_DEBUG_DIR=%USERPROFILE%\.drclaw"
set "DRCLAW_BACKEND_LOGS=%DRCLAW_DEBUG_DIR%\desktop.log;%DRCLAW_DEBUG_DIR%\drclaw.log;%DRCLAW_DEBUG_DIR%\qwenpaw.log"
set "DRCLAW_SHELL_LOGS=%LOCALAPPDATA%\io.drclaw.desktop\logs\drclaw-desktop.log;%LOCALAPPDATA%\io.agentscope.qwenpaw.desktop\logs\drclaw-desktop.log;%LOCALAPPDATA%\com.qwenpaw.desktop\logs\drclaw-desktop.log"

echo ====================================
echo Dr.Claw Desktop - Debug Mode
echo ====================================
echo Log level: %DRCLAW_LOG_LEVEL%
echo Working directory: %DRCLAW_DEBUG_DIR%
echo Press Ctrl+C to stop watching logs.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0drclaw-desktop-debug.ps1"
