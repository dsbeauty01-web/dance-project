#!/usr/bin/env bash
# maya-ops/meta-review/exchange_token.sh
# Long-lived token exchange for Maya Live (Meta Graph v26.0).
#   short-lived user token --(fb_exchange_token)--> long-lived user token (~60d)
#   long-lived user token --(/me/accounts)-------> long-lived Page token
# Writes META_USER_TOKEN_LL and META_PAGE_TOKEN_LL back into .maya/meta.env.
# Prints only token *validity + expiry* (via debug_token), never the tokens.
# KEYS LAW: .maya/meta.env is never committed.
set -euo pipefail
ENV="${1:-$HOME/.maya/meta.env}"
GV="v26.0"
[ -f "$ENV" ] || { echo "no env at $ENV"; exit 1; }
# Read a key WITHOUT sourcing (the file has a UTF-8 BOM and parens in comments that
# break `.`): strip BOM, take the last matching KEY=VALUE, trim CR.
getenv() { sed 's/\xEF\xBB\xBF//' "$ENV" | grep -E "^$1=" | tail -1 | cut -d= -f2- | tr -d '\r'; }

APP_ID="$(getenv META_APP_ID)";      [ -n "$APP_ID" ]     || { echo "META_APP_ID missing"; exit 1; }
APP_SECRET="$(getenv META_APP_SECRET)"; [ -n "$APP_SECRET" ] || { echo "META_APP_SECRET missing"; exit 1; }
PAGE_ID_V="$(getenv META_PAGE_ID)"
# prefer the freshest short-lived user token available
SHORT="$(getenv META_USER_TOKEN_NEW)"; [ -n "$SHORT" ] || SHORT="$(getenv META_USER_TOKEN)"
[ -n "$SHORT" ] || { echo "no user token in env"; exit 1; }

echo ">> exchanging short-lived user token for a long-lived one ..."
LL_USER=$(curl -sG "https://graph.facebook.com/$GV/oauth/access_token" \
  --data-urlencode "grant_type=fb_exchange_token" \
  --data-urlencode "client_id=$APP_ID" \
  --data-urlencode "client_secret=$APP_SECRET" \
  --data-urlencode "fb_exchange_token=$SHORT" \
  | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
[ -n "$LL_USER" ] || { echo "!! user-token exchange failed (check the short-lived token is fresh)"; exit 2; }

echo ">> fetching the long-lived Page token for META_PAGE_ID ..."
PAGE_ID="$PAGE_ID_V"; [ -n "$PAGE_ID" ] || { echo "META_PAGE_ID missing"; exit 1; }
LL_PAGE=$(curl -sG "https://graph.facebook.com/$GV/me/accounts" \
  --data-urlencode "access_token=$LL_USER" \
  | tr '{' '\n' | grep "\"id\":\"$PAGE_ID\"" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p' | head -1)
# fallback: page node directly
[ -n "$LL_PAGE" ] || LL_PAGE=$(curl -sG "https://graph.facebook.com/$GV/$PAGE_ID" \
  --data-urlencode "fields=access_token" --data-urlencode "access_token=$LL_USER" \
  | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

# write back (replace existing LL lines, then append fresh)
tmp=$(mktemp)
grep -vE '^META_(USER|PAGE)_TOKEN_LL=' "$ENV" > "$tmp" || true
{
  echo "META_USER_TOKEN_LL=$LL_USER"
  [ -n "$LL_PAGE" ] && echo "META_PAGE_TOKEN_LL=$LL_PAGE"
} >> "$tmp"
mv "$tmp" "$ENV"
echo ">> wrote META_USER_TOKEN_LL$([ -n "$LL_PAGE" ] && echo ' + META_PAGE_TOKEN_LL') to $ENV"

echo ">> verifying (debug_token) — expiry only, token not printed:"
APP_TOKEN="$APP_ID|$APP_SECRET"
curl -sG "https://graph.facebook.com/$GV/debug_token" \
  --data-urlencode "input_token=$LL_USER" \
  --data-urlencode "access_token=$APP_TOKEN" \
  | tr ',' '\n' | grep -E '"(is_valid|expires_at|data_access_expires_at|type)"' || true
