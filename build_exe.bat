@echo off
setlocal
echo ============================================
echo  SonOyuncu Auto Message Bot - EXE Olusturucu
echo ============================================
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo PyInstaller derlemesi baslatiliyor...
pyinstaller --clean --noconfirm SonOyuncuAutoMessage.spec

echo.
if exist "dist\SonOyuncuAutoMessageBot.exe" (
    echo [BASARILI] EXE olusturuldu: dist\SonOyuncuAutoMessageBot.exe
) else (
    echo [HATA] EXE olusturulamadi. Yukaridaki ciktiyi kontrol edin.
    exit /b 1
)
pause
