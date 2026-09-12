import { expect, test } from '@playwright/test'

test('completes the human-controlled VPN and PayrollPro flow', async ({
  page,
}) => {
  const unique = `${Date.now().toString()}-${Math.random()
    .toString(36)
    .slice(2, 8)}`
  const title = `VPN access to PayrollPro unavailable ${unique}`

  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Evidence first. Humans decide.' }),
  ).toBeVisible()
  await page.getByRole('link', { name: 'Start 90-second guided demo' }).click()
  await page.getByRole('button', { name: 'Continue guided demo' }).click()
  await expect(
    page.getByRole('heading', { name: 'Create a service request.' }),
  ).toBeVisible()

  await expect(page.getByLabel('Location')).toHaveValue('Dallas')
  await expect(page.getByLabel('Application')).toHaveValue('PayrollPro')
  await page.getByLabel(/Title/).fill(title)
  await page.getByRole('button', { name: 'Create ticket' }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()

  await page.getByRole('button', { name: 'Analyze ticket' }).click()
  await expect(page.getByText('Deterministic demo analysis')).toBeVisible({
    timeout: 60_000,
  })
  await expect(page.getByText('Extracted entities')).toBeVisible()
  await expect(page.getByText('Dallas', { exact: true }).last()).toBeVisible()
  await expect(
    page.getByText('PayrollPro', { exact: true }).last(),
  ).toBeVisible()
  await expect(page.getByText(/evidence confidence/).first()).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Start investigation' }),
  ).toBeVisible({ timeout: 60_000 })
  await page.getByRole('button', { name: 'Start investigation' }).click()
  await expect(
    page.getByRole('heading', { name: 'Knowledge Sources' }),
  ).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText(/VPN/i).first()).toBeVisible()
  await expect(page.getByText(/healthy/i).first()).toBeVisible()
  await expect(page.getByText(/degraded/i).first()).toBeVisible()
  await expect(page.getByText(/DNS/i).first()).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Generate assessment' }),
  ).toBeVisible({ timeout: 60_000 })
  await page.getByRole('button', { name: 'Generate assessment' }).click()
  await expect(page.getByText(/AI inference - not confirmed/i)).toBeVisible({
    timeout: 60_000,
  })
  await expect(
    page.getByText(
      /Evidence confidence in this recommendation, not measured accuracy/i,
    ),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Show Me Why' }).click()
  await expect(
    page.getByRole('heading', { name: 'Why this assessment?' }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).click()

  const resolution = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'Human Decision & Resolution' }),
  })
  await expect(
    resolution.getByRole('button', { name: 'Approve', exact: true }),
  ).toBeVisible({ timeout: 60_000 })
  await resolution.getByRole('button', { name: 'Approve', exact: true }).click()
  await resolution
    .getByLabel('Decision reason')
    .fill('Evidence and bounded guidance reviewed by the demo analyst')
  await resolution.getByRole('button', { name: 'Confirm approve' }).click()
  await expect(
    resolution.getByText('Recommendation decision recorded.'),
  ).toBeVisible()

  await resolution
    .getByRole('button', { name: 'Generate requester response' })
    .click()
  const response = resolution.getByLabel('Professional response draft')
  await expect(response).toBeEditable()
  await response.fill(
    'Hello Jordan, based on evidence, the VPN connection appears healthy while the probable issue is the PayrollPro DNS path. Please follow the approved guidance; no remediation action has been completed or sent by this response.',
  )
  await resolution.getByRole('button', { name: 'Save draft' }).click()
  await expect(resolution.getByText('Response draft saved.')).toBeVisible()
  await resolution.getByRole('button', { name: 'Approve response' }).click()
  await expect(
    resolution.getByText('Response approved. It has not been sent.'),
  ).toBeVisible()

  const summary =
    'Human-reviewed guidance and approved response recorded; no automated remediation was performed.'
  await resolution.getByLabel('Resolution summary').fill(summary)
  await resolution.getByRole('button', { name: 'Resolve ticket' }).click()
  await expect(
    resolution.getByRole('heading', { name: 'Ticket resolved' }),
  ).toBeVisible()
  await expect(resolution.getByText(summary)).toBeVisible()
  await expect(resolution.getByText('Terminal state')).toBeVisible()
})
