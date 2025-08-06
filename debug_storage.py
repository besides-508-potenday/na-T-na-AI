# 데이터 저장 문제 진단 스크립트

import asyncio
import json
import aiofiles
from pathlib import Path
import os

# 테스트용 간단한 저장 함수
async def test_file_saving():
    """파일 저장 테스트"""
    print("=== 파일 저장 테스트 시작 ===")
    
    # 1. 현재 작업 디렉토리 확인
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    
    # 2. chat_data 폴더 확인
    chat_data_dir = Path("chat_data")
    print(f"chat_data 디렉토리 경로: {chat_data_dir.absolute()}")
    print(f"chat_data 디렉토리 존재 여부: {chat_data_dir.exists()}")
    
    # 3. 폴더 생성 (이미 있어도 에러 안남)
    chat_data_dir.mkdir(exist_ok=True)
    print(f"chat_data 디렉토리 생성 후 존재 여부: {chat_data_dir.exists()}")
    
    # 4. 테스트 파일 저장
    test_file = chat_data_dir / "test_user_test_bot.json"
    test_data = {
        "user_nickname": "test_user",
        "chatbot_name": "test_bot",
        "test_message": "Hello World!",
        "timestamp": "2024-01-01T00:00:00"
    }
    
    try:
        # aiofiles로 저장 시도
        print(f"aiofiles로 저장 시도: {test_file.absolute()}")
        async with aiofiles.open(test_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(test_data, ensure_ascii=False, indent=2))
        print("✅ aiofiles 저장 성공")
        
        # 파일이 실제로 생성되었는지 확인
        if test_file.exists():
            file_size = test_file.stat().st_size
            print(f"✅ 파일 생성 확인됨. 크기: {file_size} bytes")
            
            # 파일 읽기 테스트
            async with aiofiles.open(test_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                loaded_data = json.loads(content)
                print(f"✅ 파일 읽기 성공: {loaded_data}")
        else:
            print("❌ 파일이 생성되지 않음!")
            
    except Exception as e:
        print(f"❌ aiofiles 저장 실패: {e}")
        
        # 일반 파일 쓰기로 시도
        try:
            print("일반 파일 쓰기로 재시도...")
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            print("✅ 일반 파일 쓰기 성공")
            
            if test_file.exists():
                print(f"✅ 파일 생성 확인됨")
            else:
                print("❌ 여전히 파일이 생성되지 않음!")
                
        except Exception as e2:
            print(f"❌ 일반 파일 쓰기도 실패: {e2}")
    
    # 5. 디렉토리 권한 확인
    try:
        print(f"\n=== 디렉토리 권한 확인 ===")
        print(f"디렉토리 권한: {oct(chat_data_dir.stat().st_mode)[-3:]}")
        print(f"쓰기 권한 있음: {os.access(chat_data_dir, os.W_OK)}")
        print(f"읽기 권한 있음: {os.access(chat_data_dir, os.R_OK)}")
    except Exception as e:
        print(f"권한 확인 실패: {e}")
    
    # 6. 현재 디렉토리의 모든 파일 나열
    print(f"\n=== chat_data 폴더 내용 ===")
    try:
        files = list(chat_data_dir.glob("*"))
        if files:
            for file in files:
                print(f"- {file.name} (크기: {file.stat().st_size} bytes)")
        else:
            print("폴더가 비어있음")
    except Exception as e:
        print(f"폴더 내용 확인 실패: {e}")

# 메인 함수에서 실행하기 위한 동기 함수
def run_test():
    asyncio.run(test_file_saving())

if __name__ == "__main__":
    run_test()


# =====================================================
# 실제 코드에서 사용할 수 있는 개선된 저장 클래스
# =====================================================

class ImprovedChatDataStorage:
    def __init__(self, storage_dir: str = "chat_data"):
        self.storage_dir = Path(storage_dir)
        self._ensure_directory()
        
    def _ensure_directory(self):
        """디렉토리 생성 및 권한 확인"""
        try:
            self.storage_dir.mkdir(exist_ok=True)
            print(f"✅ Storage directory ensured: {self.storage_dir.absolute()}")
            
            # 쓰기 권한 확인
            if not os.access(self.storage_dir, os.W_OK):
                raise PermissionError(f"No write permission for {self.storage_dir}")
                
        except Exception as e:
            print(f"❌ Directory setup failed: {e}")
            raise
        
    def _get_user_file_path(self, user_nickname: str, chatbot_name: str) -> Path:
        """안전한 파일명 생성"""
        # 특수문자 제거 및 안전한 파일명 만들기
        safe_user = "".join(c for c in user_nickname if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_bot = "".join(c for c in chatbot_name if c.isalnum() or c in (' ', '-', '_')).strip()
        
        # 공백을 언더스코어로 변경
        safe_filename = f"{safe_user}_{safe_bot}".replace(" ", "_")
        
        # 파일명이 너무 길면 줄이기
        if len(safe_filename) > 100:
            safe_filename = safe_filename[:100]
            
        file_path = self.storage_dir / f"{safe_filename}.json"
        print(f"📁 Generated file path: {file_path.absolute()}")
        return file_path
    
    async def save_user_data_improved(self, user_nickname: str, chatbot_name: str, data: dict):
        """개선된 데이터 저장 함수"""
        file_path = self._get_user_file_path(user_nickname, chatbot_name)
        
        try:
            print(f"💾 Attempting to save data to: {file_path}")
            
            # 임시 파일에 먼저 저장
            temp_file = file_path.with_suffix('.tmp')
            
            # aiofiles로 저장 시도
            async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                await f.write(json_str)
            
            # 임시 파일을 실제 파일로 이동 (원자적 연산)
            temp_file.replace(file_path)
            
            # 저장 확인
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"✅ Data saved successfully. Size: {file_size} bytes")
                return True
            else:
                print(f"❌ File was not created: {file_path}")
                return False
                
        except Exception as e:
            print(f"❌ Save failed with aiofiles: {e}")
            
            # 폴백: 일반 파일 쓰기 시도
            try:
                print("🔄 Trying fallback with regular file operations...")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                if file_path.exists():
                    print(f"✅ Fallback save successful")
                    return True
                else:
                    print(f"❌ Fallback save failed - file not created")
                    return False
                    
            except Exception as e2:
                print(f"❌ Fallback save also failed: {e2}")
                return False

    async def load_user_data_improved(self, user_nickname: str, chatbot_name: str) -> dict:
        """개선된 데이터 로드 함수"""
        file_path = self._get_user_file_path(user_nickname, chatbot_name)
        
        # 기본 데이터 구조
        default_data = {
            "user_nickname": user_nickname,
            "chatbot_name": chatbot_name,
            "sessions": [],
            "total_score": 0,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        if not file_path.exists():
            print(f"📄 File doesn't exist, returning default data: {file_path}")
            return default_data
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                print(f"✅ Data loaded successfully from: {file_path}")
                return data
                
        except Exception as e:
            print(f"❌ Load failed: {e}")
            return default_data

# 테스트 함수
async def test_improved_storage():
    """개선된 저장소 테스트"""
    print("\n=== 개선된 저장소 테스트 ===")
    
    storage = ImprovedChatDataStorage()
    
    # 테스트 데이터
    test_data = {
        "user_nickname": "testuser",
        "chatbot_name": "testbot",
        "sessions": [
            {
                "session_id": 1,
                "quiz_list": ["질문1", "질문2"],
                "conversation_history": [
                    {
                        "timestamp": "2024-01-01T12:00:00",
                        "conversation": ["안녕", "안녕하세요"],
                        "score": 10
                    }
                ],
                "total_session_score": 10,
                "completed": False
            }
        ],
        "total_score": 10,
        "created_at": "2024-01-01T10:00:00",
        "updated_at": "2024-01-01T12:00:00"
    }
    
    # 저장 테스트
    success = await storage.save_user_data_improved("testuser", "testbot", test_data)
    print(f"저장 성공 여부: {success}")
    
    # 로드 테스트
    loaded_data = await storage.load_user_data_improved("testuser", "testbot")
    print(f"로드된 데이터: {loaded_data.get('user_nickname', 'N/A')}")
    
    return success

def run_improved_test():
    asyncio.run(test_improved_storage())

print("""
이 스크립트를 실행해보세요:

1. 터미널에서: python debug_storage_issue.py
   또는
2. 파이썬 인터프리터에서:
   from debug_storage_issue import run_test, run_improved_test
   run_test()  # 기본 테스트
   run_improved_test()  # 개선된 테스트

이 스크립트가 다음을 확인합니다:
- 파일 시스템 권한
- 디렉토리 생성 가능 여부  
- 파일 쓰기/읽기 가능 여부
- aiofiles vs 일반 파일 쓰기 비교
""")