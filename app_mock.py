import streamlit as st
import requests
import time

API_BASE = "http://localhost:8000"

# --- 세션 상태 초기화 ---
def initialize_session():
    if "started" not in st.session_state:
        st.session_state.started = False
    if "quiz_list" not in st.session_state:
        st.session_state.quiz_list = []
    if "user_nickname" not in st.session_state:
        st.session_state.user_nickname = "삐롱이"
    if "chatbot_name" not in st.session_state:
        st.session_state.chatbot_name = "투닥이"
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = 0
    # 피드백 내용을 저장할 상태 변수 추가
    if "feedback" not in st.session_state:
        st.session_state.feedback = None

initialize_session()

# --- 사이드바 ---
with st.sidebar:
    st.markdown("### 👤 사용자 설정")
    st.session_state.user_nickname = st.text_input("사용자 닉네임", value=st.session_state.user_nickname)
    st.session_state.chatbot_name = st.text_input("챗봇 이름", value=st.session_state.chatbot_name)
    if st.button("🔄 대화 초기화"):
        # 세션 상태의 모든 키를 삭제하고 재초기화
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- 메인 화면 ---
st.title(f"💬 {st.session_state.chatbot_name}와의 거리")

# --- 대화 시작 버튼 ---
if not st.session_state.started:
    if st.button("🎯 대화 시작하기"):
        with st.spinner("상황을 준비 중입니다..."):
            # res = requests.post(f"{API_BASE}/situation", json=payload)
            res_data = {
                "situation": "깜짝 생일파티 준비 중인데, 친구가 좋아해줄까 걱정될 때",
                "quiz_list": [
                    "내 말 좀 들어줄래...? 사실 이번에 깜짝 생일파티를 준비하고 있는데, 혹시라도 내 친구가 마음에 들지 않으면 어쩌나 걱정이 돼서...",
                    "친구가 기뻐했으면 좋겠는데, 너무 과하게 준비한 건 아닐까 싶어서 자꾸 마음이 불안해져...😥",
                    "내가 열심히 준비한 게 헛수고가 될까 봐 두려워. 너라면 어떻게 생각해?",
                ]
            }
            st.session_state.quiz_list = res_data["quiz_list"]
            st.session_state.started = True
            first_bot_message = f"안녕... {st.session_state.quiz_list[0]}"
            st.session_state.conversation.append({"role": st.session_state.chatbot_name, "content": first_bot_message})
        st.rerun()

# --- 대화 인터페이스 ---
if st.session_state.started:
    # 대화 기록 표시
    for msg in st.session_state.conversation:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력 처리
    if user_input := st.chat_input(f"{st.session_state.user_nickname}의 응답", disabled=st.session_state.feedback is not None):
        # 사용자 메시지 추가
        st.session_state.conversation.append({"role": st.session_state.user_nickname, "content": user_input})

        # 챗봇 응답 처리
        with st.chat_message(st.session_state.chatbot_name):
            with st.spinner(f"{st.session_state.chatbot_name}가 생각 중이에요..."):
                st.session_state.current_idx += 1
                is_last_question = st.session_state.current_idx >= len(st.session_state.quiz_list)

                # Mock 챗봇 응답
                if not is_last_question:
                    next_message = f"그렇구나... {st.session_state.quiz_list[st.session_state.current_idx]}"
                else:
                    next_message = "네 생각을 들려줘서 고마워. 너랑 대화하길 정말 잘한 것 같아."

                st.session_state.conversation.append({"role": st.session_state.chatbot_name, "content": next_message})
        
        # 마지막 질문이었으면 피드백 생성 및 저장
        if is_last_question:
            with st.spinner("피드백을 생성 중입니다..."):
                # Mock 피드백 생성
                time.sleep(1) 
                mock_feedback = f"📨 **{st.session_state.chatbot_name}의 편지:**\n\n너와 대화하면서 정말 즐거웠어. 특히 내 걱정에 진심으로 공감해주는 모습에 큰 위로를 받았어. 앞으로도 좋은 친구가 될 수 있을 것 같아!"
                st.session_state.feedback = mock_feedback
        
        st.rerun()

    # 저장된 피드백이 있으면 표시
    if st.session_state.feedback:
        st.success("🎉 모든 대화를 마쳤습니다!")
        st.info(st.session_state.feedback)