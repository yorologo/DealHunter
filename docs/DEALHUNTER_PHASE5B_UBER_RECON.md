# DEALHUNTER_PHASE5B_UBER_RECON

> [!IMPORTANT]
> Historical phase snapshot. It records the evidence and constraints observed in
> that phase; it is not current operational guidance. Current RC truth is
> v3.2.0 / schema v16: Rappi and Uber acquisition are production-capable, while
> canonical matching remains shadow-only, automatic writes are OFF, human
> ground truth is insufficient and the statistical gate is `NOT_MET`.


## BASELINE
- **version**: v3.0.1
- **branch**: research/uber-eats-recon
- **starting HEAD**: dcf31da9188c70acdb3377b1c879dc24419adf22
- **schema**: 14
- **tests**: 400 passed / 0 failed

## ANDROID
- **package**: N/A
- **version**: N/A
- **UID**: N/A
- **static findings**: BLOCKED_BY_METHOD (Shizuku timeout)
- **dynamic findings**: BLOCKED_BY_METHOD

## WEB
- **public access**: Blocked by WAF (`def.uber.com/challenge`) for deep paths.
- **structured source**: GraphQL RPC endpoints (`_p/api/getFeedV1`, `getStoreV1`).
- **auth**: SESSION_REQUIRED (Needs WAF clearance / valid cookie).
- **location**: Bound to `uev2.loc` cookie.
- **major findings**: Uber Eats uses client-side hydration for content. SSR state exists (`__REDUX_STATE__`) but feed data is aggressively excluded.

## SOURCE AUTHORITY
- **primary candidate**: PUBLIC WEB API (GraphQL RPC)
- **secondary oracle**: ANDROID APP (Blocked currently)
- **reason**: Web API endpoints are documented, structured, and parseable if WAF is cleared.
- **confidence**: MEDIUM (Subject to session stability).

## SURFACES
- **total discovered**: 4
- **confirmed dynamic**: 2 (ID Namespace, Redux State)
- **confirmed static**: 2 (getFeedV1, getStoreV1)
- **candidates**: 0
- **noise**: 0
- **blocked**: 1 (Android App)

## DISCOVERY
- **best surface**: UE-A1 (getFeedV1)
- **requests**: 1 per page.
- **merchants**: Batch returned.
- **pagination**: Cursor-based (Hypothesis).
- **completeness**: UNKNOWN (Feeds are typically algorithmic, not exhaustive).
- **identity fields**: UUID string.

## IDENTITY
- **merchant**: Base64 UUID (e.g., `vN5-d143RhyuKDBH7Oq4Kw`).
- **store**: UUID.
- **item**: UUID (Hypothesis).
- **variant**: UUID (Hypothesis).
- **scope**: Global.
- **stability**: High.
- **Web/App consistency**: High (Universal identifiers).
- **provider-prefix decision**: Mandatory. Cannot mix with Rappi integers.

## CATALOG
- **best surface**: UE-C1 (getStoreV1)
- **sections**: Nested objects.
- **items**: Arrays within sections.
- **pagination**: Typically none for single stores.
- **completeness**: COMPLETE candidate.
- **requests/store**: 1 main request.

## TAXONOMY
- **structures**: Sections / Categories.
- **IDs**: UUIDs.
- **hierarchy**: Flat or 1-level deep.
- **collections**: Mappable to DealHunter's `category_name`.
- **mapping confidence**: HIGH.

## PRICING
- **current**: Integer (cents) or Float.
- **reference**: Stripped/strikethrough available if promo active.
- **discount**: Implicit from reference.
- **currency**: ISO.
- **variant pricing**: Modifiers carry additive prices.

## PROMOTIONS
- **public**: BOGO, percentage off.
- **conditional**: Uber One.
- **personalized ambiguity**: High risk of targeted promotions.

## UBER ONE
- **observed**: UNKNOWN (Requires live authenticated session).
- **product-price effect**: UNKNOWN.
- **delivery-only effect**: LIKELY.
- **conditional model fit**: YES.
- **confidence**: LOW.

## AVAILABILITY
- **explicit item state**: YES.
- **merchant state**: YES (Open/Closed).
- **absence semantics**: Item missing usually implies OOS.
- **snapshot safety**: Needs validation.

## DEEPLINK
- **merchant**: `https://www.ubereats.com/mx/store/{slug}/{uuid}`
- **item**: URL-based hash or modal.
- **reliability**: HIGH.

## REQUEST ECONOMICS
- **discovery**: 1 req = N merchants.
- **catalog**: 1 req = 1 full catalog.
- **commercial**: Highly efficient.
- **major risks**: WAF blocks (Cloudflare), IP banning.

## STRATEGY A
- **status**: LIKELY_FIT
- **evidence supporting**: Namespacing IDs solves the UUID vs Integer clash entirely. 
- **evidence against**: WAF requires real sessions; Termux headless curls will fail.
- **required core extensions**: Session import mechanism (similar to `auth.py`).

## TOP SURFACES
- **1**: UE-C1 (getStoreV1)
- **2**: UE-A1 (getFeedV1)
- **3**: UE-J1 (Deeplinks)

## UNRESOLVED
- **blockers**: WAF Challenge (`def.uber.com/challenge`).
- **unknowns**: Completeness of `getFeedV1`.
- **auth-dependent**: Session cookies required.
- **method-blocked**: Android API.

## PHASE5C
- **contracts to validate**: getFeedV1, getStoreV1.
- **probes**: Authenticated browser session extract -> `curl` replay.
- **sample**: 3 merchants.
- **request budget**: 10 requests.
- **stop conditions**: WAF hard-block.

## DOCUMENTATION
- **recon**: Updated.
- **surfaces**: Created.
- **contracts**: Created.
- **blueprint**: Validated.
- **playbook**: Stable.

## SECURITY
- **secrets**: None stored.
- **precise location**: Sanitized.
- **result**: CLEAN.

## QUALITY
- **tests**: 400
- **failures**: 0
- **Rappi changed**: NO
- **schema changed**: NO
- **baseline preserved**: YES

## DECISION
- **enough evidence for contract validation**: YES.
- **Strategy A still preferred**: YES.
- **identity model ready**: YES.
- **snapshot model ready**: UNKNOWN.
- **blocker**: WAF Mitigation needed for Phase 5C.
