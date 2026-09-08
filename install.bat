@echo off
setlocal EnableDelayedExpansion
set "HERE=%~dp0"
set "HERE=%HERE:~0,-1%"
cd /d "%HERE%"
if not exist "%HERE%\agents\code-reviewer.md" (
    echo [ERROR] agents\code-reviewer.md missing. Run this from the unpacked artifact or git checkout.
    exit /b 1
)
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    echo [ERROR] python is not on PATH.
    exit /b 1
)
%PY% "%HERE%\install.py" --root "%HERE%"
exit /b %ERRORLEVEL%
