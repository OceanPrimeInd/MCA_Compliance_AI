# Compliance AI — Frontend

React + Vite frontend for the Compliance AI backend, deployable to Netlify or Vercel
(a Streamlit app can't be — Netlify/Vercel only serve static sites, and Streamlit needs a
persistent Python server like your Render backend).

## 1. Local development

```bash
npm install
cp .env.example .env.local
# edit .env.local if your backend URL differs
npm run dev
```

## 2. Set up Supabase auth (one-time, in Supabase's dashboard)

You mentioned you already have Supabase access from your boss — use that existing
project rather than creating a new one, unless you specifically want this isolated.

1. Go to your project → **Authentication → Providers** → confirm **Email** is enabled
   (it is by default).
2. Decide whether you want email confirmation required before first login:
   **Authentication → Settings → Email Auth** → toggle "Confirm email" on/off.
   Turn it **off** for a fast internal beta (testers can sign up and use it
   immediately); turn it **on** before a public launch.
3. Go to **Project Settings → API** and copy:
   - **Project URL** → this is `VITE_SUPABASE_URL`
   - **anon public** key → this is `VITE_SUPABASE_ANON_KEY`
   (Never use the `service_role` key in the frontend — that one bypasses all
   security rules and must only ever live server-side.)
4. Put both into `.env.local`:
   ```
   VITE_SUPABASE_URL=https://your-project-ref.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-public-key
   ```
5. **Create the conversations table**: open **SQL Editor** in the Supabase
   dashboard → **New query** → paste the contents of
   `supabase/migrations/001_conversations.sql` → **Run**. This creates one table
   (`conversations`) with Row Level Security enabled, so each user can only ever
   read or write their own rows — the app's `anon` key can't be used to see
   anyone else's history even if someone inspected the network requests.
6. **Run the second migration**: `supabase/migrations/002_add_user_email.sql`,
   same way. This adds a `user_email` column so you can see who had which
   conversation directly in **Table Editor → conversations**, without needing
   to join against the protected `auth.users` table each time. (You can also
   always see the full account list at **Authentication → Users**.)

Conversation history now lives in Postgres, not `localStorage` — it syncs across
devices and survives a cleared browser, which matters once real beta testers are
using this on their own laptops/phones.

**If you use the magic-link option**, also set your deployed URL in
**Authentication → URL Configuration → Site URL** (and add it to **Redirect URLs**
too) once you deploy to Netlify/Vercel — otherwise the link in the email will
redirect back to `localhost` instead of your live site.

## 3. Required: enable CORS on your FastAPI backend

Right now your backend only ever received requests from the same Render network or
localhost. Once the frontend is on Netlify/Vercel, the browser will block requests
unless the backend explicitly allows that origin. In `backend/app/main.py`, add:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://YOUR-SITE-NAME.netlify.app",
        "https://YOUR-SITE-NAME.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Add this once, right after `app = FastAPI(...)`. Redeploy the backend before testing
the deployed frontend, or every request will fail with a CORS error in the browser
console (not a 500 — it'll look like the request never reached your server).

## 4. Deploy to Netlify

```bash
npm install -g netlify-cli   # if you don't have it
netlify deploy --prod
```
Or via the Netlify dashboard: "Add new site" → connect your GitHub repo →
build command `npm run build`, publish directory `dist`.

Either way, set the environment variable in **Site settings → Environment variables**:
```
VITE_BACKEND_URL=https://mca-compliance-ai.onrender.com
```

## 5. Deploy to Vercel

```bash
npm install -g vercel
vercel --prod
```
Or via the Vercel dashboard: "Add New Project" → import your GitHub repo →
framework preset auto-detects Vite.

Set the same environment variable in **Project Settings → Environment Variables**:
```
VITE_BACKEND_URL=https://mca-compliance-ai.onrender.com
```

Vite only reads `VITE_`-prefixed env vars, and only at build time — if you change it,
trigger a redeploy.

## What changed from the Streamlit version

- **Conversation history**: was SQLite via `storage.py` on the server; now `localStorage`
  in the browser (`src/lib/storage.js`). This means history is per-browser, not shared
  across devices — a fair tradeoff for a static site with no database. If you later want
  cross-device history, that needs a small backend endpoint plus a real DB, not something
  a static host can do alone.
- **Everything else** (chat UI, clause citation chips, confidence coloring, verified/cached
  badges, example questions) is a direct port — same behavior, same backend contract
  (`POST /ask` with `{"question": "..."}`).
