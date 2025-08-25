import { test, expect } from '@playwright/test';

test.describe('EmailPilot SPA - Unauthenticated Debug Mode', () => {
  let authAttempts = 0;
  
  test.beforeEach(async ({ page, context }) => {
    authAttempts = 0;
    
    // Enable debug mode, no auth token
    await context.addInitScript(() => {
      localStorage.setItem('debug', '1');
      localStorage.removeItem('emailpilot-token');
    });
    
    // Mock auth endpoint to return 401
    await page.route('**/api/auth/me', async route => {
      authAttempts++;
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Not authenticated'
        })
      });
    });
    
    // Mock telemetry
    await page.route('**/api/dev/telemetry', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'received' })
      });
    });
  });
  
  test('redirects to login without 401 spam', async ({ page }) => {
    await page.goto('/?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    
    // Should show login form
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    
    // Should only make ONE auth check, not spam
    expect(authAttempts).toBeLessThanOrEqual(1);
  });
  
  test('protected routes redirect gracefully', async ({ page }) => {
    const protectedRoutes = ['/calendar', '/clients', '/reports', '/settings'];
    
    for (const route of protectedRoutes) {
      authAttempts = 0;
      
      await page.goto(`${route}?debug=1`);
      await page.waitForLoadState('networkidle');
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
      
      // Should not spam auth endpoint
      expect(authAttempts).toBeLessThanOrEqual(1);
    }
  });
  
  test('login page loads without errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('Debug Mode')) {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('/login?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Login form should be visible
    await expect(page.locator('h1:has-text("EmailPilot")')).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    
    // No console errors
    expect(consoleErrors).toHaveLength(0);
  });
  
  test('failed login shows error without console spam', async ({ page }) => {
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Invalid credentials'
        })
      });
    });
    
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && 
          !msg.text().includes('Debug Mode') &&
          !msg.text().includes('Invalid credentials')) {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('/login?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Try to login
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    // Error message should appear
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
    
    // No unexpected console errors
    expect(consoleErrors).toHaveLength(0);
  });
  
  test('successful login redirects to dashboard', async ({ page }) => {
    let loginCalled = false;
    
    await page.route('**/api/auth/login', async route => {
      loginCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'new-token-123',
          user: {
            id: 'user-1',
            email: 'test@example.com',
            name: 'Test User'
          }
        })
      });
    });
    
    // After login, auth/me should work
    await page.route('**/api/auth/me', async route => {
      if (loginCalled) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'user-1',
            email: 'test@example.com',
            name: 'Test User'
          })
        });
      } else {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Not authenticated' })
        });
      }
    });
    
    await page.goto('/login?debug=1');
    await page.waitForLoadState('networkidle');
    
    // Login
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'correctpassword');
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await page.waitForURL(/^[^/]*\/$/, { timeout: 5000 });
    
    // Navigation should be visible
    await expect(page.locator('nav')).toBeVisible();
  });
});