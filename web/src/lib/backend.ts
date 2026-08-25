/** Where the backend lives during development.
 *
 * Imported by both `vite.config.ts` (to aim the /api proxy) and the shell (to
 * name the backend it talks to), so the label and the proxy cannot drift apart.
 * In a built app FastAPI serves the SPA itself, so the page origin IS the backend.
 */
export const DEV_API_TARGET = "http://127.0.0.1:8000";

export const DEV_API_HOST = new URL(DEV_API_TARGET).host;
