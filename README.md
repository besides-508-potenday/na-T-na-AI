# 나 T나?? 🤖💬

> T 성향을 가진 사람들이 감정 공감을 훈련해볼 수 있는 AI 챗봇 기반의 감정 시뮬레이션 서비스

![Service Overview](data/overview.png)

<div align="center">

### 🗒️ [Notion](https://ubiquitous-blackberry-1d3.notion.site/2483cff2c9eb805eb6edc5cc93cf8e2b?pvs=74) | 🤖 [Github Organization](https://github.com/besides-508-potenday)

</div>

---

## 📑 Table of Contents

- [프로젝트 소개](#-프로젝트-소개)
- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시스템 아키텍처](#-시스템-아키텍처)
- [AI Pipeline](#-ai-pipeline)
- [CLOVA 활용](#-clova-활용)
- [프로젝트 구조](#-프로젝트-구조)
- [설치 및 실행](#-설치-및-실행)
- [API 명세](#-api-명세)
- [환경 변수 설정](#-환경-변수-설정)
- [배포](#-배포)
- [개발 가이드](#-개발-가이드)
- [트러블슈팅](#-트러블슈팅)

---

## 🎯 프로젝트 소개


"나 T나??"는 MBTI T(사고형) 성향의 사용자가 F(감정형) 성향의 친구와 대화하는 시뮬레이션을 통해 감정 공감 능력을 훈련할 수 있는 서비스입니다.

### 서비스 특징

- 🎭 **실제 같은 F 성향 챗봇**: Naver HyperCLOVA X를 활용한 감정적이고 섬세한 대화
- 📊 **실시간 공감 점수 평가**: 사용자 응답의 공감 수준을 AI가 즉시 평가
- 💌 **개인화된 피드백**: 대화 종료 후 감정적인 편지 형식의 음성 피드백 제공
- 🎵 **음성 지원**: CLOVA Voice TTS로 생성된 자연스러운 음성 피드백

### 데모 영상

> 채팅 대화 시연

https://github.com/user-attachments/assets/8ab339ad-0bf5-4a8a-9a53-3c7d7342cde3

---

## ✨ 주요 기능

### 1. 감정 상황 생성
- AI가 현실적인 친구 관계 시나리오를 자동 생성
- 공감이 필요한 5개의 감정 표현 문장 제공
- 매 세션마다 새로운 상황으로 다양한 훈련 가능

### 2. 대화형 감정 훈련
- 사용자의 각 응답에 대해 실시간 평가 (0~1점)
- 공감적 응답 기준:
  - ✅ 감정 정확히 읽고 언급하기
  - ✅ 감정 정당화 ("그렇게 느끼는 게 자연스러워")
  - ✅ 함께 공감하기 ("나도 마음이 아파")
  - ❌ 즉각적인 해결책 제시
  - ❌ 감정 무시 ("괜찮은 거 아니야?")

### 3. 감정 거리 측정
- 초기 거리: 5
- 공감 성공 시: -1
- 최종 거리를 통한 공감 능력 시각화

### 4. 피드백 레터
- 대화 전체를 분석한 개인화된 피드백
- 감정을 담은 편지 형식
- CLOVA Voice로 생성된 음성 파일 제공
- AWS S3에 저장되어 언제든 다시 듣기 가능

---

## 🛠 기술 스택

### AI & ML
<p>
<img src="https://img.shields.io/badge/HyperCLOVA_X-03C75A?style=for-the-badge&logo=naver&logoColor=white"/>
<img src="https://img.shields.io/badge/CLOVA_Voice-03C75A?style=for-the-badge&logo=naver&logoColor=white"/>
</p>

- **HyperCLOVA X (HCX-007)**: 대화 생성, 평가, 피드백 생성
- **CLOVA Voice TTS**: 피드백 음성 변환 (멍멍이 음색)

### Backend
<p>
<img src="https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Uvicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white"/>
</p>

- **FastAPI**: 비동기 API 서버
- **Poetry**: 의존성 관리
- **Pydantic**: 데이터 검증

### Frontend
<p>
<img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
</p>

### Infrastructure
<p>
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
<img src="https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white"/>
<img src="https://img.shields.io/badge/AWS_S3-569A31?style=for-the-badge&logo=amazons3&logoColor=white"/>
<img src="https://img.shields.io/badge/AWS_EC2-FF9900?style=for-the-badge&logo=amazonec2&logoColor=white"/>
</p>

- **Docker & Docker Compose**: 컨테이너화
- **Nginx**: 리버스 프록시, 로드 밸런싱
- **AWS S3**: 음성 파일 저장소
- **AWS EC2**: 서버 호스팅

---

## 🏗 시스템 아키텍처

### 전체 아키텍처

![AI Architecture](data/AI_architecture.png)

### 구성 요소

```
사용자 (Streamlit UI)
    ↓
[Nginx:80] ← 리버스 프록시, Rate Limiting
    ↓
[FastAPI:8000] ← 비동기 처리, 세션 관리
    ↓
├─ HyperCLOVA X API ← 대화 생성 및 평가
├─ CLOVA Voice API ← TTS 음성 합성
└─ AWS S3 ← 음성 파일 저장
```

### 배포 구조

- **Docker Compose** 기반 멀티 컨테이너 오케스트레이션
- **Worker Pool**: 4 workers (CPU 기반 동적 조정 가능)
- **연결 풀링**: HTTP 연결 재사용으로 성능 최적화
- **헬스체크**: 자동 장애 감지 및 복구

---

## 🔄 AI Pipeline

### 전체 흐름도

![AI Pipeline](data/AI_pipeline.png)

### 상세 프로세스

#### **Phase 1: 초기화 (Initialization)**
```python
POST /situation
```
1. 사용자 정보 수신 (닉네임, 챗봇 이름, 채팅방 ID)
2. HyperCLOVA X로 상황 생성
3. 5개의 감정 문장 생성
4. 세션 생성 및 JSON 저장

**출력 예시:**
```json
{
  "quiz_list": [
    "친구가 다음 주에 생일이라 깜짝 파티 준비하려는데, 정말 마음이 무거워...",
    "요즘 일이 너무 바빠서 시간 내기가 쉽지 않아... 그래서 더 초조해지고 있어.",
    ...
  ]
}
```

#### **Phase 2: 대화 턴 (Conversation Loop)**
```python
POST /conversation
```

각 턴마다 4단계 처리:

**1단계: 검증 및 평가**
- 부적절한 언어 필터링 (욕설, 프롬프트 탈취)
- 공감 점수 평가 (0 또는 1)
- 평가 근거 생성

**2단계: 감정 반응 생성**
- 점수에 따라 감정 톤 조정 (실망/기쁨)
- 60자 이내 자연스러운 반응

**3단계: 다음 질문 개선**
- 대화 흐름에 맞게 질문 수정
- 접속사 추가로 자연스러운 전환

**4단계: 상태 업데이트**
- 거리 업데이트 (공감 성공 시 -1)
- 대화 로그 저장

#### **Phase 3: 피드백 생성 (Feedback)**
```python
POST /feedback
```
1. 전체 대화 분석
2. 거리 기반 감정 톤 결정
   - 거리 0: 행복하고 감동적인 톤
   - 거리 1: 신나고 감동적인 톤
   - 거리 2: 아쉽고 서운한 톤
   - 거리 3+: 실망스럽고 슬픈 톤
3. 편지 형식 피드백 생성 (300자 이내)
4. CLOVA TTS로 음성 변환
5. S3 업로드 및 URL 반환

---

## 🧠 CLOVA 활용

### 1. HyperCLOVA X (HCX-007)

#### 모델 정보
- **Model**: HCX-007
- **Provider**: Naver Cloud Platform
- **용도**: 대화 생성, 평가, 피드백

#### 프롬프트 전략

**F 성향 페르소나 설정:**
```
- Personality: 수줍고, 감정적으로 강렬하며, 인정을 추구하고, 관계 중심적 언어 사용
- Tone: 감정적 단어를 자주 사용하며 이모지 포함, 반말 사용
```

#### 코드 구조

![Chat Code Flow](data/chat_code.png)

**주요 함수:**
- `generate_situation_and_quiz()`: 상황 및 문제 생성
- `generate_verification_and_score()`: 응답 검증 및 점수 평가
- `generate_response()`: 감정 반응 생성
- `improved_question()`: 질문 개선
- `generate_feedback()`: 최종 피드백 생성

#### API 파라미터 (`config/params.yaml`)

```yaml
DEFAULT_PARAMS:
  temperature: 0.7
  topP: 0.8
  maxTokens: 200

REACT_PARAMS:
  temperature: 0.8
  topP: 0.9
  maxTokens: 100

FEEDBACK_PARAMS:
  temperature: 0.6
  topP: 0.85
  maxTokens: 500
```

### 2. CLOVA Voice (TTS)

#### 음성 설정
- **Voice**: 멍멍이 (nwoof)
- **음색**: 2
- **높낮이**: 1
- **속도**: 0 (기본)
- **포맷**: MP3

#### 샘플 음성

<div align="center">

<table>
<tr>
<td align="center">
<a href="data/tudak_voice.mp3">
<img src="https://img.shields.io/badge/🎵_Play_Audio-투닥이_보이스-FF69B4?style=for-the-badge&labelColor=blue" alt="Play Audio"/>
</a>
<br/>
<sub><b>투닥이 캐릭터 샘플 음성</b></sub>
</td>
</tr>
</table>

</div>

#### 음성 생성 프로세스

```python
def generate_tts(text, save_path="sample.mp3"):
    # CLOVA Voice API 호출
    # MP3 파일 생성
    # Base64 인코딩
    # S3 업로드
    return s3_url
```

---

## 📂 프로젝트 구조

```
natna/
├── config/
│   └── params.yaml              # HyperCLOVA API 파라미터 설정
│
├── conversation_logs/           # 대화 세션 JSON 저장소
│   └── {session_id}.json        # 각 세션의 전체 대화 기록
│
├── logs/                        # 애플리케이션 로그
│   ├── app.log                  # 일반 로그 (일별 로테이션)
│   ├── error.log                # 에러 로그
│   └── access.log               # API 접근 로그
│
│
├── main.py                      # FastAPI 메인 서버
│   ├── FastAPI 앱 초기화
│   ├── 미들웨어 설정 (CORS, Rate Limiting)
│   ├── API 엔드포인트 정의
│   ├── ConversationLogger 클래스 (세션 관리)
│   └── 로깅 설정
│
├── chat.py                      # AI 로직 모듈
│   ├── execute_chat(): HyperCLOVA API 호출
│   ├── generate_situation_and_quiz(): 상황 생성
│   ├── generate_verification_and_score(): 평가
│   ├── generate_response(): 반응 생성
│   ├── improved_question(): 질문 개선
│   ├── generate_feedback(): 피드백 생성
│   └── generate_tts(): TTS 음성 생성
│
├── app.py                       # Streamlit UI
│   ├── 사용자 인터페이스
│   ├── 채팅 인터랙션
│   └── 상태 관리
│
├── s3_utils.py                  # AWS S3 유틸리티
│   ├── upload_audio_base64(): 음성 파일 업로드
│   └── create_presigned_url(): 임시 URL 생성
│
├── debug_storage.py             # 디버깅 도구
│
├── Dockerfile                   # Docker 이미지 빌드
├── docker-compose.yml           # 멀티 컨테이너 구성
├── nginx.conf                   # Nginx 설정
│
├── pyproject.toml               # Poetry 의존성 정의
├── poetry.lock                  # 의존성 잠금 파일
│
└── __init__.py                  # 패키지 초기화
```

---

## 🚀 설치 및 실행

### 사전 요구사항

- Python 3.11 이상
- Poetry (의존성 관리)
- Docker & Docker Compose (배포용)
- Naver Cloud Platform 계정 (HyperCLOVA, CLOVA Voice)
- AWS 계정 (S3 사용)

### 1. 로컬 개발 환경

#### Step 1: 저장소 클론

```bash
git clone https://github.com/besides-508-potenday/na-T-na-AI.git
cd na-T-na-AI
```

#### Step 2: Poetry 설치 및 의존성 설치

```bash
# Poetry 설치 (미설치 시)
curl -sSL https://install.python-poetry.org | python3 -

# 의존성 설치
poetry install
```

#### Step 3: 환경 변수 설정

`.env` 파일 생성:

```bash
# Naver Cloud Platform - HyperCLOVA X
HOST=https://clovastudio.apigw.ntruss.com
CLOVASTUDIO_API_KEY=your_hyperclova_api_key
REQUEST_ID=your_request_id

# Naver Cloud Platform - CLOVA Voice
CLIENT_ID=your_clova_voice_client_id
CLIENT_SECRET=your_clova_voice_client_secret

# AWS S3
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET=your_s3_bucket_name
S3_PUBLIC=true

# Application
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

#### Step 4: 서버 실행

**FastAPI 서버 실행:**
```bash
poetry run python main.py
```

**또는 Uvicorn으로 실행:**
```bash
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Streamlit UI 실행 (별도 터미널):**
```bash
poetry run streamlit run app.py --server.port 8502
```

#### Step 5: 접속

- FastAPI Swagger UI: http://localhost:8000/docs
- Streamlit UI: http://localhost:8502
- Health Check: http://localhost:8000/health

### 2. Docker 환경

#### Step 1: Docker Compose 실행

```bash
# 빌드 및 실행
docker-compose up --build -d

# 로그 확인
docker-compose logs -f ai-be
```

#### Step 2: 접속

- API Server: http://localhost:80
- Health Check: http://localhost:80/health
- Swagger UI: http://localhost:80/docs

#### Step 3: 서비스 관리

```bash
# 중지
docker-compose stop

# 재시작
docker-compose restart

# 완전 삭제
docker-compose down -v
```

---

## 📡 API 명세

### API Swagger 문서

**온라인 문서**: [API Swagger (AI-BE)](https://www.notion.so/API-swagger-AI-BE-2453cff2c9eb80c18ed8d7dfc294b557)

**로컬 Swagger UI**: `http://localhost:8000/docs`

### 엔드포인트 개요

| Method | Endpoint | 설명 | 주요 파라미터 |
|--------|----------|------|--------------|
| GET | `/health` | 헬스체크 | - |
| POST | `/situation` | 초기 상황 생성 | user_nickname, chatbot_name, chatroom_id |
| POST | `/conversation` | 대화 턴 처리 | conversation, quiz_list, current_distance |
| POST | `/feedback` | 최종 피드백 생성 | conversation, current_distance |
| GET | `/conversations/{session_id}` | 세션 조회 | session_id |
| GET | `/conversations` | 전체 세션 조회 | - |
| GET | `/debug/logger` | 디버그 정보 | - |

### 상세 API 명세

#### 1. 상황 생성 API

```http
POST /situation
Content-Type: application/json

{
  "user_nickname": "삐롱이",
  "chatbot_name": "투닥이",
  "chatroom_id": "unique_chatroom_id"
}
```

**응답:**
```json
{
  "quiz_list": [
    "친구가 다음 주에 생일이라 깜짝 파티 준비하려는데, 정말 마음이 무거워...",
    "요즘 일이 너무 바빠서 시간 내기가 쉽지 않아... 그래서 더 초조해지고 있어.",
    "친구 몰래 다른 애들이랑 연락하면서 계획을 세워야 하니까 부담스럽기도 하고...",
    "선물도 골라야 하는데 도대체 어디서부터 시작해야 할지 감이 안 와...",
    "마음속으로는 이미 모든 게 완벽한 것 같은데, 현실은 왜 이렇게 복잡한지 모르겠어."
  ]
}
```

#### 2. 대화 API

```http
POST /conversation
Content-Type: application/json

{
  "user_nickname": "삐롱이",
  "chatbot_name": "투닥이",
  "chatroom_id": "unique_chatroom_id",
  "conversation": [
    "친구가 다음 주에 생일이라 깜짝 파티 준비하려는데, 정말 마음이 무거워...",
    "너무 걱정하지 마. 친구가 좋아할 거야."
  ],
  "quiz_list": [...],
  "current_distance": 5
}
```

**응답 (검증 성공 시):**
```json
{
  "react": "고마워… 네 말 들으니 조금 마음이 놓이는 것 같아. 😔",
  "score": 1,
  "improved_quiz": "친구 몰래 다른 애들이랑 연락하면서 계획을 세워야 하니까 부담스럽기도 하고...",
  "verification": true
}
```

**응답 (검증 실패 시):**
```json
{
  "react": "",
  "score": 0,
  "improved_quiz": "",
  "verification": false
}
```

#### 3. 피드백 API

```http
POST /feedback
Content-Type: application/json

{
  "user_nickname": "삐롱이",
  "chatbot_name": "투닥이",
  "chatroom_id": "unique_chatroom_id",
  "conversation": [...],
  "current_distance": 2
}
```

**응답:**
```json
{
  "feedback": "오늘 너랑 이야기 나누면서 따뜻한 말들을 많이 들을 수 있어서 정말 좋았어...",
  "last_greeting": "빛나는 우리의 우정을 염원하며,",
  "audio_base64": "https://your-bucket.s3.ap-northeast-2.amazonaws.com/chatrooms/results/{chatroom_id}/letter_voice.mp3"
}
```

---

## ⚙️ 환경 변수 설정

### 필수 환경 변수

#### Naver Cloud Platform

```bash
# HyperCLOVA X API
HOST=https://clovastudio.apigw.ntruss.com
CLOVASTUDIO_API_KEY=NTA0MjU2MWZlZT...  # API Gateway에서 발급
REQUEST_ID=your_request_id              # 임의의 고유 ID

# CLOVA Voice API
CLIENT_ID=your_client_id                # API Gateway Client ID
CLIENT_SECRET=your_client_secret        # API Gateway Client Secret
```

**발급 방법:**
1. [Naver Cloud Platform Console](https://console.ncloud.com/) 로그인
2. AI Services > CLOVA Studio 선택
3. API Keys 메뉴에서 키 발급

#### AWS S3

```bash
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_BUCKET=your-bucket-name
S3_PUBLIC=true  # 공개 버킷 여부
```

**S3 버킷 설정:**
```bash
# AWS CLI로 버킷 생성
aws s3 mb s3://your-bucket-name --region ap-northeast-2

# 공개 읽기 권한 설정 (선택)
aws s3api put-bucket-acl --bucket your-bucket-name --acl public-read
```

### 선택 환경 변수

```bash
# 애플리케이션
WORKERS=4                    # Uvicorn 워커 수
MAX_WORKERS=8                # 최대 워커 수
WORKER_CONNECTIONS=1000      # 워커당 연결 수
KEEPALIVE_TIMEOUT=5          # Keep-alive 타임아웃 (초)
REQUEST_TIMEOUT=30           # 요청 타임아웃 (초)

# 로깅
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
PYTHONUNBUFFERED=1           # 실시간 로그 출력

# Python 경로
PYTHONPATH=/app
```

---

## 🌐 배포

### AWS EC2 배포

#### Step 1: EC2 인스턴스 생성

**권장 스펙:**
- **인스턴스 타입**: t3.medium 이상 (2 vCPU, 4GB RAM)
- **운영체제**: Ubuntu 22.04 LTS
- **스토리지**: 20GB 이상
- **보안 그룹**: 
  - Inbound: 80 (HTTP), 443 (HTTPS), 8000 (API), 22 (SSH)

#### Step 2: 서버 초기 설정

```bash
# SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo apt install docker-compose-plugin -y

# Git 설치
sudo apt install git -y
```

#### Step 3: 프로젝트 배포

```bash
# 저장소 클론
git clone https://github.com/besides-508-potenday/na-T-na-AI.git
cd na-T-na-AI

# 환경 변수 설정
nano .env
# (위 환경 변수 설정 참고)

# Docker Compose 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

#### Step 4: 서비스 확인

```bash
# 헬스체크
curl http://your-ec2-ip/health

# 컨테이너 상태 확인
docker-compose ps
```

### 프로덕션 체크리스트

- [✅] FastAPI 서버 정상 실행
- [✅] Docker 이미지 빌드 완료
- [✅] AWS EC2 배포 완료
- [✅] S3 연동 확인
- [✅] API 응답 속도 최적화
- [✅] 로깅 시스템 구축
- [✅] 헬스체크 설정
- [✅] Rate Limiting 적용
- [✅] CORS 설정
- [✅] 에러 핸들링

---

## 💻 개발 가이드

### 코드 스타일

**Python:**
- PEP 8 준수
- Type Hints 사용
- Docstring 작성 (Google Style)

**예시:**
```python
def generate_situation_and_quiz() -> tuple[str, list[str]]:
    """
    HyperCLOVA X를 사용하여 감정 상황과 퀴즈를 생성합니다.
    
    Returns:
        tuple[str, list[str]]: (상황 설명, 5개의 감정 문장 리스트)
    
    Raises:
        Exception: API 호출 실패 시
    """
    # 구현 코드
```

### 테스트

#### 단위 테스트

```bash
# pytest 설치
poetry add --group dev pytest pytest-asyncio

# 테스트 실행
poetry run pytest tests/
```

#### API 테스트

```bash
# HTTPie 설치
pip install httpie

# 헬스체크
http GET localhost:8000/health

# 상황 생성 테스트
http POST localhost:8000/situation \
  user_nickname="테스터" \
  chatbot_name="투닥이" \
  chatroom_id="test_room_001"
```

### 성능 모니터링

**로그 확인:**
```bash
# 실시간 로그
tail -f logs/app.log

# 에러 로그
tail -f logs/error.log

# API 접근 로그
tail -f logs/access.log
```

**메트릭:**
- TPS (Tokens Per Second): HyperCLOVA 응답 속도
- API 응답 시간: 엔드포인트별 평균 응답 시간
- 메모리 사용량: 각 요청의 메모리 증감

### 프로젝트 기여 가이드

1. **Fork** 저장소
2. **Feature Branch** 생성 (`git checkout -b feature/amazing-feature`)
3. **Commit** 변경사항 (`git commit -m 'Add amazing feature'`)
4. **Push** to Branch (`git push origin feature/amazing-feature`)
5. **Pull Request** 생성

---

## 🔧 트러블슈팅

### 자주 발생하는 문제

#### 1. HyperCLOVA API 연결 실패

**증상:**
```
API Error: 401, Unauthorized
```

**해결:**
- `.env` 파일의 `CLOVASTUDIO_API_KEY` 확인
- API 키 유효기간 확인
- Request ID가 올바른지 확인

#### 2. S3 업로드 실패

**증상:**
```
S3 upload failed: ClientError
```

**해결:**
- AWS 자격증명 확인
- S3 버킷 권한 확인
- 버킷 정책에 `PutObject` 권한 추가

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

#### 3. Docker 메모리 부족

**증상:**
```
docker-compose: Container killed (OOMKilled)
```

**해결:**
- `docker-compose.yml`에서 메모리 제한 조정:
```yaml
deploy:
  resources:
    limits:
      memory: 4G  # 2G → 4G로 증가
```

#### 4. 세션 저장 실패

**증상:**
```
Session {session_id} not found in memory for saving
```

**해결:**
- `conversation_logs/` 디렉토리 권한 확인
- 디렉토리 생성:
```bash
mkdir -p conversation_logs
chmod 755 conversation_logs
```

### 디버깅 도구

#### 디버그 엔드포인트

```bash
# ConversationLogger 상태 확인
curl http://localhost:8000/debug/logger

# 특정 세션 조회
curl http://localhost:8000/conversations/{session_id}
```

#### 로그 분석

```bash
# 에러만 필터링
grep "ERROR" logs/app.log

# 특정 세션 추적
grep "session_id_here" logs/app.log

# API 응답 시간 분석
grep "total_time" logs/app.log | awk '{print $NF}'
```

<!-- ---

## 📈 향후 계획

- [ ] 멀티 턴 대화 심화 학습
- [ ] 사용자별 통계 대시보드
- [ ] 모바일 앱 개발
- [ ] 다국어 지원
- [ ] 실시간 음성 대화 기능 -->

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
