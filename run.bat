@echo off
rem Create the venv if needed, install requirements, build assets, run the game.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv || python -m venv .venv || goto :nopython
)
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :fail
".venv\Scripts\python.exe" tools\build_assets.py || goto :fail
".venv\Scripts\python.exe" tools\build_audio.py || goto :fail
".venv\Scripts\python.exe" main.py %*
goto :eof

:nopython
echo Could not find Python 3.11 or newer. Install it from python.org or the
echo Microsoft Store, tick "Add python.exe to PATH", and run this again.
exit /b 1

:fail
echo Something went wrong above. The game was not started.
exit /b 1
