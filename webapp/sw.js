const CACHE_NAME = 'mimy-wiki-v5'; // バージョンを上げて古いキャッシュを破棄

self.addEventListener('install', (event) => {
    // インストール時に即座にアクティブにする
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    // 古いキャッシュをすべて削除する
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    return caches.delete(cacheName);
                })
            );
        })
    );
});

self.addEventListener('fetch', (event) => {
    // 開発中のため、キャッシュを一切使わず常にネットワークから取得する
    event.respondWith(fetch(event.request));
});
