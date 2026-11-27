import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react"
import { cn } from "@/lib/utils"

export interface TabDef {
  id: string
  label: string
  render: () => ReactNode
}

/**
 * ARIA tabs (kích hoạt tự động): mũi tên trái/phải đổi tab (vòng tròn), Home/End về đầu/cuối.
 * Roving tabindex: chỉ tab đang chọn nằm trong thứ tự Tab; panel focus được để đọc tiếp bằng bàn phím.
 * Tab đang chọn khác tab còn lại bằng gạch chân + chữ đậm, không chỉ bằng màu.
 */
export function Tabs({ tabs, label }: { tabs: TabDef[]; label: string }) {
  const baseId = useId()
  const [selected, setSelected] = useState(tabs[0]?.id ?? "")
  const buttons = useRef<Record<string, HTMLButtonElement | null>>({})
  const activeIndex = Math.max(0, tabs.findIndex((tab) => tab.id === selected))
  const active = tabs[activeIndex]

  function activate(index: number) {
    const next = tabs[(index + tabs.length) % tabs.length]
    setSelected(next.id)
    buttons.current[next.id]?.focus()
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    switch (event.key) {
      case "ArrowRight":
        activate(activeIndex + 1)
        break
      case "ArrowLeft":
        activate(activeIndex - 1)
        break
      case "Home":
        activate(0)
        break
      case "End":
        activate(tabs.length - 1)
        break
      default:
        return
    }
    event.preventDefault()
  }

  if (!active) return null
  return (
    <div>
      <div
        role="tablist"
        aria-label={label}
        aria-orientation="horizontal"
        onKeyDown={onKeyDown}
        className="flex gap-1 overflow-x-auto border-b border-violet-200"
      >
        {tabs.map((tab) => {
          const isActive = tab.id === active.id
          return (
            <button
              key={tab.id}
              ref={(node) => {
                buttons.current[tab.id] = node
              }}
              type="button"
              role="tab"
              id={`${baseId}-tab-${tab.id}`}
              aria-selected={isActive}
              aria-controls={`${baseId}-panel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => setSelected(tab.id)}
              className={cn(
                "-mb-px h-11 shrink-0 whitespace-nowrap border-b-2 px-4 text-sm outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-700",
                isActive
                  ? "border-violet-700 font-bold text-violet-950"
                  : "border-transparent font-medium text-slate-700 hover:bg-violet-50 hover:text-violet-950",
              )}
            >
              {tab.label}
            </button>
          )
        })}
      </div>
      <div
        role="tabpanel"
        id={`${baseId}-panel-${active.id}`}
        aria-labelledby={`${baseId}-tab-${active.id}`}
        tabIndex={0}
        className="mt-5 outline-none focus-visible:ring-2 focus-visible:ring-violet-700"
      >
        {active.render()}
      </div>
    </div>
  )
}
