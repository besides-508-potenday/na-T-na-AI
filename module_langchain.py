import os
import re
import json
from langchain_naver import ChatClovaX

from dotenv import load_dotenv
load_dotenv()


chat_init = ChatClovaX(
    model="HCX-007", # 모델명 입력 (기본값: HCX-005) 
    temperature = 0.7,
    max_completion_tokens = 1024,
    api_key=os.environ["CLOVASTUDIO_API_KEY"]
)

chat = ChatClovaX(
    model="HCX-007", # 모델명 입력 (기본값: HCX-005) 
    temperature = 0.7,
    max_completion_tokens = 1024,
    api_key=os.environ["CLOVASTUDIO_API_KEY"],
)

chat_feedback = ChatClovaX(
    model="HCX-007", # 모델명 입력 (기본값: HCX-005) 
    temperature = 0.7,
    max_completion_tokens = 2048,
    api_key=os.environ["CLOVASTUDIO_API_KEY"],
)
user_id = "nickname"
# 상황 생성
def generate_situation(user_id):
    system_message_situation = f"""You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.
    Your name is "투닥이".
    You are an F-type (emotional) MBTI personality type, and you have the following tone of voice and personality.
    - Personality: Shy, emotionally intense, seeking validation, and using relationship-centric language
    - Tone: Frequently using emotional words with emoji and employing a lingering tone to prompt a response, 반말

    Your goal is:
    - Generate a realistic, emotionally heavy situation that feels natural for a conversation starter.  


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
    messages = [
        (
            "system",
            system_message_situation,
        ),
    ]
    ai_msg = chat_init.invoke(messages)
    situation = ai_msg.content
    return ai_msg, situation, user_id

# situation = ai_msg.content
def generate_questions(situation):
    system_message_questions = f"""Your task is to generate 10 emotionally vulnerable self-expressive sentences (not questions) based on specific situation.
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
    messages = [
        (
            "system",
            system_message_questions,
        ),
    ]
    ai_msg = chat_init.invoke(messages)

    raw_questions = ai_msg.content
    lines = raw_questions.strip().split("\n")
    questions = [re.sub(r'^\d+\.\s*', '', line.strip()) for line in lines if line.strip()][:10]
    return ai_msg, questions




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