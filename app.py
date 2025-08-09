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
        st.session_state.user_nickname = ""
    if "chatbot_name" not in st.session_state:
        st.session_state.chatbot_name = "투닥이"
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = 0
    if "current_distance" not in st.session_state:
        st.session_state.current_distance = 10  # 초기 거리값
    # 피드백 내용을 저장할 상태 변수 추가
    if "feedback" not in st.session_state:
        st.session_state.feedback = None

initialize_session()

# --- 사이드바 ---
with st.sidebar:
    st.markdown("### 👤 사용자 설정")
    st.session_state.user_nickname = st.text_input("사용자 닉네임", value=st.session_state.user_nickname)
    st.session_state.chatbot_name = st.text_input("챗봇 이름", value=st.session_state.chatbot_name)
    
    # 현재 상태 표시
    if st.session_state.started:
        st.markdown("### 📊 현재 상태")
        st.markdown(f"**현재 거리**: {st.session_state.current_distance}")
        st.markdown(f"**진행도**: {st.session_state.current_idx}/{len(st.session_state.quiz_list)}")
    
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
                # quiz_list = ['친구가 다음 주에 생일이라 깜짝 파티 준비하려는데, 정말 마음이 무거워...',
                #             '요즘 일이 너무 바빠서 시간 내기가 쉽지 않아... 그래서 더 초조해지고 있어.',
                #             '친구 몰래 다른 애들이랑 연락하면서 계획을 세워야 하니까 부담스럽기도 하고...',
                #             '선물도 골라야 하는데 도대체 어디서부터 시작해야 할지 감이 안 와...',
                #             '마음속으로는 이미 모든 게 완벽한 것 같은데, 현실은 왜 이렇게 복잡한지 모르겠어.',
                #             '이런 상황 속에서 그냥 도망치고 싶을 때도 많아... 하지만 친구 생각하면 그럴 수 없잖아?',
                #             '가끔씩 이럴 때마다 내가 진짜 뭘 할 수 있을까 의심하게 돼...',
                #             '그래도 이번엔 꼭 특별한 날을 만들어주고 싶어... 그게 내 욕심일까?',
                #             '혹시 나도 모르게 스트레스를 받고 있어서 그런 걸까...?',
                #             '결국 난 친구에게 좋은 시간을 선사하기 위해 최선을 다할 거지만, 지금은 조금 지쳐있는 것 같아... 이해해줬으면 좋겠다.']
                # st.session_state.quiz_list = quiz_list
                # st.session_state.started = True

                    first_bot_message = f"안녕... {st.session_state.user_nickname}! {st.session_state.quiz_list[0]}"
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
            final_bot_msg = "오늘 너랑 얘기해서 정말 즐거웠어 😊"
            st.session_state.conversation.append(final_bot_msg)

            st.session_state.current_idx += 1  # 마지막 질문 처리 완료
            st.rerun()

        # 요청 payload 생성
        payload = {
            "user_nickname": st.session_state.user_nickname,
            "chatbot_name": st.session_state.chatbot_name,
            "conversation": st.session_state.conversation,
            "quiz_list": st.session_state.quiz_list,
            "current_distance": st.session_state.current_distance
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
                        time.sleep(5)
                        st.session_state.conversation.pop()
                    
                    else:
                        # 성공적인 응답 처리
                        react = data.get('react', '')
                        improved_quiz = data.get('improved_quiz', '')
                        score = data.get('score',0)
                        next_message = f"{react} {improved_quiz}".strip()
                        
                        # print(react, score)
                        st.session_state.conversation.append(next_message)

                        # 퀴즈 업데이트 및 인덱스 증가
                        st.session_state.current_idx += 1
                        # st.session_state.quiz_list[st.session_state.current_idx] = data.get('improved_quiz', '')
                        st.session_state.current_distance = st.session_state.current_distance - (score)
                        print(f"점수: {score}, 현재 거리: {st.session_state.current_distance}")
                        # 다음 질문이 있으면 quiz_list 업데이트
                        if st.session_state.current_idx < len(st.session_state.quiz_list):
                            st.session_state.quiz_list[st.session_state.current_idx] = improved_quiz

        st.rerun()
    if (
        st.session_state.current_idx >= len(st.session_state.quiz_list)
        and st.session_state.feedback is None
    ):
        with st.spinner("✏️ 편지 작성중... 💌"):
            fb_payload = {
                "user_nickname": st.session_state.user_nickname,
                "chatbot_name": st.session_state.chatbot_name,
                "conversation": st.session_state.conversation,
                "current_distance": st.session_state.current_distance
            }
            fb_res = requests.post(f"{API_BASE}/feedback", json=fb_payload)
            if fb_res.status_code == 200:
                feedback_output = fb_res.json()
                feedback_text = feedback_output['feedback']
                last_greeting = feedback_output['last_greeting']
                # print(feedback_output)

                full_feedback = f"📨안녕 {st.session_state.user_nickname}!\n\n{feedback_text}\n\n{last_greeting}\n\n-{st.session_state.chatbot_name}-"
                st.session_state.feedback = full_feedback
                st.rerun()

    # 저장된 피드백이 있으면 표시
    if st.session_state.feedback:
        st.success("🎉 모든 대화를 마쳤습니다!")
        feedback_length = len(st.session_state.feedback)
        st.markdown(f"전체 편지 길이: {feedback_length}")
        st.info(st.session_state.feedback)

if __name__ == "__main__":
    import subprocess
    import sys
    
    # Streamlit 앱 실행
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        __file__, 
        "--server.port=8502", 
        "--server.address=0.0.0.0"
    ])