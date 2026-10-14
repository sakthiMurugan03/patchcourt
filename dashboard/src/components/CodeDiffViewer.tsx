"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

// Monaco touches `window`, so it must never render on the server.
const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.DiffEditor),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[240px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading diff viewer…
      </div>
    ),
  },
);

export type CodeDiffViewerProps = {
  /** Base/old version of the snippet. */
  original: string;
  /** Head/new version of the snippet. */
  modified: string;
  /** Monaco language id, e.g. "python", "typescript". */
  language?: string;
  /** CSS height of the editor container. */
  height?: string | number;
  className?: string;
};

/** Side-by-side diff of an analyzed snippet using Monaco's DiffEditor. */
export function CodeDiffViewer({
  original,
  modified,
  language = "plaintext",
  height = "420px",
  className,
}: CodeDiffViewerProps) {
  return (
    <div className={className} style={{ height }}>
      <DiffEditor
        original={original}
        modified={modified}
        language={language}
        theme="vs-dark"
        height="100%"
        options={{
          readOnly: true,
          renderSideBySide: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          renderOverviewRuler: false,
          fontSize: 12,
        }}
      />
    </div>
  );
}
