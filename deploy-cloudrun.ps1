# Google Cloud Run Deployment Script
# This script builds and deploys your FastAPI app to Google Cloud Run

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "webwatch-api",
    
    [Parameter(Mandatory=$true)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$true)]
    [string]$GeminiApiKey,

    [Parameter(Mandatory=$true)]
    [string]$FirebaseWebApiKey,

    [Parameter(Mandatory=$false)]
    [string]$GoogleClientId = "",

    [Parameter(Mandatory=$false)]
    [string]$GoogleClientSecret = "",

    [Parameter(Mandatory=$false)]
    [string]$GoogleRedirectUri = "",

    [Parameter(Mandatory=$false)]
    [string]$FirestoreDatabase = "indexing-sitegrip"
)

Write-Host "Deploying to Google Cloud Run..." -ForegroundColor Green
Write-Host "Project ID: $ProjectId" -ForegroundColor Yellow
Write-Host "Service Name: $ServiceName" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Firestore Database: $FirestoreDatabase" -ForegroundColor Yellow

# Set the project
Write-Host "Setting project..." -ForegroundColor Blue
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "Enabling required APIs..." -ForegroundColor Blue
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com

# Build and deploy to Cloud Run
Write-Host "Building and deploying to Cloud Run..." -ForegroundColor Blue
gcloud run deploy $ServiceName `
    --source . `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 1 `
    --timeout 600 `
    --max-instances 10 `
    --min-instances 0 `
    --port 8080 `
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_FIRESTORE_DATABASE=$FirestoreDatabase,GEMINI_API_KEY=$GeminiApiKey,FIREBASE_WEB_API_KEY=$FirebaseWebApiKey,GOOGLE_CLIENT_ID=$GoogleClientId,GOOGLE_CLIENT_SECRET=$GoogleClientSecret,GOOGLE_REDIRECT_URI=$GoogleRedirectUri"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment successful!" -ForegroundColor Green
    Write-Host "Getting service URL..." -ForegroundColor Blue
    $serviceUrl = gcloud run services describe $ServiceName --region $Region --format "value(status.url)"
    Write-Host "Your service is available at: $serviceUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "Environment Configuration:" -ForegroundColor Cyan
    Write-Host "  - Project ID: $ProjectId" -ForegroundColor White
    Write-Host "  - Firestore Database: $FirestoreDatabase" -ForegroundColor White
    Write-Host "  - Service URL: $serviceUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "Test your deployment:" -ForegroundColor Cyan
    Write-Host "  curl $serviceUrl/api/auth/debug/firestore" -ForegroundColor White
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
} 