@echo off
setlocal
chcp 65001 > nul

:: ドライブとパスの固定
set "BASE_DIR=%~dp0"
%BASE_DIR:~0,2%
cd "%BASE_DIR%"

set PYTHONPATH=%BASE_DIR%

:menu
cls
echo ======================================================
echo    真白猫ミミィ 誤読管理システム (新ワークフロー版)
echo ======================================================
echo.
echo  【現在の流れ】
echo   1. 最新配信をスキャン (refined.txt に追記)
echo   2. refined.txt を自分で編集 (確定作業)
echo   3. Webサイト・DBに反映 (同期実行)
echo.
echo ------------------------------------------------------
echo 1. 最新配信をスキャン 🔍 (新規候補を追記)
echo 2. refined.txt を開く 📝 (内容を確認・編集)
echo 3. Webサイト・DBに反映 🚀 (編集内容を確定)
echo ------------------------------------------------------
echo 4. 無視リストを編集 ⚙️
echo 5. 終了
echo.
set /p choice="選択 (1-5): "

if "%choice%"=="1" (
    echo.
    echo --- 最新配信のコメントをスキャン中... ---
    python scripts\collect_comments.py
    pause
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
    echo ✅ 反映が完了しました！
    pause
    goto menu
)

if "%choice%"=="4" (
    start notepad.exe exclude_keywords.txt
    goto menu
)

if "%choice%"=="5" exit

goto menu
