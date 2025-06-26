# SiteGrip Indexing Module - Testing Guide

This guide explains how to test the complete indexing backend functionality before integrating with the frontend.

## Test Files Overview

### 1. `run_indexing_tests.py` - Main Test Runner
- Checks module imports
- Verifies server connection
- Runs comprehensive API tests
- **Best for**: Full integration testing

### 2. `test_indexing_module.py` - API Level Tests
- Tests all API endpoints
- Validates request/response flow
- Tests file uploads and error handling
- **Best for**: API endpoint validation

### 3. `test_indexing_services.py` - Service Level Tests
- Tests services directly (no API layer)
- Validates business logic
- Tests database operations
- **Best for**: Unit testing and debugging

## How to Run Tests

### Prerequisites

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up Firestore** (Optional for testing)
   - Set up a test Firestore project
   - Download service account key
   - Set environment variable or update `firestore.py`

### Quick Start

1. **Start the Backend Server**
   ```bash
   cd backend
   python main.py
   ```
   
   The server should start on `http://localhost:8080`

2. **Run All Tests (Recommended)**
   ```bash
   cd backend
   python run_indexing_tests.py
   ```
   
   This will:
   - ✅ Check all module imports
   - ✅ Verify server is running
   - ✅ Run comprehensive API tests
   - ✅ Generate test results JSON file

### Individual Test Runs

#### API Tests Only
```bash
python test_indexing_module.py
```

#### Service Tests Only
```bash
python test_indexing_services.py
```

## Test Coverage

### URL Indexing Tests
- ✅ Submit individual URLs
- ✅ Submit URLs via file upload
- ✅ Handle invalid URLs
- ✅ Retrieve indexing entries
- ✅ Batch status checking

### Sitemap Management Tests
- ✅ Submit sitemaps to Google
- ✅ Analyze sitemap content
- ✅ Discover sitemaps from robots.txt
- ✅ Auto-sync functionality
- ✅ Sitemap deletion and management

### Quota Management Tests
- ✅ Check current quota usage
- ✅ Update quota allocations
- ✅ Domain-based quota tracking
- ✅ Priority-based quota reserves

### Google Search Console Tests
- ✅ OAuth URL generation
- ✅ OAuth callback handling (mock)
- ✅ Property management
- ✅ URL data fetching
- ✅ Credential storage

### Statistics and Analytics Tests
- ✅ Indexing statistics generation
- ✅ Success rate calculations
- ✅ Quota usage percentages
- ✅ Historical data tracking

### Background Scheduler Tests
- ✅ Daily quota reset
- ✅ Sitemap synchronization
- ✅ Status checking automation
- ✅ History cleanup

## Test Results

### Output Files
- `indexing_test_results.json` - Detailed test results with timestamps
- Console output with real-time test status

### Success Indicators
- ✅ **All Green**: Module is ready for frontend integration
- ⚠️  **Some Red**: Check specific failures and fix issues
- ❌ **Import Errors**: Dependencies or module structure issues

## Mock vs Real Services

### Currently Mocked
- **Google Indexing API**: Returns mock responses
- **Google Search Console API**: Returns sample data
- **OAuth Flow**: Simulates authentication

### Real Services
- **Firestore Database**: Uses actual Firestore (if configured)
- **URL Validation**: Real URL parsing and validation
- **File Upload**: Real file processing
- **Background Scheduler**: Real threading and scheduling

## Troubleshooting

### Common Issues

1. **Server Not Running**
   ```
   ❌ Cannot connect to backend server
   ```
   **Fix**: Start the server with `python main.py`

2. **Import Errors**
   ```
   ❌ ImportError: No module named 'some_module'
   ```
   **Fix**: Install dependencies with `pip install -r requirements.txt`

3. **Firestore Connection Issues**
   ```
   ❌ Firestore initialization failed
   ```
   **Fix**: Either set up proper credentials or run tests without Firestore

4. **Port Already in Use**
   ```
   ❌ Address already in use
   ```
   **Fix**: Stop other services on port 8080 or change port in `main.py`

### Debug Mode

For detailed debugging, modify the test files:

```python
# Add detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add print statements in services
print(f"Debug: {variable_name}")
```

## Production Readiness Checklist

After all tests pass:

- [ ] ✅ All API endpoints working
- [ ] ✅ Database operations successful
- [ ] ✅ File upload functionality working
- [ ] ✅ Error handling robust
- [ ] ✅ Mock services ready for real API integration
- [ ] ✅ Background scheduler functional
- [ ] ✅ Quota management working
- [ ] ✅ Statistics generation accurate

## Next Steps

Once all tests pass:

1. **Frontend Integration**: Start building the React components
2. **Real API Integration**: Replace mock services with real Google APIs
3. **Authentication**: Implement proper user authentication
4. **Production Deployment**: Deploy to production environment

## Support

If you encounter issues:

1. Check the console output for specific error messages
2. Review the `indexing_test_results.json` file for detailed results
3. Run individual service tests to isolate issues
4. Check the `INDEXING_README.md` for API documentation 