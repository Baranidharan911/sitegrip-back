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
    [string]$FirebaseWebApiKey
)

Write-Host "Deploying to Google Cloud Run..." -ForegroundColor Green
Write-Host "Project ID: $ProjectId" -ForegroundColor Yellow
Write-Host "Service Name: $ServiceName" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow

# Set the project
Write-Host "Setting project..." -ForegroundColor Blue
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "Enabling required APIs..." -ForegroundColor Blue
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Build and deploy to Cloud Run
Write-Host "Building and deploying to Cloud Run..." -ForegroundColor Blue
gcloud run deploy $ServiceName `
    --source . `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 1 `
    --timeout 300 `
    --max-instances 10 `
    --min-instances 0 `
    --port 8080 `
    --set-env-vars "GOOGLE_CLOUD_PROJECT=sitegrip-firestore,GEMINI_API_KEY=$GeminiApiKey,FIREBASE_WEB_API_KEY=$FirebaseWebApiKey"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment successful!" -ForegroundColor Green
    Write-Host "Getting service URL..." -ForegroundColor Blue
    $serviceUrl = gcloud run services describe $ServiceName --region $Region --format "value(status.url)"
    Write-Host "Your service is available at: $serviceUrl" -ForegroundColor Green
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
} 