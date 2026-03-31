# Shop INTEX Prep - Cursor Handoff

This file helps a new Cursor chat quickly understand project context after moving this folder to a local path.

## Current status

- Stack: Next.js app in `web` (App Router, TypeScript).
- Objective: complete Part 1 web app + Part 2 CRISP-DM notebook for class integrated project.
- Data source now: temporary in-memory store for MVP click-through.
- Real target data source: `shop.db` -> Supabase Postgres (then Vercel deployment).

## Implemented so far (Part 1 MVP pages/actions)

- `web/src/app/page.tsx`
  - Select Customer screen.
- `web/src/app/customer/[id]/page.tsx`
  - Customer dashboard + order history.
- `web/src/app/customer/[id]/new-order/page.tsx`
  - Place new order form.
- `web/src/app/warehouse/page.tsx`
  - Late Delivery Priority Queue page.
  - Run Scoring button.
  - Pipeline prediction output display section.
- `web/src/app/api/orders/route.ts`
  - Saves new order (currently to in-memory store).
- `web/src/app/api/scoring/run/route.ts`
  - Runs scoring (currently in-memory simulation) and refreshes queue.
- `web/src/lib/shop-store.ts`
  - Temporary in-memory data layer for demo flow.
- `web/src/app/layout.tsx`
  - Basic nav/header for app.
- `web/README.md`
  - Updated with MVP feature list.

## Why installs failed earlier

- The project was in Google Drive.
- `npm install` produced archive/file-write errors (`tar`, `EBADF`), likely from sync interference.
- Recommended fix: run project from a local non-synced folder (for example `C:\dev\Shop INTEX Prep`).

## Immediate next steps

1. Move/copy this full folder to local disk (non-synced).
2. Open local folder in Cursor.
3. In `web`, run:
   - `npm install`
   - `npm run dev`
4. Verify all current pages and flows.
5. Replace `shop-store` with real DB access:
   - First local SQLite read parity checks (`shop.db`).
   - Then Supabase Postgres migration and app query wiring.
6. Keep `Run Scoring` + queue display, but wire it to real pipeline outputs.

## Assignment alignment reminders

- Web app must include:
  - Select Customer (no auth)
  - Customer dashboard
  - New order save
  - Order history
  - Late Delivery Priority Queue (top 50)
  - Run Scoring button
  - Visible prediction results on site
- Notebook must predict `orders.is_fraud` (CRISP-DM end-to-end).

## Copy-paste prompt for new Cursor chat

Use this prompt in a new chat after opening the local folder:

```text
I moved this project to a local folder and need you to continue implementation.

Context:
- This is my IS 455 integrated project prep.
- App is in `web` (Next.js + TypeScript App Router).
- `shop.db` is in the project root.
- The app currently has an MVP UI and API routes implemented using an in-memory store in `web/src/lib/shop-store.ts`.
- Required app features are: Select Customer, dashboard, new order save, order history, late-delivery queue top 50, Run Scoring button, and visible prediction output on the site.
- Notebook deliverable predicts `orders.is_fraud` (notebook work can come after web app wiring).

What I want now:
1) Verify app runs locally (`npm install`, `npm run dev`) and fix any compile/runtime issues.
2) Replace in-memory data with real data access mapped to `shop.db` schema.
3) Prepare migration path to Supabase Postgres and keep the same app pages/routes.
4) Wire Run Scoring + queue/prediction display to persisted scoring output tables.
5) Keep changes incremental and explain each step clearly.

Please start by inspecting the existing files in `web/src` and propose the smallest safe next implementation step, then execute it.
```
