# Influencer Discovery MVP Design

## Context

The user is responsible for overseas media work at Guangdong Advertising Group and wants an internal tool that reduces repetitive influencer discovery work. The team size is about 10 people. The tool should help users enter a topic, brand brief, or seed influencer link, then find suitable creators on TikTok, YouTube, and Instagram, summarize their recent content, expose public contact options, and help managers choose a shortlist.

This design treats the request as a new software product concept, not as a change to the existing HRL routing experiment code in this repository.

## Confirmed Requirements

- Target platforms: TikTok, YouTube, Instagram.
- Target regions: no region restriction.
- Matching criteria: field/topic match, follower count, view/play count, engagement rate.
- Ranking preference: data performance first; topic match is used as a threshold or secondary signal.
- Contact boundary: collect public business contact information and record DM entry points, but do not automatically send messages.
- Search output: standard workflow returns 20-50 creators; managers can select the best matches for deeper due diligence.
- Data acquisition preference: mixed approach using public data, search results, and pluggable APIs or low-cost third-party services.
- Monthly external tool/API budget: 0-3000 RMB.
- Product shape: lightweight MVP with internal web UI and spreadsheet export.
- Input modes: keyword, brand/product brief, and seed influencer links.
- Follow-up management: lightweight tracking with favorites, tags, assignment, notes, and status.
- Review output: both sortable tables and proposal-style creator cards.
- Language support: multilingual support with language detection, translation, and cross-language keyword expansion.
- Usage level: 20-100 searches per day, with standard results expected in 1-5 minutes when feasible.
- Deployment preference: local machine or lightweight cloud MVP first.
- Existing tools/data: no existing influencer platform or database; the first version must create a reusable creator database from scratch.
- Primary user: project/client managers reviewing candidate lists for proposal decisions.
- Timeline preference: as fast as possible; design assumes a 2-4 week usable MVP.

## Recommended Approach

Build a mixed-data MVP.

The first version should not try to become a full influencer CRM or a fully automated outreach platform. It should focus on discovery, scoring, shortlist review, public contact collection, lightweight follow-up state, and export. This balances speed, low budget, and practical usefulness for a 10-person internal team.

Rejected alternatives:

- Pure public-data MVP: fastest and cheapest, but TikTok and Instagram data stability would be weak and the tool would be harder to rely on long term.
- Buy mature influencer data platforms first: more stable, but likely exceeds the monthly budget and may delay internal workflow validation.

## Product Scope

The MVP is a 10-person internal creator discovery and screening tool.

Core workflow:

1. User enters a keyword, brand brief, or seed influencer link.
2. The system expands the query into multilingual keywords and platform-specific search terms.
3. The system finds candidates from TikTok, YouTube, Instagram, search engine results, public pages, and optional API/data-service connectors.
4. The system enriches each candidate with profile URL, follower count, recent content, views, engagement data, public business contact information, website/Linktree-style links, and DM entry point.
5. The system outputs 20-50 standard candidates ranked by data-performance-first scoring.
6. A manager selects a smaller shortlist for deep due diligence cards.
7. Users can favorite creators, add tags, assign owners, add notes, set status, and export tables or card reports.

Out of scope for MVP:

- Automatic DM sending.
- Contract, quote, payment, or invoice management.
- Full campaign CRM.
- Complex enterprise permissions.
- Multi-team approval flows.
- Full paid-media performance attribution.

## Data Flow

The system uses mixed data and caching instead of attempting real-time full-platform crawling.

1. Input parsing:
   - Parse keywords, brand/product brief, and seed profile links.
   - Extract topics, target audience hints, platform preferences, language keywords, exclusion terms, and seed creator signals.

2. Candidate discovery:
   - Use search engine results, platform public pages, YouTube Data API, and pluggable TikTok/Instagram connectors.
   - Store raw source evidence for traceability.

3. Data enrichment:
   - Normalize creator profiles across platforms.
   - Fetch or infer profile metadata, public contact links, recent content links, titles/descriptions, follower count, view/play count, and engagement signals.

4. Cache and database:
   - Save creator profiles and platform accounts.
   - Reuse cached records for repeated searches.
   - Refresh stale metrics instead of refetching everything.

5. Standard and deep analysis:
   - Standard analysis runs on 20-50 candidates.
   - Deep due diligence only runs on selected creators to reduce cost and latency.

6. Compliance boundary:
   - Record only public business contact information and public DM entry points.
   - Do not bypass login permissions.
   - Do not collect non-public personal information.
   - Do not send messages automatically.

## Scoring Logic

The score should use topic match as a gate and rank primarily by data performance.

Recommended standard score:

- Data performance: 75%
  - Recent average views or plays: 35%
  - Engagement rate: 25%
  - Follower count: 15%
- Topic match: 15%
  - Match against title, description, hashtags, bio, recent content summaries, and translated keywords.
  - Candidates below a minimum topic threshold are excluded or heavily downgraded.
- Contactability: 10%
  - Public business email, website, Linktree/Beacons-style profile, cooperation form, or DM entry point.

Platform metrics must be normalized by platform and search batch. TikTok plays, YouTube views, and Instagram engagement should not be compared as raw absolute numbers without normalization.

Deep due diligence cards should include:

- Representative recent content summary.
- Why the creator is recommended.
- Data highlights.
- Risk points, such as unstable topic fit, abnormal engagement, missing contact information, or recent content drift.
- Suggested contact channel.

## Interface Design

The confirmed interface structure has three primary screens:

1. Search and task creation:
   - Input box for keyword, brief, or seed creator link.
   - Platform toggles for TikTok, YouTube, and Instagram.
   - Multilingual expansion option.
   - Async task status: queued, searching, analyzing, complete.

2. Standard candidate list:
   - Sortable table with creator, platform, followers, recent views/plays, engagement rate, match score, contact method, and status.
   - Actions: favorite, assign, generate deep due diligence, export Excel, export review cards.

3. Deep due diligence card:
   - Creator identity, profile link, platform, follower count, contact options, status.
   - Recommendation reason, representative content, data highlights, risk points, suggested contact method, and tags.

The visual wireframe is stored at:

- `output/playwright/influencer-mvp-layout.png`
- `output/playwright/influencer-mvp-layout.html`

## Technical Architecture

Recommended MVP architecture:

- Internal web UI:
  - Search page, candidate list, creator detail page, due diligence card page, follow-up state, and export.

- Backend service:
  - Creates search tasks, coordinates data connectors, normalizes creator data, runs scoring, and exposes API endpoints to the UI.

- Async task queue:
  - Runs candidate discovery, enrichment, and AI analysis without blocking the UI.
  - Required for 20-100 searches per day and 1-5 minute target response time.

- Database:
  - Stores search tasks, creators, platform accounts, content samples, contact records, scoring outputs, notes, tags, assignments, and statuses.

- Connector layer:
  - YouTube official API connector.
  - Search engine connector.
  - TikTok connector, implemented conservatively because official APIs have approval and use-case limits.
  - Instagram/Meta connector, implemented as pluggable because Graph API access depends on account type, permissions, and app review.
  - Optional low-cost third-party data services can be added later without changing core business logic.

- AI analysis layer:
  - Multilingual keyword expansion.
  - Language detection.
  - Translation for summaries.
  - Topic thresholding.
  - Standard content summaries.
  - Deep due diligence card generation.

- Export layer:
  - Excel export for internal screening.
  - Card/report export for manager or client review.

Recommended deployment:

- Docker Compose on a local machine or lightweight cloud server for MVP.
- Split services later only if concurrency, data volume, or reliability needs justify it.

## Platform Notes

YouTube is the strongest official API fit for MVP. `search.list` can find video/channel/playlist results and has a cost of 100 quota units per call. `videos.list` can retrieve video statistics at lower cost. YouTube Data API projects have a default daily quota of 10,000 units.

TikTok official Display API is mainly for displaying an authorized TikTok user's profile and videos. TikTok Research API can query public video data but has approval and use-case restrictions. The MVP should not assume unrestricted commercial full-platform TikTok search through official APIs.

Instagram/Meta Graph API can support some discovery-style features such as Business Discovery, Hashtag Search, and recent media references, but access depends on account type, permissions, tokens, and app review. Instagram should be implemented as a pluggable connector so MVP delivery is not blocked by approval.

References:

- YouTube Data API `search.list`: https://developers.google.com/youtube/v3/docs/search/list
- YouTube Data API quota costs: https://developers.google.com/youtube/v3/determine_quota_cost
- TikTok Display API overview: https://developers.tiktok.com/doc/display-api-overview
- TikTok Research API Query Videos: https://developers.tiktok.com/doc/research-api-specs-query-videos/
- Instagram Business Discovery reference: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery
- Instagram Hashtag Search guide: https://developers.facebook.com/docs/instagram-api/guides/hashtag-search

## Data Model

Core entities:

- User:
  - Name, email/login, role, active status.

- SearchTask:
  - Input text, input type, platforms, language options, status, created by, timestamps, error summary.

- Creator:
  - Canonical creator record, display name, primary topics, language, country/region hints, created/updated timestamps.

- PlatformAccount:
  - Creator ID, platform, handle, profile URL, follower count, profile bio, avatar URL, account type hints, last refreshed timestamp.

- ContentSample:
  - Platform account ID, content URL, title/description/caption, hashtags, posted time, view/play count, like count, comment count, share count, language, translated summary.

- ContactRecord:
  - Creator or platform account ID, type, value or URL, source URL, confidence, public/private flag, last verified timestamp.

- ScoreResult:
  - Search task ID, creator ID, platform account ID, normalized metrics, topic score, data performance score, contactability score, final score, reasons, risks.

- FollowUp:
  - Creator ID, owner, status, tags, notes, assignment, timestamps.

## Development Plan

Week 1: clickable MVP shell and base data model.

- Build internal web UI for search task, candidate list, creator detail, favorites, notes, status.
- Create database schema.
- Implement manual import/entry path so the workflow can be tested before all connectors are ready.
- Implement basic Excel export.
- Acceptance: users can create a search-like task, view/edit candidate records, and export a table.

Week 2: YouTube and search engine MVP.

- Implement YouTube Data API connector.
- Implement search engine based candidate discovery.
- Implement basic scoring.
- Acceptance: a topic search returns 20-50 YouTube/web candidates with normalized data and export.

Week 3: TikTok/Instagram connector interfaces and caching.

- Add TikTok and Instagram connector interfaces.
- Implement conservative public profile/contact extraction where legally and technically safe.
- Add cache, stale-data refresh, retries, and failure logging.
- Acceptance: all three platforms can contribute candidate links or profiles, even if data completeness differs by platform.

Week 4: AI analysis and deep due diligence cards.

- Implement multilingual keyword expansion.
- Implement content summaries and translated summaries.
- Implement deep due diligence card generation.
- Acceptance: manager can select 3-5 creators from a standard result list and generate review-ready cards.

## MVP Acceptance Criteria

- 10 users can use the system through individual or shared internal access.
- The system can handle 20-100 searches per day in MVP conditions.
- A standard search returns progress and aims to finish in 1-5 minutes when source availability permits.
- Each standard search returns 20-50 candidates.
- Candidate rows include platform, profile link, followers, views/plays, engagement rate, contact/DM entry, score, and short reason.
- Managers can select a shortlist and generate deep due diligence cards.
- Users can favorite, tag, assign, add notes, and set follow-up status.
- Excel export works for standard candidate lists.
- The system records source URLs and extraction timestamps for auditability.

## Risks and Mitigations

- TikTok and Instagram data instability:
  - Keep connectors pluggable.
  - Cache successful records.
  - Provide partial results instead of failing the full task.

- API approval or quota limits:
  - Start with YouTube and search engine results.
  - Keep TikTok/Instagram as incremental connectors.
  - Add per-source usage tracking and fallback behavior.

- Low budget:
  - Use AI only for high-value steps.
  - Run deep due diligence only on selected creators.
  - Cache summaries and translations.

- Multilingual quality:
  - Start with query expansion, language detection, and summary translation.
  - Improve cross-language retrieval later based on actual usage.

- Manager trust:
  - Always show match reasons, source URLs, and risk points.
  - Avoid opaque scoring-only output.

## Open Implementation Decisions

These do not block the design, but should be decided before implementation planning:

- Exact technology stack for web UI and backend.
- Whether the MVP uses individual logins or a shared internal account first.
- Which search engine provider/API to use under the 0-3000 RMB/month budget.
- Whether the first TikTok/Instagram connector uses public page extraction, a low-cost third-party API, or manual profile import plus enrichment.
- Preferred export format for review cards: HTML/PDF, PowerPoint, or spreadsheet tabs.

## Spec Self-Review

- Empty-field scan: no unfinished markers or incomplete sections remain.
- Internal consistency: the scope, scoring, data flow, interface, and timeline all target the same mixed-data MVP.
- Scope check: this is focused enough for one MVP implementation plan; full CRM and automatic outreach are explicitly out of scope.
- Ambiguity check: the most uncertain platform API areas are documented as connector risks and not assumed as guaranteed capabilities.
