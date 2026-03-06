/**
 * 中割りアニメーションを表示するキャンバスコンポーネント。
 *
 * 2 つのストローク群の間を線形補間してアニメーションを再生する。
 * requestAnimationFrame で 60fps のアニメーションを実装する。
 */

import { useRef, useCallback, forwardRef, useImperativeHandle } from "react";
import type { Stroke } from "../types";
import { pchipInterpolate } from "../lib/interpolation";

const INTERP_STEPS = 60;
const ANIMATION_FRAMES = 100;

export interface InbetweenCanvasHandle {
  /** アニメーションを開始する */
  play: (strokes1: Stroke[], strokes2: Stroke[]) => void;
  /** 描画をクリアする */
  clear: () => void;
}

interface Props {
  size: number;
}

const InbetweenCanvas = forwardRef<InbetweenCanvasHandle, Props>(
  ({ size }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rafRef = useRef<number | null>(null);

    const ctx = useCallback(
      () => canvasRef.current?.getContext("2d") ?? null,
      []
    );

    const clearCanvas = useCallback(() => {
      const c = ctx();
      if (!c) return;
      c.fillStyle = "#ffffff";
      c.fillRect(0, 0, size, size);
    }, [ctx, size]);

    useImperativeHandle(ref, () => ({
      clear: () => {
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
        }
        clearCanvas();
      },

      play: (strokes1: Stroke[], strokes2: Stroke[]) => {
        // 実行中のアニメーションをキャンセル
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
        }

        // 各ストロークの補間点列を事前計算
        const ts = Array.from(
          { length: INTERP_STEPS },
          (_, i) => i / (INTERP_STEPS - 1)
        );
        const pts1 = strokes1.map((s) => ts.map((t) => pchipInterpolate(s, t)));
        const pts2 = strokes2.map((s) => ts.map((t) => pchipInterpolate(s, t)));

        let frame = 0;

        const tick = () => {
          const c = ctx();
          if (!c) return;

          clearCanvas();

          const alpha = frame / (ANIMATION_FRAMES - 1);

          for (let si = 0; si < pts1.length; si++) {
            const p1 = pts1[si];
            const p2 = pts2[si];

            c.beginPath();
            for (let i = 0; i < p1.length; i++) {
              const x = p1[i][0] + alpha * (p2[i][0] - p1[i][0]);
              const y = p1[i][1] + alpha * (p2[i][1] - p1[i][1]);
              if (i === 0) c.moveTo(x, y);
              else c.lineTo(x, y);
            }
            c.strokeStyle = "#000000";
            c.lineWidth = 1.5;
            c.stroke();
          }

          frame++;
          if (frame < ANIMATION_FRAMES) {
            rafRef.current = requestAnimationFrame(tick);
          } else {
            rafRef.current = null;
          }
        };

        rafRef.current = requestAnimationFrame(tick);
      },
    }));

    return (
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{ border: "1px solid #ccc" }}
      />
    );
  }
);

InbetweenCanvas.displayName = "InbetweenCanvas";

export default InbetweenCanvas;
