# Testing Guide

This guide explains how to run the test suite for the IndexPlease-style indexing implementation.

## Test Types

### 1. Unit Tests (`test_indexing_module.py`)
Tests individual components without requiring real authentication:
- OAuth URL generation
- Authentication status checks
- Property retrieval
- Single URL submission
- Bulk URL submission
- History and statistics
- Error handling
- Quota management

```bash
python test_indexing_module.py
```

### 2. Integration Tests (`test_indexing_real_account.py`)
Tests the complete system with a real Google account:
- Real OAuth authentication flow
- Search Console property access
- URL submission to your verified properties
- Batch processing
- Result verification

## Prerequisites for Integration Testing

### 1. Environment Setup
Create a `.env` file with:
```env
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
TEST_USER_EMAIL=your-google-account@gmail.com

# Optional: Service Account (fallback)
GOOGLE_SERVICE_ACCOUNT_FILE=serviceAccountKey.json
```

### 2. Google Cloud Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Enable APIs:
   - Google Search Console API
   - Indexing API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs:
     - http://localhost:8000/api/auth/google/callback
     - http://localhost:3000/auth/google/callback

### 3. Search Console Setup
1. Have at least one verified property in [Google Search Console](https://search.google.com/search-console)
2. The property should be accessible with your Google account

### 4. Test URLs
Update `TEST_URLS` in `test_indexing_real_account.py` with URLs from your verified property:
```python
TEST_URLS = [
    "https://your-domain.com/page1",
    "https://your-domain.com/page2",
    # ...
]
```

## Running Integration Tests

1. Start the backend server:
```bash
python run.py
```

2. In a new terminal, run the integration tests:
```bash
python test_indexing_real_account.py
```

3. Follow the prompts:
   - Confirm prerequisites
   - Complete Google OAuth when browser opens
   - Select a Search Console property
   - Watch the test progress

## Test Results

Both test scripts generate detailed results:
- Console output with pass/fail status
- JSON result files with timestamps
- Individual test details and error messages

### Example Output
```
🧪 TEST SUMMARY
============
✅ Passed: 11
❌ Failed: 0
📝 Total:  11

📄 Test results saved to real_account_test_results_20250627_123456.json
```

## Troubleshooting

### Common Issues

1. **OAuth Errors**
   - Check client ID and secret
   - Verify redirect URIs in Google Cloud Console
   - Ensure APIs are enabled

2. **Property Access Errors**
   - Verify property ownership in Search Console
   - Check account permissions
   - Ensure TEST_USER_EMAIL matches the account used

3. **URL Submission Errors**
   - URLs must be from verified properties
   - Check URL format and accessibility
   - Verify quota availability

4. **Firestore Errors**
   - Check service account key
   - Verify database rules
   - Create necessary indexes

### Creating Firestore Indexes

If you see errors about missing indexes, follow the provided links to create them:
```
The query requires an index. You can create it here: https://console.firebase.google.com/...
```

## Best Practices

1. **Test Data**
   - Use real, accessible URLs
   - Test various URL patterns
   - Include error cases

2. **Authentication**
   - Use a dedicated test account
   - Don't commit credentials
   - Rotate secrets regularly

3. **Quota Management**
   - Monitor usage during testing
   - Stay within daily limits
   - Use lower priority for tests

4. **Error Handling**
   - Check all error responses
   - Verify error messages
   - Test recovery flows

## Continuous Integration

For CI environments:
1. Use service account authentication
2. Mock OAuth flow
3. Use test properties
4. Limit test URL count

## Support

For issues or questions:
1. Check error logs
2. Review Google API quotas
3. Verify credentials
4. Contact support team 