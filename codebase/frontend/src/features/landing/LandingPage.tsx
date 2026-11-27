import Flow from "./Flow"
import Hero from "./Hero"
import LandingNav from "./LandingNav"
import Principles from "./Principles"
import Problem from "./Problem"

/**
 * Trang giới thiệu công khai (route `/` sẽ được nối ở bước sau).
 * Step 3 sẽ thêm minh hoạ báo cáo, FAQ và footer.
 */
export default function LandingPage() {
  return (
    <div className="min-h-dvh bg-gradient-to-b from-violet-50 via-white to-violet-50 text-slate-900 antialiased">
      <a
        href="#landing-main"
        className="sr-only rounded-md bg-white px-4 py-2 font-medium text-violet-900 focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:ring-2 focus:ring-violet-700"
      >
        Bỏ qua điều hướng
      </a>
      <LandingNav />
      <main id="landing-main">
        <Hero />
        <Problem />
        <Flow />
        <Principles />
        {/* Step 3: minh hoạ báo cáo, FAQ */}
      </main>
      {/* Step 3: footer */}
    </div>
  )
}
