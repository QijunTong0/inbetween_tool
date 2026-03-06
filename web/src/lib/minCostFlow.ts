/**
 * SPFA（Shortest Path Faster Algorithm）ベースの最小費用フローモジュール。
 *
 * Successive Shortest Path アルゴリズムで最小費用最大流を求める。
 * Python の solve_min_cost_flow() 関数に相当する。
 *
 * グラフ構造（類似度行列が m×n の場合）:
 *   - ノード 0: ソース
 *   - ノード 1..m: キーフレーム 1 の点
 *   - ノード m+1..m+n: キーフレーム 2 の点
 *   - ノード m+n+1: シンク
 */

/** 有向グラフのエッジ */
interface Edge {
  to: number;
  cap: number;  // 残余容量
  cost: number; // 単位コスト
  rev: number;  // 逆辺のインデックス
}

/**
 * 有向グラフを構築してエッジを追加する。
 *
 * @param graph  グラフ（各ノードのエッジリスト）
 * @param from   始点ノード番号
 * @param to     終点ノード番号
 * @param cap    容量
 * @param cost   コスト
 */
function addEdge(
  graph: Edge[][],
  from: number,
  to: number,
  cap: number,
  cost: number
): void {
  graph[from].push({ to, cap, cost, rev: graph[to].length });
  graph[to].push({ to: from, cap: 0, cost: -cost, rev: graph[from].length - 1 });
}

/**
 * SPFA（キューを使った Bellman-Ford）で最短経路を求める。
 *
 * @param graph   グラフ
 * @param source  ソースノード
 * @param sink    シンクノード
 * @param n       ノード数
 * @returns       (prev: 直前ノード, prevEdge: 直前エッジ番号, dist: 最短距離) または null（到達不可）
 */
function spfa(
  graph: Edge[][],
  source: number,
  sink: number,
  n: number
): { prev: number[]; prevEdge: number[]; dist: number[] } | null {
  const INF = 1e15;
  const dist = new Array<number>(n).fill(INF);
  const inQueue = new Array<boolean>(n).fill(false);
  const prev = new Array<number>(n).fill(-1);
  const prevEdge = new Array<number>(n).fill(-1);

  dist[source] = 0;
  const queue: number[] = [source];
  inQueue[source] = true;

  while (queue.length > 0) {
    const u = queue.shift()!;
    inQueue[u] = false;

    for (let i = 0; i < graph[u].length; i++) {
      const e = graph[u][i];
      if (e.cap > 0 && dist[u] + e.cost < dist[e.to]) {
        dist[e.to] = dist[u] + e.cost;
        prev[e.to] = u;
        prevEdge[e.to] = i;
        if (!inQueue[e.to]) {
          queue.push(e.to);
          inQueue[e.to] = true;
        }
      }
    }
  }

  if (dist[sink] === INF) return null;
  return { prev, prevEdge, dist };
}

/**
 * 類似度行列を受け取り、最小費用フローで最適な点対応を求める。
 *
 * コスト = 1 - 類似度 として最小費用最大流を解く。
 * min(m, n) 単位のフローを流して一対一対応を得る。
 *
 * @param similarityMatrix  shape (m, n) の類似度行列（値は 0〜1）
 * @returns                 match[i][j] = true の点対応行列と転置フラグ
 */
export function solveMinCostFlow(similarityMatrix: number[][]): {
  match: boolean[][];
  transposed: boolean;
} {
  let cost = similarityMatrix.map((row) => row.map((v) => Math.round((1 - v) * 1000)));
  let m = cost.length;
  let n = cost[0].length;

  // 行 >= 列 になるよう調整
  let transposed = false;
  if (m < n) {
    cost = cost[0].map((_, j) => cost.map((row) => row[j]));
    [m, n] = [n, m];
    transposed = true;
  }

  // ノード: 0=source, 1..m=key1_points, m+1..m+n=key2_points, m+n+1=sink
  const SOURCE = 0;
  const SINK = m + n + 1;
  const totalNodes = m + n + 2;
  const graph: Edge[][] = Array.from({ length: totalNodes }, () => []);

  // source → key1_i
  for (let i = 0; i < m; i++) {
    addEdge(graph, SOURCE, i + 1, 1, 0);
  }

  // key1_i → key2_j
  for (let i = 0; i < m; i++) {
    for (let j = 0; j < n; j++) {
      addEdge(graph, i + 1, m + 1 + j, 1, cost[i][j]);
    }
  }

  // key2_j → sink（各 key2 点は最大 1 回対応）
  for (let j = 0; j < n; j++) {
    addEdge(graph, m + 1 + j, SINK, 1, 0);
  }

  // n 単位のフロー（少ない側に合わせる）を流す
  const match: boolean[][] = Array.from({ length: m }, () =>
    new Array<boolean>(n).fill(false)
  );

  for (let flow = 0; flow < n; flow++) {
    const result = spfa(graph, SOURCE, SINK, totalNodes);
    if (!result) break;

    // 最短経路に沿ってフローを 1 単位流す
    let cur = SINK;
    while (cur !== SOURCE) {
      const u = result.prev[cur];
      const ei = result.prevEdge[cur];
      graph[u][ei].cap--;
      graph[cur][graph[u][ei].rev].cap++;

      // key1_i → key2_j のエッジを記録
      if (u >= 1 && u <= m && cur >= m + 1 && cur <= m + n) {
        match[u - 1][cur - m - 1] = true;
      }
      cur = u;
    }
  }

  if (transposed) {
    // 転置前の次元に戻す (n×m → m×n は元の m×n)
    const origM = n;
    const origN = m;
    const unTransposed: boolean[][] = Array.from({ length: origM }, () =>
      new Array<boolean>(origN).fill(false)
    );
    for (let i = 0; i < m; i++) {
      for (let j = 0; j < n; j++) {
        if (match[i][j]) unTransposed[j][i] = true;
      }
    }
    return { match: unTransposed, transposed };
  }

  return { match, transposed };
}
