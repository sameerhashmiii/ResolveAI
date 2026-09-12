import { expect, test } from '@playwright/test'

test('completes the human-controlled VPN and PayrollPro flow', async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, 'The critical flow runs in the desktop project.')
  const unique = `${Date.now().toString()}-${Math.random()
    .toString(36)
    .slice(2, 8)}`
  const title = `VPN access to PayrollPro unavailable ${unique}`

  await page.goto('/login')
  await page.getByRole('button', { name: 'Try Demo' }).click()
  await expect(
    page.getByRole('heading', { name: 'Service desk, at a glance.' }),
  ).toBeVisible()

  await page.getByRole('link', { name: /New request/ }).click()
  await page.getByLabel(/Title/).fill(title)
  await page
    .getByLabel(/Description/)
    .fill(
      'The VPN connects from Dallas, but PayrollPro remains unavailable and its internal service name does not resolve. Other internet services work.',
    )
  await page.getByLabel(/Requester name/).fill('Jordan Lee')
  await page.getByLabel('Department').fill('Payroll')
  await page.getByLabel('Location').fill('Dallas')
  await page.getByLabel('Device').fill('SYN-DEV-00041')
  await page.getByLabel('Application').fill('PayrollPro')
  await page.getByRole('button', { name: 'Create ticket' }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()

  await page.getByRole('button', { name: 'Analyze ticket' }).click()
  await expect(
    page.getByRole('button', { name: 'Start investigation' }),
  ).toBeVisible({ timeout: 60_000 })
  await page.getByRole('button', { name: 'Start investigation' }).click()
  await expect(
    page.getByRole('button', { name: 'Generate assessment' }),
  ).toBeVisible({ timeout: 60_000 })
  await page.getByRole('button', { name: 'Generate assessment' }).click()

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
    .getByRole('button', { name: 'Generate customer response' })
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
})
