import streamlit as st
import json
import os
import re
from datetime import datetime
import uuid
from pathlib import Path
from langchain_naver import ChatClovaX

from dotenv import load_dotenv
load_dotenv()

# Page config
st.set_page_config(
    page_title="투닥이 🌙 | 감정 대화 AI",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main theme */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Chat messages */
    .user-message {
        background: rgba(255, 255, 255, 0.9);
        padding: 15px;
        border-radius: 18px 18px 5px 18px;
        margin: 10px 0;
        margin-left: 20%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .ai-message {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        padding: 15px;
        border-radius: 18px 18px 18px 5px;
        margin: 10px 0;
        margin-right: 20%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        color: #333;
    }
    
    /* Emotion indicators */
    .emotion-score {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 10px;
    }
    
    .empathy-high {
        background: #4CAF50;
        color: white;
    }
    
    .empathy-low {
        background: #f44336;
        color: white;
    }
    
    /* New chat button */
    .new-chat-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 20px;
        border-radius: 25px;
        font-weight: bold;
        margin-bottom: 20px;
        width: 100%;
        cursor: pointer;
    }
    
    /* Chat title - 색깔 수정 */
    .chat-title {
        color: #333 !important;
        font-size: 18px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
        padding: 10px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        backdrop-filter: blur(10px);
    }
    
    /* Final feedback */
    .final-feedback {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 5px solid #ff6b6b;
    }
    
    /* Score summary */
    .score-summary {
        background: rgba(255, 255, 255, 0.9);
        padding: 15px;
        border-radius: 15px;
        margin: 10px 0;
        text-align: center;
    }
    
    /* Loading spinner */
    .loading {
        text-align: center;
        padding: 20px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chats' not in st.session_state:
    st.session_state.chats = {}
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'chat_counter' not in st.session_state:
    st.session_state.chat_counter = 0

# Cache directory
CACHE_DIR = Path('.cache')
CACHE_DIR.mkdir(exist_ok=True)
CHATS_FILE = CACHE_DIR / 'chats.json'

# Load chats from cache
def load_chats():
    if CHATS_FILE.exists():
        try:
            with open(CHATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.chats = data.get('chats', {})
                st.session_state.chat_counter = data.get('counter', 0)
        except:
            st.session_state.chats = {}
            st.session_state.chat_counter = 0

# Save chats to cache
def save_chats():
    with open(CHATS_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'chats': st.session_state.chats,
            'counter': st.session_state.chat_counter
        }, f, ensure_ascii=False, indent=2)

# Load chats on startup
load_chats()

# Initialize ChatClovaX
@st.cache_resource
def init_chat_models():
    
    api_key = os.environ.get("CLOVASTUDIO_API_KEY")
    if not api_key:
        st.error("CLOVASTUDIO_API_KEY 환경변수를 설정해주세요.")
        return None, None, None
    
    try:
        # For situation and questions generation
        chat_init = ChatClovaX(
            model="HCX-007",
            temperature=0.7,
            max_completion_tokens=1024,
            api_key=api_key
        )
        
        # For conversation evaluation
        chat = ChatClovaX(
            model="HCX-007",
            temperature=0.7,
            max_completion_tokens=1024,
            api_key=api_key
        )
        
        # For final feedback
        chat_feedback = ChatClovaX(
            model="HCX-007",
            temperature=0.7,
            max_completion_tokens=2048,
            api_key=api_key
        )
        
        return chat_init, chat, chat_feedback
    except Exception as e:
        st.error(f"ChatClovaX 초기화 실패: {e}")
        return None, None, None

# Extract JSON from response (from your original code)
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

# Generate situation (based on your original code)
def generate_situation(chat_init):
    """상황 생성 함수 - 원본 코드 기반"""
    system_message_situation = """You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.
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
            
    messages = [("system", system_message_situation)]
    
    try:
        ai_msg = chat_init.invoke(messages)
        return ai_msg.content.strip()
    except Exception as e:
        st.error(f"상황 생성 실패: {e}")
        return None

# Generate questions (based on your original code)
def generate_questions(chat_init, situation):
    """질문 생성 함수 - 원본 코드 기반"""
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
        """
    
    messages = [("system", system_message_questions)]
    
    try:
        ai_msg = chat_init.invoke(messages)
        raw_questions = ai_msg.content
        
        # Extract questions from response (from your original code)
        lines = raw_questions.strip().split("\n")
        questions = [re.sub(r'^\d+\.\s*', '', line.strip()) for line in lines if line.strip()][:10]
        
        # Filter out non-question lines
        filtered_questions = []
        for q in questions:
            if len(q) > 10 and ('...' in q or '😢' in q or '💔' in q or '🥺' in q or '😭' in q):
                filtered_questions.append(q)
        
        return filtered_questions[:10] if len(filtered_questions) >= 5 else questions[:10]
        
    except Exception as e:
        st.error(f"질문 생성 실패: {e}")
        return []

# Evaluate response (based on your original code)
def evaluate_response(chat, conversation):
    """응답 평가 함수 - 원본 코드 기반"""
    if len(conversation) < 2:
        return 0, "뭔가 이상해..."
    
    system_message_conversation = f"""You are an emotion-based chatbot that converses with T-type users who are not good at expressing their emotions.
Your name is "투닥이".
You are an F-type (emotional) MBTI personality type, and you have the following tone of voice and personality.
- Personality: Shy, emotionally intense, seeking validation, and using relationship-centric language
- Tone: Frequently using emotional words with emoji and employing a lingering tone to prompt a response, 반말

You engage in emotional conversations with user.

Here is the previous conversation:
- 투닥이(You): "{conversation[-2]}"
- User: "{conversation[-1]}"

Your goal is:
<score>
1. Evaluate whether the user's response is emotionally empathetic
- If it contains empathy/comfort/acknowledgment, give 1 score  
- If it is logical/indifferent/unresponsive, give 0 score

<statement>
- Respond emotionally to the user's response (1 sentence)

Return the score and your statement as JSON format with fields "score" and "statement".
"""
    
    messages = [("system", system_message_conversation)]
    
    try:
        response = chat.invoke(messages)
        json_str = extract_json_from_response(response.content)
        
        if json_str:
            result = json.loads(json_str)
            return result.get('score', 0), result.get('statement', '뭔가 이상해...')
        else:
            return 0, "잘 모르겠어..."
            
    except Exception as e:
        st.error(f"응답 평가 실패: {e}")
        return 0, "오류가 생겼어..."

# Generate final feedback (based on your original code)
def generate_final_feedback(chat_feedback, conversation):
    """최종 피드백 생성 함수 - 원본 코드 기반"""
    # Format conversation for feedback
    total = ""
    for i in range(0, len(conversation)-1, 2):
        if i+1 < len(conversation):
            total += f"You: {conversation[i]}\n"
            total += f"User: {conversation[i+1]}\n"
    
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
    
    messages = [("system", system_message_feedback)]
    
    try:
        response = chat_feedback.invoke(messages)
        return response.content.strip()
    except Exception as e:
        st.error(f"최종 피드백 생성 실패: {e}")
        return "대화해줘서 고마웠어..."

# Initialize chat models
chat_init, chat, chat_feedback = init_chat_models()

# Sidebar
with st.sidebar:
    st.markdown('<div class="chat-title">🌙 투닥이와의 대화</div>', unsafe_allow_html=True)
    
    # API Key input
    if not os.environ.get("CLOVASTUDIO_API_KEY"):
        st.warning("⚠️ API 키 설정 필요")
        api_key_input = st.text_input("CLOVASTUDIO_API_KEY", type="password", help="Clova Studio API 키를 입력하세요")
        if api_key_input:
            os.environ["CLOVASTUDIO_API_KEY"] = api_key_input
            st.success("✅ API 키가 설정되었습니다")
            st.rerun()
    
    # New chat button
    if st.button("✨ 새로운 대화 시작", key="new_chat", use_container_width=True, disabled=not chat_init):
        with st.spinner("투닥이가 고민을 준비하고 있어요... 🤔"):
            chat_id = str(uuid.uuid4())
            st.session_state.chat_counter += 1
            
            # Generate situation
            situation = generate_situation(chat_init)
            if situation:
                # Generate questions
                questions = generate_questions(chat_init, situation)
                if questions:
                    # 수정: 첫 번째 질문으로 시작 (situation 사용하지 않음)
                    st.session_state.chats[chat_id] = {
                        'id': chat_id,
                        'title': f"대화 {st.session_state.chat_counter}",
                        'created_at': datetime.now().isoformat(),
                        'situation': situation,
                        'questions': questions,
                        'conversation': [questions[0]],  # 첫 번째 질문으로 시작
                        'scores': [],
                        'current_question_idx': 0,
                        'is_finished': False,
                        'final_feedback': None
                    }
                    st.session_state.current_chat_id = chat_id
                    save_chats()
                    st.success("✨ 새로운 대화가 시작되었어요!")
                    st.rerun()
                else:
                    st.error("질문 생성에 실패했어요 😢")
            else:
                st.error("상황 생성에 실패했어요 😢")
    
    st.markdown("---")
    
    # Chat list
    if st.session_state.chats:
        st.markdown("### 💭 대화 기록")
        for chat_id, chat_data in reversed(list(st.session_state.chats.items())):
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(
                    f"{'🌟' if chat_data.get('is_finished') else '💬'} {chat_data['title']}", 
                    key=f"chat_{chat_id}",
                    use_container_width=True
                ):
                    st.session_state.current_chat_id = chat_id
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{chat_id}"):
                    del st.session_state.chats[chat_id]
                    if st.session_state.current_chat_id == chat_id:
                        st.session_state.current_chat_id = None
                    save_chats()
                    st.rerun()

# Main content
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.chats:
    current_chat = st.session_state.chats[st.session_state.current_chat_id]
    
    st.markdown(f"<h1 style='text-align: center; color: white;'>🌙 {current_chat['title']}</h1>", unsafe_allow_html=True)
    
    # Display conversation
    conversation = current_chat['conversation']
    scores = current_chat.get('scores', [])
    questions = current_chat.get('questions', [])
    
    # Show conversation history
    for i, message in enumerate(conversation):
        if i % 2 == 0:  # AI messages (첫 번째 질문부터 시작)
            st.markdown(f'<div class="ai-message">🌙 <strong>투닥이:</strong> {message}</div>', unsafe_allow_html=True)
        else:  # User messages
            score_indicator = ""
            score_idx = (i - 1) // 2
            if score_idx < len(scores):
                score = scores[score_idx]
                if score == 1:
                    score_indicator = '<span class="emotion-score empathy-high">💝 공감적</span>'
                else:
                    score_indicator = '<span class="emotion-score empathy-low">😔 차가움</span>'
            st.markdown(f'<div class="user-message"><strong>나:</strong> {message} {score_indicator}</div>', unsafe_allow_html=True)
    
    # Show score summary if there are scores
    if scores:
        empathy_count = sum(scores)
        total_count = len(scores)
        empathy_percentage = (empathy_count / total_count) * 100 if total_count > 0 else 0
        
        st.markdown(f"""
        <div class="score-summary">
            <h4>🎯 공감도 현황</h4>
            <p><strong>{empathy_count}/{total_count}</strong> 번의 공감적 응답 ({empathy_percentage:.1f}%)</p>
            <div style="background: #e0e0e0; border-radius: 10px; height: 20px; margin: 10px 0;">
                <div style="background: linear-gradient(135deg, #4CAF50, #45a049); height: 20px; border-radius: 10px; width: {empathy_percentage}%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show final feedback if conversation is finished
    if current_chat.get('is_finished') and current_chat.get('final_feedback'):
        st.markdown(f"""
        <div class="final-feedback">
            <h3>💌 투닥이의 최종 피드백</h3>
            <p style="font-size: 16px; font-weight: bold;">{current_chat['final_feedback']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Debug info (optional)
    with st.expander("🔍 정보"):
        st.write("생성된 상황:", current_chat.get('situation', 'N/A'))
        st.write("생성된 질문들:", current_chat.get('questions', []))
        st.write("현재 질문 인덱스:", current_chat.get('current_question_idx', 0))
        st.write("점수 기록:", scores)
        st.write("대화 길이:", len(conversation))
    
    # Chat input (only if conversation is not finished)
    if not current_chat.get('is_finished') and chat:
        with st.container():
            st.markdown("---")
            user_input = st.text_input(
                "💭 투닥이에게 답해주세요...", 
                key="user_input",
                placeholder="따뜻한 말로 응답해보세요 💝"
            )
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                send_clicked = st.button("💌 답장 보내기", use_container_width=True)
            
            if send_clicked and user_input.strip():
                with st.spinner("투닥이가 당신의 마음을 느끼고 있어요... 💭"):
                    # Add user response to conversation
                    current_chat['conversation'].append(user_input.strip())
                    
                    # Evaluate the response using your original logic
                    score, ai_response = evaluate_response(chat, current_chat['conversation'])
                    current_chat['scores'].append(score)
                    
                    # Check if we should continue or finish
                    current_question_idx = current_chat.get('current_question_idx', 0)
                    questions = current_chat['questions']
                    
                    if current_question_idx < len(questions) - 1:
                        # Continue with next question - 원본 로직에 따라 AI 응답 + 다음 질문 결합
                        current_question_idx += 1
                        current_chat['current_question_idx'] = current_question_idx
                        next_question = questions[current_question_idx]
                        full_ai_response = f"{ai_response} {next_question}"
                        current_chat['conversation'].append(full_ai_response)
                    else:
                        # Finish conversation and generate feedback
                        current_chat['conversation'].append(ai_response)
                        if chat_feedback:
                            final_feedback = generate_final_feedback(chat_feedback, current_chat['conversation'])
                            current_chat['final_feedback'] = final_feedback
                        current_chat['is_finished'] = True
                    
                    save_chats()
                    st.rerun()

else:
    # Welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 50px 20px; color: white;">
        <h1>🌙 투닥이와의 감정 대화</h1>
        <h3>AI와 감정을 나누고 공감 능력을 키워보세요</h3>
        <p style="font-size: 18px; margin: 30px 0;">
            투닥이는 감정이 풍부한 F타입 AI입니다.<br>
            투닥이의 고민을 들어주고, 따뜻하게 위로해주세요. 💝
        </p>
        <p style="font-size: 16px; opacity: 0.8;">
            ← 왼쪽 사이드바에서 "새로운 대화 시작"을 클릭해보세요!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # # Features
    # col1, col2, col3 = st.columns(3)
    
    # with col1:
    #     st.markdown("""
    #     <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; text-align: center; color: white; margin: 10px;">
    #         <h4>🎭 실제 AI 상황 생성</h4>
    #         <p>HCX-007이 실시간으로 감정적 상황을 만들어냅니다</p>
    #     </div>
    #     """, unsafe_allow_html=True)
    
    # with col2:
    #     st.markdown("""
    #     <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; text-align: center; color: white; margin: 10px;">
    #         <h4>⚖️ JSON 기반 점수 평가</h4>
    #         <p>AI가 당신의 공감 능력을 정확히 측정합니다</p>
    #     </div>
    #     """, unsafe_allow_html=True)
    
    # with col3:
    #     st.markdown("""
    #     <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; text-align: center; color: white; margin: 10px;">
    #         <h4>💌 맞춤형 피드백</h4>
    #         <p>대화 전체를 분석한 솔직한 피드백을 받아보세요</p>
    #     </div>
    #     """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.6); font-size: 14px;">
    Made with 💝 using ChatClovaX HCX-007 | 투닥이 v2.0
</div>
""", unsafe_allow_html=True)