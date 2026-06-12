# physics-prob-v2 conda 환경에서 스크립트 실행
# 사용법: .\run.ps1 step1_test_grid.py
#         .\run.ps1 main.py --single-test
#         .\run.ps1 main.py --rho uniform --trials 1000

$Python = "C:\Users\codin\miniconda3\envs\physics-prob-v2\python.exe"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $PSScriptRoot
& $Python @args
