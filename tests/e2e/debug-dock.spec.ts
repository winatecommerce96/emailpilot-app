import { test, expect } from '@playwright/test';

test('Debug Dock visible and captures events', async ({ page }) => {
  await page.goto('http://localhost:8000/?debug=1');
  const toggle = page.locator('#ep-debug-toggle');
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.locator('#ep-debug-dock')).toHaveClass(/open/);
  // Trigger a failing fetch to exercise telemetry capture
  await page.evaluate(async () => {
    try { await fetch('/__nope__'); } catch {}
  });
  await expect(page.locator('#ep-debug-log')).toContainText('fetch');
});

