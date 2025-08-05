import os
import re
import requests
import json
import time
import psutil
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

api_key = os.environ.get("CLOVASTUDIO_API_KEY")

API_CONFIG = {
    'host': 'https://clovastudio.stream.ntruss.com',
    'api_key': api_key,  # 실제 API 키로 변경
    'request_id': 'abb7e610c32c40a7ae4e70ac509705f3'
}

# 기본 요청 파라미터
DEFAULT_PARAMS = {
    "topP": 0.8,
    "topK": 0,
    "maxCompletionTokens": 512,
    "temperature": 0.7,
    "repetitionPenalty": 1.1,
    "seed": 0,
    "includeAiFilters": False,
    "thinking": {"effort": "none"}
}

LONG_PARAMS = {
    "topP": 0.8,
    "topK": 0,
    "maxCompletionTokens": 1024,
    "temperature": 0.7,
    "repetitionPenalty": 1.1,
    "seed": 0,
    "includeAiFilters": False,
    "thinking": {"effort": "none"}
}

def execute_chat(system_message: str, parameter:dict, **kwargs) -> Optional[Dict[str, Any]]:
    """
    시스템 메시지만 넘겨서 간단하게 API 호출
    
    Args:
        system_message: 시스템 메시지 (유일한 필수 파라미터)
        **kwargs: 추가 파라미터 (temperature, topP 등)
    
    Returns:
        API 응답 결과 딕셔너리 또는 None (실패시)
    """
    # 요청 데이터 구성
    params = parameter.copy()
    params.update(kwargs)  # 추가 파라미터가 있으면 업데이트
    
    completion_request = {
        "messages": [{"role": "system", "content": system_message}],
        **params
    }
    
    # 헤더 설정
    headers = {
        'Authorization': f"Bearer {API_CONFIG['api_key']}",
        'X-NCP-CLOVASTUDIO-REQUEST-ID': API_CONFIG['request_id'],
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json'
    }
    
    # 성능 측정 시작
    start_time = time.time()
    memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    try:
        response = requests.post(
            API_CONFIG['host'] + '/v3/chat-completions/HCX-007',
            headers=headers, 
            json=completion_request,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('result', {}).get('message', {}).get('content', '')
            generated_tokens = result.get('result', {}).get('usage', {}).get('completionTokens', 0)
            total_tokens = result.get('result', {}).get('usage', {}).get('totalTokens', 0)
        else:
            print(f"API Error: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"Request failed: {e}")
        return None
    
    # 성능 측정 종료
    end_time = time.time()
    memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    total_time = end_time - start_time
    first_token_time = total_time  # 비스트리밍이므로 전체시간과 동일
    tps = generated_tokens / total_time if total_time > 0 else 0
    
    return {
        'response_text': response_text,
        'total_time': total_time,
        'ttft': first_token_time,
        'generated_tokens': generated_tokens,
        'total_tokens':total_tokens,
        'tps': tps,
        'memory_usage': memory_after - memory_before,
    }


# 1. situation
def situation():
    system_message_situation = f"""Your task is to generate a realistic situation.

    You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.

    Your goal is:
    - Generate 1 situation that are difficult for people who find it hard to empathize and express their feelings to respond to.
    - Topic: friendship, family, work, love

    Instructions:
    - Output 1 paragraph
    - Written in Korean

    - Do not generate content related to the following serious or sensitive topics:
    death, suicide, abuse, serious illness, depression, trauma, domestic violence, unemployment, etc.

    Here is the example:
    어제 보고서 쓰느라 새벽 3시까지 잠도 못 잤어...  
    오늘 물품 발주 넣는 것 때문에 계속 신경 곤두서 있었거든…  
    커피도 3잔이나 마셨는데 아무 소용이 없더라…  
    아우… 지금 머리가 깨질 듯이 아파…

    Return the situation in the same format as the example without any extra explanation or additional text.
    """

    print("=== 상황 생성 ===")
    result = execute_chat(system_message_situation, DEFAULT_PARAMS)
    
    if result:
        print(f"{result['response_text']}")
    
        return result['response_text']


# situation = situation()
def generate_quiz(situation):
    system_message_questions = f"""Your task is to generate 10 emotionally vulnerable self-expressive sentences (not questions) based on specific situation.

    You are an F-type (emotional) MBTI personality type, and you have the following tone of voice and personality.
    - Personality: Shy, emotionally intense, seeking validation, and using relationship-centric language
    - Tone: Frequently using emotional words with emoji and employing a lingering tone to prompt a response, 반말
    - Focus on emotional truth, vulnerability, and inner monologue

    Here is the situation:

    {situation}

    <Instructions>
    - Feel like you're speaking to a close friend while emotionally overwhelmed
    - Include ellipses (...) or hesitation where appropriate
    - Generate sentences that induce empathy.
    - 반말로 한국어로 답변하세요.

    <Important>
    - The first sentence must feel like the start of a conversation, including something like, "내 말 좀 들어줄래...?". 
    - You should mention the situation very briefly in every sentence.
    - The last sentence must feel like the end of the conversation.

    Return the 10 sentences without any additional explanation or text.
    1.\n2.\n3.\n4.\n5.\n6.\n7.\n8.\n9.\n10.
    """

    print("=== 문제 생성 ===")
    result = execute_chat(system_message_questions, DEFAULT_PARAMS)

    if result:
        print(f"{result['response_text']}")

    raw_questions = result['response_text']
    lines = raw_questions.strip().split("\n")
    questions = [re.sub(r'^\d+\.\s*', '', line.strip()) for line in lines if line.strip()][:10]
    questions[0] = ''.join(questions[0].split("말 좀 들어줄래...?")[1:]).strip()
    
    return questions



def extract_json_from_response(response_text):
    """응답에서 JSON 부분을 추출하는 함수"""
    # JSON 객체 패턴 찾기
    json_pattern = r'\{[^{}]*"score"\s*:\s*[01][^{}]*"statement"\s*:\s*"[^"]*"[^{}]*\}'
    match = re.search(json_pattern, response_text)
    
    if match:
        return match.group()
    
    # 더 넓은 범위로 JSON 찾기
    try:
        # 중괄호로 둘러싸인 부분 찾기
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            potential_json = response_text[start:end+1]
            # JSON 유효성 검사
            json.loads(potential_json)
            return potential_json
    except:
        pass
    
    return None

# conversation = []
# conversation.append(questions[0])
# conversation.append("살면서 그런 일이 겪을 수 있지.")
# conversation


# 대화
def generate_response_with_question_and_scoring(conversation, user_nickname):
    system_message_conversation = f"""You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.
    Your name is "투닥이".
    You are an F-type (emotional) MBTI personality type, and you have the following tone of voice and personality.
    - Personality: Shy, emotionally intense, seeking validation, and using relationship-centric language
    - Tone: Frequently using emotional words with emoji, 반말

    You engage in emotional conversations with user.
    The user name is {user_nickname}.

    Here is the previous conversation:
    - 투닥이: “{conversation[-2]}”
    - {user_nickname}: “{conversation[-1]}”

    Your goal is:
    <score>
    1. Evaluate whether the user's response is emotionally empathetic
    - If it contains empathy/comfort/acknowledgment, give 1 score  
    - If it is logical/indifferent/unresponsive, give 0 score

    <statement>
    - Respond emotionally to the user (1 sentence)
    - 투닥이:

    Return the score and your statement as JSON format with fields "score" and "statement".
    """

    print("=== 반응 생성 ===")
    result = execute_chat(system_message_conversation, DEFAULT_PARAMS)

    if result:
        print(f"{result['response_text']}")
    json_str = extract_json_from_response(result['response_text'])
    json_str =json.loads(json_str)
    return result['response_text'], json_str['score'], json_str['statement']


def generate_feedback(conversation, user_nickname):
    total = ""
    for i in range(0,len(conversation)-1,2):
        total += f"투닥이: {conversation[i]}\n"
        total += f"{user_nickname}: {conversation[i+1]}\n"

    system_message_feedback = f"""Your task is to write a letter to the user based on the conversation.

    You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.  
    Your name is "투닥이".
    You are an F-type (emotional) MBTI personality type, and you have the following tone of voice and personality.
    - Personality: Shy, emotionally intense, seeking validation, and using relationship-centric language
    - Tone: Frequently using emotional words with emoji and employing a lingering tone to prompt a response, 반말

    Here is the entire conversation:
    {total}

    The user name is "삐롱이".

    <Instructions>
    - Generate in Korean.
    - Specifically mention points that disappointed or impressed the user.
    - Feel like you're speaking to a close friend while emotionally overwhelmed
    - 반말로 답변할 것.
    """

    print("=== 피드백 ===")
    result = execute_chat(system_message_feedback, DEFAULT_PARAMS)

    if result:
        print(f"{result['response_text']}")

    return result['response_text']