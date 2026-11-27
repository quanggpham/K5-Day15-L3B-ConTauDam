import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts"
import { CHART_COLORS } from "./chartColors"

const nf = new Intl.NumberFormat("vi-VN")

/** Phân bố lượt chấm lần đầu: đúng / sai (lượt chưa chấm ngoài mẫu số, hiện bằng chữ ở ngoài biểu đồ). */
export function DistributionChart({ correct, incorrect }: { correct: number; incorrect: number }) {
  const data = [
    { name: "Lượt đúng", value: correct, fill: CHART_COLORS.correct },
    { name: "Lượt sai", value: incorrect, fill: CHART_COLORS.incorrect },
  ]
  return (
    <div className="h-40 w-full" aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, bottom: 4, left: 4 }} accessibilityLayer={false}>
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: CHART_COLORS.axis }} />
          <YAxis type="category" dataKey="name" width={84} tickLine={false} tick={{ fontSize: 12, fill: CHART_COLORS.axis }} />
          <Bar dataKey="value" isAnimationActive={false} radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
            <LabelList dataKey="value" position="right" formatter={(v) => `${nf.format(Number(v))} lượt`} fontSize={12} fill={CHART_COLORS.axis} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
