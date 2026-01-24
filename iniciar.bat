@echo off
title TTS Rapidim - Servidor
color 0A

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    TTS Rapidim v1.0                        ║
echo ║      Text-to-Speech com Azure Edge TTS e Google TTS        ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Ativa o ambiente virtual se existir
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo [*] Verificando dependencias...
pip install -q flask gTTS pydub python-dotenv azure-cognitiveservices-speech 2>nul

echo [*] Verificando atualizacao do edge-tts...
pip install --upgrade edge-tts -q 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [+] Dependencias instaladas!
) else (
    echo [!] Aviso: Erro ao verificar dependencias
)

echo [*] Iniciando servidor...
echo.
echo    Acesse: http://localhost:5000
echo    Pressione Ctrl+C para encerrar
echo.

start http://localhost:5000
python app.py

pause
