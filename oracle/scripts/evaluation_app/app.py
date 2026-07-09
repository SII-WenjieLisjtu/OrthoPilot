#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学AI评测系统 - Streamlit主应用
运行方式: streamlit run app.py
"""

import streamlit as st
import json
import os
import sys
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    MODELS, TASKS, RATING_DIMENSIONS,
    TITLE_OPTIONS, EXPERIENCE_OPTIONS, HOSPITAL_LEVEL_OPTIONS, SPECIALTY_OPTIONS
)
from utils.data_loader import (
    load_task_samples, get_available_tasks, get_sample_by_index, get_task_sample_count
)
from utils.storage import (
    load_doctors, save_doctor, get_doctor, save_evaluation,
    get_evaluated_case_ids, get_progress
)
from i18n import get_text, get_language_name

# 页面配置 - 必须在其他Streamlit命令之前
st.set_page_config(
    page_title="Medical AI Evaluation System | 医学AI评测系统",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS - 增大显示区域
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .model-tab {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin-bottom: 1rem;
    }
    .rating-label {
        font-weight: bold;
        color: #333;
    }
    .progress-bar {
        height: 20px;
        background-color: #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background-color: #4CAF50;
        transition: width 0.3s ease;
    }
    /* 思考过程样式 */
    .thinking-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .thinking-header {
        color: #856404;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 10px;
    }
    /* 最终回答样式 */
    .answer-box {
        background-color: #d4edda;
        border: 1px solid #28a745;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .answer-header {
        color: #155724;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 10px;
    }
    /* 增大文本区域 */
    .stTextArea textarea {
        font-size: 14px !important;
        line-height: 1.6 !important;
    }
</style>
""", unsafe_allow_html=True)

def parse_thinking_and_answer(output: str) -> tuple:
    """
    解析模型输出，分离思考过程和最终回答
    返回: (thinking, answer)
    """
    import re

    # 处理空输出
    if not output or output == "无输出":
        return "", "无输出"

    # 尝试匹配 <think>...</think> 格式
    think_pattern = r'<think>(.*?)</think>'
    think_match = re.search(think_pattern, output, re.DOTALL)

    if think_match:
        thinking = think_match.group(1).strip()
        # 移除思考部分，剩余为回答
        answer = re.sub(think_pattern, '', output, flags=re.DOTALL).strip()
        return thinking, answer

    # 尝试匹配 【思考】...【回答】 格式
    if '【思考】' in output and '【回答】' in output:
        parts = output.split('【回答】')
        thinking = parts[0].replace('【思考】', '').strip()
        answer = parts[1].strip() if len(parts) > 1 else ""
        return thinking, answer

    # 尝试匹配 **思考过程**...  格式
    if '思考过程' in output or '思考：' in output or '分析：' in output:
        # 查找可能的分隔点
        for sep in ['\n\n最终', '\n\n回答：', '\n\n结论：', '\n\n建议：', '\n\n诊断', '\n\n治疗']:
            if sep in output:
                idx = output.find(sep)
                thinking = output[:idx].strip()
                answer = output[idx:].strip()
                return thinking, answer

    # 无法分离时，全部作为回答
    return "", output

def init_session_state():
    """初始化会话状态"""
    if "doctor_id" not in st.session_state:
        st.session_state.doctor_id = None
    if "current_task" not in st.session_state:
        st.session_state.current_task = None
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "language" not in st.session_state:
        st.session_state.language = "zh"

def show_login_page():
    """显示登录/注册页面"""
    lang = st.session_state.language

    st.markdown(f'<div class="main-header">{get_text("page.icon", lang)} {get_text("page.title", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f"### {get_text('login.tab_login', lang)}/{get_text('login.tab_register', lang)}")

    # 检查是否有已存在的医生
    doctors = load_doctors()

    tab1, tab2 = st.tabs([get_text("login.tab_login", lang), get_text("login.tab_register", lang)])

    with tab1:
        if doctors:
            # 处理 doctors 可能是列表或字典的情况
            if isinstance(doctors, list):
                doctor_options = {f"{d['name']} ({d['doctor_id']})": d['doctor_id']
                                  for d in doctors}
            else:
                doctor_options = {f"{d['name']} ({d['doctor_id']})": d['doctor_id']
                                  for d in doctors.values()}
            selected = st.selectbox(
                get_text("login.label_name", lang),
                options=list(doctor_options.keys()),
                key="login_select"
            )
            if st.button(get_text("login.button_login", lang), key="login_btn"):
                st.session_state.doctor_id = doctor_options[selected]
                st.success(get_text("login.success_login", lang))
                st.rerun()
        else:
            st.info(get_text("login.error_not_found", lang))

    with tab2:
        with st.form("register_form"):
            st.markdown(f"#### {get_text('login.tab_register', lang)}")

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(f"{get_text('login.label_name', lang)} *", placeholder=get_text('login.label_name', lang))
                title_options = get_text("config.title_options", lang)
                title = st.selectbox(f"{get_text('login.label_title', lang)} *", options=title_options)
                specialty_options = get_text("config.specialty_options", lang)
                specialty = st.selectbox(f"{get_text('login.label_specialty', lang)} *", options=specialty_options)

            with col2:
                experience_options = get_text("config.experience_options", lang)
                experience = st.selectbox(f"{get_text('login.label_experience', lang)} *", options=experience_options)
                hospital_options = get_text("config.hospital_options", lang)
                hospital_level = st.selectbox(f"{get_text('login.label_hospital', lang)} *", options=hospital_options)
                hospital_name = st.text_input(get_text('login.label_hospital', lang), placeholder="")

            submitted = st.form_submit_button(get_text("login.button_register", lang))

            if submitted:
                if not name:
                    st.error(get_text("login.error_empty", lang))
                else:
                    doctor_info = {
                        "name": name,
                        "title": title,
                        "specialty": specialty,
                        "experience_years": experience,  # 使用 experience_years 保持一致
                        "hospital_level": hospital_level,
                        "hospital_name": hospital_name
                    }
                    doctor_id = save_doctor(doctor_info)
                    st.session_state.doctor_id = doctor_id
                    st.success(get_text("login.success_register", lang))
                    st.rerun()

def show_task_selection():
    """显示任务选择页面"""
    lang = st.session_state.language
    doctor = get_doctor(st.session_state.doctor_id)
    st.markdown(f"### {get_text('task_selection.welcome', lang, name=doctor['name'], title=doctor['title'])}")

    st.markdown(f"### {get_text('task_selection.select_task', lang)}")

    available_tasks = get_available_tasks()

    cols = st.columns(3)
    for i, (task_id, info) in enumerate(available_tasks.items()):
        with cols[i % 3]:
            progress = get_progress(st.session_state.doctor_id, task_id, info['sample_count'])

            # 根据语言选择任务名称和描述
            task_name = TASKS[task_id].get('name_en' if lang == 'en' else 'name', TASKS[task_id]['name'])
            task_desc = TASKS[task_id].get('description_en' if lang == 'en' else 'description', TASKS[task_id]['description'])

            st.markdown(f"**Task {task_id}: {task_name}**")
            st.markdown(f"_{task_desc}_")
            st.markdown(f"{get_text('task_selection.progress', lang)}: {get_text('task_selection.completed', lang, completed=progress['completed'], total=progress['total'])}")

            # 进度条
            pct = progress['completed'] / progress['total'] * 100 if progress['total'] > 0 else 0
            st.progress(pct / 100)

            button_text = get_text('task_selection.button_start', lang) if progress['completed'] == 0 else get_text('task_selection.button_continue', lang)
            if st.button(f"{button_text} Task {task_id}", key=f"start_task_{task_id}"):
                st.session_state.current_task = task_id
                st.session_state.current_index = progress['completed']
                st.session_state.start_time = datetime.now()
                st.rerun()

    st.markdown("---")
    if st.button(get_text("sidebar.logout", lang)):
        st.session_state.doctor_id = None
        st.session_state.current_task = None
        st.rerun()

def show_evaluation_page():
    """显示评价页面"""
    lang = st.session_state.language
    task_id = st.session_state.current_task
    index = st.session_state.current_index
    doctor_id = st.session_state.doctor_id

    samples = load_task_samples(task_id)
    total_samples = len(samples)

    # 获取已评价的case_ids
    evaluated_ids = get_evaluated_case_ids(doctor_id, task_id)

    # 找到下一个未评价的样本
    current_sample = None
    for i, sample in enumerate(samples):
        if sample['case_id'] not in evaluated_ids:
            current_sample = sample
            index = i
            break

    if current_sample is None:
        st.success(get_text("evaluation.task_complete", lang))
        if st.button(get_text("evaluation.button_back", lang)):
            st.session_state.current_task = None
            st.rerun()
        return

    # 顶部信息栏
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        task_name = TASKS[task_id].get('name_en' if lang == 'en' else 'name', TASKS[task_id]['name'])
        st.markdown(f"### Task {task_id}: {task_name}")
    with col2:
        progress = len(evaluated_ids)
        st.metric(get_text("evaluation.progress", lang, current=progress, total=total_samples), f"{progress}/{total_samples}")
    with col3:
        if st.button(get_text("evaluation.button_back", lang)):
            st.session_state.current_task = None
            st.rerun()

    st.markdown("---")

    # 患者信息
    with st.expander(f"📋 {get_text('evaluation.patient_info', lang)}", expanded=True):
        st.markdown(current_sample['patient_info'])

    st.markdown("---")

    # 模型回答展示
    st.markdown(f"### 📝 {get_text('evaluation.model_answer', lang)}")
    tabs = st.tabs(MODELS)

    for tab, model in zip(tabs, MODELS):
        with tab:
            output = current_sample['model_outputs'].get(model, "无输出")
            thinking, answer = parse_thinking_and_answer(output)

            st.markdown(f"**{model}**")

            # 显示思考过程（如果有）
            if thinking:
                st.markdown('<div class="thinking-box">', unsafe_allow_html=True)
                st.markdown("**🧠 思考过程**")
                st.text_area(
                    label="",
                    value=thinking,
                    height=250,
                    key=f"thinking_{model}",
                    disabled=True
                )
                st.markdown('</div>', unsafe_allow_html=True)

            # 显示最终回答
            st.markdown('<div class="answer-box">', unsafe_allow_html=True)
            st.markdown("**✅ 最终回答**")
            st.text_area(
                label="",
                value=answer,
                height=400,
                key=f"answer_{model}",
                disabled=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 评价表单
    with st.form("evaluation_form"):
        st.markdown(f"### 🏆 {get_text('evaluation.evaluation_form', lang)}")
        st.markdown(get_text("evaluation.score_help", lang))

        rank_cols = st.columns(4)
        rankings = {}
        for i, model in enumerate(MODELS):
            with rank_cols[i]:
                rankings[model] = st.selectbox(
                    f"{model}",
                    options=[1, 2, 3, 4],
                    index=i,
                    key=f"rank_{model}"
                )

        allow_ties = st.checkbox("允许并列（如有模型质量相当）", value=False)

        st.markdown("---")
        st.markdown(f"### ⭐ {get_text('evaluation.label_score', lang)}")

        # 获取评分维度
        rating_dimensions = get_text("config.rating_dimensions", lang)

        likert_scores = {}
        for model in MODELS:
            st.markdown(f"**{model}**")
            score_cols = st.columns(5)
            likert_scores[model] = {}
            for j, (dim_key, dim_name) in enumerate(rating_dimensions.items()):
                with score_cols[j]:
                    likert_scores[model][dim_key] = st.slider(
                        dim_name,
                        min_value=1,
                        max_value=5,
                        value=3,
                        key=f"likert_{model}_{dim_key}"
                    )

        st.markdown("---")
        st.markdown("### ⚠️ 严重错误标记")
        st.markdown("勾选存在可能导致患者伤害的严重错误的模型")

        error_cols = st.columns(4)
        critical_errors = {}
        for i, model in enumerate(MODELS):
            with error_cols[i]:
                critical_errors[model] = st.checkbox(f"{model}", key=f"error_{model}")

        st.markdown("---")
        st.markdown(f"### 💬 {get_text('evaluation.label_comment', lang)}")
        rationale = st.text_area(
            get_text("evaluation.placeholder_comment", lang),
            max_chars=200,
            key="rationale"
        )

        submitted = st.form_submit_button(get_text("evaluation.button_submit", lang), type="primary")

        if submitted:
            # 验证排序
            rank_values = list(rankings.values())
            if not allow_ties and len(rank_values) != len(set(rank_values)):
                st.error(get_text("evaluation.ranking_error", lang))
            else:
                # 计算评价用时
                time_spent = 0
                if st.session_state.start_time:
                    time_spent = (datetime.now() - st.session_state.start_time).total_seconds()

                # 构建评价数据
                evaluation = {
                    "doctor_id": doctor_id,
                    "task_id": task_id,
                    "case_id": current_sample['case_id'],
                    "timestamp": datetime.now().isoformat(),
                    "time_spent_seconds": round(time_spent),
                    "ranking": rankings,
                    "allow_ties": allow_ties,
                    "likert_scores": likert_scores,
                    "critical_errors": critical_errors,
                    "rationale": rationale
                }

                # 保存评价
                save_evaluation(evaluation)

                st.success(get_text("evaluation.success_submit", lang))
                st.session_state.start_time = datetime.now()
                st.rerun()

def show_sidebar():
    """显示侧边栏"""
    lang = st.session_state.language

    with st.sidebar:
        # 语言切换器和标题
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"## {get_text('page.icon', lang)} {get_text('sidebar.system_title', lang)}")
        with col2:
            # 语言切换按钮
            current_lang_name = "EN" if lang == "zh" else "中"
            if st.button(current_lang_name, key="lang_switch"):
                st.session_state.language = "en" if lang == "zh" else "zh"
                st.rerun()

        st.markdown("---")

        # 用户信息
        if st.session_state.doctor_id:
            doctor = get_doctor(st.session_state.doctor_id)
            if doctor:
                st.markdown(f"**{get_text('sidebar.user_info', lang)}**")
                st.markdown(f"**{get_text('sidebar.name', lang)}:** {doctor['name']}")
                st.markdown(f"**{get_text('sidebar.title', lang)}:** {doctor['title']}")
                st.markdown(f"**{get_text('sidebar.specialty', lang)}:** {doctor['specialty']}")
                # 使用 experience_years 字段，如果不存在则使用 experience
                experience = doctor.get('experience_years', doctor.get('experience', 'N/A'))
                st.markdown(f"**{get_text('sidebar.experience', lang)}:** {experience}")
                st.markdown(f"**{get_text('sidebar.hospital', lang)}:** {doctor['hospital_level']}")

        st.markdown("---")
        st.markdown(f"### {get_text('sidebar.instructions_title', lang)}")
        instructions = get_text('sidebar.instructions', lang)
        for instruction in instructions:
            st.markdown(instruction)

def main():
    init_session_state()

    # 显示侧边栏
    show_sidebar()

    # 主页面逻辑
    if st.session_state.doctor_id is None:
        show_login_page()
    elif st.session_state.current_task is None:
        show_task_selection()
    else:
        show_evaluation_page()

if __name__ == "__main__":
    main()
