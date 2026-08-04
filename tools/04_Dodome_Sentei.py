"""
矢板規格選定（矢板安定計算.md 7章・7.1章）。

必要断面係数 Z_req を上回る最小の Z を持つ規格を、外部JSON（yaita_spec.json）
から選定する。規格値はソースコードにハードコードしない。
"""

import json
import sys


class NoSpecFoundError(Exception):
    """Z_reqを満たす規格が見つからない場合。"""


def select_spec(z_req, spec_file):
    with open(spec_file, encoding="utf-8") as f:
        spec_data = json.load(f)

    candidates = [s for s in spec_data["specs"] if s["Z"] >= z_req]
    if not candidates:
        raise NoSpecFoundError(
            f"必要断面係数 Z_req={z_req:.1f} cm3/m を満たす規格が"
            f"{spec_file} 内に見つかりません。"
        )

    return min(candidates, key=lambda s: s["Z"])


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "dodome_data.json"

    with open(input_path, encoding="utf-8") as f:
        dodome = json.load(f)

    try:
        selected = select_spec(dodome["Z_req"], dodome["yaita_spec_file"])
        dodome["selected_spec"] = selected
        print(f"選定規格: {selected['name']} (Z={selected['Z']} cm3/m)")
    except NoSpecFoundError as e:
        dodome["selected_spec"] = None
        dodome["selection_warning"] = str(e)
        print(f"[警告] {e}", file=sys.stderr)

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(dodome, f, ensure_ascii=False, indent=2)
