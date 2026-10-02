@echo off
echo ============================================
echo   Career Buddy - Setup Script
echo ============================================
echo.

REM ---- Step 1: Prompt for MySQL password ----
set /p MYSQL_PASS=Enter your MySQL root password (press Enter if none):

REM ---- Step 2: Create database ----
echo.
echo [1/4] Creating MySQL database...
if "%MYSQL_PASS%"=="" (
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS business_english_lms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
) else (
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p%MYSQL_PASS% -e "CREATE DATABASE IF NOT EXISTS business_english_lms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
)

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Could not create database. Check your MySQL password and try again.
    pause
    exit /b 1
)
echo Database created successfully!

REM ---- Step 3: Update .env with password ----
echo.
echo [2/4] Updating .env with MySQL password...
(
echo SECRET_KEY=django-insecure-biz-english-lms-secret-key-2024-change-in-production
echo DEBUG=True
echo DB_NAME=business_english_lms
echo DB_USER=root
echo DB_PASSWORD=%MYSQL_PASS%
echo DB_HOST=localhost
echo DB_PORT=3306
) > .env
echo .env updated!

REM ---- Step 4: Run migrations ----
echo.
echo [3/4] Running database migrations...
python manage.py makemigrations
python manage.py migrate
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Migrations failed. Check your database connection.
    pause
    exit /b 1
)
echo Migrations complete!

REM ---- Step 5: Populate activities ----
echo.
echo [4/4] Loading all 20 activities and exercises...
python manage.py populate_activities
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Data population failed.
    pause
    exit /b 1
)

REM ---- Step 6: Create superuser ----
echo.
echo ---- Creating Admin (Superuser) Account ----
python manage.py createsuperuser

REM ---- Step 7: Done ----
echo.
echo ============================================
echo   Setup Complete!
echo   Run: python manage.py runserver
echo   Open: http://127.0.0.1:8000
echo   Admin: http://127.0.0.1:8000/admin
echo ============================================
pause
