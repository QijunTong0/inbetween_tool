/**
 * ストロークを描画するキャンバスコンポーネント。
 *
 * Mode 0: マウスドラッグで連続した線を描く。
 * Mode 1: クリックで点を置いてストロークを構成する。
 */

import {
  useRef,
  useEffect,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from "react";
import type { DrawMode, Point, Stroke } from "../types";
import { extractDominantPoints } from "../lib/dominantPoints";
import { pchipInterpolate } from "../lib/interpolation";

const INTERP_STEPS = 60;
const DOT_RADIUS = 3;
const DOT_COLOR = "#fa3253";
const STROKE_COLOR = "#000000";
const INTERP_COLOR = "#5998ff";
const DOMINANT_COLOR = "#6ef442";

export interface StrokeCanvasHandle {
  /** 現在のストローク群を取得する */
  getStrokes: () => Stroke[];
  /** ストロークを外部からセットする（自動中割り後の key2 書き換え用） */
  setStrokes: (strokes: Stroke[]) => void;
  /** 全描画をリセットする */
  clear: () => void;
  /** 補間ストロークを描画する */
  drawInterpolated: (mode: DrawMode) => void;
}

interface Props {
  /** キャンバスの一辺のピクセル数 */
  size: number;
  mode: DrawMode;
  /** ストローク追加時のコールバック（任意） */
  onStrokesChange?: (strokes: Stroke[]) => void;
}

const StrokeCanvas = forwardRef<StrokeCanvasHandle, Props>(
  ({ size, mode, onStrokesChange }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const strokesRef = useRef<Stroke[]>([]);
    const drawingRef = useRef(false);

    /** Canvas の 2D コンテキストを取得する（内部ユーティリティ） */
    const ctx = useCallback(
      () => canvasRef.current?.getContext("2d") ?? null,
      []
    );

    /** キャンバスを白で初期化する */
    const initCanvas = useCallback(() => {
      const c = ctx();
      if (!c) return;
      c.fillStyle = "#ffffff";
      c.fillRect(0, 0, size, size);
    }, [ctx, size]);

    useEffect(() => {
      initCanvas();
    }, [initCanvas]);

    /** 点を赤い丸で描画する */
    const drawDot = useCallback(
      (c: CanvasRenderingContext2D, x: number, y: number, color = DOT_COLOR) => {
        c.beginPath();
        c.arc(x, y, DOT_RADIUS, 0, Math.PI * 2);
        c.fillStyle = color;
        c.fill();
      },
      []
    );

    /** ストロークラベルを描画する */
    const drawLabel = useCallback(
      (c: CanvasRenderingContext2D, stroke: Stroke, label: string) => {
        if (stroke.length === 0) return;
        const [x, y] = stroke[0];
        c.fillStyle = "#333";
        c.font = "12px sans-serif";
        c.fillText(label, x - 10, y - 8);
      },
      []
    );

    /** 全ストロークを黒い線で再描画する */
    const redrawAll = useCallback(() => {
      const c = ctx();
      if (!c) return;
      initCanvas();
      for (const stroke of strokesRef.current) {
        if (stroke.length < 2) continue;
        c.beginPath();
        c.moveTo(stroke[0][0], stroke[0][1]);
        for (let i = 1; i < stroke.length; i++) {
          c.lineTo(stroke[i][0], stroke[i][1]);
        }
        c.strokeStyle = STROKE_COLOR;
        c.lineWidth = 1.5;
        c.stroke();
      }
    }, [ctx, initCanvas]);

    // ---- Imperative API ----

    useImperativeHandle(
      ref,
      () => ({
        getStrokes: () => strokesRef.current,

        setStrokes: (strokes: Stroke[]) => {
          strokesRef.current = strokes;
          redrawAll();
        },

        clear: () => {
          strokesRef.current = [];
          initCanvas();
          onStrokesChange?.([]);
        },

        drawInterpolated: (m: DrawMode) => {
          const c = ctx();
          if (!c) return;
          redrawAll();

          for (const stroke of strokesRef.current) {
            if (stroke.length < 2) continue;

            const controlPts =
              m === 0 ? extractDominantPoints(stroke) : stroke;

            // 優勢点を緑の丸で表示
            if (m === 0) {
              for (const pt of controlPts) {
                drawDot(c, pt[0], pt[1], DOMINANT_COLOR);
              }
            }

            // PCHIP 補間曲線を青で描画
            const pts: Point[] = Array.from({ length: INTERP_STEPS }, (_, i) =>
              pchipInterpolate(controlPts, i / (INTERP_STEPS - 1))
            );

            c.beginPath();
            c.moveTo(pts[0][0], pts[0][1]);
            for (let i = 1; i < pts.length; i++) {
              c.lineTo(pts[i][0], pts[i][1]);
            }
            c.strokeStyle = INTERP_COLOR;
            c.lineWidth = 1.5;
            c.stroke();
          }
        },
      }),
      [ctx, initCanvas, redrawAll, drawDot, onStrokesChange]
    );

    // ---- マウスイベントハンドラ ----

    const handleMouseDown = useCallback(
      (e: React.MouseEvent<HTMLCanvasElement>) => {
        const c = ctx();
        if (!c) return;
        const { offsetX: x, offsetY: y } = e.nativeEvent;

        if (mode === 1) {
          // Mode 1: 最初のクリックで新規ストロークを開始
          if (strokesRef.current.length === 0) {
            strokesRef.current.push([]);
          }
          strokesRef.current[strokesRef.current.length - 1].push([x, y]);
          drawDot(c, x, y);
          onStrokesChange?.([...strokesRef.current]);
        } else {
          // Mode 0: ドラッグ開始
          drawingRef.current = true;
          strokesRef.current.push([[x, y]]);
        }
      },
      [ctx, mode, drawDot, onStrokesChange]
    );

    const handleMouseMove = useCallback(
      (e: React.MouseEvent<HTMLCanvasElement>) => {
        if (mode !== 0 || !drawingRef.current) return;
        const c = ctx();
        if (!c) return;
        const { offsetX: x, offsetY: y } = e.nativeEvent;
        const stroke = strokesRef.current[strokesRef.current.length - 1];
        const prev = stroke[stroke.length - 1];

        c.beginPath();
        c.moveTo(prev[0], prev[1]);
        c.lineTo(x, y);
        c.strokeStyle = STROKE_COLOR;
        c.lineWidth = 1.5;
        c.stroke();

        stroke.push([x, y]);
        onStrokesChange?.([...strokesRef.current]);
      },
      [ctx, mode, onStrokesChange]
    );

    const handleMouseUp = useCallback(
      (e: React.MouseEvent<HTMLCanvasElement>) => {
        if (mode !== 0 || !drawingRef.current) return;
        drawingRef.current = false;
        const c = ctx();
        if (!c) return;
        const strokes = strokesRef.current;
        if (strokes.length > 0 && strokes[strokes.length - 1].length > 0) {
          drawLabel(c, strokes[strokes.length - 1], `L${strokes.length}`);
        }
        onStrokesChange?.([...strokesRef.current]);
        void e;
      },
      [ctx, mode, drawLabel, onStrokesChange]
    );

    const handleRightClick = useCallback(
      (e: React.MouseEvent<HTMLCanvasElement>) => {
        e.preventDefault();
        if (mode !== 1) return;
        const c = ctx();
        if (!c) return;
        const strokes = strokesRef.current;
        if (strokes.length > 0 && strokes[strokes.length - 1].length > 0) {
          drawLabel(c, strokes[strokes.length - 1], `L${strokes.length}`);
          strokes.push([]);
        }
        onStrokesChange?.([...strokesRef.current]);
      },
      [ctx, mode, drawLabel, onStrokesChange]
    );

    return (
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{ border: "1px solid #ccc", cursor: "crosshair" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onContextMenu={handleRightClick}
      />
    );
  }
);

StrokeCanvas.displayName = "StrokeCanvas";

export default StrokeCanvas;
