import apiClient from './client';

export async function login(email, password) {
  const { data } = await apiClient.post('/auth/login', { email, password });
  return data.access_token;
}

export function getCurrentUser(token) {
  try {
    const bytes = atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'));
    const { sub, email, role, name, exp } = JSON.parse(
      new TextDecoder().decode(Uint8Array.from(bytes, c => c.charCodeAt(0)))
    );
    if (!sub || !role || !(exp > Date.now() / 1000)) return null;
    return { id: sub, email, rol: role, nombre: name };
  } catch {
    return null;
  }
}
