/**
 * Shape Context 特徴量計算モジュール。
 *
 * 各点を基準として、他の全点へのベクトルを
 * binSize × binSize の 2D ヒストグラムで集計する。
 * Python の compute_shape_context() 関数に相当する。
 */

import type { Point, Stroke } from "../types";

/**
 * 全ストロークの点に対して Shape Context ヒストグラムを計算する。
 *
 * @param strokes  ストロークのリスト
 * @param binSize  ヒストグラムの各軸のビン数（デフォルト 32）
 * @param range    ヒストグラムの座標範囲 [-range, range]（デフォルト 32）
 * @returns        各点の平坦化されたヒストグラム配列（長さ N × binSize²）
 */
export function computeShapeContext(
  strokes: Stroke[],
  binSize = 32,
  range = 32
): Float32Array[] {
  // 全点を結合
  const allPoints: Point[] = [];
  for (const stroke of strokes) {
    for (const pt of stroke) {
      allPoints.push(pt);
    }
  }

  const n = allPoints.length;
  const step = (2 * range) / binSize;
  const results: Float32Array[] = [];

  for (let i = 0; i < n; i++) {
    const hist = new Float32Array(binSize * binSize);
    const [xi, yi] = allPoints[i];

    for (let j = 0; j < n; j++) {
      if (j === i) continue;
      const dx = allPoints[j][0] - xi;
      const dy = allPoints[j][1] - yi;

      // ビンのインデックスを計算
      const bx = Math.floor((dx + range) / step);
      const by = Math.floor((dy + range) / step);

      if (bx >= 0 && bx < binSize && by >= 0 && by < binSize) {
        hist[bx * binSize + by]++;
      }
    }
    results.push(hist);
  }

  return results;
}

/**
 * 2 つの Shape Context ヒストグラム間のユークリッド距離を計算する。
 *
 * @param h1  ヒストグラム 1
 * @param h2  ヒストグラム 2
 * @returns   ユークリッド距離
 */
export function histogramDistance(h1: Float32Array, h2: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < h1.length; i++) {
    const d = h1[i] - h2[i];
    sum += d * d;
  }
  return Math.sqrt(sum);
}

/**
 * 2 つのストローク群の全点間の距離行列を計算する。
 *
 * 計算コストが大きいため、点数が多い場合はリサンプリングを推奨する。
 *
 * @param strokes1  キーフレーム 1 のストローク群
 * @param strokes2  キーフレーム 2 のストローク群
 * @param binSize   Shape Context のビン数
 * @returns         コスト行列（行: strokes1 の点, 列: strokes2 の点）と各キーの点数
 */
export function buildCostMatrix(
  strokes1: Stroke[],
  strokes2: Stroke[],
  binSize = 32
): { costMatrix: number[][]; m1: number; m2: number } {
  const hist1 = computeShapeContext(strokes1, binSize);
  const hist2 = computeShapeContext(strokes2, binSize);

  const m1 = hist1.length;
  const m2 = hist2.length;

  // 距離行列を計算して 0〜1 に正規化
  const raw: number[][] = Array.from({ length: m1 }, () =>
    new Array<number>(m2).fill(0)
  );
  let maxDist = 0;

  for (let i = 0; i < m1; i++) {
    for (let j = 0; j < m2; j++) {
      const d = histogramDistance(hist1[i], hist2[j]);
      raw[i][j] = d;
      if (d > maxDist) maxDist = d;
    }
  }

  // 正規化（類似度 = 1 - 正規化距離）
  const costMatrix = raw.map((row) =>
    row.map((d) => 1 - d / (maxDist + 1e-8))
  );

  return { costMatrix, m1, m2 };
}
