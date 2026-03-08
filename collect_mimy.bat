@echo off
setlocal
:: 文字コードをUTF-8に設定
chcp 65001 > nul

:: スクリプトがあるディレクトリを取得
set "BASE_DIR=%~dp0"
%BASE_DIR:~0,2%
cd "%BASE_DIR%"

set PYTHONPATH=%BASE_DIR%

echo ======================================================
echo    真白猫ミミィ 誤読収集専用バッチ
echo ======================================================
echo.
echo 2026/02/20 以降の最新動画から、
echo ageha1st さんのコメントのみを収集します。
echo (誤読の判定は Antigravity が行います)
echo.

python scripts\collect_comments.py

echo.
echo ======================================================
echo 処理が完了しました。Antigravityに解析を依頼してください。
echo ======================================================
pause
