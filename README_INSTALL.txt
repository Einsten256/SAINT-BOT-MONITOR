SAINT BOT ROOM — PHONE INSTALL (PWA)

1. Copy these into:
   D:\SAINT-BOT_WIRED\DASHBOARD\
   manifest.json
   service-worker.js

2. Create:
   D:\SAINT-BOT_WIRED\DASHBOARD\icons\
   and copy icon-192.png and icon-512.png there.

3. Add the routes from server_PWA_routes.txt to server.py.

4. In DASHBOARD/index.html, inside <head>, add:
   <link rel="manifest" href="/manifest.json">
   <meta name="theme-color" content="#070b14">
   <meta name="mobile-web-app-capable" content="yes">
   <meta name="apple-mobile-web-app-capable" content="yes">
   <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

   Before </body>, add:
   <script>
   if ("serviceWorker" in navigator) {
     navigator.serviceWorker.register("/service-worker.js").catch(console.error);
   }
   </script>

5. Commit and push:
   cd "D:\SAINT-BOT_WIRED"
   git add DASHBOARD server.py
   git commit -m "Add SAINT BOT ROOM mobile PWA"
   git push

6. On Android Chrome:
   open https://saint-bot-monitor.onrender.com
   then ⋮ -> Install app / Add to Home screen.
