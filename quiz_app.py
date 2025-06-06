import streamlit as st
import random
import datetime
import io
import pandas as pd
import os
import json

# 문제 유형 라벨
TYPE_LABELS = {
    '참거짓': 'True/False',
    '단답형:일반': 'Short Answer',
    '단답형:빈칸': 'Fill in the Blank',
    '단답형:한글': 'Korean Term',
    '단답형:약자': 'Acronym',
    '객관식': 'Multiple Choice'
}

# 문제 불러오기 (JSON)
def load_questions_from_json(file):
    raw = json.load(file)
    questions = []
    for item in raw:
        qtype = item.get('type', '객관식')
        label = TYPE_LABELS.get(qtype, qtype)
        question = item['question']
        options = item.get('options', [])
        answer = item['answer']
        questions.append({
            'type': qtype,
            'label': label,
            'question': question,
            'options': options,
            'answer': answer
        })
    return questions

# 결과 텍스트 생성
def generate_result_text(questions, user_answers, score):
    output = io.StringIO()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    output.write(f"GIS 랜덤 퀴즈 결과 - {now}\n")
    output.write(f"총 점수: {score} / {len(questions)}\n\n")
    for idx, (q, ua) in enumerate(zip(questions, user_answers), start=1):
        correct = q['options'][q['answer']] if isinstance(q['answer'], int) else str(q['answer'])
        result = "정답" if correct.strip() == ua.strip() else "오답"
        output.write(f"{idx}. [{q['label']}] {q['question']}\n")
        output.write(f"    - 정답: {correct} | 내 답: {ua} → {result}\n")
    return output.getvalue()

# 통계 저장
def save_stats_to_csv(questions, user_answers, score, filepath="quiz_stats.csv"):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data = []
    for q, ua in zip(questions, user_answers):
        correct = q['options'][q['answer']] if isinstance(q['answer'], int) else str(q['answer'])
        user = ua.strip()
        is_correct = correct.strip() == user
        data.append({
            "timestamp": now,
            "type": q['type'],
            "label": q['label'],
            "question": q['question'],
            "user_answer": user,
            "correct_answer": correct,
            "result": "정답" if is_correct else "오답"
        })
    new_df = pd.DataFrame(data)
    if os.path.exists(filepath):
        existing_df = pd.read_csv(filepath)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
    combined_df.to_csv(filepath, index=False)

# 스트림릿 앱 실행
st.title("🌍 GIS 랜덤 퀴즈 (JSON 기반)")

uploaded_file = st.file_uploader("📁 문제 JSON 파일을 업로드해주세요", type=['json'])

if uploaded_file:
    all_questions = load_questions_from_json(uploaded_file)
    total_available = len(all_questions)

    if total_available < 5:
        st.warning("❗ 문제 수가 너무 적습니다.")
    else:
        tab1, tab2 = st.tabs(["📝 퀴즈 풀기", "📊 통계 보기"])

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
                st.info("📌 오답률이 높은 문제들입니다.")
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
                    correct = q['options'][q['answer']] if isinstance(q['answer'], int) else str(q['answer'])
                    user = ua.strip()
                    is_correct = correct.strip() == user
                    if is_correct:
                        score += 1
                    st.markdown(f"{idx}. {'✅ 정답' if is_correct else f'❌ 오답'} - 정답: {correct} / 내 답: {user}")
                st.success(f"🎯 총 점수: {score} / {len(selected_questions)}")
                result_text = generate_result_text(selected_questions, user_answers, score)
                st.download_button("📥 결과 저장 (txt)", result_text, file_name="quiz_result.txt")
                save_stats_to_csv(selected_questions, user_answers, score)
