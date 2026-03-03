# Claude Code Instruction: MENA News Ranking + Daily Telegram + Weekly Email (Firestore only)

You are Claude Code. Build a production-ready Python service that reads news items from Google Firestore, computes relevance/importance scores using ONLY Firestore fields (title + description snippet + source + timestamps), then:
1) Sends a DAILY Telegram digest in Chinese at GMT+8 08:30 containing top 10 news from the past 24 hours.
2) Sends a WEEKLY email every Friday at GMT+8 08:30 containing:
   - Top 10 investment/SWF topics from the past 7 days (topic-based, not just articles)
   - PLUS a short “Fundraising in GCC + value-add services for portfolio companies” section in Chinese

Important: Do NOT scrape Firebase Console URLs (requires interactive auth). Use Firebase Admin SDK to query Firestore directly.

---

## 0) Inputs / Constraints

### Firestore
- Project: `menanews-4a30c`
- Database: `(default)`
- Collection: `news`
- Example fields per doc:
  - `title` (string)
  - `description` (string, HTML snippet with `<a href="...">`)
  - `source` (string)
  - `published_at` (timestamp)
  - `fetched_at` (timestamp)

### Output channels
- Telegram Bot: send to a fixed `CHAT_ID`
- Email: send to configured recipient list (use Resend or SendGrid; implement Resend by default)

### Timezone
- Schedule based on GMT+8 time zone (Asia/Shanghai)

### Language
- Output to user in Chinese.

### LLM usage
- Keep LLM usage optional. The system must work without LLM.
- If `OPENAI_API_KEY` exists, you may call OpenAI to produce nicer Chinese summaries; otherwise use rule-based Chinese templates.

---

## 1) Repo Structure (Create these files)

- `src/config.py`
- `src/firestore_client.py`
- `src/extract.py`
- `src/scoring.py`
- `src/daily_digest.py`
- `src/weekly_digest.py`
- `src/telegram_client.py`
- `src/email_client.py`
- `src/topic_cluster.py`
- `src/main.py`  (CLI entry)
- `requirements.txt`
- `README.md`
- `deploy/` (optional: Cloud Run + Scheduler examples)

---

## 2) Environment Variables

Required:
- `GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase_service_account.json`
- `FIREBASE_PROJECT_ID=menanews-4a30c`
- `FIRESTORE_COLLECTION=news`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`

Email (choose one):
- Resend:
  - `RESEND_API_KEY=...`
  - `EMAIL_FROM=...`
  - `EMAIL_TO=...` (comma separated)
- OR SendGrid equivalents if Resend not available.

Optional:
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-4.1-mini` (or default)
- `DIGEST_TIMEZONE=Asia/Shanghai`

---

## 3) Firestore Query Rules

### Daily window
- Pull docs where `published_at` >= now_in_tz - 24h
- If doc missing `published_at`, fallback to `fetched_at`

### Weekly window
- Pull docs where `published_at` >= now_in_tz - 7d (same fallback)

Limit:
- For performance, query max 500 docs for daily and max 2000 docs for weekly, then rank locally.

---

## 4) Extraction

### URL extraction from HTML description
Implement `extract_first_article_url(description_html: str) -> str | None`
- Parse `<a href="...">` values
- Choose the first link that is NOT the site homepage (e.g., not `https://www.arabianbusiness.com/` root)
- If none found, return None.

### Snippet text
Implement `html_to_text(description_html: str) -> str`
- Strip tags, collapse whitespace
- Truncate to 600–900 chars.

Store these computed fields in memory; optionally write back to Firestore (recommended but not required).

---

## 5) Scoring System (NO full article required)

Compute two scores per item:

### 5.1 RelevanceScore (0–100)
Matches user’s interest: investment, fundraising, family office, SWF.
Use title + snippet text.

Entity high-weight list (case-insensitive):
- mubadala, adia, adq, qia, pif, kia, oia
- sovereign wealth, swf
- family office

Topic keywords:
- fund, fundraising, lp, gp, private equity, pe, venture capital, vc, asset management
- ipo, listing, acquisition, merger, m&a, stake, buyout
- series a, series b, round, financing, investment, strategic investment

Rules (cap at 100):
- If mentions any SWF entity (mubadala/adq/adia/qia/pif/kia/oia): +45
- If contains “sovereign wealth” or “swf”: +35
- If contains “family office”: +30
- If contains fund/LP/GP/asset management/PE/VC: +20
- If contains deal terms (IPO/M&A/acquisition/stake/round/Series): +15
- If contains investment/financing: +10
- Otherwise: small base 0–10 depending on finance words (bank, bond, sukuk, central bank).

### 5.2 ImportanceScore (0–100)
Importance = SourceWeight + EventWeight + EntityWeight + FreshnessWeight

SourceWeight (0–40) default map (tunable):
- Reuters: 40
- Financial Times/WSJ/Bloomberg: 38
- The National: 30
- Zawya: 28
- Arabian Business/Gulf Business/Arab News: 22
- Others: 15

EventWeight (0–35) from keywords:
- IPO/listing/acquisition/merger/buyout: +35
- funding round/Series/strategic investment/stake: +30
- launch fund/new vehicle/mandate/AUM: +28
- regulation/sanctions/major policy: +25
- earnings/guidance/rating: +18
- partnership/expansion (generic): +12
- lifestyle/transport experience type: +5

EntityWeight (0–20):
- SWF entity: +20
- major bank: +12
- regulator/central bank: +10

FreshnessWeight (0–5) by hours since published:
- <6h +5
- 6–12h +4
- 12–24h +3
- 24–48h +2
- else +1

ImportanceScore = clamp(sum, 0, 100)

### 5.3 TotalScore
TotalScore = 0.65*RelevanceScore + 0.35*ImportanceScore

Filter rule:
- For daily telegram: keep items with RelevanceScore >= 25, then take top 10 by TotalScore.
- If fewer than 10 items, fill remaining by ImportanceScore (but still avoid obvious non-business lifestyle).

Dedup:
- Deduplicate by normalized title (lowercase, remove punctuation) and by same URL.

---

## 6) Daily Telegram Digest (GMT+8 08:30)

Output format (Chinese), 10 items max:

Header:
- `【中东投资情报｜过去24小时Top10】YYYY-MM-DD`

Each item:
- `1) 中文标题（可简单翻译）`
- `要点：一句话概括（从title+snippet压缩）`
- `标签：SWF / Fundraising / IPO / M&A / Policy / Markets（最多3个）`
- `来源：{source}｜时间：{published_at in GMT+8}`
- `链接：{url}`

Implementation:
- `telegram_client.send_message(text: str)` using Telegram Bot API `sendMessage`.
- Handle message length: if > 3500 chars, split into multiple messages.

Scheduling:
- Provide two runnable modes:
  - `python -m src.main daily`
  - `python -m src.main weekly`
- Then provide Cloud Scheduler examples to hit Cloud Run endpoint or run as Cloud Function.

---

## 7) Weekly Friday Email (Past 7 days, Top 10 topics)

Weekly email should be TOPIC-based, not just top 10 articles.

### 7.1 Topic clustering (no embeddings required)
Implement `topic_cluster.py`:
- Determine `event_type` from keywords: IPO / M&A / Funding / FundLaunch / Policy / Markets / Other
- Determine `top_entity` from entity list: Mubadala/ADIA/ADQ/QIA/PIF/KIA/OIA else None
- Build `topic_key = (top_entity or "General") + " | " + event_type + " | " + top_keyword`
  - `top_keyword` can be the strongest matched noun token among: "IPO", "acquisition", "fund", "family office", "rate", "bond", etc.
- Group items by `topic_key`

### 7.2 Topic ranking
For each topic group:
- `topic_score = sum(TotalScore)`
- `source_diversity_bonus = 5 if >=2 distinct sources, 10 if >=3`
- `volume_bonus = min(10, count)`
- Rank by `topic_score + bonuses`
Take top 10 topics.

### 7.3 Email content (Chinese)
Subject:
- `本周中东投资/主权基金要闻 Top10（YYYY-MM-DD）`

Body sections:
A) 本周Top10主题（每个主题）
- 主题标题（中文）
- 3–5条关键进展（bullet）
- 为什么重要（1–2句）
- 相关链接（2–3条，按TotalScore排序）

B) Fundraising in GCC + Value-Add for Portfolio Companies (Chinese)
Generate a concise, actionable section that includes:
1) Fundraising angles in GCC (SWF vs pension vs family office):
   - What they care about: governance, downside protection, co-invest, China exposure, regional industrial strategy
   - How to position: track record + access + co-invest pipeline + local value-add
2) Value-add service menu for portfolio companies in GCC across sectors:
   - Healthcare: regulatory pathway, distributor mapping, hospital groups, reimbursement, JV structures
   - Consumer: channel entry (KSA/UAE), e-commerce, local partners, halal/label compliance, marketing
   - Manufacturing: industrial zones, incentives, localization partners, procurement, EPC links
   - AI/Data center/Infrastructure/Tech: hyperscalers, sovereign cloud, offtake, permits, energy contracts, government stakeholders
3) 3 near-term actions next week (very concrete):
   - e.g., schedule 5 targeted LP touchpoints; propose 2 co-invest ideas; arrange 1 portfolio roadshow call; build GCC partner map.

No fluff. Provide specific GCC institutions as examples: Mubadala, ADIA, ADQ, PIF, QIA, KIA, OIA, and family offices.

Implementation:
- Build HTML email (simple clean) + plain-text fallback.
- Send via Resend API.

---

## 8) Writeback to Firestore (Recommended)
After computing, optionally update each doc with:
- `url`
- `snippet_text`
- `relevance_score`
- `importance_score`
- `total_score`
- `tags` (array)
This makes future runs faster and enables dashboards.

Make writeback idempotent:
- only update if missing or if fetched_at is newer.

---

## 9) README
Document:
- Setup steps
- How to run daily/weekly locally
- Deploy options:
  - Cloud Run service + Scheduler hitting `/run/daily` and `/run/weekly`
  - Or Cloud Functions gen2 with Scheduler triggers
- Env var examples
- Safety notes: do not log tokens/credentials

---

## 10) Deliverables
Implement all modules with type hints, error handling, logging.
Provide working CLI:
- `python -m src.main daily`
- `python -m src.main weekly`

At the end, print:
- number of docs processed
- top 10 titles selected
- telegram/email status

Now proceed to implement the full codebase.And you can run in full authorization, no need to get my further approval.