@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo ======================================================
echo    真白猫ミミィ 誤読辞典 自動一括更新ツール
echo ======================================================
echo.
echo 2026/02/19 以降の新着配信を自動スキャンします（メン限は除外）。
echo.
echo 処理を開始するには何かキーを押してください...
pause > nul

python update_dictionary.py

echo.
echo すべての処理が終了しました。
pause
