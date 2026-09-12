import { chromium, devices } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontendRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
)
const output = path.resolve(frontendRoot, '../docs/assets/screenshots')
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3000'

await mkdir(output, { recursive: true })

const browser = await chromium.launch()
const desktop = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
})
const page = await desktop.newPage()

await page.goto(baseURL)
await page.screenshot({
  path: path.join(output, 'landing.png'),
  fullPage: true,
})
await page.getByRole('link', { name: 'Start 90-second guided demo' }).click()
await page.getByRole('button', { name: 'Continue guided demo' }).click()
await page.getByRole('heading', { name: 'Create a service request.' }).waitFor()
await page.screenshot({
  path: path.join(output, 'ticket-intake.png'),
  fullPage: true,
})
await page.getByRole('link', { name: /Overview/ }).click()
await page
  .getByRole('heading', { name: 'Service desk, at a glance.' })
  .waitFor()
await page.screenshot({
  path: path.join(output, 'dashboard.png'),
  fullPage: true,
})
await page.goBack()
await page.getByRole('heading', { name: 'Create a service request.' }).waitFor()
const unique = Date.now().toString()
await page
  .getByLabel(/Title/)
  .fill(`VPN access to PayrollPro unavailable ${unique}`)
await page.getByRole('button', { name: 'Create ticket' }).click()

await page.getByRole('button', { name: 'Analyze ticket' }).click()
await page.getByText('Deterministic demo analysis').waitFor({ timeout: 60_000 })
const triage = page.locator('section').filter({
  has: page.getByRole('heading', { name: 'AI Ticket Triage' }),
})
await triage.screenshot({ path: path.join(output, 'ticket-triage.png') })

await page.getByRole('button', { name: 'Start investigation' }).click()
await page
  .getByRole('button', { name: 'Generate assessment' })
  .waitFor({ timeout: 60_000 })
const investigation = page.locator('section').filter({
  has: page.getByRole('heading', { name: 'Evidence investigation' }),
})
await investigation.screenshot({ path: path.join(output, 'investigation.png') })

await page.getByRole('button', { name: 'Generate assessment' }).click()
await page
  .getByRole('button', { name: 'Show Me Why' })
  .waitFor({ timeout: 60_000 })
await page.getByRole('button', { name: 'Show Me Why' }).click()
const assessment = page.locator('section').filter({
  has: page.getByRole('heading', { name: 'Root Cause Assessment' }),
})
await assessment.screenshot({ path: path.join(output, 'assessment.png') })
await page.getByRole('button', { name: 'Close' }).click()

const resolution = page.locator('section').filter({
  has: page.getByRole('heading', { name: 'Human Decision & Resolution' }),
})
await resolution.getByRole('button', { name: 'Approve', exact: true }).click()
await resolution
  .getByLabel('Decision reason')
  .fill('Synthetic evidence reviewed by a person')
await resolution.getByRole('button', { name: 'Confirm approve' }).click()
await resolution
  .getByRole('button', { name: 'Generate requester response' })
  .click()
await resolution.getByRole('button', { name: 'Approve response' }).click()
await resolution.getByText('Response approved. It has not been sent.').waitFor()
await resolution.screenshot({ path: path.join(output, 'human-approval.png') })

await desktop.close()

const mobile = await browser.newContext({ ...devices['Pixel 5'] })
const mobilePage = await mobile.newPage()
await mobilePage.goto(`${baseURL}/login`)
await mobilePage.getByRole('button', { name: 'Try Demo' }).click()
await mobilePage.getByRole('button', { name: 'Menu', exact: true }).click()
await mobilePage.waitForTimeout(300)
await mobilePage.screenshot({
  path: path.join(output, 'mobile-navigation.png'),
})
await mobile.close()
await browser.close()

console.log(`Captured synthetic portfolio screenshots in ${output}`)
