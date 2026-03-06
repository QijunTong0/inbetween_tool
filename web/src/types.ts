/** [x, y] 座標の型 */
export type Point = [number, number];

/** 点列（ストローク）の型 */
export type Stroke = Point[];

/** 描画モード: 0 = ドラッグで線、1 = クリックで点 */
export type DrawMode = 0 | 1;
