# API Reference

The FastAPI app auto-generates interactive docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc:      `http://localhost:8000/redoc`
- OpenAPI:    `http://localhost:8000/openapi.json`

## Endpoint Summary

### Health

| Method | Path             | Description                |
|--------|------------------|----------------------------|
| GET    | `/health`        | Liveness check             |
| GET    | `/health/ready`  | Readiness (DB connection)  |

### Tenders

| Method | Path                                  | Description                          |
|--------|---------------------------------------|--------------------------------------|
| POST   | `/tenders`                            | Create a new awarded tender          |
| GET    | `/tenders`                            | List tenders (filtered)              |
| GET    | `/tenders/{id}`                       | Get a single tender                  |
| PATCH  | `/tenders/{id}`                       | Update tender fields                 |
| POST   | `/tenders/{id}/boq-items`             | Append BoQ items                     |
| GET    | `/tenders/{id}/anomaly-check`         | Statistical anomaly check on value   |

### Master Items

| Method | Path                          | Description                |
|--------|-------------------------------|----------------------------|
| POST   | `/master-items`               | Create a master item       |
| GET    | `/master-items`               | List master items          |
| GET    | `/master-items/{id}`          | Get a single master item   |
| POST   | `/master-items/synonyms`      | Add a synonym              |

### Normalization

| Method | Path                  | Description                        |
|--------|-----------------------|------------------------------------|
| POST   | `/normalize/item`     | Normalize a free-text item         |

### Analytics

| Method | Path                                       | Description                |
|--------|--------------------------------------------|----------------------------|
| POST   | `/analytics/reference-price`               | Engine #1 — for one item   |
| POST   | `/analytics/price-boq`                     | Engine #1 — for full BoQ   |
| POST   | `/analytics/go-no-go`                      | Engine #2                  |
| GET    | `/analytics/competitors/{id}/profile`      | Engine #3                  |
| POST   | `/analytics/win-probability`               | Engine #4                  |
| POST   | `/analytics/optimal-bid`                   | Engine #4 — optimization   |

## Authentication

The current build is unauthenticated for development. Production
deployment will sit behind an Odoo session-token check or an external
OAuth proxy (configuration in `api/main.py`).

## Error Format

All errors return:

```json
{ "detail": "human-readable message" }
```

Status codes:
- `400` — validation error (bad request body)
- `404` — resource not found
- `409` — insufficient data (e.g. for analytics)
- `422` — domain error (allocation / normalization)
- `502` — upstream Claude error
