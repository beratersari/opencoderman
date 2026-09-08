@echo off
REM Online machine: fetch the OpenCode CLI into vendor\bin.
REM Same as: python packaging\build_artifact.py --in-place
REM IMPORTANT: never use unescaped "->" in echo lines (cmd redirect).

setlocal EnableDelayedExpansion
set "HERE=%~dp0"
set "HERE=%HERE:~0,-1%"
cd /d "%HERE%"
if not exist "%HERE%\agents\code-reviewer.md" (
    echo [ERROR] agents\code-reviewer.md missing. Run this from the git checkout.
    exit /b 1
)
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    echo [ERROR] python is not on PATH.
    exit /b 1
)
echo ========================================
echo   OpenCoderman - vendor OpenCode CLI
echo ========================================
%PY% "%HERE%\packaging\build_artifact.py" --in-place --root "%HERE%"
exit /b %ERRORLEVEL%
