import streamlit as st
import requests

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

# 타이틀
st.title("💬 F와의 거리")

# 🎯 대화 시작
if not st.session_state.started:
    if st.button("🎯 대화 시작하기"):
        with st.spinner("상황을 준비 중입니다..."):
            payload = {
                "user_nickname": st.session_state.user_nickname,
                "chatbot_name": st.session_state.chatbot_name
            }

            try:
                res = requests.post(f"{API_BASE}/situation", json=payload)
                if res.status_code == 200:
                    res_data = res.json()
                    st.session_state.quiz_list = res_data["quiz_list"]
                    st.session_state.started = True
                    first_bot_message = f"안녕... {st.session_state.quiz_list[0]}"
                    st.session_state.conversation.append(first_bot_message)
                else:
                    st.error("❌ 상황 생성 실패: 서버에서 에러가 발생했습니다.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ 서버 연결 오류: {e}")

            # res_data = {
            #     "situation": "깜짝 생일파티 준비 중인데, 친구가 좋아해줄까 걱정될 때",
            #     "quiz_list": [
            #         "내 말 좀 들어줄래...? 사실 이번에 깜짝 생일파티를 준비하고 있는데, 혹시라도 내 친구가 마음에 들지 않으면 어쩌나 걱정이 돼서...",
            #         "친구가 기뻐했으면 좋겠는데, 너무 과하게 준비한 건 아닐까 싶어서 자꾸 마음이 불안해져...😥",
            #         # "내가 열심히 준비한 게 헛수고가 될까 봐 두려워. 너라면 어떻게 생각해?",
            #     ]
            # }

            # st.session_state.quiz_list = res_data["quiz_list"]
            # st.session_state.started = True
            # first_bot_message = f"안녕... {st.session_state.quiz_list[0]}"
            # st.session_state.conversation.append(first_bot_message)
 
            st.rerun()

# 💬 대화 인터페이스
if st.session_state.started:
# 대화 기록 표시
    for i in range(0, len(st.session_state.conversation), 2):
        st.markdown(f"🐥 **{st.session_state.chatbot_name}**: {st.session_state.conversation[i]}")
        if i + 1 < len(st.session_state.conversation):
            st.markdown(f"🐕 **{st.session_state.user_nickname}**: {st.session_state.conversation[i + 1]}")
    
    # 사용자 입력 처리
    if user_input := st.chat_input(f"{st.session_state.user_nickname}의 응답", disabled=st.session_state.feedback is not None):
        st.session_state.conversation.append(user_input)

        # 마지막 질문에 대한 응답이라면 자동 응답 + 피드백
        if st.session_state.current_idx == len(st.session_state.quiz_list) -1 :
            final_bot_msg = "지금까지 이야기해줘서 고마워 😊"
            st.session_state.conversation.append(final_bot_msg)

            st.session_state.current_idx += 1  # 마지막 질문 처리 완료
            st.rerun()

        # 요청 payload 생성
        payload = {
            "user_nickname": st.session_state.user_nickname,
            "chatbot_name": st.session_state.chatbot_name,
            "conversation": st.session_state.conversation + [user_input],  # 아직 state에는 반영하지 않음
            "quiz_list": st.session_state.quiz_list,
            "current_distance": 1
        }

        # 사용자 메시지 추가
        # st.session_state.conversation.append(user_input)

        # 챗봇 응답 처리
        with st.chat_message(st.session_state.chatbot_name):
            with st.spinner(f"{st.session_state.chatbot_name}가 생각 중이에요..."):
 
                res = requests.post(f"{API_BASE}/conversation", json=payload)

                if res.status_code == 200:
                    data = res.json()

                    if not data.get("verification", False):
                        st.warning("❗ 이상한 말 하지 마세요.")
                        st.session_state.conversation.pop()
                    
                    else:
                        next_message = f"{data.get('react', '')} {data.get('improved_quiz', '')}".strip()
                        st.session_state.conversation.append(next_message)

                        # 퀴즈 업데이트 및 인덱스 증가
                        st.session_state.current_idx += 1
                        st.session_state.quiz_list[st.session_state.current_idx] = data.get('improved_quiz', '')

        st.rerun()
    if (
        st.session_state.current_idx >= len(st.session_state.quiz_list)
        and st.session_state.feedback is None
    ):
        with st.spinner("피드백을 생성 중입니다..."):
            fb_payload = {
                "user_nickname": st.session_state.user_nickname,
                "chatbot_name": st.session_state.chatbot_name,
                "conversation": st.session_state.conversation,
                "current_distance": 3
            }
            fb_res = requests.post(f"{API_BASE}/feedback", json=fb_payload)
            if fb_res.status_code == 200:
                feedback_output = fb_res.json()
                print(feedback_output)
                feedback = f"📨안녕 {st.session_state.user_nickname}!\n\n{feedback_output['feedback']}\n\n{feedback_output['last_greeting']}\n\n삐롱이가"
                length = str(len(feedback_output['feedback']))
                st.session_state.feedback = feedback

                st.rerun()
    # 저장된 피드백이 있으면 표시
    if st.session_state.feedback:
        st.success("🎉 모든 대화를 마쳤습니다!")
        length = str(len(st.session_state.feedback))
        st.markdown(f"편지 길이: {length}")
        st.info(st.session_state.feedback)