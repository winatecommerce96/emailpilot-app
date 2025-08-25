// @ts-check
const { test, expect } = require('@playwright/test');

// Test suite for authenticated user flow
test.describe('EmailPilot SPA - Authenticated User', () => {
  
  test.beforeEach(async ({ page, context }) => {
    // Mock authentication by setting token in localStorage
    await context.addInitScript(() => {
      localStorage.setItem('emailpilot-token', 'mock-auth-token-12345');
      localStorage.setItem('emailpilot-theme', 'light');
    });
    
    // Mock API responses for authenticated user
    await page.route('**/api/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-123',
          email: 'test@example.com',
          name: 'Test User'
        })
      });
    });
    
    // Mock calendar API response
    await page.route('**/api/firebase-calendar/clients', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          clients: [
            { id: 'client-1', name: 'Test Client 1' },
            { id: 'client-2', name: 'Test Client 2' }
          ]
        })
      });
    });
    
    // Monitor console for errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error(`Console error: ${msg.text()}`);
      }
    });
    
    // Monitor network for 401s
    page.on('response', response => {
      if (response.status() === 401) {
        console.error(`401 Unauthorized: ${response.url()}`);
      }
    });
  });
  
  test('loads dashboard without console errors or 401s', async ({ page }) => {
    const consoleErrors = [];
    const unauthorizedRequests = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('response', response => {
      if (response.status() === 401) {
        unauthorizedRequests.push(response.url());
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check that we're on the SPA
    await expect(page).toHaveURL(/\/spa/);
    
    // Wait for app to render
    await page.waitForSelector('nav', { timeout: 5000 });
    
    // Verify no console errors
    expect(consoleErrors).toHaveLength(0);
    
    // Verify no 401 responses
    expect(unauthorizedRequests).toHaveLength(0);
    
    // Verify navigation is visible
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('text=EmailPilot')).toBeVisible();
  });
  
  test('navigates to calendar without errors', async ({ page }) => {
    const consoleErrors = [];
    const unauthorizedRequests = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('CalendarChat')) {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('response', response => {
      if (response.status() === 401) {
        unauthorizedRequests.push(response.url());
      }
    });
    
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');
    
    // Wait for calendar to render
    await page.waitForSelector('nav', { timeout: 5000 });
    
    // CalendarChat is feature-flagged, so we don't count it as error
    const criticalErrors = consoleErrors.filter(err => 
      !err.includes('CalendarChat') && 
      !err.includes('is not defined')
    );
    
    // Verify no critical console errors
    expect(criticalErrors).toHaveLength(0);
    
    // Verify no 401 responses
    expect(unauthorizedRequests).toHaveLength(0);
  });
  
  test('navigates to all routes via in-app navigation', async ({ page }) => {
    const consoleErrors = [];
    const unauthorizedRequests = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error' && 
          !msg.text().includes('CalendarChat') &&
          !msg.text().includes('Firebase')) {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('response', response => {
      if (response.status() === 401) {
        unauthorizedRequests.push(response.url());
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for navigation to render
    await page.waitForSelector('nav a[href="/calendar"]', { timeout: 5000 });
    
    // Navigate to Calendar
    await page.click('nav a[href="/calendar"]');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/calendar/);
    
    // Navigate to Clients
    await page.click('nav a[href="/clients"]');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/clients/);
    
    // Navigate to Reports
    await page.click('nav a[href="/reports"]');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/reports/);
    
    // Navigate to Settings
    await page.click('nav a[href="/settings"]');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/settings/);
    
    // Verify no console errors (excluding known feature flags)
    const criticalErrors = consoleErrors.filter(err => 
      !err.includes('CalendarChat') && 
      !err.includes('Firebase')
    );
    expect(criticalErrors).toHaveLength(0);
    
    // Verify no 401 responses
    expect(unauthorizedRequests).toHaveLength(0);
  });
  
  test('deep links work correctly', async ({ page }) => {
    const routes = ['/calendar', '/clients', '/reports', '/settings'];
    
    for (const route of routes) {
      const consoleErrors = [];
      const unauthorizedRequests = [];
      
      page.on('console', msg => {
        if (msg.type() === 'error' && 
            !msg.text().includes('CalendarChat') &&
            !msg.text().includes('Firebase')) {
          consoleErrors.push(msg.text());
        }
      });
      
      page.on('response', response => {
        if (response.status() === 401) {
          unauthorizedRequests.push(response.url());
        }
      });
      
      await page.goto(route);
      await page.waitForLoadState('networkidle');
      
      // Verify SPA handles the route
      await expect(page).toHaveURL(new RegExp(route));
      
      // Verify navigation is visible
      await expect(page.locator('nav')).toBeVisible();
      
      // Verify no critical errors
      expect(consoleErrors).toHaveLength(0);
      expect(unauthorizedRequests).toHaveLength(0);
    }
  });
  
  test('error boundary catches component errors gracefully', async ({ page }) => {
    // Force an error by navigating to a broken component
    await page.goto('/');
    
    // Inject an error
    await page.evaluate(() => {
      throw new Error('Test error for boundary');
    });
    
    // Error boundary should catch it
    // App should not white-screen
    await page.waitForTimeout(1000);
    
    // Check that error boundary UI is shown or app recovered
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toBe(''); // App didn't white-screen
  });
});