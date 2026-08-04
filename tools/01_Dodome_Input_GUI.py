"""
条件入力GUI（矢板安定計算.md 5章）。tkinter製。

役割は input.json の作成・保存・（保存前の）検証のみ。安定計算の実行は
行わない（計算は 00_Dodome_Tougou.py を別途CLIで実行する運用のため）。
"""

import importlib.util
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

DEFAULT_DELTA = 0.01
HERE = Path(__file__).parent

# 土質タイプ別の目安値（γ, γ', Ka）。あくまで概略検討・初期入力の参考値であり、
# 実際の地盤調査結果（土質試験・N値等）がある場合はそちらを優先すること。
#
# 礫質土: 単位体積重量は道路橋示方書系の目安値（自然地盤・砂及び砂礫 18〜20kN/m3）、
# Kaは擁壁工指針の裏込め土内部摩擦角（礫質土 φ=35°）から算出。国交省地方整備局
# 設計要領に典拠あり（https://www.cbr.mlit.go.jp/kawatomizu/kouzou/pdf/08_04sekkeiippan2.pdf）。
#
# 玉石まじり砂質土: 公的な目安値は存在しない（同資料も「混合割合及び状態に応じて
# 適当な値を定める」としている）。以下は礫質土（φ=35°→Ka=0.27）を土質分類上の
# 目安として流用し、玉石分だけ単位体積重量を割増した「たたき台」の値であり、
# 出典に基づく値ではない。混入率欄で判断根拠を残した上で必ず調整すること。
SOIL_TYPE_REFERENCE = [
    ("(手動入力)", None),
    ("粘性土（非常に軟らかい, N値<2）", {"gamma": 1.6, "gamma_prime": 0.7, "Ka": 0.50}),
    ("粘性土（軟らかい, N値2〜4）", {"gamma": 1.7, "gamma_prime": 0.8, "Ka": 0.50}),
    ("粘性土（中位, N値4〜8）", {"gamma": 1.8, "gamma_prime": 0.9, "Ka": 0.45}),
    ("砂質土（ゆるい, N値<10）", {"gamma": 1.7, "gamma_prime": 0.9, "Ka": 0.40}),
    ("砂質土（中位, N値10〜30）", {"gamma": 1.8, "gamma_prime": 1.0, "Ka": 0.33}),
    ("砂質土（密, N値>30）", {"gamma": 1.9, "gamma_prime": 1.1, "Ka": 0.27}),
    ("礫質土（砂礫）", {"gamma": 2.0, "gamma_prime": 1.1, "Ka": 0.27}),
    ("玉石まじり砂質土（目安なし・たたき台）", {"gamma": 2.1, "gamma_prime": 1.2, "Ka": 0.27}),
    ("ローム", {"gamma": 1.4, "gamma_prime": 0.6, "Ka": 0.45}),
    ("埋土（雑多）", {"gamma": 1.7, "gamma_prime": 0.9, "Ka": 0.45}),
]
SOIL_TYPE_LOOKUP = dict(SOIL_TYPE_REFERENCE)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dodome_input = _load_module("dodome_input", "01_Dodome_Input.py")


class SoilLayerRow:
    """土質層1行分の入力（層厚・単位体積重量・水中単位体積重量・主働土圧係数Ka）。

    上段：土質タイプを選ぶと目安値(γ, γ', Ka)を自動入力するコンボボックス。
    下段：層厚と実際に計算へ使われる数値項目（選択後も手で微調整できる）。"""

    FIELDS = [
        ("thickness", "層厚 (m)"),
        ("gamma", "単位体積重量(γ) (tf/m3)"),
        ("gamma_prime", "水中単位体積重量(γ') (tf/m3)"),
        ("Ka", "主働土圧係数(Ka)"),
        ("gravel_content", "礫・玉石混入率 (%) 任意"),
    ]

    def __init__(self, parent, on_delete):
        self.frame = ttk.Frame(parent, relief="groove", borderwidth=1)
        self.vars = {}

        top_row = ttk.Frame(self.frame)
        top_row.pack(fill="x", padx=4, pady=(4, 2))
        ttk.Label(top_row, text="土質タイプ（目安値）").pack(side="left")
        self.soil_type = tk.StringVar(value=SOIL_TYPE_REFERENCE[0][0])
        combo = ttk.Combobox(
            top_row,
            textvariable=self.soil_type,
            values=[name for name, _ in SOIL_TYPE_REFERENCE],
            state="readonly",
            width=30,
        )
        combo.pack(side="left", padx=(6, 0))
        combo.bind("<<ComboboxSelected>>", self._on_soil_type_selected)
        del_btn = ttk.Button(top_row, text="この層を削除", command=lambda: on_delete(self))
        del_btn.pack(side="right")

        values_row = ttk.Frame(self.frame)
        values_row.pack(fill="x", padx=4, pady=(0, 4))
        for col, (key, label) in enumerate(self.FIELDS):
            ttk.Label(values_row, text=label).grid(row=0, column=col * 2, padx=(0, 2), pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(values_row, textvariable=var, width=8)
            entry.grid(row=0, column=col * 2 + 1, padx=(0, 10))
            self.vars[key] = var

    def _on_soil_type_selected(self, event=None):
        values = SOIL_TYPE_LOOKUP.get(self.soil_type.get())
        if values is None:
            return  # 「(手動入力)」選択時は何もしない
        for key in ("gamma", "gamma_prime", "Ka"):
            self.vars[key].set(str(values[key]))

    def get(self) -> dict:
        return {key: var.get() for key, var in self.vars.items()}

    def set(self, values: dict):
        for key, var in self.vars.items():
            if key in values:
                var.set(str(values[key]))

    def destroy(self):
        self.frame.destroy()


class DodomeInputGUI:
    def __init__(self, root):
        self.root = root
        root.title("簡易土留Happy - 条件入力")

        self.project_name = tk.StringVar(value="無題")
        self.H = tk.StringVar()
        self.z1 = tk.StringVar()
        self.z2 = tk.StringVar()
        self.gl_back = tk.StringVar()
        self.gl_excavation = tk.StringVar()
        self.q = tk.StringVar()
        self.sigma_a = tk.StringVar(value="1800")
        self.yaita_spec_file = tk.StringVar(value="yaita_spec.json")

        self.layer_rows = []

        self._build_ui()
        self.add_layer_row()

    # ---- UI構築 ----

    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="プロジェクト名").pack(side="left")
        ttk.Entry(top, textvariable=self.project_name, width=30).pack(side="left", padx=6)

        exc = ttk.LabelFrame(self.root, text="掘削条件")
        exc.pack(fill="x", **pad)
        self._labeled_entry(exc, "掘削深 H (m)", self.H, 0, 0)
        ttk.Label(exc, text=f"計算ピッチ Δ = {DEFAULT_DELTA} m 固定").grid(
            row=0, column=2, padx=6
        )

        wales = ttk.LabelFrame(self.root, text="支保工（腹起し、天端からの深さ）")
        wales.pack(fill="x", **pad)
        self._labeled_entry(wales, "上段 z1 (m)", self.z1, 0, 0)
        self._labeled_entry(wales, "下段 z2 (m)", self.z2, 0, 2)

        self.layers_frame = ttk.LabelFrame(self.root, text="土質層（上から順）")
        self.layers_frame.pack(fill="x", **pad)
        ttk.Label(
            self.layers_frame,
            text="※土質タイプの値は概略検討用の目安です。実際の地盤調査結果があればそちらを優先してください。",
            foreground="#555555",
        ).pack(anchor="w", padx=4, pady=(4, 0))
        self.layers_list_frame = ttk.Frame(self.layers_frame)
        self.layers_list_frame.pack(fill="x")
        ttk.Button(self.layers_frame, text="層を追加", command=self.add_layer_row).pack(
            anchor="w", padx=4, pady=4
        )

        water = ttk.LabelFrame(self.root, text="水位（天端からの深さ）")
        water.pack(fill="x", **pad)
        self._labeled_entry(water, "背面地下水位 (m)", self.gl_back, 0, 0)
        self._labeled_entry(water, "掘削側水位 (m)", self.gl_excavation, 0, 2)

        surcharge = ttk.LabelFrame(self.root, text="上載荷重")
        surcharge.pack(fill="x", **pad)
        self._labeled_entry(surcharge, "過載荷重 q (tf/m2)", self.q, 0, 0)

        material = ttk.LabelFrame(self.root, text="部材")
        material.pack(fill="x", **pad)
        self._labeled_entry(material, "許容曲げ応力度 σa (kgf/cm2)", self.sigma_a, 0, 0)
        self._labeled_entry(material, "矢板規格表ファイル", self.yaita_spec_file, 0, 2, width=24)

        btns = ttk.Frame(self.root)
        btns.pack(fill="x", **pad)
        ttk.Button(btns, text="読込...", command=self.load_file).pack(side="left", padx=4)
        ttk.Button(btns, text="検証", command=self.validate).pack(side="left", padx=4)
        ttk.Button(btns, text="保存...", command=self.save_file).pack(side="left", padx=4)

    def _labeled_entry(self, parent, label, var, row, col, width=10):
        ttk.Label(parent, text=label).grid(row=row, column=col, padx=6, pady=4, sticky="e")
        ttk.Entry(parent, textvariable=var, width=width).grid(
            row=row, column=col + 1, padx=6, pady=4, sticky="w"
        )

    # ---- 土質層の行操作 ----

    def add_layer_row(self):
        row = SoilLayerRow(self.layers_list_frame, self.remove_layer_row)
        row.frame.pack(fill="x", pady=2)
        self.layer_rows.append(row)

    def remove_layer_row(self, row):
        if len(self.layer_rows) <= 1:
            messagebox.showwarning("警告", "土質層は最低1層必要です。")
            return
        row.destroy()
        self.layer_rows.remove(row)

    # ---- データ変換 ----

    def _layer_to_dict(self, row) -> dict:
        """土質層1行をinput.json用の辞書に変換する。混入率は任意項目のため、
        空欄の場合はキー自体を省略する（計算には使わない記録用の値）。"""
        values = row.get()
        layer = {
            "thickness": float(values["thickness"]),
            "gamma": float(values["gamma"]),
            "gamma_prime": float(values["gamma_prime"]),
            "Ka": float(values["Ka"]),
        }
        gravel_content = values.get("gravel_content", "").strip()
        if gravel_content:
            layer["gravel_content"] = float(gravel_content)
        return layer

    def _to_raw_dict(self) -> dict:
        try:
            return {
                "project_name": self.project_name.get(),
                "excavation": {
                    "H": float(self.H.get()),
                    "delta": DEFAULT_DELTA,
                },
                "wales": {
                    "z1": float(self.z1.get()),
                    "z2": float(self.z2.get()),
                },
                "soil_layers": [self._layer_to_dict(row) for row in self.layer_rows],
                "water": {
                    "gl_back": float(self.gl_back.get()),
                    "gl_excavation": float(self.gl_excavation.get()),
                },
                "surcharge": {"q": float(self.q.get())},
                "material": {
                    "sigma_a": float(self.sigma_a.get()),
                    "yaita_spec_file": self.yaita_spec_file.get(),
                },
            }
        except ValueError as e:
            raise ValueError(f"数値項目に不正な値があります: {e}")

    def _from_raw_dict(self, raw: dict):
        self.project_name.set(raw.get("project_name", "無題"))
        exc = raw["excavation"]
        self.H.set(str(exc["H"]))
        wales = raw["wales"]
        self.z1.set(str(wales["z1"]))
        self.z2.set(str(wales["z2"]))

        for row in list(self.layer_rows):
            row.destroy()
        self.layer_rows.clear()
        for layer in raw["soil_layers"]:
            self.add_layer_row()
            self.layer_rows[-1].set(layer)  # 混入率が無い層は空欄のまま（新規行は初期値が空）
        if not self.layer_rows:
            self.add_layer_row()

        water = raw["water"]
        self.gl_back.set(str(water["gl_back"]))
        self.gl_excavation.set(str(water["gl_excavation"]))
        self.q.set(str(raw["surcharge"]["q"]))
        material = raw["material"]
        self.sigma_a.set(str(material["sigma_a"]))
        self.yaita_spec_file.set(material.get("yaita_spec_file", "yaita_spec.json"))

    # ---- ボタン動作 ----

    def validate(self):
        try:
            raw = self._to_raw_dict()
            data = dodome_input.parse_input(raw)
        except ValueError as e:
            messagebox.showerror("入力エラー", str(e))
            return
        except dodome_input.ApplicabilityError as e:
            messagebox.showwarning("適用範囲外", str(e))
            return
        except KeyError as e:
            messagebox.showerror("入力エラー", f"項目が不足しています: {e}")
            return

        messagebox.showinfo(
            "検証OK",
            f"適用範囲内です。\nH={data.H}m, z1={data.z1}m, z2={data.z2}m, "
            f"層数={len(data.soil_layers)}",
        )

    def save_file(self):
        try:
            raw = self._to_raw_dict()
        except ValueError as e:
            messagebox.showerror("入力エラー", str(e))
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="input.json",
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("保存完了", f"保存しました:\n{path}")

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            self._from_raw_dict(raw)
        except (KeyError, json.JSONDecodeError) as e:
            messagebox.showerror("読込エラー", f"input.jsonの形式が不正です: {e}")


def main():
    root = tk.Tk()
    DodomeInputGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
