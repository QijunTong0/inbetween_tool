/**
 * アニメーション中割りツールのメインコンポーネント。
 *
 * 3 つのキャンバス（key1・inbetween・key2）を管理し、
 * ストローク描画・補間表示・中割りアニメーション・自動対応を提供する。
 */

import { useRef, useState, useCallback } from "react";
import type { DrawMode } from "./types";
import StrokeCanvas, { type StrokeCanvasHandle } from "./components/StrokeCanvas";
import InbetweenCanvas, {
  type InbetweenCanvasHandle,
} from "./components/InbetweenCanvas";
import { runAutoCorrespondence } from "./lib/strokeCorrespondence";

const CANVAS_SIZE = 384;

function App() {
  const key1Ref = useRef<StrokeCanvasHandle>(null);
  const key2Ref = useRef<StrokeCanvasHandle>(null);
  const inbetRef = useRef<InbetweenCanvasHandle>(null);

  const [mode, setMode] = useState<DrawMode>(0);
  const [status, setStatus] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);

  /** 補間ストロークを各キャンバスに描画する */
  const handleInterpolate = useCallback(() => {
    key1Ref.current?.drawInterpolated(mode);
    key2Ref.current?.drawInterpolated(mode);
  }, [mode]);

  /** 手動中割り: key1 と key2 のストロークを線形補間してアニメーション再生 */
  const handleInbetween = useCallback(() => {
    const s1 = key1Ref.current?.getStrokes() ?? [];
    const s2 = key2Ref.current?.getStrokes() ?? [];

    if (s1.length === 0 || s2.length === 0) {
      setStatus("エラー: 両方のキャンバスにストロークを描いてください");
      return;
    }
    if (s1.length !== s2.length) {
      setStatus(
        `エラー: 線の本数が一致しません (key1: ${s1.length}, key2: ${s2.length})`
      );
      return;
    }
    setStatus("");
    inbetRef.current?.play(s1, s2);
  }, []);

  /** 自動中割り: Shape Context + 最小費用フローでストローク対応を求めてアニメーション再生 */
  const handleAutoInbetween = useCallback(async () => {
    const s1 = key1Ref.current?.getStrokes() ?? [];
    const s2 = key2Ref.current?.getStrokes() ?? [];

    if (s1.length === 0 || s2.length === 0) {
      setStatus("エラー: 両方のキャンバスにストロークを描いてください");
      return;
    }

    setStatus("自動対応を計算中...");
    setIsProcessing(true);

    // 重い計算を setTimeout でメインスレッドから分離（UI をフリーズさせない）
    await new Promise<void>((resolve) => {
      setTimeout(() => {
        try {
          const fixedS2 = runAutoCorrespondence(s1, s2);
          key2Ref.current?.setStrokes(fixedS2);
          inbetRef.current?.play(s1, fixedS2);
          setStatus("自動対応完了");
        } catch (err) {
          setStatus(`エラー: ${err instanceof Error ? err.message : String(err)}`);
        } finally {
          setIsProcessing(false);
          resolve();
        }
      }, 0);
    });
  }, []);

  /** 全ストロークと中割りをリセットする */
  const handleDelete = useCallback(() => {
    key1Ref.current?.clear();
    key2Ref.current?.clear();
    inbetRef.current?.clear();
    setStatus("");
  }, []);

  return (
    <div style={styles.root}>
      <h2 style={styles.title}>中割りツール</h2>

      {/* キャンバス群 */}
      <div style={styles.canvasRow}>
        <div style={styles.canvasWrapper}>
          <div style={styles.canvasLabel}>Key Frame 1</div>
          <StrokeCanvas
            ref={key1Ref}
            size={CANVAS_SIZE}
            mode={mode}
          />
        </div>

        <div style={styles.canvasWrapper}>
          <div style={styles.canvasLabel}>In-between</div>
          <InbetweenCanvas ref={inbetRef} size={CANVAS_SIZE} />
        </div>

        <div style={styles.canvasWrapper}>
          <div style={styles.canvasLabel}>Key Frame 2</div>
          <StrokeCanvas
            ref={key2Ref}
            size={CANVAS_SIZE}
            mode={mode}
          />
        </div>
      </div>

      {/* コントロールパネル */}
      <div style={styles.controls}>
        {/* モード選択 */}
        <div style={styles.modeGroup}>
          <span style={styles.modeLabel}>Mode:</span>
          <label style={styles.radioLabel}>
            <input
              type="radio"
              name="mode"
              value={0}
              checked={mode === 0}
              onChange={() => setMode(0)}
            />
            {" 0: ドラッグ（線）"}
          </label>
          <label style={styles.radioLabel}>
            <input
              type="radio"
              name="mode"
              value={1}
              checked={mode === 1}
              onChange={() => setMode(1)}
            />
            {" 1: クリック（点）"}
          </label>
        </div>

        {/* ボタン群 */}
        <div style={styles.buttonGroup}>
          <button style={styles.btnBlue} onClick={handleInterpolate}>
            補間
          </button>
          <button style={styles.btnOrange} onClick={handleInbetween}>
            中割り
          </button>
          <button
            style={{ ...styles.btnGreen, opacity: isProcessing ? 0.5 : 1 }}
            onClick={handleAutoInbetween}
            disabled={isProcessing}
          >
            {isProcessing ? "計算中..." : "自動中割り"}
          </button>
          <button style={styles.btnGray} onClick={handleDelete}>
            消去
          </button>
        </div>

        {/* 操作説明 */}
        <div style={styles.help}>
          {mode === 0
            ? "左ドラッグ: 描画 ／ 離す: ストローク確定"
            : "左クリック: 点追加 ／ 右クリック: ストローク確定"}
        </div>
      </div>

      {/* ステータスバー */}
      {status && (
        <div
          style={{
            ...styles.status,
            color: status.startsWith("エラー") ? "#c00" : "#060",
          }}
        >
          {status}
        </div>
      )}
    </div>
  );
}

// ---- インラインスタイル ----

const styles = {
  root: {
    fontFamily: "sans-serif",
    padding: "16px",
    userSelect: "none" as const,
  },
  title: {
    margin: "0 0 12px",
    fontSize: "1.2rem",
    color: "#333",
  },
  canvasRow: {
    display: "flex",
    gap: "12px",
    alignItems: "flex-start",
  },
  canvasWrapper: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    gap: "4px",
  },
  canvasLabel: {
    fontSize: "0.8rem",
    color: "#666",
    fontWeight: "bold" as const,
  },
  controls: {
    marginTop: "16px",
    display: "flex",
    flexDirection: "column" as const,
    gap: "10px",
  },
  modeGroup: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
  },
  modeLabel: {
    fontWeight: "bold" as const,
    color: "#444",
  },
  radioLabel: {
    cursor: "pointer",
    color: "#444",
    fontSize: "0.9rem",
  },
  buttonGroup: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap" as const,
  },
  btnBlue: {
    padding: "8px 20px",
    background: "#5998ff",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.95rem",
  },
  btnOrange: {
    padding: "8px 20px",
    background: "#f78e80",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.95rem",
  },
  btnGreen: {
    padding: "8px 20px",
    background: "#4caf50",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.95rem",
  },
  btnGray: {
    padding: "8px 20px",
    background: "#888",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.95rem",
  },
  help: {
    fontSize: "0.8rem",
    color: "#888",
  },
  status: {
    marginTop: "8px",
    fontSize: "0.9rem",
    fontWeight: "bold" as const,
  },
} as const;

export default App;
