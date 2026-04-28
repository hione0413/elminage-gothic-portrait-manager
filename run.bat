@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 portrait_manager.py %*
    goto :end
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python portrait_manager.py %*
    goto :end
)

echo Python 3 가 설치되어 있지 않습니다. https://www.python.org/ 에서 설치 후 다시 실행하세요.
echo Pillow 도 필요합니다:  pip install pillow
pause

:end
endlocal
