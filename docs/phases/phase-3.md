# Phase 3: Frontend Authentication UI

## Objective

Stand up the React frontend with a working authentication flow: registration, login, silent re-authentication on page reload, and protected routing. This phase establishes the foundational structure (providers, API client, auth state, routing) that every subsequent feature will build on.

---

## Technical Specifications

### 1. Dependency Setup

Install the required packages into the existing Vite + React + TypeScript project:

- `@mantine/core`, `@mantine/hooks`, `@mantine/form`, `@mantine/notifications` — UI components and form handling.
- `@tabler/icons-react` — icon set that pairs with Mantine.
- `@tanstack/react-query`, `@tanstack/react-query-devtools` — server state and data fetching.
- `axios` — HTTP client.
- `react-router-dom` — client-side routing.


### 2. Application Providers (`main.tsx`)

Wrap the app in the required providers in this order (inner to outer):

1. `MantineProvider` — theme and component defaults.
2. `Notifications` — toast notification system.
3. `QueryClientProvider` — TanStack Query client instance.
4. `AuthProvider` — custom context (see §3).
5. `BrowserRouter` — routing.

### 3. Auth State: React Context

Auth state is managed with a plain React Context + `useReducer`.

**State shape:**
```ts
interface AuthState {
  accessToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean; // true during the boot-time silent refresh
}
```

**Actions:** `SET_AUTH`, `SET_ACCESS_TOKEN`, `CLEAR_AUTH`, `SET_LOADING`.

The context exposes the state and a `dispatch` function. A `useAuth()` hook wraps the context access and throws if used outside the provider.

### 4. HTTP Client (`src/api/client.ts`)

A singleton `axios` instance with:

- `baseURL` set to `VITE_API_URL ?? ""` + `/api/v1` — empty in dev (falls through to Vite proxy), set to the backend origin in production.
- `withCredentials: true` — required to send the httpOnly refresh cookie.
- **Request interceptor:** reads `accessToken` from the auth context (via a getter passed from the provider) and attaches `Authorization: Bearer <token>` to every request.
- **Response interceptor (401 handler):** on a 401, triggers a token refresh (see §5), replays the original request with the new access token, and redirects to `/login` if the refresh fails.

The pending-request queue pattern must be implemented: if a refresh is already in flight when a second 401 arrives, the second request is held and replayed once the single refresh resolves. This avoids a flood of parallel refresh calls.

### 5. Token Refresh (`src/api/authRefresh.ts`)

A module-level promise singleton (`_refreshPromise`) ensures the refresh endpoint is called at most once at a time, regardless of how many concurrent requests trigger a 401.

**Two-phase refresh strategy:**

- **Phase 1 (primary):** call `POST /api/v1/auth/token/refresh/` with no body — the backend reads the httpOnly cookie.
- **Phase 2 (fallback):** if Phase 1 fails (cookie absent due to Safari ITP, Brave Shields, or proxy stripping), read a stored token from `sessionStorage` and send it in the request body instead.

On a successful refresh the backend returns a rotated refresh token in the response body. Store it in `sessionStorage` to keep the fallback copy in sync.

### 6. Auth API (`src/api/auth.ts`)

Domain-specific functions that call the auth endpoints through the shared axios client. Each function maps to one endpoint: `register`, `login`, `logout`, and `me`. The `login` function is responsible for persisting the rotated refresh token returned in the response body to `sessionStorage` (the fallback path). The `logout` function clears that stored token before calling the server, so even if the blacklist request fails the local fallback copy is gone.

### 7. Silent Re-authentication on Boot

`AuthProvider` runs a `useEffect` on mount that attempts a silent refresh + `/me/` fetch before rendering any protected content. While this is in flight, `isLoading` is `true` and the app renders a full-screen spinner. If the refresh fails (no valid cookie), `isLoading` is set to `false` and the user is unauthenticated — no redirect happens here, the route guards handle that.

This ensures users with a live session stay logged in across hard page reloads without any credentials in `localStorage`.

### 8. Pages

#### `RegisterPage` (`/register`)
- Mantine `TextInput` fields for `email`, `password`, `password_confirm`.
- On success: show a success notification and redirect to `/login`.
- On failure: display field-level errors from the API response.

#### `LoginPage` (`/login`)
- Mantine `TextInput` + `PasswordInput` for `email` and `password`.
- On success: call `SET_AUTH` with the access token and user payload (embedded in the login response), then redirect to `/`.
- On failure: display a general error notification.

Both pages use a centered card layout and are publicly accessible.

### 9. Route Guards

Two guard components in `App.tsx`:

- **`ProtectedRoute`:** redirects unauthenticated users to `/login`. Wraps all app pages.
- **`PublicRoute`:** redirects already-authenticated users to `/` (prevents logged-in users from seeing login/register). Wraps `/login` and `/register`.

### 10. Backend: CORS & Proxy Setup

**Backend (`django-cors-headers`):**
- Add `corsheaders` to `INSTALLED_APPS`.
- Add `CorsMiddleware` before `CommonMiddleware` in `MIDDLEWARE`.
- Set `CORS_ALLOWED_ORIGINS` to `http://localhost:3000` in dev (read from `.env`).
- Set `CORS_ALLOW_CREDENTIALS = True` — required for the browser to send the httpOnly cookie cross-origin.

**Frontend (`vite.config.ts`):**
- Configure a dev-server proxy so `/api` requests are forwarded to `http://backend:8000` (the Docker service name), avoiding CORS issues in local development entirely.

---

## File Structure (New Files)

```
frontend/src/
├── api/
│   ├── auth.ts
│   ├── authRefresh.ts
│   └── client.ts
├── context/
│   └── AuthContext.tsx       # AuthProvider, useAuth hook, reducer
├── pages/
│   ├── auth/
│   │   ├── LoginPage.tsx
│   │   └── RegisterPage.tsx
│   └── NotFoundPage.tsx
├── components/
│   └── layout/
│       └── AppShell.tsx      # Top nav with logout — placeholder for Phase 5
└── types/
    └── auth.ts               # User, AuthTokens interfaces
```

---

## Acceptance Criteria

- [ ] `npm install` completes with no peer dependency errors.
- [ ] Mantine theme renders correctly at `http://localhost:3000`.
- [ ] `POST /api/v1/auth/register/` via the Register form creates a user and shows a success notification.
- [ ] `POST /api/v1/auth/login/` via the Login form stores the access token in context and redirects to `/`.
- [ ] Navigating to `/` without being logged in redirects to `/login`.
- [ ] Navigating to `/login` while logged in redirects to `/`.
- [ ] A hard page reload restores the authenticated session silently (no flash of the login page).
- [ ] Logout clears the session, clears the cookie, and redirects to `/login`.
- [ ] All API requests to `/api/v1/` include the `Authorization: Bearer` header.
- [ ] A 401 on any request triggers a silent token refresh and replays the original request.
