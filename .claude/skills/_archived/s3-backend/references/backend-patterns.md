# Backend Patterns — 코드 템플릿 모음

> 실제 `backend/src/` 코드에서 추출한 패턴. 새 코드 작성 시 이 템플릿을 따를 것.

---

## 1. New Router Endpoint Template

```python
# src/segmentation/router.py 에 추가

@router.post("/predict/video", response_model=VideoPredictResponse)
async def predict_video(
    request: VideoPredictRequest,
    _: str = Depends(verify_api_key),
):
    """비디오 세그멘테이션 엔드포인트."""
    service = SegmentationService(
        predictor=app.state.predictor,
        storage=app.state.storage,
        task_service=app.state.task_service,
    )
    result = await service.run_video_prediction(
        video_url=request.video_url,
        text_prompt=request.text_prompt,
        task_id=request.task_id,
        user_id=request.user_id,
    )
    return result
```

---

## 2. SAM3Predictor Implementation Template

```python
# src/sam3/predictor.py — 실제 추론 구현

import time
import torch
import numpy as np
from src.sam3.config import SAM3Config

class SAM3Predictor:
    def __init__(self, config: SAM3Config):
        self.config = config
        self.model = None
        self.image_encoder = None
        self.prompt_encoder = None
        self.mask_decoder = None
        self._loaded = False

    async def load(self) -> None:
        """모델 가중치 로드 → GPU 배치."""
        # TODO: SAM3 라이브러리가 공개되면 import 경로 확정
        # from sam3 import build_sam3
        # self.model = build_sam3(checkpoint=self.config.weights_path)
        # self.model = self.model.to(self.config.device)
        # if self.config.dtype == "float16":
        #     self.model = self.model.half()
        # self.model.eval()
        self._loaded = True

    async def predict(self, image: np.ndarray, text_prompt: str) -> PredictResult:
        """
        단일 추론:
        1. 이미지 전처리 (resize, normalize)
        2. 이미지 인코딩
        3. 텍스트 프롬프트 인코딩
        4. 마스크 디코딩
        5. 후처리 (threshold, resize to original)
        """
        start = time.perf_counter()

        # 1. Preprocess
        original_size = image.shape[:2]
        input_image = self._preprocess(image)

        # 2. Inference (torch.no_grad)
        with torch.no_grad():
            input_tensor = torch.from_numpy(input_image).to(self.config.device)
            if self.config.dtype == "float16":
                input_tensor = input_tensor.half()

            # image_embedding = self.image_encoder(input_tensor)
            # prompt_embedding = self.prompt_encoder(text_prompt)
            # masks, scores = self.mask_decoder(image_embedding, prompt_embedding)
            pass

        # 3. Postprocess
        # mask = self._postprocess(masks[0], original_size)
        mask = np.zeros(original_size, dtype=np.uint8)  # placeholder

        elapsed = (time.perf_counter() - start) * 1000

        return PredictResult(
            mask=mask,
            labels=[text_prompt],
            confidence=0.95,
            inference_time_ms=elapsed,
        )

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """이미지 전처리: resize → normalize → CHW → batch."""
        h, w = image.shape[:2]
        max_size = self.config.max_image_size
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            image = np.array(
                __import__('PIL.Image', fromlist=['Image']).Image.fromarray(image).resize(
                    (int(w * scale), int(h * scale))
                )
            )

        # Normalize to [0, 1]
        image = image.astype(np.float32) / 255.0
        # HWC → CHW → BCHW
        image = np.transpose(image, (2, 0, 1))[np.newaxis, ...]
        return image
```

---

## 3. StorageService Implementation (boto3 + R2)

```python
# src/storage/service.py
import io
import boto3
import numpy as np
from PIL import Image

class StorageService:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",  # R2는 region 불필요하나 boto3 요구
        )

    async def download_image(self, image_url: str) -> np.ndarray:
        """R2에서 이미지 다운로드 → numpy array."""
        # URL에서 key 추출 (uploads/user-id/image-id)
        key = self._url_to_key(image_url)
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        image_bytes = response["Body"].read()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(image)

    async def upload_mask(self, mask: np.ndarray, task_id: str) -> str:
        """마스크 numpy → PNG → R2 업로드."""
        # numpy → PIL → bytes
        mask_image = Image.fromarray((mask * 255).astype(np.uint8))
        buffer = io.BytesIO()
        mask_image.save(buffer, format="PNG")
        buffer.seek(0)

        key = f"masks/{task_id}.png"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=buffer.getvalue(),
            ContentType="image/png",
        )

        return self._key_to_url(key)

    def _url_to_key(self, url: str) -> str:
        """R2 public URL → object key."""
        # https://pub-xxx.r2.dev/uploads/user-id/image-id → uploads/user-id/image-id
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.path.lstrip("/")

    def _key_to_url(self, key: str) -> str:
        """Object key → R2 public URL."""
        # endpoint에서 public URL 생성
        return f"{self.client.meta.endpoint_url}/{self.bucket}/{key}"
```

---

## 4. TaskService Implementation (Supabase service_role)

```python
# src/tasks/service.py
import httpx

class TaskService:
    """segmentation_results UPDATE만 담당 (Backend → Supabase)."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.base_url = f"{supabase_url}/rest/v1"
        self.headers = {
            "Content-Type": "application/json",
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",  # service_role → RLS bypass
            "Prefer": "return=minimal",
        }

    async def update_status(self, task_id: str, status: str) -> None:
        """status 업데이트: pending → processing → done | error."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/segmentation_results?id=eq.{task_id}",
                headers=self.headers,
                json={"status": status},
            )
            response.raise_for_status()

    async def update_result(
        self,
        task_id: str,
        mask_url: str,
        labels: list[str],
        metadata: dict,
    ) -> None:
        """추론 완료 결과 저장 + status=done."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/segmentation_results?id=eq.{task_id}",
                headers=self.headers,
                json={
                    "status": "done",
                    "mask_image_url": mask_url,
                    "labels": labels,
                    "metadata": metadata,
                },
            )
            response.raise_for_status()
```

---

## 5. SegmentationService Pipeline (Complete)

```python
# src/segmentation/service.py
from src.sam3.predictor import SAM3Predictor, PredictResult
from src.storage.service import StorageService
from src.tasks.service import TaskService

class SegmentationService:
    def __init__(self, predictor: SAM3Predictor, storage: StorageService, task_service: TaskService):
        self.predictor = predictor
        self.storage = storage
        self.tasks = task_service

    async def run_prediction(
        self, image_url: str, text_prompt: str, task_id: str, user_id: str
    ) -> dict:
        try:
            # 1. Status → processing
            await self.tasks.update_status(task_id, "processing")

            # 2. Download image from R2
            image = await self.storage.download_image(image_url)

            # 3. SAM3 inference
            result: PredictResult = await self.predictor.predict(image, text_prompt)

            # 4. Upload mask to R2
            mask_url = await self.storage.upload_mask(result.mask, task_id)

            # 5. Update Supabase with results
            await self.tasks.update_result(
                task_id=task_id,
                mask_url=mask_url,
                labels=result.labels,
                metadata={
                    "inference_time_ms": result.inference_time_ms,
                    "confidence": result.confidence,
                    "user_id": user_id,
                },
            )

            return {
                "task_id": task_id,
                "mask_url": mask_url,
                "labels": result.labels,
                "inference_time_ms": result.inference_time_ms,
                "confidence": result.confidence,
            }

        except Exception as e:
            # Error → Supabase 상태 업데이트
            await self.tasks.update_status(task_id, "error")
            raise
```

---

## 6. Test Fixtures Template

```python
# tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient

# 환경변수를 app import 전에 설정
os.environ.setdefault("API_SECRET_KEY", "test-secret-key")

from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-secret-key"}

@pytest.fixture
def mock_predict_request():
    return {
        "image_url": "https://example.com/uploads/user1/image1.png",
        "text_prompt": "cat",
        "user_id": "test-user-id",
        "task_id": "test-task-id",
    }
```

---

## 7. Test Template

```python
# tests/test_segmentation.py

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_model_info(client, auth_headers):
    response = client.get("/api/v1/model/info", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "SAM3"
    assert data["parameters"] == 848_000_000

def test_predict_requires_auth(client):
    response = client.post("/api/v1/predict", json={
        "image_url": "https://example.com/image.png",
        "text_prompt": "cat",
        "user_id": "test-user",
        "task_id": "test-task",
    })
    assert response.status_code == 401

def test_predict_with_auth(client, auth_headers, mock_predict_request):
    response = client.post(
        "/api/v1/predict",
        headers=auth_headers,
        json=mock_predict_request,
    )
    # NotImplementedError → 500 (stub)
    assert response.status_code == 500
```

---

## 8. Lifespan Service Registration

```python
# src/main.py — lifespan에서 서비스 등록

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.sam3.predictor import SAM3Predictor
    from src.sam3.config import SAM3Config
    from src.storage.service import StorageService
    from src.tasks.service import TaskService

    # Model
    config = SAM3Config.from_settings(settings)
    predictor = SAM3Predictor(config)
    await predictor.load()
    app.state.predictor = predictor

    # Storage
    app.state.storage = StorageService(
        endpoint=settings.r2_endpoint,
        access_key=settings.r2_access_key_id,
        secret_key=settings.r2_secret_access_key,
        bucket=settings.r2_bucket,
    )

    # Tasks
    app.state.task_service = TaskService(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key,
    )

    yield

    # Cleanup
    await predictor.unload()
```

---

## 9. Docker Production Setup

```dockerfile
# Dockerfile
FROM nvidia/cuda:12.6.0-runtime-ubuntu24.04

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3-pip \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
# weights는 volume mount (Docker image에 포함하지 않음)

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  backend:
    build: .
    ports: ["8000:8000"]
    volumes: ["./weights:/app/weights"]
    env_file: [".env"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```
