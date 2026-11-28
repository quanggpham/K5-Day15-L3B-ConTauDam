import { defineConfig } from "@playwright/test"

export default defineConfig({
  testDir: "./tests/knowledge-e2e",
  use: { baseURL: "http://127.0.0.1:5181", screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: { command: "pnpm exec vite --host 127.0.0.1 --port 5181 --strictPort", url: "http://127.0.0.1:5181/tests/knowledge-e2e/", reuseExistingServer: false },
})
