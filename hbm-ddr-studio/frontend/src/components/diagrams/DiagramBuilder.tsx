// Visual subsystem builder. Drag block types from the palette onto the canvas,
// connect them, edit properties, and click "Apply to Form" to populate the
// existing rtl_subsystem_integration form with derived values.

import { useCallback, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2, Save, Wand2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Block catalog: which block "kinds" can be dropped on the canvas.
// ---------------------------------------------------------------------------

type BlockKind = {
  id: string;
  label: string;
  category: "memory" | "interconnect" | "safety" | "custom";
  // optional default sub-label / property values
  sub?: string;
  props?: Record<string, string>;
};

const DEFAULT_PALETTE: BlockKind[] = [
  // Memory
  { id: "ddr-controller", label: "DDR Controller", category: "memory",       sub: "DDR5", props: { protocol: "DDR5" } },
  { id: "hbm-controller", label: "HBM Controller", category: "memory",       sub: "HBM3", props: { protocol: "HBM3" } },
  { id: "phy",            label: "PHY",            category: "memory",       sub: "Synopsys", props: { phy_vendor: "Synopsys" } },
  { id: "channel",        label: "Memory Channel", category: "memory",       sub: "1 ch" },
  // Interconnect
  { id: "noc",            label: "NoC",            category: "interconnect", sub: "Custom", props: { noc: "Custom" } },
  { id: "axi-bridge",     label: "AXI Bridge",     category: "interconnect", sub: "AXI4" },
  { id: "crossbar",       label: "Crossbar",       category: "interconnect", sub: "" },
  // Safety / address translation
  { id: "ras",            label: "RAS",            category: "safety",       sub: "ECC", props: { ras_ip: "ECC" } },
  { id: "smmu",           label: "SMMU",           category: "safety",       sub: "ARM-MMU-700", props: { smmu_ip: "ARM-MMU-700" } },
  { id: "iommu",          label: "IOMMU",          category: "safety",       sub: "Generic" },
  // Custom
  { id: "custom",         label: "Custom Block",   category: "custom",       sub: "" },
];

const CATEGORY_LABEL: Record<BlockKind["category"], string> = {
  memory: "Memory",
  interconnect: "Interconnect",
  safety: "Safety / MMU",
  custom: "Custom",
};

// Visual styling per category — uses theme tokens so it matches the studio.
const CATEGORY_STYLE: Record<BlockKind["category"], { bg: string; border: string; chip: string }> = {
  memory:       { bg: "bg-primary/15",   border: "border-primary/60",   chip: "bg-primary/20 text-primary" },
  interconnect: { bg: "bg-accent/15",    border: "border-accent/60",    chip: "bg-accent/20 text-accent-foreground" },
  safety:       { bg: "bg-secondary/30", border: "border-secondary",    chip: "bg-secondary/60 text-secondary-foreground" },
  custom:       { bg: "bg-muted/40",     border: "border-border",       chip: "bg-muted text-muted-foreground" },
};

// ---------------------------------------------------------------------------
// Custom node renderer
// ---------------------------------------------------------------------------

type BlockNodeData = {
  label: string;
  sub?: string;
  category: BlockKind["category"];
  props?: Record<string, string>;
};

function BlockNode({ data, selected }: { data: BlockNodeData; selected: boolean }) {
  const s = CATEGORY_STYLE[data.category];
  return (
    <div
      className={[
        "min-w-[140px] rounded-lg border-2 px-3 py-2 shadow-sm transition-all",
        s.bg, s.border,
        selected ? "ring-2 ring-ring ring-offset-2 ring-offset-background" : "",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-semibold">{data.label}</div>
        <span className={["rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider", s.chip].join(" ")}>
          {data.category}
        </span>
      </div>
      {data.sub && <div className="mt-1 font-mono text-[11px] text-muted-foreground">{data.sub}</div>}
    </div>
  );
}

const nodeTypes = { block: BlockNode };

// ---------------------------------------------------------------------------
// Helpers: derive form values from the diagram
// ---------------------------------------------------------------------------

function deriveFormValues(nodes: Node<BlockNodeData>[]): Record<string, any> {
  const out: Record<string, any> = {};
  let channels = 0;
  for (const n of nodes) {
    const d = n.data;
    if (d?.props) Object.assign(out, d.props);
    if (n.id.startsWith("channel-") || d?.label === "Memory Channel") channels += 1;
  }
  if (channels > 0) out.channels = channels;
  return out;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

let nodeIdCounter = 1;
const nextNodeId = (kind: string) => `${kind}-${nodeIdCounter++}`;

export function DiagramBuilder({ onApply }: { onApply: (values: Record<string, any>) => void }) {
  return (
    <ReactFlowProvider>
      <DiagramBuilderInner onApply={onApply} />
    </ReactFlowProvider>
  );
}

function DiagramBuilderInner({ onApply }: { onApply: (values: Record<string, any>) => void }) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [palette, setPalette] = useState<BlockKind[]>(DEFAULT_PALETTE);
  const [nodes, setNodes, onNodesChange] = useNodesState<BlockNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Add-new-block-type form state
  const [newKindLabel, setNewKindLabel] = useState("");
  const [newKindCat, setNewKindCat] = useState<BlockKind["category"]>("custom");

  const onConnect = useCallback(
    (c: Connection) => setEdges((eds) => addEdge({ ...c, animated: true }, eds)),
    [setEdges],
  );

  const onDragStart = (e: React.DragEvent, kind: BlockKind) => {
    e.dataTransfer.setData("application/diagram-kind", JSON.stringify(kind));
    e.dataTransfer.effectAllowed = "move";
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const raw = e.dataTransfer.getData("application/diagram-kind");
    if (!raw || !rfInstance || !wrapperRef.current) return;
    const kind: BlockKind = JSON.parse(raw);
    const bounds = wrapperRef.current.getBoundingClientRect();
    const position = rfInstance.project({
      x: e.clientX - bounds.left,
      y: e.clientY - bounds.top,
    });
    const id = nextNodeId(kind.id);
    const node: Node<BlockNodeData> = {
      id,
      type: "block",
      position,
      data: {
        label: kind.label,
        sub: kind.sub,
        category: kind.category,
        props: kind.props ? { ...kind.props } : undefined,
      },
    };
    setNodes((ns) => ns.concat(node));
  };

  const selected = useMemo(() => nodes.find((n) => n.id === selectedId) || null, [nodes, selectedId]);

  function updateSelected(patch: Partial<BlockNodeData>) {
    if (!selectedId) return;
    setNodes((ns) =>
      ns.map((n) => (n.id === selectedId ? { ...n, data: { ...n.data, ...patch } } : n)),
    );
  }

  function deleteSelected() {
    if (!selectedId) return;
    setNodes((ns) => ns.filter((n) => n.id !== selectedId));
    setEdges((es) => es.filter((e) => e.source !== selectedId && e.target !== selectedId));
    setSelectedId(null);
  }

  function clearAll() {
    setNodes([]);
    setEdges([]);
    setSelectedId(null);
  }

  function applyToForm() {
    onApply(deriveFormValues(nodes));
  }

  function addCustomKind() {
    const label = newKindLabel.trim();
    if (!label) return;
    const id = label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || `kind-${Date.now()}`;
    setPalette((p) => p.concat({ id, label, category: newKindCat, sub: "" }));
    setNewKindLabel("");
  }

  // Group palette by category for display
  const grouped = useMemo(() => {
    const out: Record<BlockKind["category"], BlockKind[]> = {
      memory: [], interconnect: [], safety: [], custom: [],
    };
    for (const k of palette) out[k.category].push(k);
    return out;
  }, [palette]);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-[220px_minmax(0,1fr)_260px]">
      {/* Palette ------------------------------------------------------------ */}
      <aside className="rounded-lg border border-border bg-card/40 p-3">
        <div className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Palette
        </div>
        <div className="space-y-3">
          {(Object.keys(grouped) as BlockKind["category"][]).map((cat) => (
            <div key={cat}>
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {CATEGORY_LABEL[cat]}
              </div>
              <div className="flex flex-col gap-1.5">
                {grouped[cat].map((k) => {
                  const s = CATEGORY_STYLE[k.category];
                  return (
                    <div
                      key={k.id}
                      draggable
                      onDragStart={(e) => onDragStart(e, k)}
                      className={["cursor-grab rounded-md border px-2 py-1.5 text-xs font-medium active:cursor-grabbing", s.bg, s.border].join(" ")}
                      title="Drag onto the canvas"
                    >
                      {k.label}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Add new block type ------------------------------------------------ */}
        <div className="mt-4 rounded-md border border-dashed border-border p-2">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Add new block type
          </div>
          <Input
            value={newKindLabel}
            placeholder="e.g. DMA Engine"
            onChange={(e) => setNewKindLabel(e.target.value)}
            className="h-8 text-xs"
          />
          <Select value={newKindCat} onValueChange={(v) => setNewKindCat(v as BlockKind["category"])}>
            <SelectTrigger className="mt-1.5 h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="memory">Memory</SelectItem>
              <SelectItem value="interconnect">Interconnect</SelectItem>
              <SelectItem value="safety">Safety / MMU</SelectItem>
              <SelectItem value="custom">Custom</SelectItem>
            </SelectContent>
          </Select>
          <Button size="sm" variant="secondary" onClick={addCustomKind} className="mt-1.5 w-full">
            <Plus className="mr-1.5 h-3.5 w-3.5" /> Add
          </Button>
        </div>
      </aside>

      {/* Canvas ------------------------------------------------------------- */}
      <div
        ref={wrapperRef}
        onDrop={onDrop}
        onDragOver={onDragOver}
        className="relative h-[520px] rounded-lg border border-border bg-card/20"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setRfInstance}
          onNodeClick={(_, n) => setSelectedId(n.id)}
          onPaneClick={() => setSelectedId(null)}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode={["Backspace", "Delete"]}
        >
          <Background gap={16} />
          <MiniMap pannable zoomable />
          <Controls />
        </ReactFlow>

        {nodes.length === 0 && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
            Drag blocks from the palette onto the canvas to design your subsystem.
          </div>
        )}
      </div>

      {/* Properties + actions ---------------------------------------------- */}
      <aside className="rounded-lg border border-border bg-card/40 p-3">
        <div className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Properties
        </div>
        {selected ? (
          <div className="space-y-2">
            <div>
              <Label className="text-xs">Label</Label>
              <Input
                value={selected.data.label}
                onChange={(e) => updateSelected({ label: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
            <div>
              <Label className="text-xs">Sub-label</Label>
              <Input
                value={selected.data.sub || ""}
                onChange={(e) => updateSelected({ sub: e.target.value })}
                className="h-8 text-xs"
                placeholder="e.g. DDR5, 4ch"
              />
            </div>
            {selected.data.props && Object.keys(selected.data.props).length > 0 && (
              <div className="rounded-md border border-border bg-muted/30 p-2">
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Form-mapped props
                </div>
                {Object.entries(selected.data.props).map(([k, v]) => (
                  <div key={k} className="mb-1.5">
                    <Label className="text-xs">{k}</Label>
                    <Input
                      value={v}
                      onChange={(e) =>
                        updateSelected({ props: { ...selected.data.props, [k]: e.target.value } })
                      }
                      className="h-7 text-xs"
                    />
                  </div>
                ))}
              </div>
            )}
            <Button size="sm" variant="destructive" onClick={deleteSelected} className="w-full">
              <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Delete block
            </Button>
          </div>
        ) : (
          <div className="text-xs text-muted-foreground">
            Click a block on the canvas to edit its properties.
          </div>
        )}

        <div className="mt-4 space-y-1.5 border-t border-border pt-3">
          <Button size="sm" onClick={applyToForm} className="w-full" disabled={nodes.length === 0}>
            <Wand2 className="mr-1.5 h-3.5 w-3.5" /> Apply to Form
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              const json = JSON.stringify({ nodes, edges }, null, 2);
              localStorage.setItem("hds.subsystem.diagram", json);
            }}
            className="w-full"
            disabled={nodes.length === 0}
          >
            <Save className="mr-1.5 h-3.5 w-3.5" /> Save (local)
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              const raw = localStorage.getItem("hds.subsystem.diagram");
              if (!raw) return;
              try {
                const parsed = JSON.parse(raw);
                setNodes(parsed.nodes || []);
                setEdges(parsed.edges || []);
              } catch { /* ignore */ }
            }}
            className="w-full"
          >
            Load saved
          </Button>
          <Button size="sm" variant="ghost" onClick={clearAll} className="w-full">
            Clear canvas
          </Button>
        </div>
      </aside>
    </div>
  );
}
