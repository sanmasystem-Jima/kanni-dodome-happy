"""
統括スクリプト。input.json から計算書までを一括実行する。

01_Dodome_Input -> 02_Dodome_Doatsu -> 03_Dodome_Danmenryoku
-> 04_Dodome_Sentei -> 06_Dodome_Keisansho

各段のJSON成果物はディスクに残す（デバッグ・後続ツールからの再利用のため）。
"""

import importlib.util
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent / "tools"


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, TOOLS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(input_path, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    m01 = _load_module("dodome_input", "01_Dodome_Input.py")
    m02 = _load_module("dodome_doatsu", "02_Dodome_Doatsu.py")
    m03 = _load_module("dodome_danmenryoku", "03_Dodome_Danmenryoku.py")
    m04 = _load_module("dodome_sentei", "04_Dodome_Sentei.py")
    m06 = _load_module("dodome_keisansho", "06_Dodome_Keisansho.py")

    try:
        data = m01.load_input(input_path)
    except m01.ApplicabilityError as e:
        print(f"[適用範囲外] {e}", file=sys.stderr)
        sys.exit(1)

    doatsu = m02.compute_doatsu(data)
    (output_dir / "doatsu_data.json").write_text(
        json.dumps(doatsu, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    dodome = m03.compute_danmenryoku(doatsu)
    for w in dodome["warnings"]:
        print(f"[警告] {w}", file=sys.stderr)

    try:
        dodome["selected_spec"] = m04.select_spec(dodome["Z_req"], dodome["yaita_spec_file"])
    except m04.NoSpecFoundError as e:
        dodome["selected_spec"] = None
        dodome["selection_warning"] = str(e)
        print(f"[警告] {e}", file=sys.stderr)

    (output_dir / "dodome_data.json").write_text(
        json.dumps(dodome, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report_path = m06.generate_report(dodome, output_dir)
    print(f"完了: {report_path}")
    return report_path


def _select_input_path() -> str:
    """コマンドライン引数が無い場合、ダイアログでinput.jsonを選ばせる
    （バッチファイルからダブルクリック起動する運用のため）。"""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="計算する input.json を選択",
        filetypes=[("JSON", "*.json")],
        initialdir=Path(__file__).parent,
    )
    root.destroy()
    return path


def _select_output_dir(default_dir: Path) -> Path:
    """コマンドライン引数が無い場合、ダイアログで出力先フォルダを選ばせる。
    キャンセル時は default_dir（input.jsonと同じ場所のoutput）を使う。"""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askdirectory(
        title="計算書の保存先フォルダを選択（キャンセルで既定のoutputフォルダ）",
        initialdir=default_dir if default_dir.exists() else default_dir.parent,
    )
    root.destroy()
    return Path(path) if path else default_dir


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = _select_input_path()
        if not input_path:
            print("入力ファイルが選択されなかったため終了します。")
            sys.exit(0)

    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = _select_output_dir(Path(input_path).parent / "output")

    run(input_path, output_dir)

    try:
        import os
        os.startfile(output_dir)  # Windows専用。他OSでは黙って無視する。
    except AttributeError:
        pass
