import { describe, it, expect, beforeAll } from 'vitest';
import request from 'supertest';
import { openDb, setDb } from '../src/db.js';
import { createApp } from '../src/app.js';

let app;

beforeAll(() => {
  // Isolated in-memory DB so this test never touches console/data/console.db.
  setDb(openDb(':memory:'));
  app = createApp();
});

describe('auth guard', () => {
  it('redirects an unauthenticated GET / to /login', async () => {
    const res = await request(app).get('/');
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe('/login');
  });

  it('redirects an unauthenticated GET /agent/:role/:slug to /login', async () => {
    const res = await request(app).get('/agent/cto/contabo-migration');
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe('/login');
  });

  it('serves /login without redirecting', async () => {
    const res = await request(app).get('/login');
    expect(res.status).toBe(200);
  });

  it('returns 401 JSON (not a redirect) for unauthenticated API calls', async () => {
    const res = await request(app).get('/api/sessions');
    expect(res.status).toBe(401);
    expect(res.body).toEqual({ error: 'unauthenticated' });
  });

  it('rejects a request carrying a garbage cookie the same as no cookie', async () => {
    const res = await request(app).get('/').set('Cookie', 'mx_console=not-a-real-token');
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe('/login');
  });
});
