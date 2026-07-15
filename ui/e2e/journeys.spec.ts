import { test, expect } from '@playwright/test';

test.describe('CSIS SmartAssist Critical User Journeys', () => {

  test('Unauthenticated Redirect Flow', async ({ page }) => {
    // Attempting to visit /chat directly without being logged in should redirect to /
    await page.goto('/chat');
    
    // Playwright automatically waits for URL to change
    await expect(page).toHaveURL('/');
    
    // Check that login screen is visible
    await expect(page.locator('text=Sign in with BITS Mail')).toBeVisible();
  });

  // Since actual authentication uses Google OAuth and Supabase with strict domain checking,
  // we would typically use a seeded user session cookie for E2E tests.
  // For the purpose of these robust tests, we'll demonstrate the E2E structure assuming 
  // auth state can be mocked or injected via Playwright storageState, or we'll mock the Supabase auth.
  
  // NOTE: In a true CI environment, we use `storageState` with a valid test user token.
  test.describe('Authenticated flows', () => {
    
    // Intercept API calls to mock the backend responses, allowing full frontend E2E testing
    // without relying on Gemini limits or live DB state during CI.
    test.beforeEach(async ({ page }) => {
      // Mock user session on frontend via localStorage/cookies or intercept auth endpoints if needed
      
      // Mock the initial session load
      await page.route('/api/chat/sessions', async route => {
        if (route.request().method() === 'GET') {
          await route.fulfill({ json: [] });
        } else if (route.request().method() === 'POST') {
          await route.fulfill({ json: { id: 'sess-123', title: 'New Chat' } });
        }
      });
      
      // Mock bookings list
      await page.route('/api/calendar/bookings*', async route => {
        await route.fulfill({ json: [] });
      });
    });

    test('Chat & RAG Journey', async ({ page }) => {
      // Go directly to chat, intercepting auth to simulate logged in state
      await page.route('**/auth/v1/user', async route => {
        await route.fulfill({ json: { id: 'u-123', email: 'test@goa.bits-pilani.ac.in', user_metadata: { full_name: 'Test User' } } });
      });
      
      await page.goto('/chat');
      
      // Verify empty state
      await expect(page.locator('text=Start a conversation')).toBeVisible();

      // Mock chat send stream response
      await page.route('/api/chat/send', async route => {
        const payload = route.request().postDataJSON();
        expect(payload.message).toBe('What are the rules for TA allocation?');
        
        // Fulfill with a mocked text response (not stream for simplicity, or stream mock)
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: 'Here are the rules for TA allocation...'
        });
      });

      // Send a message
      await page.fill('textarea[placeholder="Ask about syllabi, policies, or book a lab..."]', 'What are the rules for TA allocation?');
      await page.click('button:has-text("↑")');

      // Verify the response appears
      await expect(page.locator('text=Here are the rules for TA allocation...')).toBeVisible();
    });

    test('Booking Journey', async ({ page }) => {
      // Mock auth
      await page.route('**/auth/v1/user', async route => {
        await route.fulfill({ json: { id: 'u-123', email: 'test@goa.bits-pilani.ac.in', user_metadata: { full_name: 'Test User' } } });
      });

      await page.goto('/chat');

      // Mock chat returning a booking proposal
      await page.route('/api/chat/send', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: 'I can book that for you. ```booking_proposal\n{"room_id": "dlt_8", "room_name": "DLT-8", "title": "Test Event", "start_time": "2026-07-13T11:00:00+05:30", "end_time": "2026-07-13T12:00:00+05:30", "description": ""}\n```'
        });
      });

      // Send booking request
      await page.fill('textarea', 'Book DLT-8 tomorrow 11am to 12pm');
      await page.click('button:has-text("↑")');

      // Wait for the Booking Proposal card to appear
      await expect(page.locator('text=BOOKING PROPOSAL')).toBeVisible();
      await expect(page.locator('text=DLT-8')).toBeVisible();
      await expect(page.locator('text=Test Event')).toBeVisible();

      // Mock the create booking API
      await page.route('/api/calendar/book', async route => {
        await route.fulfill({
          status: 200,
          json: { id: 'b-999', status: 'pending' }
        });
      });

      // Click Confirm
      await page.click('button#confirm-booking-btn');

      // Verify UI changes to submitted state
      await expect(page.locator('text=✅ Booking submitted! Awaiting admin approval.')).toBeVisible();
    });
  });
});
