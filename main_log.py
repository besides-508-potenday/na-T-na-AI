from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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
import aiofiles

print(os.getcwd())
# os.chdir('/Users/hongbikim/Dev/natna/')

from chat import generate_situation_and_quiz, generate_verification_and_score, generate_response, improved_question, generate_feedback

# 로깅 설정 모듈
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import logging.config

# =============================================================================
# 데이터 저장 클래스
# =============================================================================
class ChatDataStorage:
    def __init__(self, storage_dir: str = "chat_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
    def _get_user_file_path(self, user_nickname: str, chatbot_name: str) -> Path:
        """사용자별 파일 경로 생성"""
        safe_filename = f"{user_nickname}_{chatbot_name}".replace(" ", "_").replace("/", "_")
        file_path = self.storage_dir / f"{safe_filename}.json"
        print(f"Generated file path: {file_path.absolute()}")  # 디버깅용
        return file_path
    
    async def load_user_data(self, user_nickname: str, chatbot_name: str) -> Dict:
        """사용자 데이터 로드"""
        file_path = self._get_user_file_path(user_nickname, chatbot_name)
        
        if not file_path.exists():
            print(f"File does not exist, creating new data structure: {file_path}")  # 디버깅용
            return {
                "user_nickname": user_nickname,
                "chatbot_name": chatbot_name,
                "sessions": [],
                "total_score": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                print(f"Successfully loaded data from: {file_path}")  # 디버깅용
                return json.loads(content)
        except Exception as e:
            logging.getLogger(__name__).error(f"Error loading user data: {e}")
            print(f"Error loading data: {e}")  # 디버깅용
            return {
                "user_nickname": user_nickname,
                "chatbot_name": chatbot_name,
                "sessions": [],
                "total_score": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
    
    async def save_user_data(self, user_nickname: str, chatbot_name: str, data: Dict):
        """사용자 데이터 저장"""
        file_path = self._get_user_file_path(user_nickname, chatbot_name)
        data["updated_at"] = datetime.now().isoformat()
        
        try:
            print(f"Attempting to save data to: {file_path}")  # 디버깅용
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            print(f"Successfully saved data to: {file_path}")  # 디버깅용
            
            # 파일이 실제로 저장되었는지 확인
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"File saved with size: {file_size} bytes")
            else:
                print("ERROR: File was not created!")
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Error saving user data: {e}")
            print(f"Error saving data: {e}")  # 디버깅용
    
    async def set_quiz_list(self, user_nickname: str, chatbot_name: str, quiz_list: List[str]):
        """퀴즈 리스트 설정 및 새 세션 시작"""
        print(f"Setting quiz list for {user_nickname} with {chatbot_name}")  # 디버깅용
        data = await self.load_user_data(user_nickname, chatbot_name)
        
        # 새 세션 시작
        new_session = {
            "session_id": len(data["sessions"]) + 1,
            "started_at": datetime.now().isoformat(),
            "quiz_list": quiz_list,
            "conversation_history": [],
            "scores": [],
            "total_session_score": 0,
            "completed": False
        }
        data["sessions"].append(new_session)
        
        await self.save_user_data(user_nickname, chatbot_name, data)
        print(f"Quiz list set successfully for session {new_session['session_id']}")  # 디버깅용
        return data
    
    async def add_conversation_turn(self, user_nickname: str, chatbot_name: str, 
                                 conversation: List[str], score: int, improved_quiz: str = "",
                                 verification: bool = True):
        """대화 턴 추가"""
        print(f"Adding conversation turn for {user_nickname} with {chatbot_name}, score: {score}")  # 디버깅용
        data = await self.load_user_data(user_nickname, chatbot_name)
        
        # 현재 활성 세션 찾기
        current_session = None
        if data["sessions"] and not data["sessions"][-1].get("completed", False):
            current_session = data["sessions"][-1]
        else:
            # 활성 세션이 없으면 임시 세션 생성
            current_session = {
                "session_id": len(data["sessions"]) + 1,
                "started_at": datetime.now().isoformat(),
                "quiz_list": [],
                "conversation_history": [],
                "scores": [],
                "total_session_score": 0,
                "completed": False
            }
            data["sessions"].append(current_session)
        
        # 대화 기록 추가
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "conversation": conversation.copy(),
            "score": score,
            "improved_quiz": improved_quiz,
            "verification": verification
        }
        
        current_session["conversation_history"].append(conversation_entry)
        if verification:  # 검증 성공한 경우만 점수 추가
            current_session["scores"].append(score)
        current_session["total_session_score"] = sum(current_session["scores"])
        
        # 전체 점수 업데이트
        data["total_score"] = sum(session["total_session_score"] for session in data["sessions"])
        
        await self.save_user_data(user_nickname, chatbot_name, data)
        print(f"Conversation turn added successfully")  # 디버깅용
        return data
    
    async def complete_session(self, user_nickname: str, chatbot_name: str, feedback: str = "", last_greeting: str = ""):
        """세션 완료 처리"""
        print(f"Completing session for {user_nickname} with {chatbot_name}")  # 디버깅용
        data = await self.load_user_data(user_nickname, chatbot_name)
        
        if data["sessions"] and not data["sessions"][-1].get("completed", False):
            data["sessions"][-1]["completed"] = True
            data["sessions"][-1]["completed_at"] = datetime.now().isoformat()
            data["sessions"][-1]["feedback"] = feedback
            data["sessions"][-1]["last_greeting"] = last_greeting
            
            await self.save_user_data(user_nickname, chatbot_name, data)
            print(f"Session completed successfully")  # 디버깅용
        
        return data

# 전역 스토리지 인스턴스
storage = ChatDataStorage()

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
    description="This is a FastAPI application for AI-BE with data storage.",
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
# 백그라운드 태스크 함수들
# =============================================================================
async def save_quiz_list_background(user_nickname: str, chatbot_name: str, quiz_list: List[str]):
    """백그라운드에서 퀴즈 리스트 저장"""
    try:
        print(f"Background task: Saving quiz list for {user_nickname} with {chatbot_name}")  # 디버깅용
        await storage.set_quiz_list(user_nickname, chatbot_name, quiz_list)
        logger.info(f"Quiz list saved for {user_nickname} with {chatbot_name}")
        print(f"Quiz list saved successfully in background task")  # 디버깅용
    except Exception as e:
        logger.error(f"Error saving quiz list: {e}")
        print(f"Error in background quiz list save: {e}")  # 디버깅용

async def save_conversation_background(user_nickname: str, chatbot_name: str, 
                                     conversation: List[str], score: int, improved_quiz: str = "",
                                     verification: bool = True):
    """백그라운드에서 대화 저장"""
    try:
        print(f"Background task: Saving conversation for {user_nickname} with {chatbot_name}")  # 디버깅용
        await storage.add_conversation_turn(user_nickname, chatbot_name, conversation, score, improved_quiz, verification)
        logger.info(f"Conversation saved for {user_nickname} with {chatbot_name}, score: {score}")
        print(f"Conversation saved successfully in background task")  # 디버깅용
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        print(f"Error in background conversation save: {e}")  # 디버깅용

async def save_feedback_background(user_nickname: str, chatbot_name: str, feedback: str, last_greeting: str = ""):
    """백그라운드에서 피드백 저장"""
    try:
        print(f"Background task: Saving feedback for {user_nickname} with {chatbot_name}")  # 디버깅용
        await storage.complete_session(user_nickname, chatbot_name, feedback, last_greeting)
        logger.info(f"Session completed for {user_nickname} with {chatbot_name}")
        print(f"Feedback saved successfully in background task")  # 디버깅용
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        print(f"Error in background feedback save: {e}")  # 디버깅용

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
        
        # 비동기로 퀴즈 생성
        situation, quiz_list = await async_generate_situation_and_quiz()
        logger.info(f"Situation generated: {situation}")
        logger.info(f"Quiz list generated for user: {nickname}")
        print(f"Quiz list generated: {quiz_list}")  # 디버깅용
        
        # # 백그라운드에서 퀴즈 리스트 저장
        # background_tasks.add_task(save_quiz_list_background, nickname, chatbot_name, quiz_list)
        # print(f"Background task added for quiz list save")  # 디버깅용

        try:
            print(f"Immediately saving quiz list...")
            await storage.set_quiz_list(nickname, chatbot_name, quiz_list)
            print(f"✅ Quiz list saved successfully")
        except Exception as save_error:
            print(f"❌ Failed to save quiz list: {save_error}")
            logger.error(f"Failed to save quiz list: {save_error}")
            # 저장 실패해도 응답은 반환 (사용자 경험 유지)

        return {"quiz_list": quiz_list}
        
    except Exception as e:
        logger.error(f"Error in situation endpoint: {str(e)}", exc_info=True)
        print(f"Error in situation endpoint: {str(e)}")  # 디버깅용
        raise HTTPException(status_code=500, detail="Internal server error")

# 2. Conversaion
@app.post("/conversation", response_class = JSONResponse)
async def conversation(request: Conversation, background_tasks: BackgroundTasks):
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
            # 검증 실패시에도 기록 (점수 0, verification False로)
            background_tasks.add_task(save_conversation_background, user_nickname, chatbot_name, 
                                    conversation, 0, "", False)
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

            # # 백그라운드에서 대화 저장 (검증 성공)
            # background_tasks.add_task(save_conversation_background, user_nickname, chatbot_name, 
            #                         conversation, score, improved_quiz, True)
            # print(f"Verification passed, saving with score {score}")  # 디버깅용
            try:
                print(f"Verification passed, saving with score {score}...")
                await storage.add_conversation_turn(user_nickname, chatbot_name, 
                                                 conversation, score, improved_quiz, True)
                print(f"✅ Successful conversation saved")
            except Exception as save_error:
                print(f"❌ Failed to save successful conversation: {save_error}")
                logger.error(f"Failed to save successful conversation: {save_error}")

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
async def feedback(request: Feedback, background_tasks: BackgroundTasks):
    try:
        user_nickname = request.user_nickname
        chatbot_name = request.chatbot_name
        conversation = request.conversation
        current_distance = request.current_distance
        
        logger.info(f"Processing feedback for user: {user_nickname} with chatbot: {chatbot_name}, distance: {current_distance}")
        print(f"=== FEEDBACK ENDPOINT CALLED ===")  # 디버깅용
        print(f"User: {user_nickname}, Chatbot: {chatbot_name}")  # 디버깅용
        
        # 비동기로 피드백 생성
        first_greeting, text, last_greeting = await async_generate_feedback(conversation, chatbot_name, user_nickname)

        # # 백그라운드에서 세션 완료 처리
        # background_tasks.add_task(save_feedback_background, user_nickname, chatbot_name, text, last_greeting)
        # print(f"Background task added for feedback save")  # 디버깅용

        try:
            print(f"Saving feedback and completing session...")
            await storage.complete_session(user_nickname, chatbot_name, text, last_greeting)
            print(f"✅ Session completed and feedback saved")
        except Exception as save_error:
            print(f"❌ Failed to save feedback: {save_error}")
            logger.error(f"Failed to save feedback: {save_error}")

        return {
                "feedback": text,
                "last_greeting": last_greeting
                }
        
    except Exception as e:
        logger.error(f"Error in feedback endpoint: {str(e)}", exc_info=True)
        print(f"Error in feedback endpoint: {str(e)}")  # 디버깅용
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# 추가: 저장 상태 확인을 위한 디버깅 엔드포인트
# =============================================================================

@app.get("/debug/files")
async def debug_files():
    """chat_data 폴더의 모든 파일 나열"""
    try:
        files = []
        chat_data_dir = Path("chat_data")
        
        if chat_data_dir.exists():
            for file_path in chat_data_dir.glob("*.json"):
                try:
                    stat = file_path.stat()
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    files.append({
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "user_nickname": data.get("user_nickname", "unknown"),
                        "chatbot_name": data.get("chatbot_name", "unknown"),
                        "total_sessions": len(data.get("sessions", [])),
                        "total_score": data.get("total_score", 0)
                    })
                except Exception as e:
                    files.append({
                        "filename": file_path.name,
                        "error": str(e)
                    })
        
        return {
            "chat_data_exists": chat_data_dir.exists(),
            "chat_data_path": str(chat_data_dir.absolute()),
            "file_count": len(files),
            "files": files
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/debug/test-save")
async def debug_test_save():
    """저장 기능 테스트"""
    try:
        test_user = "debug_user"
        test_bot = "debug_bot"
        
        print(f"Testing save functionality for {test_user} with {test_bot}")
        
        # 테스트 데이터로 저장 시도
        await storage.set_quiz_list(test_user, test_bot, ["테스트 질문 1", "테스트 질문 2"])
        
        # 대화 추가 테스트
        await storage.add_conversation_turn(
            test_user, test_bot, 
            ["안녕하세요", "안녕하세요! 반갑습니다."], 
            15, 
            "개선된 질문", 
            True
        )
        
        # 세션 완료 테스트
        await storage.complete_session(test_user, test_bot, "테스트 피드백", "안녕히 가세요!")
        
        # 저장된 데이터 확인
        saved_data = await storage.load_user_data(test_user, test_bot)
        
        return {
            "success": True,
            "message": "Test save completed",
            "saved_data": saved_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =============================================================================
# 간단한 테스트용 엔드포인트
# =============================================================================

@app.get("/test-simple-save")
async def test_simple_save():
    """가장 간단한 저장 테스트"""
    try:
        file_path = Path("chat_data") / "simple_test.json"
        test_data = {
            "message": "Hello from FastAPI!",
            "timestamp": datetime.now().isoformat()
        }
        
        # 동기식으로 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        # 파일 존재 확인
        exists = file_path.exists()
        size = file_path.stat().st_size if exists else 0
        
        return {
            "success": True,
            "file_created": exists,
            "file_size": size,
            "file_path": str(file_path.absolute())
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
# =============================================================================
# 시작점
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting FastAPI application with data storage...")
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