import streamlit as st
import pandas as pd 
from supabase import create_client, Client
import uuid

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


st.set_page_config(page_title="健康管理ダッシュボード", page_icon="🏥", layout="wide")

st.title("データベース連携健康管理アプリ")

if not st.user.is_logged_in:
    st.warning("ログインしてください")
    if st.button("Googleでログイン"):
        st.login("google")

else:
    st.success(f"ようこそ、{st.user.name}さん！")
    st.write(f"メールアドレス: {st.user.email}")
    user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, st.user.email.strip()))

    with st.form("health_log_form"):
        date = st.date_input("日付を選択してください")
        condition = st.slider("今日の調子", 0, 10, 5, step=1)
        sleep = st.slider("睡眠時間(h)", 0.0, 12.0, 7.0, step=0.5, format="%.1f")
        weather = st.selectbox("天気",["晴れ", "くもり", "雨", "晴れのちくもり", "晴れのち雨", "くもりのち晴れ", "くもりのち雨", "雨のち晴れ", "雨のちくもり", "雷", "その他"])
        headahce = st.radio(
            "頭痛の有無",
            options=[True, False],
            format_func=lambda x: "あり" if x else "なし",
            index=1,
        )
        study = st.number_input("勉強時間(分)", min_value=0, value=0)

        submit_button = st.form_submit_button("記録を保存")

    if submit_button:
    
        insert_data = {
            "user_id": user_uuid, 
            "record_date": str(date),
            "condition_score": condition,
            "sleep_hours": sleep,
            "weather": weather,
            "headache": headahce,
            "study_minutes": study,
        }

        try:
            response = supabase.table("health-log").insert(insert_data).execute()
            st.success("データを保存しました")
        except Exception as e:
                st.error(f"保存エラー: {e}")

    st.divider()

    st.subheader("データ抽出と可視化")

    if st.button("このユーザーのデータを読み込んで分析"):
        
        try:
            response = (
                supabase.table("health-log")
                .select("*")
                .eq("user_id", user_uuid)
                .order("record_date", desc=True)
                .execute()
                )

            df = pd.DataFrame(response.data)

            if df.empty:
                st.info("該当するユーザーのデータがありません")
            else:
                df["record_date"] = pd.to_datetime(df["record_date"]).dt.strftime('%Y-%m-%d')

                st.subheader("総勉強時間")
                total_study = df["study_minutes"].sum()
                hours = total_study // 60
                minutes = total_study % 60
                st.write(f"総勉強時間は{hours}時間{minutes}分です")


                st.subheader("📈グラフ")
                st.caption("体調スコア(0-10)と睡眠時間(h)の推移")
                st.line_chart(df.set_index("record_date")[["condition_score", "sleep_hours"]])

                st.subheader("🗒️データ一覧表示")
                st.dataframe(df[["record_date", "condition_score", "sleep_hours", "weather", "headache", "study_minutes"]], use_container_width=True)
        except Exception as e:
            st.error(f"データ取得エラー: {e}")

    st.divider()
    st.subheader("🗑️データの削除")

    delete_target_date = st.date_input(
        "削除したいデータの日付を選択してください", key="delete_date_picler"
    )

    @st.dialog("データ削除の確認")
    def confirm_delete_dialog(selected_date_str, user_uuid_val):
        st.warning(
            f"本当に **{selected_date_str}** のデータを削除しますか\n"
            "この操作は取り消せません"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("削除を実行する", type="primary"):
                try:
                    res = (
                        supabase.table("health-log")
                        .delete()
                        .eq("user_id", user_uuid_val)
                        .eq("record_date", selected_date_str)
                        .execute()
                    )
                    if res.data and len(res.data) > 0 :
                        st.success(
                            f"{selected_date_str}のデータを{len(res.data)}件削除しました。"
                        )
                    else:
                        st.info(
                            f"{selected_date_str}に該当するデータが存在しないか、すでに削除されています。"
                        )
                    st.rerun()
                except Exception as e:
                    st.error(f"削除エラー: {e}")

        with col2:
            if st.button("キャンセル"):
                st.rerun()

    if st.button("選択した日付のデータを削除", type="primary"):
        confirm_delete_dialog(str(delete_target_date), user_uuid)


