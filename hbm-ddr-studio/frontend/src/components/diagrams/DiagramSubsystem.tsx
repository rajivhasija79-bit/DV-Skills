// Compact isometric diagram for the DDR/HBM subsystem. Theme-token aware.
// Updates as the user changes form fields.

export function DiagramSubsystem({
  protocol = "DDR5",
  phyVendor = "Synopsys",
  channels = 4,
  noc = "Custom",
  rasIp = "ECC",
  smmuIp = "ARM-MMU-700",
}: {
  protocol?: string;
  phyVendor?: string;
  channels?: number;
  noc?: string;
  rasIp?: string;
  smmuIp?: string;
}) {
  const blocks = [
    { x: 60,  y: 70,  w: 100, h: 56, label: "NoC",          sub: noc,      tone: "primary" },
    { x: 200, y: 70,  w: 110, h: 56, label: "SMMU",         sub: smmuIp,   tone: "muted" },
    { x: 350, y: 70,  w: 110, h: 56, label: "RAS",          sub: rasIp,    tone: "muted" },
    { x: 60,  y: 160, w: 400, h: 64, label: "DDR Controller", sub: protocol, tone: "primary" },
    { x: 60,  y: 250, w: 400, h: 56, label: `${phyVendor} PHY`, sub: `${channels} ch`, tone: "muted" },
  ];
  const channelW = 400 / channels;
  return (
    <div className="rounded-lg border border-border bg-card/40 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Subsystem preview
        </div>
        <div className="font-mono text-[11px] text-muted-foreground">
          {protocol} · {phyVendor} · {channels}ch
        </div>
      </div>
      <svg viewBox="0 0 520 340" className="w-full">
        {/* connectors */}
        <g stroke="hsl(var(--border))" strokeWidth="1.5" fill="none">
          <line x1="110" y1="126" x2="110" y2="160" />
          <line x1="255" y1="126" x2="255" y2="160" />
          <line x1="405" y1="126" x2="405" y2="160" />
          <line x1="260" y1="224" x2="260" y2="250" />
        </g>
        {blocks.map((b) => (
          <g key={b.label} transform={`translate(${b.x}, ${b.y})`}>
            <rect
              width={b.w} height={b.h} rx="8"
              fill={b.tone === "primary" ? "hsl(var(--primary) / 0.18)" : "hsl(var(--muted) / 0.6)"}
              stroke={b.tone === "primary" ? "hsl(var(--primary))" : "hsl(var(--border))"}
              strokeWidth="1.5"
            />
            <text x={b.w / 2} y={22} textAnchor="middle" fontSize="13" fontWeight="600"
              fill="hsl(var(--card-foreground))">{b.label}</text>
            <text x={b.w / 2} y={40} textAnchor="middle" fontSize="11"
              fill="hsl(var(--muted-foreground))">{b.sub}</text>
          </g>
        ))}
        {/* per-channel ticks under PHY */}
        {Array.from({ length: channels }).map((_, i) => (
          <rect key={i}
            x={60 + i * channelW + 4} y={310}
            width={channelW - 8} height={10} rx="3"
            fill="hsl(var(--primary) / 0.3)" stroke="hsl(var(--primary))" strokeWidth="1" />
        ))}
      </svg>
    </div>
  );
}
