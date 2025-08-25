import { test, expect } from '@playwright/test';

const pages = ['/', '/clients', '/calendar', '/reports', '/settings', '/admin', '/admin/services', '/admin/clients', '/admin/logs'];

for (const path of pages) {
  test(`MPA route loads cleanly: ${path}`, async ({ page }) => {
    const consoleMessages: string[] = [];
    page.on('console', (msg) => {
      const type = msg.type();
      if (type === 'error' || type === 'warning') {
        consoleMessages.push(`${type}: ${msg.text()}`);
      }
    });

    const badAssets: string[] = [];
    page.on('response', (res) => {
      const url = res.url();
      const isAsset = url.includes('/static/') || url.endsWith('.js') || url.endsWith('.css');
      if (isAsset && res.status() >= 400) {
        badAssets.push(`${res.status()} ${url}`);
      }
    });

    await page.goto(`http://localhost:8000${path}`);
    // Wait for main content to be visible
    await expect(page.locator('#app-main')).toBeVisible();
    expect(badAssets, `Asset failures: ${badAssets.join('\n')}`).toHaveLength(0);
    expect(consoleMessages, `Console errors/warns: ${consoleMessages.join('\n')}`).toHaveLength(0);
  });
}
