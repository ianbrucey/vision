/**
 * Dynamic View System — TypeScript type definitions.
 *
 * Mirrors the JSON Schema at context-engine/specs/dynamic-view-system/01-view-envelope-schema.json
 * and the backend validation at backend/schemas/view_envelope.py.
 */

/* ------------------------------------------------------------------ */
/* View Envelope                                                      */
/* ------------------------------------------------------------------ */

export interface ViewEnvelope {
  documentMetadata: DocumentMetadata;
  views: ViewDefinition[];
}

export interface DocumentMetadata {
  title: string;
  sourceId?: string;
  lastUpdated?: string;
}

/* ------------------------------------------------------------------ */
/* View Definitions (discriminated union on viewType)                 */
/* ------------------------------------------------------------------ */

export type ViewDefinition = TableView | ListView | CardsView | ChartView;

export interface TableView {
  viewType: "table";
  title: string;
  description?: string;
  data: TableData;
}

export interface ListView {
  viewType: "list";
  title: string;
  description?: string;
  data: ListData;
}

export interface CardsView {
  viewType: "cards";
  title: string;
  description?: string;
  data: CardsData;
}

export interface ChartView {
  viewType: "chart";
  title: string;
  description?: string;
  data: ChartData;
}

/* ------------------------------------------------------------------ */
/* Per-View Data Shapes                                               */
/* ------------------------------------------------------------------ */

export interface TableData {
  headers: string[];
  rows: TableRow[];
}

/** A table row. id is required; all other keys are string column values. */
export interface TableRow {
  id: string;
  [column: string]: string;
}

export type ListStyle = "checkbox" | "ordered" | "bullet";

export interface ListData {
  listStyle: ListStyle;
  items: ListItem[];
}

export interface ListItem {
  id: string;
  text: string;
  completed?: boolean;
  notes?: string;
}

export type Emphasis = "default" | "warning" | "danger" | "success" | "info";

export interface CardsData {
  pairs: CardPair[];
}

export interface CardPair {
  key: string;
  value: string;
  emphasis?: Emphasis;
}

export type ChartType = "bar" | "line" | "pie";

/** Chart reuses table's {headers, rows} structure — same data, different render.
 *  This makes table↔chart fully non-lossy (only viewType changes on switch). */
export interface ChartData {
  chartType: ChartType;
  headers: string[];
  rows: TableRow[];
}

/* ------------------------------------------------------------------ */
/* View Compatibility                                                 */
/* ------------------------------------------------------------------ */

/** Which viewTypes can be switched to client-side from a given viewType.
 *  Only includes non-lossy transforms.
 *  table↔chart: same {headers, rows} data — only viewType changes. */
export const COMPATIBLE_VIEWS: Record<string, string[]> = {
  table: ["chart"],
  chart: ["table"],
  cards: [],
  list: [],
};

export function canSwitchView(
  from: string,
  to: string,
): boolean {
  return (COMPATIBLE_VIEWS[from] ?? []).includes(to);
}
