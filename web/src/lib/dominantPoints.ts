/**
 * 二分割法（Divide & Conquer）による優勢点（Dominant Points）検出モジュール。
 *
 * ストロークの端点を結ぶ直線から最も遠い点を繰り返し検出し、
 * ストロークを圧縮した制御点列を返す。
 * Python の extract_dominant_points() 関数に相当する。
 */

import type { Stroke } from "../types";

/** インデックスを付加した点の内部型 */
type IndexedPoint = [number, number, number]; // [x, y, originalIndex]

/**
 * 端点を結ぶ直線からの各点の距離を計算し、
 * 閾値を超えた最遠点を再帰的に優勢点リストに追加する。
 *
 * @param line    [x, y, index] の配列
 * @param result  優勢点を追加する配列（破壊的変更）
 */
function detectRecursive(
  line: IndexedPoint[],
  result: IndexedPoint[]
): void {
  if (line.length <= 1) return;

  const [x0, y0] = line[0];
  const [xn, yn] = line[line.length - 1];

  // 端点を結ぶ直線の方程式: ax + by + c = 0
  const a = yn - y0;
  const b = x0 - xn;
  const c = xn * y0 - x0 * yn;
  const chordLen = Math.hypot(a, b);

  if (chordLen === 0) return;

  // 各点の直線からの距離を計算
  let maxDist = 0;
  let maxIdx = 0;
  for (let i = 0; i < line.length; i++) {
    const dist = Math.abs(a * line[i][0] + b * line[i][1] + c) / chordLen;
    if (dist > maxDist) {
      maxDist = dist;
      maxIdx = i;
    }
  }

  // 最大距離が閾値（弦長の 1/50）を超えた場合のみ分割を続ける
  if (maxDist > chordLen / 50) {
    result.push(line[maxIdx]);
    detectRecursive(line.slice(0, maxIdx), result);
    detectRecursive(line.slice(maxIdx + 1), result);
  }
}

/**
 * ストロークから優勢点を検出して返す。
 *
 * 始点と終点は必ず含まれる。内部の優勢点は元の順序に並べ直す。
 *
 * @param stroke  入力ストローク（[x, y] の配列）
 * @returns       優勢点のみで構成されたストローク
 */
export function extractDominantPoints(stroke: Stroke): Stroke {
  if (stroke.length <= 2) return stroke;

  // 各点にオリジナルインデックスを付加
  const indexed: IndexedPoint[] = stroke.map((p, i) => [p[0], p[1], i]);

  const dominant: IndexedPoint[] = [];
  detectRecursive(indexed, dominant);

  // 元のインデックス順に並べ直して始点・終点を追加
  dominant.sort((a, b) => a[2] - b[2]);

  const result: Stroke = [stroke[0]];
  for (const pt of dominant) {
    result.push([pt[0], pt[1]]);
  }
  result.push(stroke[stroke.length - 1]);

  return result;
}
