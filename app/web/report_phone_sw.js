/* No health content is cached. A push carries no body; text is fixed here. */
'use strict';
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('push',event=>event.waitUntil(self.registration.showNotification('PTDS',{body:'你的状态报告已生成',tag:'ptds-report-ready',icon:'/report-icon-192.png',badge:'/report-icon-192.png',data:{path:'/'}})));
self.addEventListener('notificationclick',event=>{event.notification.close();event.waitUntil((async()=>{const tabs=await self.clients.matchAll({type:'window',includeUncontrolled:true});for(const tab of tabs){if(new URL(tab.url).origin===self.location.origin){await tab.focus();tab.postMessage({type:'REPORT_READY'});return;}}await self.clients.openWindow('/');})());});
// No fetch interception, offline report store or session credential in the worker.
