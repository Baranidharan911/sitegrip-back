#!/usr/bin/env pwsh

Write-Host "Starting Firebase (Google App Engine) Deployment..." -ForegroundColor Green
Write-Host ""

# Check if gcloud is available
try {
    $gcloudVersion = gcloud --version 2>$null
    Write-Host "Google Cloud SDK found!" -ForegroundColor Green
    Write-Host $gcloudVersion[0]
} catch {
    Write-Host "ERROR: Google Cloud SDK not found in PATH" -ForegroundColor Red
    Write-Host "Please install Google Cloud SDK and add it to PATH"
    Write-Host "Download from: https://cloud.google.com/sdk/docs/install"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Step 1: Authentication
Write-Host "Step 1: Authenticating with Google Cloud..." -ForegroundColor Yellow
gcloud auth login

# Step 2: Project setup
Write-Host ""
Write-Host "Step 2: Setting up project..." -ForegroundColor Yellow
$PROJECT_ID = Read-Host "Enter your Google Cloud Project ID"
gcloud config set project $PROJECT_ID

# Step 3: Enable APIs
Write-Host ""
Write-Host "Step 3: Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com

# Step 4: Deploy
Write-Host ""
Write-Host "Step 4: Deploying to App Engine..." -ForegroundColor Yellow
gcloud app deploy app.yaml --quiet

Write-Host ""
Write-Host "Deployment completed!" -ForegroundColor Green
Write-Host "Your API will be available at: https://$PROJECT_ID.appspot.com" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit" 