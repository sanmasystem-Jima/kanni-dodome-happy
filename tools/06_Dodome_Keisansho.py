"""
計算書出力（Markdown + PNG）。矢板安定計算.md 6.2章に対応。

土圧分布図・S図・M図を含め、検査時に計算過程を追える形式で出力する。
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 日本語グリフ対応フォント
matplotlib.rcParams["font.family"] = [
    "Yu Gothic", "Meiryo", "MS Gothic",
    "Noto Sans CJK JP", "IPAexGothic", "TakaoGothic",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False


def _plot_profile(z, values, title, xlabel, out_path, formula=None):
    fig, ax = plt.subplots(figsize=(4, 6))
    ax.plot(values, z, color="black")
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.set_ylabel("深さ z (m)")
    ax.set_title(title)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.grid(True, linewidth=0.3)
    if formula:
        fig.suptitle(formula, fontsize=9, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _plot_moment(z, M, z1, z2, R1, R2, out_path):
    """曲げモーメント図。腹起し位置(z1, z2)に横線を引き、反力R1・R2を数値ラベルで示す。"""
    fig, ax = plt.subplots(figsize=(4, 6))
    ax.plot(M, z, color="black")
    ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.5)

    trans = ax.get_yaxis_transform()  # x: 軸フラクション, y: データ座標
    for wale_z, R, label in ((z1, R1, "R1"), (z2, R2, "R2")):
        ax.axhline(wale_z, color="black", linewidth=0.6, linestyle="--")
        ax.text(
            1.02, wale_z, f"{label}={R:.3f} tf/m",
            transform=trans, color="black", fontsize=8,
            va="center", ha="left", clip_on=False,
        )

    ax.set_xlabel("M (tf*m/m)")
    ax.set_ylabel("深さ z (m)")
    ax.set_title("曲げモーメント図 M")
    ax.grid(True, linewidth=0.3)

    fig.suptitle(
        "M = M(前) + S・Δ\n"
        "（S：せん断力 tf/m　Δ：計算ピッチ 0.01m）",
        fontsize=9, y=1.02,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _plot_earth_pressure(z, p, z1, z2, R1, R2, out_path):
    """側圧分布図。矢板を左側の太線として描き、その右側に荷重（p）の形状を描く。
    腹起し位置(z1, z2)に横線を引き、反力R1・R2を左側に数値ラベルで示す。
    最大値に応じた適切な上限値と目盛りを強制し、matplotlibの勝手な軸変更を防ぐ。"""
    fig, ax = plt.subplots(figsize=(4, 6))

    ax.fill_betweenx(z, 0, p, facecolor="none", edgecolor="black", linewidth=0, hatch="///")
    ax.plot(p, z, color="black", linewidth=1.2)
    ax.axvline(0, color="black", linewidth=4)  # 矢板

    ax.invert_yaxis()

    # 実際のpの最大値に応じてスケールする（余白15%）。目盛りはmatplotlibの
    # 自動配置に任せる（固定値だと最大値が小さいときにグラフが不自然に細くなるため）。
    max_p = max(p) if p else 1.0
    ax.set_xlim(left=0, right=max_p * 1.15)

    trans = ax.get_yaxis_transform()  # x: 軸フラクション, y: データ座標
    for wale_z, R, label in ((z1, R1, "R1"), (z2, R2, "R2")):
        ax.axhline(wale_z, color="black", linewidth=0.6, linestyle="--")
        ax.annotate(
            "", xy=(0, wale_z), xycoords=trans,
            xytext=(-0.22, wale_z), textcoords=trans,
            arrowprops=dict(arrowstyle="-|>", color="black", linewidth=2.5, mutation_scale=25),
            annotation_clip=False,
        )
        ax.text(
            -0.25, wale_z, f"{label}={R:.3f} tf/m",
            transform=trans, color="black", fontsize=8,
            va="center", ha="right", clip_on=False,
        )

    ax.set_xlabel("p (tf/m2)")
    ax.set_ylabel("深さ z (m)")
    ax.set_title("側圧分布 p")
    ax.grid(True, linewidth=0.3)

    fig.suptitle(
        "p = σv・Ka + u\n"
        "（σv：鉛直有効応力 tf/m2　Ka：主働土圧係数　u：水圧 tf/m2）",
        fontsize=9, y=1.02,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _plot_soil_column(dodome, out_path):
    """土質柱状図。水位位置と各層の物性値（γ, γ', Ka）を記入した柱状図。"""
    H = dodome["H"]
    soil_layers = dodome["soil_layers"]
    gl_back = dodome["gl_back"]

    col_left, col_right = 0.0, 1.0
    hatches = ["", "//", "xx", "..", "\\\\"]

    fig, ax = plt.subplots(figsize=(5, 6))

    cum = 0.0
    for i, layer in enumerate(soil_layers):
        top = cum
        cum += layer["thickness"]
        if top >= H:
            break
        bottom = min(cum, H)
        ax.fill_between(
            [col_left, col_right], top, bottom,
            facecolor="white", edgecolor="black", linewidth=0.8,
            hatch=hatches[i % len(hatches)],
        )
        label = (
            f"層厚 {layer['thickness']}m\n"
            f"γ={layer['gamma']}  γ'={layer['gamma_prime']}\n"
            f"Ka={layer['Ka']}"
        )
        if layer.get("gravel_content") is not None:
            label += f"\n礫・玉石混入率 {layer['gravel_content']}%"
        ax.text(col_right + 0.15, (top + bottom) / 2, label, fontsize=8, va="center", color="black")

    if gl_back > 0:
        ax.plot([col_left, col_right], [gl_back, gl_back], color="black", linewidth=1)
        ax.text((col_left + col_right) / 2, gl_back, "▽", color="black",
                 fontsize=14, ha="center", va="bottom")
        ax.text(col_left - 0.1, gl_back, f"背面地下水位 GL-{gl_back}m", color="black",
                 fontsize=8, ha="right", va="center")

    ax.set_xlim(col_left - 1.6, col_right + 1.8)
    ax.invert_yaxis()
    ax.set_ylabel("深さ z (m)")
    ax.set_xticks([])
    ax.set_title("土質柱状図")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _dim_line(ax, x, y0, y1, text, tick_x0):
    """縦方向の寸法線。y0〜y1の区間を両矢印で示し、tick_x0からxまで引出線を引く。"""
    ax.annotate(
        "", xy=(x, y0), xytext=(x, y1),
        arrowprops=dict(arrowstyle="<->", color="black", linewidth=0.7),
    )
    for y in (y0, y1):
        ax.plot([tick_x0, x], [y, y], color="black", linewidth=0.4, linestyle=(0, (2, 2)))
    ax.text(x + 0.08, (y0 + y1) / 2, text, va="center", ha="left", fontsize=8, rotation=90)


def _plot_section(dodome, out_path):
    """検討断面図（模式図）。矢板・腹起し・土質層・水位・上載荷重を寸法線付きで示す。
    水平方向は縮尺なし（入力に掘削幅が無いため模式表示）。"""
    H = dodome["H"]
    z1, z2 = dodome["z1"], dodome["z2"]
    soil_layers = dodome["soil_layers"]
    gl_back = dodome["gl_back"]
    gl_excavation = dodome["gl_excavation"]
    q = dodome["q"]

    half_back = 1.8
    half_exc = 1.8

    fig, ax = plt.subplots(figsize=(7, 6))

    # 矢板（中心の太線）
    ax.plot([0, 0], [0, H], color="black", linewidth=4, zorder=5)

    # 土質層境界（背面側）とラベル
    cum = 0.0
    for layer in soil_layers:
        top = cum
        cum += layer["thickness"]
        if top >= H:
            break
        bottom = min(cum, H)
        ax.plot([-half_back, 0], [top, top], color="black", linewidth=0.5, linestyle="--")
        section_label = (
            f"層厚{layer['thickness']}m γ={layer['gamma']} γ'={layer['gamma_prime']} Ka={layer['Ka']}"
        )
        if layer.get("gravel_content") is not None:
            section_label += f" 混入率{layer['gravel_content']}%"
        ax.text(
            -half_back + 0.05, (top + bottom) / 2,
            section_label,
            fontsize=6.5, va="center",
        )

    # 地表面（背面側）・掘削底面（掘削側）
    ax.plot([-half_back, 0], [0, 0], color="black", linewidth=1.2)
    ax.plot([0, half_exc], [H, H], color="black", linewidth=1.2)
    ax.plot([half_exc, half_exc], [0, H], color="black", linewidth=0.8)
    ax.plot([half_exc, half_exc + 0.3], [0, 0], color="black", linewidth=1.2)

    # 腹起し（z1, z2）
    for wale_z, label in ((z1, "上段"), (z2, "下段")):
        ax.plot([-0.3, 0.3], [wale_z, wale_z], color="black", linewidth=5, zorder=6)
        ax.text(0.35, wale_z, f"{label}腹起し z={wale_z}m", color="black", fontsize=8, va="center")

    # 上載荷重 q
    if q > 0:
        import numpy as _np
        for x in _np.linspace(-half_back + 0.15, -0.15, 5):
            ax.annotate(
                "", xy=(x, 0), xytext=(x, -0.35),
                arrowprops=dict(arrowstyle="->", color="black", linewidth=0.8),
            )
        ax.text(-half_back / 2, -0.45, f"上載荷重 q={q} tf/m2", ha="center", fontsize=8)

    # 水位
    if gl_back > 0:
        ax.plot([-half_back, 0], [gl_back, gl_back], color="black", linestyle="--", linewidth=1)
        ax.text(-half_back, gl_back - 0.06, f"▽背面水位 GL-{gl_back}m", color="black", fontsize=7)
    if gl_excavation > 0:
        ax.plot([0, half_exc], [gl_excavation, gl_excavation], color="black", linestyle="--", linewidth=1)
        ax.text(half_exc, gl_excavation - 0.06, f"▽掘削側水位 GL-{gl_excavation}m", color="black", fontsize=7, ha="right")

    # 寸法線（掘削側の外側にネストして表示。引出し線は掘削境界線から起こす）
    dim_base = half_exc + 0.5
    _dim_line(ax, dim_base, 0, z1, f"z1={z1}m", tick_x0=half_exc)
    _dim_line(ax, dim_base + 0.5, 0, z2, f"z2={z2}m", tick_x0=half_exc)
    _dim_line(ax, dim_base + 1.0, 0, H, f"H={H}m", tick_x0=half_exc)

    ax.invert_yaxis()
    ax.set_xlim(-half_back - 0.5, dim_base + 1.6)
    ax.set_ylim(H + 0.3, -0.7)
    ax.axis("off")
    ax.set_title("検討断面（模式図・水平方向は縮尺なし）")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def generate_report(dodome, output_dir):
    output_dir = Path(output_dir)
    img_dir = output_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    name = dodome["project_name"]

    # 検討断面図・土質柱状図・側圧分布図・S図・M図のプロット生成
    _plot_section(dodome, img_dir / "section.png")
    _plot_soil_column(dodome, img_dir / "soil_column.png")
    _plot_earth_pressure(
        dodome["z"], dodome["p"], dodome["z1"], dodome["z2"],
        dodome["R1"], dodome["R2"], img_dir / "p.png",
    )
    _plot_profile(
        dodome["z"], dodome["S"], "せん断力図 S", "S (tf/m)", img_dir / "s.png",
        formula="S = S(前) + p・Δ　（腹起し位置ではR分を減じる。Δ：計算ピッチ 0.01m）",
    )
    _plot_moment(
        dodome["z"], dodome["M"], dodome["z1"], dodome["z2"],
        dodome["R1"], dodome["R2"], img_dir / "m.png",
    )

    spec = dodome.get("selected_spec")
    if spec:
        judge = "OK" if spec["Z"] >= dodome["Z_req"] else "NG"
        spec_line = (
            f"選定規格: **{spec['name']}**（Z={spec['Z']} cm3/m） "
            f"→ 判定: **{judge}**"
        )
    else:
        spec_line = f"⚠ {dodome.get('selection_warning', '規格選定に失敗しました。')}"

    warnings = dodome.get("warnings", [])
    warning_block = ""
    if warnings:
        warning_block = "\n".join(f"- ⚠ {w}" for w in warnings)
        warning_block = f"\n## 検算\n\n{warning_block}\n"

    md = f"""# 簡易土留 安定計算書 — {name}

## 設計条件

| 項目 | 値 |
|---|---|
| 掘削深 H | {dodome['H']} m |
| 上段腹起し z1 | {dodome['z1']} m |
| 下段腹起し z2 | {dodome['z2']} m |
| 許容曲げ応力度 σa | {dodome['sigma_a']} kgf/cm2 |

## 検討断面

![検討断面](img/section.png)

## 土質柱状図

![土質柱状図](img/soil_column.png)

## 反力

| 項目 | 値 |
|---|---|
| 上段腹起し反力 R1 | {dodome['R1']:.3f} tf/m |
| 下段腹起し反力 R2 | {dodome['R2']:.3f} tf/m |

## 最大曲げモーメントと必要断面係数

| 項目 | 値 |
|---|---|
| 最大曲げモーメント Mmax | {dodome['M_max']:.3f} tf*m/m（z={dodome['z_at_max']:.2f}m） |
| 必要断面係数 Z_req | {dodome['Z_req']:.1f} cm3/m |

{spec_line}
{warning_block}
## 側圧分布図

![側圧分布](img/p.png)

## せん断力図（S図）

![S図](img/s.png)

## 曲げモーメント図（M図）

![M図](img/m.png)
"""

    report_path = output_dir / f"計算書_{name}.md"
    report_path.write_text(md, encoding="utf-8")
    return report_path


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "dodome_data.json"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    with open(input_path, encoding="utf-8") as f:
        dodome = json.load(f)

    path = generate_report(dodome, output_dir)
    print(f"計算書を出力しました: {path}")
