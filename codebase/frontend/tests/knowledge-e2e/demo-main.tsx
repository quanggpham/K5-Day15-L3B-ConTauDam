import { createRoot } from "react-dom/client"
import DemoPreview from "../../src/features/reports/DemoPreview"
import "../../src/style.css"
createRoot(document.getElementById("root")!).render(<DemoPreview runId="run-1" kcCode="K1" />)
