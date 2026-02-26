import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
import ollama
import re
import streamlit.components.v1 as components

# --- 1. 页面配置与 CSS/JS 注入 ---
st.set_page_config(page_title="德语语境工作台", page_icon="🇩🇪", layout="wide")

# CSS: 美化卡片和布局
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 左侧语境卡片的样式 */
    .context-card {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .context-card strong {
        color: #ff4b4b;
        background-color: rgba(255, 75, 75, 0.1);
        padding: 0 4px;
        border-radius: 4px;
    }
    .context-source {
        font-size: 0.85em;
        color: #666;
        margin-top: 8px;
        display: flex;
        justify-content: space-between;
    }
    
    /* 暗黑模式适配 */
    @media (prefers-color-scheme: dark) {
        .context-card {
            background-color: #262730;
            border-left-color: #ff4b4b;
            color: #ffffff;
        }
        .context-source {
            color: #aaa;
        }
    }
</style>
""", unsafe_allow_html=True)

# JS: 实现按 "/" 键聚焦输入框
# 注意：这需要查找 Streamlit特定的 textarea DOM 元素
components.html("""
<script>
document.addEventListener('keydown', function(e) {
    // 如果按下的是 "/" 且当前没有在输入框内
    if (e.key === '/' && document.activeElement.tagName !== 'TEXTAREA' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        // 查找 Streamlit 的聊天输入框
        const input = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (input) {
            input.focus();
            input.select();
        }
    }
});
</script>
""", height=0, width=0)

# --- 2. 数据库连接 ---
@st.cache_resource
def get_collection():
    client = chromadb.PersistentClient(path="./german_subs_db")
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_collection(name="german_learning", embedding_function=ef)

try:
    collection = get_collection()
except Exception as e:
    st.error(f"❌ 数据库连接失败: {e}")
    st.stop()

# --- 3. 侧边栏设置 ---
with st.sidebar:
    st.header("⚙️ 控制台")
    model_name = st.selectbox(
        "AI 模型", 
        ["qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b"],
        index=0,
        help="推荐 1.5b，速度最快。"
    )
    n_results = st.slider("检索例句数", 1, 8, 4)
    st.info("⌨️ **快捷键提示**：\n\n按下 `/` 键可直接聚焦输入框。")
    
    if st.button("🗑️ 清空历史"):
        st.session_state.messages = []
        st.rerun()

# --- 4. 历史记录管理 ---
# 我们需要一种特殊的结构来存储“左侧语境”和“右侧AI回复”
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. 渲染历史消息 ---
# 这是一个极其重要的循环，保证历史记录也能保持“左右分栏”的样式
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(f"**查询：** {msg['content']}")
    
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            # 在历史记录里也重建左右分栏
            lc, rc = st.columns([1, 1])
            
            with lc:
                st.caption("📺 视频语境溯源")
                # 渲染之前存下来的语境 HTML
                for html_card in msg["context_htmls"]:
                    st.markdown(html_card, unsafe_allow_html=True)
            
            with rc:
                st.caption("🤖 AI 语法解析")
                st.markdown(msg["ai_text"])

# --- 6. 主交互逻辑 ---
if query := st.chat_input("输入单词，按回车搜索 (按 '/' 聚焦)..."):
    
    # 6.1 用户输入上屏
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(f"**查询：** {query}")

    # 6.2 处理响应
    with st.chat_message("assistant"):
        # 建立左右分栏
        col_left, col_right = st.columns([1, 1], gap="medium")
        
        context_data_for_ai = ""
        saved_context_htmls = [] # 用于存入 session_state

        # --- 左侧：检索与显示 ---
        with col_left:
            st.caption("📺 视频语境溯源 (Context)")
            
            # 数据库查询
            results = collection.query(query_texts=[query], n_results=n_results)
            
            if not results['documents'][0]:
                st.warning("未找到相关视频例句。")
            else:
                # 遍历结果并生成 HTML 卡片
                for i, (text, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
                    # 高亮关键词
                    hl_text = re.sub(f"({query})", r"<strong>\1</strong>", text, flags=re.IGNORECASE)
                    
                    # 生成 HTML 卡片
                    card_html = f"""
                    <div class="context-card">
                        <div style="font-size: 1.1em; line-height: 1.5;">"{hl_text}"</div>
                        <div class="context-source">
                            <span>🎬 {meta['series']} E{meta['episode']}</span>
                            <span>⏰ {meta['start']}</span>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    # 保存数据
                    saved_context_htmls.append(card_html)
                    context_data_for_ai += f"例句 {i+1}: {text}\n"

        # --- 右侧：AI 解析 ---
        with col_right:
            st.caption("🤖 AI 语法解析 (Analysis)")
            
            # 构造 Prompt
            prompt = f"""
            你是一位德语私教。用户查询单词："{query}"。
            
            请根据左侧提供的视频例句（如下）进行教学：
            {context_data_for_ai if context_data_for_ai else "（未找到例句，请直接解释单词）"}
            
            任务：
            1. **核心释义**：结合语境解释单词含义。
            2. **语法深挖**：
               - 动词：给出原形、时态、人称变位。
               - 名词：词性、格（Nominativ/Dativ等）。
               - 句式：如果有特殊句型（如倒装、从句）请指出。
            3. **翻译**：翻译最具代表性的一个例句。
            
            请用 Markdown 格式输出，排版清晰。
            """

            # 流式输出
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                stream = ollama.chat(
                    model=model_name,
                    messages=[{'role': 'user', 'content': prompt}],
                    stream=True
                )
                
                for chunk in stream:
                    content = chunk['message']['content']
                    full_response += content
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                # --- 保存完整状态到历史 ---
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "query_processed", # 占位符，实际显示靠下面两个字段
                    "context_htmls": saved_context_htmls, # 保存左侧卡片数据
                    "ai_text": full_response              # 保存右侧AI回复
                })

            except Exception as e:
                st.error(f"AI 生成出错: {e}")
