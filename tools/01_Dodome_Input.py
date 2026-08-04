"""
input.json の読込・スキーマ検証・適用範囲チェック。
矢板安定計算.md 1章（適用範囲）・5章（入力仕様）に対応。

対話的な入力プロンプトは持たない。CLI/JSON直接編集が確定方針のため、
このモジュールは「読んで検証するだけ」に徹する。
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_H = 3.5


class ApplicabilityError(Exception):
    """適用範囲外の入力を示す。計算を実行せず終了させるための例外。"""


@dataclass
class SoilLayer:
    thickness: float
    gamma: float
    gamma_prime: float
    Ka: float
    gravel_content: float | None = None  # 礫・玉石混入率(%)。任意の記録用項目で計算には使わない。


@dataclass
class DodomeInput:
    project_name: str
    H: float
    delta: float
    z1: float
    z2: float
    soil_layers: list
    gl_back: float
    gl_excavation: float
    q: float
    sigma_a: float
    yaita_spec_file: str


def load_input(path) -> DodomeInput:
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return parse_input(raw)


def parse_input(raw: dict) -> DodomeInput:
    """input.json相当の辞書からDodomeInputを構築し、適用範囲チェックまで行う。
    GUI（01_Dodome_Input_GUI.py）がファイルに保存する前の内容を検証する際にも使う。"""

    exc = raw["excavation"]
    wales = raw["wales"]
    water = raw["water"]
    surcharge = raw["surcharge"]
    material = raw["material"]

    H = float(exc["H"])
    delta = float(exc.get("delta", 0.01))
    z1 = float(wales["z1"])
    z2 = float(wales["z2"])

    layers = [
        SoilLayer(
            thickness=float(layer["thickness"]),
            gamma=float(layer["gamma"]),
            gamma_prime=float(layer["gamma_prime"]),
            Ka=float(layer["Ka"]),
            gravel_content=(
                float(layer["gravel_content"]) if "gravel_content" in layer else None
            ),
        )
        for layer in raw["soil_layers"]
    ]

    data = DodomeInput(
        project_name=raw.get("project_name", "無題"),
        H=H,
        delta=delta,
        z1=z1,
        z2=z2,
        soil_layers=layers,
        gl_back=float(water["gl_back"]),
        gl_excavation=float(water["gl_excavation"]),
        q=float(surcharge["q"]),
        sigma_a=float(material["sigma_a"]),
        yaita_spec_file=material.get("yaita_spec_file", "yaita_spec.json"),
    )

    _check_applicability(data)
    return data


def _check_applicability(data: DodomeInput) -> None:
    """矢板安定計算.md 1章の適用範囲チェック。外れる場合は計算せず例外を送出する。"""

    if data.H > MAX_H:
        raise ApplicabilityError(
            f"掘削深 H={data.H}m は適用範囲（{MAX_H}m程度まで）を超えています。"
            "本ツールでは計算できません。"
        )

    if not (0 <= data.z1 < data.z2 < data.H):
        raise ApplicabilityError(
            f"腹起し配置が不正です（0 <= z1 < z2 < H である必要があります）。"
            f" z1={data.z1}, z2={data.z2}, H={data.H}"
        )

    layer_total = sum(layer.thickness for layer in data.soil_layers)
    if layer_total < data.H:
        raise ApplicabilityError(
            f"土質層の層厚合計（{layer_total}m）が掘削深 H（{data.H}m）に"
            "達していません。"
        )


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "input.json"
    try:
        result = load_input(target)
        print(f"読込OK: {result.project_name} (H={result.H}m)")
    except ApplicabilityError as e:
        print(f"[適用範囲外] {e}", file=sys.stderr)
        sys.exit(1)
