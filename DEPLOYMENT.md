# Firebase (Google App Engine) Deployment Guide

This guide will help you deploy your FastAPI backend to Google App Engine (Firebase hosting for backend services).

## Prerequisites

1. **Google Cloud Account**: Create one at [cloud.google.com](https://cloud.google.com)
2. **Google Cloud Project**: Create a new project in the Google Cloud Console
3. **Firebase Project**: Link your Google Cloud project to Firebase
4. **Service Account**: You should have `serviceAccountKey.json` in your project root

## Step-by-Step Deployment

### 1. Install Google Cloud SDK

**Option A: Using the installer (Recommended)**
- Download from: https://cloud.google.com/sdk/docs/install
- Run the installer and make sure to check "Add gcloud to PATH"
- Restart your terminal after installation

**Option B: Using winget (if available)**
```bash
winget install Google.CloudSDK
```

### 2. Verify Installation
```bash
gcloud --version
```

If this command doesn't work, you may need to:
- Restart your terminal
- Manually add gcloud to your PATH
- The default installation path is: `C:\Users\[USERNAME]\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin`

### 3. Authenticate with Google Cloud
```bash
gcloud auth login
```
This will open a browser window for authentication.

### 4. Set Your Project
```bash
gcloud config set project YOUR_PROJECT_ID
```
Replace `YOUR_PROJECT_ID` with your actual Google Cloud project ID.

### 5. Enable Required APIs
```bash
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
```

### 6. Initialize App Engine (First time only)
```bash
gcloud app create --region=us-central1
```
Choose a region close to your users. Common options:
- `us-central1` (Iowa)
- `us-east1` (South Carolina)
- `europe-west1` (Belgium)
- `asia-southeast1` (Singapore)

### 7. Deploy Your Application
```bash
gcloud app deploy app.yaml
```

### 8. View Your Deployed Application
```bash
gcloud app browse
```
Or visit: `https://YOUR_PROJECT_ID.appspot.com`

## Quick Deployment (Using Scripts)

### PowerShell Script
```powershell
.\deploy.ps1
```

### Batch Script
```cmd
deploy.bat
```

Both scripts will guide you through the entire deployment process.

## Project Structure

Your project is configured with:
- `app.yaml`: App Engine configuration
- `.gcloudignore`: Files to exclude from deployment
- `main.py`: FastAPI application entry point
- `requirements.txt`: Python dependencies
- `serviceAccountKey.json`: Firebase service account credentials

## Environment Variables

The following environment variables are configured in `app.yaml`:
- `GOOGLE_APPLICATION_CREDENTIALS`: Points to your service account key

## Firestore Setup

Your application uses Firestore as the database. Make sure:
1. Firestore is enabled in your Firebase project
2. Your service account has the necessary permissions
3. The `serviceAccountKey.json` file is in your project root

## API Endpoints

After deployment, your API will be available at:
- Root: `https://YOUR_PROJECT_ID.appspot.com/`
- API docs: `https://YOUR_PROJECT_ID.appspot.com/docs`
- Health check: `https://YOUR_PROJECT_ID.appspot.com/health`

## Troubleshooting

### Common Issues

1. **"gcloud command not found"**
   - Restart your terminal
   - Check if gcloud is in your PATH
   - Reinstall Google Cloud SDK

2. **"Permission denied" errors**
   - Make sure you're authenticated: `gcloud auth login`
   - Check your service account permissions
   - Verify your project ID is correct

3. **"App Engine application does not exist"**
   - Run: `gcloud app create --region=YOUR_REGION`

4. **"API not enabled" errors**
   - Enable required APIs as shown in step 5

5. **Deployment fails**
   - Check your `app.yaml` syntax
   - Ensure all required files are present
   - Check the build logs for specific errors

### Viewing Logs
```bash
gcloud app logs tail -s default
```

### Managing Versions
```bash
# List versions
gcloud app versions list

# Delete old versions
gcloud app versions delete VERSION_ID
```

## Cost Optimization

- App Engine offers a generous free tier
- Set up budget alerts in Google Cloud Console
- Consider using `automatic_scaling` parameters to control costs
- Delete unused versions regularly

## Security Best Practices

1. **Service Account Security**:
   - Never commit `serviceAccountKey.json` to version control
   - Use environment variables for sensitive data
   - Regularly rotate service account keys

2. **CORS Configuration**:
   - Update CORS settings in `main.py` to only allow your frontend domains
   - Remove `allow_origins=["*"]` in production

3. **Firestore Security**:
   - Set up proper Firestore security rules
   - Use authentication for sensitive operations

## Updating Your Deployment

To update your deployed application:
```bash
gcloud app deploy app.yaml
```

App Engine will create a new version and automatically route traffic to it.

## Support

- Google Cloud Documentation: https://cloud.google.com/appengine/docs
- Firebase Documentation: https://firebase.google.com/docs
- FastAPI Documentation: https://fastapi.tiangolo.com/ 