from __future__ import annotations

import base64
import hmac
import io
import os
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


BASE_DIR = Path(__file__).resolve().parent

IMAGE_FILES = {
    "全体勢力図": BASE_DIR / "dominant_territory_tsuge_30km.png",
    "都祁診療所+上位5勢力図": BASE_DIR / "dominant_territory_tsuge_30km_tsuge_plus5.png",
    "上位10ヒートマップ図": BASE_DIR / "town_med_heatmap_top10.png",
    "上位3マトリクス図": BASE_DIR / "town_med_matrix_top3.png",
    "グラフ": BASE_DIR / "town_med_graph_top60.png",
}

CSV_FILES = {
    "全体勢力図データ": BASE_DIR / "dominant_territory_tsuge_30km_result.csv",
    "都祁+上位5勢力図データ": BASE_DIR / "dominant_territory_tsuge_30km_tsuge_plus5_result.csv",
    "上位3マトリクスCSV": BASE_DIR / "town_med_matrix_top3_only.csv",
    "上位10マトリクスCSV": BASE_DIR / "town_med_matrix_top10.csv",
    "施設ランキングCSV": BASE_DIR / "facility_rank_summary.csv",
}

PALETTE = {
    "bg": "#eef5ea",
    "main": "#70AD47",
    "deep": "#2f6b2f",
    "light": "#cfe8bf",
    "accent": "#9BC53D",
    "text": "#1f2d1f",
}


def file_ok(path: Path) -> bool:
    return path.exists() and path.is_file()


def read_csv_safely(path: Path) -> pd.DataFrame:
    if not file_ok(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def build_zip_bytes() -> bytes:
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for _, p in IMAGE_FILES.items():
            if file_ok(p):
                zf.write(p, arcname=p.name)
        for _, p in CSV_FILES.items():
            if file_ok(p):
                zf.write(p, arcname=p.name)
    memory.seek(0)
    return memory.read()


def get_expected_password() -> str:
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except StreamlitSecretNotFoundError:
        pass
    return os.getenv("APP_PASSWORD", "")


def require_password() -> None:
    expected = get_expected_password()
    if not expected:
        st.warning("パスワードが未設定です。`APP_PASSWORD` を secrets か環境変数に設定してください。")
        st.stop()

    if st.session_state.get("authed", False):
        return

    st.title("都祁診療所競合分析（閲覧認証）")
    st.caption("閲覧にはパスワードが必要です")
    pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if hmac.compare_digest(pw, expected):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()


def inject_style() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
              radial-gradient(circle at 8% 10%, #dcefcf 0%, transparent 30%),
              radial-gradient(circle at 88% 18%, #d2e9c0 0%, transparent 28%),
              linear-gradient(180deg, {PALETTE['bg']} 0%, #f7fbf4 100%);
            color: {PALETTE['text']};
        }}
        .hero-card {{
            background: linear-gradient(120deg, {PALETTE['main']} 0%, {PALETTE['deep']} 100%);
            padding: 1.4rem 1.6rem;
            border-radius: 18px;
            color: white;
            box-shadow: 0 10px 26px rgba(30,60,30,0.16);
            position: relative;
            overflow: hidden;
        }}
        .hero-card:before {{
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            border-radius: 999px;
            right: -70px;
            top: -70px;
            background: rgba(255,255,255,0.14);
        }}
        .hero-card:after {{
            content: "";
            position: absolute;
            width: 180px;
            height: 180px;
            border-radius: 999px;
            left: -70px;
            bottom: -90px;
            background: rgba(255,255,255,0.12);
        }}
        .hero-title {{
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: 0.03em;
            margin-bottom: 0.2rem;
        }}
        .hero-sub {{
            font-size: 1rem;
            opacity: 0.95;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero-card">
          <div class="hero-title">都祁診療所競合分析</div>
          <div class="hero-sub">町丁目別勢力図・ヒートマップ・マトリクス・グラフ</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_zoomable_image(title: str, path: Path, key_prefix: str) -> None:
    st.subheader(title)
    if not file_ok(path):
        st.warning(f"{title} が見つかりません。")
        return

    c1, c2 = st.columns([1, 1])
    with c1:
        zoom_pct = st.slider("拡大率(%)", 80, 400, 140, 10, key=f"{key_prefix}_zoom")
    with c2:
        viewport_h = st.slider("表示枠の高さ(px)", 300, 1400, 760, 20, key=f"{key_prefix}_height")

    image_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <div style="
            overflow: auto;
            max-height: {viewport_h}px;
            border: 1px solid #aacb98;
            border-radius: 10px;
            background: white;
            box-shadow: inset 0 0 0 1px #e8f2e0;
            padding: 8px;
        ">
            <img src="data:image/png;base64,{image_b64}"
                 style="width: {zoom_pct}%; max-width: none; height: auto;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_tab() -> None:
    left, right = st.columns(2)
    with left:
        render_zoomable_image("全体勢力図", IMAGE_FILES["全体勢力図"], "map_all")
    with right:
        render_zoomable_image("都祁診療所+上位5勢力図", IMAGE_FILES["都祁診療所+上位5勢力図"], "map_plus5")


def render_heatmap_tab() -> None:
    render_zoomable_image("上位10ヒートマップ", IMAGE_FILES["上位10ヒートマップ図"], "heat_top10")


def render_matrix_tab() -> None:
    render_zoomable_image("上位3マトリクス", IMAGE_FILES["上位3マトリクス図"], "matrix_top3")


def render_graph_tab() -> None:
    render_zoomable_image("グラフ", IMAGE_FILES["グラフ"], "graph_top60")


def render_data_tab() -> None:
    st.subheader("用語と集計範囲")
    st.info(
        "この画面では『患者数』と『利用者数』は同じ意味（人数）です。"
        "表ごとに集計対象が異なるため、数値は一致しないことがあります。"
    )
    st.markdown(
        "- 施設ランキング: 表示対象町丁目内での合計人数\n"
        "- 勢力図: 各町丁目で最も人数が多い施設を着色\n"
        "- グラフ: 距離の近い順上位60町丁目での積み上げ表示"
    )

    rank_df = read_csv_safely(CSV_FILES["施設ランキングCSV"])
    if not rank_df.empty:
        st.subheader("施設ランキング（上位20）")
        rank_view = rank_df.head(20).rename(
            columns={
                "facility": "施設名",
                "total_patients": "総患者数",
                "top3_frequency": "上位3出現回数",
            }
        )
        st.dataframe(rank_view, use_container_width=True, hide_index=True)

    plus5_df = read_csv_safely(CSV_FILES["都祁+上位5勢力図データ"])
    dom_col = None
    for c in ["sel_dominant", "plot_label", "dominant"]:
        if c in plus5_df.columns:
            dom_col = c
            break
    if not plus5_df.empty and dom_col is not None:
        st.subheader("都祁+上位5の勢力分布（町丁目数）")
        plus5_view = plus5_df[dom_col].fillna("未結合").value_counts().rename_axis("施設名").reset_index(name="町丁目数")
        st.dataframe(plus5_view, use_container_width=True, hide_index=True)


def render_download_tab() -> None:
    st.subheader("ダウンロード")
    for label, path in {**IMAGE_FILES, **CSV_FILES}.items():
        if file_ok(path):
            st.download_button(
                label=f"{label} をダウンロード",
                data=path.read_bytes(),
                file_name=path.name,
                mime="application/octet-stream",
                key=f"dl_{path.name}",
            )

    zip_bytes = build_zip_bytes()
    st.download_button(
        label="資料一式 ZIP をダウンロード",
        data=zip_bytes,
        file_name="tsuge_report_bundle.zip",
        mime="application/zip",
    )


st.set_page_config(page_title="都祁診療所競合分析", layout="wide")
require_password()
inject_style()
render_header()

missing = [name for name, p in {**IMAGE_FILES, **CSV_FILES}.items() if not file_ok(p)]
if missing:
    st.warning("不足ファイル: " + " / ".join(missing))

c1, c2, c3, c4 = st.columns(4)
c1.metric("勢力図", "2種")
c2.metric("ヒートマップ", "1種")
c3.metric("マトリクス", "1種")
c4.metric("更新日", datetime.now().strftime("%Y-%m-%d"))

map_tab, heat_tab, matrix_tab, graph_tab, data_tab, dl_tab = st.tabs(
    ["勢力図", "ヒートマップ", "マトリクス", "グラフ", "データ確認", "ダウンロード"]
)

with map_tab:
    render_map_tab()
with heat_tab:
    render_heatmap_tab()
with matrix_tab:
    render_matrix_tab()
with graph_tab:
    render_graph_tab()
with data_tab:
    render_data_tab()
with dl_tab:
    render_download_tab()

st.info(
    "起動コマンド: `cd /Users/itotsubasa/IdeaProjects/pythoN && "
    "./.venv/bin/streamlit run JADECOM/202603/streamlit_report.py`"
)
