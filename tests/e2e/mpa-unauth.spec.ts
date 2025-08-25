import { test, expect } from '@playwright/test';

test('Unauthenticated access does not spam 401 on assets', async ({ page }) => {
  const assetResponses: {url: string, status: number}[] = [];
  page.on('response', (res) => {
    const url = res.url();
    const isAsset = url.includes('/static/') || url.endsWith('.js') || url.endsWith('.css');
    if (isAsset) assetResponses.push({url, status: res.status()});
  });
  await page.goto('http://localhost:8000/');
  // Page loads
  await expect(page.locator('#app-main')).toBeVisible();
  // No asset 401s
  const assets401 = assetResponses.filter(r => r.status === 401);
  expect(assets401, `Asset 401s: ${assets401.map(a=>a.url).join('\n')}`).toHaveLength(0);
});
