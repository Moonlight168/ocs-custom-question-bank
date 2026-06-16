@echo off
REM Package Python project into a single standalone executable (incremental build mode).
REM Navigate to project root (parent of this script) to resolve relative paths correctly.
cd /d "%~dp0.."

set MAIN_SCRIPT=run.py
set SPEC_DIR=scripts
set OUTPUT_DIR=dist
set EXE_NAME=DOUBAO_ASKED_QUICKLY
set VENV_DIR=venv
set VENV_PY=%VENV_DIR%\Scripts\python.exe

REM Pre-check: verify the entry script exists
if not exist "%MAIN_SCRIPT%" (
    echo [ERROR] Entry script not found: %MAIN_SCRIPT%
    echo Current working directory: %cd%
    pause
    exit /b 1
)

REM Create project-local virtual environment on first run.
REM venv keeps the build slim: PyInstaller only sees the 5 deps in requirements.txt
REM instead of pulling every global package (torch, transformers, etc.) into the exe.
if not exist "%VENV_PY%" (
    echo [SETUP] Creating virtual environment: %VENV_DIR%
    python -m venv "%VENV_DIR%" || ( echo [ERROR] venv creation failed & pause & exit /b 1 )
    echo [SETUP] Installing requirements into venv...
    "%VENV_PY%" -m pip install --upgrade pip >nul
    "%VENV_PY%" -m pip install -r requirements.txt || ( echo [ERROR] pip install failed & pause & exit /b 1 )
    "%VENV_PY%" -m pip install pyinstaller || ( echo [ERROR] pyinstaller install failed & pause & exit /b 1 )
)

set PY=%VENV_PY%

REM Create spec directory if it does not exist to avoid path errors
if not exist "%SPEC_DIR%" mkdir "%SPEC_DIR%"

REM Only clean output directory, KEEP build folder for incremental cache
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
REM Note: do NOT delete "build" directory, it stores cached build artifacts for speedup

echo Starting incremental build...
REM Removed --clean flag to reuse cached dependencies
REM Use --log-level INFO to show real-time build progress
REM Capture start time as epoch seconds (PowerShell avoids %time%'s 24h wrap)
for /f %%t in ('powershell -NoProfile -Command "[int][double]::Parse((Get-Date -UFormat %%s))"') do set START_EPOCH=%%t

"%PY%" -m PyInstaller ^
  --onefile ^
  --name %EXE_NAME% ^
  --specpath="%SPEC_DIR%" ^
  --distpath="%OUTPUT_DIR%" ^
  --paths . ^
  --collect-submodules src ^
  --log-level INFO ^
  "%MAIN_SCRIPT%"

REM Compute elapsed time via PowerShell (no midnight wrap issues)
for /f %%t in ('powershell -NoProfile -Command "$s=%START_EPOCH%; $e=[int][double]::Parse((Get-Date -UFormat %%s)); Write-Output ($e-$s)"') do set ELAPSED=%%t
set /a "M=ELAPSED/60, R=ELAPSED%%60"

if %errorlevel% equ 0 (
  echo.
  echo [SUCCESS] Build completed in %M%m%R%s: %OUTPUT_DIR%\%EXE_NAME%.exe
) else (
  echo.
  echo [FAILED] Build failed after %M%m%R%s. Check the log above for details.
)

pause