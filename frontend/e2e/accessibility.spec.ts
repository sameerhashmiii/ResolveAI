import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

async function expectNoSeriousViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze()
  expect(
    results.violations.filter(
      ({ impact }) => impact === 'serious' || impact === 'critical',
    ),
  ).toEqual([])
}

test.describe('critical page accessibility', () => {
  test.skip(
    ({ isMobile }) => isMobile,
    'Axe runs once; responsive behavior has separate coverage.',
  )

  test('landing and login', async ({ page }) => {
    await page.goto('/')
    await expectNoSeriousViolations(page)
    await page.goto('/login')
    await expectNoSeriousViolations(page)
  })

  test('workspace and create request', async ({ page }) => {
    await page.route('**/api/v1/auth/demo', async (route) => {
      await route.fulfill({
        json: {
          user: {
            id: 'axe-demo-user',
            email: 'axe@example.test',
            display_name: 'Axe Analyst',
            role: 'support_analyst',
            is_demo: true,
          },
          csrf_token: 'axe-demo-token',
        },
      })
    })
    await page.route('**/api/v1/dashboard/overview', async (route) => {
      await route.fulfill({
        json: {
          total_tickets: 0,
          open_tickets: 0,
          resolved_tickets: 0,
          escalated_tickets: 0,
          recent_tickets: [],
        },
      })
    })
    await page.goto('/login')
    await page.getByRole('button', { name: 'Try Demo' }).click()
    await expect(
      page.getByRole('heading', { name: 'Service desk, at a glance.' }),
    ).toBeVisible()
    await expectNoSeriousViolations(page)
    await page.getByRole('link', { name: /New request/ }).click()
    await expect(
      page.getByRole('heading', { name: 'Create a service request.' }),
    ).toBeVisible()
    await expectNoSeriousViolations(page)
  })
})
