@echo off
echo Setting environment variables...
set GEMINI_API_KEY=AIzaSyC20lXgVUt4gBzx7NKKB85CdI1pY1nh0ZI
set FIREBASE_WEB_API_KEY=AIzaSyDcOJh_ClEATDdmsZ7haVXAhuEMBxo026U
set GOOGLE_CLIENT_ID=305806997667-uk3asnrtmbajvifs3nf9q3o55o5g4lts.apps.googleusercontent.com
set GOOGLE_CLIENT_SECRET=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
set GOOGLE_REDIRECT_URI=https://www.sitegrip.com/auth/callback

echo Starting Cloud Build deployment...
gcloud beta builds submit --config cloudbuild.yaml ^
--substitutions ^
"_GEMINI_API_KEY=%GEMINI_API_KEY%,^
_FIREBASE_WEB_API_KEY=%FIREBASE_WEB_API_KEY%,^
_GOOGLE_CLIENT_ID=%GOOGLE_CLIENT_ID%,^
_GOOGLE_CLIENT_SECRET=%GOOGLE_CLIENT_SECRET%,^
_GOOGLE_REDIRECT_URI=%GOOGLE_REDIRECT_URI%" ^
--project=sitegrip-backend > deploy.log 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Deployment completed successfully!
    type deploy.log
) else (
    echo Deployment failed with error code %ERRORLEVEL%
    echo Full error log:
    type deploy.log
    pause
) 