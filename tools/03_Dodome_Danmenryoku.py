"""
反力・せん断力図(S図)・曲げモーメント図(M図)の計算（矢板安定計算.md 4.3〜4.7章）。

矢板は上下端とも自由端、腹起し2段のみを支点とする静定構造（両端に突出部を
持つ単純ばり）。根入れ部の抵抗は一切考慮しない（0.1章の禁止事項）。

手順:
  1. 反力 R1, R2 をつり合い式（ΣV=0, ΣM=0）から先に確定する（4.5章）
  2. 上端 S=0, M=0 から1cmごとに累加し、腹起し位置のセルで反力を減じる（4.3〜4.4章）
  3. 下端で S≈0, M≈0 になることを検算する（4.7章）
  4. |M| の配列最大値を Mmax とする（位置の事前分岐はしない、4.6章）
"""

import json
import sys

TOL_S = 1e-6
TOL_M = 1e-6


def _nearest_index(z_list, z_target):
    return min(range(len(z_list)), key=lambda i: abs(z_list[i] - z_target))


def compute_danmenryoku(doatsu):
    z = doatsu["z"]
    p = doatsu["p"]
    delta = doatsu["delta"]
    z1, z2 = doatsu["z1"], doatsu["z2"]

    # 4.5章: 反力の算出（先に確定させる）。
    # S図の累加が i=1..N の右端リーマン和であることに合わせ、ここも同じ範囲・
    # 同じ重みで積分する（範囲がずれると下端でS,Mが0に収束しなくなる）。
    p_total = sum(p[i] * delta for i in range(1, len(z)))
    moment_about_z1 = sum(p[i] * delta * (z[i] - z1) for i in range(1, len(z)))
    R2 = moment_about_z1 / (z2 - z1)
    R1 = p_total - R2

    idx_z1 = _nearest_index(z, z1)
    idx_z2 = _nearest_index(z, z2)

    # 4.3〜4.4章: S図・M図を上端から累加
    S = [0.0] * len(z)
    M = [0.0] * len(z)
    s_running = 0.0
    m_running = 0.0
    for i in range(len(z)):
        if i > 0:
            s_running += p[i] * delta
        if i == idx_z1:
            s_running -= R1
        if i == idx_z2:
            s_running -= R2
        S[i] = s_running

        if i > 0:
            m_running += S[i] * delta
        M[i] = m_running

    # 4.7章: 検算
    warnings = []
    if abs(S[-1]) > TOL_S:
        warnings.append(f"下端のS={S[-1]:.6f}が0に収束していません（許容誤差{TOL_S}）")
    if abs(M[-1]) > TOL_M:
        warnings.append(f"下端のM={M[-1]:.6f}が0に収束していません（許容誤差{TOL_M}）")

    # 4.6章: 最大曲げモーメント（配列の絶対値最大探索のみ、位置の事前分岐はしない）
    idx_max = max(range(len(M)), key=lambda i: abs(M[i]))
    M_max = M[idx_max]
    z_at_max = z[idx_max]

    Z_req = abs(M_max) * 100000 / doatsu["sigma_a"]  # 3.1章の式

    return {
        "project_name": doatsu["project_name"],
        "H": doatsu["H"],
        "z1": z1,
        "z2": z2,
        "sigma_a": doatsu["sigma_a"],
        "yaita_spec_file": doatsu["yaita_spec_file"],
        "soil_layers": doatsu["soil_layers"],
        "gl_back": doatsu["gl_back"],
        "gl_excavation": doatsu["gl_excavation"],
        "q": doatsu["q"],
        "R1": R1,
        "R2": R2,
        "M_max": M_max,
        "z_at_max": z_at_max,
        "Z_req": Z_req,
        "z": z,
        "p": p,
        "S": S,
        "M": M,
        "warnings": warnings,
    }


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "doatsu_data.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "dodome_data.json"

    with open(input_path, encoding="utf-8") as f:
        doatsu = json.load(f)

    result = compute_danmenryoku(doatsu)

    for w in result["warnings"]:
        print(f"[警告] {w}", file=sys.stderr)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(
        f"R1={result['R1']:.3f} tf/m, R2={result['R2']:.3f} tf/m, "
        f"Mmax={result['M_max']:.3f} tf*m/m (z={result['z_at_max']:.2f}m), "
        f"Zreq={result['Z_req']:.1f} cm3/m"
    )
