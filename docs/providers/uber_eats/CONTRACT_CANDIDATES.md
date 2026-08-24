# UBER EATS CONTRACT CANDIDATES

## 1. UE-A1: Discovery (getFeedV1)

**INPUT**
- Location context (lat/lng, typically via `uev2.loc` cookie or payload).
- CSRF Token.
- Device / Session headers (`x-uber-device-id`).

**OUTPUT**
- Array of merchants.
- Basic metadata: Name, UUID, estimated delivery time, rating.

**COMPLETENESS**
- UNKNOWN. Feed APIs typically return algorithmic subsets, not exhaustive geospatial inventories.

**AUTH**
- WAF / Session dependent.

## 2. UE-C1: Catalog (getStoreV1)

**INPUT**
- Merchant UUID (`storeUuid`).
- Location context (to validate delivery radius).

**OUTPUT**
- Nested sections (Categories).
- Items (UUID, name, description, price).
- Availability flags.

**COMPLETENESS**
- LIKELY COMPLETE. Uber Eats typically renders the entire store menu via this endpoint, grouped by sections.

**AUTH**
- WAF / Session dependent.

## 3. UE-H1: Uber One (Conditional Pricing)

**INPUT**
- User session with active Uber One membership.

**OUTPUT**
- Promoted items or reduced delivery fees.

**COMPLETENESS**
- UNKNOWN. We need a live session with Uber One to observe if `item.price` changes or if it only affects the cart delivery fee.
