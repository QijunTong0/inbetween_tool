"""キーフレームデータの読み込みと点列のリサンプリングを行うモジュール。

アニメーションの中割りに使用する2枚のキーフレームを pickle ファイルから読み込み、
一定間隔で再サンプリングして返す。
"""

from __future__ import annotations

import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from scipy import interpolate


def compute_stroke_length(points: list[list[float]]) -> float:
    """点列の総弧長（折れ線の全長）を計算する。

    Args:
        points: (x, y) 座標のリスト。

    Returns:
        隣接点間のユークリッド距離の総和。
    """
    total = 0.0
    for i in range(1, len(points)):
        total += float(np.linalg.norm(np.array(points[i]) - np.array(points[i - 1])))
    return total


def resample_strokes(
    lines: list[list[list[float]]],
    rate: float = 2.0,
) -> list[list[list[int]]]:
    """各ストロークを指定したピクセル間隔で等間隔リサンプリングする。

    PCHIP 補間を使ってストロークを滑らかに補間し、
    `rate` ピクセルごとに点を配置した新しい点列を返す。

    Args:
        lines: ストロークのリスト。各ストロークは (x, y) 座標のリスト。
        rate: サンプリング間隔（ピクセル単位）。デフォルトは 2.0。

    Returns:
        リサンプリング後のストロークのリスト。
    """
    resampled: list[list[list[int]]] = []
    for line in lines:
        sample: list[list[int]] = []
        x = np.array(line)[:, 0]
        y = np.array(line)[:, 1]
        ts = np.linspace(0.0, 1.0, len(line))
        interp_x = interpolate.PchipInterpolator(ts, x)
        interp_y = interpolate.PchipInterpolator(ts, y)
        for i in range(1, len(ts)):
            seg_len = np.sqrt((x[i] - x[i - 1]) ** 2 + (y[i] - y[i - 1]) ** 2)
            t_vals = np.linspace(ts[i - 1], ts[i], int(seg_len / rate + 1))
            for t in t_vals:
                sample.append([int(interp_x(t)), int(interp_y(t))])
        resampled.append(sample)
    return resampled


def plot_strokes(strokes: list[list[list[float]]]) -> None:
    """ストローク群を jet カラーマップで描画する（y 軸は上向きに反転）。

    Args:
        strokes: 描画するストロークのリスト。
    """
    cmap = plt.get_cmap("jet")
    for idx, stroke in enumerate(strokes):
        pts = np.array(stroke)
        color = cmap(idx / len(strokes))
        plt.plot(pts[:, 0], -pts[:, 1], color=color)
    plt.xticks([])
    plt.yticks([])


def load_keyframes(
    path1: str | Path = "key1_2.p",
    path2: str | Path = "key2_2.p",
    resample_rate: float = 2.0,
) -> tuple[list[list[list[int]]], list[list[list[int]]]]:
    """pickle ファイルからキーフレームデータを読み込み、リサンプリングして返す。

    各ファイルの末尾要素（空ストロークなど）を除去した後、
    `resample_rate` の間隔でリサンプリングする。

    Args:
        path1: キーフレーム1 の pickle ファイルパス。
        path2: キーフレーム2 の pickle ファイルパス。
        resample_rate: サンプリング間隔（ピクセル単位）。

    Returns:
        (key1_strokes, key2_strokes) のタプル。
    """
    with open(path1, "rb") as f:
        key1: list[list[list[float]]] = pickle.load(f)
    with open(path2, "rb") as f:
        key2: list[list[list[float]]] = pickle.load(f)

    # 末尾の空ストロークを除去
    del key1[-1]
    del key2[-1]

    return resample_strokes(key1, rate=resample_rate), resample_strokes(key2, rate=resample_rate)
