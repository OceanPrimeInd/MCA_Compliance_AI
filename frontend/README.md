# MCA Compliance AI — Frontend

React + Vite frontend for the MCA Compliance AI backend, deployable to Netlify or Vercel
(a Streamlit app can't be — Netlify/Vercel only serve static sites, and Streamlit needs a
persistent Python server like your Render backend).

## 1. Local development

```bash
npm install
cp .env.example .env.local
# edit .env.local if your backend URL differs
npm run dev
```

## 2. Required: enable CORS on your FastAPI backend

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

## 3. Deploy to Netlify

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

## 4. Deploy to Vercel

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
