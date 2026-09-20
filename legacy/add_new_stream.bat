@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo ======================================================
echo    真白猫ミミィ 誤読辞典 更新ツール
echo ======================================================
echo.
echo 更新したい動画のURLを入力してください。
echo (例: https://www.youtube.com/watch?v=xxxxxx)
echo.
set /p VIDEO_URL="URL: "

if "%VIDEO_URL%"=="" (
    echo URLが入力されていません。終了します。
    pause
    exit /b
)

echo.
echo 処理を開始します...
python update_dictionary.py "%VIDEO_URL%"

echo.
echo 全ての処理が終わりました。
pause
