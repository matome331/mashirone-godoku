@echo off
setlocal
chcp 65001 > nul

set "BASE_DIR=%~dp0"
%BASE_DIR:~0,2%
cd "%BASE_DIR%"

set PYTHONPATH=%BASE_DIR%

echo ======================================================
echo    真白猫ミミィ 誤読レビュー用コメント収集
echo ======================================================
echo.
echo ageha1st さんのコメントだけを収集し、
echo Chat確認用の review_comments に保存します。
echo 誤読判定や refined.txt の変更は行いません。
echo.

echo [1/3] GitHub同期状態を確認中...
python scripts\publish_review_comments.py --preflight
if errorlevel 1 goto :preflight_error

echo.
echo [2/3] YouTubeコメントを収集中...
python scripts\collect_comments.py
if errorlevel 1 goto :collect_error

echo.
echo [3/3] Chat確認用ログをGitHubへ送信中...
python scripts\publish_review_comments.py
if errorlevel 1 goto :publish_error

echo.
echo ======================================================
echo 完了しました。
echo ChatGPTで「新しい誤読見て」と依頼してください。
echo ======================================================
pause
exit /b 0

:preflight_error
echo.
echo ======================================================
echo GitHubの同期確認で止まりました。
echo 表示された案内に従って git pull 等を行ってください。
echo ======================================================
pause
exit /b 1

:collect_error
echo.
echo ======================================================
echo コメント収集が正常完了しませんでした。
echo GitHubへの送信は行っていません。
echo ======================================================
pause
exit /b 1

:publish_error
echo.
echo ======================================================
echo 収集は完了しましたがGitHub送信に失敗しました。
echo review_comments のローカルデータは残っています。
echo ======================================================
pause
exit /b 1
