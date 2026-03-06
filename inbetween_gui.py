"""アニメーション中割り GUI アプリケーション。

tkinter を使い、2 枚のキーフレームにストロークを描画して
中割りアニメーションを生成する。

操作方法:
  - Mode 0（デフォルト）: ドラッグで線を描く
  - Mode 1: クリックで点を置いてストロークを作成
  - 左ボタン押下: 新しいストローク開始 / 点追加
  - 左ドラッグ: ストローク描画（Mode 0）
  - 左ボタン離す: ストロークラベル表示（Mode 0）
  - 右ボタン: ストロークラベル表示 / 次のストローク開始（Mode 1）
  - 「補間」ボタン: 各ストロークを PCHIP 補間で描画
  - 「中割り」ボタン: 2 枚のキーフレーム間をアニメーション
  - 「自動中割り」ボタン: ML 対応を使った自動中割り
  - 「消去」ボタン: 全ストロークを削除
"""

from __future__ import annotations

import time
import tkinter
from typing import Any

import numpy as np
import numpy.typing as npt
from scipy import interpolate

from conbshapecontex import compute_shape_context
from matchingnetwork import solve_min_cost_flow
from recovery import load_keyframes, resample_strokes
from stroke_correspond import (
    build_match_matrix,
    run_auto_correspondence_pipeline,
)

# 中割りアニメーションの補間点数
_INTERPOLATION_STEPS = 30
# アニメーションのフレーム数
_ANIMATION_FRAMES = 100
# キャンバスの一辺のピクセル数
_CANVAS_SIZE = 256


def _interpolate_stroke(t: float, points: list[list[float]]) -> list[float]:
    """PCHIP 補間でストローク上のパラメータ t に対応する点を返す。

    Args:
        t: 0.0 〜 1.0 のパラメータ。
        points: ストロークの制御点リスト（各要素は [x, y]）。

    Returns:
        [x, y] 形式の補間結果。
    """
    x = np.array(points)[:, 0]
    y = np.array(points)[:, 1]
    if len(x) > 2:
        ts = np.linspace(0.0, 1.0, len(x))
        return [float(interpolate.PchipInterpolator(ts, x)(t)),
                float(interpolate.PchipInterpolator(ts, y)(t))]
    # 制御点が 2 点のみの場合は線形補間
    return [float(x[0] + t * (x[1] - x[0])),
            float(y[0] + t * (y[1] - y[0]))]


def _detect_dominant_points_recursive(
    line: npt.NDArray[np.float64],
    result: list[npt.NDArray[np.float64]],
) -> None:
    """二分割法で優勢点（Dominant Points）を再帰的に検出する。

    端点を結ぶ直線から最も遠い点を優勢点として追加し、
    その点を境に再帰的に探索を続ける。
    最大距離が閾値（弦長の 1/50）以下になったら再帰を終了する。

    Args:
        line: shape (N, 3) の配列。各行は [x, y, original_index]。
        result: 優勢点を追加していくリスト（破壊的変更）。
    """
    if len(line) <= 1:
        return

    a = line[-1, 1] - line[0, 1]
    b = line[0, 0] - line[-1, 0]
    c = line[-1, 0] * line[0, 1] - line[0, 0] * line[-1, 1]
    chord_len = np.sqrt(a * a + b * b)

    if chord_len == 0.0:
        return

    dist = np.abs(a * line[:, 0] + b * line[:, 1] + c) / chord_len

    if dist.max() > chord_len / 50.0:
        max_idx = int(np.argmax(dist))
        result.append(line[max_idx])
        _detect_dominant_points_recursive(line[:max_idx], result)
        _detect_dominant_points_recursive(line[max_idx:-1], result)


def extract_dominant_points(
    line: list[list[float]],
) -> npt.NDArray[np.float64]:
    """二分割法でストロークの優勢点を検出し、元の順序で返す。

    始点と終点は必ず含まれる。内部の優勢点は元のインデックス順に並べ直す。

    Args:
        line: [x, y] 座標のリスト。

    Returns:
        shape (K, 3) の配列。各行は [x, y, original_index]。
    """
    pts = np.array(line, dtype=np.float64)
    # 元のインデックスを 3 列目として追加
    indexed = np.concatenate((pts, np.arange(len(pts)).reshape(-1, 1)), axis=1)

    dominant: list[npt.NDArray[np.float64]] = []
    _detect_dominant_points_recursive(indexed, dominant)

    if dominant:
        domi = np.array(dominant)
        order = domi[:, -1].argsort()
        domi = domi[order]
        return np.vstack((indexed[0], domi, indexed[-1]))
    else:
        return np.vstack((indexed[0], indexed[-1]))


class InbetweenApp:
    """アニメーション中割りアプリケーションクラス。

    3 つの tkinter Canvas を持ち、key1（左）・INBET（中央）・key2（右）を管理する。
    ストロークの描画、補間表示、中割りアニメーションを提供する。
    """

    def __init__(self, root: tkinter.Tk) -> None:
        """アプリケーションを初期化してウィジェットを構築する。

        Args:
            root: tkinter のルートウィンドウ。
        """
        self.root = root
        self.root.title("Inbetween Tool")

        # 描画モード: 0 = ドラッグで線、1 = クリックで点
        self.mode: int = 0
        # ドラッグ中の前の座標
        self._prev_x: int = 0
        self._prev_y: int = 0

        self._setup_canvases()
        self._setup_buttons()
        self._bind_events()

    # ------------------------------------------------------------------
    # ウィジェット構築
    # ------------------------------------------------------------------

    def _setup_canvases(self) -> None:
        """3 つの Canvas（key1・INBET・key2）を生成してレイアウトする。"""
        size = _CANVAS_SIZE

        self.key1_canvas = tkinter.Canvas(self.root, width=size, height=size)
        self.key1_canvas.strokes: list[list[list[int]]] = []
        self.key1_canvas.pack(side="left")
        self.key1_canvas.create_rectangle(0, 0, size, size, fill="#ffffff")

        self.inbet_canvas = tkinter.Canvas(self.root, width=size, height=size)
        self.inbet_canvas.pack(side="left")
        self.inbet_canvas.create_rectangle(0, 0, size, size, fill="#ffffff")

        self.key2_canvas = tkinter.Canvas(self.root, width=size, height=size)
        self.key2_canvas.strokes: list[list[list[int]]] = []
        self.key2_canvas.pack(side="left")
        self.key2_canvas.create_rectangle(0, 0, size, size, fill="#ffffff")

    def _setup_buttons(self) -> None:
        """ボタンとスライダーを生成してレイアウトする。"""
        btn_interp = tkinter.Button(
            self.root, text="補間", command=self._on_interpolate, bg="#5998ff"
        )
        btn_interp.pack(side=tkinter.RIGHT)

        btn_inbet = tkinter.Button(
            self.root, text="中割り", command=self._on_inbetween, bg="#f78e80"
        )
        btn_inbet.pack(side=tkinter.RIGHT)

        btn_del = tkinter.Button(self.root, text="消去", command=self._on_delete)
        btn_del.pack(side=tkinter.RIGHT)

        btn_auto = tkinter.Button(
            self.root, text="自動中割り", command=self._on_auto_inbetween
        )
        btn_auto.pack(side=tkinter.RIGHT)

        self.mode_scale = tkinter.Scale(
            self.root,
            label="Mode",
            orient="h",
            from_=0,
            to=1,
            command=self._on_mode_change,
        )
        self.mode_scale.pack()

    def _bind_events(self) -> None:
        """各 Canvas にマウスイベントをバインドする。"""
        for canvas in (self.key1_canvas, self.key2_canvas):
            canvas.bind("<Button-1>", lambda e, c=canvas: self._on_press(e, c))
            canvas.bind("<Button1-Motion>", lambda e, c=canvas: self._on_drag(e, c))
            canvas.bind("<ButtonRelease-1>", lambda e, c=canvas: self._on_release(e, c))
            canvas.bind("<Button-3>", lambda e, c=canvas: self._on_right_click(e, c))

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_mode_change(self, _value: Any) -> None:
        """スライダー変更時にモードを更新する。"""
        self.mode = self.mode_scale.get()

    def _on_press(self, event: tkinter.Event, canvas: tkinter.Canvas) -> None:
        """左ボタン押下: Mode 0 では新ストローク開始、Mode 1 では点追加。"""
        if self.mode == 1:
            if len(canvas.strokes) == 0:
                canvas.strokes.append([])
            self._add_point(event, canvas)
        elif self.mode == 0:
            self._prev_x = event.x
            self._prev_y = event.y
            canvas.strokes.append([])

    def _on_drag(self, event: tkinter.Event, canvas: tkinter.Canvas) -> None:
        """左ドラッグ: Mode 0 でストロークを描画する。"""
        if self.mode == 0:
            x, y = event.x, event.y
            canvas.create_line(
                self._prev_x, self._prev_y, x, y,
                tags="draw", fill="#000000",
            )
            self._prev_x = x
            self._prev_y = y
            canvas.strokes[-1].append([x, y])

    def _on_release(self, event: tkinter.Event, canvas: tkinter.Canvas) -> None:
        """左ボタン離し: Mode 0 でストロークのラベルを表示する。"""
        if self.mode == 0 and canvas.strokes:
            first = canvas.strokes[-1][0] if canvas.strokes[-1] else None
            if first:
                canvas.create_text(
                    first[0] - 10, first[1] - 10,
                    text=f"L{len(canvas.strokes)}",
                    tags="draw",
                )

    def _on_right_click(self, event: tkinter.Event, canvas: tkinter.Canvas) -> None:
        """右ボタン: Mode 1 でラベル表示 & 次のストローク開始。"""
        if self.mode == 1 and canvas.strokes:
            first = canvas.strokes[-1][0] if canvas.strokes[-1] else None
            if first:
                canvas.create_text(
                    first[0] - 10, first[1] - 10,
                    text=f"L{len(canvas.strokes)}",
                    tags="draw",
                )
            canvas.strokes.append([])

    def _add_point(self, event: tkinter.Event, canvas: tkinter.Canvas) -> None:
        """クリック位置に点を描画してストロークに追加する（Mode 1）。"""
        x, y = event.x, event.y
        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#fa3253", tags="draw")
        canvas.strokes[-1].append([x, y])

    # ------------------------------------------------------------------
    # ボタンコマンド
    # ------------------------------------------------------------------

    def _on_delete(self) -> None:
        """全ストロークと中割り画像を削除してリセットする。"""
        self.key1_canvas.delete("draw")
        self.key2_canvas.delete("draw")
        self.key1_canvas.strokes = []
        self.key2_canvas.strokes = []
        self.inbet_canvas.delete("inbetween")

    def _on_interpolate(self) -> None:
        """各ストロークを PCHIP 補間（または優勢点ベース）で描画する。"""
        t_vals = np.linspace(0.0, 1.0, _INTERPOLATION_STEPS)

        for canvas, strokes in (
            (self.key1_canvas, self.key1_canvas.strokes),
            (self.key2_canvas, self.key2_canvas.strokes),
        ):
            for stroke in strokes:
                if self.mode == 0:
                    dominant = extract_dominant_points(stroke)
                    for pt in dominant:
                        p = [int(pt[0]), int(pt[1])]
                        canvas.create_oval(
                            p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3,
                            fill="#6ef442", tags="draw",
                        )
                    interp_pts = [_interpolate_stroke(t, dominant.tolist()) for t in t_vals]
                else:
                    interp_pts = [_interpolate_stroke(t, stroke) for t in t_vals]

                flat: list[float] = [coord for pt in interp_pts for coord in pt]
                canvas.create_line(flat, smooth=False, tags="draw", fill="#5998ff")

    def _on_inbetween(self) -> None:
        """key1 と key2 の間を線形補間してアニメーション再生する。"""
        if len(self.key1_canvas.strokes) != len(self.key2_canvas.strokes):
            self.inbet_canvas.create_text(
                80, 10, text="エラー: 線の本数が一致しません", tags="draw"
            )
            return

        t_vals = np.linspace(0.0, 1.0, _INTERPOLATION_STEPS)
        self._play_inbetween_animation(
            self.key1_canvas.strokes,
            self.key2_canvas.strokes,
            t_vals,
        )

    def _on_auto_inbetween(self) -> None:
        """ML 対応（Shape Context + 最小費用フロー）を使って自動中割りを行う。

        処理フロー:
          1. 現在の GUI ストロークをリサンプリング。
          2. Shape Context 特徴量を計算。
          3. 最小費用フローで点対応を求める。
          4. ストローク対応を確定して中割りアニメーションを再生。
        """
        key1_strokes = resample_strokes(self.key1_canvas.strokes, rate=2.0)
        key2_strokes = resample_strokes(self.key2_canvas.strokes, rate=2.0)

        if not key1_strokes or not key2_strokes:
            self.inbet_canvas.create_text(
                80, 10, text="エラー: ストロークがありません", tags="draw"
            )
            return

        # 全点数を取得してコスト行列を準備
        m1 = sum(len(s) for s in key1_strokes)
        m2 = sum(len(s) for s in key2_strokes)

        # Shape Context 特徴量を計算（注: 点数が多いと重い）
        sp1 = compute_shape_context(key1_strokes).reshape(m1, -1).astype(np.float64)
        sp2 = compute_shape_context(key2_strokes).reshape(m2, -1).astype(np.float64)

        # ユークリッド距離を正規化してコスト行列を作成
        from scipy.spatial import distance as scipy_dist
        cost_matrix = scipy_dist.cdist(sp1, sp2, metric="euclidean")
        cost_matrix = cost_matrix / (cost_matrix.max() + 1e-8)

        # 最小費用フローで点対応を求める
        _flow_cost, flow_dict, transposed = solve_min_cost_flow(cost_matrix)
        match = build_match_matrix(flow_dict, m1, m2, transposed)

        # ストローク対応を確定して key2 を並べ直す
        fixed_key2 = run_auto_correspondence_pipeline(
            key1_strokes, key2_strokes, match
        )
        t_vals = np.linspace(0.0, 1.0, _INTERPOLATION_STEPS)
        self._play_inbetween_animation(key1_strokes, fixed_key2, t_vals)

    # ------------------------------------------------------------------
    # アニメーション
    # ------------------------------------------------------------------

    def _play_inbetween_animation(
        self,
        strokes1: list[list[list[float]]],
        strokes2: list[list[list[float]]],
        t_vals: npt.NDArray[np.float64],
    ) -> None:
        """2 つのストローク群の間を線形補間してアニメーションを再生する。

        Args:
            strokes1: キーフレーム1 のストローク群。
            strokes2: キーフレーム2 のストローク群。
            t_vals: 補間パラメータの配列（0.0 〜 1.0）。
        """
        # 各ストロークの補間点列を事前計算
        key1_pts: list[npt.NDArray[np.float64]] = []
        key2_pts: list[npt.NDArray[np.float64]] = []

        for s1, s2 in zip(strokes1, strokes2):
            k1 = np.array([_interpolate_stroke(t, s1) for t in t_vals])
            k2 = np.array([_interpolate_stroke(t, s2) for t in t_vals])
            key1_pts.append(k1)
            key2_pts.append(k2)

        # フレームをループして描画
        for frame in range(_ANIMATION_FRAMES):
            time.sleep(1.0 / 60.0)
            self.inbet_canvas.delete("inbetween")
            alpha = frame / (_ANIMATION_FRAMES - 1)

            for p1, p2 in zip(key1_pts, key2_pts):
                inbet = (p1 + alpha * (p2 - p1)).astype(np.int64).tolist()
                flat: list[int] = [coord for pt in inbet for coord in pt]
                self.inbet_canvas.create_line(
                    flat, smooth=True, tags="inbetween", fill="#000000"
                )
            self.inbet_canvas.update()


def main() -> None:
    """アプリケーションを起動する。"""
    root = tkinter.Tk()
    _app = InbetweenApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
