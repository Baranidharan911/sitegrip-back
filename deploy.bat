@echo off
echo Starting Firebase (Google App Engine) Deployment...
echo.

REM Check if gcloud is available
gcloud --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Google Cloud SDK not found in PATH
    echo Please install Google Cloud SDK and add it to PATH
    echo Download from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

echo Google Cloud SDK found!
echo.

REM Authenticate (if not already done)
echo Step 1: Authenticating with Google Cloud...
gcloud auth login

echo.
echo Step 2: Setting up project...
set /p PROJECT_ID="Enter your Google Cloud Project ID: "
gcloud config set project %PROJECT_ID%

echo.
echo Step 3: Enable required APIs...
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com

echo.
echo Step 4: Deploying to App Engine...
gcloud app deploy app.yaml --quiet

echo.
echo Deployment completed!
echo Your API will be available at: https://%PROJECT_ID%.appspot.com
echo.
pause 