"""最小費用フローを用いた点対応計算モジュール。

NetworkX の network_simplex アルゴリズムで 2 つの点群間の最適対応を求める。
ストローク類似度行列などのコスト行列を入力として、
各点の最適なマッチングを流量として出力する。
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import numpy.typing as npt


def solve_min_cost_flow(
    cost_matrix: npt.NDArray[np.floating],
    source_capacity: int = 1000,
    sink_capacity: int = 1000,
) -> tuple[int, dict, bool]:
    """最小費用フローで 2 点群の最適対応を求める。

    コスト行列 C が与えられたとき、各行（点群1の点）と列（点群2の点）の
    最小コスト対応を NetworkX の network_simplex で求める。
    行数 < 列数 の場合は内部で転置し、`transposed=True` を返す。

    グラフ構造:
      - ソースノード 's' → 点群1の各ノード (0..row-1)
      - 点群1の各ノード → 点群2の各ノード (row..row+col-1)
      - 点群2の各ノード → シンクノード 't'

    Args:
        cost_matrix: shape (m, n) のコスト行列（値は小さいほど良い対応）。
        source_capacity: ソースエッジの容量上限。
        sink_capacity: シンクエッジの容量上限。

    Returns:
        (flow_cost, flow_dict, transposed) のタプル:
          - flow_cost: 最小コストの合計値。
          - flow_dict: {node: {neighbor: flow}} 形式のフロー辞書。
          - transposed: コスト行列を転置したかどうか。
            True のとき、呼び出し側で対応行列を転置し直す必要がある。
    """
    # 値を整数化し、最小値を 0 に揃える
    cost = (cost_matrix).astype(np.int64)
    cost = cost - np.min(cost)
    row, col = cost.shape

    # 行 >= 列 になるよう調整（network_simplex の要件）
    transposed = False
    if row < col:
        cost = cost.T
        row, col = cost.shape
        transposed = True

    demand = row

    # demand パラメータ: 正=供給、負=需要
    lower = [-1] * row + [1] * col
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("s", demand=-demand + row)
    for i in range(row + col):
        G.add_node(i, demand=lower[i])
    G.add_node("t", demand=demand - col)

    # 点群1 ↔ 点群2 のエッジ（容量 1、重みはコスト値）
    for i in range(row):
        for j in range(col):
            G.add_edge(i, j + row, weight=int(cost[i, j]), capacity=1)

    # ソース → 点群1 のエッジ
    for k in range(row):
        G.add_edge("s", k, weight=0, capacity=source_capacity)

    # 点群2 → シンク のエッジ
    for k in range(col):
        G.add_edge(k + row, "t", weight=0, capacity=sink_capacity)

    flow_cost, flow_dict = nx.network_simplex(
        G, demand="demand", capacity="capacity", weight="weight"
    )
    return int(flow_cost), flow_dict, transposed
