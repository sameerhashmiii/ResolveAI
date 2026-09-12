import { expect, test } from '@playwright/test'

test('mobile menu works without horizontal document overflow', async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, 'The mobile smoke test runs in the mobile project.')

  await page.goto('/login')
  await page.getByRole('button', { name: 'Try Demo' }).click()
  const menu = page.getByRole('button', { name: 'Menu', exact: true })
  await expect(menu).toBeVisible()
  await menu.click()
  await expect(menu).toHaveAttribute('aria-expanded', 'true')
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
