@echo off
chcp 65001 >nul
echo ============================================================
echo  PDF Editor — 打包成執行檔
echo ============================================================

:: 確認在正確目錄
cd /d "%~dp0"

:: 啟動 venv
call .venv\Scripts\activate.bat

:: 清除上次的建置結果
echo [1/2] 清除舊版本...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

:: 開始打包
echo [2/2] 開始打包 (可能需要 1~3 分鐘)...
pyinstaller PDFEditor.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 打包失敗，請查看上方錯誤訊息。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  打包完成！
echo  執行檔位置: dist\PDFEditor\PDFEditor.exe
echo ============================================================
pause
