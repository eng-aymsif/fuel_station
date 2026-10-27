# Fuel Station Management System (نظام إدارة محطات الوقود)

> **Fuel Station Management System** is a comprehensive, enterprise-grade multi-station fuel operations and retail management application natively integrated with ERPNext (Stock, Accounts, Purchasing, Sales, Taxes, and Cash Custody). It covers underground tank monitoring, pump and nozzle dispensing, attendant shift management, touch POS, card settlements, fleet customer agreements, and automated reconciliations.
>
> **نظام إدارة محطات الوقود** هو تطبيق متكامل لإدارة محطة أو عدة محطات وقود مبني بالكامل على Frappe Framework ومترابط قياسياً مع ERPNext (المخزون، الحسابات، المشتريات، المبيعات، الضرائب، والعهد النقدية). يغطي النظام متابعة الخزانات الأرضية، عمليات الضخ والمسدسات، ورديات المحصلين، نقطة البيع السريعة POS، تسويات الشبكة والبطاقات، عقود وأساطيل العملاء، والمطابقات الآلية الدقيقة.

---

## Features / الميزات

### English

- **Multi-Station & Tank Operations** — Multi-station support, underground tank monitoring, dip calibration charts, water volume detection, and real-time stock balance.
- **Pump & Nozzle Management** — Flexible dispenser/nozzle mapping, mechanical & electronic continuous meter tracking, calibration loss logging, and attendant pump assignments.
- **Shift & Cash Custody Lifecycle** — Comprehensive shift workflow (Open, Handover, Close), cash box balances, denomination counts (multi-currency), safe vault drops, and cash variance tracking.
- **Dedicated Fuel Station POS** — Fast, touch-friendly POS interface for cashiers, quick fuel preset buttons, multi-payment support (Cash, Bank Card, Fleet Card, On-Account), and thermal receipts.
- **Fleet & Credit Customers** — Corporate fuel contracts, vehicle license plate validation, authorized driver tracking, RFID/Fuel card quotas, and automated batch invoicing.
- **Standard ERPNext Integration** — Automatic generation of Stock Entries (tank depletion), Sales Invoices, Purchase Receipts (tanker delivery receipts), and Payment Entries.
- **Card & Network Settlement** — Reconciliation of POS card payment batches, terminal transaction audits, bank commission tracking, and settlement discrepancy management.
- **Electronic Invoicing & Compliance** — Standard tax invoice format with ZATCA-compliant QR codes (TLV encoding), tamper-evident audit logging, and operations scoping.
- **20+ Analytical Reports & Dashboards** — Deep visibility into attendant productivity, daily fuel sales, tank reconciliations, discount analytics, meter discrepancies, and credit aging.
- **Bilingual Interface** — Complete native Arabic & English localization with proper RTL layout support.

### العربية

- **إدارة المحطات والخزانات المتعددة** — دعم إدارة شبكة محطات، مراقبة الخزانات الأرضية، جداول المعايرة، قياس منسوب المياه، ومطابقة الأرصدة المخزنية اللحظية.
- **إدارة المضخات والمسدسات** — ربط المسدسات بالخزانات والأصناف، تتبع العدادات الميكانيكية والإلكترونية، توثيق كميات المعايرة، وتكليف العمال على المضخات.
- **دورة حياة الورديات والعهد النقدية** — دورة كاملة للورديات (فتح، تسليم، إغلاق)، إدارة صناديق نقدية المحصلين، عد الفئات النقدية، التوريد لخزينة المحطة، وضبط الفروقات والعجز.
- **نقطة بيع وقود متخصصة (POS)** — واجهة سريعة ومتجاوبة مع الشاشات اللمسية، أزرار سريعة لمبالغ ولترات الوقود، تعدد طرق الدفع (نقدي، شبكة/بطاقة، آجل/أسطول)، وإيصالات حرارية.
- **عملاء الأسطول والشركات والآجل** — عقود توريد الوقود، حصر لوحات المركبات المعتمدة، إدارة السائقين، بطاقات الوقود وRFID، وأوامر الصرف مع فوترة دورية مجمعة.
- **تكامل قياسي مع ERPNext** — ربط تلقائي مع قيود وسندات المخزون (صرف الوقود من المستودعات)، فواتير المبيعات، إيصالات استلام الشراء (تفريغ الناقلات)، وسندات القبض.
- **تسوية مدفوعات الشبكة والبطاقات** — مطابقة تسويات أجهزة نقاط البيع البنكية (POS Terminals)، مراجعة العمليات، قيد عمولات البنوك آلياً، ومعالجة أي فروقات.
- **الفوترة الإلكترونية والامتثال** — فواتير ضريبية مبسطة وأساسية متوافقة مع متطلبات هيئة الزكاة والضريبة والجمارك (ZATCA QR Code TLV)، وسجل تدقيق للعمليات الحساسة.
- **أكثر من ٢٠ تقريراً ولوحة تحكم** — تقارير أداء المحصلين، مبيعات الوقود اليومية، مطابقة الخزانات، تحليل الخصومات، فروقات العدادات، وأعمار ديون العملاء.
- **واجهة ثنائية اللغة** — دعم كامل ومتقن للغتين العربية والإنجليزية مع اتجاه كتابة من اليمين إلى اليسار (RTL).

---

## Architecture / البنية

```text
fuel_station/
├── fuel_station/                      # Core app package / حزمة التطبيق الأساسية
│   ├── fuel_station/                  # App Module / وحدة محطات الوقود
│   │   ├── doctype/                   # DocTypes definition & controllers / أنواع المستندات
│   │   │   ├── fuel_station/          # Station master / المحطة الرئيسية
│   │   │   ├── fuel_tank/             # Fuel tank master / الخزانات الأرضية
│   │   │   ├── fuel_pump/             # Fuel pump & nozzle configuration / المضخات والمسدسات
│   │   │   ├── fuel_shift/            # Shift management / الورديات
│   │   │   ├── fuel_cash_box/         # Cashier box balance / صندوق النقدية
│   │   │   ├── fuel_station_safe/     # Station safe / الخزينة الرئيسية
│   │   │   ├── fuel_cash_custody/     # Cash custody transfers / العهد النقدية
│   │   │   ├── fuel_meter_reading/    # Meter logs / قراءات العدادات
│   │   │   ├── fuel_dispense_event/   # Dispense transactions / عمليات التعبئة
│   │   │   ├── fuel_customer_contract/# Fleet agreements / عقود عملاء الأسطول
│   │   │   ├── fuel_card/             # Fuel cards & RFID / بطاقات الوقود
│   │   │   ├── fuel_issue_order/      # Fuel issue vouchers / أوامر صرف الوقود
│   │   │   ├── fuel_delivery/         # Fuel tanker receiving / توريد وتفريغ الوقود
│   │   │   ├── fuel_pump_reconciliation/ # Pump meter audits / تسوية مبيعات المضخات
│   │   │   ├── fuel_tank_reconciliation/ # Tank physical audits / تسوية مخزون الخزانات
│   │   │   ├── card_settlement/       # Bank POS settlements / تسويات أجهزة الشبكة
│   │   │   └── ...                    # Additional DocTypes / مستندات داعمة
│   │   ├── report/                    # Analytical reports / التقارير التحليلية
│   │   ├── page/                      # Custom Desk pages (POS & Dashboard) / صفحات النظام
│   │   ├── print_format/              # Thermal & invoice formats / نماذج الطباعة
│   │   └── workspace/                 # Desk workspace shortcuts & charts / مساحة العمل
│   ├── customizations/                # Standard DocType customizations / التخصيصات
│   ├── overrides/                     # ERPNext class overrides / تجاوز فئات ERPNext
│   ├── services/                      # Business logic & settings engine / منطق الأعمال
│   ├── setup/                         # Auto setup, permissions & fixtures / التهيئة الآلية
│   ├── templates/                     # Website & Jinja documentation / قوالب التوثيق
│   ├── translations/                  # i18n translations (ar.csv) / ملفات التعريب
│   ├── www/                           # Portal & documentation routes / صفحات الويب والتوثيق
│   ├── hooks.py                       # Frappe configuration & triggers / خطافات النظام
│   └── boot.py                        # Boot session info extension / معلومات بدء الجلسة
├── license.txt                        # MIT Dual License (English & Arabic) / الترخيص
├── pyproject.toml                     # Python package metadata / إعدادات الحزمة
└── README.md                          # Project documentation / دليل المشروع
```

---

## Tech Stack / التقنيات

- **Backend:** Frappe Framework v15+ (Python 3.10+)
- **ERP Integration:** ERPNext v15+ (Stock, Accounts, Selling, Buying)
- **Frontend:** Frappe Desk, JavaScript (ES6+), HTML5 / CSS3 / SCSS
- **Database:** MariaDB / MySQL with transactional consistency
- **Invoicing & Compliance:** ZATCA QR Code (Base64 TLV Encoding)

---

## Key Doctypes / أنواع المستندات الرئيسية

### Infrastructure & Assets / البنية التحتية والمحطات
| DocType | Arabic / بالعربية | Description |
| --- | --- | --- |
| `Fuel Station` | محطة الوقود | Multi-station definition, location, default cost center, and warehouse linkages |
| `Fuel Tank` | خزان الوقود | Fuel storage tank master with capacity, current level, deadstock, and water dip monitoring |
| `Fuel Pump` | المضخة | Fuel dispenser unit holding one or more nozzles mapped to tanks and fuel items |
| `Fuel Station Safe` | خزينة المحطة | Main station safe for consolidating shift drops, banking deposits, and cash transfers |

### Shifts & Daily Operations / الورديات والعمليات اليومية
| DocType | Arabic / بالعربية | Description |
| --- | --- | --- |
| `Fuel Shift` | وردية المحطة | Full shift lifecycle including opening balances, attendant assignments, and closing totals |
| `Fuel Shift Type` | نوع الوردية | Morning, evening, and night shift schedule templates |
| `Fuel Pump Assignment` | تكليف المضخة | Assignment of an attendant to specific nozzles/pumps for a designated shift |
| `Fuel Meter Reading` | قراءة العداد | Mechanical and electronic start/end meter records per nozzle |
| `Fuel Dispense Event` | عملية التعبئة | Individual or batch fuel dispensing transaction linked to customers, vehicles, and tanks |
| `Pump Handover` | تسليم المضخة | Mid-shift or end-shift handover between station attendants |
| `Fuel Calibration Event` | معايرة العدادات | Official calibration test runs returned to tanks without triggering sales |

### Cash & Financial Custody / النقدية والعهد المالية
| DocType | Arabic / بالعربية | Description |
| --- | --- | --- |
| `Fuel Cash Box` | صندوق نقدية المحصل | Individual cashier cash box with tracking of collected cash, vouchers, and card slips |
| `Fuel Cash Custody` | العهدة النقدية | Custody movements and handover between shift supervisors and cashiers |
| `Fuel Denomination Count`| عد الفئات النقدية | Breakdown of physical cash counts by currency denomination notes and coins |
| `Cash Transfer` | تحويل نقدية | Movement of cash from cashier boxes into the main station safe or bank deposit |
| `Card Settlement` | تسوية البطاقات | Daily or shift settlement batch from bank POS payment terminals |
| `Fuel Pump Invoice Batch`| دفعة فواتير المضخات | Consolidated sales invoice generation from shift pump dispense transactions |

### Fleet & Corporate Accounts / الأسطول والشركات والآجل
| DocType | Arabic / بالعربية | Description |
| --- | --- | --- |
| `Fuel Customer Contract` | عقد عميل الوقود | Corporate credit agreement specifying fuel quotas, discounts, pricing, and payment terms |
| `Fuel Card` | بطاقة الوقود | RFID / NFC or numeric customer fuel card assigned to specific vehicles or accounts |
| `Fuel Issue Order` | أمر صرف وقود | Pre-authorized coupon or voucher authorizing fuel dispensing for a specific vehicle |
| `Customer Vehicle` | مركبة العميل | Plate number, model, fuel type restriction, and odometer tracking |
| `Customer Driver` | سائق العميل | Driver profiles authorized to receive fuel on behalf of contract customers |

### Reconciliations & Quality / التسويات والتدقيق
| DocType | Arabic / بالعربية | Description |
| --- | --- | --- |
| `Fuel Pump Reconciliation` | تسوية المضخات | Mathematical reconciliation between meter differences and recorded POS sales |
| `Fuel Tank Reconciliation` | تسوية الخزانات | Physical dip stick vs. book balance reconciliation to track gain/loss |
| `Fuel Delivery` | توريد وقود | Tanker offloading receiving document updating tank volume and Purchase Receipt |
| `Fuel Reconciliation Exception` | استثناء تسوية | Handling and management approval for unexplained fuel variance or losses |
| `Fuel Audit Log` | سجل التدقيق | Tamper-evident audit trail for meter resets, overrides, and critical changes |

---

## Analytical Reports / التقارير التحليلية

| Report Name / اسم التقرير | Type | Description / الوصف |
| --- | --- | --- |
| **Daily Fuel Sales** | Script Report | ملخص مبيعات الوقود اليومية موزعة حسب الأصناف، المحطات، وطرق الدفع |
| **Pump Sales Report** | Script Report | تفصيل مبيعات كل مضخة ومسدس باللترات والقيمة المالية |
| **Tank Stock Report** | Script Report | حركة مخزون الخزانات (رصيد افتتاحي، توريدات، مسحوبات، رصيد ختامي) |
| **Pump Reconciliation Report** | Script Report | مقارنة قراءات العدادات بالمبيعات المسجلة وكشف الفروقات |
| **Shift Closing Report** | Script Report | بيان إغلاق الوردية الشامل بالمبيعات والمتحصلات والعجز أو الفائض |
| **Cash Custody Report** | Script Report | تتبع العهد النقدية وحركات التسليم والاستلام بين المحصلين |
| **Cash Boxes & Safe Closing**| Script Report | مطابقة أرصدة صناديق المحصلين مع حركة الإيداع بالخزينة الرئيسية |
| **Card Settlement Reconciliation**| Script Report | مطابقة مدفوعات الشبكة المسجلة مع إشعارات تسوية ماكينات البنك |
| **Attendant Performance Report** | Script Report | تقرير إنتاجية وكفاءة عمال ومحصلي المحطة ومبيعات كل عامل |
| **Customer Fuel Consumption** | Script Report | استهلاك عملاء العقود والآجل مقسمين حسب الفترات والأصناف |
| **Vehicle Fuel Consumption** | Script Report | معدلات استهلاك مركبات الأسطول والمسافة المقطوعة (كم/لتر) |
| **Fuel Delivery Report** | Script Report | سجل تفريغ شحنات الوقود الواردة وفروقات درجة الحرارة والمعايرة |
| **Credit Aging Report** | Script Report | تقرير أعمار الديون لعملاء عقود الوقود والحدود الائتمانية |
| **Tax Sales Report** | Script Report | مبيعات الوقود الخاضعة للضريبة وقيمة ضريبة القيمة المضافة |
| **Electronic Invoice Status**| Script Report | تتبع حالة إرسال واعتماد الفواتير الإلكترونية والتوافق مع ZATCA |
| **Fuel Audit Trail Report** | Script Report | سجل الرقابة والتدقيق لكافة الإجراءات الإدارية والتعديلات الحساسة |
| **Period Closing Checklist** | Script Report | قائمة فحص ومراجعة المهام الإلزامية قبل الإقفال الدوري للمحطة |
| **Meter Reading Report** | Script Report | السجل التاريخي لقراءات العدادات وتتبع الزيادة التراكمية |
| **Discount Analysis Report** | Script Report | تحليل الخصومات الممنوحة للعملاء وأثرها المالي |
| **Fuel Dispense Report** | Script Report | التقرير التفصيلي لعمليات التعبئة الفردية الصادرة من المسدسات |

---

## Override Classes / التخصيصات

| Original ERPNext Class | Fuel Station Override Class |
| --- | --- |
| `Customer` | `fuel_station.overrides.customer.CustomCustomer` |
| `Sales Invoice` | `fuel_station.overrides.sales_invoice.CustomSalesInvoice` |
| `Stock Entry` | `fuel_station.overrides.stock_entry.CustomStockEntry` |
| `Payment Entry` | `fuel_station.overrides.payment_entry.CustomPaymentEntry` |
| `Purchase Receipt` | `fuel_station.overrides.purchase_receipt.CustomPurchaseReceipt` |

---

## Installation / التثبيت

### Prerequisites / المتطلبات الأساسية

- Frappe Bench (v15+)
- ERPNext (v15+)
- Python 3.10+
- MariaDB 10.6+

### Setup / الإعداد

```bash
# Get the app / تنزيل التطبيق
bench get-app https://github.com/eng-aymsif/fuel_station

# Install onto your site / تثبيت التطبيق على الموقع
bench --site your-site.local install-app fuel_station

# Run database migrations / ترحيل الجداول والحقول المخصصة
bench --site your-site.local migrate

# Build frontend bundles / بناء ملفات الواجهة
bench build --app fuel_station
```

---

## Development Workflow / سير العمل التطويري

After modifying files, execute the corresponding command: / بعد تعديل الملفات، شغّل الأوامر المناسبة:

1. **Python files / ملفات بايثون** — `bench restart`
2. **DocType / JSON files / ملفات المستندات** — `bench --site <site> migrate`
3. **Frontend JS/SCSS / ملفات الواجهة** — `bench build --app fuel_station`
4. **Translations / الترجمة** — `bench --site <site> clear-cache`
5. **Fixtures & Custom Fields / الحقول والتخصيصات** — `bench --site <site> export-fixtures`

---

## Electronic Invoicing (ZATCA) / الفوترة الإلكترونية

The app comes out of the box with built-in Jinja methods supporting ZATCA electronic invoice requirements:
- **Seller Name**
- **Tax Identification Number (VAT Registration Number)**
- **Timestamp (ISO 8601 UTC)**
- **Invoice Total (With VAT)**
- **VAT Amount**
- **Base64 TLV Encoded QR Code**

Available via standard print formats:
- `fuel_standard_tax_invoice`
- `fuel_pos_thermal_receipt`
- `fuel_dispense_thermal_receipt`

---

## Testing / الاختبارات

```bash
# Run all fuel_station test suites / تشغيل جميع اختبارات التطبيق
bench --site <site> run-tests --app fuel_station

# Run tests with failfast / تشغيل مع التوقف عند أول خطأ
bench --site <site> run-tests --app fuel_station --failfast
```

---

## License / الترخيص

This project is licensed under the **MIT License**. See [license.txt](license.txt) for the complete dual-language text (English & Arabic).

هذا المشروع مرخص بموجب **رخصة MIT**. راجع ملف [license.txt](license.txt) للاطلاع على نص الرخصة باللغتين العربية والإنجليزية.

---

## Contact / التواصل

- **Project / المشروع:** Fuel Station Management System
- **Description / الوصف:** ERPNext Standard Fuel Station Management System
- **Developer / المطور:** Ayman Mohammed Saif Al-Maqtari — أيمن محمد سيف المقطري
- **Facebook / فيسبوك:** [أيمن محمد سيف المقطري][facebook]
- **WhatsApp / واتساب:** [‎+967 777 609 160‎][whatsapp]

[facebook]: https://www.facebook.com/aymansifq/
[whatsapp]: https://wa.me/967777609160
