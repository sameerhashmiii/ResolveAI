import { expect, test } from '@playwright/test'

test('authenticated users see bounded analytics labels', async ({
  page,
  isMobile,
}) => {
  test.skip(isMobile, 'Analytics labels run once in the desktop project.')
  await page.route('**/api/v1/auth/demo', async (route) => {
    await route.fulfill({
      json: {
        user: {
          id: 'analytics-demo-user',
          email: 'analytics@example.test',
          display_name: 'Analytics Analyst',
          role: 'support_analyst',
          is_demo: true,
        },
        csrf_token: 'analytics-demo-token',
      },
    })
  })
  await page.route('**/api/v1/analytics/overview', async (route) => {
    await route.fulfill({
      json: {
        synthetic: true,
        source: 'stored demo runs',
        methodology: 'aggregate snapshot',
        measured_at: '2026-09-11T00:00:00Z',
        dataset_version: 'tickets-v11',
        tickets: {
          total_tickets: 5,
          open_tickets: 1,
          resolved_tickets: 4,
          escalated_tickets: 0,
          resolution_rate: 0.8,
          sample_count: 5,
        },
        workflows: [
          {
            name: 'investigation',
            workflow_version: 'v11',
            completed: 4,
            failed: 1,
            total: 5,
            completion_rate: 0.8,
            median_duration_ms: 20,
          },
        ],
      },
    })
  })
  await page.route('**/api/v1/analytics/evaluation-summary', async (route) => {
    await route.fulfill({
      json: {
        synthetic: true,
        source: 'curated synthetic set',
        methodology: 'fixed runner',
        latest_run: null,
      },
    })
  })
  await page.goto('/login')
  await page.getByRole('button', { name: 'Try Demo' }).click()
  await page.getByRole('link', { name: /Evaluation/ }).click()
  await expect(
    page.getByRole('heading', { name: 'Evaluation, with receipts.' }),
  ).toBeVisible()
  await expect(
    page.getByText('Workflow completion is not accuracy.'),
  ).toBeVisible()
  await expect(page.getByText(/Synthetic/).first()).toBeVisible()
  await expect(page.getByText(/Denominator:/).first()).toBeVisible()
})
