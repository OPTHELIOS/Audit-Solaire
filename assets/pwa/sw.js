// Service worker de l'appli OPT'HELIOS — Audit Solaire Thermique.
//
// Deux raisons d'exister, aucune n'etant la mise en cache de l'appli :
//
// 1. Rendre l'appli INSTALLABLE sur Android. Chrome n'affiche sa banniere
//    "Installer l'application" que si la page declare un service worker
//    muni d'un gestionnaire `fetch`. Sans ce fichier, l'ajout a l'ecran
//    d'accueil reste possible mais uniquement en manuel, via le menu du
//    navigateur. (Sur iOS, l'ajout est de toute facon toujours manuel :
//    menu Partager de Safari.)
//
// 2. Remplacer l'ecran d'erreur du navigateur par un ecran OPT'HELIOS
//    quand le reseau tombe. Une fois l'appli lancee depuis l'ecran
//    d'accueil, une coupure affiche sinon la page d'erreur brute de
//    Safari/Chrome, ce qui donne l'impression que l'appli a plante.
//
// CE QUI N'EST VOLONTAIREMENT PAS FAIT : mettre en cache le code de
// l'appli. Streamlit sert un bundle JS versionne et pilote l'ecran par
// websocket ; un cache agressif servirait un jour un bundle perime face a
// un serveur a jour, panne insoluble pour l'utilisateur. Tout ce qui n'est
// pas une icone precachee part donc au reseau, systematiquement.

const CACHE = "opthelios-audit-v1";
const OFFLINE_URL = "/offline.html";

// Strict minimum : l'ecran de repli et les icones. Aucun fichier applicatif.
const PRECACHE = [
  OFFLINE_URL,
  "/icon-192.png",
  "/icon-512.png",
  "/apple-touch-icon.png",
  "/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      // `addAll` echoue en bloc si un seul fichier manque : on tolere les
      // absences une par une pour ne jamais empecher l'installation.
      .then((cache) =>
        Promise.all(
          PRECACHE.map((url) =>
            cache.add(url).catch((e) =>
              console.warn("[opthelios-sw] precache ignore pour " + url, e)
            )
          )
        )
      )
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Endpoints internes de Streamlit (websocket, health, upload de
  // fichiers) : jamais interceptes, comportement navigateur par defaut.
  if (url.pathname.startsWith("/_stcore/")) return;

  // Navigation (ouverture / rechargement de l'appli) : reseau d'abord,
  // ecran OPT'HELIOS de repli si le reseau ne repond pas.
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  // Reste : reseau d'abord, cache en secours uniquement pour ce qui a ete
  // precache (les icones). Renvoie une 504 explicite plutot qu'une
  // promesse rejetee, qui afficherait une erreur illisible.
  event.respondWith(
    fetch(req).catch(() =>
      caches
        .match(req)
        .then(
          (hit) =>
            hit ||
            new Response("", { status: 504, statusText: "Reseau indisponible" })
        )
    )
  );
});
