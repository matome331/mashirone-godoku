@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul

set "BASE_DIR=%~dp0"
%BASE_DIR:~0,2%
cd "%BASE_DIR%"

set PYTHONPATH=%BASE_DIR%

:menu
cls
echo ======================================================
echo    真白猫ミミィ 誤読管理システム
echo ======================================================
echo.
echo  【現在の流れ】
echo   1. ageha1stさんのコメントを収集してGitHubへ送信
echo   2. Chat上で誤読候補を確認・精査
echo   3. 採用分だけ refined.txt に反映
echo   4. Webサイト・DBに同期
echo.
echo ------------------------------------------------------
echo 1. Chat確認用コメントを収集・送信
echo 2. refined.txt を開く
echo 3. Webサイト・DBに反映
echo 4. 非公開・削除動画を除外
echo 5. 終了
echo.
set /p choice="選択 (1-5): "

if "%choice%"=="1" (
    call collect_mimy.bat
    goto menu
)

if "%choice%"=="2" (
    start notepad.exe mimy_misreadings_refined.txt
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo --- refined.txt の内容をデータベース・Webに反映中... ---
    python scripts\sync_txt_to_db.py
    echo.
    pause
    goto menu
)

if "%choice%"=="4" (
    echo.
    python scripts\exclude_video.py
    echo.
    set /p syncnow="続けてWebサイト・DBへ反映しますか？ (y/n): "
    if /I "!syncnow!"=="y" (
        python scripts\sync_txt_to_db.py
        echo.
        echo 除外設定を反映しました。
    )
    pause
    goto menu
)

if "%choice%"=="5" exit

goto menu
