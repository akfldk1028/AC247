---
name: s3-backend
description: |
  Backend SAM3 추론 서버 개발 (FastAPI + PyTorch). 추론 파이프라인, R2 스토리지, Supabase 결과 업데이트.
  사용 시점: (1) SAM3 추론 구현/수정 시, (2) 스토리지 서비스 구현 시, (3) 새 추론 엔드포인트 추가 시
  사용 금지: Edge API 로직, Frontend UI, DB 마이그레이션, CRUD 엔드포인트 추가
argument-hint: "[predict|storage|tasks|endpoint|docker] [description]"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# s3-backend — Backend SAM3 추론 개발 가이드

> Backend = SAM3 추론 전용 Internal API.
> GPU에서 추론만 실행. Edge에서만 호출 가능. CRUD 없음.

## When to Use

- SAM3 추론 파이프라인 구현/수정 (predictor, postprocess)
- R2 스토리지 서비스 구현 (boto3 S3 client)
- Supabase 결과 업데이트 구현 (service_role, UPDATE만)
- 새 추론 엔드포인트 추가
- Docker/GPU 설정 수정
- 테스트 작성

## When NOT to Use

- Edge API 라우트/CRUD → `/s3-edge`
- DB 마이그레이션, RLS → `/s3-supabase`
- Frontend UI → Flutter 직접
- CRUD 엔드포인트 추가 금지 (Backend는 추론만)

---

## Core Principle

```
Edge → POST /api/v1/predict → Backend (GPU 추론) → R2 업로드 + Supabase UPDATE
```

- **Backend는 CRUD 없음** — Edge가 모든 CRUD 담당
- **Edge에서만 호출** — `X-API-Key` 인증
- **Supabase UPDATE만** — `service_role` 키로 `segmentation_results` 업데이트

---

## Project Structure

```
backend/
├── src/
│   ├── main.py                  ← FastAPI factory + lifespan (모델 로드)
│   ├── config.py                ← Settings (pydantic_settings.BaseSettings)
│   ├── database.py              ← Supabase client (stub)
│   │
│   ├── segmentation/            ★ 메인 추론 도메인
│   │   ├── router.py            ← 3 endpoints (predict, batch, info)
│   │   ├── schemas.py           ← Pydantic request/response models
│   │   ├── service.py           ← 파이프라인 오케스트레이터
│   │   ├── dependencies.py      ← X-API-Key 검증
│   │   └── constants.py         ← 도메인 상수
│   │
│   ├── sam3/                    ★ 모델 래퍼
│   │   ├── predictor.py         ← SAM3Predictor (load, predict, batch)
│   │   ├── postprocess.py       ← 마스크 후처리
│   │   └── config.py            ← SAM3Config (dataclass)
│   │
│   ├── storage/
│   │   └── service.py           ← R2 다운로드/업로드 (boto3)
│   │
│   ├── tasks/
│   │   └── service.py           ← Supabase UPDATE만 (service_role)
│   │
│   └── core/
│       └── middleware.py        ← CORS setup
│
├── tests/
│   ├── conftest.py              ← TestClient + fixtures
│   └── test_segmentation.py    ← 기본 테스트
│
├── Dockerfile                   ← CUDA 12.6 + Python 3.12
├── docker-compose.yml           ← GPU + volume mount
├── requirements.txt
└── .env.example
```

---

## Core Patterns

### 1. Configuration (Singleton)

```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    sam3_weights_path: str = "/app/weights/sam3.pt"
    sam3_device: str = "cuda"
    hf_token: str = ""
    r2_endpoint: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "s3-images"
    supabase_url: str = ""
    supabase_service_key: str = ""  # service_role (RLS bypass)
    api_secret_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()  # 모듈 레벨 싱글턴
```

### 2. FastAPI Application Factory + Lifespan

```python
# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 모델 로드
    # app.state.predictor = SAM3Predictor(...)
    # await app.state.predictor.load()
    yield
    # Shutdown: cleanup

def create_app() -> FastAPI:
    app = FastAPI(
        title="S3 Backend — SAM3 GPU Inference Server",
        version="0.1.0",
        lifespan=lifespan,
    )
    setup_middleware(app)

    from src.segmentation.router import router as segmentation_router
    app.include_router(segmentation_router)  # 유일한 라우터

    @app.get("/health")
    async def health():
        return {"status": "ok", "model_loaded": False, "gpu_available": False}

    return app

app = create_app()
```

### 3. Router + Dependencies

```python
# src/segmentation/router.py
from fastapi import APIRouter, Depends
from src.segmentation.dependencies import verify_api_key
from src.segmentation.schemas import PredictRequest, PredictResponse

router = APIRouter(prefix="/api/v1", tags=["segmentation"])

@router.post("/predict", response_model=PredictResponse)
async def predict(
    request: PredictRequest,
    _: str = Depends(verify_api_key),  # X-API-Key 인증
):
    raise NotImplementedError  # TODO: service.run_prediction()
```

### 4. API Key Dependency

```python
# src/segmentation/dependencies.py
from fastapi import HTTPException, Request, status
from src.config import settings

async def verify_api_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key", "")
    if not settings.api_secret_key:
        return api_key  # Dev mode: no key → pass through
    if api_key != settings.api_secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return api_key
```

### 5. Pydantic Schemas

```python
# src/segmentation/schemas.py
from pydantic import BaseModel

class PredictRequest(BaseModel):
    image_url: str       # R2 URL from Edge
    text_prompt: str     # User's text prompt
    user_id: str         # For audit trail
    task_id: str         # Task ID for DB update

class PredictResponse(BaseModel):
    task_id: str
    mask_url: str        # R2 URL of result mask
    labels: list[str]
    inference_time_ms: float
    confidence: float

class BatchPredictRequest(BaseModel):
    image_url: str
    prompts: list[str]
    user_id: str
    task_id: str

class BatchPredictResponse(BaseModel):
    task_id: str
    results: list[PredictResponse]
    total_inference_time_ms: float

class ModelInfoResponse(BaseModel):
    model_name: str      # "SAM3"
    model_version: str   # "1.0"
    parameters: int      # 848_000_000
    weights_size_gb: float
    device: str
    dtype: str
```

### 6. SAM3Predictor

```python
# src/sam3/predictor.py
from dataclasses import dataclass
import numpy as np
from src.sam3.config import SAM3Config

@dataclass
class PredictResult:
    mask: np.ndarray          # H x W binary mask
    labels: list[str]
    confidence: float
    inference_time_ms: float

class SAM3Predictor:
    def __init__(self, config: SAM3Config):
        self.config = config
        self.model = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        """모델 가중치 로드 (app startup 시 1회)"""
        # TODO: sam3 import + GPU placement
        pass

    async def predict(self, image: np.ndarray, text_prompt: str) -> PredictResult:
        """단일 이미지 + 텍스트 → 마스크"""
        raise NotImplementedError

    async def predict_batch(self, image: np.ndarray, prompts: list[str]) -> list[PredictResult]:
        """단일 이미지 + 다중 프롬프트 → 다중 마스크"""
        raise NotImplementedError

    async def unload(self) -> None:
        self.model = None
        self._loaded = False
```

### 7. SAM3Config (dataclass)

```python
# src/sam3/config.py
from dataclasses import dataclass

@dataclass
class SAM3Config:
    weights_path: str = "/app/weights/sam3.pt"
    device: str = "cuda"
    dtype: str = "float16"
    model_name: str = "SAM3"
    model_version: str = "1.0"
    parameters: int = 848_000_000
    weights_size_gb: float = 3.4
    max_image_size: int = 1024
    mask_threshold: float = 0.5

    @classmethod
    def from_settings(cls, settings) -> "SAM3Config":
        return cls(weights_path=settings.sam3_weights_path, device=settings.sam3_device)
```

### 8. Pipeline Orchestrator

```python
# src/segmentation/service.py
class SegmentationService:
    def __init__(self, predictor, storage, task_service):
        self.predictor = predictor
        self.storage = storage
        self.tasks = task_service

    async def run_prediction(self, image_url, text_prompt, task_id, user_id):
        """추론 파이프라인:
        1. tasks.update_status(task_id, "processing")
        2. storage.download_image(image_url) → numpy
        3. predictor.predict(image, text_prompt) → PredictResult
        4. storage.upload_mask(result.mask, task_id) → mask_url
        5. tasks.update_result(task_id, mask_url, labels, metadata)
        """
        raise NotImplementedError
```

---

## Commands

| Command | Description |
|---------|-------------|
| `uvicorn src.main:app --reload` | 로컬 개발 서버 (`backend/` 디렉토리에서) |
| `pytest -v` | 테스트 실행 |
| `docker build -t s3-backend .` | Docker 이미지 빌드 |
| `docker compose up` | Docker + GPU 실행 |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SAM3_WEIGHTS_PATH` | 모델 가중치 경로 (`/app/weights/sam3.pt`) |
| `SAM3_DEVICE` | `cuda` or `cpu` |
| `HF_TOKEN` | HuggingFace 토큰 (가중치 다운로드) |
| `R2_ENDPOINT` | Cloudflare R2 endpoint URL |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_BUCKET` | `s3-images` |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | service_role key (RLS bypass) |
| `API_SECRET_KEY` | Edge → Backend 인증 키 |

---

## Checklist: 새 추론 기능 추가

1. `src/segmentation/schemas.py` — Request/Response 스키마 추가
2. `src/segmentation/router.py` — 엔드포인트 추가 (`Depends(verify_api_key)`)
3. `src/segmentation/service.py` — 파이프라인 로직 추가
4. `src/sam3/predictor.py` — 필요시 predict 메서드 추가
5. `tests/` — 테스트 추가
6. `docs/contracts/api-contracts.md` — **API Contract SSoT 먼저 수정**
7. `pytest -v` — 테스트 통과 확인

---

## Related Skills

- `/s3-edge` — Edge API (Backend를 프록시하는 호출자)
- `/s3-supabase` — DB 스키마 (Backend가 UPDATE하는 대상)
- `/s3-build` — 전체 빌드 검증
- `/s3-test` — 전체 테스트 실행

---

## References

- [backend-patterns.md](references/backend-patterns.md) — 코드 템플릿 모음
- [API Contract SSoT](C:\DK\S3\docs\contracts\api-contracts.md) — 엔드포인트 명세
- [Backend README](C:\DK\S3\backend\README.md) — Agent 작업 가이드
