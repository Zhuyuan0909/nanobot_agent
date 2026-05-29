# CloudSync API FAQ

## How do I get an API key?

1. Go to **Settings > API > Create API Key**
2. Give your key a name (e.g., "Production Server", "Dev Testing")
3. Select permissions: Read, Write, or Admin
4. Click **Generate**
5. Copy and save the key immediately — it won't be shown again

API keys have the format: `cs_live_` followed by 32 alphanumeric characters.

## Authentication method

All API requests require an `Authorization` header:

```
Authorization: Bearer cs_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Example using curl:

```bash
curl -H "Authorization: Bearer cs_live_xxx" \
     https://api.cloudsync.example.com/v1/sources
```

Never expose your API key in client-side code or version control.

## Rate limits

| Plan | Requests per minute | Requests per day |
|------|---------------------|--------------------|
| Free | 10 | 1,000 |
| Starter | 60 | 10,000 |
| Professional | 300 | 50,000 |
| Enterprise | 1,000 | Unlimited |

Rate limit headers are included in every response:

- `X-RateLimit-Limit`: Your plan's per-minute limit
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `X-RateLimit-Reset`: Unix timestamp when the window resets

If you exceed the limit, you'll receive a `429 Too Many Requests` response.

## What does 429 Too Many Requests mean?

You have exceeded your plan's API rate limit. Options:

1. Wait for the rate limit window to reset (check the `X-RateLimit-Reset` header)
2. Implement exponential backoff in your integration
3. Upgrade to a higher plan with more requests/minute
4. Batch multiple operations into a single request where possible

## API endpoints overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/sources` | GET | List connected data sources |
| `/v1/syncs` | POST | Trigger a data sync job |
| `/v1/syncs/{id}` | GET | Check sync job status |
| `/v1/data/{source}` | GET | Query synced data |
| `/v1/webhooks` | POST | Register a webhook endpoint |

Full API reference: https://docs.cloudsync.example.com/api

## How do I set up a webhook?

CloudSync supports webhooks for event notifications (sync completed, sync failed, schema changed).

1. Go to **Settings > API > Webhooks**
2. Click **Add Webhook**
3. Enter your endpoint URL
4. Select the events you want to subscribe to
5. Optionally set a secret for HMAC signature verification

We send a verification challenge first. Your endpoint must respond with `200 OK` and the challenge token to confirm.

## What SDKs are available?

- **Python**: `pip install cloudsync-sdk`
- **JavaScript/Node.js**: `npm install cloudsync-sdk`
- **Java**: Maven artifact `com.cloudsync:sdk:1.x`
- **Go**: `go get github.com/cloudsync/sdk-go`

SDK documentation: https://docs.cloudsync.example.com/sdk

## Common API error codes

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad request | Check your request body for missing or invalid fields |
| 401 | Unauthorized | Check your API key is valid and not expired |
| 403 | Forbidden | Your API key does not have the required permissions |
| 404 | Not found | The requested resource does not exist |
| 429 | Rate limited | Slow down your requests or upgrade your plan |
| 500 | Server error | Something went wrong on our side — retry with backoff |
