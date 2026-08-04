"""
側圧分布計算（矢板安定計算.md 4.1〜4.2章）。

天端から掘削底面までを delta（既定0.01m）刻みのセルに分解し、各セルで
・所属する土質層から gamma / gamma_prime / Ka を判定
・地下水位（背面）より上か下かで gamma か gamma_prime を加算し有効鉛直応力 sigma_v を累加
・残留水圧 u（背面水位と掘削側水位の差分水頭）を算出
・側圧強度 p = sigma_v * Ka + u
を求める、全セル共通の一様な数値積分ループ。層数が増えても構造は変わらない
（0.2章の設計原則）。層境・水位境で式そのものを切り替える分岐は書かない。
"""

import json
import sys
from pathlib import Path

GAMMA_W = 1.0  # tf/m3, 水の単位体積重量（固定値）

# ファイル名が数字始まりのため importlib.util で直接ロードする
import importlib.util


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dodome_input = _load_module("dodome_input", "01_Dodome_Input.py")


def _layer_at(depth, soil_layers):
    """深さdepthが属する土質層を返す（層境界の判定のみ。式は全層共通）。"""
    cum = 0.0
    for layer in soil_layers:
        cum += layer.thickness
        if depth <= cum + 1e-9:
            return layer
    return soil_layers[-1]


def compute_doatsu(data):
    N = round(data.H / data.delta)
    z_list = []
    p_list = []
    sigma_v_list = []
    u_list = []

    sigma_v = data.q  # 初期値として上載荷重をセット（4.2章）

    for i in range(N + 1):
        z = i * data.delta
        layer = _layer_at(z, data.soil_layers)

        if i > 0:
            gamma_use = layer.gamma if z <= data.gl_back else layer.gamma_prime
            sigma_v += gamma_use * data.delta

        u = GAMMA_W * (max(0.0, z - data.gl_back) - max(0.0, z - data.gl_excavation))
        
        # 側圧強度の算出（一時的なガードは行わず、物理・数式通りに算出する）
        p = sigma_v * layer.Ka + u

        z_list.append(z)
        sigma_v_list.append(sigma_v)
        u_list.append(u)
        p_list.append(p)

    return {
        "project_name": data.project_name,
        "H": data.H,
        "delta": data.delta,
        "z1": data.z1,
        "z2": data.z2,
        "sigma_a": data.sigma_a,
        "yaita_spec_file": data.yaita_spec_file,
        "soil_layers": [
            {
                "thickness": layer.thickness,
                "gamma": layer.gamma,
                "gamma_prime": layer.gamma_prime,
                "Ka": layer.Ka,
                **(
                    {"gravel_content": layer.gravel_content}
                    if layer.gravel_content is not None
                    else {}
                ),
            }
            for layer in data.soil_layers
        ],
        "gl_back": data.gl_back,
        "gl_excavation": data.gl_excavation,
        "q": data.q,
        "z": z_list,
        "p": p_list,
        "sigma_v": sigma_v_list,
        "u": u_list,
    }


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "input.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "doatsu_data.json"

    data = dodome_input.load_input(input_path)
    result = compute_doatsu(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"側圧分布を計算しました: {output_path}")
