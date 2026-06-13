@echo off
REM physics-prob-v2 conda 환경에서 스크립트 실행 (실행 정책 무관)
REM 사용법: run.bat sphere_study.py --run --trials 50000

set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"C:\Users\codin\miniconda3\envs\physics-prob-v2\python.exe" %*
