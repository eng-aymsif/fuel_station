/* وثائق مُعين — السلوك التفاعلي (Vanilla JS، بلا innerHTML لبيانات البحث) */
(function () {
	"use strict";

	const root = document.documentElement;
	const LANG_COOKIE = "fuel_station_docs_lang";
	const THEME_KEY = "fuel_station_docs_theme";
	const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

	let data = { ui: {}, titles: {}, nav: [] };
	const $ = (sel, ctx) => (ctx || document).querySelector(sel);
	const $$ = (sel, ctx) => Array.from((ctx || document).querySelectorAll(sel));
	const lang = () => (root.lang === "ar" ? "ar" : "en");
	const t = (key) => (data.ui[key] ? data.ui[key][lang()] : key);

	/* ---------- المظهر ---------- */
	function currentTheme() {
		const explicit = root.getAttribute("data-theme");
		if (explicit) return explicit;
		return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
	}
	function toggleTheme() {
		const next = currentTheme() === "dark" ? "light" : "dark";
		root.setAttribute("data-theme", next);
		try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* تخزين غير متاح */ }
	}

	/* ---------- اللغة ---------- */
	function applyI18nAttributes() {
		$$("[data-i18n-aria]").forEach((el) => el.setAttribute("aria-label", t(el.dataset.i18nAria)));
		$$("[data-i18n-placeholder]").forEach((el) => el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder)));
		if (data.titles[lang()]) document.title = data.titles[lang()];
	}

	function swapArticle(next) {
		const article = $("#doc-article");
		if (!article || article.dataset.lang === next) return;
		const tpl = document.getElementById("doc-content-" + next);
		if (!tpl) return;
		const prev = article.dataset.lang;
		// المحتوى الحالي يذهب إلى <template> والمحتوى الآخر يحل محله (بلا معرفات مكررة في الصفحة)
		const stash = document.createElement("template");
		stash.id = "doc-content-" + prev;
		while (article.firstChild) stash.content.appendChild(article.firstChild);
		article.appendChild(tpl.content);
		tpl.replaceWith(stash);
		article.dataset.lang = next;
	}

	function setLang(next) {
		if (next === lang()) return;
		const article = $("#doc-article");
		const anchor = activeHeadingId;
		document.cookie = LANG_COOKIE + "=" + next + "; path=/; max-age=31536000; SameSite=Lax";

		const apply = () => {
			root.lang = next;
			root.dir = next === "ar" ? "rtl" : "ltr";
			swapArticle(next);
			applyI18nAttributes();
			enhanceArticle();
			buildToc();
			if (anchor) {
				const target = document.getElementById(anchor);
				if (target) target.scrollIntoView({ behavior: "instant", block: "start" });
			}
			if (article) requestAnimationFrame(() => article.classList.remove("is-switching"));
			renderResults();
		};

		if (article && !reduceMotion) {
			article.classList.add("is-switching");
			setTimeout(apply, 260);
		} else {
			apply();
		}
	}

	/* ---------- تحسينات المقال: أزرار النسخ ---------- */
	function enhanceArticle() {
		$$("#doc-article .copy-label").forEach((el) => { el.textContent = t("copy"); });
		$$("#doc-article .copy-btn").forEach((btn) => btn.setAttribute("aria-label", t("copy")));
	}

	async function copyCode(btn) {
		const code = btn.closest(".code-block").querySelector("code");
		const text = code ? code.textContent : "";
		try {
			await navigator.clipboard.writeText(text);
		} catch (e) {
			const area = document.createElement("textarea");
			area.value = text;
			area.style.position = "fixed";
			area.style.opacity = "0";
			document.body.appendChild(area);
			area.select();
			document.execCommand("copy");
			area.remove();
		}
		const label = btn.querySelector(".copy-label");
		btn.classList.add("copied");
		if (label) label.textContent = t("copied");
		setTimeout(() => {
			btn.classList.remove("copied");
			if (label) label.textContent = t("copy");
		}, 1600);
	}

	/* ---------- جدول المحتويات ---------- */
	let activeHeadingId = null;
	let tocObserver = null;

	function buildToc() {
		const nav = $("#toc");
		const article = $("#doc-article");
		if (!nav || !article) return;
		nav.textContent = "";
		const headings = $$("h2[id], h3[id]", article);
		const indicator = document.createElement("span");
		indicator.className = "toc-indicator";
		nav.appendChild(indicator);

		headings.forEach((h) => {
			const a = document.createElement("a");
			a.href = "#" + h.id;
			a.dataset.target = h.id;
			a.className = "lvl-" + h.tagName.charAt(1);
			const tag = h.querySelector(".h-tag");
			const clone = h.cloneNode(true);
			clone.querySelectorAll(".h-anchor, .h-dates, .h-tag").forEach((n) => n.remove());
			const label = clone.textContent.trim();
			if (tag && !label) {
				const s = document.createElement("span");
				s.className = "toc-tag";
				s.textContent = tag.textContent;
				a.appendChild(s);
			} else {
				a.textContent = label || (tag ? tag.textContent : h.id);
			}
			nav.appendChild(a);
		});

		if (tocObserver) tocObserver.disconnect();
		if (!headings.length) return;
		const visible = new Map();
		tocObserver = new IntersectionObserver((entries) => {
			entries.forEach((e) => visible.set(e.target.id, e.isIntersecting));
			const first = headings.find((h) => visible.get(h.id));
			if (first) setActive(first.id);
		}, { rootMargin: "-70px 0px -65% 0px" });
		headings.forEach((h) => tocObserver.observe(h));
		setActive(activeHeadingId && document.getElementById(activeHeadingId) ? activeHeadingId : headings[0].id);
	}

	function setActive(id) {
		activeHeadingId = id;
		const nav = $("#toc");
		if (!nav) return;
		let current = null;
		$$("a", nav).forEach((a) => {
			const on = a.dataset.target === id;
			a.classList.toggle("active", on);
			if (on) current = a;
		});
		const indicator = $(".toc-indicator", nav);
		if (indicator && current) {
			indicator.style.transform = "translateY(" + current.offsetTop + "px)";
			indicator.style.height = current.offsetHeight + "px";
			const box = nav.closest(".toc");
			if (box && (current.offsetTop < box.scrollTop || current.offsetTop > box.scrollTop + box.clientHeight - 80)) {
				box.scrollTo({ top: current.offsetTop - 80, behavior: "smooth" });
			}
		}
	}

	/* ---------- التمرير: شريط التقدم وزر الأعلى ---------- */
	function onScroll() {
		const max = document.documentElement.scrollHeight - window.innerHeight;
		const ratio = max > 0 ? Math.min(1, window.scrollY / max) : 0;
		const bar = $("#read-progress");
		if (bar) bar.style.transform = "scaleX(" + ratio + ")";
		const top = $("#to-top");
		if (top) {
			top.classList.toggle("show", window.scrollY > 500);
			top.style.setProperty("--ring", String(132 - 132 * ratio));
		}
	}

	/* ---------- القائمة الجانبية على الجوال ---------- */
	function setNav(open) {
		document.body.classList.toggle("nav-open", open);
		const btn = $("#menu-btn");
		const backdrop = $("#sidebar-backdrop");
		if (btn) btn.setAttribute("aria-expanded", String(open));
		if (backdrop) backdrop.hidden = !open;
	}

	/* ---------- البحث ---------- */
	let index = null;
	let loading = null;
	let results = [];
	let selected = 0;

	function loadIndex() {
		if (index) return Promise.resolve(index);
		if (!loading) {
			loading = fetch(data.search, { headers: { Accept: "application/json" } })
				.then((r) => r.json())
				.then((r) => { index = r.message || { ar: [], en: [] }; return index; })
				.catch(() => { loading = null; return { ar: [], en: [] }; });
		}
		return loading;
	}

	function normalize(s) {
		return (s || "")
			.toLowerCase()
			.replace(/[ً-ْـ]/g, "")
			.replace(/[أإآ]/g, "ا")
			.replace(/ة/g, "ه")
			.replace(/ى/g, "ي");
	}

	function search(query) {
		const terms = normalize(query).split(/\s+/).filter(Boolean);
		if (!terms.length || !index) return [];
		const out = [];
		(index[lang()] || []).forEach((entry) => {
			const heading = normalize(entry.heading);
			const text = normalize(entry.text);
			const title = normalize(entry.title);
			let score = 0;
			for (const term of terms) {
				const inHeading = heading.includes(term);
				const inText = text.includes(term);
				const inTitle = title.includes(term);
				if (!inHeading && !inText && !inTitle) return;
				score += (inHeading ? 10 : 0) + (inTitle ? 4 : 0) + (inText ? 1 : 0);
				if (heading.startsWith(term)) score += 5;
			}
			out.push({ entry, score });
		});
		return out.sort((a, b) => b.score - a.score).slice(0, 30).map((r) => r.entry);
	}

	// إبراز الكلمات بعقد DOM آمنة (بلا innerHTML)
	function highlight(el, text, terms) {
		const norm = normalize(text);
		const marks = [];
		terms.forEach((term) => {
			let i = norm.indexOf(term);
			while (term && i !== -1) { marks.push([i, i + term.length]); i = norm.indexOf(term, i + term.length); }
		});
		marks.sort((a, b) => a[0] - b[0]);
		let pos = 0;
		marks.forEach(([s, e]) => {
			if (s < pos) return;
			el.appendChild(document.createTextNode(text.slice(pos, s)));
			const m = document.createElement("mark");
			m.textContent = text.slice(s, e);
			el.appendChild(m);
			pos = e;
		});
		el.appendChild(document.createTextNode(text.slice(pos)));
	}

	function snippet(text, terms) {
		const norm = normalize(text);
		let at = -1;
		for (const term of terms) { at = norm.indexOf(term); if (at !== -1) break; }
		if (at < 60) return text.slice(0, 180);
		return "…" + text.slice(at - 50, at + 130);
	}

	function renderResults() {
		const box = $("#search-results");
		const input = $("#search-input");
		if (!box || !input || $("#search-overlay").hidden) return;
		const query = input.value.trim();
		box.textContent = "";
		if (!query) {
			const empty = document.createElement("p");
			empty.className = "search-empty";
			empty.textContent = index ? t("search_hint") : t("loading");
			box.appendChild(empty);
			results = [];
			return;
		}
		results = search(query);
		selected = Math.min(selected, Math.max(0, results.length - 1));
		if (!results.length) {
			const empty = document.createElement("p");
			empty.className = "search-empty";
			empty.textContent = index ? t("no_results") : t("loading");
			box.appendChild(empty);
			return;
		}
		const terms = normalize(query).split(/\s+/).filter(Boolean);
		const colors = {};
		data.nav.forEach((n) => { colors[n.slug] = n.color; });
		let lastPage = null;
		results.forEach((entry, i) => {
			const color = colors[entry.page] || "#7c3aed";
			if (entry.page !== lastPage) {
				const g = document.createElement("div");
				g.className = "search-group";
				g.style.setProperty("--gc", color);
				g.textContent = entry.title;
				box.appendChild(g);
				lastPage = entry.page;
			}
			const item = document.createElement("a");
			item.className = "search-item" + (i === selected ? " active" : "");
			item.href = data.base + "/" + entry.page + "#" + entry.id;
			item.setAttribute("role", "option");
			item.style.setProperty("--gc", color);
			item.style.setProperty("--n", String(i));
			const icon = document.createElement("span");
			icon.className = "search-item-icon";
			icon.textContent = "#";
			const body = document.createElement("span");
			body.className = "search-item-body";
			const title = document.createElement("div");
			title.className = "search-item-title";
			highlight(title, entry.heading, terms);
			const text = document.createElement("div");
			text.className = "search-item-text";
			highlight(text, snippet(entry.text, terms), terms);
			body.append(title, text);
			item.append(icon, body);
			item.addEventListener("mouseenter", () => select(i, false));
			item.addEventListener("click", () => closeSearch());
			box.appendChild(item);
		});
	}

	function select(i, scroll) {
		selected = i;
		$$(".search-item").forEach((el, n) => {
			el.classList.toggle("active", n === i);
			if (n === i && scroll) el.scrollIntoView({ block: "nearest" });
		});
	}

	function openSearch() {
		const overlay = $("#search-overlay");
		if (!overlay) return;
		overlay.hidden = false;
		document.body.style.overflow = "hidden";
		const input = $("#search-input");
		input.focus();
		input.select();
		renderResults();
		loadIndex().then(renderResults);
	}

	function closeSearch() {
		const overlay = $("#search-overlay");
		if (!overlay || overlay.hidden) return;
		overlay.hidden = true;
		document.body.style.overflow = "";
	}

	/* ---------- عدّادات الإحصاءات وظهور العناصر ---------- */
	function countUp(el) {
		const target = parseInt(el.dataset.count, 10) || 0;
		if (reduceMotion) { el.textContent = String(target); return; }
		const start = performance.now();
		const dur = 1400;
		const step = (now) => {
			const p = Math.min(1, (now - start) / dur);
			el.textContent = String(Math.round(target * (1 - Math.pow(1 - p, 3))));
			if (p < 1) requestAnimationFrame(step);
		};
		el.textContent = "0";
		requestAnimationFrame(step);
	}

	function setupReveal() {
		const items = $$(".reveal");
		if (!("IntersectionObserver" in window) || reduceMotion) {
			items.forEach((el) => el.classList.add("in"));
			$$("[data-count]").forEach(countUp);
			return;
		}
		const io = new IntersectionObserver((entries) => {
			entries.forEach((e) => {
				if (!e.isIntersecting) return;
				e.target.classList.add("in");
				const counter = e.target.querySelector("[data-count]");
				if (counter) countUp(counter);
				io.unobserve(e.target);
			});
		}, { threshold: 0.15 });
		items.forEach((el) => io.observe(el));
	}

	// توهج البطاقات يتبع مؤشر الفأرة
	function setupCardGlow() {
		$$(".card").forEach((card) => {
			card.addEventListener("pointermove", (e) => {
				const r = card.getBoundingClientRect();
				card.style.setProperty("--mx", e.clientX - r.left + "px");
				card.style.setProperty("--my", e.clientY - r.top + "px");
			});
		});
	}

	/* ---------- التهيئة ---------- */
	function init() {
		try { data = JSON.parse($("#docs-data").textContent); } catch (e) { /* بيانات غير متاحة */ }
		applyI18nAttributes();
		enhanceArticle();
		buildToc();
		setupReveal();
		setupCardGlow();
		onScroll();

		window.addEventListener("scroll", onScroll, { passive: true });
		window.addEventListener("resize", () => { if (activeHeadingId) setActive(activeHeadingId); }, { passive: true });

		$("#theme-btn")?.addEventListener("click", toggleTheme);
		$("#lang-btn")?.addEventListener("click", () => setLang(lang() === "ar" ? "en" : "ar"));
		$("#menu-btn")?.addEventListener("click", () => setNav(!document.body.classList.contains("nav-open")));
		$("#sidebar-backdrop")?.addEventListener("click", () => setNav(false));
		$("#to-top")?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" }));
		$$("[data-open-search]").forEach((b) => b.addEventListener("click", openSearch));

		document.addEventListener("click", (e) => {
			const copy = e.target.closest("[data-copy]");
			if (copy) copyCode(copy);
			const tocLink = e.target.closest("#toc a");
			if (tocLink) {
				e.preventDefault();
				const target = document.getElementById(tocLink.dataset.target);
				if (target) {
					target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
					history.replaceState(null, "", "#" + target.id);
					setActive(target.id);
				}
			}
		});

		$("#search-overlay")?.addEventListener("click", (e) => { if (e.target.id === "search-overlay") closeSearch(); });
		$("#search-input")?.addEventListener("input", () => { selected = 0; renderResults(); });

		document.addEventListener("keydown", (e) => {
			const overlay = $("#search-overlay");
			const open = overlay && !overlay.hidden;
			if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
				e.preventDefault();
				open ? closeSearch() : openSearch();
				return;
			}
			if (e.key === "/" && !open && !/input|textarea/i.test(document.activeElement.tagName)) {
				e.preventDefault();
				openSearch();
				return;
			}
			if (e.key === "Escape") { closeSearch(); setNav(false); return; }
			if (!open || !results.length) return;
			if (e.key === "ArrowDown") { e.preventDefault(); select((selected + 1) % results.length, true); }
			else if (e.key === "ArrowUp") { e.preventDefault(); select((selected - 1 + results.length) % results.length, true); }
			else if (e.key === "Enter") {
				e.preventDefault();
				const item = $$(".search-item")[selected];
				if (item) { closeSearch(); window.location.href = item.href; }
			}
		});
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
	else init();
})();
