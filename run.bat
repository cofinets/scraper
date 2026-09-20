@echo off
chcp 65001 >nul
title Iran Medicine Scraper
py -3.12 main.py
if errorlevel 1 (
  echo اجرای برنامه ناموفق بود.
  pause
)
