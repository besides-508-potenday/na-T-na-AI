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
import uuid

print(os.getcwd())
# os.chdir('/Users/hongbikim/Dev/natna/')

from chat import generate_situation_and_quiz, generate_verification_and_score, generate_response, improved_question, generate_feedback

# 로깅 설정 모듈
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import logging.config
# =============================================================================
# JSON 대화 기록 관리 클래스
# =============================================================================
class ConversationLogger:
    def __init__(self, log_dir: str = "conversation_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.sessions = {}  # session_id -> conversation_data
        self.user_sessions = {}  # user_nickname -> session_id (최근 세션 추적)
    
    def get_or_create_session(self, user_nickname: str, chatbot_name: str) -> str:
        """기존 세션을 찾거나 새로운 세션을 생성"""
        # 기존 세션이 있는지 확인
        if user_nickname in self.user_sessions:
            session_id = self.user_sessions[user_nickname]
            if session_id in self.sessions:
                return session_id
        
        # 새로운 세션 생성
        return self.create_session(user_nickname, chatbot_name)
    
    def create_session(self, user_nickname: str, chatbot_name: str) -> str:
        """새로운 대화 세션 생성"""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        session_data = {
            "session_id": session_id,
            "user_nickname": user_nickname,
            "chatbot_name": chatbot_name,
            "start_time": timestamp,
            "current_distance": 10,  # 초기값
            "situation": "",
            "quiz_list": [],
            "conversation_log": [],
            "scores": [],
            "reactions": [],
            "improved_quizzes": [],
            "verification_results": [],
            "final_feedback": {},
            "end_time": None
        }
        
        self.sessions[session_id] = session_data
        self.user_sessions[user_nickname] = session_id  # 사용자별 최근 세션 추적
        self._save_session(session_id)
        return session_id
    
    def update_situation(self, session_id: str, situation: str, quiz_list: List[str]):
        """상황 및 퀴즈 리스트 업데이트"""
        if session_id in self.sessions:
            self.sessions[session_id]["situation"] = situation
            self.sessions[session_id]["quiz_list"] = quiz_list
            self._save_session(session_id)
    
    def add_conversation_turn(self, session_id: str, user_message: str, bot_message: str, 
                            score: int, react: str, improved_quiz: str, verification: bool):
        """대화 턴 추가"""
        if session_id in self.sessions:
            session_data = self.sessions[session_id]
            
            # current_distance 업데이트
            if score == 0:
                session_data["current_distance"] -= 1
            # score == 1이면 거리 유지
            
            # 대화 기록 추가
            turn_data = {
                "timestamp": datetime.now().isoformat(),
                "user_message": user_message,
                "bot_message": bot_message,
                "score": score,
                "react": react,
                "improved_quiz": improved_quiz,
                "verification": verification,
                "current_distance": session_data["current_distance"]
            }
            
            session_data["conversation_log"].append(turn_data)
            session_data["scores"].append(score)
            session_data["reactions"].append(react)
            session_data["improved_quizzes"].append(improved_quiz)
            session_data["verification_results"].append(verification)
            
            self._save_session(session_id)
    
    def add_feedback(self, session_id: str, feedback: str, last_greeting: str):
        """최종 피드백 추가"""
        if session_id in self.sessions:
            self.sessions[session_id]["final_feedback"] = {
                "feedback": feedback,
                "last_greeting": last_greeting,
                "timestamp": datetime.now().isoformat()
            }
            self.sessions[session_id]["end_time"] = datetime.now().isoformat()
            self._save_session(session_id)
    
    def get_session_data(self, session_id: str) -> Dict:
        """세션 데이터 조회"""
        return self.sessions.get(session_id, {})
    
    def _save_session(self, session_id: str):
        """세션을 JSON 파일로 저장"""
        if session_id in self.sessions:
            file_path = self.log_dir / f"{session_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.sessions[session_id], f, ensure_ascii=False, indent=2)
    
    def get_all_sessions(self) -> List[Dict]:
        """모든 세션 데이터 조회"""
        return list(self.sessions.values())

# 전역 conversation logger 인스턴스
conversation_logger = ConversationLogger()

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


# 1. situation
@app.post("/situation", response_class = JSONResponse)
async def situation(request: Situation, background_tasks: BackgroundTasks):
    try:
        nickname = request.user_nickname
        chatbot_name = request.chatbot_name
        logger.info(f"Starting situation generation for user: {nickname} with chatbot: {chatbot_name}")
        print(f"=== SITUATION ENDPOINT CALLED ===")  # 디버깅용
        print(f"User: {nickname}, Chatbot: {chatbot_name}")  # 디버깅용

        # 자동으로 세션 생성 (기존 세션이 있으면 재사용)
        session_id = conversation_logger.get_or_create_session(nickname, chatbot_name)
        
        # 비동기로 퀴즈 생성
        situation, quiz_list = await async_generate_situation_and_quiz()
        logger.info(f"Situation generated: {situation}")
        logger.info(f"Quiz list generated for user: {nickname}")
        print(f"Quiz list generated: {quiz_list}")  # 디버깅용

        # 세션에 상황과 퀴즈 리스트 저장
        conversation_logger.update_situation(session_id, situation, quiz_list)

        return {"quiz_list": quiz_list}
        
    except Exception as e:
        logger.error(f"Error in situation endpoint: {str(e)}", exc_info=True)
        print(f"Error in situation endpoint: {str(e)}")  # 디버깅용
        raise HTTPException(status_code=500, detail="Internal server error")



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

        # 현재 사용자의 세션 ID 가져오기
        session_id = conversation_logger.get_or_create_session(user_nickname, chatbot_name)

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

            # 실패한 경우에도 기록
            user_message = conversation[-1] if conversation else ""
            conversation_logger.add_conversation_turn(
                session_id, user_message, "", 0, "", "", False
            )

            return {
                "react": "",
                "score": 0,
                "improved_quiz": "",
                "verification" : False
            }
        else:
            statement = await async_generate_response(conversation, score, chatbot_name, user_nickname)
            improved_quiz = await async_improved_question(quiz_list, conversation, statement, chatbot_name)

            # 성공한 경우 기록
            user_message = conversation[-1] if conversation else ""
            bot_message = f"{statement} {improved_quiz}".strip()
            conversation_logger.add_conversation_turn(
                session_id, user_message, bot_message, score, statement, improved_quiz, True
            )
             
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

        # 현재 사용자의 세션 ID 가져오기
        session_id = conversation_logger.get_or_create_session(user_nickname, chatbot_name)
        
        # 비동기로 피드백 생성
        first_greeting, text, last_greeting, audio_base64 = await async_generate_feedback(conversation, current_distance, chatbot_name, user_nickname)

        # 피드백 기록
        conversation_logger.add_feedback(session_id, text, last_greeting)

        return {
                "feedback": text,
                "last_greeting": last_greeting,
                "feedback_mp3_file": audio_base64
                }
        
    except Exception as e:
        logger.error(f"Error in feedback endpoint: {str(e)}", exc_info=True)
        print(f"Error in feedback endpoint: {str(e)}")  # 디버깅용
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# 추가: 대화 기록 조회 엔드포인트
# =============================================================================
@app.get("/conversations/{session_id}")
async def get_conversation(session_id: str):
    """특정 세션의 대화 기록 조회"""
    session_data = conversation_logger.get_session_data(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_data

@app.get("/conversations")
async def get_all_conversations():
    """모든 대화 기록 조회"""
    return conversation_logger.get_all_sessions()

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