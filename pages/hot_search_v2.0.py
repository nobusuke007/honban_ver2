#まずは必要なライブラリをimport ※gspreadなどはインストール必要と思います。
import streamlit as st
import requests
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
#map機能使うなら
import folium
from streamlit_folium import st_folium
# "いたの" 以下ライブラリに関する記述を新たに追加（2024/12/13）↓
# なお、ライブラリのインストールが必要になるため、
# "pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib"で
# 必要なライブラリはインストールしておく↑

from googleapiclient.discovery import build

# 設定
# "いたの" Streamlit Secretsからサービスアカウントキーを取得する処理。(2024/12/13)
# Streamlit Cloud上では、TOML形式にてst.secretsに設定する必要があるため、以下の参照キーもTOML変換時に設定した"general"を指定
service_account_info = st.secrets["general"]
# いたのでAPIと連携させたスプレッドシートのURLです。こちらはサービスアカウントキーを私のものを使って貰えればそのまま使えるものと推測します。
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1KNOF6o3k12tvaHiysZX0ntRlOC44nQP_f-W4mUNQdGg/edit"  
# いたののHot PepperのAPI KEYです。こちらは漏れてもまあ問題ないかな、という事でベタ打ちしています。
API_KEY = "a074064d60de7979" 

# Googleスプレッドシート認証
# 以下はお作法的な意味合いが強いと思っています。
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# 変数、service_account_infoでの認証に記述を変更。(2024/12/13)
credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
gc = gspread.authorize(credentials)
# 以上までが認証のところで、以下はスプレッドシートのsheet1を参照する事を指定しています。
worksheet = gc.open_by_url(SPREADSHEET_URL).sheet1

# ここから以下はあまぬんさんが記述頂いたものと近い内容になってくるかと思います。
# Hotpepper APIのエリアマスタ取得URL
# それぞれのURLをマスタとして記述します。
AREA_API_URL = "http://webservice.recruit.co.jp/hotpepper/large_area/v1/"
MIDDLE_AREA_API_URL = "http://webservice.recruit.co.jp/hotpepper/middle_area/v1/"
SMALL_AREA_API_URL = "http://webservice.recruit.co.jp/hotpepper/small_area/v1/"
SHOP_SEARCH_API_URL = "http://webservice.recruit.co.jp/hotpepper/gourmet/v1/"

#map機能使うならコメントアウトさせない。foliumのimportも必要

def mapping(shop_data):

    m = folium.Map(location=[shop_data[0]["lat"], shop_data[0]["lng"]], zoom_start=14)  # 初期位置は1番目のデータとする

    for shop in shop_data:
        lat = shop["lat"]
        lng = shop["lng"]
        name = shop["name"]
    
        # 店舗の情報を地図に追加
        folium.Marker(
            location=[lat, lng],
            popup=f"{name}",
        ).add_to(m)
    
    return m

    

# 以下が関数の定義を実施している部分です。導通が取れたらjson形式で返す、という感じっすね。
def fetch_area_data(api_url, params):
    """APIからエリアデータを取得"""
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        return response.json()
    return {}
# こちらも同様です。
def fetch_shop_data(params):
    """店舗情報を取得"""
    response = requests.get(SHOP_SEARCH_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    return {}
# スプレッドシートに記載されているデータを参照しにいく関数です。
# 当初はキャッシュする作動を提案されたのですが、最新のデータが反映されなかったことから、毎度取りに行く処理にして貰いました。
def get_past_data():
    """スプレッドシートから最新の利用済店舗データを取得"""
    rows = worksheet.get_all_values()
    if len(rows) > 1:
        return {row[0]: row[2] for row in rows[1:]}  # 店舗IDをキーに、利用日を値として辞書化
    return {}

# 初期化
# ページの読み込みに依るStreamlit特有の事象をクリアするための、sessionを設定している領域となります。
# こちらの設定が出来ていない状態だと以下で記述しているラジオボタンなど選択の際に毎度初期化されてしまうという事象が起きていました。
if "shops" not in st.session_state:
    st.session_state.shops = []
if "selected_shop_id" not in st.session_state:
    st.session_state.selected_shop_id = None
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None

# UI
# 以下はStreamlitでのUIについての記述です。あまぬんさんのコードともけっこう近い…かな？
st.title("飲み会レストラン設定サポートアプリ")

# 大エリア選択・・・まずはエリアマスタから取得した大エリアを選んでもらいます。
large_area_params = {"key": API_KEY, "format": "json"}
large_area_data = fetch_area_data(AREA_API_URL, large_area_params)
large_area_options = [
    (area["code"], area["name"]) for area in large_area_data.get("results", {}).get("large_area", [])
]
selected_large_area = st.selectbox(
    "大エリアを選択してください", options=[("", "選択してください")] + large_area_options, format_func=lambda x: x[1] if x else ""
)

# 中エリア選択・・・大エリアを選んでもらったら、それに順じた中エリアをプルダウンで選べるようにします。
if selected_large_area:
    middle_area_params = {"key": API_KEY, "large_area": selected_large_area[0], "format": "json"}
    middle_area_data = fetch_area_data(MIDDLE_AREA_API_URL, middle_area_params)
    middle_area_options = [
        (area["code"], area["name"]) for area in middle_area_data.get("results", {}).get("middle_area", [])
    ]
    selected_middle_area = st.selectbox(
        "中エリアを選択してください", options=[("", "選択してください")] + middle_area_options, format_func=lambda x: x[1] if x else ""
    )
else:
    selected_middle_area = None

# 小エリア選択・・・同様最後は小エリアです。
if selected_middle_area:
    small_area_params = {"key": API_KEY, "middle_area": selected_middle_area[0], "format": "json"}
    small_area_data = fetch_area_data(SMALL_AREA_API_URL, small_area_params)
    small_area_options = [
        (area["code"], area["name"]) for area in small_area_data.get("results", {}).get("small_area", [])
    ]
    selected_small_area = st.selectbox(
        "小エリアを選択してください", options=[("", "選択してください")] + small_area_options, format_func=lambda x: x[1] if x else ""
    )
else:
    selected_small_area = None

# 諸条件
Private_room = st.checkbox("個室あり")
if Private_room:
    Private_room_key = 1
else:
    Private_room_key = 0

free_drink = st.checkbox("飲み放題あり")
if free_drink:
    free_drink_key = 1
else:
    free_drink_key = 0

free_food = st.checkbox("食べ放題あり")
if free_food:
    free_food_key = 1
else:
    free_food_key = 0

# 店の最大パーティ人数で絞る
party_capacity = st.slider('最大宴会収容人数', 1, 200, 5)

# 表示データ数
count = st.slider('最大表示データ数', 1, 100, 30)

# 候補店舗検索・・・検索ボタンをつけて、ボタンを押すと、10件の店舗が表示できるようにしています。
# 以下paramsのcount部分の数値を変更してもらえれば、出力件数の調整が可能です。※ここは選べるようにするUIがいいすかね。
if selected_small_area and st.button("検索"):
    shop_params = {
        "key": API_KEY,
        "format": "json",
        "small_area": selected_small_area[0],
        "Private_room":Private_room_key,
        "free_drink":free_drink_key,
        "free_food":free_food_key,
        "party_capacity": party_capacity,
        "count": count,
    }
    shop_data = fetch_shop_data(shop_params)
    st.session_state.shops = shop_data.get("results", {}).get("shop", [])

# ここからが、出力された候補店舗に対する、
# 過去利用店舗との識別、それを、過去利用した店舗を上位に出す、という流れの部分です。
# 候補店舗リスト表示
if st.session_state.shops:
    st.subheader("候補店舗リスト")
    past_data = get_past_data()  # 常に最新データを取得　※defの関数で指定した部分ですね。

    # 過去利用店舗と新規店舗を分離　
    # この処理勉強になるわー笑 の感じです。
    # shop"id"をキーとして、name、address、mark(星っすね)を辞書型として持つために、used/newで条件を切り分けて、
    # 空の辞書にappendしていっています。
    used_shops = []
    new_shops = []
    for shop in st.session_state.shops:
        shop_id = shop["id"]
        shop_entry = {
            "id": shop["id"],
            "name": shop["name"],
            "address": shop["address"],
            "lat":shop["lat"], #map化のために追加
            "lng":shop["lng"], #map化のために追加
            "url":shop["urls"]["pc"],
            "mark": f"⭐ (利用日: {past_data[shop_id]})" if shop_id in past_data else "",
        }
        if shop_id in past_data:
            used_shops.append(shop_entry)
        else:
            new_shops.append(shop_entry)

    # リストを結合して順番に表示
    # 上記処理の結果作成出来たリストをall_shopsとして変数設定します。
    all_shops = used_shops + new_shops

    # 店舗選択用ラジオボタン
    # ここの処理、私さっぱり分からなかったので、GPTに深堀したところ、
    # 店舗選択用の空の辞書を作成し、そこにfor分で表示されている店舗の選択肢を入れていくとの事。
    # そこからラジオボタンで選択した店舗情報が"st.session_state.selected_shop_id"に保存されていくとの事。。うーん、まだ分からん笑
    shop_options = {shop["id"]: f"{shop['name']} - {shop['address']} {shop['url']} {shop['mark']}" for shop in all_shops}
    st.session_state.selected_shop_id = st.radio(
        "店舗を選択してください。使用履歴のある店には⭐が付いています", options=list(shop_options.keys()), format_func=lambda x: shop_options[x]
    )

    #map機能使うなら！
    
    m = mapping(all_shops)
    st_folium(m, width=700, height=500)
    

    # 利用日時を選択
    # st.dateはカレンダーを扱うStreamlitの関数ですね。
    st.session_state.selected_date = st.date_input("利用日時を選択してください")

    # 決定ボタン
    # 決定ボタンが押されると、以下の処理が動くイメージです。next関数はall_shopsから最初に一致した値を返す関数らしい。。。
    # shop["id"] が st.session_state.selected_shop_idと一致する店舗を探し、一致する店舗があった場合、selected_shopに代入されます。
    if st.button("決定"):
        selected_shop = next((shop for shop in all_shops if shop["id"] == st.session_state.selected_shop_id), None)
        if selected_shop:
            st.success(f"店舗: {selected_shop['name']} が選択されました！ 利用日時: {st.session_state.selected_date}")

    # スプレッドシートに書き込み
    # 最後にスプレッドシートへの書き込み処理です。"利用済店舗登録"のボタンが押されたら、"決定"ボタンと同様に選択された店舗を
    # all_shopsから検索します。selected_shopに選択された店舗のデータが辞書形式で代入されます。
    # その後worksheet.append_rowで、指定のid、name、date(-形式に変換)をスプレッドシートに書き込みます。
    if st.button("利用済店舗登録"):
        selected_shop = next((shop for shop in all_shops if shop["id"] == st.session_state.selected_shop_id), None)
        if selected_shop:
            try:
                worksheet.append_row([
                    selected_shop["id"],
                    selected_shop["name"],
                    st.session_state.selected_date.strftime("%Y-%m-%d")
                ])
                st.success("利用済店舗として登録ができました！")
            except Exception as e:
                st.error(f"スプレッドシート書き込みエラー: {e}")