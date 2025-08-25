# Testing Klaviyo OAuth Start Endpoint

## Quick Test with cURL

Test if the OAuth start endpoint is properly mounted and responding:

```bash
# Test the simple test endpoint
curl -i "http://localhost:8000/api/integrations/klaviyo/test"

# Test the simplified OAuth start (no auth required)
curl -i "http://localhost:8000/api/integrations/klaviyo/oauth/start-simple"

# Test the main OAuth start endpoint
curl -i "http://localhost:8000/api/integrations/klaviyo/oauth/start?redirect_path=/admin/clients"
```

## Expected Responses

### For `/test` endpoint:
```
HTTP/1.1 200 OK
{"status":"ok","message":"Klaviyo OAuth router is mounted"}
```

### For `/oauth/start-simple` and `/oauth/start`:
```
HTTP/1.1 302 Found
Location: https://www.klaviyo.com/oauth/authorize?response_type=code&client_id=...
```

## Troubleshooting

If you get a 404:
1. Check that the server is running with the correct main file:
   ```bash
   uvicorn main_firestore:app --port 8000 --host localhost --reload
   ```

2. Verify the router is imported and included in `main_firestore.py`:
   - Import: `from app.api.integrations.klaviyo_oauth import router as klaviyo_oauth_router`
   - Include: `app.include_router(klaviyo_oauth_router, prefix="/api/integrations/klaviyo")`

3. Check for import errors in the server logs

4. Run the test script:
   ```bash
   python test_oauth_endpoint.py
   ```

## Frontend Button Test

1. Navigate to http://localhost:8000/admin/clients
2. Click the "🔗 Connect Klaviyo" button
3. You should be redirected to Klaviyo's OAuth consent page

If the button shows an error:
- Check browser console for JavaScript errors
- Verify the URL in the button's onClick handler matches the endpoint
- Ensure you're using `window.location.href` not `fetch()`