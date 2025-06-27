# Real-Time Production Deployment Guide

## ✅ **Firestore Configuration Status**
- **Local Environment**: ✅ Working with `indexing-sitegrip` database
- **Production Environment**: ✅ Ready for deployment with proper configuration

## 🚀 **Deploy to Cloud Run**

### Option 1: Using PowerShell Script (Recommended)

```powershell
# Navigate to backend directory
cd backend

# Deploy with all required environment variables
.\deploy-cloudrun.ps1 `
    -ProjectId "sitegrip-backend" `
    -Region "us-central1" `
    -GeminiApiKey "YOUR_GEMINI_API_KEY" `
    -FirebaseWebApiKey "YOUR_FIREBASE_WEB_API_KEY" `
    -GoogleClientId "YOUR_GOOGLE_CLIENT_ID" `
    -GoogleClientSecret "YOUR_GOOGLE_CLIENT_SECRET" `
    -GoogleRedirectUri "https://YOUR_DOMAIN.com/auth/callback" `
    -FirestoreDatabase "indexing-sitegrip"
```

### Option 2: Using Cloud Build

```bash
# Navigate to backend directory
cd backend

# Deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml \
    --substitutions=_GEMINI_API_KEY="YOUR_GEMINI_API_KEY",_FIREBASE_WEB_API_KEY="YOUR_FIREBASE_WEB_API_KEY",_GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID",_GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET",_GOOGLE_REDIRECT_URI="https://YOUR_DOMAIN.com/auth/callback"
```

## 🔧 **Environment Variables**

The deployment automatically sets these environment variables:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GOOGLE_CLOUD_PROJECT` | `sitegrip-backend` | Firebase project ID |
| `GOOGLE_FIRESTORE_DATABASE` | `indexing-sitegrip` | Firestore Native mode database |
| `GEMINI_API_KEY` | Your API key | AI functionality |
| `FIREBASE_WEB_API_KEY` | Your Firebase key | Frontend authentication |
| `GOOGLE_CLIENT_ID` | Your OAuth client ID | Google authentication |
| `GOOGLE_CLIENT_SECRET` | Your OAuth secret | Google authentication |
| `GOOGLE_REDIRECT_URI` | Your callback URL | OAuth flow |

## 🧪 **Test Your Deployment**

After deployment, test the Firestore connection:

```bash
# Test database connection
curl https://YOUR_SERVICE_URL/api/auth/debug/firestore

# Expected response:
{
  "success": true,
  "client_type": "Real Firestore Client",
  "message": "Firestore is working correctly",
  "test_write_read": true
}
```

## 🔍 **Troubleshooting**

### If you see "MockFirestoreClient" in production:

1. **Check Cloud Run logs**:
   ```bash
   gcloud logs read --service=webwatch-api --limit=50
   ```

2. **Verify environment variables**:
   ```bash
   gcloud run services describe webwatch-api --region=us-central1 --format="export"
   ```

3. **Check service account permissions**:
   - Ensure the Cloud Run service account has Firestore permissions
   - Verify the project ID matches your Firebase project

### Common Issues:

- **Database not found**: Ensure `indexing-sitegrip` database exists in Firebase Console
- **Permission denied**: Check service account has `Cloud Datastore User` role
- **Project mismatch**: Verify `GOOGLE_CLOUD_PROJECT` matches your Firebase project

## 📊 **Monitoring**

Monitor your deployment:

1. **Cloud Run Console**: https://console.cloud.google.com/run
2. **Cloud Logging**: https://console.cloud.google.com/logs
3. **Firebase Console**: https://console.firebase.google.com/project/sitegrip-backend

## ✅ **Success Indicators**

Your deployment is working correctly when you see:

- ✅ `Connected to Firestore database: indexing-sitegrip` in logs
- ✅ `Client type: Client` (not MockFirestoreClient)
- ✅ User registration creates documents in Firestore
- ✅ Authentication endpoints return `"database_status": "connected_and_verified"`

## 🔄 **Updating Configuration**

To update Firestore configuration after deployment:

```bash
# Update environment variables
gcloud run services update webwatch-api \
    --region=us-central1 \
    --set-env-vars="GOOGLE_FIRESTORE_DATABASE=new-database-name"
``` 