/**
 * PCHIP（Piecewise Cubic Hermite Interpolating Polynomial）補間モジュール。
 *
 * scipy.interpolate.PchipInterpolator と同等のアルゴリズムを実装する。
 * Fritsch-Carlson 法によって単調性を保持した微分値を計算し、
 * 区間ごとに三次エルミート補間を行う。
 */

import type { Point, Stroke } from "../types";

/** 端点での微分値を求める（scipy の pchip_slopes エンドポイント式）。 */
function endpointSlope(
  h1: number,
  h2: number,
  d1: number,
  d2: number
): number {
  const slope = ((2 * h1 + h2) * d1 - h1 * d2) / (h1 + h2);
  if (Math.sign(slope) !== Math.sign(d1)) return 0;
  if (Math.sign(d1) !== Math.sign(d2) && Math.abs(slope) > 3 * Math.abs(d1)) {
    return 3 * d1;
  }
  return slope;
}

/**
 * 各ノードの微分値を Fritsch-Carlson 法で計算する。
 *
 * @param h  区間幅の配列（長さ n-1）
 * @param d  各区間の傾き配列（長さ n-1）
 * @returns  各ノードの微分値（長さ n）
 */
function pchipSlopes(h: number[], d: number[]): number[] {
  const n = d.length + 1;
  const m = new Array<number>(n).fill(0);

  // 端点
  m[0] = endpointSlope(h[0], h[1], d[0], d[1]);
  m[n - 1] = endpointSlope(h[n - 2], h[n - 3], d[n - 2], d[n - 3]);

  // 内部点：調和平均（符号が異なる場合は 0）
  for (let i = 1; i < n - 1; i++) {
    if (d[i - 1] * d[i] <= 0) {
      m[i] = 0;
    } else {
      const w1 = 2 * h[i] + h[i - 1];
      const w2 = h[i] + 2 * h[i - 1];
      m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
    }
  }
  return m;
}

/**
 * パラメータ t（0〜1）に対してストロークを PCHIP 補間した点を返す。
 *
 * 制御点数が 1 の場合はその点、2 の場合は線形補間を行う。
 * 制御点の x, y をそれぞれ独立に補間するパラメトリック曲線として扱う。
 *
 * @param points  制御点のリスト（各要素は [x, y]）
 * @param t       補間パラメータ（0.0 〜 1.0）
 * @returns       [x, y] 形式の補間結果
 */
export function pchipInterpolate(points: Point[], t: number): Point {
  const n = points.length;
  if (n === 0) return [0, 0];
  if (n === 1) return points[0];
  if (n === 2) {
    return [
      points[0][0] + t * (points[1][0] - points[0][0]),
      points[0][1] + t * (points[1][1] - points[0][1]),
    ];
  }

  // パラメータ ts = linspace(0, 1, n)
  const ts = Array.from({ length: n }, (_, i) => i / (n - 1));
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);

  // 区間幅と各区間の傾きを計算
  const h: number[] = [];
  const dx: number[] = [];
  const dy: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    h.push(ts[i + 1] - ts[i]);
    dx.push((xs[i + 1] - xs[i]) / h[i]);
    dy.push((ys[i + 1] - ys[i]) / h[i]);
  }

  const mx = pchipSlopes(h, dx);
  const my = pchipSlopes(h, dy);

  // t が属する区間を二分探索で特定
  let lo = 0;
  let hi = n - 2;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (ts[mid] <= t) lo = mid;
    else hi = mid - 1;
  }
  const i = lo;

  // 区間内の正規化パラメータ u ∈ [0, 1]
  const u = (t - ts[i]) / h[i];
  const u2 = u * u;
  const u3 = u2 * u;

  // 三次エルミート基底関数
  const h00 = 2 * u3 - 3 * u2 + 1;
  const h10 = u3 - 2 * u2 + u;
  const h01 = -2 * u3 + 3 * u2;
  const h11 = u3 - u2;

  const xi = h00 * xs[i] + h10 * h[i] * mx[i] + h01 * xs[i + 1] + h11 * h[i] * mx[i + 1];
  const yi = h00 * ys[i] + h10 * h[i] * my[i] + h01 * ys[i + 1] + h11 * h[i] * my[i + 1];

  return [xi, yi];
}

/**
 * ストロークを PCHIP 補間で `count` 点にリサンプリングする。
 *
 * @param stroke  入力ストローク
 * @param count   出力する点数
 * @returns       補間後のストローク
 */
export function sampleStroke(stroke: Stroke, count: number): Stroke {
  return Array.from({ length: count }, (_, i) =>
    pchipInterpolate(stroke, i / (count - 1))
  );
}

/**
 * ストロークをピクセル間隔 `rate` でリサンプリングする。
 *
 * 各セグメントの長さに応じて点を配置する（Python の recovery.resample_strokes 相当）。
 *
 * @param stroke  入力ストローク
 * @param rate    サンプリング間隔（ピクセル単位）
 * @returns       リサンプリング後のストローク
 */
export function resampleStroke(stroke: Stroke, rate = 2): Stroke {
  if (stroke.length < 2) return stroke;
  const n = stroke.length;
  const ts = Array.from({ length: n }, (_, i) => i / (n - 1));
  const result: Stroke = [];

  for (let i = 0; i < n - 1; i++) {
    const [x0, y0] = stroke[i];
    const [x1, y1] = stroke[i + 1];
    const segLen = Math.hypot(x1 - x0, y1 - y0);
    const steps = Math.max(1, Math.floor(segLen / rate));
    for (let s = 0; s < steps; s++) {
      const t = ts[i] + (s / steps) * (ts[i + 1] - ts[i]);
      result.push(pchipInterpolate(stroke, t));
    }
  }
  result.push(stroke[n - 1]);
  return result;
}
