# Fix MythicMingle Page tasks → full MODERATE + MANAGE

**Problem (verified 2026-09-02):** on Page **MythicMingle** (`1100248523396303`) your access tasks
are only `MESSAGING, CREATE_CONTENT`. Replying to / moderating comments needs **MODERATE**, and
full API control needs **MANAGE**. Every other page you own (e.g. "Sela beauty") already has the
full set `MANAGE, CREATE_CONTENT, MODERATE, MESSAGING, ADVERTISE, ANALYZE`. Grant yourself the same
on MythicMingle.

Task → capability map: **MODERATE** = reply/hide/delete comments & manage community (what
`pages_manage_engagement` rides on). **MANAGE** = full control, needed for reliable API posting.

---

## Path A — New Pages Experience (most likely; do this first)
1. Go to **facebook.com** → switch/open as the Page **MythicMingle** (or open the Page directly).
2. **Settings** (left/⚙) → **New Pages experience** → **Page access**.
3. Under **People with Facebook access**, find **Refael Silanikove** → click it → **Edit**.
4. Turn **"Allow this person to have full control"** → **ON** (this grants MANAGE + MODERATE +
   everything).
5. Confirm with your password → **Save**.
   *(If it's already "partial", switching to full control is the fix. Full control = all tasks.)*

## Path B — Meta Business Suite / Business Settings (if the page is in a Business portfolio)
1. **business.facebook.com** → **Settings** (Business settings).
2. Left menu → **Accounts → Pages** → select **MythicMingle**.
3. Tab **People** (or "Assigned people") → select **Refael Silanikove** → **Edit access**.
4. Enable **Full control** (or individually toggle **Manage Page**, **Content**, **Community
   activity/Comments**, **Messages**) → **Save**.
   - "Community activity" / "Comments" = the MODERATE task. "Full control" = MANAGE.

## Path C — Classic Pages (only if you still see the old layout)
1. Page → **Settings → Page roles**.
2. Ensure your account is listed as **Admin** (not Editor/Moderator). Admin = all tasks.
3. If only Editor/Moderator, use "Assign a New Page Role" → set your account to **Admin** → Save.

---

## Verify it worked (re-mint token, then check tasks)
After changing the role, **generate a fresh token** (Graph API Explorer → User or Page → select
MythicMingle → add the 4 scopes → Generate) and send it — the app will confirm:
`GET /me/accounts` should now show MythicMingle with tasks including **MODERATE** and **MANAGE**.
Until it does, `pages_manage_engagement` won't be grantable and replies will 403.

> Note: full control changes can take a few minutes to propagate. If the new token still shows
> only MESSAGING+CREATE_CONTENT, wait ~10 min and regenerate.
