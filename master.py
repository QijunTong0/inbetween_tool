"""ML パイプラインのスクリプト実行エントリポイント。

このスクリプトは pickle ファイルからキーフレームを読み込み、
Shape Context 特徴量の計算 → 最小費用フロー → ストローク対応 の
パイプラインを実行する。

ファイル要件:
    key1_2.p, key2_2.p が同ディレクトリに存在すること。
"""

from __future__ import annotations

import numpy as np

from conbshapecontex import extract_and_save_shape_contexts
from matchingnetwork import solve_min_cost_flow
from recovery import load_keyframes
from scipy.spatial import distance as scipy_dist
from stroke_correspond import build_match_matrix, compute_stroke_matrices


def run_pipeline(
    key1_path: str = "key1_2.p",
    key2_path: str = "key2_2.p",
) -> None:
    """ML 対応パイプラインを実行して結果を標準出力に表示する。

    Args:
        key1_path: キーフレーム1 の pickle ファイルパス。
        key2_path: キーフレーム2 の pickle ファイルパス。
    """
    print("キーフレームを読み込み中...")
    key1_strokes, key2_strokes = load_keyframes(key1_path, key2_path)

    m1 = sum(len(s) for s in key1_strokes)
    m2 = sum(len(s) for s in key2_strokes)
    print(f"  キーフレーム1: {len(key1_strokes)} ストローク, {m1} 点")
    print(f"  キーフレーム2: {len(key2_strokes)} ストローク, {m2} 点")

    print("Shape Context 特徴量を計算中...")
    sp1, sp2 = extract_and_save_shape_contexts(key1_strokes, key2_strokes)

    print("コスト行列を構築中...")
    sp1_flat = sp1.reshape(m1, -1).astype(np.float64)
    sp2_flat = sp2.reshape(m2, -1).astype(np.float64)
    cost_matrix = scipy_dist.cdist(sp1_flat, sp2_flat, metric="euclidean")
    cost_matrix = cost_matrix / (cost_matrix.max() + 1e-8)

    print("最小費用フローで点対応を計算中...")
    flow_cost, flow_dict, transposed = solve_min_cost_flow(cost_matrix)
    print(f"  フローコスト: {flow_cost}")

    match = build_match_matrix(flow_dict, m1, m2, transposed)

    print("ストローク類似度行列を計算中...")
    stroke_matrix, seq_matrix = compute_stroke_matrices(
        key1_strokes, key2_strokes, match
    )
    print("ストローク類似度行列:")
    print(stroke_matrix)
    print("ストローク順序推定行列:")
    print(seq_matrix)


if __name__ == "__main__":
    run_pipeline()
