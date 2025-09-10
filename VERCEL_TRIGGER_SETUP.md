# Rivvy Webhook Trigger Setup Guide

This guide will help you create a Vercel-based webhook trigger that bridges Rivvy Observer and your GitHub Actions.

## 🎯 **What This Does**

- Receives webhooks from Rivvy Observer when MyDIY.ie products change
- Validates the webhook payload
- Forwards the data to GitHub's `repository_dispatch` API
- Triggers your GitHub Action to update product data

## 🚀 **Step 1: Create the Project**

```bash
# Navigate to your parent directory
cd /Users/emmett.maher/Downloads

# Create new project directory
mkdir rivvy-trigger
cd rivvy-trigger

# Initialize Next.js project
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

## 📁 **Step 2: Create the API Route**

Create `src/app/api/llms-full-trigger/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // Verify authorization header
    const auth = request.headers.get('authorization');
    if (auth !== `Bearer ${process.env.TRIGGER_SECRET}`) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    
    // Forward to GitHub's repository_dispatch API
    const gh = await fetch(`https://api.github.com/repos/${process.env.GH_OWNER}/${process.env.GH_REPO}/dispatches`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.GH_TOKEN}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        event_type: 'product-updated',
        client_payload: {
          action: body.action || 'product-updated',
          urls: body.urls || [],
          site: body.site || 'https://www.mydiy.ie',
          changes: body.changes || [],
          timestamp: new Date().toISOString()
        }
      })
    });

    if (!gh.ok) {
      const error = await gh.text();
      console.error('GitHub API error:', error);
      return NextResponse.json({ ok: false, error }, { status: 500 });
    }
    
    console.log('✅ Successfully triggered GitHub Action');
    return NextResponse.json({ ok: true, message: 'GitHub Action triggered' });
    
  } catch (error) {
    console.error('Trigger error:', error);
    return NextResponse.json({ ok: false, error: 'Internal server error' }, { status: 500 });
  }
}
```

## 🔧 **Step 3: Environment Variables**

Create `.env.local`:

```bash
# .env.local
TRIGGER_SECRET=your-random-secret-key-here
GH_OWNER=your-github-username
GH_REPO=rivvy_create-llmstxt
GH_TOKEN=ghp_your-github-token-here
```

## 📦 **Step 4: Update package.json**

Ensure your `package.json` has the right scripts:

```json
{
  "name": "rivvy-trigger",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "^18",
    "react-dom": "^18"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "eslint": "^8",
    "eslint-config-next": "14.0.0",
    "typescript": "^5"
  }
}
```

## 🚀 **Step 5: Deploy to Vercel**

```bash
# Install Vercel CLI if you haven't already
npm i -g vercel

# Deploy to production
vercel --prod
```

## 🔑 **Step 6: Configure Environment Variables in Vercel**

1. Go to your Vercel dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Add these variables:
   - `TRIGGER_SECRET`: Your random secret key
   - `GH_OWNER`: Your GitHub username
   - `GH_REPO`: `rivvy_create-llmstxt`
   - `GH_TOKEN`: Your GitHub Personal Access Token

## 🧪 **Step 7: Test the Trigger**

```bash
# Test with curl
curl -X POST https://your-vercel-url.vercel.app/api/llms-full-trigger \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-random-secret-key-here" \
  -d '{
    "action": "product-updated",
    "urls": ["https://www.mydiy.ie/products/test-product.html"],
    "site": "https://www.mydiy.ie"
  }'
```

## 🔗 **Step 8: Configure Rivvy Observer**

Point the Observer webhook to:
```
https://your-vercel-url.vercel.app/api/llms-full-trigger
Authorization: Bearer your-random-secret-key-here
```

## 📋 **Step 9: Update Your GitHub Action**

Add this to `.github/workflows/update-products.yml` in your main repo:

```yaml
name: Update Product Data
on:
  repository_dispatch:
    types: [product-updated, product-added, product-removed]
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          
      - name: Update products
        env:
          FIRECRAWL_API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
        run: |
          echo "Action: ${{ github.event.action }}"
          echo "URLs: ${{ github.event.client_payload.urls }}"
          
          case "${{ github.event.action }}" in
            "product-added")
              python3 scripts/update_llms_sharded.py https://www.mydiy.ie \
                --added '${{ github.event.client_payload.urls }}'
              ;;
            "product-updated")
              python3 scripts/update_llms_sharded.py https://www.mydiy.ie \
                --changed '${{ github.event.client_payload.urls }}'
              ;;
            "product-removed")
              python3 scripts/update_llms_sharded.py https://www.mydiy.ie \
                --removed '${{ github.event.client_payload.urls }}'
              ;;
          esac
          
      - name: Deploy to ElevenLabs
        run: |
          rsync -av --update out/llms-full.*.txt ${{ secrets.ELEVENLABS_SERVER }}:/data/
```

## 🔒 **Security Notes**

- The `TRIGGER_SECRET` should be a long, random string (use a password generator)
- Never commit your `.env.local` file
- Use environment variables in Vercel dashboard
- Your GitHub token needs `repo` scope
- Consider using GitHub's fine-grained personal access tokens

## 🎯 **Complete Flow**

1. **Rivvy Observer** detects changes on MyDIY.ie
2. **Observer** sends webhook to your Vercel trigger URL
3. **Trigger** validates and forwards to GitHub's `repository_dispatch` API
4. **GitHub Action** runs your update script
5. **Files updated** and deployed to ElevenLabs

## 🚨 **Troubleshooting**

### Common Issues:

1. **401 Unauthorized**: Check your `TRIGGER_SECRET` matches
2. **GitHub API Error**: Verify your `GH_TOKEN` has correct permissions
3. **Webhook Not Triggering**: Check Vercel function logs
4. **Action Not Running**: Verify the `event_type` matches your workflow

### Debug Commands:

```bash
# Check Vercel function logs
vercel logs

# Test webhook locally
npm run dev
curl -X POST http://localhost:3000/api/llms-full-trigger \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret" \
  -d '{"action": "test"}'
```

## 📚 **Additional Resources**

- [Vercel Functions Documentation](https://vercel.com/docs/functions)
- [GitHub repository_dispatch API](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [Next.js API Routes](https://nextjs.org/docs/api-routes/introduction)

## ✅ **Checklist**

- [ ] Project created and deployed to Vercel
- [ ] Environment variables configured
- [ ] API route tested manually
- [ ] Rivvy Observer configured
- [ ] GitHub Action updated
- [ ] End-to-end flow tested

---

**Once you've completed these steps, your webhook trigger will be ready to bridge Rivvy Observer and your GitHub Actions! 🚀**
