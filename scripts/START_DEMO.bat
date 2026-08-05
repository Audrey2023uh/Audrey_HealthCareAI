@echo off
title Healthcare AI Evidence Assistant
color 0A

REM Always go to project root (parent of scripts\), not scripts\
cd /d "%~dp0.."
if exist "%~dp0..\app.py" (
  cd /d "%~dp0.."
) else if exist "%~dp0app.py" (
  cd /d "%~dp0"
)

echo.
echo ========================================
echo  Healthcare AI - Starting GUI
echo  Folder: %CD%
echo ========================================
echo.

if not exist "app.py" (
  echo ERROR: app.py not found in:
  echo   %CD%
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is not on PATH.
  pause
  exit /b 1
)

echo Using Python:
python -c "import sys; print(sys.executable)"
echo.

echo [0/2] Checking / installing required packages (faiss, streamlit, ...)
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Trying faiss-cpu alone...
  python -m pip install faiss-cpu streamlit scikit-learn numpy langgraph langchain openai python-dotenv fastapi uvicorn requests pandas tqdm
)

echo.
echo [1/2] Building / refreshing FAISS index...
python scripts\build_index.py
if errorlevel 1 (
  echo.
  echo ERROR: Index build failed.
  echo If you see ModuleNotFoundError, run this in the same window:
  echo   python -m pip install faiss-cpu
  echo Then double-click START_DEMO.bat again.
  pause
  exit /b 1
)

echo.
echo [2/2] Opening Streamlit GUI in your browser...
echo.
echo *** KEEP THIS WINDOW OPEN ***
echo If browser does not open, go to:  http://localhost:8501
echo Press Ctrl+C here to stop.
echo.

python -m streamlit run app.py --server.headless false --browser.gatherUsageStats false

echo.
echo Streamlit stopped.
pause
