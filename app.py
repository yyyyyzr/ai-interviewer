import datetime
import json
import os
import re
import plotly.graph_objects as go
import streamlit as st
from openai import OpenAI

# ── 1. 页面基本配置与视觉美化 ───────────────────────────────────
st.set_page_config(page_title="AI 模拟面试官 Pro", page_icon="🤖", layout="wide")

# 隐藏默认底部水印，压缩全局留白，注入深空极客风配色灵感
st.markdown(
    """
<style>
    footer {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    button[data-baseweb="tab"] {font-size: 1.05rem; font-weight: 600;}
</style>
""",
    unsafe_allow_html=True,
)

# ── 2. 本地持久化数据库封装 ─────────────────────────────
HISTORY_FILE = "interview_records.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(records):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


# ── 3. 初始化进阶多轮会话 Session State ──────────────────
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "questions" not in st.session_state:
    st.session_state.questions = ""
if "current_job" not in st.session_state:
    st.session_state.current_job = ""
# 流程引擎核心状态：1代表初试答题，2代表深度追问答题，3代表已出最终报告
if "interview_stage" not in st.session_state:
    st.session_state.interview_stage = 1
if "round1_answer" not in st.session_state:
    st.session_state.round1_answer = ""
if "round1_feedback" not in st.session_state:
    st.session_state.round1_feedback = ""
if "round2_answer" not in st.session_state:
    st.session_state.round2_answer = ""
if "final_feedback" not in st.session_state:
    st.session_state.final_feedback = ""
if "radar_scores" not in st.session_state:
    st.session_state.radar_scores = {}


@st.cache_resource
def get_client():
    return OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )


# ── 4. 辅助映射与雷达图绘制引擎 (引入 Plotly 极客视觉) ──
MODE_MAP = {"⌨️ 键盘打字输入": "text", "🎙️ 原生语音作答": "audio"}


def draw_radar_chart(scores_dict):
    """根据分数返回具有深空科技感的 Plotly 雷达图对象"""
    categories = list(scores_dict.keys())
    values = [int(v) for v in scores_dict.values()]

    # 闭合雷达图环线
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                line=dict(color="#00F0FF", width=2),
                fillcolor="rgba(0, 240, 255, 0.25)",
                marker=dict(color="#00F0FF", size=6),
            )
        ]
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(255, 255, 255, 0.1)",
                linecolor="rgba(255, 255, 255, 0.1)",
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.1)",
                linecolor="rgba(255, 255, 255, 0.1)",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=30, t=20, b=20),
        height=260,
    )
    return fig


# ── 5. 二次确认清空弹窗 ───────────────────────────────
@st.dialog("⚠️ 危险操作确认")
def confirm_clear_dialog():
    st.warning(
        "您确定要彻底清空所有历史面试档案吗？此操作同步删除本地数据文件，且无法恢复。"
    )
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("取消", use_container_width=True):
            st.rerun()
    with col_d2:
        if st.button("确定清空", type="primary", use_container_width=True):
            st.session_state.history = []
            save_history([])
            st.rerun()


def reset_interview_flow():
    """重置整个面试引擎流状态"""
    st.session_state.questions = ""
    st.session_state.interview_stage = 1
    st.session_state.round1_answer = ""
    st.session_state.round1_feedback = ""
    st.session_state.round2_answer = ""
    st.session_state.final_feedback = ""
    st.session_state.radar_scores = {}


# ── 6. 页面顶栏布局 ───────────────────────────────────
st.title("🤖 AI 模拟面试官 Pro")
st.caption(
    "东南大学 - 机器人工程专属作品集 | 双轮压力测试引擎 + Plotly 多维度量化评估平台"
)
st.divider()

tab_interview, tab_strategy, tab_history = st.tabs(
    ["🎯 现场多轮模拟面试", "💡 岗位避坑与攻略", "📂 历史档案与成长看板"]
)

# ══════════════════════════════════════════════════
# 模块一：现场多轮模拟面试室 (注入流程引擎)
# ══════════════════════════════════════════════════
with tab_interview:
    col_left, col_right = st.columns([1, 1.3], gap="large")

    # ── 左侧：试题锁定区 ──
    with col_left:
        st.subheader("第一阶段：考题装载")
        preset_jobs = [
            "机器人控制系统开发实习生",
            "AI 应用开发实习生",
            "AI 产品运营实习生",
            "自定义其他岗位...",
        ]
        selected_job = st.selectbox("选择目标岗位：", preset_jobs)

        job_title = (
            st.text_input("输入自定义岗位名称：")
            if selected_job == "自定义其他岗位..."
            else selected_job
        )

        question_container = st.container()

        # 仅在阶段 1 允许重新出题
        if st.session_state.interview_stage == 1:
            if st.button(
                "🚀 极速装载专属考题", type="primary", use_container_width=True
            ):
                if not job_title.strip():
                    st.warning("请确认目标岗位！")
                else:
                    reset_interview_flow()
                    with st.spinner("DeepSeek 正在按大厂标准生成深度试题..."):
                        try:
                            client = get_client()
                            prompt = f"你是一个严苛的技术面试官。请针对【{job_title}】岗位，输出1道硬核专业技术题和1道真实业务场景落地题。排版清晰简洁。"
                            response = client.chat.completions.create(
                                model="deepseek-chat",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.7,
                                stream=True,
                            )
                            with question_container:
                                st.success(f"当前考核岗位：{job_title}")
                                st.markdown("### 📋 初始面试考题")
                                with st.container(border=True):
                                    st.session_state.questions = (
                                        st.write_stream(response)
                                    )
                            st.session_state.current_job = job_title
                        except Exception as e:
                            st.error(f"出题出错: {e}")

        # 常态锁定渲染
        if st.session_state.questions:
            with question_container:
                st.success(f"当前考核岗位：{st.session_state.current_job}")
                with st.expander("### 📋 初始面试考题 (流转中)", expanded=True):
                    st.write(st.session_state.questions)
                if st.session_state.interview_stage > 1:
                    st.info("🔒 考题已锁定，当前处于面试流程深挖阶段。")

    # ── 右侧：多轮答题流转与雷达评估看板 ──
    with col_right:
        st.subheader("第二阶段：多轮追问与深度量化")
        if not st.session_state.questions:
            st.info("👈 请先在左侧生成考题，系统将开启双轮压力面试流转引擎。")
        else:
            # ── 流程分支 A：第一轮初试作答 ──
            if st.session_state.interview_stage == 1:
                answer_mode = st.radio(
                    "选择作答交互方式：", list(MODE_MAP.keys()), horizontal=True
                )
                ans1_text = ""

                with st.container(border=True):
                    st.markdown("#### 🚀 第一轮作答 (针对初始考题)")
                    if answer_mode == "⌨️ 键盘打字输入":
                        ans1_text = st.text_area(
                            "输入作答思路：",
                            height=140,
                            placeholder="请尽可能详尽地阐述技术链路...",
                        )
                    else:
                        st.info("💡 提示：点击下方麦克风录入语音作答。")
                        if st.audio_input("录制初试回答"):
                            ans1_text = st.text_area(
                                "提炼口述要点 (系统降级捕获层)：",
                                placeholder="口述核心方案基于多模态流转与系统缓存...",
                                height=80,
                            )

                flow_container1 = st.container()

                if st.button("✨ 提交初试作答，迎接面试官深度追问", type="primary"):
                    if not ans1_text.strip():
                        st.warning("作答内容不能为空！")
                    else:
                        with st.spinner("面试官正在快速审查，并针对方案漏洞生成刁钻追问..."):
                            try:
                                client = get_client()
                                prompt_r1 = f"""你正在面试【{st.session_state.current_job}】岗位。
                                初始考题：{st.session_state.questions}
                                候选人作答：{ans1_text}
                                任务：请以资深技术面试官的口吻，简短点评 1-2 句核心短板，然后**立即针对作答中的技术盲点、极端高并发或边缘硬件异常场景，提出 1 个具有极强压迫感的尖锐追问题目**。"""

                                resp_stream = client.chat.completions.create(
                                    model="deepseek-chat",
                                    messages=[
                                        {"role": "user", "content": prompt_r1}
                                    ],
                                    temperature=0.6,
                                    stream=True,
                                )

                                with flow_container1:
                                    st.markdown("### ⚡ 面试官深度追问 (压力测试)")
                                    with st.container(border=True):
                                        full_r1_feedback = st.write_stream(
                                            resp_stream
                                        )

                                # 状态机流转：记录第一轮答案与反馈，跳转至第二轮
                                st.session_state.round1_answer = ans1_text
                                st.session_state.round1_feedback = (
                                    full_r1_feedback
                                )
                                st.session_state.interview_stage = 2
                                st.rerun()
                            except Exception as e:
                                st.error(f"追问生成失败: {e}")

            # ── 流程分支 B：第二轮深度追问作答 ──
            elif st.session_state.interview_stage == 2:
                # 静态回显上一轮追问问题
                st.markdown("#### ⚡ 面试官深度追问 (压力测试)")
                with st.container(border=True):
                    st.info(st.session_state.round1_feedback)

                answer_mode = st.radio(
                    "选择作答交互方式：", list(MODE_MAP.keys()), horizontal=True
                )
                ans2_text = ""

                with st.container(border=True):
                    st.markdown("#### 🛡️ 第二轮终极抗压作答 (针对追问)")
                    if answer_mode == "⌨️ 键盘打字输入":
                        ans2_text = st.text_area(
                            "输入终极抗压防守思路：",
                            height=140,
                            placeholder="展现你面对极端场景的架构权衡能力...",
                        )
                    else:
                        st.info("💡 提示：点击下方进行追问语音作答。")
                        if st.audio_input("录制追问回答"):
                            ans2_text = st.text_area(
                                "提炼追问防守要点：",
                                placeholder="针对高并发瓶颈，引入读写分离与本地队列削峰...",
                                height=80,
                            )

                flow_container2 = st.container()

                if st.button(
                    "🏆 提交终极防守，生成多维度量化看板与存档", type="primary"
                ):
                    if not ans2_text.strip():
                        st.warning("防守作答不能为空！")
                    else:
                        with st.spinner("AI 大脑正在进行全链路评估，并计算5大核心维度量化分值..."):
                            try:
                                client = get_client()
                                # 绝密提示词设计：强制输出格式化 JSON 用于绘图
                                prompt_r2 = f"""你正在面试【{st.session_state.current_job}】岗位。
                                初始试题：{st.session_state.questions}
                                初试回答：{st.session_state.round1_answer}
                                面试官追问：{st.session_state.round1_feedback}
                                候选人追问回答：{ans2_text}
                                
                                请输出最终全方位深度评估报告。包含：1.综合定级点评 2.亮点挖掘 3.致命短板 4.标准答案架构指导。
                                🔥 重要指令：在报告内容的最后，请严格按照以下 JSON 格式输出 5 个维度的分值（务必使用且仅使用 ```json 和 ``` 包裹）：
                                ```json
                                {{
                                  "技术深度": 85,
                                  "业务落地": 80,
                                  "逻辑思维": 88,
                                  "表达提炼": 82,
                                  "抗压与应变": 90
                                }}
                                ```"""

                                resp_stream = client.chat.completions.create(
                                    model="deepseek-chat",
                                    messages=[
                                        {"role": "user", "content": prompt_r2}
                                    ],
                                    temperature=0.4,  # 打分极度严谨
                                    stream=True,
                                )

                                with flow_container2:
                                    st.markdown("### 📊 最终评估与能力矩阵")
                                    with st.container(border=True):
                                        full_final_feedback = st.write_stream(
                                            resp_stream
                                        )

                                # 正则极速提取 JSON 评分字典
                                scores_dict = {
                                    "技术深度": 80,
                                    "业务落地": 80,
                                    "逻辑思维": 80,
                                    "表达提炼": 80,
                                    "抗压与应变": 80,
                                }  # 健壮性保底分值
                                json_match = re.search(
                                    r"```json\s*(.*?)\s*```",
                                    full_final_feedback,
                                    re.DOTALL,
                                )
                                if json_match:
                                    try:
                                        parsed_scores = json.loads(
                                            json_match.group(1)
                                        )
                                        if isinstance(parsed_scores, dict):
                                            scores_dict = parsed_scores
                                    except Exception:
                                        pass

                                # 清洗掉报告最后输出给前端查看的裸 JSON 字符串，保持 UI 纯净
                                clean_feedback = re.sub(
                                    r"```json\s*.*?\s*```",
                                    "",
                                    full_final_feedback,
                                    flags=re.DOTALL,
                                )

                                # 状态机同步与持久化归档
                                st.session_state.round2_answer = ans2_text
                                st.session_state.final_feedback = (
                                    clean_feedback.strip()
                                )
                                st.session_state.radar_scores = scores_dict
                                st.session_state.interview_stage = 3

                                record_id = datetime.datetime.now().strftime(
                                    "%Y%m%d%H%M%S"
                                )
                                new_record = {
                                    "id": record_id,
                                    "time": datetime.datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                     "job": st.session_state.current_job,
                                    "questions": st.session_state.questions,
                                    "r1_answer": st.session_state.round1_answer,
                                    "followup": st.session_state.round1_feedback,
                                    "r2_answer": ans2_text,
                                    "feedback": st.session_state.final_feedback,
                                    "scores": scores_dict,
                                    "mode": MODE_MAP[answer_mode],
                                }
                                st.session_state.history.insert(0, new_record)
                                save_history(st.session_state.history)
                                st.toast(
                                    "🎉 全真抗压闭环完成！能力雷达图已同步载入本地数据库。"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"终极评估失败: {e}")

            # ── 流程分支 C：第三阶段 终极看板与雷达图展示 ──
            elif st.session_state.interview_stage == 3:
                st.success("🎯 当前轮次全模态模拟面试闭环已彻底归档！")

                # 极简大气的左右对比布局展示报告与雷达图
                fc1, fc2 = st.columns([1.4, 1])
                with fc1:
                    st.markdown("#### 📊 最终综合定级评估报告")
                    with st.container(border=True):
                        st.markdown(st.session_state.final_feedback)
                with fc2:
                    st.markdown("#### 🕸️ 候选人核心能力雷达图")
                    with st.container(border=True):
                        fig = draw_radar_chart(st.session_state.radar_scores)
                        st.plotly_chart(
                            fig, use_container_width=True, config={"displayModeBar": False}
                        )

                st.divider()
                if st.button("🔄 开启下一轮全新模拟面试", type="secondary"):
                    reset_interview_flow()
                    st.rerun()

# ══════════════════════════════════════════════════
# 模块二：岗位避坑与攻略分析
# ══════════════════════════════════════════════════
with tab_strategy:
    st.subheader("💡 机器人与 AI 赛道面试核心通关指南")
    st.markdown("利用了多轮状态追踪与正则解析重构底层逻辑，高分答辩核心剖析：")
    col_s1, col_s2 = st.columns(2, gap="medium")
    with col_s1:
        with st.container(border=True):
            st.markdown("#### 🚨 产品护城河底层追问")
            st.markdown(
                """
            * **为什么不直接用 DeepSeek？** 阐述系统利用了 **有限状态机 (FSM)** 强行隔离初试与压力追问环节，杜绝了通用大模型一次性倾倒答案的无效工作流。
            * **结构化数据抽取：** 主动展示如何通过底层 Prompt 精准吐出标准化 JSON 字典，打通非结构化语言与数据看板的转换链路。
            """
            )
    with col_s2:
        with st.container(border=True):
            st.markdown("#### 🏆 STAR 高分绝杀公式")
            st.markdown(
                """
            1. **情境 (Situation)：** 突破传统大模型对话界面的单轮无状态壁垒。
            2. **任务 (Task)：** 构建具备深度压力追问与可视化量化能力的垂直评估平台。
            3. **行动 (Action)：** 接入双重 FSM 路由，封装流式响应，利用正则拦截并驱动 Plotly 极速绘制能力雷达。
            4. **结果 (Result)：** 成功交付完整实现前后端解耦、闭环追踪且视觉极具冲击力的工业级 SaaS。
            """
            )

# ══════════════════════════════════════════════════
# 模块三：历史档案与成长看板 (支持单条追踪与雷达图持久化)
# ══════════════════════════════════════════════════
with tab_history:
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.subheader("📂 成长记录档案室与能力矩阵追踪")
    with col_h2:
        if st.session_state.history:
            if st.button(
                "🗑️ 清空所有档案", type="secondary", use_container_width=True
            ):
                confirm_clear_dialog()

    st.caption(
        "实时映射本地 interview_records.json 文件，完美保留历史考核轮次与多维度技能图谱。"
    )

    if not st.session_state.history:
        st.info("📭 当前档案室空空如也。快去【现场模拟面试】完成初测并点亮技能图谱吧！")
    else:
        for i, record in enumerate(st.session_state.history):
            record_id = record.get("id", str(i))
            job = record.get("job", "未知岗位")
            time_str = record.get("time", "")
            mode = record.get("mode", "text")
            scores = record.get(
                "scores",
                {
                    "技术深度": 80,
                    "业务落地": 80,
                    "逻辑思维": 80,
                    "表达提炼": 80,
                    "抗压与应变": 80,
                },
            )

            with st.expander(
                f"🏷️ 【{job}】 📅 {time_str} | 载体: {mode.upper()}"
            ):
                # 档案室内部构建左右布局展现详细记录与雷达图
                hc1, hc2 = st.columns([1.4, 1])
                with hc1:
                    st.markdown("**🎯 初始考核题目：**")
                    st.info(record.get("questions", ""))
                    st.markdown("**✍️ 第一轮初试回答：**")
                    st.write(record.get("r1_answer", "未记录"))
                    st.markdown("**⚡ 面试官深度追问：**")
                    st.warning(record.get("followup", "无追问记录"))
                    st.markdown("**🛡️ 终极防守回答：**")
                    st.write(record.get("r2_answer", "未记录"))
                    st.markdown("**📊 最终深度定级报告：**")
                    with st.container(border=True):
                        st.markdown(record.get("feedback", ""))
                with hc2:
                    st.markdown("**🕸️ 考核维度分值矩阵：**")
                    with st.container(border=True):
                        archived_fig = draw_radar_chart(scores)
                        st.plotly_chart(
                            archived_fig,
                            use_container_width=True,
                            config={"displayModeBar": False},
                            key=f"radar_{record_id}",
                        )

                if st.button(
                    "删除此条记录", key=f"del_{record_id}", type="secondary"
                ):
                    st.session_state.history = [
                        r
                        for r in st.session_state.history
                        if r.get("id") != record_id
                    ]
                    save_history(st.session_state.history)
                    st.rerun()