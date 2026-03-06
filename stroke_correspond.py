"""ストローク対応の計算モジュール。

点対応行列からストロークレベルの類似度を計算し、
最適なストローク対応と向き（順/逆）を決定する。
"""

from __future__ import annotations

import copy

import numpy as np
import numpy.typing as npt


def build_match_matrix(
    flow_dict: dict,
    m1: int,
    m2: int,
    transposed: bool,
) -> npt.NDArray[np.float64]:
    """フロー辞書から点対応行列 (m1 × m2) を構築する。

    `match[i, j] = 1` はキーフレーム1 の i 番目の点と
    キーフレーム2 の j 番目の点が対応することを示す。

    Args:
        flow_dict: network_simplex が返すフロー辞書。
        m1: キーフレーム1 の総点数。
        m2: キーフレーム2 の総点数。
        transposed: solve_min_cost_flow がコスト行列を転置したかどうか。

    Returns:
        shape (m1, m2) の 0/1 対応行列。
    """
    if transposed:
        # 転置前は m1 < m2 だったので、フローは (m2, m1) の順
        match = np.zeros((m2, m1))
        for i in range(m2):
            for j in range(m2, m1 + m2):
                if flow_dict[i].get(j, 0) == 1:
                    match[i, j - m2] = 1.0
        # key1 → key2 方向に戻す
        match = match.T
    else:
        match = np.zeros((m1, m2))
        for i in range(m1):
            for j in range(m1, m1 + m2):
                if flow_dict[i].get(j, 0) == 1:
                    match[i, j - m1] = 1.0
    return match


def correspondence_ratio(
    st1: npt.NDArray[np.intp],
    st2: npt.NDArray[np.intp],
    match: npt.NDArray[np.float64],
) -> float:
    """2 ストローク間の点対応カバレッジ率を計算する。

    st1（ストローク1の点インデックス）と st2（ストローク2の点インデックス）の
    サブ対応行列 W を取り出し、両側からの対応カバレッジ率の平均を返す。

    Args:
        st1: キーフレーム1 側のストローク内点インデックスの配列。
        st2: キーフレーム2 側のストローク内点インデックスの配列。
        match: shape (m1, m2) の点対応行列。

    Returns:
        0.0 〜 1.0 のカバレッジ率。対応がなければ 0.0。
    """
    W = match[st1].T[st2].T
    if np.sum(W) > 0:
        # st1 側で少なくとも 1 点と対応する行の割合
        r1 = float(np.sum(np.sum(W, axis=1) > 0))
        # st2 側で少なくとも 1 点と対応する列の割合
        r2 = float(np.sum(np.sum(W, axis=0) > 0))
        return (r1 / len(st1) + r2 / len(st2)) * 0.5
    return 0.0


def covariance_estimate(
    st1: npt.NDArray[np.intp],
    st2: npt.NDArray[np.intp],
    match: npt.NDArray[np.float64],
) -> float:
    """2 ストローク間の対応点列から順序方向を推定する。

    対応点のインデックスペアの共分散を計算し、
    正規化相関係数（-1 〜 1）を返す。
    正の値は同方向、負の値は逆方向を示す。

    Args:
        st1: キーフレーム1 側のストローク内点インデックスの配列。
        st2: キーフレーム2 側のストローク内点インデックスの配列。
        match: shape (m1, m2) の点対応行列。

    Returns:
        -1.0 〜 1.0 の正規化相関。対応点が不足の場合は 0.0。
    """
    W = match[st1].T[st2].T
    if np.sum(W) > 1:
        idx_pairs = np.array(np.where(W == 1))
        cov = np.cov(idx_pairs[0], idx_pairs[1])
        denom = np.sqrt(cov[0, 0] * cov[1, 1])
        if denom == 0.0:
            return 0.0
        return float(cov[0, 1] / denom)
    return 0.0


def match_strokes_one_to_one(
    stroke_matrix: npt.NDArray[np.float64],
    seq_matrix: npt.NDArray[np.float64],
    n_strokes: int,
) -> npt.NDArray[np.int64]:
    """類似度行列に基づいて一対一のストローク対応を貪欲法で求める。

    各ステップで stroke_matrix の最大値の位置を選び、
    その行と列を無効化することで繰り返す。
    seq_matrix の符号から各ストローク対の向きを決定する。

    Args:
        stroke_matrix: shape (n1, n2) の類似度行列。
        seq_matrix: shape (n1, n2) の順序方向推定行列。
        n_strokes: キーフレーム1 のストローク数（= 対応を求めるペア数）。

    Returns:
        shape (n_strokes, 3) の int64 配列。
        各行は [key1_stroke_index, key2_stroke_index, orientation_sign]。
        orientation_sign は +1（同方向）または -1（逆方向）。
    """
    stmat = copy.deepcopy(stroke_matrix)
    revmat = copy.deepcopy(seq_matrix)
    st_ind: list[tuple[int, int]] = []
    rev_ind: list[float] = []

    while len(st_ind) != n_strokes:
        max_idx = np.unravel_index(stmat.argmax(), stmat.shape)
        st_ind.append(max_idx)
        # 選んだ行・列をすべて無効化（再選択を防ぐ）
        stmat[max_idx[0], :] = -1.0
        stmat[:, max_idx[1]] = -1.0
        rev_ind.append(float(np.sign(revmat[max_idx])))

    result = np.array(st_ind)
    rev_arr = np.array(rev_ind).reshape((len(rev_ind), 1))
    combined = np.hstack((result, rev_arr)).astype(np.int64)
    # key1 のインデックス順に並べ直す
    return combined[np.argsort(combined[:, 0])]


def fix_stroke_order(
    key2_points_array: list[list[list[float]]],
    stmatch: npt.NDArray[np.int64],
) -> list[list[list[float]]]:
    """ストローク対応結果に基づき key2 のストロークを並べ直す。

    stmatch[:, 2] == 1 ならそのまま、-1 なら点列を逆順にしてから返す。

    Args:
        key2_points_array: キーフレーム2 のストローク群。
        stmatch: match_strokes_one_to_one が返す対応行列。
                 各行は [key1_idx, key2_idx, orientation]。

    Returns:
        key1 のストロークと対応付けられた key2 のストロークのリスト。
    """
    result: list[list[list[float]]] = []
    for i in range(len(stmatch)):
        matched_idx = int(stmatch[i, 1])
        stroke = list(key2_points_array[matched_idx])
        if stmatch[i, 2] != 1:
            stroke = stroke[::-1]
        result.append(stroke)
    return result


def compute_stroke_matrices(
    key1_points_array: list[list[list[float]]],
    key2_points_array: list[list[list[float]]],
    match: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """点対応行列からストロークレベルの類似度行列と順序推定行列を計算する。

    各ストロークに属する点のインデックスを求め、
    correspondence_ratio と covariance_estimate を全ペアに適用する。

    Args:
        key1_points_array: キーフレーム1 のストローク群。
        key2_points_array: キーフレーム2 のストローク群。
        match: shape (m1, m2) の点対応行列。

    Returns:
        (stroke_matrix, seq_matrix) のタプル:
          - stroke_matrix: shape (n1, n2) の類似度行列。
          - seq_matrix: shape (n1, n2) の順序推定行列。
    """
    # 各点がどのストロークに属するかのインデックス配列を作成
    key1_ind: npt.NDArray[np.intp] = np.concatenate([
        np.full(len(stroke), i) for i, stroke in enumerate(key1_points_array)
    ])
    key2_ind: npt.NDArray[np.intp] = np.concatenate([
        np.full(len(stroke), i) for i, stroke in enumerate(key2_points_array)
    ])

    n1 = len(key1_points_array)
    n2 = len(key2_points_array)
    stroke_matrix = np.zeros((n1, n2))
    seq_matrix = np.zeros((n1, n2))

    for i in range(n1):
        for j in range(n2):
            idx1 = np.where(key1_ind == i)[0]
            idx2 = np.where(key2_ind == j)[0]
            stroke_matrix[i, j] = correspondence_ratio(idx1, idx2, match)
            seq_matrix[i, j] = covariance_estimate(idx1, idx2, match)

    return stroke_matrix, seq_matrix


def run_auto_correspondence_pipeline(
    key1_points_array: list[list[list[float]]],
    key2_points_array: list[list[list[float]]],
    initial_match: npt.NDArray[np.float64],
) -> list[list[list[float]]]:
    """点対応から自動ストローク対応を求め、修正済み key2 ストロークを返す。

    パイプライン:
      1. 点対応行列からストローク類似度行列を計算。
      2. 貪欲法で一対一ストローク対応を決定。
      3. 向きを考慮した key2 ストローク列を返す。

    Args:
        key1_points_array: キーフレーム1 のストローク群。
        key2_points_array: キーフレーム2 のストローク群。
        initial_match: shape (m1, m2) の点対応行列。

    Returns:
        key1 と対応付けられた key2 のストロークリスト。
        各ストロークは必要に応じて逆順に変換済み。
    """
    stroke_matrix, seq_matrix = compute_stroke_matrices(
        key1_points_array, key2_points_array, initial_match
    )
    stmatch = match_strokes_one_to_one(
        stroke_matrix, seq_matrix, len(key1_points_array)
    )
    return fix_stroke_order(key2_points_array, stmatch)
