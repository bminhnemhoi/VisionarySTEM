@echo off
REM Backend keepalive — auto-restart uvicorn nếu chết.
REM Dùng cho Windows dev: chạy file này 1 lần, để chạy nền.

cd /d "%~dp0\.."
echo [%date% %time%] VisionarySTEM backend keepalive started
echo Working dir: %cd%
echo Logs: output\uvicorn.out + output\uvicorn.err

if not exist output mkdir output

:loop
echo [%date% %time%] Starting uvicorn... >> output\uvicorn.keepalive.log
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 >> output\uvicorn.out 2>> output\uvicorn.err
echo [%date% %time%] Backend exited with code %errorlevel%. Restarting in 3s... >> output\uvicorn.keepalive.log
timeout /t 3 /nobreak > nul
goto loop
