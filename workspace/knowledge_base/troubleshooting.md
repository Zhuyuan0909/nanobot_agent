# CloudSync Troubleshooting FAQ

## Data sync is stuck or not completing

Common causes and solutions:

1. **Source API rate limit**: Your data source (e.g., Salesforce, HubSpot) may be throttling requests. Wait 5-10 minutes and try again.

2. **Authentication expired**: The OAuth token for your data source may have expired. Go to **Data Sources > [Source Name] > Reconnect** to refresh.

3. **Large data volume**: Initial syncs for large datasets can take hours. Check the estimated time in the sync dashboard. You can continue using the platform while syncs run in the background.

4. **Schema mismatch**: If the source schema changed, go to **Data Sources > [Source Name] > Refresh Schema** to update.

## I can't log in to my account

1. Check you are using the correct email address
2. Try resetting your password (see general FAQ)
3. Check if your company uses SSO — ask your admin for the SSO login URL
4. Clear your browser cache and cookies, then try again
5. Try a different browser or incognito/private window

If none of these work, the issue may be account-related. I'll help you create a support ticket.

## Data looks incorrect or missing

1. **Refresh the page**: Sometimes the UI cache shows stale data. Press Ctrl+F5 (Cmd+Shift+R on Mac) for a hard refresh.

2. **Check sync status**: Go to **Sync Jobs** to see if the latest sync completed successfully. A failed sync means the data shown is from the last successful run.

3. **Filter or query issue**: If using a custom API query or dashboard filter, double-check the filter conditions. Try removing all filters to see if data appears.

4. **Timezone mismatch**: Data timestamps are stored in UTC. Your dashboard may display in your local timezone (configurable in **Settings > Profile > Timezone**).

## Why is my dashboard loading slowly?

Performance issues may be caused by:

1. **Too many widgets**: More than 20 widgets on a single dashboard degrades performance. Split into multiple dashboards.

2. **Large date range**: Querying 12+ months of data loads millions of rows. Narrow the date range for faster loading.

3. **Complex calculated fields**: Custom metrics with nested calculations are expensive. Simplify where possible or pre-aggregate.

4. **Browser resources**: Close unused tabs. Ensure at least 4GB RAM is available. Try Chrome or Edge for best compatibility.

## Error: "Connection refused" when adding a data source

This means CloudSync could not reach your data source. Check:

1. Your firewall is not blocking outbound connections from our IP ranges (see https://docs.cloudsync.example.com/network)
2. The data source URL is correct and accessible from the public internet
3. If using a self-hosted database, ensure it is exposed via a public IP or use our CloudSync Bridge agent
4. Proxy settings are configured in **Settings > Network** if your organization uses a proxy

## Mobile app issues

1. **App crashes on startup**: Uninstall and reinstall the app. Ensure your OS is updated to the latest version.
2. **Notifications not working**: Check app notification permissions in your phone settings. Check **Settings > Notifications** in the app.
3. **Data not syncing on mobile**: Pull down to refresh. Check your internet connection. Mobile app refreshes data every 5 minutes automatically.

Supported mobile platforms: iOS 15+, Android 11+

## Error message: "CS-ERR-5001" or similar codes

- **CS-ERR-5001**: Internal server error. Wait 2 minutes and retry. If persistent, create a ticket.
- **CS-ERR-4003**: Permission denied. Your account role does not have access to this resource. Contact your team admin.
- **CS-ERR-4007**: Resource quota exceeded. You have reached your plan's limit. Upgrade your plan or delete unused resources.
- **CS-ERR-4012**: Export too large. Your data export exceeds the 100MB limit. Apply filters to reduce size or split into multiple exports.
