import { Line, LineChart, ResponsiveContainer } from "recharts";

export function Sparkline({ data, accent = "primary" }: { data: number[]; accent?: string }) {
  const stroke = accent === "destructive" ? "hsl(var(--destructive))" :
                 accent === "success"     ? "hsl(var(--success))"     :
                 "hsl(var(--primary))";
  const points = data.map((v, i) => ({ i, v }));
  return (
    <div className="h-7 w-20">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points}>
          <Line type="monotone" dataKey="v" stroke={stroke} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
