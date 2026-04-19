import asyncio
import os
import pandas as pd
import plotly.express as px
import streamlit as st

from src.api import GitHubAPI
from src.analyzer import RelationshipAnalyzer
from src.config import GITHUB_TOKEN
from src.storage import StorageEngine

# 配置页面
st.set_page_config(
    page_title="GitHub Relation Analyzer",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定义 CSS (保留干净的卡片网格样式，移除极端的暗黑风格)
st.markdown("""
<style>
/* 用户卡片网格系统 - 适配日间/夜间模式 */
.user-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
    margin-bottom: 2rem;
}
.user-card {
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 8px;
    padding: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: all 0.2s ease;
    text-decoration: none !important;
    color: inherit !important;
    background-color: rgba(128, 128, 128, 0.05);
}
.user-card:hover {
    border-color: #0366d6;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.user-card img {
    width: 50px;
    height: 50px;
    border-radius: 50%; /* 圆形头像更亲切 */
    border: 1px solid rgba(128, 128, 128, 0.2);
}
.user-info {
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.user-name {
    font-weight: 600;
    font-size: 1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.user-link {
    font-size: 0.8rem;
    opacity: 0.7;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
""", unsafe_allow_html=True)

st.title("🐙 GitHub 用户关系分析")
st.markdown("直观地分析您的 GitHub 关注者 (Followers) 与正在关注 (Following) 之间的关系。")

# 侧边栏配置
st.sidebar.header("⚙️ 配置与输入")
username = st.sidebar.text_input("GitHub 用户名", value="RainyNight9", placeholder="例如: torvalds")
token_input = st.sidebar.text_input(
    "AUTH TOKEN (OPTIONAL)", 
    value=GITHUB_TOKEN, 
    type="password", 
    help="不填则使用默认限流 (60次/小时)。填写可提升至 5000次/小时。建议填写个人访问令牌 (PAT)。"
)
force_refresh = st.sidebar.checkbox(
    "FORCE REFRESH / 强制更新", 
    value=False, 
    help="勾选后将忽略本地缓存，从 GitHub 重新拉取最新数据。"
)

# --- 状态管理 ---
if "analyzed_user" not in st.session_state:
    st.session_state.analyzed_user = None
if "do_full_refresh" not in st.session_state:
    st.session_state.do_full_refresh = False

def handle_analyze_click():
    st.session_state.analyzed_user = username
    st.session_state.do_full_refresh = force_refresh

def handle_update_single(relation_type):
    api = GitHubAPI(token=token_input if token_input else None)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    with st.spinner(f"正在单独更新 {relation_type}..."):
        try:
            users = loop.run_until_complete(api.fetch_users(st.session_state.analyzed_user, relation_type))
            loop.close()
            
            storage = StorageEngine()
            cursor = storage.conn.cursor()
            cursor.execute("DELETE FROM relations WHERE owner_login = ? AND relation_type = ?", 
                           (st.session_state.analyzed_user, relation_type))
            storage.conn.commit()
            
            storage.save_users(st.session_state.analyzed_user, users, relation_type)
            st.toast(f"✅ {relation_type.capitalize()} 更新完成！", icon="✅")
        except Exception as e:
            st.error(f"更新 {relation_type} 时出错: {str(e)}")

# 封装异步拉取函数供 Streamlit (同步框架) 调用
def fetch_and_analyze(user: str, token: str, refresh: bool):
    storage = StorageEngine()
    
    if not refresh:
        # 尝试从本地数据库加载
        cached_followers = storage.get_relations(user, "followers")
        cached_following = storage.get_relations(user, "following")
        if cached_followers or cached_following:
            st.toast("⚡ 已加载本地缓存数据，如需最新数据请勾选 [FORCE REFRESH]", icon="⚡")
            analyzer = RelationshipAnalyzer(user, storage)
            return cached_followers, cached_following, analyzer

    api = GitHubAPI(token=token if token else None)
    
    # 建立事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 拉取前清空旧关系数据 (可选，避免取消关注后仍在数据库中)
    # 这里我们采用覆盖策略，理想情况下应该全量替换
    followers, following = loop.run_until_complete(api.fetch_all(user))
    loop.close()
    
    # 存储前清除该用户的旧关系以确保数据最新
    cursor = storage.conn.cursor()
    cursor.execute("DELETE FROM relations WHERE owner_login = ?", (user,))
    storage.conn.commit()
    
    # 存储并分析
    storage.save_users(user, followers, "followers")
    storage.save_users(user, following, "following")
    
    analyzer = RelationshipAnalyzer(user, storage)
    return followers, following, analyzer

st.sidebar.button("🚀 开始分析", on_click=handle_analyze_click, use_container_width=True)

if st.session_state.analyzed_user:
    with st.spinner(f"正在加载 {st.session_state.analyzed_user} 的数据，请稍候..."):
        try:
            # 读取并分析数据，用完 refresh 标志后重置
            followers, following, analyzer = fetch_and_analyze(
                st.session_state.analyzed_user, 
                token_input, 
                st.session_state.do_full_refresh
            )
            st.session_state.do_full_refresh = False
            
            mutual = analyzer.get_mutual()
            only_following = analyzer.get_one_way_following()
            only_followers = analyzer.get_one_way_followers()
            
            # --- 1. 顶部指标看板 (Metrics) ---
            st.markdown("### 📊 核心指标")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Followers (粉丝)", len(followers))
                st.button("↻ 单独更新粉丝", key="btn_update_followers", 
                          on_click=handle_update_single, args=("followers",), 
                          use_container_width=True)
                          
            with col2:
                st.metric("Following (关注了)", len(following))
                st.button("↻ 单独更新关注", key="btn_update_following", 
                          on_click=handle_update_single, args=("following",), 
                          use_container_width=True)
                          
            with col3:
                st.metric("Mutual (互关)", len(mutual))
                
            with col4:
                st.metric("单向关注 (未回关我)", len(only_following))
                
            # --- 2. 可视化图表 (Charts) ---
            st.markdown("### 🥧 关系分布图")
            
            # 构造绘图数据
            labels = ['互关 (Mutual)', '单向关注 (对方没回关)', '单向粉丝 (我没回关)']
            values = [len(mutual), len(only_following), len(only_followers)]
            
            if sum(values) == 0:
                st.info("当前用户暂无任何关系数据可以展示。")
            else:
                df_chart = pd.DataFrame({'关系类型': labels, '数量': values})
                fig = px.pie(
                    df_chart, 
                    values='数量', 
                    names='关系类型', 
                    hole=0.4, 
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_traces(textposition='inside', textinfo='percent+label+value')
                st.plotly_chart(fig, use_container_width=True)
            
            # --- 3. 详细数据表格 (Data Tables) ---
            st.markdown("### 📋 详细人员名单")
            
            # 定义渲染高级卡片网格的函数
            def render_table(data_list, empty_msg="暂无数据"):
                if not data_list:
                    st.info(empty_msg)
                    return
                
                html_content = '<div class="user-grid">'
                for user in data_list:
                    login = user.get('login', 'Unknown')
                    avatar = user.get('avatar_url', '')
                    url = user.get('html_url', '#')
                    # 将HTML写在同一行，避免被 Markdown 解析为代码块 (Markdown中行首4个空格会被解析为代码块)
                    html_content += f'<a href="{url}" target="_blank" class="user-card"><img src="{avatar}" alt="{login}"><div class="user-info"><span class="user-name">{login}</span><span class="user-link">github.com/{login}</span></div></a>'
                html_content += '</div>'
                st.markdown(html_content, unsafe_allow_html=True)
            
            tab1, tab2, tab3 = st.tabs([
                f"💔 单向关注 (对方没回关) [{len(only_following)}]", 
                f"� 单向粉丝 (我没回关) [{len(only_followers)}]",
                f"🤝 互关 (Mutual) [{len(mutual)}]"
            ])
            
            with tab1:
                render_table(only_following, "太棒了！你关注的人都回关了你。")
            with tab2:
                render_table(only_followers, "没有单向粉丝。")
            with tab3:
                render_table(mutual, "没有互关的人员。")

        except Exception as e:
            st.error(f"❌ 拉取或分析时发生错误: {str(e)}")
