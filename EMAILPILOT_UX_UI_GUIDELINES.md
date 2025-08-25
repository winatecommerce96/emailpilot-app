EmailPilot Frontend UX/UI Guidelines

Overview
- Goal: Create a calm, professional UI with clear hierarchy, minimal visual noise, and consistent primary actions.
- Scope: Global shadows, primary button styling, login screen layout, and popover/dialog usage.

Design Tokens (source of truth)
- Colors (defined in `frontend/public/index.html` under `:root`):
  - `--ep-blue: #3369DC`
  - `--ep-purple: #8A6CF7`
  - `--ep-lime: #C5FF75`
  - `--ep-black: #000000`
  - `--ep-white: #FFFFFF`
- Typography:
  - Body: Poppins, ui-sans-serif, system-ui
  - Headings: Red Hat Display, weight 900
- Radii and borders:
  - Cards: 20px radius, 4px solid `--ep-black`
  - Buttons/inputs: rounded-lg
- Motion:
  - Use `ep-hero-bg` animated gradient for hero/login; respect `prefers-reduced-motion` (already implemented)

Global Class Names (apply these to implement the system)
- Containers/Cards: `ep-card`, `ep-shadow-none` (default), `ep-shadow-heavy` (login + popovers only)
- Primary Button: `ep-btn-primary` (auto-applied by theme enhancer where appropriate)
- Force primary style: add `data-ep-primary` or class `ep-primary`
- Animated brand background: `ep-hero-bg`

Shadow Policy
- Bold blocky shadow (`ep-shadow-heavy`) is allowed only for:
  - Login screen primary card
  - Popovers and modal/dialog containers (e.g., context menus, event modals)
- All other large containers/cards must be flat:
  - Use `ep-card ep-shadow-none`
  - `brand-theme.js` strips Tailwind shadow utility classes from large content blocks to prevent heavy shadows.
- Buttons: No bold/sharp shadows anywhere.

Buttons
- Primary (implemented): `.ep-btn-primary`
  - Gradient ep-blue → ep-purple, white text, rounded-lg, bold label
  - Hover: gradient slide; Focus: visible outline; Disabled: reduced opacity
  - Prefer one primary per view; avoid stacking primaries
- Secondary (recommended pattern for future): `.ep-btn-secondary` (not yet implemented)
  - Neutral background or subtle outline, rounded-lg, consistent padding with primary
  - Use for neutral actions like “Cancel”, “Back”, or less-critical CTAs
- Destructive (recommended pattern for future): `.ep-btn-danger` (not yet implemented)
  - Red theme, clear hover/focus, never default/focused by mistake

Inputs & Forms
- Inputs: `w-full px-4 py-2 border border-gray-300 rounded-lg`
- Focus ring: `focus:ring-2 focus:ring-indigo-500 focus:border-transparent`
- Form submit buttons should use `.ep-btn-primary` for the main action

Links
- Default: neutral gray or blue depending on placement, clear hover state
- Inside login microcopy: use underlined links for terms/privacy

Primary Buttons
- Class: `ep-btn-primary` (gradient ep-blue → ep-purple, rounded-lg, bold label, smooth hover, visible focus ring, disabled state)
- Applied automatically by `brand-theme.js` to likely primary actions (e.g., elements with `bg-gradient-to-r`, `from-indigo-600`, etc.).
- To force apply on any button:
  - Add `data-ep-primary` attribute OR the class `ep-primary`.
- Buttons should not use Tailwind `shadow*` utilities.

Login Screen UX
- Card: `ep-card ep-shadow-heavy` on animated brand background (`ep-hero-bg`).
- Heading (dynamic): shows “Sign In” or “Create Account” above the Google button.
- Divider: label “Or use your email”.
- Form: Email/Password; in Create Account mode include Name + Company (optional).
- Bottom actions (mode-aware):
  - Login mode: primary “Create Account” (prominent), secondary “Continue as Guest”.
  - Create Account mode: primary “Sign In”, secondary “Continue as Guest”.
- Microcopy (friendly, pilot themed):
  - Login: “New to the crew? Create an account to get cleared for takeoff.”
  - Create Account: “Already on board? Sign in to resume your flight.”

Navigation
- Top nav uses `animated-gradient-nav` (animated brand gradient); avoid heavy shadows
- Keep nav icons/branding compact, with clear contrast and accessible hit targets

Popovers and Dialogs
- Use `ep-shadow-heavy` for container shell only; contents remain flat.
- Components already configured:
  - EventModal, EventModalDynamic
  - PlanCampaignDialog, CalendarPlanningModal
  - Calendar context menus (Calendar.js, CalendarDynamic.js)

Implementation Hooks (files)
- Global CSS and tokens: `frontend/public/index.html`
  - Defines `.ep-btn-primary` and brand color variables.
- Theme enhancer: `frontend/public/dist/brand-theme.js`
  - Enforces `ep-card ep-shadow-none` on large containers; strips Tailwind shadows.
  - Applies `.ep-btn-primary` to likely primary buttons and anything with `data-ep-primary`/`ep-primary`.
  - Observes DOM mutations to keep late-rendered views consistent.
- Login screen (precompiled): `frontend/public/dist/AuthScreen.js`
- Login screen (source): `frontend/public/components/AuthScreen.js`

Developer Notes
- To ensure consistent primary CTAs, prefer adding `data-ep-primary` to primary buttons created in new components.
- Avoid adding Tailwind `shadow*` classes to containers; the theme enhancer will remove them for consistency.
- Keep new dialogs/popovers consistent by adding `ep-shadow-heavy` to their outer container.
- If a secondary button style is desired, add a dedicated `.ep-btn-secondary` (outline or subtle neutral) and integrate it into `brand-theme.js` similarly to the primary style.

Accessibility
- Minimum contrast: text vs background meets WCAG AA where feasible
- Always provide focus-visible styles (primary buttons already do)
- Respect `prefers-reduced-motion`; avoid gratuitous animations

AI Implementation Checklist
- For any new view:
  - Wrap large content blocks with `ep-card ep-shadow-none`; do not add Tailwind `shadow*` utilities
  - Primary action: add `data-ep-primary` (or ensure the button matches auto-detection) to get `.ep-btn-primary`
  - Secondary or neutral actions: avoid gradient; consider future `.ep-btn-secondary`
  - Popovers/Modals: add `ep-shadow-heavy` to the outer container only
  - Inputs: use the standard input classes and focus ring
  - Use pilot-themed microcopy on login/register entry points; keep tone friendly and concise

Verification
- Run `npm run serve` and open `http://localhost:8080/`.
- Visual pass:
  - Login: bold shadow on card only; heading + microcopy present; bottom actions switch with mode.
  - Dashboard/Admin/Calendar: cards flat (no bold shadows); primary CTAs share the same look.
  - Popovers/Dialogs: bold shadow on shell; internals clean.

Change Log (key updates tied to this guideline)
- `frontend/public/index.html`: button style `.ep-btn-primary`; removed heavy button shadows; brand tokens.
- `frontend/public/dist/brand-theme.js`: flat cards; strip `shadow*`; auto-apply primary button style.
- `frontend/public/dist/AuthScreen.js` + `frontend/public/components/AuthScreen.js`: refined login layout, microcopy, dynamic heading; removed top toggle.
- Dialog/Popover components updated to use `ep-shadow-heavy`.
