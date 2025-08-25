import { test, expect, Page, ConsoleMessage } from '@playwright/test';

test.describe('EmailPilot SPA - Authenticated Debug Mode', () => {
  let consoleErrors: string[] = [];
  let networkErrors: { url: string; status: number }[] = [];
  let cdnRequests: string[] = [];
  
  test.beforeEach(async ({ page, context }) => {
    // Clear tracking arrays
    consoleErrors = [];
    networkErrors = [];
    cdnRequests = [];
    
    // Enable debug mode and set auth token
    await context.addInitScript(() => {
      localStorage.setItem('debug', '1');
      localStorage.setItem('emailpilot-token', 'test-auth-token-123');
    });
    
    // Mock auth endpoint
    await page.route('**/api/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-1',
          email: 'test@example.com',
          name: 'Test User'
        })
      });
    });
    
    // Mock clients endpoint
    await page.route('**/api/admin/clients', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          clients: [
            { id: '1', name: 'Client A', status: 'active', created_at: new Date().toISOString() },
            { id: '2', name: 'Client B', status: 'active', created_at: new Date().toISOString() }
          ]
        })
      });
    });
    
    // Track console errors and warnings
    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        const text = msg.text();
        // Ignore expected debug messages
        if (!text.includes('Debug Mode Enabled')) {
          consoleErrors.push(`${msg.type()}: ${text}`);
        }
      }
    });
    
    // Track network errors and CDN requests
    page.on('response', response => {
      const url = response.url();
      const status = response.status();
      
      // Check for CDN requests
      if (url.includes('unpkg.com') || 
          url.includes('jsdelivr.com') || 
          url.includes('cdnjs.cloudflare.com')) {
        cdnRequests.push(url);
      }
      
      // Track errors (excluding expected 401 for initial auth check)
      if (status >= 400 && !url.includes('/api/auth/me')) {
        networkErrors.push({ url, status });
      }
    });
    
    // Mock telemetry endpoint to capture debug events
    await page.route('**/api/dev/telemetry', async route => {
      const data = route.request().postDataJSON();
      console.log('Debug telemetry:', data);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'received' })
      });
    });
  });
  
  test('loads dashboard without errors', async ({ page }) => {
    await page.goto('/?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Wait for app to render
    await page.waitForSelector('nav', { timeout: 10000 });
    
    // Verify debug overlay is present
    await expect(page.locator('text=🐛')).toBeVisible();
    
    // Check no console errors
    expect(consoleErrors).toHaveLength(0);
    
    // Check no network errors
    expect(networkErrors).toHaveLength(0);
    
    // Check no CDN requests
    expect(cdnRequests).toHaveLength(0);
  });
  
  test('navigates to /clients without CORS errors', async ({ page }) => {
    await page.goto('/clients?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Wait for clients page to render
    await page.waitForSelector('h1:has-text("Clients")', { timeout: 10000 });
    
    // Verify no "BrowserRouter undefined" errors
    const routerErrors = consoleErrors.filter(e => 
      e.includes('BrowserRouter') || 
      e.includes('ReactRouterDOM') ||
      e.includes('window.ReactRouterDOM')
    );
    expect(routerErrors).toHaveLength(0);
    
    // Verify no CORS errors
    const corsErrors = consoleErrors.filter(e => 
      e.includes('CORS') || 
      e.includes('blocked by CORS policy')
    );
    expect(corsErrors).toHaveLength(0);
    
    // Check no CDN requests
    expect(cdnRequests).toHaveLength(0);
    
    // Check no network errors
    expect(networkErrors).toHaveLength(0);
  });
  
  test('CalendarChat handles missing module gracefully', async ({ page }) => {
    await page.goto('/calendar?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Wait for calendar page
    await page.waitForSelector('h2:has-text("Campaign Calendar")', { timeout: 10000 });
    
    // Check no "CalendarChat is not defined" errors
    const calendarErrors = consoleErrors.filter(e => 
      e.includes('CalendarChat is not defined') ||
      e.includes('CalendarChat')
    );
    
    // Should either load successfully or show warning, not error
    const hasError = calendarErrors.some(e => e.startsWith('error:'));
    expect(hasError).toBe(false);
  });
  
  test('all routes work via navigation', async ({ page }) => {
    await page.goto('/?debug=1');
    await page.waitForLoadState('networkidle');
    
    const routes = [
      { path: '/calendar', selector: 'h2:has-text("Campaign Calendar")' },
      { path: '/clients', selector: 'h1:has-text("Clients")' },
      { path: '/reports', selector: 'h1:has-text("Reports")' },
      { path: '/settings', selector: 'h1:has-text("Settings")' }
    ];
    
    for (const route of routes) {
      // Navigate via link click
      await page.click(`nav a[href="${route.path}"]`);
      await page.waitForLoadState('networkidle');
      
      // Verify page loaded
      await expect(page.locator(route.selector)).toBeVisible();
      
      // Verify URL changed (client-side routing)
      expect(page.url()).toContain(route.path);
    }
    
    // Final check: no errors accumulated
    expect(consoleErrors).toHaveLength(0);
    expect(networkErrors).toHaveLength(0);
    expect(cdnRequests).toHaveLength(0);
  });
  
  test('debug overlay captures and displays events', async ({ page }) => {
    await page.goto('/?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Open debug overlay
    await page.click('button:has-text("🐛")');
    
    // Verify overlay is open
    await expect(page.locator('text=all')).toBeVisible();
    await expect(page.locator('text=errors')).toBeVisible();
    await expect(page.locator('text=network')).toBeVisible();
    await expect(page.locator('text=warnings')).toBeVisible();
    
    // Generate a test error
    await page.evaluate(() => {
      console.error('Test error for debug overlay');
    });
    
    // Check error appears in overlay
    await page.click('button:has-text("errors")');
    await expect(page.locator('text=Test error for debug overlay')).toBeVisible();
  });
  
  test('telemetry posts events to backend', async ({ page }) => {
    const telemetryEvents: any[] = [];
    
    await page.route('**/api/dev/telemetry', async route => {
      const data = route.request().postDataJSON();
      telemetryEvents.push(data);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'received' })
      });
    });
    
    await page.goto('/?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Generate an error
    await page.evaluate(() => {
      console.error('Telemetry test error');
    });
    
    // Wait for telemetry
    await page.waitForTimeout(500);
    
    // Verify telemetry was sent
    const errorEvent = telemetryEvents.find(e => 
      e.type === 'console.error' && 
      e.message.includes('Telemetry test error')
    );
    expect(errorEvent).toBeDefined();
    expect(errorEvent.route).toBe('/');
    expect(errorEvent.ts).toBeGreaterThan(0);
  });
});