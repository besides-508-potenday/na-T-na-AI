from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uvicorn
import logging
import time
import os
import json
from datetime import datetime
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextlib

print(os.getcwd())
# os.chdir('/Users/hongbikim/Dev/natna/')

from chat import generate_situation_and_quiz, generate_verification_and_score, generate_response, improved_question, generate_feedback

# 로깅 설정 모듈
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import logging.config

# =============================================================================
# 로깅 설정
# =============================================================================
def setup_logging():
    """로깅 설정 함수"""
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 로깅 설정 딕셔너리
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file_info": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": "logs/app.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 30,
                "encoding": "utf-8"
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "access_log": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": "logs/access.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 30,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "": {  # root logger
                "level": "INFO",
                "handlers": ["console", "file_info", "file_error"]
            },
            "access": {
                "level": "INFO",
                "handlers": ["access_log"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "access_log"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # 커스텀 JSON 포매터
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
            
            if hasattr(record, 'request_id'):
                log_entry["request_id"] = record.request_id
            if hasattr(record, 'user_id'):
                log_entry["user_id"] = record.user_id
            if hasattr(record, 'extra_data'):
                log_entry["extra_data"] = record.extra_data
                
            return json.dumps(log_entry, ensure_ascii=False)
    
    # JSON 핸들러에 커스텀 포매터 적용
    for handler in logging.getLogger("access").handlers:
        if isinstance(handler, TimedRotatingFileHandler):
            handler.setFormatter(JSONFormatter())
            break

# 로깅 설정 실행
setup_logging()
logger = logging.getLogger(__name__)
access_logger = logging.getLogger("access")


# =============================================================================
# Thread Pool 설정 (CPU 집약적 작업용)
# =============================================================================
executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 2)

# =============================================================================
# 미들웨어 추가
# =============================================================================
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    logger.info("Application startup")
    yield
    # 종료 시 실행
    logger.info("Application shutdown")
    executor.shutdown(wait=True)

# =============================================================================
# Pydantic 모델들
# =============================================================================
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"

class Situation(BaseModel):
    user_nickname: str
    chatbot_name: str

class Conversation(BaseModel):
    user_nickname: str
    chatbot_name: str
    conversation: List[str]
    quiz_list: List[str]
    current_distance: int

class Feedback(BaseModel):
    user_nickname: str
    chatbot_name: str
    conversation: List[str]
    current_distance: int

# =============================================================================
# 요청 제한 미들웨어
# =============================================================================
class RateLimitMiddleware:
    def __init__(self, calls: int = 100, period: int = 60):
        self.calls = calls
        self.period = period
        self.requests = {}

    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # 만료된 요청 정리
        self.requests = {
            ip: [req_time for req_time in times if now - req_time < self.period]
            for ip, times in self.requests.items()
        }
        
        # 현재 IP의 요청 수 확인
        if client_ip in self.requests:
            if len(self.requests[client_ip]) >= self.calls:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"}
                )
            self.requests[client_ip].append(now)
        else:
            self.requests[client_ip] = [now]
        
        response = await call_next(request)
        return response

# =============================================================================
# FastAPI 앱 설정
# =============================================================================

app = FastAPI(
    title="API Swagger (AI-BE)",
    description="This is a FastAPI application for AI-BE.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

origins = [
    "https://petstore.swagger.io",  # Swagger 공식 UI
    "http://localhost:8000",        # 로컬 접근도 허용
    "http://localhost",
    "http://localhost:80",
]

# origins = [
#     "https://yourdomain.com",       # 실제 프론트엔드 도메인
#     "https://api.yourdomain.com",   # API 도메인
#     "https://petstore.swagger.io",  # Swagger (필요시)
#     # 개발환경은 제거하거나 환경변수로 분리
# ]
# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins= origins, # ["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting 미들웨어 추가
rate_limiter = RateLimitMiddleware(calls=300, period=60)  # 분당 300회로 증가
app.middleware("http")(rate_limiter)


# =============================================================================
# 헬스체크 엔드포인트
# =============================================================================
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# =============================================================================
# 비동기 래퍼 함수들
# =============================================================================
async def async_generate_situation_and_quiz():
    """비동기로 상황 생성"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_situation_and_quiz)

async def async_generate_verification_and_score(conversation, chatbot_name, user_nickname):
    """비동기로 응답 생성"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_verification_and_score, conversation, chatbot_name, user_nickname)

async def async_generate_response(conversation, score, chatbot_name, user_nickname):
    """비동기로 응답 생성"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_response,conversation, score, chatbot_name, user_nickname)

async def async_improved_question(quiz_list, conversation, react, chatbot_name):
    """비동기로 응답 생성"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, improved_question, quiz_list, conversation, react, chatbot_name)

async def async_generate_feedback(conversation, current_distance, chatbot_name, user_nickname):
    """비동기로 피드백 생성"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_feedback, conversation, current_distance, chatbot_name, user_nickname)


# =============================================================================
# API 엔드포인트들
# =============================================================================

"""
{
  "user_nickname": "삐롱이",
  "chatbot_name": "투닥이"
}
"""

# 1. situation
@app.post("/situation", response_class = JSONResponse)
async def situation(request: Situation, background_tasks: BackgroundTasks):
    try:
        nickname = request.user_nickname
        chatbot_name = request.chatbot_name
        logger.info(f"Starting situation generation for user: {nickname} with chatbot: {chatbot_name}")
        print(f"=== SITUATION ENDPOINT CALLED ===")  # 디버깅용
        print(f"User: {nickname}, Chatbot: {chatbot_name}")  # 디버깅용
        
        # 비동기로 퀴즈 생성
        situation, quiz_list = await async_generate_situation_and_quiz()
        logger.info(f"Situation generated: {situation}")
        logger.info(f"Quiz list generated for user: {nickname}")
        print(f"Quiz list generated: {quiz_list}")  # 디버깅용

        return {"quiz_list": quiz_list}
        
    except Exception as e:
        logger.error(f"Error in situation endpoint: {str(e)}", exc_info=True)
        print(f"Error in situation endpoint: {str(e)}")  # 디버깅용
        raise HTTPException(status_code=500, detail="Internal server error")

"""
{
  "user_nickname": "삐롱이",
  "chatbot_name": "투닥이",
  "conversation": [
    "안녕... 나 할말 있어... 오랜만에 만나는 건 좋은데, 막상 만나면 할 말도 없고 어색하면 어쩌지?", "괜찮아."
  ],
  "quiz_list": [
    "오랜만에 만나는 건 좋은데, 막상 만나면 할 말도 없고 어색하면 어쩌지?",
    "어디서부터 말을 꺼내야 할지 모르겠어... 그냥 조용히 있다가 오게 될까 봐 무섭다...",
    "친구도 바쁘니까 자주 못 봤는데, 어색해지지 않을까 걱정이야.",
    "내가 먼저 말 걸어볼까 싶다가도 괜히 이상한 말 할까봐 두려워...",
    "옛날엔 이렇게까지 어색하지 않았는데, 지금은 왜 이렇게 떨리지?",
    "너라면 이런 상황에서 어떻게 하겠어...?",
    "우리 사이가 예전 같지 않으면 어쩌나 싶어...",
    "막상 만나면 서로 웃으면서 대화할 수 있을까?",
    "이렇게 긴장되는 게 나만 그런 걸까...",
    "괜히 약속 잡았나 싶기도 하고..."
  ],
  "current_distance": 9
}
"""


# 2. Conversaion
@app.post("/conversation", response_class = JSONResponse)
async def conversation(request: Conversation):
    try:
        user_nickname = request.user_nickname
        chatbot_name = request.chatbot_name
        conversation = request.conversation
        quiz_list = request.quiz_list
        current_distance = request.current_distance
        
        logger.info(f"Processing conversation for user: {user_nickname} with chatbot: {chatbot_name}, distance: {current_distance}")
        print(f"=== CONVERSATION ENDPOINT CALLED ===")  # 디버깅용
        print(f"User: {user_nickname}, Chatbot: {chatbot_name}")  # 디버깅용

        # 비동기로 응답 생성
        try:
            verification, score = await async_generate_verification_and_score(
                conversation, chatbot_name, user_nickname
            )
        except Exception as e:
            logger.error(f"Error generating verification and score: {str(e)}", exc_info=True)
            try:
                verification, score = await async_generate_verification_and_score(
                    conversation, chatbot_name, user_nickname
                )
            except Exception as e:
                logger.error(f"Retry failed: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal server error")
        if verification == False:
            print(f"Verification failed, saving with score 0")  # 디버깅용
            return {
                "react": "",
                "score": 0,
                "improved_quiz": "",
                "verification" : False
            }
        else:
            statement = await async_generate_response(conversation, score, chatbot_name, user_nickname)
            improved_quiz = await async_improved_question(quiz_list, conversation, statement, chatbot_name)


            return {
                "react": statement,
                "score": score,
                "improved_quiz": improved_quiz,
                "verification" : True
            }
        
    except Exception as e:
        logger.error(f"Error in conversation endpoint: {str(e)}", exc_info=True)
        print(f"Error in conversation endpoint: {str(e)}")  # 디버깅용
        raise HTTPException(status_code=500, detail="Internal server error")

"""
{
  "user_nickname": "삐롱이",
  "chatbot_name": "투닥이",
  "conversation": [
    "친구가 다음 주에 생일이라 깜짝 파티 준비하려는데, 정말 마음이 무거워...",
    "왜?",
    "음... 그냥 모든 게 잘 안 풀릴 것 같아서 그런가 봐. 친구가 좋아할지 모르겠어... 요즘 일이 너무 바빠서 시간 내기가 쉽지 않아... 그래서 더 초조해지고 있어.",
    "마음이 중요한거지. 너무 걱정하지마",
    "고마워… 네 말 들으니 조금 마음이 놓이는 것 같아. 😔 친구 몰래 다른 애들이랑 연락하면서 계획을 세워야 하니까 부담스럽기도 하고...",
    "들키면 어때!",
    "그렇지만 들키는 게 무서운 걸 어떡해… 😢 그냥 너무 걱정돼... 선물도 골라야 하는데 도대체 어디서부터 시작해야 할지 감이 안 와...",
    "친구가 좋아하는거 뭐야? 알고 있어?",
    "아, 그렇구나! 네 친구가 뭘 좋아하는지 알면 선물을 고르기 더 쉬울 거 같아! 🤔 마음속으로는 이미 모든 게 완벽한 것 같은데, 현실은 왜 이렇게 복잡한지 모르겠어.",
    "친구 생일 준비로 이렇게 스트레스 받으면 어떡해.",
    "스트레스 받는 것도 당연하지... 친구를 생각하는 마음이 그만큼 크다는 뜻이니까! 😢 조금만 더 힘내자! 이런 상황 속에서 그냥 도망치고 싶을 때도 많아... 하지만 친구 생각하면 그럴 수 없잖아?",
    "아닠ㅋㅋㅋㅋ 친구 생일 준비하는데 도망치고 싶으면 그냥 하지마",
    "그렇게 말해주니 좀 섭섭하다…😞 내가 얼마나 열심히 준비하고 있는 건데! 가끔씩 이럴 때마다 내가 진짜 뭘 할 수 있을까 의심하게 돼...",
    "의심하지마!",
    "고마워… 네가 그렇게 말해줘서 마음이 조금 나아졌어! 😄 그래도 항상 응원해 주는 너 덕분에 힘이 나! 그래도 이번엔 꼭 특별한 날을 만들어주고 싶어... 그게 내 욕심일까?",
    "하... 나도 이제 모르겠다.",
    "그렇게 말하는 걸 보니 많이 힘들었나 보네... 내가 더 도와줄 수 있는 게 있을까? 😔 혹시 나도 모르게 스트레스를 받고 있어서 그런 걸까...?",
    "너가 힘들다며...",
    "정말 나 때문에 힘든 거야? 너무 미안해… 😢 네 마음이 편해질 방법이 있으면 좋겠어. 결국 난 친구에게 좋은 시간을 선사하기 위해 최선을 다할 거지만, 지금은 조금 지쳐있는 것 같아... 이해해줬으면 좋겠다.",
    "이해 못해"
  ],
  "current_distance": 7
}

"""

# 3. Feedback
@app.post("/feedback", response_class = JSONResponse)
async def feedback(request: Feedback):
    try:
        user_nickname = request.user_nickname
        chatbot_name = request.chatbot_name
        conversation = request.conversation
        current_distance = request.current_distance
        
        logger.info(f"Processing feedback for user: {user_nickname} with chatbot: {chatbot_name}, distance: {current_distance}")
        print(f"=== FEEDBACK ENDPOINT CALLED ===")  # 디버깅용
        print(f"User: {user_nickname}, Chatbot: {chatbot_name}")  # 디버깅용
        
        # 비동기로 피드백 생성
        first_greeting, text, last_greeting = await async_generate_feedback(conversation, current_distance, chatbot_name, user_nickname)

        return {
                "feedback": text,
                "last_greeting": last_greeting
                }
        
    except Exception as e:
        logger.error(f"Error in feedback endpoint: {str(e)}", exc_info=True)
        print(f"Error in feedback endpoint: {str(e)}")  # 디버깅용
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# 시작점
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting FastAPI application...")
    # 프로덕션 환경용 설정
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,        # 프로덕션에서는 반드시 False
        workers=4,           # CPU 코어 수에 맞춰 조정 (일반적으로 2 * CPU 코어 + 1)
        access_log=True,     # 프로덕션에서는 로그 활성화
        log_config=None,
        loop="uvloop",       # 성능 향상을 위한 uvloop 사용 (Linux/macOS)
        http="httptools",    # HTTP 파싱 성능 향상
        backlog=2048,        # 대기 중인 연결 수 증가
        timeout_keep_alive=30,  # Keep-alive 타임아웃
        limit_concurrency=200,  # 동시 연결 제한
        limit_max_requests=1000,  # 워커당 최대 요청 수 (메모리 누수 방지)
    )