import { expect, test } from '@playwright/test'

test('mobile menu works without horizontal document overflow', async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, 'The mobile smoke test runs in the mobile project.')

  await page.route('**/api/v1/auth/demo', async (route) => {
    await route.fulfill({
      json: {
        user: {
          id: 'menu-demo-user',
          email: 'menu@example.test',
          display_name: 'Menu Analyst',
          role: 'support_analyst',
          is_demo: true,
        },
        csrf_token: 'menu-demo-token',
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
  const menu = page.getByRole('button', { name: 'Menu', exact: true })
  await expect(menu).toBeVisible()
  await menu.click()
  await expect(menu).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByRole('link', { name: /Overview/ })).toBeFocused()
  await expect(
    page.getByRole('navigation', { name: 'Primary navigation' }),
  ).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(menu).toHaveAttribute('aria-expanded', 'false')
  await expect(menu).toBeFocused()

  const overflow = await page.evaluate(() => {
    return (
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth
    )
  })
  expect(overflow).toBe(false)
})

test('landing and scenario intake remain usable at mobile width', async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, 'The responsive journey runs in the mobile project.')
  await page.route('**/api/v1/auth/demo', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        user: {
          id: 'responsive-demo-user',
          email: 'mobile@example.test',
          display_name: 'Mobile Analyst',
          role: 'support_analyst',
          is_demo: true,
        },
        csrf_token: 'responsive-demo-token',
      }),
    })
  })
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Evidence first. Humans decide.' }),
  ).toBeVisible()
  await page.getByRole('link', { name: 'Start 90-second guided demo' }).click()
  await page.getByRole('button', { name: 'Continue guided demo' }).click()
  await expect(page.getByLabel(/Title/)).toHaveValue(
    'VPN works, PayrollPro does not',
  )
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  )
  expect(overflow).toBe(false)
})
