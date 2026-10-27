"""محرك دليل المستخدم لمحطة الوقود (Fuel Station).

- دليل المستخدم (/docs): شرح تشغيلي مفصل للعامل والمشرف والمحاسب والمدير.

المحتوى HTML ثابت بلغتين في fuel_station/templates/docs/guide/{ar,en}/<slug>.html.
اللغة الافتراضية من إعدادات النظام، ويغيّرها الزائر بزر التبديل (كوكي fuel_station_docs_lang).
"""

import os
import re
from urllib.parse import quote

import frappe
from frappe.utils import cint

LANGS = ("ar", "en")
LANG_COOKIE = "fuel_station_docs_lang"


def _nav(slug, icon, color, color2, title_ar, title_en, desc_ar, desc_en):
	return {
		"slug": slug,
		"icon": icon,
		"color": color,
		"color2": color2,
		"title": {"ar": title_ar, "en": title_en},
		"description": {"ar": desc_ar, "en": desc_en},
	}


# ترتيب القراءة المنطقي لدليل المستخدم
GUIDE_NAV = [
	_nav(
		"getting-started",
		"sparkles",
		"#ea580c",
		"#fb923c",
		"البدء السريع",
		"Getting Started",
		"المفاهيم الأساسية لمحطة الوقود، دورة التعبئة والفوترة، وتشغيل النظام لأول مرة.",
		"Core fuel station concepts, dispense-to-invoice lifecycle, and first-time setup.",
	),
	_nav(
		"setup",
		"settings",
		"#0891b2",
		"#22d3ee",
		"التهيئة والإعدادات التشغيلية",
		"Setup & Operational Settings",
		"تهيئة حسابات الشركة، إعدادات Fuel Operations Settings، وسيناريوهات الفوترة والمخزون.",
		"Company COA setup, Fuel Operations Settings, and invoicing/stock policies.",
	),
	_nav(
		"roles",
		"users",
		"#db2777",
		"#f472b6",
		"المستخدمون والأدوار والصلاحيات",
		"Users, Roles & Permissions",
		"أدوار النظام السبعة من عامل المضخة حتى مدير العمليات، وحدود وفصل المهام.",
		"The seven station roles from attendant to operations manager and segregation of duties.",
	),
	_nav(
		"shifts-and-safes",
		"clock",
		"#7c3aed",
		"#c084fc",
		"إدارة الورديات والصناديق والخزائن",
		"Shifts, Cash Boxes & Safes",
		"فتح الوردية، تكليف المضخات، تسليم واستلام العامل، عد النقد بالفئات، وخزينة المحطة.",
		"Opening shifts, pump assignment, worker handovers, cash denominations, and station safes.",
	),
	_nav(
		"meters-and-dispense",
		"compass",
		"#2563eb",
		"#60a5fa",
		"العدادات وعمليات التعبئة",
		"Meters & Dispense Events",
		"القراءات الافتتاحية والختامية، تسجيل Fuel Dispense Event، واستنتاج الكمية النقدية.",
		"Opening/closing meter readings, Fuel Dispense Events, and cash residual deduction.",
	),
	_nav(
		"customers-and-fleet",
		"idcard",
		"#059669",
		"#34d399",
		"العملاء وإدارة الأساطيل والائتمان",
		"Customers, Fleets & Credit Limits",
		"المركبات، السائقين، عقود العملاء، فحص الرصيد الائتماني الحقيقي، وسياسات المنع والاعتماد.",
		"Vehicles, drivers, customer contracts, true credit limit checks, and approval policies.",
	),
	_nav(
		"issue-orders-and-internal",
		"ticket",
		"#d97706",
		"#fde047",
		"أوامر الصرف والاستهلاك الداخلي",
		"Issue Orders & Internal Consumption",
		"أوامر الصرف Fuel Issue Order، تفويضات الـ QR، وصرف الوقود الداخلي بسيارات وأقسام الشركة.",
		"Fuel Issue Orders, QR authorizations, and internal stock consumption entries.",
	),
	_nav(
		"invoicing-and-taxes",
		"coins",
		"#10b981",
		"#6ee7b7",
		"المبيعات والفوترة والضرائب",
		"Sales, Invoicing & Taxes",
		"الفواتير النقدية والآجلة والبطاقات، الأسعار الشاملة وغير الشاملة، وقوالب الضرائب القياسية.",
		"Cash, credit, card invoices, inclusive/exclusive pricing, and ERPNext tax templates.",
	),
	_nav(
		"tanks-and-procurement",
		"database",
		"#0284c7",
		"#38bdf8",
		"الخزانات والتوريدات والمخزون",
		"Tanks, Deliveries & Stock",
		"خزانات الوقود، استلام توريدات الوقود Fuel Delivery، وربطها بـ Purchase Receipt ومعايرة الخزانات.",
		"Fuel tanks, Fuel Delivery receiving, Purchase Receipts, calibration, and stock reconciliations.",
	),
	_nav(
		"reconciliation-and-reports",
		"chart",
		"#9333ea",
		"#e879f9",
		"التسوية والمطابقة والتقارير",
		"Reconciliation & Reports",
		"تسوية المضخة، معالجة الفروقات والاستثناءات، وكشوفات المبيعات والمخزون وصناديق النقد.",
		"Pump reconciliations, exceptions, sales registers, stock balance, and cash reports.",
	),
	_nav(
		"returns-and-adjustments",
		"undo",
		"#dc2626",
		"#fb7185",
		"المرتجعات والإشعارات الدائنة",
		"Returns & Credit Notes",
		"معالجة مرتجع المبيعات، الإشعارات الدائنة والمدينة، واسترداد المدفوعات دون حذف المستندات.",
		"Sales returns, credit and debit notes, and payment refunds without deleting records.",
	),
	_nav(
		"faq",
		"help",
		"#65a30d",
		"#a3e635",
		"أسئلة شائعة وحلول",
		"FAQ & Troubleshooting",
		"إرشادات التعامل مع فروقات العدادات، تعليق الفواتير، وفك تعارض الورديات.",
		"Handling meter variances, blocked sales, conflicting shifts, and best practices.",
	),
]


def _t(ar, en):
	return {"ar": ar, "en": en}


UI = {
	"brand": _t("محطة الوقود", "Fuel Station"),
	"overview": _t("نظرة عامة", "Overview"),
	"guides": _t("الأدلة", "Guides"),
	"search": _t("ابحث في الوثائق…", "Search the docs…"),
	"search_short": _t("بحث", "Search"),
	"no_results": _t("لا توجد نتائج مطابقة", "No matching results"),
	"search_hint": _t("اكتب كلمة للبحث في كل الأقسام", "Type a word to search every section"),
	"loading": _t("جارٍ التحميل…", "Loading…"),
	"on_this_page": _t("في هذه الصفحة", "On this page"),
	"prev": _t("السابق", "Previous"),
	"next": _t("التالي", "Next"),
	"copy": _t("نسخ", "Copy"),
	"copied": _t("تم النسخ", "Copied"),
	"sections": _t("قسماً", "sections"),
	"min_read": _t("دقيقة قراءة", "min read"),
	"updated": _t("آخر تحديث", "Last updated"),
	"toggle_theme": _t("تبديل المظهر", "Toggle theme"),
	"toggle_lang": _t("English", "العربية"),
	"toggle_lang_label": _t("التبديل إلى الإنجليزية", "Switch to Arabic"),
	"menu": _t("القائمة", "Menu"),
	"back_top": _t("إلى الأعلى", "Back to top"),
	"to_navigate": _t("للتنقل", "to navigate"),
	"to_open": _t("للفتح", "to open"),
	"to_close": _t("للإغلاق", "to close"),
	"start_reading": _t("ابدأ القراءة", "Start reading"),
	"stat_guides": _t("أدلة", "Guides"),
	"stat_sections": _t("قسماً موثقاً", "Documented sections"),
	"stat_tables": _t("جدولاً مرجعياً", "Reference tables"),
	"stat_langs": _t("لغتان", "Languages"),
	"explore": _t("استكشف أدلة النظام", "Explore System Guides"),
	"read_guide": _t("اقرأ الدليل", "Read guide"),
	"search_tip": _t("اضغط Ctrl + K للبحث السريع في كل الوثائق", "Press Ctrl + K to quickly search all docs"),
	"skip": _t("تخطَّ إلى المحتوى", "Skip to content"),
	"go_desk": _t("الذهاب إلى النظام", "Go to Desk"),
	"go_login": _t("تسجيل الدخول", "Go to Login"),
	# المشهد البصري في الصفحة الرئيسية
	"mock_dispense": _t("حدث تعبئة", "Dispense Event"),
	"mock_pump": _t("المضخة", "Pump"),
	"mock_status": _t("الحالة", "Status"),
	"mock_invoiced": _t("مفوتر", "Invoiced"),
	"mock_qty": _t("الكمية", "Quantity"),
	"mock_invoice": _t("فاتورة وقود", "Fuel Sales Invoice"),
	"mock_paid": _t("مسدد بالكامل", "Paid"),
	"mock_tank": _t("مخزون الخزانات", "Tank Stock Status"),
}

SITES = {
	"guide": {
		"key": "guide",
		"base": "/docs",
		"nav": GUIDE_NAV,
		"ui": {
			"site": _t("دليل محطة الوقود", "Fuel Station Guide"),
			"docs": _t("دليل المستخدم", "User Guide"),
			"hero_badge": _t("الدليل التشغيلي الرسمي لنظام محطة الوقود", "The official Fuel Station user guide"),
			"hero_title_1": _t("أدِر محطات الوقود والعدادات", "Operate your fuel stations & pumps"),
			"hero_title_2": _t("بدقة وأمان مالي متكامل", "with complete precision & ledger integrity"),
			"hero_sub": _t(
				"شرح شامل ومفصل لكل خطوة وعملية في نظام محطة الوقود: من فتح الوردية وقراءات العدادات، إلى مبيعات الأساطيل والبطاقات، وتسوية الصناديق والخزائن والتوريدات المخزنية.",
				"A comprehensive walkthrough of every operation in Fuel Station: from shift opening and meter readings to fleet sales, cash box handovers, safe closings, and tank reconciliations.",
			),
			"explore_sub": _t(
				"اثنا عشر دليلاً عملياً تغطي دورة تشغيل المحطة من البدء السريع حتى التسوية والتقارير.",
				"Twelve practical guides covering the full station operational cycle from getting started to reconciliations.",
			),
			"path_title": _t("دورة العمل في محطة الوقود", "Station Operational Flow"),
			"path_sub": _t(
				"خمس مراحل تشغيلية تضمن مطابقة كل لتر وقود مع الإيراد وحركة المخزون.",
				"Five operational steps ensuring every dispensed liter matches ledger revenue and stock balance.",
			),
			"flow_1": _t("الوردية والتكليف", "Shift & Assignment"),
			"flow_1_sub": _t("فتح الوردية وقراءة البداية", "Shift open & opening meter"),
			"flow_2": _t("التعبئة والتصنيف", "Dispense & Classify"),
			"flow_2_sub": _t("نقدي، بطاقات، وأساطيل", "Cash, card & fleet credit"),
			"flow_3": _t("إغلاق العدادات", "Closing Meters"),
			"flow_3_sub": _t("قراءة الختام واستنتاج النقد", "Closing reading & residual"),
			"flow_4": _t("الفوترة والترحيل", "Invoicing & Stock"),
			"flow_4_sub": _t("فواتير وقيود آلية معتمدة", "Automated invoices & GL/Stock"),
			"flow_5": _t("التسوية والصناديق", "Safe & Reconciliation"),
			"flow_5_sub": _t("عد الفئات وترحيل الخزينة", "Denominations & safe balance"),
			"mock_pill": _t("دليل المستخدم", "User Guide"),
			"footer": _t("نظام محطة الوقود القياسي · دليل المستخدم", "Fuel Station Management System · User Guide"),
		},
		"flow": [
			("clock", "#ea580c", "flow_1"),
			("compass", "#0891b2", "flow_2"),
			("ticket", "#7c3aed", "flow_3"),
			("coins", "#059669", "flow_4"),
			("chart", "#db2777", "flow_5"),
		],
	},
}


def can_access(site_key="guide"):
	return site_key == "guide"


def check_access(site_key="guide"):
	if not can_access(site_key):
		raise frappe.PermissionError


def get_lang():
	# الكوكي أولاً ثم لغة المستخدم/النظام
	cookie = frappe.request.cookies.get(LANG_COOKIE) if getattr(frappe, "request", None) else None
	if cookie in LANGS:
		return cookie
	sys_lang = frappe.local.lang or "ar"
	return "ar" if sys_lang.startswith("ar") else "en"


def read_content(site_key, slug, lang):
	path = os.path.join(frappe.get_app_path("fuel_station", "templates", "docs"), site_key, lang, f"{slug}.html")
	if not os.path.exists(path):
		return f"<div class='alert alert-warning'>Documentation page {slug} ({lang}) is under preparation.</div>"
	with open(path, encoding="utf-8") as f:
		return f.read()


_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r'<h([234]) id="([^"]+)">(.*?)</h\1>', re.S)


def _text(html):
	text = _TAG_RE.sub(" ", html)
	text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
	return re.sub(r"\s+", " ", text).strip()


def _heading_text(inner):
	inner = re.sub(r'<a class="h-anchor".*?</a>', "", inner)
	inner = re.sub(r'<span class="h-dates">.*?</span></span>', "", inner, flags=re.S)
	return _text(inner)


def get_doc_stats(site_key, slug, lang="ar"):
	html = read_content(site_key, slug, lang)
	words = len(_text(html).split())
	return {
		"sections": max(1, len(_HEADING_RE.findall(html))),
		"tables": html.count("<table>"),
		"minutes": max(1, round(words / 180)),
		"updated": "2026-10-26",
	}


def _asset_version():
	folder = frappe.get_app_path("fuel_station", "public", "docs")
	try:
		return int(max(os.path.getmtime(os.path.join(folder, f)) for f in ("docs.css", "docs.js")))
	except Exception:
		return 1


def base_context(context, site_key, page):
	check_access(site_key)
	site = SITES[site_key]
	lang = get_lang()
	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.lang = lang
	context.dir = "rtl" if lang == "ar" else "ltr"
	context.site = site
	context.ui = {**UI, **site["ui"]}
	context.docs_nav = site["nav"]
	context.page = page
	context.asset_v = _asset_version()
	context.search_url = f"/api/method/fuel_station.www.docs_utils.get_search_index?site={site_key}"
	context.is_logged_in = frappe.session.user != "Guest"
	path = frappe.request.path if getattr(frappe, "request", None) else site["base"]
	context.login_url = "/login?redirect-to=" + quote(path)
	return lang


def get_doc_context(site_key, slug, context):
	nav_by_slug = {d["slug"]: d for d in SITES[site_key]["nav"]}
	if slug not in nav_by_slug:
		raise frappe.PageDoesNotExistError
	lang = base_context(context, site_key, slug)
	nav = nav_by_slug[slug]
	docs_nav = SITES[site_key]["nav"]
	idx = docs_nav.index(nav)

	context.doc = nav
	context.doc_content = {code: read_content(site_key, slug, code) for code in LANGS}
	context.doc_stats = get_doc_stats(site_key, slug, lang)
	context.prev_doc = docs_nav[idx - 1] if idx > 0 else None
	context.next_doc = docs_nav[idx + 1] if idx < len(docs_nav) - 1 else None
	context.titles = {code: f"{nav['title'][code]} — {context.ui['site'][code]}" for code in LANGS}
	context.title = context.titles[lang]


def get_landing_context(site_key, context):
	lang = base_context(context, site_key, "overview")
	stats = {d["slug"]: get_doc_stats(site_key, d["slug"], lang) for d in context.docs_nav}
	context.doc_stats = stats
	context.totals = {
		"guides": len(context.docs_nav),
		"sections": sum(s["sections"] for s in stats.values()),
		"tables": sum(s["tables"] for s in stats.values()),
	}
	context.titles = {code: f"{context.ui['docs'][code]} — {context.ui['site'][code]}" for code in LANGS}
	context.title = context.titles[lang]


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_search_index(site="guide"):
	"""فهرس بحث لكل الأقسام باللغتين، يُحمَّل عند أول فتح لنافذة البحث."""
	if site not in SITES:
		frappe.throw("Invalid site", frappe.ValidationError)
	if not can_access(site):
		raise frappe.PermissionError
	index = {code: [] for code in LANGS}
	for nav in SITES[site]["nav"]:
		for code in LANGS:
			html = read_content(site, nav["slug"], code)
			matches = list(_HEADING_RE.finditer(html))
			for i, m in enumerate(matches):
				end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
				body = _text(html[m.end() : end])
				index[code].append(
					{
						"page": nav["slug"],
						"title": nav["title"][code],
						"heading": _heading_text(m.group(3)),
						"id": m.group(2),
						"text": body[:600],
					}
				)
	return index

