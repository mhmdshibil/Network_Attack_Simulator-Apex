/**
 * usePushNotifications — Phase 6E.
 * Registers the service worker, requests permission, and subscribes to push.
 * Used by Sidebar bell button via dynamic import (lazy — not needed until clicked).
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

/**
 * Returns 'subscribed' | 'denied' | 'idle'
 */
export async function subscribeToPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return 'idle'
  }

  // Register (or reuse existing) service worker
  let reg
  try {
    reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' })
    await navigator.serviceWorker.ready
  } catch (e) {
    console.warn('[SW] registration failed', e)
    return 'idle'
  }

  // Request permission
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return 'denied'

  // Get VAPID public key from server
  let vapidKey
  try {
    const r = await fetch(`${API_BASE}/api/push/vapid-public-key`)
    if (!r.ok) return 'idle'
    const j = await r.json()
    vapidKey = j.public_key
  } catch (_) {
    return 'idle'
  }

  if (!vapidKey) return 'idle'

  // Subscribe
  try {
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: _urlBase64ToUint8Array(vapidKey),
    })
    const subJson = sub.toJSON()

    const token = localStorage.getItem('apex_token')
    await fetch(`${API_BASE}/api/push/subscribe`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        endpoint: subJson.endpoint,
        keys: subJson.keys,
        user_agent: navigator.userAgent.slice(0, 200),
      }),
    })
    return 'subscribed'
  } catch (e) {
    console.warn('[PUSH] subscribe failed', e)
    return 'idle'
  }
}

export async function unsubscribeFromPush() {
  if (!('serviceWorker' in navigator)) return
  try {
    const reg = await navigator.serviceWorker.getRegistration('/')
    if (!reg) return
    const sub = await reg.pushManager.getSubscription()
    if (!sub) return
    const endpoint = sub.endpoint
    await sub.unsubscribe()
    const token = localStorage.getItem('apex_token')
    await fetch(`${API_BASE}/api/push/subscribe`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ endpoint }),
    })
  } catch (e) {
    console.warn('[PUSH] unsubscribe failed', e)
  }
}

function _urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw     = atob(base64)
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)))
}
