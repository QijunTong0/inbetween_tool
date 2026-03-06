/**
 * ストローク対応計算モジュール。
 *
 * 点対応行列からストロークレベルの類似度を計算し、
 * 最適な一対一ストローク対応と向き（順/逆）を決定する。
 * Python の stroke_correspond.py に相当する。
 */

import type { Stroke } from "../types";
import { resampleStroke } from "./interpolation";
import { buildCostMatrix } from "./shapeContext";
import { solveMinCostFlow } from "./minCostFlow";

/** ストローク対応の結果 */
export interface StrokeMatch {
  key1Idx: number;
  key2Idx: number;
  /** +1: 同方向、-1: 逆方向 */
  orientation: 1 | -1;
}

/**
 * 点対応行列から 2 ストローク間のカバレッジ率を計算する。
 *
 * @param st1   ストローク 1 に属する点のインデックス配列
 * @param st2   ストローク 2 に属する点のインデックス配列
 * @param match 点対応行列（match[i][j] = true で i と j が対応）
 * @returns     0〜1 のカバレッジ率
 */
export function correspondenceRatio(
  st1: number[],
  st2: number[],
  match: boolean[][]
): number {
  let covered1 = 0;
  let covered2 = 0;

  for (const i of st1) {
    for (const j of st2) {
      if (match[i]?.[j]) {
        covered1++;
        break;
      }
    }
  }
  for (const j of st2) {
    for (const i of st1) {
      if (match[i]?.[j]) {
        covered2++;
        break;
      }
    }
  }

  if (covered1 === 0 && covered2 === 0) return 0;
  return (covered1 / st1.length + covered2 / st2.length) * 0.5;
}

/**
 * 対応点のインデックスペアの共分散から順序方向を推定する。
 *
 * @param st1   ストローク 1 の点インデックス配列
 * @param st2   ストローク 2 の点インデックス配列
 * @param match 点対応行列
 * @returns     正規化相関係数（正: 同方向、負: 逆方向、0: 不明）
 */
export function covarianceEstimate(
  st1: number[],
  st2: number[],
  match: boolean[][]
): number {
  const pairs: [number, number][] = [];
  for (let ii = 0; ii < st1.length; ii++) {
    for (let jj = 0; jj < st2.length; jj++) {
      if (match[st1[ii]]?.[st2[jj]]) {
        pairs.push([ii, jj]);
      }
    }
  }
  if (pairs.length < 2) return 0;

  const n = pairs.length;
  const meanI = pairs.reduce((s, p) => s + p[0], 0) / n;
  const meanJ = pairs.reduce((s, p) => s + p[1], 0) / n;

  let cov = 0;
  let varI = 0;
  let varJ = 0;
  for (const [i, j] of pairs) {
    cov += (i - meanI) * (j - meanJ);
    varI += (i - meanI) ** 2;
    varJ += (j - meanJ) ** 2;
  }

  const denom = Math.sqrt(varI * varJ);
  return denom === 0 ? 0 : cov / denom;
}

/**
 * 点対応行列から各点がどのストロークに属するかのインデックスを生成する。
 *
 * @param strokes  ストローク群
 * @returns        各点のストロークインデックス配列
 */
function buildStrokeIndex(strokes: Stroke[]): number[] {
  const index: number[] = [];
  for (let i = 0; i < strokes.length; i++) {
    for (let _j = 0; _j < strokes[i].length; _j++) {
      index.push(i);
    }
  }
  return index;
}

/**
 * 点対応行列からストローク類似度行列と順序推定行列を計算する。
 *
 * @param strokes1  キーフレーム 1 のストローク群
 * @param strokes2  キーフレーム 2 のストローク群
 * @param match     点対応行列
 * @returns         { strokeMatrix, seqMatrix }
 */
export function computeStrokeMatrices(
  strokes1: Stroke[],
  strokes2: Stroke[],
  match: boolean[][]
): { strokeMatrix: number[][]; seqMatrix: number[][] } {
  const idx1 = buildStrokeIndex(strokes1);
  const idx2 = buildStrokeIndex(strokes2);
  const n1 = strokes1.length;
  const n2 = strokes2.length;

  const strokeMatrix: number[][] = Array.from({ length: n1 }, () =>
    new Array<number>(n2).fill(0)
  );
  const seqMatrix: number[][] = Array.from({ length: n1 }, () =>
    new Array<number>(n2).fill(0)
  );

  for (let i = 0; i < n1; i++) {
    for (let j = 0; j < n2; j++) {
      const st1 = idx1.map((v, k) => (v === i ? k : -1)).filter((v) => v >= 0);
      const st2 = idx2.map((v, k) => (v === j ? k : -1)).filter((v) => v >= 0);
      strokeMatrix[i][j] = correspondenceRatio(st1, st2, match);
      seqMatrix[i][j] = covarianceEstimate(st1, st2, match);
    }
  }

  return { strokeMatrix, seqMatrix };
}

/**
 * 類似度行列から貪欲法で一対一のストローク対応を求める。
 *
 * @param strokeMatrix  shape (n1, n2) の類似度行列
 * @param seqMatrix     shape (n1, n2) の順序推定行列
 * @param nStrokes      対応を求めるストローク数
 * @returns             StrokeMatch の配列（key1 のインデックス順）
 */
export function matchStrokesOneToOne(
  strokeMatrix: number[][],
  seqMatrix: number[][],
  nStrokes: number
): StrokeMatch[] {
  // 行列をコピーして破壊的に利用
  const mat = strokeMatrix.map((row) => [...row]);
  const matches: StrokeMatch[] = [];

  while (matches.length < nStrokes) {
    // 最大値の位置を探す
    let maxVal = -Infinity;
    let ri = 0;
    let ci = 0;
    for (let i = 0; i < mat.length; i++) {
      for (let j = 0; j < mat[i].length; j++) {
        if (mat[i][j] > maxVal) {
          maxVal = mat[i][j];
          ri = i;
          ci = j;
        }
      }
    }

    const orientation = seqMatrix[ri][ci] >= 0 ? 1 : -1;
    matches.push({ key1Idx: ri, key2Idx: ci, orientation: orientation as 1 | -1 });

    // 選んだ行と列を無効化
    for (let j = 0; j < mat[ri].length; j++) mat[ri][j] = -Infinity;
    for (let i = 0; i < mat.length; i++) mat[i][ci] = -Infinity;
  }

  // key1 のインデックス順に並べ直す
  return matches.sort((a, b) => a.key1Idx - b.key1Idx);
}

/**
 * 対応結果に基づき key2 のストロークを並べ直して返す。
 *
 * orientation が -1 のストロークは点列を逆順にする。
 *
 * @param strokes2  キーフレーム 2 のストローク群
 * @param matches   matchStrokesOneToOne の結果
 * @returns         key1 と対応付けられた key2 のストロークリスト
 */
export function fixStrokeOrder(
  strokes2: Stroke[],
  matches: StrokeMatch[]
): Stroke[] {
  return matches.map(({ key2Idx, orientation }) => {
    const stroke = [...strokes2[key2Idx]];
    return orientation === -1 ? stroke.reverse() : stroke;
  });
}

/**
 * 自動ストローク対応パイプラインを実行する。
 *
 * 1. ストロークをリサンプリング
 * 2. Shape Context でコスト行列を計算
 * 3. 最小費用フローで点対応を決定
 * 4. ストローク対応を貪欲法で決定
 * 5. key2 を並べ直して返す
 *
 * @param strokes1  キーフレーム 1 のストローク群（元の描画データ）
 * @param strokes2  キーフレーム 2 のストローク群（元の描画データ）
 * @returns         並べ直した key2 ストロークと進捗コールバック
 */
export function runAutoCorrespondence(
  strokes1: Stroke[],
  strokes2: Stroke[]
): Stroke[] {
  // リサンプリング
  const r1 = strokes1.map((s) => resampleStroke(s, 4));
  const r2 = strokes2.map((s) => resampleStroke(s, 4));

  // Shape Context + コスト行列
  const { costMatrix, m1, m2 } = buildCostMatrix(r1, r2, 16);

  // 最小費用フロー
  const { match } = solveMinCostFlow(costMatrix);

  // ストローク行列を計算（リサンプリング後の点数に合わせる）
  const { strokeMatrix, seqMatrix } = computeStrokeMatrices(r1, r2, match);

  // 一対一対応
  const nStrokes = Math.min(strokes1.length, strokes2.length);
  const matches = matchStrokesOneToOne(strokeMatrix, seqMatrix, nStrokes);

  // key2 を並べ直す（元の解像度で）
  return fixStrokeOrder(strokes2, matches);

  void m1; void m2; // 未使用警告を抑制
}
