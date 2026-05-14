# AI 模拟面试官

一个基于大模型的智能面试模拟平台，支持多轮追问和量化评估。

## 功能

- 🎯 根据目标岗位自动生成面试题
- ⚡ 两轮面试：初试作答 → 深度追问 → 综合评估
- 📊 五大维度能力雷达图（技术深度、业务落地、逻辑思维、表达提炼、抗压应变）
- 📂 历史面试记录归档与回溯

## 技术栈

- **前端界面**：Streamlit（纯 Python Web 框架）
- **大模型**：DeepSeek API（出题 + 追问 + 评估）
- **可视化**：Plotly 雷达图
- **状态管理**：有限状态机（FSM）控制多轮面试流程

## 在线体验

👉 [点击体验](https://ai-interviewer-t8sf5rdkxuis9k5m4fbkmc.streamlit.app/)

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

需在 `.streamlit/secrets.toml` 中配置 `DEEPSEEK_API_KEY`。
