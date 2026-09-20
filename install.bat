@echo off
chcp 65001 >nul
title نصب اسکرپر دارو
where py >nul 2>&1
if errorlevel 1 (
  echo Python Launcher پیدا نشد.
  pause
  exit /b 1
)
py -3.12 -m pip install -r requirements.txt
if errorlevel 1 (
  echo نصب وابستگی‌ها ناموفق بود.
  pause
  exit /b 1
)
echo نصب با موفقیت انجام شد.
pause
