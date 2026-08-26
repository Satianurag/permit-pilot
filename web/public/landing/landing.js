/**
 * Permit Pilot landing — maps, scroll narrative, verified NYC data
 */
(function () {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /** Verified from seeds.py + PLUTO (64uk-42ks) coordinates */
  const CASES = [
    {
      id: "parsons",
      address: "43-30 Parsons Boulevard",
      borough: "Queens",
      bbl: "4051980021",
      bin: "4117367",
      work: "Construction fence — demolition of 3 story building",
      owner: "Flushing Hospital Medical Center",
      lng: -73.8172074,
      lat: 40.7563439,
    },
    {
      id: "178",
      address: "112-08 178 Street",
      borough: "Queens",
      bbl: "4103000034",
      bin: null,
      work: "Alteration",
      owner: null,
      lng: -73.7740477,
      lat: 40.6959154,
    },
    {
      id: "macon",
      address: "761 Macon Street",
      borough: "Brooklyn",
      bbl: "3014930048",
      bin: "3040031",
      work: "Plumbing modifications to existing kitchen",
      owner: null,
      lng: -73.921091,
      lat: 40.6845931,
    },
  ];

  const DEPARTMENTS = [
    { name: "Zoning", dataset: "64uk-42ks", detail: "PLUTO zoning district & land use" },
    { name: "Building", dataset: "3h2n-5cm9", detail: "DOB violations + rbx6-tga4 permits" },
    { name: "Fire", dataset: "bi53-yph3", detail: "FDNY violation records" },
    { name: "Utilities", dataset: "skr7-cxt3", detail: "DEP ECB violations by address" },
    { name: "Landmarks", dataset: "gpmc-yuvp", detail: "LPC landmark & historic district" },
    { name: "Housing", dataset: "wvxf-dwi5", detail: "HPD open violation classes" },
    { name: "Critic", dataset: "policy", detail: "Cite-or-reject on department claims" },
  ];

  const header = document.querySelector(".pp-header");
  const burger = document.querySelector(".pp-burger");
  const nav = document.querySelector(".pp-nav");

  window.addEventListener(
    "scroll",
    () => header?.classList.toggle("is-scrolled", window.scrollY > 32),
    { passive: true },
  );

  burger?.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    burger.setAttribute("aria-expanded", String(open));
  });

  document.querySelectorAll(".pp-faq-q").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = btn.closest(".pp-faq-item");
      const wasOpen = item.classList.contains("is-open");
      document.querySelectorAll(".pp-faq-item").forEach((i) => i.classList.remove("is-open"));
      if (!wasOpen) item.classList.add("is-open");
      btn.setAttribute("aria-expanded", String(!wasOpen));
    });
  });

  document.querySelectorAll(".pp-reveal").forEach((el) => {
    if (!("IntersectionObserver" in window)) {
      el.classList.add("is-visible");
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -4% 0px" },
    );
    obs.observe(el);
  });

  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.getAttribute("href");
      if (!id || id === "#") return;
      const target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
        nav?.classList.remove("is-open");
      }
    });
  });

  // ── MapLibre maps ──
  const MAP_STYLE = "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json";
  const maps = [];

  function makePinEl(color) {
    const el = document.createElement("div");
    el.className = "pp-map-pin";
    el.style.setProperty("--pin-color", color);
    return el;
  }

  function initMap(containerId, options = {}) {
    const el = document.getElementById(containerId);
    if (!el || !window.maplibregl) return null;

    const map = new maplibregl.Map({
      container: el,
      style: MAP_STYLE,
      center: options.center || [-73.92, 40.72],
      zoom: options.zoom ?? 10.2,
      pitch: options.pitch ?? 0,
      bearing: options.bearing ?? -12,
      interactive: options.interactive !== false,
      attributionControl: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    if (options.nav) {
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    }

    maps.push(map);
    return map;
  }

  function addCaseMarkers(map, { flyOnClick = false, activeId = null } = {}) {
    if (!map) return;

    const onLoad = () => {
      CASES.forEach((c, i) => {
        const color = i === 0 ? "#fe4a23" : i === 1 ? "#2563eb" : "#16a34a";
        const marker = new maplibregl.Marker({ element: makePinEl(color), anchor: "bottom" })
          .setLngLat([c.lng, c.lat])
          .setPopup(
            new maplibregl.Popup({ offset: 28, closeButton: false }).setHTML(
              `<strong>${c.address}</strong><br><span style="color:#64748b;font-size:12px">BBL ${c.bbl}${c.bin ? ` · BIN ${c.bin}` : ""}</span>`,
            ),
          )
          .addTo(map);

        if (flyOnClick) {
          marker.getElement().addEventListener("click", () => selectCase(c.id));
        }
      });

      if (activeId) {
        const c = CASES.find((x) => x.id === activeId);
        if (c) map.flyTo({ center: [c.lng, c.lat], zoom: 15.5, pitch: 45, duration: 1200 });
      }
    };

    if (map.loaded()) onLoad();
    else map.on("load", onLoad);
  }

  // Hero overview map
  const heroMap = initMap("pp-hero-map", {
    center: [-73.87, 40.72],
    zoom: 10.4,
    pitch: 38,
    bearing: -18,
    interactive: false,
  });

  if (heroMap) {
    heroMap.scrollZoom.disable();
    heroMap.boxZoom.disable();
    heroMap.dragRotate.disable();
    heroMap.dragPan.disable();
    heroMap.keyboard.disable();
    heroMap.doubleClickZoom.disable();
    heroMap.touchZoomRotate.disable();
    addCaseMarkers(heroMap);

    if (!reduced) {
      let t = 0;
      const animate = () => {
        t += 0.0004;
        heroMap.setBearing(-18 + Math.sin(t) * 4);
        heroMap.setPitch(38 + Math.sin(t * 0.7) * 3);
        requestAnimationFrame(animate);
      };
      heroMap.on("load", () => requestAnimationFrame(animate));
    }
  }

  // Cases explorer map
  const casesMap = initMap("pp-cases-map", {
    center: [-73.87, 40.72],
    zoom: 10.2,
    pitch: 42,
    bearing: -14,
    nav: true,
  });
  addCaseMarkers(casesMap, { flyOnClick: true });

  function selectCase(id) {
    const c = CASES.find((x) => x.id === id);
    if (!c) return;

    document.querySelectorAll(".pp-case-card").forEach((card) => {
      card.classList.toggle("is-active", card.dataset.case === id);
    });

    casesMap?.flyTo({
      center: [c.lng, c.lat],
      zoom: 16,
      pitch: 50,
      bearing: -20,
      duration: 1400,
      essential: true,
    });

    const popup = document.querySelector(".pp-case-card.is-active .pp-case-card-title");
    popup?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "nearest" });
  }

  document.querySelectorAll(".pp-case-card").forEach((card) => {
    card.addEventListener("click", () => selectCase(card.dataset.case));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        selectCase(card.dataset.case);
      }
    });
  });

  // Department pipeline animation
  const pipelineItems = document.querySelectorAll(".pp-pipeline-item");
  if (pipelineItems.length && "IntersectionObserver" in window) {
    const pipeObs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            pipelineItems.forEach((item, i) => {
              setTimeout(() => item.classList.add("is-lit"), i * 120);
            });
            pipeObs.disconnect();
          }
        });
      },
      { threshold: 0.25 },
    );
    const pipe = document.querySelector(".pp-pipeline");
    if (pipe) pipeObs.observe(pipe);
  }

  if (!reduced && window.gsap && window.ScrollTrigger && window.innerWidth > 960) {
    gsap.registerPlugin(ScrollTrigger);
    gsap.to(".pp-hero-device", {
      y: -40,
      scrollTrigger: { trigger: ".pp-hero", start: "top top", end: "bottom top", scrub: true },
    });
  }

  // Resize maps
  window.addEventListener("resize", () => maps.forEach((m) => m.resize()));

  // Expose for debugging
  window.PP_LANDING = { CASES, DEPARTMENTS, selectCase };
})();
