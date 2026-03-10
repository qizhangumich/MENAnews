@echo off
REM MENA News System Setup Script for Windows
REM This script helps set up Python 3.10 virtual environment

echo ========================================
echo MENA News Intelligence System v2 - Setup
echo ========================================
echo.

REM Check Python version
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 from: https://www.python.org/downloads/release/python-3100/
    pause
    exit /b 1
)

echo Current Python version:
python --version
echo.

REM Check if Python version is 3.11 (incompatible)
python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo WARNING: Python 3.11+ detected!
    echo This system requires Python 3.10 for feedparser compatibility.
    echo.
    echo Please install Python 3.10 from: https://www.python.org/downloads/release/python-3100/
    echo Or use pyenv to manage multiple Python versions.
    echo.
    pause
    exit /b 1
)

echo Python version is compatible (3.10.x)
echo.

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
echo.

REM Install dependencies
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
echo.

REM Check if .env exists
if not exist ".env" (
    echo Creating .env from template...
    if exist ".env.example" (
        copy .env.example .env
        echo.
        echo IMPORTANT: Edit .env file with your API keys and credentials!
        echo.
        notepad .env
        echo.
    ) else (
        echo WARNING: .env.example not found. Creating basic .env...
        (
            echo # Firebase Configuration
            echo GOOGLE_APPLICATION_CREDENTIALS=./firebase_service_account.json
            echo FIREBASE_PROJECT_ID=menanews-4a30c
            echo.
            echo # Telegram Bot Configuration
            echo TELEGRAM_BOT_TOKEN=your_bot_token_here
            echo TELEGRAM_CHAT_ID=your_chat_id_here
            echo.
            echo # SMTP Email Configuration
            echo SMTP_HOST=smtp.163.com
            echo SMTP_PORT=465
            echo SMTP_USER=your_email@163.com
            echo SMTP_PASSWORD=your_password
            echo EMAIL_TO=recipient@example.com
            echo.
            echo # OpenAI API
            echo OPENAI_API_KEY=sk-your-key-here
        ) > .env
        echo Created .env file.
        echo.
        echo IMPORTANT: Edit .env file with your API keys and credentials!
        echo.
        notepad .env
    )
) else (
    echo .env file exists. Skipping environment setup.
)

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate
echo.
echo Then run commands:
echo   python app.py collect    # Collect news from RSS feeds
echo   python app.py score      # Score articles
echo   python app.py daily-push # Send daily Telegram push
echo   python app.py weekly     # Generate weekly report
echo   python app.py bot        # Run Telegram bot (interactive)
echo.
pause
