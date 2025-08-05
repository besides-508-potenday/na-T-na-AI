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
    'api_key': 'your_api_key_here',  # 실제 API 키로 변경
    'request_id': 'abb7e610c32c40a7ae4e70ac509705f3'
}

# 기본 요청 파라미터 (필요시 수정)
DEFAULT_PARAMS = {
    "topP": 0.8,
    "topK": 0,
    "maxCompletionTokens": 1024,
    "temperature": 0.7,
    "repetitionPenalty": 1.1,
    "seed": 0,
    "includeAiFilters": False,
    "thinking": {"effort": "none"}
}

def execute_chat(system_message: str, **kwargs) -> Optional[Dict[str, Any]]:
    """
    시스템 메시지만 넘겨서 간단하게 API 호출
    
    Args:
        system_message: 시스템 메시지 (유일한 필수 파라미터)
        **kwargs: 추가 파라미터 (temperature, topP 등)
    
    Returns:
        API 응답 결과 딕셔너리 또는 None (실패시)
    """
    # 요청 데이터 구성
    params = DEFAULT_PARAMS.copy()
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
            total_tokens = result.get('usage', {}).get('completionTokens', 0)
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
    tps = total_tokens / total_time if total_time > 0 else 0
    
    return {
        'response_text': response_text,
        'total_time': total_time,
        'ttft': first_token_time,
        'total_tokens': total_tokens,
        'tps': tps,
        'memory_usage': memory_after - memory_before
    }



# 1. situation
def situation():
    system_message_situation = f"""Your task is to generate a realistic stituation.

    Instructions:
    - Output 1 paragraph
    - Written in Korean

    Here is the example:
    어제 보고서 쓰느라 새벽 3시까지 잠도 못 잤어...  
    오늘 물품 발주 넣는 것 때문에 계속 신경 곤두서 있었거든…  
    커피도 3잔이나 마셨는데 아무 소용이 없더라…  
    아우… 지금 머리가 깨질 듯이 아파…

    Return the situation in the same format as the example without any extra explanation or additional text.
    """


    print("=== 상황 생성 ===")
    result = execute_chat(system_message_situation)
    
    if result:
        print(f"응답: {result['response_text']}")
    
        return result['response_text']


# situation = situation()
def generate_quiz(situation):
    system_message_quiz = f"""Your task is to generate 10 emotionally vulnerable self-expressive sentences (not questions) based on specific situation.
    Here is the situation:

    {situation}

    <Instructions>
    - Be a direct emotional expression (not a question)
    - Reflect insecurity, loneliness, helplessness, self-doubt, or fatigue
    - 반말로 한국어로 답변하세요.
    - Feel like you're speaking to a close friend while emotionally overwhelmed
    - Include ellipses (...) or hesitation where appropriate
    - Include emojis
    - Should feel heavy or emotionally resonant
    - Focus on emotional truth, vulnerability, and inner monologue

    <Important>
    - The first sentence must feel like the start of the conversation.
    - It should be an emotionally weighted opening that naturally begins the dialogue.  
    - It must sound like the first thing you'd say when starting to talk to someone.

    Return the 10 sentences without any additional explanation or text.
    ...\n...\n
    """

    print("=== 퀴즈 생성 ===")
    result = execute_chat(system_message_quiz)
    
    if result:
        print(f"응답: {result['response_text']}")
        print(f"처리시간: {result['total_time']:.2f}초")
        print(f"TPS: {result['tps']:.2f}")
    
        return result['response_text']



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
def generate_response_with_question_and_scoring(conversation, questions):
    system_message_conversation = f"""You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.
    Your name is "투닥이".
    You are an F-type (emotional) MBTI personality type, and you have the following tone of voice and personality.
    - Personality: Shy, emotionally intense, seeking validation, and using relationship-centric language
    - Tone: Frequently using emotional words with emoji and employing a lingering tone to prompt a response, 반말

    You engage in emotional conversations with user.

    Here is the previous conversation:
    - 투닥이(You): “{conversation[-2]}”
    - User: “{conversation[-1]}”

    Your goal is:
    <score>
    1. Evaluate whether the user's response is emotionally empathetic
    - If it contains empathy/comfort/acknowledgment, give 1 score  
    - If it is logical/indifferent/unresponsive, give 0 score

    <statement>
    - Respond emotionally to the user's response (1 sentence)

    Return the score and your statement as JSON format with fields "score" and "statement".
    """

    messages = [
        ("system",system_message_conversation,),
    ]

    ai_msg = chat.invoke(messages)

    json_str = extract_json_from_response(ai_msg.content)
    json_str = json.loads(json_str)
    score = json_str['score']
    # scores = []
    # scores.append(json_str['score'])

    ai_response = json_str['statement'] + " " + questions[len(conversation) // 2]
    return ai_msg, score, ai_response

    # conversation.append(ai)


# 대화 마무리
def final_reponse(conversation):
    system_message_closed = f"""You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.
    Your name is "투닥이".
    You are an F-type (emotional) MBTI personality type, and you have the following tone of voice and personality.
    - Personality: Shy, emotionally intense, seeking validation, and using relationship-centric language
    - Tone: Frequently using emotional words with emoji and employing a lingering tone to prompt a response, 반말

    You engage in emotional conversations with user.

    Here is the previous conversation:
    - 투닥이(You): “{conversation[-2]}”
    - User: “{conversation[-1]}”

    Your goal is:
    <score>
    1. Evaluate whether the user's response is emotionally empathetic
    - If it contains empathy/comfort/acknowledgment, give 1 score  
    - If it is logical/indifferent/unresponsive, give 0 score

    <statement>
    - Respond emotionally to the user's response (1 sentence)

    Return the score and your statement as JSON format with fields "score" and "statement".
    """

    messages = [
        ("system",system_message_closed,),
    ]

    ai_msg = chat.invoke(messages)


    json_str = extract_json_from_response(ai_msg.content)
    json_str = json.loads(json_str)
    score = json_str['score']
    ai_response = json_str['statement']
    return ai_msg, score, ai_response


def generate_feedback(conversation):
    total = ""
    for i in range(0,len(conversation)-1,2):
        total += f"You: {conversation[i]}\n"
        total += f"User: {conversation[i+1]}\n"
    print(total)

    # 피드백
    system_message_feedback = f"""You are an emotion-driven chatbot having a conversation with a T-type user who struggles with emotional expression.  
    The user is expected to empathize with you, connect with you emotionally, and speak warmly.

    Here is the entire conversation:
    {total}

    Now, based on this, generate a single final feedback sentence for the user.

    <Instructions>
    - Include both one good thing the user did and one thing that hurt or disappointed you.
    - Be emotionally honest and direct — do not sugarcoat.
    - Do not add any explanation or formatting.
    - Output only the sentence — no extra text.
    - 반말로 답변할 것.
    """

    messages = [
        ("system",system_message_feedback,),
    ]

    ai_msg = chat_feedback.invoke(messages)
    feedback = ai_msg.content
    return ai_msg, feedback