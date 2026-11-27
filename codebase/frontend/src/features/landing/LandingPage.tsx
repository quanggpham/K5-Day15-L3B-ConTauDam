import { useEffect } from "react"
import Faq from "./Faq"
import Flow from "./Flow"
import Footer from "./Footer"
import Hero from "./Hero"
import LandingNav from "./LandingNav"
import Principles from "./Principles"
import Problem from "./Problem"
import Showcase from "./Showcase"

/**
 * Trang giới thiệu công khai (route `/`).
 */
export default function LandingPage() {
  useEffect(() => {
    const previousTitle = document.title
    document.title = "LearningPulse"
    // Mở thẳng /#hoi-dap: cuộn tới mục sau khi trang đã render.
    const id = decodeURIComponent(window.location.hash.slice(1))
    if (id) document.getElementById(id)?.scrollIntoView()
    return () => {
      document.title = previousTitle
    }
  }, [])

  return (
    <div className="min-h-dvh bg-gradient-to-b from-violet-50 via-white to-violet-50 text-slate-900 antialiased">
      <a
        href="#landing-main"
        className="sr-only rounded-md bg-white px-4 py-2 font-medium text-violet-900 focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:ring-2 focus:ring-violet-700"
      >
        Bỏ qua điều hướng
      </a>
      <LandingNav />
      <main id="landing-main" tabIndex={-1} className="outline-hidden">
        <Hero />
        <Problem />
        <Flow />
        <Showcase />
        <Principles />
        <Faq />
      </main>
      <Footer />
    </div>
  )
}
