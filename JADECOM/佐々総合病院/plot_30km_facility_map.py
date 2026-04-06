from pathlib import Path

import folium
import pandas as pd
from folium.plugins import MarkerCluster

BASE = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院')
INPUT = BASE / '佐々総合病院_30km圏_病院_診療所のみ一覧.csv'
OUT_HTML = BASE / '佐々総合病院_30km圏_病院診療所マップ.html'

TARGET_NAME = '医療法人社団　時正会　佐々総合病院'
TARGET_LAT = 35.72977
TARGET_LON = 139.5388
RADIUS_M = 30000


def color_by_distance(d):
    if d <= 5:
        return '#d73027'
    if d <= 10:
        return '#fc8d59'
    if d <= 20:
        return '#fee08b'
    return '#91cf60'


def main():
    df = pd.read_csv(INPUT)
    df['distance_km'] = pd.to_numeric(df['distance_km'], errors='coerce')
    df = df.dropna(subset=['緯度', '経度', 'distance_km'])

    m = folium.Map(location=[TARGET_LAT, TARGET_LON], zoom_start=11, tiles='CartoDB positron', control_scale=True)

    # 30km circle
    folium.Circle(
        location=[TARGET_LAT, TARGET_LON],
        radius=RADIUS_M,
        color='#2c7fb8',
        weight=2,
        fill=True,
        fill_opacity=0.05,
        tooltip='30km圏',
    ).add_to(m)

    # hospital marker
    folium.Marker(
        [TARGET_LAT, TARGET_LON],
        popup=folium.Popup(f'<b>{TARGET_NAME}</b>', max_width=300),
        tooltip='佐々総合病院',
        icon=folium.Icon(color='red', icon='plus-sign'),
    ).add_to(m)

    cluster = MarkerCluster(name='病院・診療所').add_to(m)

    for _, r in df.iterrows():
        name = str(r.get('医療機関名', ''))
        pref = str(r.get('都道府県名', ''))
        city = str(r.get('市区町村名', ''))
        addr = str(r.get('所在地', ''))
        dist = float(r['distance_km'])

        popup_html = (
            f"<b>{name}</b><br>"
            f"都道府県: {pref}<br>"
            f"市区町村: {city}<br>"
            f"所在地: {addr}<br>"
            f"距離: {dist:.2f} km"
        )

        folium.CircleMarker(
            location=[float(r['緯度']), float(r['経度'])],
            radius=4,
            color=color_by_distance(dist),
            fill=True,
            fill_opacity=0.8,
            weight=1,
            popup=folium.Popup(popup_html, max_width=420),
            tooltip=f"{name} ({dist:.1f}km)",
        ).add_to(cluster)

    # legend
    legend_html = """
    <div style="position: fixed; bottom: 24px; left: 24px; z-index: 9999;
                background: white; padding: 10px 12px; border: 1px solid #bbb; border-radius: 8px;
                font-size: 13px; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
      <div style="font-weight:700; margin-bottom:6px;">距離凡例</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#d73027;border-radius:50%;margin-right:6px;"></span>0-5km</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#fc8d59;border-radius:50%;margin-right:6px;"></span>5-10km</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#fee08b;border-radius:50%;margin-right:6px;"></span>10-20km</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#91cf60;border-radius:50%;margin-right:6px;"></span>20-30km</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(OUT_HTML))

    print(f'saved: {OUT_HTML}')
    print(f'points: {len(df)}')


if __name__ == '__main__':
    main()
