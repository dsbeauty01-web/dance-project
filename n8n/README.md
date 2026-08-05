# MAYA n8n LAYER — import and wire

Three workflows, in this order. Import each (n8n → Workflows → Import from File),
set its **CONFIG** node, attach credentials, activate.

> **KEYS LAW:** every key lives in the n8n credential store or the pod env. No key goes
> in a page, in a CONFIG field, or in this repo. The CONFIG nodes hold URLs only.

| # | file | what it does | credentials |
|---|---|---|---|
| W1 | `W1-youtube-chat-ingest.json` | polls the live chat every 5s, forwards only NEW messages | YouTube OAuth2 |
| W2 | `W2-priority-queue.json` | filter → classify → prioritize → dedupe → `/chat-in` | OpenAI |
| W3 | `W3-lead-capture.json` | buy-intent / trigger word → Google Sheet + director toast | Google Sheets (+ optional Telegram) |

## Wiring order (each step needs the previous one's URL)

1. **Import W3.** Set `CONFIG.sheet_id` to the client's sheet, `CONFIG.maya_api` to the
   maya-server URL. Activate. Copy its **production webhook URL**.
2. **Import W2.** Set `CONFIG.w3_webhook` to the URL from step 1 and `CONFIG.maya_api`.
   Attach the OpenAI credential to *Classify batch*. Activate. Copy its production URL.
3. **Import W1.** Set `CONFIG.w2_webhook` to the URL from step 2. Attach the YouTube
   OAuth2 credential to both HTTP nodes. Start the broadcast **first**, then activate —
   `Find active broadcast` needs a live broadcast to resolve `liveChatId`.

## The sheet

One tab named `Leads`, header row exactly:

```
ts | platform | name | handle | product | message
```

## What each workflow refuses to do

- **W1** never re-sends a message it has already forwarded (`seenIds` in static data).
  Without that, the API's replay window makes Maya answer the same viewer every 5s.
- **W2** never forwards `noise`, never forwards abuse, and never sends three copies of
  the same question — it sends one, naming all three askers.
- **W2** never fails silently: if the classifier call fails, everything is treated as a
  product question and marked `degraded` rather than dropped.
- **W3** captures on the classifier's `buy_intent` **or** a literal trigger word. Two
  independent paths, because the classifier can be wrong and "אני רוצה" cannot.

## Test without a live stream

```bash
# pretend W1 found two messages (replace with W2's production URL)
curl -X POST http://localhost:5678/webhook/maya-chat \
  -H 'content-type: application/json' \
  -d '{"messages":[{"platform":"youtube","msg_id":"t1","name":"דנה","text":"כמה עולה המשלוח?"},
                   {"platform":"youtube","msg_id":"t2","name":"יוסי","text":"אני רוצה!"}]}'
```

Expected: the first lands in the director's chat monitor; the second lands there **and**
as a row in the Leads sheet with a 🔥 LEAD toast in the director log.
