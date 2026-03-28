import streamlit as st
from logic.roles import Villager, Seer, Medium, Hunter, Wolf, Madman

ALL_ROLES = [Villager, Seer, Medium, Hunter, Wolf, Madman]

# --------------------------------------------------
# ページ表示関数
# --------------------------------------------------

def show_top():
    st.title("人狼期待値計算ツール")

    village_roles = [r for r in ALL_ROLES if r.camp.value == "v"]
    wolf_roles    = [r for r in ALL_ROLES if r.camp.value in ["w", "k"]]

    cols = st.columns(2)
    with cols[0]:
        st.header("村陣営")
        for role in village_roles:
            st.number_input(f"{role.char}({role.name})", min_value=0, value=0, key=role.identifier)

    with cols[1]:
        st.header("狼陣営")
        for role in wolf_roles:
            st.number_input(f"{role.char}({role.name})", min_value=0, value=0, key=role.identifier)

    if st.button("simulate"):
        selected_roles = {
            key: val for key, val in st.session_state.items()
            if key in [r.identifier for r in ALL_ROLES] and val > 0
        }
        st.session_state["roles"] = selected_roles
        st.session_state["page"] = "day"
        st.rerun()


def show_day():
    st.title("日別シミュレーション")
    st.write(st.session_state.get("roles"))
    if st.button("戻る"):
        st.session_state["page"] = "top"
        st.rerun()

# --------------------------------------------------
# ページ初期化
# --------------------------------------------------

if "page" not in st.session_state:
    st.session_state["page"] = "top"

# --------------------------------------------------
# ページ切り替え (switch風)
# --------------------------------------------------

page = st.session_state["page"]

match page:
    case "top":
        show_top()
    case "day":
        show_day()
    case _:
        show_top()
