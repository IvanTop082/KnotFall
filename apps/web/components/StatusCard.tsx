type StatusCardTone = "neutral" | "good" | "warn" | "danger";

interface StatusCardProps {
  label: string;
  value: string | number;
  detail?: string;
  tone?: StatusCardTone;
}

const toneClasses: Record<StatusCardTone, string> = {
  neutral: "border-slate-700 bg-slate-900/70 text-slate-100",
  good: "border-emerald-500/50 bg-emerald-500/10 text-emerald-100",
  warn: "border-orange-500/50 bg-orange-500/10 text-orange-100",
  danger: "border-red-500/50 bg-red-500/10 text-red-100",
};

export default function StatusCard({
  label,
  value,
  detail,
  tone = "neutral",
}: StatusCardProps) {
  return (
    <section className={`rounded-lg border p-4 ${toneClasses[tone]}`}>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      {detail ? <p className="mt-1 text-sm text-slate-300">{detail}</p> : null}
    </section>
  );
}
