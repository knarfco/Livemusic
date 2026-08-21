# Live Music — Space Coast

A standalone live music calendar. Venue managers log in and edit their own
weekly schedule directly; the public page shows what's playing tonight
(and the next 6 nights) across every venue, updated the instant a venue
saves — no rebuild, no zip upload, no waiting.

Three pages, no build step, no server:
- `index.html` — public page anyone can see, no login
- `login.html` — venue manager signs in
- `dashboard.html` — venue manager's own editable weekly schedule

## One-time setup (once the Supabase project exists)

1. **Run the schema.** Supabase dashboard → **SQL Editor** → **New query** →
   paste in everything from `schema.sql` in this repo → **Run**. This
   creates the two tables (`venues`, `shows`) and the security rules that
   keep a venue from ever editing another venue's schedule.
2. **Fill in `config.js`.** Supabase dashboard → **Project Settings** → **API**.
   Copy the "Project URL" and the "anon public" key into the two blanks in
   `config.js`. These are safe to be public — they only work in combination
   with the security rules from step 1.
3. **Open `index.html`** in a browser (or upload the whole folder anywhere
   that serves static files) — the public page should load and just show
   "No live music posted for this day yet" until a venue is added.

## Adding a venue (do this once per venue that signs on)

There's no public sign-up — matches how you're already vetting businesses
personally. Two steps, both in the Supabase dashboard:

1. **Authentication → Users → Add user.** Enter the venue's email and set a
   password (this is the password you're handing them).
2. **Table Editor → venues → Insert row.** Fill in `name`, a `slug` (e.g.
   `the-tidal-table`), `city`, and paste that user's ID (shown on the Users
   page) into `owner_user_id`.

That venue can now go to `login.html`, sign in, and edit their own week.

## Not done yet

- Visual styling matches CocoaBeachToday's colors loosely but isn't wired
  into that site's actual header/nav — this is still fully standalone
- No "forgot password" flow yet (reset from the Supabase dashboard for now)
- Attaching this to cocoabeachtoday.com (as a linked page, or folded into
  the next site zip) — decide once this is tested and working
