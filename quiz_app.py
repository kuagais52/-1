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
                _, qtype, question, answer = parts[:4]
                options = parts[4:] if qtype == '객관식' else []
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

        # 📝 탭 1: 퀴즈 풀기
        with tab1:
            st.sidebar.subheader("🛠️ 문제 수 설정")
            num_questions = st.sidebar.slider("출제할 문제 수", min_value=5, max_value=min(100, total_available), value=10)

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

        # 📊 탭 2: 통계 보기
        with tab2:
            stats_file = "quiz_stats.csv"
            if os.path.exists(stats_file):
                df = pd.read_csv(stats_file)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['정답여부'] = df['result'] == '정답'

                st.subheader("📋 통계 요약")

                total = len(df)
                correct = df['정답여부'].sum()
                st.metric("전체 정답률", f"{correct}/{total} ({correct/total:.0%})")

                type_summary = df.groupby('label')['정답여부'].agg(['count', 'sum'])
                type_summary['정답률(%)'] = (type_summary['sum'] / type_summary['count'] * 100).round(1)
                st.markdown("📌 문제 유형별 정답률")
                st.dataframe(type_summary.rename(columns={'count': '총 개수', 'sum': '정답 수'}))

                wrong = df[df['result'] == '오답']
                if not wrong.empty:
                    st.markdown("❌ 최근 틀린 문제 (최대 5개)")
                    st.dataframe(wrong[['timestamp', 'label', 'question', 'user_answer', 'correct_answer']].tail(5))
                else:
                    st.success("🎉 최근에 틀린 문제가 없습니다!")

                # 📈 시각화
                st.subheader("📈 시각화")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🗓️ 날짜별 정답률")
                    score_summary = df.groupby(df['timestamp'].dt.date)['정답여부'].agg(['count', 'sum']).reset_index()
                    score_summary['정답률(%)'] = (score_summary['sum'] / score_summary['count'] * 100).round(1)
                    score_summary.columns = ['날짜', '전체 수', '맞은 수', '정답률(%)']
                    st.line_chart(score_summary.set_index('날짜')['정답률(%)'])

                with col2:
                    st.markdown("### 🧩 유형별 누적 정답률")
                    bar_data = type_summary['정답률(%)'].sort_values(ascending=False)
                    st.bar_chart(bar_data)

                st.markdown("### 🔥 히트맵 (날짜 vs. 문제 유형 정답 수)")
                heat_df = df.groupby([df['timestamp'].dt.date, 'label'])['정답여부'].sum().unstack(fill_value=0)
                st.dataframe(heat_df.style.background_gradient(cmap='Blues', axis=None))

                # 📉 오답률 상위 문제 다시 풀기
                st.markdown("### 🧪 오답률 상위 문제로 다시 풀기")
                wrong_rate_df = df.groupby(['question', 'label', 'correct_answer'])['정답여부'].agg(['count', 'sum']).reset_index()
                wrong_rate_df['오답률'] = ((wrong_rate_df['count'] - wrong_rate_df['sum']) / wrong_rate_df['count']).round(2)
                wrong_rate_df = wrong_rate_df.sort_values(by='오답률', ascending=False)

                top_wrong_questions = wrong_rate_df.head(5)
                top_questions = []
                for _, row in top_wrong_questions.iterrows():
                    top_questions.append({
                        'type': row['label'],
                        'label': row['label'],
                        'question': row['question'],
                        'answer': row['correct_answer'],
                        'options': []  # 객관식이더라도 옵션은 없음 (실제 문제파일에서 추출 필요)
                    })

                if st.button("📉 오답률 상위 문제로 다시 풀기"):
                    st.session_state['selected_questions'] = top_questions
                    st.session_state['from_wrong_top'] = True
                    st.experimental_rerun()
            else:
                st.warning("📂 아직 저장된 통계가 없습니다. 퀴즈를 먼저 풀어주세요.")
