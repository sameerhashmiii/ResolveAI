import { useEffect } from 'react'
import { Link } from 'react-router-dom'

import { Brand } from '../components/Brand'
import { ScenarioPicker } from '../components/ScenarioPicker'

export function LandingPage() {
  useEffect(() => {
    document.title = 'ResolveAI | Evidence first. Humans decide.'
  }, [])
  return (
    <div className="landing-page">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="landing-header">
        <Brand publicLink />
        <nav aria-label="Public navigation">
          <a href="#architecture">Architecture</a>
          <a href="#evaluation">Evaluation</a>
          <a href="#security">Security</a>
          <Link className="button button--outline" to="/login">
            Sign in
          </Link>
        </nav>
      </header>
      <main id="main-content">
        <section className="landing-hero" aria-labelledby="landing-title">
          <div>
            <p className="eyebrow">Evidence-led support copilot</p>
            <h1 id="landing-title">Evidence first. Humans decide.</h1>
            <p className="landing-deck">
              A local-first service desk demonstration that separates observed
              evidence from probable inference and leaves every consequential
              action to a person.
            </p>
            <div className="landing-actions">
              <Link
                className="button button--primary"
                to="/login?scenario=dallas-vpn-payrollpro-dns"
              >
                Start 90-second guided demo
              </Link>
              <Link className="button button--quiet" to="/login">
                Sign in
              </Link>
            </div>
          </div>
          <aside className="trust-dossier" aria-label="Demo trust model">
            <p className="section-label">Trust model / 01</p>
            <h2>Bounded by design.</h2>
            <ul>
              <li>
                <strong>Local</strong>
                <span>Runs with the checked-in synthetic corpus</span>
              </li>
              <li>
                <strong>No key</strong>
                <span>Guided demo needs no provider API key</span>
              </li>
              <li>
                <strong>Synthetic</strong>
                <span>People, systems, and records are fictional</span>
              </li>
              <li>
                <strong>No automated remediation</strong>
                <span>Approval is recorded, never silently executed</span>
              </li>
            </ul>
          </aside>
        </section>

        <section
          className="landing-section"
          id="evaluation"
          aria-labelledby="scenarios-title"
        >
          <div className="landing-section__heading">
            <p className="section-label">02 / Guided evidence dossiers</p>
            <h2 id="scenarios-title">Choose a service scenario.</h2>
            <p>
              Each template prefills synthetic intake only. It never changes
              roles or starts a workflow.
            </p>
          </div>
          <ScenarioPicker />
        </section>

        <section
          className="landing-method"
          id="architecture"
          aria-labelledby="architecture-title"
        >
          <div>
            <p className="section-label">03 / Architecture</p>
            <h2 id="architecture-title">
              A visible chain of support evidence.
            </h2>
          </div>
          <ol>
            <li>
              <strong>Classify</strong>
              <span>
                Structured entities and deterministic mode are disclosed.
              </span>
            </li>
            <li>
              <strong>Investigate</strong>
              <span>
                Knowledge and synthetic observations retain provenance.
              </span>
            </li>
            <li>
              <strong>Assess</strong>
              <span>
                Probable does not mean confirmed; evidence confidence is not
                accuracy.
              </span>
            </li>
            <li>
              <strong>Decide</strong>
              <span>People approve, revise, hand off, or stop.</span>
            </li>
          </ol>
        </section>

        <section
          className="landing-limits"
          id="security"
          aria-labelledby="limitations-title"
        >
          <div>
            <p className="section-label">04 / Security and limitations</p>
            <h2 id="limitations-title">What this demo does not prove.</h2>
          </div>
          <p>
            Synthetic evaluation is not production performance. Workflow
            completion is not accuracy. The product APIs do not expose held-out
            evaluation cases, send requester responses, change permissions, or
            remediate systems. Operational fit, integrations, and security
            controls require independent review.
          </p>
          <Link to="/login?scenario=dallas-vpn-payrollpro-dns">
            Start the guided dossier
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Brand publicLink />
        <span>Local evidence. Human authority.</span>
      </footer>
    </div>
  )
}
