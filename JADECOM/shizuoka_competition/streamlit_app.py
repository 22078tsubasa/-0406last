from __future__ import annotations

import base64
import hmac
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from config import DEFAULT_PASSWORD, OUT_ROOT


REGISTRY_PATH = OUT_ROOT / "registry.json"
COMPETITION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = COMPETITION_ROOT.parent
EXTRA_REGISTRY_PATHS = sorted(
    path
    for path in COMPETITION_ROOT.glob("*_competition/out/registry.json")
    if path != REGISTRY_PATH
)

PALETTE = {
    "bg": "#eef5ea",
    "main": "#70AD47",
    "deep": "#2f6b2f",
    "light": "#cfe8bf",
    "accent": "#9BC53D",
    "text": "#1f2d1f",
}

IMAGE_VIEWPORT_HEIGHT = 760
ZOOM_MIN = 80
ZOOM_MAX = 400
ZOOM_STEP = 20
ZOOM_DEFAULT = 140


def file_ok(path: Path) -> bool:
    return path.exists() and path.is_file()


def resolve_repo_path(path_like: str | Path) -> Path:
    path = Path(path_like)
    if path.exists():
        return path
    text = str(path_like)
    marker = "JADECOM/"
    if marker in text:
        rel = text.split(marker, 1)[1]
        candidate = REPO_ROOT / marker / rel
        if candidate.exists():
            return candidate
    if not path.is_absolute():
        candidate = REPO_ROOT / path
        if candidate.exists():
            return candidate
    return path


def read_csv_safely(path: Path) -> pd.DataFrame:
    if not file_ok(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def get_expected_password() -> str:
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except StreamlitSecretNotFoundError:
        pass
    return os.getenv("APP_PASSWORD", DEFAULT_PASSWORD)


def require_password() -> None:
    expected = get_expected_password()
    if st.session_state.get("authed", False):
        return
    st.title("全国競合分析アプリ（閲覧認証）")
    st.caption("閲覧にはパスワードが必要です")
    pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if hmac.compare_digest(pw, expected):
            st.session_state["authed"] = True
            st.rerun()
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


def load_registry() -> dict:
    registry_paths = [REGISTRY_PATH] + EXTRA_REGISTRY_PATHS
    merged: dict[str, dict] = {}

    found = False
    for path in registry_paths:
        if not file_ok(path):
            continue
        found = True
        data = json.loads(path.read_text(encoding="utf-8"))
        for pref_key, pref_data in data.items():
            if pref_key not in merged:
                merged[pref_key] = {
                    "label": pref_data.get("label", pref_key),
                    "facilities": [],
                }
            existing = {f["key"] for f in merged[pref_key]["facilities"]}
            for facility in pref_data.get("facilities", []):
                normalized = dict(facility)
                if "manifest" in normalized:
                    normalized["manifest"] = str(resolve_repo_path(normalized["manifest"]))
                if normalized["key"] not in existing:
                    merged[pref_key]["facilities"].append(normalized)
                    existing.add(normalized["key"])

    if not found:
        st.error(f"registry not found: {REGISTRY_PATH}")
        st.stop()

    return merged


def load_manifest(path: Path) -> dict:
    path = resolve_repo_path(path)
    if not file_ok(path):
        st.error(f"manifest not found: {path}")
        st.stop()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["images"] = {k: str(resolve_repo_path(v)) for k, v in manifest.get("images", {}).items()}
    manifest["csvs"] = {k: str(resolve_repo_path(v)) for k, v in manifest.get("csvs", {}).items()}
    return manifest


def adjust_zoom(state_key: str, delta: int) -> None:
    current = int(st.session_state.get(state_key, ZOOM_DEFAULT))
    st.session_state[state_key] = max(ZOOM_MIN, min(ZOOM_MAX, current + delta))


def render_zoomable_image(title: str, path: Path, key_prefix: str) -> None:
    st.subheader(title)
    if not file_ok(path):
        st.warning(f"{title} が見つかりません。")
        return

    zoom_key = f"{key_prefix}_zoom"
    if zoom_key not in st.session_state:
        st.session_state[zoom_key] = ZOOM_DEFAULT

    c1, c2, c3 = st.columns([0.9, 1.4, 6.7])
    with c1:
        st.button(
            "−",
            key=f"{key_prefix}_zoom_out",
            on_click=adjust_zoom,
            args=(zoom_key, -ZOOM_STEP),
            use_container_width=True,
        )
    with c2:
        st.button(
            "+",
            key=f"{key_prefix}_zoom_in",
            on_click=adjust_zoom,
            args=(zoom_key, ZOOM_STEP),
            use_container_width=True,
        )
    with c3:
        st.caption(f"拡大率: {st.session_state[zoom_key]}%")

    zoom_pct = int(st.session_state[zoom_key])

    image_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <div style="
            overflow: auto;
            height: {IMAGE_VIEWPORT_HEIGHT}px;
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


def render_header(manifest: dict) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
          <div class="hero-title">{manifest['facility']}競合分析</div>
          <div class="hero-sub">{manifest['prefecture']} | 町丁目別勢力図・ヒートマップ・マトリクス・グラフ</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_tab(image_files: dict[str, Path], target_plus5_label: str) -> None:
    left, right = st.columns(2)
    with left:
        render_zoomable_image("全体勢力図", image_files["全体勢力図"], "map_all")
    with right:
        render_zoomable_image(target_plus5_label, image_files["対象施設+上位5勢力図"], "map_plus5")


def render_heatmap_tab(image_files: dict[str, Path]) -> None:
    render_zoomable_image("上位10ヒートマップ", image_files["上位10ヒートマップ図"], "heat_top10")


def render_matrix_tab(image_files: dict[str, Path]) -> None:
    render_zoomable_image("上位3マトリクス", image_files["上位3マトリクス図"], "matrix_top3")


def render_graph_tab(image_files: dict[str, Path]) -> None:
    render_zoomable_image("グラフ", image_files["グラフ"], "graph_top60")


def render_data_tab(csv_files: dict[str, Path], scope: str, target_plus5_label: str) -> None:
    st.subheader("用語と集計範囲")
    st.info(
        "この画面では『患者数』と『利用者数』は同じ意味（人数）です。"
        "表ごとに集計対象が異なるため、数値は一致しないことがあります。"
    )
    st.markdown(
        f"- 一部抜粋60町丁目: {scope} のうち距離（dist_km）が近い順の上位60町丁目\n"
        "- 施設ランキング: 一部抜粋（表示用の上位60町丁目）内での合計人数\n"
        "- 対象施設（利用者数TOP60）: 自動車30分圏の全対象町丁目で選定した施設一覧"
    )

    rank_df = read_csv_safely(csv_files["施設ランキングCSV"])
    if not rank_df.empty:
        st.subheader("施設ランキング（上位20 / 一部抜粋60町丁目ベース）")
        st.dataframe(rank_df.head(20), use_container_width=True, hide_index=True)

    selected_df = read_csv_safely(csv_files["選定施設CSV"])
    if not selected_df.empty:
        st.subheader("対象施設（利用者数TOP60 / 30分圏全町丁目ベース）")
        st.dataframe(selected_df, use_container_width=True, hide_index=True)

    plus5_df = read_csv_safely(csv_files["対象施設+上位5勢力図データ"])
    dom_col = None
    for c in ["dominant_sel6", "plot_label", "dominant"]:
        if c in plus5_df.columns:
            dom_col = c
            break
    if not plus5_df.empty and dom_col is not None:
        st.subheader(f"{target_plus5_label}の勢力分布（町丁目数）")
        plus5_view = plus5_df[dom_col].fillna("未結合").value_counts().rename_axis("施設名").reset_index(name="町丁目数")
        st.dataframe(plus5_view, use_container_width=True, hide_index=True)


def render_help_tab(manifest: dict, csv_files: dict[str, Path]) -> None:
    st.subheader("使い方")
    st.markdown(
        f"""
        - 画面上部で都道府県と医療機関を切り替えると、対象施設の競合分析に切り替わります。
        - 各図の上にある `−` `+` ボタンは拡大率の調整用です。広く見たいときは縮小、文字や境界を確認したいときは拡大してください。
        - 表示枠の高さは固定です。スクロールしながら図の全体と細部を確認する前提にしています。
        - 集計範囲は `{manifest.get("scope", "町丁目別")}` です。表や図ごとに抽出条件が異なるため、同じ施設でも数値が一致しないことがあります。
        """
    )

    st.subheader("各可視化の見方")
    st.markdown(
        """
        - `勢力図`: 町丁目ごとに、どの医療機関の利用者数が相対的に強いかを色分けして見ます。
        - `対象施設+上位5勢力図`: 対象施設と競合上位5施設に絞って、競争関係を簡潔に確認します。
        - `ヒートマップ`: 町丁目と主要医療機関の組み合わせを濃淡で見て、利用が強い地点を把握します。
        - `マトリクス`: 上位施設に絞った比較図です。行と列を見比べることで、どの町丁目でどの施設の利用が強いかを横断的に確認できます。
        - `マトリクス` の意図: 勢力図では地理的な広がりを見て、マトリクスでは施設間の強弱を表形式で見比べます。競合の重なり方を整理して確認するための画面です。
        - `マトリクス` の見方: 濃い色や大きい値が出ているマスは、その町丁目における当該施設の利用が相対的に強いことを示します。複数施設で濃いマスが近い町丁目に並ぶ場合、その地域では競合が強いと読めます。
        - `マトリクス` の使いどころ: 対象施設と競合施設の差がどの町丁目で出ているか、逆にどの町丁目で取り合いになっているかを確認するのに向いています。
        - `グラフ`: 主要町丁目または主要施設の分布傾向を一覧的に見ます。極端な集中や分散の把握に向いています。
        - `データ確認`: 画面内で主要なCSV内容を表として確認します。
        """
    )

    st.subheader("データ一覧の意味")
    data_descriptions = [
        ("全体勢力図データ", "全町丁目を対象に、各町丁目で優勢な医療機関を整理したデータです。"),
        ("対象施設+上位5勢力図データ", "対象施設と競合上位5施設に限定した勢力図の元データです。"),
        ("上位10マトリクスCSV", "主要10施設を対象にしたヒートマップ用の集計表です。"),
        ("上位3マトリクスCSV", "主要3施設に絞った比較用の行列データです。"),
        ("施設ランキングCSV", "表示用に抽出した町丁目範囲内での施設別合計人数です。"),
        ("選定施設CSV", "30分圏全体をもとに可視化対象として選定した施設一覧です。"),
        ("表示用ベース行列CSV", "画面表示向けに整形した基礎テーブルです。"),
        ("町丁目×医療機関統合CSV", "町丁目と医療機関の組み合わせをまとめた元に近い統合データです。"),
    ]
    for key, desc in data_descriptions:
        status = "あり" if file_ok(csv_files.get(key, Path())) else "なし"
        st.markdown(f"- `{key}`: {desc} 現在の対象施設では `{status}`。")


def main() -> None:
    st.set_page_config(page_title="全国競合分析アプリ", layout="wide")
    require_password()
    inject_style()

    registry = load_registry()
    prefectures = list(registry.keys())
    pref_key = st.selectbox("都道府県を選択", prefectures, format_func=lambda k: registry[k]["label"])
    facilities = registry[pref_key]["facilities"]
    facility_key = st.selectbox("医療機関を選択", [f["key"] for f in facilities], format_func=lambda k: next(f["label"] for f in facilities if f["key"] == k))
    selected = next(f for f in facilities if f["key"] == facility_key)
    manifest = load_manifest(Path(selected["manifest"]))
    target_plus5_label = f"{manifest['facility']}+上位5勢力図"
    scope = manifest.get("scope", "町丁目別")

    st.caption("都道府県を選択後、医療機関を選ぶと既存の競合分析画面を表示します")
    render_header(manifest)

    image_files = {k: Path(v) for k, v in manifest["images"].items()}
    csv_files = {k: Path(v) for k, v in manifest["csvs"].items()}
    missing = [name for name, p in {**image_files, **csv_files}.items() if not file_ok(p)]
    if missing:
        st.warning("不足ファイル: " + " / ".join(missing))

    help_tab, map_tab, heat_tab, matrix_tab, graph_tab, data_tab = st.tabs(
        ["使い方", "勢力図", "ヒートマップ", "マトリクス", "グラフ", "データ確認"]
    )

    with help_tab:
        render_help_tab(manifest, csv_files)

    with map_tab:
        render_map_tab(image_files, target_plus5_label)

    with heat_tab:
        render_heatmap_tab(image_files)

    with matrix_tab:
        render_matrix_tab(image_files)

    with graph_tab:
        render_graph_tab(image_files)

    with data_tab:
        render_data_tab(csv_files, scope, target_plus5_label)

    st.info(
        "起動コマンド: `cd /Users/itotsubasa/IdeaProjects/pythoN && "
        "./.venv/bin/streamlit run JADECOM/shizuoka_competition/streamlit_app.py`"
    )


if __name__ == "__main__":
    main()
