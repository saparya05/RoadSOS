@echo off
REM RoadSOS – Windows Launcher (fully offline)
REM Usage: run.bat [streamlit|full|api|install|download-stt]

set MODE=%1
if "%MODE%"=="" set MODE=streamlit

echo.
echo   ========================================
echo    RoadSOS - AI Emergency Assistant
echo    Works 100%% Offline
echo   ========================================
echo.

if "%MODE%"=="install" (
    pip install -r requirements.txt
    echo Done! Run: run.bat
    goto :eof
)

if "%MODE%"=="download-stt" (
    python -c "import whisper; whisper.load_model('tiny'); print('Whisper model cached')"
    goto :eof
)

if "%MODE%"=="api" (
    echo Starting FastAPI on http://localhost:8000
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    goto :eof
)

if "%MODE%"=="full" (
    start /B uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    timeout /t 2 /nobreak >nul
    streamlit run frontend/app.py --theme.base dark --theme.primaryColor "#E53E3E" --theme.backgroundColor "#0D0D14" --theme.secondaryBackgroundColor "#111118" --theme.textColor "#ECECF1"
    goto :eof
)

REM Default: Streamlit embedded
echo Starting RoadSOS at http://localhost:8501
echo Mode: Fully Offline
streamlit run frontend/app.py --theme.base dark --theme.primaryColor "#E53E3E" --theme.backgroundColor "#0D0D14" --theme.secondaryBackgroundColor "#111118" --theme.textColor "#ECECF1"
