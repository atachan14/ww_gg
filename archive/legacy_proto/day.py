import streamlit as st

def show_session_page():
    st.title("セッションページ")
    
    if "roles" not in st.session_state:
        st.write("役職が選択されていません。トップページに戻ってください。")
        if st.button("トップに戻る"):
            st.session_state["page"] = "top"
            st.rerun()
        return

    selected_roles = st.session_state["roles"]
    st.subheader("選択された役職")
    
    for role, count in selected_roles.items():
        st.write(f"{role}: {count}人")
    
    # とりあえずのテーブル表示
    st.table({role: count for role, count in selected_roles.items()})
    
    # トップに戻るボタン
    if st.button("トップに戻る"):
        st.session_state["page"] = "top"
        st.rerun()
