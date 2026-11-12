# 🌟 真知 Agent (ZhenZhi Agent)

面向大学生的全场景 AI 智能体工作台，聚焦“科研学习 + 日常创作”。

## 核心功能

- 🔬 **科研助手**：文献导读、学术润色与翻译、数据图表生成建议
- 🎨 **创作伙伴**：PS 设计灵感、知识前沿速递、美食生活推荐
- 📅 **我的日程**：课程表导入 + To-Do 管理
- 👤 **用户中心与认证**：登录注册、每日签到领额度、学生认证（人工审核流程）

## 产品机制

- 专属智能体即点即用，降低 Prompt 使用门槛
- 签到送额度，提升活跃留存
- 学生认证审核通过后解锁 3-4 年长期学术额度（示例实现提供审核通过/驳回流程）

## 技术架构

- **前端**：Streamlit（左侧导航 + 右侧多 Tab 工作区）
- **存储**：SQLite（用户状态、余额、认证、课程与待办）
- **AI 引擎**：兼容 OpenAI Chat Completions 格式，支持流式输出

## 运行方式

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## 测试

```bash
python -m unittest discover -s tests
```
