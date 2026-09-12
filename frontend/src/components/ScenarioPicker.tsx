import { Link } from 'react-router-dom'

import { demoScenarios } from '../demo/scenarios'

export function ScenarioPicker({
  authenticated = false,
}: {
  authenticated?: boolean
}) {
  return (
    <div className="scenario-grid">
      {demoScenarios.map((scenario, index) => (
        <article className="scenario-card" key={scenario.slug}>
          <div className="scenario-card__index">
            <span>0{index + 1}</span>
            {scenario.recommended && <strong>Recommended</strong>}
          </div>
          <h3>{scenario.title}</h3>
          <p>{scenario.description}</p>
          <dl>
            <div>
              <dt>Context</dt>
              <dd>
                {scenario.location} / {scenario.application}
              </dd>
            </div>
            <div>
              <dt>Expected evidence and trust outcome</dt>
              <dd>{scenario.expectedOutcome}</dd>
            </div>
          </dl>
          <Link
            className="button button--outline"
            to={
              authenticated
                ? `/tickets/new?scenario=${scenario.slug}`
                : `/login?scenario=${scenario.slug}`
            }
          >
            Use scenario
          </Link>
        </article>
      ))}
    </div>
  )
}
