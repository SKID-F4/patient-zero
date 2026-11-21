@echo off
chcp 65001 >nul
title Patient zéro - salon
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js est introuvable sur ce PC. & pause & exit /b 1)
start "" "http://localhost:8790"
node server.js
pause
