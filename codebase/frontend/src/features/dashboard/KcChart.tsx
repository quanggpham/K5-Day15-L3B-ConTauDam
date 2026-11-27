import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { CHART_COLORS } from "./chartColors"
import type { KcChartRow } from "./kcData"

const ROW_HEIGHT = 40
const percentFormat = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 0, maximumFractionDigits: 1 })

interface TickProps {
  x?: number | string
  y?: number | string
  payload?: { value: string }
}

/** Nhãn trục KC: KC chưa đủ dữ liệu có dòng chữ thứ hai (không chỉ phân biệt bằng màu). */
function makeTick(lowKcs: Set<string>) {
  return function KcTick({ x: rawX = 0, y: rawY = 0, payload }: TickProps) {
    const x = Number(rawX)
    const y = Number(rawY)
    const code = payload?.value ?? ""
    const low = lowKcs.has(code)
    return (
      <text x={x - 6} y={y} textAnchor="end" fill={CHART_COLORS.axis} fontSize={12}>
        <tspan x={x - 6} dy={low ? "-0.2em" : "0.35em"} fontWeight={600}>
          {code}
        </tspan>
        {low && (
          <tspan x={x - 6} dy="1.2em" fontSize={10}>
            chưa đủ dữ liệu
          </tspan>
        )}
      </text>
    )
  }
}

/** Biểu đồ cột ngang: tỷ lệ sai theo KC. Cột đặc = đủ mẫu; cột nhạt viền nét đứt = chưa đủ dữ liệu. */
export function KcChart({ rows }: { rows: KcChartRow[] }) {
  const lowKcs = new Set(rows.filter((row) => row.kind === "low").map((row) => row.kc))
  const height = Math.max(180, rows.length * ROW_HEIGHT + 50)
  return (
    <div style={{ height }} className="w-full" aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 56, bottom: 4, left: 4 }}
          accessibilityLayer={false}
        >
          <CartesianGrid horizontal={false} stroke={CHART_COLORS.grid} />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 12, fill: CHART_COLORS.axis }} />
          <YAxis
            type="category"
            dataKey="kc"
            width={112}
            interval={0}
            tick={makeTick(lowKcs)}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => `${percentFormat.format(Number(value))}%`}
            labelFormatter={(label) => `KC ${String(label)}`}
          />
          <Bar dataKey="sufficient" name="Đủ mẫu" stackId="rate" fill={CHART_COLORS.sufficient} isAnimationActive={false} radius={[0, 4, 4, 0]}>
            <LabelList dataKey="sufficient" position="right" formatter={(v) => (v == null ? "" : `${percentFormat.format(Number(v))}%`)} fontSize={12} fill={CHART_COLORS.axis} />
          </Bar>
          <Bar
            dataKey="insufficient"
            name="Chưa đủ dữ liệu"
            stackId="rate"
            fill={CHART_COLORS.insufficientFill}
            stroke={CHART_COLORS.insufficientStroke}
            strokeDasharray="4 3"
            isAnimationActive={false}
            radius={[0, 4, 4, 0]}
          >
            <LabelList dataKey="insufficient" position="right" formatter={(v) => (v == null ? "" : `${percentFormat.format(Number(v))}%`)} fontSize={12} fill={CHART_COLORS.axis} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
