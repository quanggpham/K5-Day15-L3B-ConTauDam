import { createRoot } from "react-dom/client"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import DemoPreview from "../../src/features/reports/DemoPreview"
import "../../src/style.css"
createRoot(document.getElementById("root")!).render(<MemoryRouter><Routes>
  <Route path="/" element={<DemoPreview runId="run-1" kcCode="K1" />} />
  <Route path="/reports/run-1/review" element={<h1>Duyệt đề xuất</h1>} />
</Routes></MemoryRouter>)
