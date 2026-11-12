from __future__ import annotations

import json
from typing import Generator

import requests
import streamlit as st

from zhenzhi_core import (
    DB_PATH,
    add_course,
    add_todo,
    authenticate,
    checkin,
    consume_quota,
    create_user,
    get_user_by_id,
    init_db,
    list_courses,
    list_todos,
    review_student_verification,
    submit_student_verification,
    toggle_todo,
)


def stream_openai_compatible(
    api_base: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> Generator[str, None, None]:
    url = api_base.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"******",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
    }
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            body = line[5:].strip()
            if body == "[DONE]":
                break
            data = json.loads(body)
            delta = data.get("choices", [{}])[0].get("delta", {}).get("content")
            if delta:
                yield delta


def use_agent(
    title: str,
    placeholder: str,
    system_prompt: str,
    user_id: int,
) -> None:
    st.subheader(title)
    prompt = st.text_area("输入需求", placeholder=placeholder, key=title)
    if st.button("开始", key=f"run-{title}"):
        if not prompt.strip():
            st.warning("请输入需求后再开始。")
            return
        if not consume_quota(user_id):
            st.error("额度不足，请签到或完成学生认证。")
            return

        api_base = st.session_state.get("api_base", "")
        api_key = st.session_state.get("api_key", "")
        model = st.session_state.get("model", "")
        if not api_base or not api_key or not model:
            st.error("请先在用户中心配置 API Base、API Key 与模型名称。")
            return
        try:
            st.write_stream(stream_openai_compatible(api_base, api_key, model, system_prompt, prompt))
        except Exception as exc:  # noqa: BLE001
            st.error(f"调用失败：{exc}")


def auth_panel() -> None:
    st.title("🌟 真知 Agent")
    st.caption("专为大学生打造的全场景 AI 智能体工作台")
    mode = st.radio("请选择", ["登录", "注册"], horizontal=True)
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    if mode == "注册":
        if st.button("创建账号"):
            if not username.strip() or not password:
                st.warning("用户名和密码不能为空。")
                return
            ok = create_user(username, password)
            st.success("注册成功，请登录。" if ok else "用户名已存在。")
        return

    if st.button("登录"):
        user = authenticate(username, password)
        if user:
            st.session_state["user_id"] = user.id
            st.rerun()
        st.error("用户名或密码错误。")


def page_research(user_id: int) -> None:
    tabs = st.tabs(["文献导读", "学术润色与翻译", "数据图表自动生成"])
    with tabs[0]:
        use_agent("文献导读", "贴入摘要或论文段落，获取结构化导读。", "你是高校科研助手，请输出研究背景、方法、结论与可复现实验建议。", user_id)
    with tabs[1]:
        use_agent("学术润色与翻译", "输入要润色或翻译的学术文本。", "你是学术写作助手，保持术语准确，输出润色版与中英对照翻译。", user_id)
    with tabs[2]:
        use_agent("数据图表自动生成", "描述数据含义，或粘贴 CSV 片段。", "你是数据分析助手，输出可视化建议、图表说明与关键结论。", user_id)


def page_creation(user_id: int) -> None:
    tabs = st.tabs(["PS 设计灵感生成", "知识前沿速递", "美食生活推荐"])
    with tabs[0]:
        use_agent("PS 设计灵感生成", "输入主题和用途，例如海报、封面、社团招新。", "你是视觉创作助手，请输出配色、排版、文案和素材建议。", user_id)
    with tabs[1]:
        use_agent("知识前沿速递", "输入学科方向和关注关键词。", "你是前沿资讯助手，请输出近期开源趋势和学习路径建议。", user_id)
    with tabs[2]:
        use_agent("美食生活推荐", "输入城市、预算和口味偏好。", "你是校园生活助手，请输出性价比推荐与避坑提示。", user_id)


def page_schedule(user_id: int) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("课程表导入")
        with st.form("course-form"):
            course_name = st.text_input("课程名")
            slot = st.text_input("时间段（如 周三 10:00-12:00）")
            location = st.text_input("地点")
            if st.form_submit_button("添加课程") and course_name and slot:
                add_course(user_id, course_name, slot, location)
                st.success("课程已添加。")

    with col2:
        st.subheader("待办事项 To-Do")
        todo = st.text_input("新增待办")
        if st.button("添加待办") and todo.strip():
            add_todo(user_id, todo)

    courses = list_courses(user_id)
    if courses:
        st.markdown("#### 课程表")
        st.table([dict(x) for x in courses])

    todos = list_todos(user_id)
    if todos:
        st.markdown("#### 待办列表")
        for item in todos:
            done = st.checkbox(item["content"], value=bool(item["done"]), key=f"todo-{item['id']}")
            if done != bool(item["done"]):
                toggle_todo(item["id"], done)
                st.rerun()


def page_user_center(user_id: int) -> None:
    user = get_user_by_id(user_id)
    if not user:
        st.error("用户不存在，请重新登录。")
        return
    st.subheader("账户信息")
    st.write(f"用户名：{user.username}")
    st.write(f"剩余额度：{user.quota}")
    st.write(f"学生认证：{'已通过' if user.student_verified else '未通过'}")
    if user.free_until:
        st.write(f"免费学术额度有效期至：{user.free_until}")

    st.markdown("### 每日签到")
    if st.button("签到领取额度"):
        ok, msg = checkin(user_id)
        (st.success if ok else st.info)(msg)

    st.markdown("### 学生认证")
    with st.form("verify-form"):
        student_id = st.text_input("学号")
        proof_note = st.text_area("证件/材料说明（不上传图片，仅记录说明）")
        if st.form_submit_button("提交审核") and student_id.strip():
            submit_student_verification(user_id, student_id, proof_note)
            st.success("已提交，等待后台人工审核。")

    with st.expander("演示：后台审核操作（开发模式）"):
        cols = st.columns(2)
        if cols[0].button("审核通过"):
            review_student_verification(user_id, approved=True)
            st.success("已审核通过并发放长期额度。")
        if cols[1].button("审核驳回"):
            review_student_verification(user_id, approved=False)
            st.warning("已标记为驳回。")

    st.markdown("### AI 引擎配置（OpenAI 兼容）")
    st.session_state["api_base"] = st.text_input(
        "API Base",
        value=st.session_state.get("api_base", "https://api.deepseek.com/v1"),
    )
    st.session_state["api_key"] = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.get("api_key", ""),
    )
    st.session_state["model"] = st.text_input("模型名", value=st.session_state.get("model", "deepseek-chat"))


def main() -> None:
    st.set_page_config(page_title="真知 Agent", layout="wide")
    init_db(DB_PATH)

    if "user_id" not in st.session_state:
        auth_panel()
        return

    st.sidebar.title("真知 Agent")
    page = st.sidebar.radio("导航", ["🔬 科研助手", "🎨 创作伙伴", "📅 我的日程", "👤 用户中心"])
    if st.sidebar.button("退出登录"):
        st.session_state.pop("user_id", None)
        st.rerun()

    user_id = st.session_state["user_id"]
    if page == "🔬 科研助手":
        page_research(user_id)
    elif page == "🎨 创作伙伴":
        page_creation(user_id)
    elif page == "📅 我的日程":
        page_schedule(user_id)
    else:
        page_user_center(user_id)


if __name__ == "__main__":
    main()
