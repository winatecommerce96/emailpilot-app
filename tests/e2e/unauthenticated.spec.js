// @ts-check
const { test, expect } = require('@playwright/test');

// Test suite for unauthenticated user flow
test.describe('EmailPilot SPA - Unauthenticated User', () => {
  
  test.beforeEach(async ({ page, context }) => {
    // Clear any auth tokens
    await context.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    // Mock API to return 401 for auth check
    await page.route('**/api/auth/me', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Not authenticated'
        })
      });
    });
    
    // Monitor console for errors
    page.on('console', msg => {
      if (msg.type() === 'error' && 
          !msg.text().includes('401') &&
          !msg.text().includes('Not authenticated') &&
          !msg.text().includes('Authentication required')) {
        console.error(`Unexpected console error: ${msg.text()}`);
      }
    });
  });
  
  test('redirects to login without console spam', async ({ page }) => {
    const consoleErrors = [];
    const authRelatedLogs = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (msg.type() === 'error') {
        if (text.includes('401') || text.includes('auth') || text.includes('Auth')) {
          authRelatedLogs.push(text);
        } else {
          consoleErrors.push(text);
        }
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    
    // Login form should be visible
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    
    // No unexpected console errors
    expect(consoleErrors).toHaveLength(0);
    
    // Auth logs should be minimal (just one "Authentication required" is acceptable)
    expect(authRelatedLogs.length).toBeLessThanOrEqual(1);
  });
  
  test('protected routes redirect to login gracefully', async ({ page }) => {
    const protectedRoutes = ['/calendar', '/clients', '/reports', '/settings'];
    
    for (const route of protectedRoutes) {
      const consoleErrors = [];
      const networkErrors = [];
      
      page.on('console', msg => {
        if (msg.type() === 'error' && 
            !msg.text().includes('Authentication required') &&
            !msg.text().includes('401')) {
          consoleErrors.push(msg.text());
        }
      });
      
      page.on('response', response => {
        // We expect ONE 401 for the auth check, not multiple
        if (response.status() === 401 && response.url().includes('/api/auth/me')) {
          // This is expected
        } else if (response.status() >= 400 && response.status() < 500) {
          networkErrors.push(`${response.status()} on ${response.url()}`);
        }
      });
      
      await page.goto(route);
      await page.waitForLoadState('networkidle');
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
      
      // No unexpected console errors
      expect(consoleErrors).toHaveLength(0);
      
      // No unexpected network errors
      expect(networkErrors).toHaveLength(0);
    }
  });
  
  test('login page loads without errors', async ({ page }) => {
    const consoleErrors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Login form elements should be present
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    
    // No console errors
    expect(consoleErrors).toHaveLength(0);
  });
  
  test('login form handles invalid credentials gracefully', async ({ page }) => {
    // Mock login endpoint to return error
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Invalid credentials'
        })
      });
    });
    
    const consoleErrors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error' && 
          !msg.text().includes('401') &&
          !msg.text().includes('Invalid credentials')) {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Fill in login form
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Error message should be displayed
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
    
    // No unexpected console errors
    expect(consoleErrors).toHaveLength(0);
  });
  
  test('successful login redirects to dashboard', async ({ page }) => {
    // Mock successful login
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'new-auth-token',
          user: {
            id: 'user-123',
            email: 'test@example.com',
            name: 'Test User'
          }
        })
      });
    });
    
    // After login, auth/me should succeed
    let authMeCalled = false;
    await page.route('**/api/auth/me', async route => {
      if (authMeCalled) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'user-123',
            email: 'test@example.com',
            name: 'Test User'
          })
        });
      } else {
        authMeCalled = true;
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Not authenticated' })
        });
      }
    });
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Fill in login form
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'correctpassword');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await page.waitForURL(/\//);
    
    // Navigation should be visible (user is now authenticated)
    await expect(page.locator('nav')).toBeVisible();
  });
});