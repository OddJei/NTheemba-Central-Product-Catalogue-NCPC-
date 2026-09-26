# NCPC API v1

All `/v1` routes require `Authorization: Bearer <token>`. Send an optional safe
`X-Request-ID`; the service returns the accepted/generated value on every response.

| Method | Route | Scope |
| --- | --- | --- |
| GET | `/health` | public |
| GET | `/v1/catalogue/candidates` | `catalogue:read` |
| GET | `/v1/catalogue/variants/{VAR}` | `catalogue:read` |
| POST | `/v1/catalogue/variants/verify` | `catalogue:read` |
| POST | `/v1/submissions/products` | `submissions:write` + business match |
| POST | `/v1/submissions/corrections` | `submissions:write` + business match |
| GET | `/v1/submissions/{SUB}` | `submissions:read` + business match |
| GET/POST | `/v1/admin/reviews...` | `reviews:read` / `reviews:decide` |
| GET/POST | `/v1/admin/publications` | `publications:read` / `publications:write` |
| POST | `/v1/admin/variants/{VAR}/merge` | `identities:merge` |
| GET/PATCH | `/v1/businesses/{business}/coverage/{product}/...` | coverage scopes |
| POST | `/v1/discovery/coverage/by-variants` | `discovery:read`, Ntheemba/admin only |
| POST | `/v1/tradeflow` | action-dependent; Sprint 01 compatibility |

Catalogue DTOs contain only NCPC identity facts. Coverage discovery never asserts
stock or availability. OpenAPI documentation is enabled outside production.

## Shop coverage on new-product submissions

A business-authenticated new-product submission must include `shop_id`, and its
`business_product_ref` must begin with that shop ID followed by `:`. A
business-authenticated correction must likewise use a non-empty
`shop_id:product_id` reference. This is enforced from the authenticated client,
not the caller-controlled `source` field, and makes a shop-local TradeFlow
product ID unambiguous within the business.

`location_projection` is optional and accepted only with these text keys:
`country_id`, `country_name`, `province_id`, `province_name`, `district_id`,
`district_name`, `town_id`, `town_name`, and `catalogue_version`. Any other
key is rejected. Do not submit street address, area, landmark, coordinates,
staff details, stock, price, supplier, or other business-operational data.
