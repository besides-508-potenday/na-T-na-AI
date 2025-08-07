# Python 3.11 기반 이미지 사용
FROM python:3.11-slim

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Poetry 설치
RUN pip install --upgrade pip && pip install poetry

# Poetry 설정 - 가상환경 생성하지 않음 (Docker 컨테이너 내부에서만 사용)
RUN poetry config virtualenvs.create false

# pyproject.toml과 poetry.lock 복사
COPY pyproject.toml poetry.lock ./

# 의존성 설치 (개발용 패키지는 설치하지 않음)
RUN poetry install --only main --no-root


# 프로젝트 전체 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p logs

# 포트 노출 (FastAPI/Flask 등 백엔드 서버 실행 시 필요)
EXPOSE 8000

# 헬스체크 설정 (선택사항)
HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["python", "main.py"]
