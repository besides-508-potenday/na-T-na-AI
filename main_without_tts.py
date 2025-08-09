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
import unicodedata


from chat_without_tts import generate_situation_and_quiz, generate_verification_and_score, generate_response, improved_question, generate_feedback

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
        self.sessions = {}
        self.user_sessions = {}
        print(f"ConversationLogger initialized with log_dir: {self.log_dir.absolute()}")
        self._load_existing_sessions()

    def _load_existing_sessions(self):
        """기존 JSON 파일들을 메모리에 로드"""
        try:
            json_files = list(self.log_dir.glob("*.json"))
            print(f"Found {len(json_files)} existing session files")
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        session_id = session_data.get("session_id")
                        user_nickname = session_data.get("user_nickname")
                        if session_id and user_nickname:
                            self.sessions[session_id] = session_data
                            self.user_sessions[user_nickname] = session_id
                            print(f"Loaded session: {session_id} for user: {user_nickname}")
                except Exception as e:
                    print(f"Error loading session file {json_file}: {e}")
        except Exception as e:
            print(f"Error in _load_existing_sessions: {e}")

    def get_or_create_session(self, user_nickname: str, chatbot_name: str) -> str:
        """기존 세션을 찾거나 새로운 세션을 생성"""
        try:
            user_nickname = unicodedata.normalize("NFC", user_nickname.strip())
            chatbot_name = unicodedata.normalize("NFC", chatbot_name.strip())

            key = f"{user_nickname}__{chatbot_name}"
            print(f"🔍 Getting session for: {key}")
            
            # 이미 등록된 세션이 있다면 그대로 사용
            if key in self.user_sessions:
                session_id = self.user_sessions[key]
                if session_id in self.sessions:
                    print(f"✅ Existing session found: {session_id}")
                    return session_id
                else:
                    print(f"⚠️ Session ID reference exists, but data missing. Creating new session.")

            # 없으면 새로 생성
            print(f"🔧 Creating new session...")
            new_session_id = self.create_session(user_nickname, chatbot_name)
            self.user_sessions[key] = new_session_id
            print(f"✅ Created and stored session: {new_session_id}")
            return new_session_id

        except Exception as e:
            print(f"❌ Error in get_or_create_session: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return f"emergency_{user_nickname}_{int(time.time())}"

    # def get_or_create_session(self, user_nickname: str, chatbot_name: str) -> str:
    #     """새로운 세션을 무조건 생성"""
    #     try:
    #         print(f"🔧 Always creating new session for user: {user_nickname}, chatbot: {chatbot_name}")
    #         new_session_id = self.create_session(user_nickname, chatbot_name)
    #         print(f"✅ Created new session: {new_session_id}")
    #         return new_session_id
            
    #     except Exception as e:
    #         print(f"❌ Error in get_or_create_session: {str(e)}")
    #         import traceback
    #         print(f"❌ Full traceback: {traceback.format_exc()}")
            
    #         # 에러 발생 시 임시 세션 ID 반환
    #         temp_session_id = f"emergency_{user_nickname}_{int(time.time())}"
    #         print(f"🚨 Returning emergency session ID: {temp_session_id}")
    #         return temp_session_id
    
        except Exception as e:
            print(f"❌ Error in get_or_create_session: {str(e)}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            
            # 에러 발생 시 임시 세션 ID 반환
            temp_session_id = f"emergency_{user_nickname}_{int(time.time())}"
            print(f"🚨 Returning emergency session ID: {temp_session_id}")
            return temp_session_id
    
    def create_session(self, user_nickname: str, chatbot_name: str) -> str:
        """새로운 대화 세션 생성"""
        try:
            session_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            user_nickname = unicodedata.normalize("NFC", user_nickname.strip())
            chatbot_name = unicodedata.normalize("NFC", chatbot_name.strip())

            session_data = {
                "session_id": session_id,
                "user_nickname": user_nickname,
                "chatbot_name": chatbot_name,
                "start_time": timestamp,
                "current_distance": 10,
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
            
            print(f"🔧 Creating session data: {session_id}")
            key = f"{user_nickname}__{chatbot_name}"
            self.sessions[session_id] = session_data
            
            self.user_sessions[key] = session_id

            # 저장 시도
            try:
                save_result = self._save_session(session_id)
                print(f"💾 Session save result: {save_result}")
            except Exception as e:
                print(f"⚠️ Failed to save session to file, but continuing: {e}")
            
            return session_id
            
        except Exception as e:
            print(f"❌ Error in create_session: {str(e)}")
            raise e

    def update_situation(self, session_id: str, situation: str, quiz_list: List[str]):
        """상황 및 퀴즈 리스트 업데이트"""
        try:
            print(f"🔧 Updating situation for session: {session_id}")
            if session_id in self.sessions:
                self.sessions[session_id]["situation"] = situation
                self.sessions[session_id]["quiz_list"] = quiz_list
                save_result = self._save_session(session_id)
                print(f"💾 Situation update save result: {save_result}")
            else:
                print(f"⚠️ Session {session_id} not found in memory")
        except Exception as e:
            print(f"❌ Error updating situation: {e}")
    
    def add_conversation(self, session_id: str, user_message: str, bot_message: str, 
                            score: int, react: str, improved_quiz: str, verification: bool):
        """대화 턴 추가"""
        try:
            print(f"💬 Adding conversation turn for session: {session_id}")
            if session_id in self.sessions:
                session_data = self.sessions[session_id]
                
                if score == 1:
                    session_data["current_distance"] -= 1
                
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
                
                save_result = self._save_session(session_id)
                print(f"💾 Conversation turn save result: {save_result}")
            else:
                print(f"⚠️ Session {session_id} not found in memory")
        except Exception as e:
            print(f"❌ Error adding conversation turn: {e}")
    
    def add_feedback(self, session_id: str, first_greeting:str, feedback: str, last_greeting: str):
        """최종 피드백 추가"""
        try:
            print(f"💬 Adding feedback for session: {session_id}")
            if session_id in self.sessions:
                self.sessions[session_id]["final_feedback"] = {
                    "feedback": feedback,
                    "first_greeting": first_greeting,
                    "last_greeting": last_greeting,
                    "timestamp": datetime.now().isoformat()
                }
                self.sessions[session_id]["end_time"] = datetime.now().isoformat()
                save_result = self._save_session(session_id)
                print(f"💾 Feedback save result: {save_result}")
            else:
                print(f"⚠️ Session {session_id} not found in memory")
        except Exception as e:
            print(f"❌ Error adding feedback: {e}")
    
    def get_session_data(self, session_id: str) -> Dict:
        """세션 데이터 조회"""
        return self.sessions.get(session_id, {})
    
    def _save_session(self, session_id: str) -> bool:
        """세션을 JSON 파일로 저장"""
        try:
            if session_id not in self.sessions:
                print(f"❌ Session {session_id} not found in memory for saving")
                return False
                
            file_path = self.log_dir / f"{session_id}.json"
            print(f"💾 Attempting to save session to: {file_path.absolute()}")
            
            # 디렉토리 존재 확인 및 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # JSON 파일 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.sessions[session_id], f, ensure_ascii=False, indent=2)
            
            # 파일이 실제로 생성되었는지 확인
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"✅ Session saved successfully. File size: {file_size} bytes")
                return True
            else:
                print(f"❌ File was not created: {file_path}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving session {session_id}: {str(e)}")
            import traceback
            print(f"❌ Save error traceback: {traceback.format_exc()}")
            return False
    
    def get_all_sessions(self) -> List[Dict]:
        """모든 세션 데이터 조회"""
        return list(self.sessions.values())
    
    def debug_info(self) -> Dict:
        """디버깅 정보 반환"""
        return {
            "log_dir": str(self.log_dir.absolute()),
            "log_dir_exists": self.log_dir.exists(),
            "sessions_count": len(self.sessions),
            "user_sessions_count": len(self.user_sessions),
            "session_ids": list(self.sessions.keys()),
            "json_files_count": len(list(self.log_dir.glob("*.json"))),
            "json_files": [str(f.name) for f in self.log_dir.glob("*.json")]
        }

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
    print(f"ConversationLogger debug info: {conversation_logger.debug_info()}")  # 디버깅
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
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting 미들웨어 추가
rate_limiter = RateLimitMiddleware(calls=300, period=60)
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

# 디버깅용 엔드포인트들
@app.get("/debug/logger")
async def debug_logger():
    """ConversationLogger 디버깅 정보"""
    return conversation_logger.debug_info()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
    """비동기로 검증 및 점수 생성"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_verification_and_score, conversation, chatbot_name, user_nickname)

async def async_generate_response(conversation, score, chatbot_name, user_nickname):
    """비동기로 응답 생성"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_response, conversation, score, chatbot_name, user_nickname)

async def async_improved_question(quiz_list, conversation, react, chatbot_name):
    """비동기로 개선된 질문 생성"""
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
@app.post("/situation", response_class=JSONResponse)
async def situation(request: Situation, background_tasks: BackgroundTasks):
    try:
        nickname = request.user_nickname
        chatbot_name = request.chatbot_name


        nickname = unicodedata.normalize("NFC", nickname.strip())
        chatbot_name = unicodedata.normalize("NFC", chatbot_name.strip())

        print(f"=== SITUATION ENDPOINT CALLED ===")
        print(f"User: {nickname}, Chatbot: {chatbot_name}")

        # 자동으로 세션 생성 (기존 세션이 있으면 재사용)
        # session_id = conversation_logger.get_or_create_session(nickname, chatbot_name)
        session_id = conversation_logger.create_session(nickname, chatbot_name)
        print(f"Session ID: {session_id}")
        
        # 비동기로 퀴즈 생성
        situation, quiz_list = await async_generate_situation_and_quiz()
        print(f"\nSituation generated: {situation}")
        print(f"\nQuiz list generated: {quiz_list}")

        # 세션에 상황과 퀴즈 리스트 저장
        conversation_logger.update_situation(session_id, situation, quiz_list)
        
        # 디버깅 정보 출력
        debug_info = conversation_logger.debug_info()
        print(f"Debug info after situation: {debug_info}")

        return {"quiz_list": quiz_list}
        
    except Exception as e:
        print(f"Error in situation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 2. Conversation (타임아웃 적용된 버전)
@app.post("/conversation", response_class=JSONResponse)
async def conversation(request: Conversation):
    try:
        user_nickname = request.user_nickname
        chatbot_name = request.chatbot_name
        conversation = request.conversation
        quiz_list = request.quiz_list
        current_distance = request.current_distance

        user_nickname = unicodedata.normalize("NFC", user_nickname.strip())
        chatbot_name = unicodedata.normalize("NFC", chatbot_name.strip())

        session_id = conversation_logger.get_or_create_session(user_nickname, chatbot_name)

        logger.info(f"Processing conversation for user: {user_nickname} with chatbot: {chatbot_name}, distance: {current_distance}")
        print(f"\n=== CONVERSATION ENDPOINT CALLED ===")  # 디버깅용
        print(f"\nUser: {user_nickname}, Chatbot: {chatbot_name}")  # 디버깅용


        # 비동기로 응답 생성
        try:
            verification, score = await async_generate_verification_and_score(
                conversation, chatbot_name, user_nickname
            )
            print(f"✅ Verification result: {verification}, Score: {score}")
        except Exception as e:
            print(f"❌ First attempt failed: {str(e)}")
            logger.error(f"Error generating verification and score: {str(e)}", exc_info=True)
            try:
                print("🔄 Retrying verification and score generation...")
                verification, score = await async_generate_verification_and_score(
                    conversation, chatbot_name, user_nickname
                )
                print(f"✅ Retry result: {verification}, Score: {score}")
            except Exception as e:
                print(f"❌ Retry also failed: {str(e)}")
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
            print(f"✅ Verification successful! Generating responses...")

            statement = await async_generate_response(conversation, score, chatbot_name, user_nickname)
            improved_quiz = await async_improved_question(quiz_list, conversation, statement, chatbot_name)

            # 성공한 경우 기록
            user_message = conversation[-1] if conversation else ""
            bot_message = f"{statement} {improved_quiz}".strip()

            conversation_logger.add_conversation(
                session_id=session_id,
                user_message=user_message,
                bot_message=bot_message,
                score=score,
                react=statement,
                improved_quiz=improved_quiz,
                verification=verification
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
        
        user_nickname = unicodedata.normalize("NFC", user_nickname.strip())
        chatbot_name = unicodedata.normalize("NFC", chatbot_name.strip())

        logger.info(f"Processing feedback for user: {user_nickname} with chatbot: {chatbot_name}, distance: {current_distance}")
        print(f"=== FEEDBACK ENDPOINT CALLED ===")  # 디버깅용
        print(f"User: {user_nickname}, Chatbot: {chatbot_name}")  # 디버깅용

        # 현재 사용자의 세션 ID 가져오기
        session_id = conversation_logger.get_or_create_session(user_nickname, chatbot_name)
        print(f"Session ID: {session_id}")  # 디버깅용

        # 비동기로 피드백 생성
        first_greeting, text, last_greeting = await async_generate_feedback(conversation, current_distance, chatbot_name, user_nickname)
        logger.info(f"{first_greeting}\n\n{text}\n\n{last_greeting}")

        conversation_logger.add_feedback(
            session_id=session_id,
            first_greeting=first_greeting,
            feedback=text,
            last_greeting=last_greeting
        )
        return {
                "feedback": text,
                "last_greeting": last_greeting
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
    print("Registered routes:")
    for route in app.routes:
        print(route.path)
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