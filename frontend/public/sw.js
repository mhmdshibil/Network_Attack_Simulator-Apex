/* Apex Argus service worker — Phase 6E (PWA push notifications) */

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()))

self.addEventListener('push', event => {
  let data = { title: 'Apex Argus Alert', body: 'Security event detected', tag: 'apex-alert', url: '/' }
  try { if (event.data) data = { ...data, ...event.data.json() } } catch (_) {}
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body:  data.body,
      icon:  '/favicon.ico',
      badge: '/favicon.ico',
      tag:   data.tag || 'apex-alert',
      data:  { url: data.url || '/' },
      requireInteraction: false,
    })
  )
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  const targetUrl = event.notification.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      const existing = clients.find(c => c.url === targetUrl && 'focus' in c)
      if (existing) return existing.focus()
      return self.clients.openWindow(targetUrl)
    })
  )
})
