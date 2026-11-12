"""真知 Agent Streamlit application entrypoint."""

from __future__ import annotations

import streamlit as st

from auth import (
    current_user,
    initialize_auth_state,
    login_user,
    logout_user,
    register_user,
)
from database import check_in_user, submit_verification


st.set_page_config(
    page_title="真知 Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_auth_state()


def render_auth_page() -> None:
    """Render the login and registration entry point."""
    st.title("真知 Agent")
    st.caption("面向大学生的极简 AI 学习与创作助手")

    login_tab, register_tab = st.tabs(["登录", "注册"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", type="primary")
        if submitted:
            success, message = login_user(username, password)
            (st.success if success else st.error)(message)
            if success:
                st.rerun()

    with register_tab:
        with st.form("register_form"):
            username = st.text_input("用户名", key="register_username")
            password = st.text_input("密码", type="password", key="register_password")
            nickname = st.text_input("昵称")
            grade = st.text_input("年级", placeholder="例如：大二")
            major = st.text_input("专业", placeholder="例如：计算机科学与技术")
            submitted = st.form_submit_button("注册", type="primary")
        if submitted:
            success, message = register_user(
                username,
                password,
                nickname,
                grade,
                major,
            )
            (st.success if success else st.error)(message)


def render_sidebar() -> str:
    """Render the fixed navigation sidebar and return the selected route."""
    user = current_user()
    with st.sidebar:
        st.markdown("# 🧠 真知 Agent")
        st.caption(f"你好，{user['nickname']}")
        st.divider()

        route = st.radio(
            "导航",
            [
                "🏠 首页",
                "🔬 科研助手",
                "🎨 创作伙伴",
                "📅 我的日程",
                "👤 My Account",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        st.metric("当前额度", f"{user['balance']} 点")
        if st.button("退出登录", use_container_width=True):
            logout_user()
            st.rerun()
    return route


def render_home() -> None:
    st.title("欢迎回来")
    st.write("从今天的学习目标开始，让真知 Agent 帮你快速进入状态。")
    col1, col2, col3 = st.columns(3)
    col1.info("🔬 科研助手\n\n文献导读、润色翻译与数据图表。")
    col2.info("🎨 创作伙伴\n\n灵感生成、知识前沿与美食推荐。")
    col3.info("📅 我的日程\n\n集中查看课程与待办事项。")


def render_research() -> None:
    st.title("🔬 科研助手")
    tabs = st.tabs(["文献导读", "润色翻译", "数据图表"])
    with tabs[0]:
        st.subheader("文献导读")
        st.text_area("粘贴论文摘要或正文", height=180)
        st.button("生成导读", key="literature_summary")
    with tabs[1]:
        st.subheader("润色翻译")
        st.text_area("输入需要处理的内容", height=180)
        st.button("开始处理", key="polish_translate")
    with tabs[2]:
        st.subheader("数据图表")
        st.file_uploader("上传 CSV 或 Excel 文件", type=["csv", "xlsx"])


def render_creative() -> None:
    st.title("🎨 创作伙伴")
    tabs = st.tabs(["灵感生成", "知识前沿", "美食推荐"])
    for tab, title in zip(tabs, ["灵感生成", "知识前沿", "美食推荐"]):
        with tab:
            st.subheader(title)
            st.text_input("告诉我你想探索的主题", key=f"creative_{title}")
            st.button("开始探索", key=f"explore_{title}")


def render_schedule() -> None:
    st.title("📅 我的日程")
    st.caption("这里将展示课程表和待办事项。")
    st.dataframe(
        [
            {"时间": "09:00 - 10:40", "事项": "专业课程", "状态": "待开始"},
            {"时间": "14:00 - 15:00", "事项": "完成文献阅读", "状态": "待开始"},
            {"时间": "19:30 - 20:30", "事项": "整理学习笔记", "状态": "待开始"},
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_account() -> None:
    user = current_user()
    st.title("👤 My Account")
    profile, verification = st.tabs(["账户信息", "学生认证"])

    with profile:
        st.write(f"**用户名：** {user['username']}")
        st.write(f"**昵称：** {user['nickname']}")
        st.write(f"**年级：** {user['grade']}")
        st.write(f"**专业：** {user['major']}")
        st.write(f"**认证状态：** {user['verification_status']}")
        if st.button("每日签到（+10 额度）", type="primary"):
            checked_in, balance = check_in_user(user["id"])
            if checked_in:
                st.success(f"签到成功，当前额度：{balance}")
            else:
                st.info(f"今天已签到，当前额度：{balance}")
            st.rerun()

    with verification:
        st.write(f"当前状态：**{user['verification_status']}**")
        image = st.file_uploader(
            "上传学生证或校园卡图片",
            type=["png", "jpg", "jpeg"],
            key="verification_image",
        )
        if st.button("提交认证", type="primary"):
            if image is None:
                st.warning("请先上传认证图片。")
            else:
                # 第一阶段只持久化上传文件名，后续可接入对象存储。
                if submit_verification(user["id"], image.name):
                    st.success("材料已提交，当前状态为审核中。")
                    st.rerun()


def main() -> None:
    if not st.session_state.authenticated:
        render_auth_page()
        return

    route = render_sidebar()
    if route == "🏠 首页":
        render_home()
    elif route == "🔬 科研助手":
        render_research()
    elif route == "🎨 创作伙伴":
        render_creative()
    elif route == "📅 我的日程":
        render_schedule()
    elif route == "👤 My Account":
        render_account()


if __name__ == "__main__":
    main()
