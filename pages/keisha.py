import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="KEISHA", layout="wide")

# 初期化：セッションステートを利用してデータ共有
if "step" not in st.session_state:
    st.session_state["step"] = "お会計"  # 現在の進行状態
if "participant_data" not in st.session_state:
    st.session_state["participant_data"] = []
if "is_confirmed" not in st.session_state:
    st.session_state["is_confirmed"] = False
if "ichijikai_amount" not in st.session_state:
    st.session_state["ichijikai_amount"] = None  # 初期値をNoneに設定
if "nijikai_amount" not in st.session_state:
    st.session_state["nijikai_amount"] = None  # 初期値をNoneに設定

# 動的な進行管理
st.title("傾斜計算アプリ")
st.header(f"現在のステップ: {st.session_state['step']}")

# お会計の入力
if st.session_state["step"] == "お会計":
    st.subheader("1. お会計金額を入力してください")
    ichijikai_input = st.number_input("金額 (1次会)", min_value=0, step=500, value=st.session_state["ichijikai_amount"] or 0, key="ichijikai_amount_input")
    nijikai_input = st.number_input("金額 (2次会)", min_value=0, step=500, value=st.session_state["nijikai_amount"] or 0, key="nijikai_amount_input")

    if st.button("お会計を確定"):
        st.session_state["ichijikai_amount"] = ichijikai_input  # 入力値を保存
        st.session_state["nijikai_amount"] = nijikai_input  # 入力値を保存
        st.session_state["step"] = "参加者"
        st.success("お会計が確定しました。次に参加者を登録してください。")

# 参加者の登録
if st.session_state["step"] == "参加者":
    st.subheader("2. 参加者を登録してください")
    with st.form("participant_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            participant_name = st.text_input("参加者名", key="name_input")
        with col2:
            tilt = st.slider("傾斜", min_value=0, max_value=100, value=50, key="tilt_slider")
        with col3:
            attended_ichijikai = st.checkbox("1次会参加", value=True, key="attended_ichijikai")
            attended_nijikai = st.checkbox("2次会参加", value=True, key="attended_nijikai")
        submitted = st.form_submit_button("追加")
        if submitted:
            if participant_name and tilt > 0:
                st.session_state["participant_data"].append({
                    "名前": participant_name,
                    "傾斜": tilt,
                    "1次会参加": attended_ichijikai,
                    "2次会参加": attended_nijikai
                })
                st.success(f"{participant_name} を追加しました")
            else:
                st.error("名前を入力し、傾斜を0より大きくしてください。")

    # 登録済みの参加者を表示
    if st.session_state["participant_data"]:
        st.write("登録済みの参加者")
        st.dataframe(pd.DataFrame(st.session_state["participant_data"]))

    if st.button("参加者を確定"):
        if st.session_state["participant_data"]:
            st.session_state["step"] = "傾斜計算"
            st.success("参加者が確定しました。次に傾斜計算を確認してください。")
        else:
            st.error("少なくとも1人の参加者を登録してください。")

# 傾斜計算の結果
if st.session_state["step"] == "傾斜計算":
    st.subheader("3. 傾斜計算結果")
    total_tilt_ichijikai = sum(p["傾斜"] for p in st.session_state["participant_data"] if p["1次会参加"])
    total_tilt_nijikai = sum(p["傾斜"] for p in st.session_state["participant_data"] if p["2次会参加"])
    result_data = []

    distributed_nijikai = 0  # 2次会で割り当てられた金額の合計を追跡

    # 各参加者の金額を計算
    for participant in st.session_state["participant_data"]:
        name = participant["名前"]
        tilt = participant["傾斜"]

        # 傾斜を基に1次会と2次会の金額を計算
        ichijikai_share = (
            round((tilt / total_tilt_ichijikai) * st.session_state["ichijikai_amount"], -1) if participant["1次会参加"] else 0
        )
        nijikai_share = (
            round((tilt / total_tilt_nijikai) * st.session_state["nijikai_amount"], -1) if participant["2次会参加"] else 0
        )

        distributed_nijikai += nijikai_share  # 割り当てた2次会金額を追跡

        result_data.append({
            "参加者": name,
            "1次会": ichijikai_share,
            "2次会": nijikai_share,
            "合計": ichijikai_share + nijikai_share
        })

    # 丸め誤差を最後の参加者に補正
    if st.session_state["nijikai_amount"] > 0:
        difference = st.session_state["nijikai_amount"] - distributed_nijikai
        if result_data and abs(difference) > 0:  # 誤差が存在する場合
            result_data[-1]["2次会"] += difference
            result_data[-1]["合計"] += difference

    # 計算結果を表示
    result_df = pd.DataFrame(result_data)
    st.write("傾斜計算結果")
    st.dataframe(result_df)

    # 総計を表示
    st.write("総計")
    st.write(f"1次会合計: ¥{st.session_state['ichijikai_amount']}")
    st.write(f"2次会合計: ¥{st.session_state['nijikai_amount']}")