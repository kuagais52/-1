
import streamlit as st
import random
import datetime
import io
import pandas as pd
import os

# 문제 유형 라벨
TYPE_LABELS = {
    '참거짓': 'True/False',
    '단답형:일반': 'Short Answer',
    '단답형:빈칸': 'Fill in the Blank',
    '단답형:한글': 'Korean Term',
    '단답형:약자': 'Acronym',
    '객관식': 'Multiple Choice'
}

# 문제 불러오기
def load_questions_from_txt(file):
    questions = []
    lines = file.getvalue().decode('utf-8').splitlines()
    for line in lines:
        if line.strip():
            parts = line.strip().split('|')
            if len(parts) >= 4:
                _, qtype, question, answer_raw = parts[:4]
                if qtype == '객관식':
                    options_with_numbers = [opt.strip() for opt in parts[4:]]
                    options = [opt.split(')', 1)[1].strip() if ')' in opt else opt for opt in options_with_numbers]
                    # answer_raw가 숫자일 경우 -> 해당 옵션 텍스트로 정답 대체
                    if answer_raw.strip().isdigit():
                        idx = int(answer_raw.strip()) - 1
                        answer = options[idx] if 0 <= idx < len(options) else answer_raw
                    else:
                        answer = answer_raw
                else:
                    options = []
                    answer = answer_raw
                questions.append({
                    'type': qtype,
                    'label': TYPE_LABELS.get(qtype, qtype),
                    'question': question,
                    'answer': answer,
                    'options': options
                })
    return questions

# 결과 파일 생성
def generate_result_text(questions, user_answers, score):
    output = io.StringIO()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    output.write(f"GIS 랜덤 퀴즈 결과 - {now}\n")
    output.write(f"총 점수: {score} / {len(questions)}\n\n")
    for idx, (q, ua) in enumerate(zip(questions, user_answers), start=1):
        correct = q['answer'].strip().lower()
        user = ua.strip().lower()
        result = "정답" if correct == user else "오답"
        output.write(f"{idx}. [{q['label']}] {q['question']}\n")
        output.write(f"    - 정답: {q['answer']} | 내 답: {ua} → {result}\n")
    return output.getvalue()

# 통계 저장
def save_stats_to_csv(questions, user_answers, score, filepath="quiz_stats.csv"):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data = []
    for q, ua in zip(questions, user_answers):
        correct = q['answer'].strip().lower()
        user = ua.strip().lower()
        is_correct = correct == user
        data.append({
            "timestamp": now,
            "type": q['type'],
            "label": q['label'],
            "question": q['question'],
            "user_answer": ua,
            "correct_answer": q['answer'],
            "result": "정답" if is_correct else "오답"
        })

    new_df = pd.DataFrame(data)
    if os.path.exists(filepath):
        existing_df = pd.read_csv(filepath)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_csv(filepath, index=False)

# 앱 실행
st.title("🌍 GIS 랜덤 퀴즈 웹앱")

uploaded_file = st.file_uploader("📁 문제.txt 파일을 업로드해주세요", type=['txt'])

if uploaded_file:
    all_questions = load_questions_from_txt(uploaded_file)
    total_available = len(all_questions)

    if total_available < 5:
        st.warning("❗ 문제 수가 너무 적습니다. 파일을 확인해주세요.")
    else:
        tab1, tab2 = st.tabs(["📝 퀴즈 풀기", "📊 내 통계 보기"])

        with tab1:
            st.sidebar.subheader("🛠️ 문제 수 설정")
            num_questions = st.sidebar.slider(
                "출제할 문제 수",
                min_value=1,
                max_value=total_available,
                value=min(10, total_available)
            )

            if st.sidebar.button("🔄 문제 새로 뽑기"):
                st.session_state['selected_questions'] = random.sample(all_questions, num_questions)
                st.session_state['from_wrong_top'] = False

            if 'selected_questions' not in st.session_state or (len(st.session_state['selected_questions']) != num_questions and not st.session_state.get('from_wrong_top')):
                st.session_state['selected_questions'] = random.sample(all_questions, num_questions)

            selected_questions = st.session_state['selected_questions']

            if st.session_state.get('from_wrong_top'):
                st.info("📌 이 퀴즈는 오답률이 높은 문제들로 구성되었습니다.")
                del st.session_state['from_wrong_top']

            st.subheader("📝 퀴즈 문제")
            user_answers = []

            with st.form("quiz_form"):
                for idx, q in enumerate(selected_questions, start=1):
                    st.markdown(f"**{idx}. [{q['label']}]** {q['question']}")
                    if q['type'] == '객관식' and q['options']:
                        answer = st.radio("선택지", options=q['options'], key=f"ans_{idx}")
                    else:
                        answer = st.text_input(f"답변 입력 {idx}", key=f"ans_{idx}")
                    user_answers.append(answer)

                submitted = st.form_submit_button("✅ 제출하기")

            if submitted:
                score = 0
                st.subheader("📊 채점 결과")
                for idx, (q, ua) in enumerate(zip(selected_questions, user_answers), start=1):
                    correct = q['answer'].strip().lower()
                    user = ua.strip().lower()
                    is_correct = correct == user
                    if is_correct:
                        score += 1
                    st.markdown(
                        f"{idx}. {'✅ 정답' if is_correct else f'❌ 오답'} - 정답: {q['answer']} / 내 답: {ua}"
                    )

                st.success(f"🎯 총 점수: {score} / {len(selected_questions)}")

                result_text = generate_result_text(selected_questions, user_answers, score)
                st.download_button("📥 결과 저장 (txt)", result_text, file_name="quiz_result.txt")

                save_stats_to_csv(selected_questions, user_answers, score)
