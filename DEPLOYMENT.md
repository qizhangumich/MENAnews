# GitHub Deployment Guide

Deploy MENA News Ranking Service to GitHub Actions for automated scheduling.

## Schedule (Beijing Time GMT+8)

| Task | Schedule | Beijing Time |
|------|----------|--------------|
| News Collection | Every 6 hours | 08:00, 14:00, 20:00, 02:00 |
| Daily Digest | Every day | 08:00 |
| Weekly Digest | Every Friday | 08:00 |

## Step 1: Push to GitHub

```bash
# Add the remote repository
git remote add origin https://github.com/qizhangumich/MENAnews.git

# Push to GitHub
git push -u origin master
```

## Step 2: Configure GitHub Secrets

Go to your repository **Settings > Secrets and variables > Actions** and add these secrets:

### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Full Firebase credentials JSON content | `{ "type": "service_account", ... }` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | `menanews-4a30c` |
| `FIRESTORE_COLLECTION` | Firestore collection name | `news` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | `8565710049:AAGk8...` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | `123456789` |
| `SMTP_HOST` | SMTP server address | `smtp.163.com` |
| `SMTP_PORT` | SMTP port | `465` |
| `SMTP_USER` | SMTP username (email) | `your_email@163.com` |
| `SMTP_PASSWORD` | SMTP password | `your_password` |
| `EMAIL_RECIPIENTS` | Comma-separated email addresses | `user@example.com,other@example.com` |
| `OPENAI_API_KEY` | OpenAI API key for bilingual summaries | `sk-proj-...` |

### How to Get Each Secret

#### Firebase Service Account
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Project Settings > Service Accounts
3. "Generate New Private Key"
4. Copy the **entire JSON content** as the secret value

#### Telegram Bot Token
1. Chat with [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token (e.g., `8565710049:AAGk8...`)

#### Telegram Chat ID
1. Chat with your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find your `chat.id` in the response

#### SMTP Credentials (163.com)
- **Host**: `smtp.163.com`
- **Port**: `465` (SSL) or `587` (TLS)
- **User**: Your 163.com email address
- **Password**: Your email password or authorization code

#### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-proj-...`)

## Step 3: Verify Deployment

### Check Workflow Status
1. Go to **Actions** tab in your GitHub repo
2. Click on "MENA News Scheduler"
3. View recent workflow runs

### Manual Trigger
You can manually trigger all jobs:
1. Go to **Actions** tab
2. Select "MENA News Scheduler"
3. Click "Run workflow" button

## Step 4: Monitor Logs

If a job fails:
1. Click on the failed workflow run
2. Click on the failed job (e.g., "weekly-digest")
3. Expand the steps to see error logs
4. Download log artifacts if available

## Troubleshooting

### Workflow not triggering
- Check GitHub Actions is enabled in repo settings
- Verify the cron schedule syntax
- Check the "Actions" permissions in repository settings

### Firebase authentication error
- Verify `FIREBASE_SERVICE_ACCOUNT_JSON` contains valid JSON
- Check `FIREBASE_PROJECT_ID` matches your Firebase project

### Telegram not sending
- Verify bot token is correct
- Verify chat ID is correct
- Make sure you've started a conversation with your bot

### Email not sending
- Verify SMTP credentials are correct
- For 163.com, use the authorization code, not the login password
- Check if SMTP port is correct (465 for SSL, 587 for TLS)

### Weekly digest timeout
- The weekly digest may take 10-20 minutes due to OpenAI API calls
- The workflow has a 60-minute timeout configured
- If timing out, consider reducing the number of articles

## Security Notes

- Never commit secrets to your repository
- Use GitHub Secrets for all sensitive credentials
- Rotate API keys periodically
- Monitor workflow logs for accidental secret exposure
