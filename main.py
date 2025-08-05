from fastapi import FastAPI, HTTPException, Request, Depends
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
import traceback
import uuid

print(os.getcwd())
# os.chdir('/Users/hongbikim/Dev/natna/')

# from natna.module import generate_situation

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
    json_handler = logging.getLogger().handlers[2]  # access_log 핸들러
    json_handler.setFormatter(JSONFormatter())

# 로깅 설정 실행
setup_logging()
logger = logging.getLogger(__name__)
access_logger = logging.getLogger("access")

# =============================================================================
# Pydantic 모델들
# =============================================================================

class Situation(BaseModel):
    user_nickname: str

class Conversation(BaseModel):
    conversation: List[str]
    quiz_list: List[str]
    current_distance: int

class Feedback(BaseModel):
    conversation: List[str]
    current_distance: int
# =============================================================================
# FastAPI 앱 설정
# =============================================================================

app = FastAPI(
    title="API Swagger (AI-BE)",
    description="This is a FastAPI application for AI-BE.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
origins = [
    "https://petstore.swagger.io",  # Swagger 공식 UI
    "http://localhost:8000",        # 로컬 접근도 허용
]

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins= origins, # ["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# API 엔드포인트들
# =============================================================================

# 1. situation
@app.post("/situation", response_class = JSONResponse)
async def situation(request: Situation):
    nickname = request.user_nickname
    logger.info(f"User nickname: {nickname}")
    return {
        "quiz_list": ["q1","q2","q3","q4","q5","q6","q7","q8","q9","q10"]
        }

# 2. Conversaion
@app.post("/conversation", response_class = JSONResponse)
async def conversation(request: Conversation):
    conversation = request.conversation
    quiz_list = request.quiz_list
    current_distance = request.current_distance
    logger.info(f"Conversation: {conversation}")
    logger.info(f"Current Distance: {current_distance}")

    return {
        "react": "👍",
        "score": 1,
    }

# 3. Feedback
@app.post("/feedback", response_class = JSONResponse)
async def feedback(request: Feedback):
    conversation = request.conversation
    current_distance = request.current_distance
    logger.info(f"Feedback Conversation: {conversation}")
    logger.info(f"Current Distance: {current_distance}")

    return {
        "feedback": "Great job! Keep it up!",
    }

# =============================================================================
# 시작점
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting FastAPI application...")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=False,  # 우리가 커스텀 액세스 로그를 사용하므로 비활성화
        log_config=None   # 우리가 커스텀 로깅 설정을 사용하므로 비활성화
    )
# sudo docker run --gpus all -d --rm -p 8080:8080 --name test_container test -v matching_vol:/vol