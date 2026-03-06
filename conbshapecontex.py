"""Shape Context 特徴量の計算モジュール。

各点を基準に、他の全点へのベクトルを 2D ヒストグラムで集計することで
Shape Context 記述子を計算する。
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def to_log_polar(point: list[float]) -> list[float]:
    """デカルト座標の点を極座標 (r, θ) に変換する。

    原点の場合は (0, 0) を返す。
    角度は y >= 0 のとき [0, π]、y < 0 のとき (π, 2π) の範囲となる。

    Args:
        point: [x, y] 形式の座標リスト。

    Returns:
        [r, theta] 形式の極座標リスト。
    """
    x, y = point
    if x == 0.0 and y == 0.0:
        return [0.0, 0.0]

    r = float(np.sqrt(x**2 + y**2))
    if y >= 0:
        theta = float(np.arccos(x / r))
    else:
        theta = float(-np.arccos(x / r) + 2 * np.pi)
    return [r, theta]


def compute_shape_context(
    points_array: list[list[list[float]]],
    bin_size: int = 64,
) -> npt.NDArray[np.float32]:
    """全ストロークの点に対して Shape Context 記述子を計算する。

    各点 p_i に対して、他のすべての点との差分ベクトルを
    `bin_size × bin_size` の 2D ヒストグラムで集計する。
    出力は CNN への入力を想定した 4D テンソル形式。

    Args:
        points_array: ストロークのリスト。各ストロークは [x, y] 座標のリスト。
        bin_size: ヒストグラムの各軸のビン数。デフォルトは 64。

    Returns:
        shape (N, 1, bin_size, bin_size) の float32 配列。
        N は全点数の合計。
    """
    # 全ストロークの点を結合
    all_points: list[list[float]] = []
    for stroke in points_array:
        all_points.extend(stroke)
    pts = np.array(all_points)
    n = len(pts)

    edge = np.linspace(-32.0, 32.0, bin_size + 1)
    rows: list[npt.NDArray[np.float32]] = []

    for i in range(n):
        # i 番目の点を除いたすべての点との差分ベクトル
        vectors = np.delete(pts, i, axis=0) - pts[i]
        h, _, _ = np.histogram2d(vectors[:, 0], vectors[:, 1], bins=(edge, edge))
        rows.append(h.reshape(bin_size**2).astype(np.float32))

    H = np.array(rows, dtype=np.float32)
    return H.reshape(n, 1, bin_size, bin_size)


def extract_and_save_shape_contexts(
    key1_points_array: list[list[list[float]]],
    key2_points_array: list[list[list[float]]],
    out_path1: str = "sp1.npy",
    out_path2: str = "sp2.npy",
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]:
    """2 枚のキーフレームの Shape Context を計算してファイルに保存する。

    Args:
        key1_points_array: キーフレーム1 のストローク群。
        key2_points_array: キーフレーム2 のストローク群。
        out_path1: キーフレーム1 の保存先パス。
        out_path2: キーフレーム2 の保存先パス。

    Returns:
        (sp1, sp2) の Shape Context テンソルのタプル。
    """
    sp1 = compute_shape_context(key1_points_array)
    sp2 = compute_shape_context(key2_points_array)
    np.save(out_path1, sp1)
    np.save(out_path2, sp2)
    return sp1, sp2
