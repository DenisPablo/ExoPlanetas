# CORS Configuration for Exoplanetas API

## Overview
This document describes the CORS (Cross-Origin Resource Sharing) configuration for the Exoplanetas API backend to allow requests from the frontend application.

## Configuration Details

### Allowed Origins
The API is configured to accept requests from the following origins:

- **Production Frontend**: `https://exoplanetas-intersoft.onrender.com`
- **Local Development**: `http://localhost:3000`
- **Alternative Local Port**: `http://localhost:3001`
- **Alternative Localhost**: `http://127.0.0.1:3000`

### Allowed Methods
- `GET` - For retrieving data
- `POST` - For creating/uploading data
- `PUT` - For updating data
- `DELETE` - For deleting data
- `OPTIONS` - For CORS preflight requests

### Allowed Headers
- `*` - All headers are allowed

### Credentials
- `allow_credentials=True` - Enables cookies and authentication headers

## Implementation

The CORS configuration is implemented in `API/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://exoplanetas-intersoft.onrender.com",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

## Testing

### Local Testing
To test CORS locally:

```bash
# Start the backend
python3 run.py

# Test with curl
curl -H "Origin: https://exoplanetas-intersoft.onrender.com" \
     "http://localhost:8000/model/info"
```

### Frontend Integration
The frontend at `https://exoplanetas-intersoft.onrender.com` can now make requests to:
- `https://exoplanetas.onrender.com/model/info`
- `https://exoplanetas.onrender.com/predict`
- `https://exoplanetas.onrender.com/predict/upload`
- All other API endpoints

## Security Considerations

- Only specific origins are allowed (not wildcard `*`)
- Credentials are enabled for authenticated requests
- All HTTP methods are allowed for full API functionality
- All headers are allowed for maximum compatibility

## Troubleshooting

### Common CORS Issues

1. **"Access to fetch at '...' from origin '...' has been blocked by CORS policy"**
   - Verify the frontend URL is in the `allow_origins` list
   - Check that the backend is running and accessible

2. **Preflight requests failing**
   - Ensure `OPTIONS` method is in `allow_methods`
   - Verify headers are properly configured

3. **Credentials not being sent**
   - Check that `allow_credentials=True`
   - Ensure frontend is sending credentials correctly

### Debugging

To debug CORS issues:

1. Check browser developer tools Network tab
2. Look for preflight OPTIONS requests
3. Verify response headers include CORS headers
4. Test with curl to isolate frontend vs backend issues

## Deployment

The CORS configuration is automatically applied when the backend is deployed to Render at:
- **Backend**: `https://exoplanetas.onrender.com`
- **Frontend**: `https://exoplanetas-intersoft.onrender.com`

No additional configuration is needed for deployment.
