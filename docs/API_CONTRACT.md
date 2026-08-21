# AQG Studio - REST & Real-Time API Contract

## 1. Global Conventions & Standards

- **Base URL**: `/api/v1`
- **Protocol**: HTTPS / WSS / Server-Sent Events (SSE)
- **Authentication**: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`
- **Content-Type**: `application/json` (except multipart file upload endpoints)
- **Date Format**: ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)
- **Correlation Header**: `X-Correlation-ID` returned in all responses and reflected in `meta.request_id`

### Standard Response Envelope (JSON)
```json
{
  "success": true,
  "data": {},
  "meta": {
    "timestamp": "2026-08-21T10:00:00Z",
    "request_id": "req_01j6f93abcde12345"
  }
}
```

### Standard Error Envelope (JSON)
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Bearer authentication token is required to access this endpoint.",
    "details": []
  },
  "meta": {
    "timestamp": "2026-08-21T10:00:00Z",
    "request_id": "req_01j6f93abcde12345"
  }
}
```

---

## 2. API Endpoint Matrix

### 2.0 System, Health & Version Endpoints
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/health/live` | Liveness probe returning process status (`{"status": "ok"}`) | Public |
| `GET` | `/health/ready` | Readiness probe returning dependency status (`{"status": "ready", "database": "..."}`) | Public |
| `GET` | `/api/v1/version` | Returns API build version, environment, and system status wrapped in standard envelope | Public |

---

### 2.1 Authentication & Profile
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile, display name & quota usage stats | Authenticated |
| `GET` | `/api/v1/me` | Alias for `/api/v1/auth/me` | Authenticated |

#### Request Example: `GET /api/v1/auth/me`
- Header: `Authorization: Bearer <SUPABASE_JWT_TOKEN>`

#### Response Example:
```json
{
  "success": true,
  "data": {
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "educator@institution.edu",
    "role": "authenticated",
    "display_name": "Dr. Eleanor Vance",
    "app_metadata": {
      "provider": "email"
    },
    "user_metadata": {
      "display_name": "Dr. Eleanor Vance"
    },
    "quota": {
      "today_requests": 12,
      "today_input_tokens": 4500,
      "today_output_tokens": 1850,
      "today_assessments": 2
    }
  },
  "meta": {
    "timestamp": "2026-08-21T11:00:00Z",
    "request_id": "req_a1b2c3d4e5f67890"
  }
}
```

---

### 2.2 Documents & Ingestion Lifecycle
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/documents/initiate` | Validate format/size and obtain target private Storage path (`<user_id>/<doc_id>/<sanitized_filename>`) | Authenticated |
| `POST` | `/api/v1/documents/{document_id}/complete` | Confirm direct client upload to private `source-documents` bucket | Authenticated |
| `POST` | `/api/v1/documents/{document_id}/process` | Deterministically parse document bytes, extract sections & hierarchical chunks | Authenticated |
| `GET` | `/api/v1/documents` | List uploaded documents with pagination (`limit`, `offset`) | Authenticated |
| `GET` | `/api/v1/documents/{document_id}` | Get document metadata, parsing status, word count & page count | Authenticated |
| `GET` | `/api/v1/documents/{document_id}/chunks` | List extracted structured chunks (600–900 tokens, 10% overlap) | Authenticated |
| `DELETE`| `/api/v1/documents/{document_id}` | Delete document and cascade delete all associated chunks | Authenticated |

#### Request Example: `POST /api/v1/documents/initiate`
```json
{
  "original_filename": "Calculus_Chapter_1.pdf",
  "declared_mime_type": "application/pdf",
  "size_bytes": 2048500
}
```

#### Response Example:
```json
{
  "success": true,
  "data": {
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "storage_path": "3fa85f64-5717-4562-b3fc-2c963f66afa6/3fa85f64-5717-4562-b3fc-2c963f66afa6/Calculus_Chapter_1.pdf",
    "upload_bucket": "source-documents"
  },
  "meta": {
    "timestamp": "2026-08-21T11:00:00Z",
    "request_id": "req_01j6f93abcde12345"
  }
}
```

---

### 2.3 Knowledge Analysis, Topics & RAG Retrieval
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/documents/{document_id}/analyze` | Trigger Knowledge Retrieval & Analysis Agent | Authenticated |
| `GET` | `/api/v1/documents/{document_id}/analysis` | Retrieve extracted topics, concepts & hierarchy | Authenticated |
| `POST` | `/api/v1/documents/{document_id}/retrieve` | Hybrid vector & lexical chunk retrieval | Authenticated |

---

### 2.4 Assessment Blueprints
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/blueprints` | Create or auto-generate an assessment blueprint | Authenticated |
| `GET` | `/api/v1/blueprints/{blueprint_id}` | Retrieve specific blueprint specifications | Authenticated |
| `PUT` | `/api/v1/blueprints/{blueprint_id}` | Update question counts, difficulty ratios & Bloom distribution | Authenticated |

---

### 2.5 Multi-Agent Generation & Real-Time Streaming
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/jobs/generate` | Launch full LangGraph assessment generation job | Authenticated |
| `GET` | `/api/v1/jobs/{job_id}` | Check job execution progress, current agent & status | Authenticated |
| `GET` | `/api/v1/jobs/{job_id}/stream` | Server-Sent Events (SSE) live progress stream | Authenticated |
| `POST` | `/api/v1/jobs/{job_id}/cancel` | Abort a running generation job | Authenticated |

---

### 2.6 Questions & Human Review Studio
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/assessments/{assessment_id}/questions` | List questions with evaluation scores & citations | Authenticated |
| `GET` | `/api/v1/questions/{question_id}` | Retrieve individual question with full audit trace | Authenticated |
| `PATCH`| `/api/v1/questions/{question_id}` | Update stem, options, key, explanation or status | Authenticated |
| `POST` | `/api/v1/questions/{question_id}/refine` | Request single-item AI regeneration pass | Authenticated |

---

### 2.7 Multi-Format Export Center
| Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/exports` | Request asynchronous assessment export generation | Authenticated |
| `GET` | `/api/v1/exports/{export_id}` | Check export status & retrieve signed download URL | Authenticated |
