"""
scripts/generate_mock_pdfs.py

Generates 4 realistic mock PDF documents for the AI Driver Chatbot POC:
  - data/insurance_card.pdf
  - data/driver_manual.pdf
  - data/maintenance_records.pdf
  - data/warranty_info.pdf

Run from the project root:
    python scripts/generate_mock_pdfs.py
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

OUTPUT_DIR = "data"

# ── Shared colors ─────────────────────────────────────────────────────────────
DARK_BLUE   = HexColor("#0D2B55")
MID_BLUE    = HexColor("#1A4A8A")
LIGHT_BLUE  = HexColor("#E8F0FB")
ACCENT_RED  = HexColor("#C0392B")
GREY        = HexColor("#555555")
LIGHT_GREY  = HexColor("#F5F5F5")
MID_GREY    = HexColor("#CCCCCC")
GREEN       = HexColor("#1E7A45")
ORANGE      = HexColor("#D35400")
WHITE       = colors.white
BLACK       = colors.black


# ══════════════════════════════════════════════════════════════════════════════
# 1. INSURANCE CARD
# ══════════════════════════════════════════════════════════════════════════════

def generate_insurance_card():
    path = os.path.join(OUTPUT_DIR, "insurance_card.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    # ── Front of card ─────────────────────────────────────────────────────────
    # Card background
    card_x, card_y = 0.75 * inch, h - 4.5 * inch
    card_w, card_h = 7.0 * inch, 3.5 * inch
    c.setFillColor(DARK_BLUE)
    c.roundRect(card_x, card_y, card_w, card_h, 12, fill=1, stroke=0)

    # Header stripe
    c.setFillColor(MID_BLUE)
    c.roundRect(card_x, card_y + card_h - 0.9 * inch, card_w, 0.9 * inch, 12, fill=1, stroke=0)
    c.rect(card_x, card_y + card_h - 0.9 * inch, card_w, 0.45 * inch, fill=1, stroke=0)

    # Insurer name
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(card_x + 0.25 * inch, card_y + card_h - 0.6 * inch, "SafeDrive Insurance Company")

    # "PROOF OF INSURANCE" label
    c.setFillColor(HexColor("#90CAF9"))
    c.setFont("Helvetica", 9)
    c.drawString(card_x + 0.25 * inch, card_y + card_h - 0.82 * inch, "PROOF OF MOTOR VEHICLE LIABILITY INSURANCE")

    # Two-column content
    left_x = card_x + 0.25 * inch
    right_x = card_x + 3.8 * inch
    row_h = 0.42 * inch
    top_y = card_y + card_h - 1.3 * inch

    def field(label, value, x, y, label_size=7.5, value_size=11):
        c.setFillColor(HexColor("#90CAF9"))
        c.setFont("Helvetica", label_size)
        c.drawString(x, y, label.upper())
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", value_size)
        c.drawString(x, y - 0.17 * inch, value)

    field("Named Insured",       "John Doe",                         left_x,  top_y)
    field("Policy Number",       "SDI-TX-2024-447192-JHN",           right_x, top_y)
    field("Vehicle",             "2021 Ford F-150 XLT",              left_x,  top_y - row_h)
    field("VIN",                 "1FTFW1E85MFA12345",                right_x, top_y - row_h)
    field("Policy Period",       "01/01/2026 – 12/31/2026",          left_x,  top_y - 2 * row_h)
    field("State",               "Texas",                            right_x, top_y - 2 * row_h)
    field("License Plate",       "TX-KLM-4892",                      left_x,  top_y - 3 * row_h)
    field("Agent Phone",         "1-800-723-3474",                   right_x, top_y - 3 * row_h)

    # Footer bar
    c.setFillColor(ACCENT_RED)
    c.rect(card_x, card_y, card_w, 0.32 * inch, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(card_x + 0.25 * inch, card_y + 0.1 * inch,
                 "In case of accident: Call 1-800-SAFEDRIVE (1-800-723-3748) • 24/7 Claims")

    # ── Coverage details below card ───────────────────────────────────────────
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(card_x, card_y - 0.45 * inch, "Coverage Summary")

    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawString(card_x, card_y - 0.65 * inch, "Policy SDI-TX-2024-447192-JHN  |  Effective January 1, 2026 – December 31, 2026")

    coverage_data = [
        ["Coverage Type",              "Limit / Deductible",         "Premium"],
        ["Bodily Injury Liability",    "$100,000 / $300,000",        "$42.10/mo"],
        ["Property Damage Liability",  "$50,000",                    "$18.40/mo"],
        ["Collision",                  "$500 deductible",            "$34.20/mo"],
        ["Comprehensive",              "$250 deductible",            "$12.80/mo"],
        ["Uninsured Motorist (BI)",    "$100,000 / $300,000",        "$8.90/mo"],
        ["Medical Payments",           "$5,000 per person",          "$4.20/mo"],
        ["Roadside Assistance",        "Tow (35 mi), battery, flat", "$2.10/mo"],
        ["Rental Reimbursement",       "$40/day, max $1,200",        "$4.70/mo"],
        ["TOTAL MONTHLY PREMIUM",      "",                           "$127.40/mo"],
    ]

    table = Table(coverage_data, colWidths=[2.8*inch, 2.4*inch, 1.6*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  9),
        ("BACKGROUND",   (0, -1), (-1, -1), MID_BLUE),
        ("TEXTCOLOR",    (0, -1), (-1, -1), WHITE),
        ("FONTNAME",     (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_GREY]),
        ("FONTSIZE",     (0, 1), (-1, -1), 8.5),
        ("GRID",         (0, 0), (-1, -1), 0.5, MID_GREY),
        ("ALIGN",        (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",        (2, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))

    table_y = card_y - 0.75 * inch
    table.wrapOn(c, 7 * inch, 10 * inch)
    table_w, table_h_val = table.wrap(7 * inch, 10 * inch)
    table.drawOn(c, card_x, table_y - table_h_val)

    # Discounts
    disc_y = table_y - table_h_val - 0.25 * inch
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(DARK_BLUE)
    c.drawString(card_x, disc_y, "Applied Discounts:")
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawString(card_x + 1.2 * inch, disc_y,
                 "Safe Driver (12%)   Multi-Policy (8%)   Paperless Billing (3%)")

    c.save()
    print(f"  ✅  {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. DRIVER'S MANUAL (maintenance-relevant excerpt)
# ══════════════════════════════════════════════════════════════════════════════

def generate_driver_manual():
    path = os.path.join(OUTPUT_DIR, "driver_manual.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=0.9*inch, rightMargin=0.9*inch,
                            topMargin=0.9*inch, bottomMargin=0.9*inch)
    styles = getSampleStyleSheet()

    H1 = ParagraphStyle("H1", parent=styles["Heading1"],
                        textColor=DARK_BLUE, fontSize=16, spaceBefore=18, spaceAfter=6)
    H2 = ParagraphStyle("H2", parent=styles["Heading2"],
                        textColor=MID_BLUE, fontSize=12, spaceBefore=12, spaceAfter=4)
    H3 = ParagraphStyle("H3", parent=styles["Heading3"],
                        textColor=DARK_BLUE, fontSize=10, spaceBefore=8, spaceAfter=3)
    BODY = ParagraphStyle("BODY", parent=styles["Normal"],
                          fontSize=9.5, leading=14, textColor=HexColor("#222222"))
    NOTE = ParagraphStyle("NOTE", parent=styles["Normal"],
                          fontSize=8.5, leading=12, textColor=GREY,
                          leftIndent=12, borderPad=4)
    COVER_TITLE = ParagraphStyle("COVER", parent=styles["Normal"],
                                 fontSize=28, textColor=WHITE, alignment=TA_CENTER,
                                 fontName="Helvetica-Bold")
    COVER_SUB = ParagraphStyle("COVERSUB", parent=styles["Normal"],
                               fontSize=13, textColor=HexColor("#B0C4DE"), alignment=TA_CENTER)

    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("2021 FORD F-150 XLT", COVER_TITLE))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Owner's Manual — Maintenance &amp; Reference Guide", COVER_SUB))
    story.append(Spacer(1, 0.15*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#4A7ABF")))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("VIN: 1FTFW1E85MFA12345", COVER_SUB))
    story.append(Paragraph("License Plate: TX-KLM-4892  |  Color: Carbonized Gray Metallic", COVER_SUB))
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph("John Doe  |  512-555-0147  |  john.doe@email.com", COVER_SUB))
    story.append(PageBreak())

    # ── Section 1: Vehicle Specifications ─────────────────────────────────────
    story.append(Paragraph("Section 1 — Vehicle Specifications", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))

    spec_data = [
        ["Specification", "Detail"],
        ["Year / Make / Model / Trim", "2021 Ford F-150 XLT"],
        ["Engine",                     "3.5L EcoBoost V6 Twin-Turbo"],
        ["Transmission",               "10-Speed Automatic (SelectShift)"],
        ["Drivetrain",                 "4WD — Electronic Shift-on-the-Fly"],
        ["Fuel Type",                  "Regular Unleaded (87 octane minimum)"],
        ["Fuel Tank Capacity",         "26.0 gallons"],
        ["Towing Capacity",            "12,700 lbs (properly equipped)"],
        ["Payload Capacity",           "1,985 lbs"],
        ["Curb Weight",                "4,705 lbs"],
        ["GVWR",                       "7,050 lbs"],
        ["Wheelbase",                  "145.4 in (SuperCrew, 5.5 ft bed)"],
    ]
    t = Table(spec_data, colWidths=[3.0*inch, 3.6*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",         (0, 0), (-1, -1), 0.5, MID_GREY),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("FONTNAME",     (0, 1), (0, -1),  "Helvetica-Bold"),
    ]))
    story.append(t)

    # ── Section 2: Fluids & Capacities ────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(Paragraph("Section 2 — Fluids &amp; Capacities", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))

    fluids_data = [
        ["Fluid",                   "Specification",                    "Capacity"],
        ["Engine Oil",              "Motorcraft SAE 5W-30 Full Synthetic","6.0 qts (with filter)"],
        ["Transmission Fluid",      "Motorcraft MERCON ULV",            "13.1 qts (total fill)"],
        ["Transfer Case Fluid",     "Motorcraft MERCON LV",             "2.0 pts"],
        ["Front Axle Fluid",        "Motorcraft SAE 80W-90 Premium",    "3.5 pts"],
        ["Rear Axle Fluid",         "Motorcraft SAE 75W-140 Synthetic", "4.0 pts"],
        ["Power Steering Fluid",    "Motorcraft MERCON LV (EPS)",       "N/A (Electric)"],
        ["Brake Fluid",             "Motorcraft DOT 4 LV",              "As needed"],
        ["Coolant / Antifreeze",    "Motorcraft Orange Coolant VC-3-B", "17.0 qts"],
        ["Windshield Washer Fluid", "Motorcraft Windshield Wash",       "As needed"],
    ]
    t2 = Table(fluids_data, colWidths=[2.0*inch, 2.5*inch, 2.0*inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",         (0, 0), (-1, -1), 0.5, MID_GREY),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("FONTNAME",     (0, 1), (0, -1),  "Helvetica-Bold"),
    ]))
    story.append(t2)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "⚠  Using non-recommended fluids may void applicable warranties. Always use Motorcraft-specified "
        "products or equivalents meeting Ford engineering specifications.", NOTE))

    story.append(PageBreak())

    # ── Section 3: Scheduled Maintenance ──────────────────────────────────────
    story.append(Paragraph("Section 3 — Scheduled Maintenance", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Follow the maintenance schedule below based on mileage OR time, whichever comes first. "
        "Severe-duty conditions (towing, off-road, dusty environments) require more frequent service — "
        "see intervals marked with an asterisk (*).", BODY))
    story.append(Spacer(1, 8))

    maint_data = [
        ["Service Item",            "Normal Interval",      "Severe Interval*",    "Estimated Cost"],
        ["Engine Oil & Filter",     "Every 5,000 mi / 6 mo","Every 3,000 mi / 3 mo","$65–$85"],
        ["Tire Rotation",           "Every 7,500 mi / 6 mo","Every 5,000 mi",       "$40–$55"],
        ["Brake Inspection",        "Every 15,000 mi / 1 yr","Every 7,500 mi",      "$Free–$75"],
        ["Cabin Air Filter",        "Every 15,000–25,000 mi","Every 12,000 mi",     "$20–$40"],
        ["Engine Air Filter",       "Every 30,000 mi",      "Every 15,000 mi",      "$25–$50"],
        ["Spark Plugs (Platinum)",  "Every 60,000 mi",      "Every 60,000 mi",      "$150–$200"],
        ["Transmission Fluid",      "Every 75,000 mi",      "Every 37,500 mi*",     "$150–$200"],
        ["Front/Rear Diff Fluid",   "Every 75,000 mi",      "Every 37,500 mi*",     "$80–$120 each"],
        ["4WD Transfer Case Fluid", "Every 75,000 mi",      "Every 37,500 mi*",     "$60–$90"],
        ["Coolant / Antifreeze",    "Every 100,000 mi / 10 yr","Every 50,000 mi",   "$100–$150"],
        ["Drive Belt Inspection",   "Every 60,000 mi",      "Every 30,000 mi",      "$Free–$20"],
        ["Fuel Filter (in-tank)",   "Every 60,000 mi",      "Every 30,000 mi",      "$80–$130"],
        ["Battery Test",            "Every 50,000 mi / 5 yr","Every 25,000 mi",     "$Free"],
    ]
    t3 = Table(maint_data, colWidths=[2.0*inch, 1.6*inch, 1.7*inch, 1.2*inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",         (0, 0), (-1, -1), 0.5, MID_GREY),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("FONTNAME",     (0, 1), (0, -1),  "Helvetica-Bold"),
        ("ALIGN",        (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t3)

    # ── Section 4: Tire Information ────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Section 4 — Tires &amp; Wheel Information", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))

    tire_data = [
        ["Specification",      "Front",                "Rear"],
        ["Tire Size",          "P275/65R18",           "P275/65R18"],
        ["Recommended PSI",    "35 PSI",               "35 PSI"],
        ["Load Rating",        "116T",                 "116T"],
        ["Wheel Size",         "18 x 7.5 in",          "18 x 7.5 in"],
        ["Spare Tire",         "Full-size spare, 35 PSI", "—"],
        ["Lug Nut Torque",     "150 ft-lbs",           "150 ft-lbs"],
        ["TPMS Warning",       "Below 28 PSI",         "Below 28 PSI"],
    ]
    t4 = Table(tire_data, colWidths=[2.6*inch, 2.0*inch, 2.0*inch])
    t4.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",         (0, 0), (-1, -1), 0.5, MID_GREY),
        ("ALIGN",        (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(t4)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Check tire pressure monthly and before long trips. Pressure should be checked when tires are cold "
        "(vehicle has not been driven more than 1 mile). The recommended pressure is printed on the "
        "door placard (driver's door jamb), not on the tire sidewall.", BODY))

    # ── Section 5: Texas Registration & Inspection ────────────────────────────
    story.append(Spacer(1, 10))
    story.append(Paragraph("Section 5 — Texas Registration &amp; Inspection Requirements", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Texas requires annual vehicle registration renewal. Before renewing your registration, your vehicle "
        "must pass a Texas state vehicle inspection at an authorized inspection station.", BODY))
    story.append(Spacer(1, 6))

    reg_data = [
        ["Requirement",              "Detail"],
        ["Registration Renewal",     "Annually — due by last day of expiry month"],
        ["Current Expiry",           "June 30, 2026 (TX-KLM-4892)"],
        ["State Inspection Required","Yes — must pass before registration renewal"],
        ["Inspection Validity",      "1 year"],
        ["Emissions Test",           "Required in Dallas, Harris, and Bexar counties"],
        ["Late Fee",                 "$20 penalty after grace period"],
        ["Online Renewal",           "Texas.gov/dmv — requires passing inspection first"],
    ]
    t5 = Table(reg_data, colWidths=[2.6*inch, 4.0*inch])
    t5.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",         (0, 0), (-1, -1), 0.5, MID_GREY),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("FONTNAME",     (0, 1), (0, -1),  "Helvetica-Bold"),
    ]))
    story.append(t5)

    # ── Section 6: Emergency Procedures ───────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Section 6 — Emergency Procedures", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))

    for title, body in [
        ("Flat Tire",
         "1. Pull safely off the road and turn on hazard lights.  "
         "2. Apply parking brake.  "
         "3. Retrieve full-size spare tire from beneath the truck bed (requires lug wrench and jack handle).  "
         "4. Loosen lug nuts BEFORE jacking (one-half turn only).  "
         "5. Position floor jack under the frame rail jack point closest to the flat tire.  "
         "6. Raise vehicle until flat tire clears the ground by 3 inches.  "
         "7. Remove lug nuts and flat tire; mount spare.  "
         "8. Torque lug nuts to 150 ft-lbs in star pattern.  "
         "9. Lower vehicle. Drive to a tire shop as soon as possible."),
        ("Dead Battery",
         "Roadside Assistance (SafeDrive): 1-800-723-3748 for a free battery jump (covered under policy).  "
         "If jump-starting yourself: Connect RED (+) to dead battery positive, RED (+) to good battery positive, "
         "BLACK (–) to good battery negative, BLACK (–) to unpainted metal ground on dead vehicle (NOT to dead battery). "
         "Start good vehicle, wait 2 minutes, then start dead vehicle."),
        ("Roadside Assistance Contacts",
         "SafeDrive 24/7 Roadside: 1-800-723-3748  |  "
         "Ford Roadside Assistance: 1-800-241-3673  |  "
         "Covered services: towing up to 35 miles, flat tire change, battery jump-start, "
         "fuel delivery (up to 2 gallons), lockout service."),
    ]:
        story.append(Spacer(1, 6))
        story.append(Paragraph(title, H2))
        story.append(Paragraph(body, BODY))

    def add_header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFillColor(DARK_BLUE)
        canvas_obj.rect(0, letter[1] - 0.45*inch, letter[0], 0.45*inch, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawString(0.9*inch, letter[1] - 0.3*inch, "2021 FORD F-150 XLT — Owner's Manual Excerpt")
        canvas_obj.drawRightString(letter[0] - 0.9*inch, letter[1] - 0.3*inch, "VIN: 1FTFW1E85MFA12345")
        canvas_obj.setFillColor(LIGHT_GREY)
        canvas_obj.rect(0, 0, letter[0], 0.35*inch, fill=1, stroke=0)
        canvas_obj.setFillColor(GREY)
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawString(0.9*inch, 0.12*inch, "For reference only. Consult a certified Ford dealer for complete information.")
        canvas_obj.drawRightString(letter[0] - 0.9*inch, 0.12*inch, f"Page {doc.page}")
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"  ✅  {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. MAINTENANCE RECORDS
# ══════════════════════════════════════════════════════════════════════════════

def generate_maintenance_records():
    path = os.path.join(OUTPUT_DIR, "maintenance_records.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.9*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    H1   = ParagraphStyle("H1",   parent=styles["Heading1"], textColor=DARK_BLUE,  fontSize=15, spaceBefore=14, spaceAfter=4)
    H2   = ParagraphStyle("H2",   parent=styles["Heading2"], textColor=MID_BLUE,   fontSize=11, spaceBefore=10, spaceAfter=3)
    BODY = ParagraphStyle("BODY", parent=styles["Normal"],   fontSize=9,   leading=13, textColor=HexColor("#222222"))
    SMALL= ParagraphStyle("SM",   parent=styles["Normal"],   fontSize=7.5, leading=11, textColor=GREY)

    story = []

    # Header block
    header_data = [[
        Paragraph("<b>VEHICLE SERVICE RECORD</b>", ParagraphStyle("hdr", fontSize=16, textColor=WHITE, fontName="Helvetica-Bold")),
        Paragraph("2021 Ford F-150 XLT<br/>"
                  "VIN: 1FTFW1E85MFA12345<br/>"
                  "Owner: John Doe  |  TX-KLM-4892",
                  ParagraphStyle("sub", fontSize=9, textColor=HexColor("#B0C4DE"), leading=14)),
    ]]
    ht = Table(header_data, colWidths=[3.2*inch, 3.8*inch])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK_BLUE),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("LEFTPADDING",(0,0),(-1,-1),14),
        ("LINEBELOW",  (0,0), (-1,-1), 3, ACCENT_RED),
    ]))
    story.append(ht)
    story.append(Spacer(1, 12))

    # ── Service History ────────────────────────────────────────────────────────
    story.append(Paragraph("Service History", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))

    history_data = [
        ["Date",        "Mileage",  "Service Performed",                     "Shop",                    "Cost",    "Notes"],
        ["11/12/2024",  "44,100",   "Oil & Filter Change\n5W-30 Full Synthetic Motorcraft",
                                                                              "Jiffy Lube #2847\nAustin, TX",
                                                                                                         "$74.99",  "Next oil due: 49,100 mi or May 2025"],
        ["07/20/2024",  "40,000",   "Tire Rotation & Balance\nAll 4 tires",  "Discount Tire #0341\nAustin, TX",
                                                                                                         "$49.99",  "Tread depth: 7/32\" all corners"],
        ["01/08/2024",  "35,000",   "Brake Inspection\nFront pads replaced (OEM)",
                                                                              "Ford of Austin\nAustin, TX","$189.00", "Rear brakes 65% remaining"],
        ["08/05/2023",  "28,500",   "Engine Air Filter\nMotocraft FA-1951",  "O'Reilly Auto Parts\nDIY", "$95.00",  "Cabin filter also inspected — OK"],
        ["02/18/2023",  "22,000",   "Multi-Point Inspection\nWiper blades replaced",
                                                                              "Ford of Austin\nAustin, TX","$45.00",  "All fluid levels topped off"],
        ["06/10/2022",  "15,300",   "Oil & Filter Change\nTire rotation performed",
                                                                              "Jiffy Lube #2847\nAustin, TX",
                                                                                                         "$118.99", ""],
        ["08/14/2021",  "50",       "New Vehicle PDI\nAll delivery checks",  "Ford of Austin\nAustin, TX","$0.00",   "Vehicle purchased 08/14/2021"],
    ]

    hist_table = Table(history_data, colWidths=[0.8*inch, 0.7*inch, 2.1*inch, 1.5*inch, 0.65*inch, 1.45*inch])
    hist_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  8.5),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0, 0), (-1, -1), 0.4, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (4, 0), (4, -1),  "RIGHT"),
    ]))
    story.append(hist_table)

    # ── Upcoming Maintenance ───────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(Paragraph("Upcoming Maintenance Schedule", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Based on current odometer reading of <b>47,250 miles</b>. Services listed in order of urgency.", BODY))
    story.append(Spacer(1, 8))

    upcoming_data = [
        ["Priority", "Service",                    "Due at",     "Miles Remaining", "Est. Cost",  "Status"],
        ["⚠  HIGH",  "Tire Rotation",              "47,500 mi",  "250 mi",          "~$50",       "DUE SOON"],
        ["⚠  HIGH",  "Oil & Filter Change\n5W-30 Synthetic",
                                                   "49,100 mi",  "1,850 mi",        "~$75",       "UPCOMING"],
        ["MEDIUM",   "Brake Inspection",           "50,000 mi",  "2,750 mi",        "~$75",       "UPCOMING"],
        ["MEDIUM",   "Cabin Air Filter",           "55,000 mi",  "7,750 mi",        "~$35",       "SCHEDULED"],
        ["LOW",      "Spark Plug Replacement\n(Platinum)",
                                                   "60,000 mi",  "12,750 mi",       "~$175",      "SCHEDULED"],
        ["LOW",      "Transmission Fluid",         "75,000 mi",  "27,750 mi",       "~$175",      "SCHEDULED"],
        ["LOW",      "Transfer Case Fluid",        "75,000 mi",  "27,750 mi",       "~$80",       "SCHEDULED"],
        ["LOW",      "Coolant / Antifreeze Flush", "100,000 mi", "52,750 mi",       "~$130",      "SCHEDULED"],
    ]

    up_table = Table(upcoming_data, colWidths=[0.7*inch, 1.7*inch, 0.85*inch, 1.1*inch, 0.75*inch, 0.95*inch])
    up_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),   DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),   WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),   "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1),  8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),  [WHITE, LIGHT_GREY]),
        ("BACKGROUND",    (0, 1), (-1, 2),   HexColor("#FFF3E0")),  # highlight urgent rows
        ("TEXTCOLOR",     (0, 1), (0, 2),    ORANGE),
        ("FONTNAME",      (0, 1), (0, 2),    "Helvetica-Bold"),
        ("TEXTCOLOR",     (5, 1), (5, 2),    ORANGE),
        ("FONTNAME",      (5, 1), (5, 2),    "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1),  0.4, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1),  5),
        ("BOTTOMPADDING", (0, 0), (-1, -1),  5),
        ("LEFTPADDING",   (0, 0), (-1, -1),  5),
        ("ALIGN",         (3, 0), (4, -1),   "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1),  "TOP"),
    ]))
    story.append(up_table)

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Total lifetime maintenance spend to date: $572.97  |  "
        "Average annual maintenance cost: $114.59  |  Next scheduled visit: Tire rotation at 47,500 mi", SMALL))

    def header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFillColor(DARK_BLUE)
        canvas_obj.rect(0, letter[1] - 0.4*inch, letter[0], 0.4*inch, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(0.75*inch, letter[1] - 0.27*inch, "VEHICLE SERVICE RECORD — 2021 Ford F-150 XLT")
        canvas_obj.drawRightString(letter[0] - 0.75*inch, letter[1] - 0.27*inch, "John Doe  |  TX-KLM-4892")
        canvas_obj.setFillColor(LIGHT_GREY)
        canvas_obj.rect(0, 0, letter[0], 0.3*inch, fill=1, stroke=0)
        canvas_obj.setFillColor(GREY)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawString(0.75*inch, 0.1*inch, "Confidential — For vehicle owner use only")
        canvas_obj.drawRightString(letter[0] - 0.75*inch, 0.1*inch, f"Page {doc.page}")
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"  ✅  {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. WARRANTY INFORMATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_warranty_info():
    path = os.path.join(OUTPUT_DIR, "warranty_info.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=0.85*inch, rightMargin=0.85*inch,
                            topMargin=0.9*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    H1   = ParagraphStyle("H1",   parent=styles["Heading1"], textColor=DARK_BLUE,  fontSize=14, spaceBefore=14, spaceAfter=4)
    H2   = ParagraphStyle("H2",   parent=styles["Heading2"], textColor=MID_BLUE,   fontSize=10, spaceBefore=8,  spaceAfter=3)
    BODY = ParagraphStyle("BODY", parent=styles["Normal"],   fontSize=9,   leading=13)
    SMALL= ParagraphStyle("SM",   parent=styles["Normal"],   fontSize=7.5, leading=11, textColor=GREY)

    story = []

    # Title block
    title_data = [[
        Paragraph("<b>FORD MOTOR COMPANY</b><br/>WARRANTY INFORMATION DOCUMENT",
                  ParagraphStyle("t", fontSize=15, textColor=WHITE, fontName="Helvetica-Bold", leading=20)),
        Paragraph("Owner: John Doe<br/>"
                  "Vehicle: 2021 Ford F-150 XLT<br/>"
                  "VIN: 1FTFW1E85MFA12345<br/>"
                  "Purchase Date: August 14, 2021",
                  ParagraphStyle("s", fontSize=9, textColor=HexColor("#B0C4DE"), leading=14)),
    ]]
    tt = Table(title_data, colWidths=[3.5*inch, 3.5*inch])
    tt.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), DARK_BLUE),
        ("TOPPADDING",   (0,0),(-1,-1), 14),
        ("BOTTOMPADDING",(0,0),(-1,-1), 14),
        ("LEFTPADDING",  (0,0),(-1,-1), 14),
        ("LINEBELOW",    (0,0),(-1,-1), 3, ACCENT_RED),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(tt)
    story.append(Spacer(1, 12))

    # ── Coverage Summary ───────────────────────────────────────────────────────
    story.append(Paragraph("Warranty Coverage Summary", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))

    warranty_data = [
        ["Warranty Type",           "Coverage",         "Expires (Date)",   "Expires (Miles)",  "Remaining Miles",  "Status"],
        ["Bumper-to-Bumper\n(New Vehicle Limited)",
                                    "3 years / 36,000 mi","Aug 14, 2024",   "36,000 mi",        "EXPIRED",          "EXPIRED"],
        ["Powertrain Limited",      "5 years / 60,000 mi","Aug 14, 2026",   "60,000 mi",        "~12,750 mi",       "ACTIVE"],
        ["Corrosion (Rust-Through)","5 years / Unlimited","Aug 14, 2026",   "Unlimited",        "—",                "ACTIVE"],
        ["Emissions (Federal)",     "8 years / 80,000 mi","Aug 14, 2029",   "80,000 mi",        "~32,750 mi",       "ACTIVE"],
        ["Safety Restraints",       "5 years / Unlimited","Aug 14, 2026",   "Unlimited",        "—",                "ACTIVE"],
        ["Ford Roadside Assistance","5 years / 60,000 mi","Aug 14, 2026",   "60,000 mi",        "~12,750 mi",       "ACTIVE"],
        ["Audio/Navigation (SYNC)", "3 years / 36,000 mi","Aug 14, 2024",   "36,000 mi",        "EXPIRED",          "EXPIRED"],
    ]

    wt = Table(warranty_data, colWidths=[1.5*inch, 1.3*inch, 1.0*inch, 1.0*inch, 1.1*inch, 0.8*inch])
    wt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),   DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),   WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),   "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1),  8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),  [WHITE, LIGHT_GREY]),
        # EXPIRED rows
        ("TEXTCOLOR",     (5, 1), (5, 1),    ACCENT_RED),
        ("FONTNAME",      (5, 1), (5, 1),    "Helvetica-Bold"),
        ("TEXTCOLOR",     (5, -1),(5, -1),   ACCENT_RED),
        ("FONTNAME",      (5, -1),(5, -1),   "Helvetica-Bold"),
        # ACTIVE rows
        ("TEXTCOLOR",     (5, 2), (5, 6),    GREEN),
        ("FONTNAME",      (5, 2), (5, 6),    "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1),  0.4, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1),  5),
        ("BOTTOMPADDING", (0, 0), (-1, -1),  5),
        ("LEFTPADDING",   (0, 0), (-1, -1),  5),
        ("ALIGN",         (2, 0), (-1, -1),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1),  "TOP"),
    ]))
    story.append(wt)

    # ── Powertrain Coverage Detail ─────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(Paragraph("Powertrain Limited Warranty — Coverage Detail", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The Powertrain Limited Warranty covers defects in factory-supplied materials or workmanship for "
        "the following components. Coverage expires August 14, 2026 OR 60,000 miles, whichever occurs first. "
        "<b>Current mileage: 47,250 — approximately 12,750 miles remaining under this warranty.</b>", BODY))
    story.append(Spacer(1, 8))

    pt_data = [
        ["Covered Component",       "Covered Parts",                                       "Covered?"],
        ["Engine",                  "Block, heads, all internally lubricated parts,\ncamshaft, crankshaft, timing chain/gears",
                                                                                            "YES"],
        ["Transmission (10-spd)",   "Case, all internal parts, torque converter",          "YES"],
        ["Transfer Case",           "Case, all internal parts",                             "YES"],
        ["Drive Axles",             "Front and rear axle assemblies, CV joints, U-joints", "YES"],
        ["Driveshaft",              "Front and rear driveshafts",                           "YES"],
        ["Seals & Gaskets",         "For all above-listed covered components",              "YES"],
        ["Engine Oil & Filter",     "Routine maintenance item",                             "NO"],
        ["Brake Pads & Rotors",     "Normal wear items",                                   "NO"],
        ["Tires",                   "Covered by separate tire manufacturer warranty",       "NO"],
        ["Clutch Assembly",         "Normal wear item (N/A — automatic transmission)",     "N/A"],
        ["Damage from misuse",      "Accidents, improper use, modifications",              "NO"],
    ]
    pt_table = Table(pt_data, colWidths=[1.7*inch, 3.9*inch, 0.75*inch])
    pt_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),   DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),   WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),   "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1),  8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),  [WHITE, LIGHT_GREY]),
        ("TEXTCOLOR",     (2, 1), (2, 6),    GREEN),
        ("FONTNAME",      (2, 1), (2, 6),    "Helvetica-Bold"),
        ("TEXTCOLOR",     (2, 7), (2, -1),   ACCENT_RED),
        ("FONTNAME",      (2, 7), (2, -1),   "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1),  0.4, MID_GREY),
        ("ALIGN",         (2, 0), (2, -1),   "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1),  5),
        ("BOTTOMPADDING", (0, 0), (-1, -1),  5),
        ("LEFTPADDING",   (0, 0), (-1, -1),  7),
        ("VALIGN",        (0, 0), (-1, -1),  "TOP"),
    ]))
    story.append(pt_table)

    # ── Warranty Conditions ────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(Paragraph("Warranty Conditions &amp; Requirements", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BLUE))
    story.append(Spacer(1, 6))

    conditions = [
        ("Maintain with Approved Fluids",
         "Engine oil must be Motorcraft SAE 5W-30 Full Synthetic or equivalent meeting Ford specification "
         "WSS-M2C946-B1. Using non-approved fluids may void powertrain warranty coverage."),
        ("Follow Maintenance Schedule",
         "Warranty does not cover failures caused by lack of maintenance. Keep all service records "
         "(receipts, invoices) as proof of maintenance compliance."),
        ("No Unauthorized Modifications",
         "Aftermarket modifications, tuning, or use of non-OEM parts that cause damage are not covered. "
         "Performance modifications void powertrain coverage."),
        ("How to File a Claim",
         "Contact any authorized Ford dealership. Bring this document and proof of maintenance records. "
         "Ford of Austin: 512-555-0200  |  Ford Customer Relationship Center: 1-800-392-3673"),
    ]
    for title, body in conditions:
        story.append(Paragraph(title, H2))
        story.append(Paragraph(body, BODY))
        story.append(Spacer(1, 4))

    def header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFillColor(DARK_BLUE)
        canvas_obj.rect(0, letter[1] - 0.4*inch, letter[0], 0.4*inch, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(0.85*inch, letter[1] - 0.27*inch, "FORD WARRANTY INFORMATION — 2021 F-150 XLT")
        canvas_obj.drawRightString(letter[0] - 0.85*inch, letter[1] - 0.27*inch, "VIN: 1FTFW1E85MFA12345")
        canvas_obj.setFillColor(LIGHT_GREY)
        canvas_obj.rect(0, 0, letter[0], 0.3*inch, fill=1, stroke=0)
        canvas_obj.setFillColor(GREY)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawString(0.85*inch, 0.1*inch, "This document is for reference only. Contact an authorized Ford dealer for official warranty service.")
        canvas_obj.drawRightString(letter[0] - 0.85*inch, 0.1*inch, f"Page {doc.page}")
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"  ✅  {path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nGenerating mock PDFs into ./{OUTPUT_DIR}/\n")
    generate_insurance_card()
    generate_driver_manual()
    generate_maintenance_records()
    generate_warranty_info()
    print("\nDone! All 4 PDFs generated.")
    print("Next step: upload to Azure Blob Storage.")
    print("  python scripts/upload_pdfs_to_azure.py")
