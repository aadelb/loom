"""UAE/Dubai legal compliance and regulatory intelligence tools.

Tools for UAE Labor Law, Trade Licenses, Food Safety, Visas, Commercial Law,
Customs, RERA (Dubai Real Estate), and Tax Compliance with real legal references.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.llm_client import query_llm
except ImportError:
    query_llm = None

logger = logging.getLogger("loom.tools.legal.uae_legal")


# =============================================================================
# UAE LABOR LAW DATA (Federal Decree-Law No. 33/2021)
# =============================================================================

UAE_LABOR_LAW_TOPICS = {
    "general": {
        "legal_reference": "Federal Decree-Law No. 33/2021",
        "key_articles": [
            {
                "article": 1,
                "title": "Scope and Definition",
                "summary": "Applies to all workers in UAE (citizens and expatriates) in private sector",
            },
            {
                "article": 4,
                "title": "Definitions",
                "summary": "Defines employer, worker, wages, work, employment contract",
            },
            {
                "article": 30,
                "title": "Wages",
                "summary": "No statutory minimum for private sector expatriates. Ministerial Decree No. 43/2022 set AED 3,000/month for skilled workers in some categories. Emirati minimum: AED 6,000/month (2026 guidance).",
            },
        ],
        "overview": "UAE Federal Labor Law governs employment relationships, minimum wage, working hours, leave, health & safety",
    },
    "termination": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Articles 120-136",
        "key_provisions": [
            {
                "type": "Without Cause",
                "notice_period": "Minimum 30 days, maximum 90 days as agreed in contract (Article 43)",
                "compensation": "End-of-service gratuity + accrued leave",
                "details": "Either party can terminate without cause with notice",
            },
            {
                "type": "For Cause (Employer)",
                "notice_period": "Immediate",
                "compensation": "No gratuity if terminated for gross misconduct",
                "details": "Gross negligence, theft, fighting, breach of contract, unauthorized leave >30 days",
            },
            {
                "type": "For Cause (Employee)",
                "notice_period": "Immediate",
                "compensation": "Full gratuity + unpaid wages",
                "details": "Employer withholding wages, unsafe conditions, forced labor, discrimination",
            },
        ],
        "end_of_service_gratuity": {
            "rate": "21 days salary per year of service (first 5 years), 30 days per year (6+ years)",
            "max_period": "Not less than 2 years",
            "calculation": "Based on last basic salary at termination",
        },
    },
    "salary": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Articles 30-64",
        "minimum_wage": "No statutory minimum for private sector expatriates. Ministerial Decree No. 43/2022 set AED 3,000/month for skilled workers in some categories. Emirati minimum: AED 6,000/month (2026 guidance).",
        "wage_components": [
            "Basic salary (minimum wage floor)",
            "Housing allowance",
            "Transportation allowance",
            "Cost of living allowance",
            "Other contractual allowances",
        ],
        "payment_rules": {
            "frequency": "Minimum monthly, can be weekly/bi-weekly",
            "method": "Bank transfer (mandatory since 2009)",
            "currency": "UAE Dirhams (AED)",
            "deductions": "Can only deduct valid items (tax, insurance, court orders, loan repayment)",
        },
    },
    "leave": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Articles 78-98",
        "annual_leave": {
            "days": "30 days minimum (can be negotiated higher)",
            "accrual": "2.5 days per month of service",
            "carry_over": "Max 10 days can carry to next year (or pay)",
            "payment": "Paid at regular wage if not taken",
            "notice": "Employer notifies dates, or mutual agreement",
        },
        "sick_leave": {
            "days": "90 calendar days per year (Article 31): first 15 days full pay, next 30 days half pay, remaining 45 days unpaid",
            "rules": "Medical certificate required after 3 consecutive days",
            "emergency": "Up to 5 days per year without salary for personal reasons",
        },
        "maternity_leave": {
            "duration": "60 calendar days: 45 days full pay + 15 days half pay (Article 30)",
            "paid": "45 days at 100% salary, 15 days at 50% salary",
            "breastfeeding": "1 hour daily for 1 year after return",
            "reference": "Article 30",
        },
        "public_holidays": {
            "islamic": "Eid Al-Fitr (3 days), Eid Al-Adha (4 days), Islamic New Year, Prophet's Birthday",
            "civil": "UAE National Day (2 days: Nov 30-Dec 1)",
            "total": "~13 days public holidays annually",
        },
    },
    "gratuity": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Articles 131-136",
        "calculation": {
            "less_than_1_year": "Not entitled",
            "1_to_5_years": "21 days basic salary per year",
            "more_than_5_years": "30 days basic salary per year",
        },
        "payment_timing": "Due within 30 days of termination",
        "no_gratuity_if": [
            "Terminated for gross misconduct (theft, fighting, breach)",
            "Resigned without notice during probation",
            "Retired voluntarily before minimum service",
        ],
    },
    "visa_cancellation": {
        "legal_reference": "Federal Decree-Law No. 33/2021 + Cabinet Decision No. 65/2022 (reforms)",
        "process": "Employer can cancel visa if contract ends or without cause",
        "notice": "30 days notice to employee",
        "grace_period": "30-60 days to find new job (depends on case)",
        "new_rules_2022": [
            "Employee can cancel own visa without employer permission",
            "Transfer to new employer without cancellation fee",
            "Golden Visa holders get special protections",
        ],
    },
    "part_time": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Article 110",
        "definition": "Work <30 hours per week or <120 hours per month",
        "benefits": "Entitled to leave, gratuity, health insurance (proportional)",
        "contract": "Must specify part-time hours clearly",
        "restrictions": "Cannot work part-time for 2+ employers simultaneously",
    },
    "probation": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Article 72",
        "duration": "Maximum 6 months. Article 9 prohibits extending beyond 6 months.",
        "termination": "Either party can terminate without notice during probation. During probation: 14 days notice required.",
        "gratuity": "Not entitled to gratuity if terminated during probation",
        "notice": "During probation: 14 days notice required.",
    },
    "discrimination": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Article 10",
        "prohibited": [
            "Discrimination by nationality, gender, religion, disability",
            "Forced labor or child labor",
            "Sexual harassment or abuse",
        ],
        "remedy": "File complaint with Ministry of Human Resources & Emiratization (MoHRE)",
        "penalties": "Fines AED 5,000-100,000 + compensation to worker",
    },
    "work_hours": {
        "legal_reference": "Federal Decree-Law No. 33/2021, Articles 73-77",
        "standard": "Max 48 hours per week (8 hours per day)",
        "flexible": "Can negotiate longer hours with extra pay",
        "ramadan": "Reduced by 2 hours during Ramadan",
        "overtime": {
            "rate": "1.25x basic salary (1st 2 hours), 1.5x (after 2 hours)",
            "limit": "Max 20 hours per week overtime",
            "rest": "Minimum 1 hour rest per 5 hours work",
        },
        "public_holidays": "Work on public holiday = 3x salary + day off",
    },
}


# =============================================================================
# UAE TRADE LICENSE DATA (DED, Ajman DED, Free Zones)
# =============================================================================

UAE_TRADE_LICENSES = {
    "commercial": {
        "type": "Commercial Activity License",
        "use_case": "Buying/selling goods (retail, wholesale, distribution)",
        "emirates": {
            "dubai": {
                "authority": "Dubai Department of Economy & Tourism (DET)",
                "cost": "AED 2,000-5,000 (renewal AED 2,000)",
                "processing_time": "3-7 days",
                "required_docs": [
                    "Passport copy",
                    "Visa copy",
                    "Tenancy contract/property ownership",
                    "Bank reference",
                    "NOC (No Objection Certificate) from landlord if leasing",
                ],
            },
            "ajman": {
                "authority": "Ajman Department of Economic Development (DED)",
                "cost": "AED 1,000-2,000 (renewal AED 1,000)",
                "processing_time": "2-3 days",
                "required_docs": [
                    "Passport copy",
                    "Visa copy",
                    "Property contract/lease",
                    "Bank certificate",
                ],
            },
            "sharjah": {
                "authority": "Sharjah Department of Economic Development",
                "cost": "AED 1,500-3,500",
                "processing_time": "3-5 days",
            },
        },
    },
    "professional": {
        "type": "Professional Services License",
        "use_case": "Consulting, accounting, legal, IT, engineering services",
        "emirates": {
            "dubai": {
                "authority": "Dubai Department of Economy & Tourism",
                "cost": "AED 2,500-5,000",
                "processing_time": "5-10 days",
                "requirements": [
                    "Professional qualification certificate",
                    "Experience letter from previous employer (min 3 years)",
                    "Passport & visa copy",
                ],
            },
            "ajman": {
                "authority": "Ajman DED",
                "cost": "AED 1,500-2,500",
                "processing_time": "3-5 days",
            },
        },
    },
    "industrial": {
        "type": "Industrial Activity License",
        "use_case": "Manufacturing, processing, assembly",
        "location": "Must be in industrial zone",
        "emissions": "Environmental compliance certificate required",
        "labor": "May require Ministry of Human Resources approval for foreign workers",
        "cost": "AED 5,000-15,000",
        "requirements": [
            "Industrial site/factory lease",
            "Environmental impact assessment",
            "Safety & health plan",
            "Waste management plan",
        ],
    },
    "free_zone": {
        "type": "Free Zone License",
        "authorities": [
            {
                "name": "AFZA (Ajman Free Zone Authority)",
                "location": "Ajman",
                "cost": "AED 3,000-10,000/year",
                "benefits": [
                    "100% foreign ownership allowed",
                    "No customs duty on import/export",
                    "12-month visa exemption for setup",
                ],
            },
            {
                "name": "DMCC (Dubai Multi Commodities Centre)",
                "location": "Dubai",
                "cost": "AED 10,000-50,000+",
                "benefits": [
                    "100% foreign ownership",
                    "No restrictions on trading commodities",
                    "Excellent connectivity & logistics",
                ],
            },
            {
                "name": "JAFZA (Jebel Ali Free Zone)",
                "location": "Dubai",
                "cost": "AED 15,000-100,000+ (depends on space)",
                "benefits": [
                    "State-of-art port/airport infrastructure",
                    "No restriction on goods traded",
                    "100% foreign ownership",
                ],
            },
        ],
    },
    "renewal_requirements": {
        "frequency": "Annual (birthday of license)",
        "documents": [
            "Completed application form",
            "Trade name certificate (if changed)",
            "Passport & visa copy",
            "Tenancy contract (if renewed)",
            "Health certificate (for food/beverage)",
        ],
        "timing": "Renew within 30 days of expiry (grace period with penalty)",
    },
}


# =============================================================================
# UAE FOOD SAFETY REGULATIONS
# =============================================================================

UAE_FOOD_SAFETY = {
    "legal_references": [
        "Federal Law No. 10/2015 (Food Safety Law)",
        "ESMA UAE.S 5009 (UAE Standards for Food Safety)",
        "Municipality Food Safety Requirements",
    ],
    "requirements": {
        "supermarket": {
            "permit": "Food Safety Card from Municipality",
            "inspection": "Quarterly inspections minimum",
            "certifications": [
                "HACCP (Hazard Analysis Critical Control Points) certification",
                "ISO 22000 (Food Safety Management) recommended",
                "Halal certification (for meat/poultry)",
            ],
        },
        "restaurant": {
            "permit": "Food Safety Certificate from Municipality",
            "staff": "Food handler certification for all kitchen staff",
            "inspection": "Monthly health inspections",
            "kitchen": "Separate areas for meat/fish/vegetables (segregation)",
        },
        "food_manufacturing": {
            "license": "Industrial license + Food Safety Approval",
            "standards": "ESMA standards compliance",
            "traceability": "Full ingredient traceability system required",
            "audit": "Annual third-party audit (HACCP/ISO 22000)",
        },
    },
    "temperature_control": {
        "refrigerated": "Store at 4°C or below (dairy, meat, ready-to-eat)",
        "frozen": "Store at -18°C or below (meat, seafood, vegetables)",
        "monitoring": "Temperature logs required daily",
        "equipment": "Certified thermometers and temperature monitoring devices",
    },
    "labeling_rules": {
        "arabic_required": "All labels must have Arabic text",
        "content": [
            "Product name (Arabic & English)",
            "Ingredients list (Arabic & English)",
            "Country of origin",
            "Manufacturing & expiry date",
            "Allergen warnings (if applicable)",
            "Net weight/volume",
            "Storage instructions",
            "Nutritional information (for most foods)",
        ],
        "allergen_warning": "Must clearly label if contains: peanuts, tree nuts, soy, eggs, dairy, fish, shellfish, sesame",
    },
    "halal_certification": {
        "required_for": "All meat, poultry, seafood products",
        "authorities": [
            "UAE Ministry of Climate Change & Environment (MOCCAE)",
            "Municipality food safety authority",
            "Approved Halal certifiers (British Standards Institution, TÜV, etc.)",
        ],
        "slaughter": "Only at approved halal slaughterhouses",
        "audit": "Annual Halal certification audit",
    },
    "import_requirements": {
        "documents": [
            "Health certificate from country of origin",
            "Laboratory test results (for food safety)",
            "Halal certificate (if meat/poultry)",
            "Invoice & packing list",
        ],
        "inspection": "Customs + Municipality joint inspection upon arrival",
        "quarantine": "May be quarantined pending test results (1-3 weeks)",
        "banned_items": [
            "Pork products",
            "Products from non-halal sources",
            "Alcohol",
            "Counterfeit brands",
        ],
    },
    "penalties": {
        "violations": "AED 5,000-100,000 fine + product seizure",
        "repeat": "Double fine + closure of business (30-90 days)",
        "serious": "Criminal prosecution (false labeling, contamination)",
    },
}


# =============================================================================
# UAE VISA AND RESIDENCY RULES (Cabinet Decision No. 65/2022)
# =============================================================================

UAE_VISA_TYPES = {
    "employment": {
        "duration": "2-3 years (renewable)",
        "sponsor": "Employer (company/individual)",
        "cost": "Employer pays (visa + medical AED 500-1,000)",
        "requirements": [
            "Employment contract (attested by notary)",
            "Passport valid 6+ months",
            "Medical fitness test",
            "Police clearance certificate",
            "Sponsor with trade license",
        ],
        "quota": "Subject to Labour Market Nationalization (varies by emirate)",
        "transfer": "Can transfer to new employer (new sponsorship)",
    },
    "investor": {
        "duration": "3 years (renewable)",
        "investment": {
            "new_business": "AED 500,000 (capital investment)",
            "investment_account": "AED 500,000-1,000,000 (bank deposit)",
        },
        "benefits": [
            "100% business ownership (no local partner required in UAE)",
            "Bring family members (spouse, children)",
            "Work permit for family members",
        ],
        "requirements": [
            "Proof of investment (bank certificate/property deed)",
            "Business plan",
            "Passport valid 6+ months",
            "Medical fitness",
        ],
    },
    "golden_visa": {
        "duration": "5 or 10 years (renewable)",
        "categories": [
            {
                "name": "Investors",
                "investment": "AED 2,000,000 minimum in real estate or business",
                "requirements": "Proof of investment, clean background",
            },
            {
                "name": "Entrepreneurs",
                "investment": "Successful startup/business (discretionary)",
                "requirements": "Business plan, proof of concept",
            },
            {
                "name": "Brilliant talented persons (Scientists, inventors, creatives)",
                "qualification": "Significant research contributions or creative achievements",
                "requirements": "Portfolio, publications, or creative works evidence",
            },
            {
                "name": "Scientists and Specialists",
                "qualification": "PhD or significant specialized contributions",
                "requirements": "Degree, research publications, job offer",
            },
            {
                "name": "Excellent students and graduates",
                "qualification": "Top academic achievers",
                "requirements": "Academic records, degree certificate",
            },
            {
                "name": "Pioneers of humanitarian work",
                "qualification": "Recognized humanitarian contributions",
                "requirements": "Evidence of humanitarian work impact",
            },
            {
                "name": "First line of defense heroes",
                "qualification": "Military, emergency services personnel",
                "requirements": "Service verification",
            },
        ],
        "benefits": [
            "Can live, work, or study in UAE",
            "Bring family members",
            "No requirement to have local sponsor for business",
            "Can invest in real estate freely",
        ],
    },
    "green_visa": {
        "duration": "2-3 years (renewable)",
        "eligibility": [
            "Skilled employees (minimum salary AED 15,000/month)",
            "Freelancers/self-employed (minimum annual income AED 360,000)",
            "Investors/partners in commercial establishments",
        ],
        "requirements": [
            "Income proof (AED 15,000/month minimum or AED 360,000 annual for freelancers)",
            "Health insurance",
            "Accommodation proof",
            "Passport valid 6+ months",
        ],
        "cost": "Visa fee ~AED 500-700, sponsorship fee ~AED 1,000",
    },
    "tourist": {
        "duration": "30 days (can extend to 60-90 days)",
        "cost": "AED 100-200 (visa on arrival at airport)",
        "requirements": [
            "Valid passport",
            "Return ticket proof",
            "Accommodation booking",
            "Sufficient funds",
        ],
        "no_work": "Cannot work on tourist visa (penalty: deportation + fine)",
    },
    "family": {
        "duration": "2-3 years",
        "sponsor": "Spouse or parent living in UAE",
        "requirements": [
            "Marriage certificate (for spouse)",
            "Birth certificate (for children)",
            "Sponsor income proof (AED 3,000+ for spouse)",
            "Accommodation proof",
        ],
        "dependents": "Can include spouse & children up to age 18",
    },
    "domestic_worker": {
        "duration": "2 years",
        "sponsor": "Individual employer (household)",
        "contract": "Mandatory employment contract in Arabic",
        "requirements": [
            "Medical fitness test",
            "Sponsor ID copy",
            "Contract attested by notary",
            "Police clearance (in home country)",
        ],
        "restrictions": [
            "Cannot work outside sponsor's household",
            "Subject to Federal Law No. 10/2008 (Domestic Workers)",
            "Minimum wage AED 1,200/month",
            "1.5 days weekly rest mandatory",
        ],
    },
    "recent_changes_2024_2026": [
        "Green Visa introduced (2021) for freelancers & retirees",
        "Golden Visa expanded to more professionals (2022)",
        "Visa transfer simplified (no sponsorship cancellation needed)",
        "Family visas made easier (lower income requirements)",
        "Multiple entry tourist visas available (180-day validity)",
    ],
}


# =============================================================================
# UAE COMMERCIAL LAW (Federal Decree-Law No. 32/2021)
# =============================================================================

UAE_COMMERCIAL_LAW = {
    "legal_reference": "Federal Decree-Law No. 32/2021 (Commercial Companies Law)",
    "company_formation": {
        "types": [
            {
                "name": "Limited Liability Company (LLC)",
                "minimum_partners": 1,
                "local_ownership": "No statutory minimum (abolished under Decree-Law 32/2021). Activity-specific minimums may apply.",
                "capital": "No statutory minimum (abolished under Decree-Law 32/2021). Activity-specific minimums may apply.",
                "setup_cost": "AED 5,000-15,000 (legal, registration)",
            },
            {
                "name": "Public Joint Stock Company",
                "minimum_partners": 3,
                "capital": "AED 1,000,000+",
                "share": "Shares can be public/private",
                "requirements": "Board of directors, audit committee",
            },
            {
                "name": "Private Joint Stock Company",
                "minimum_partners": 2,
                "capital": "AED 500,000+",
                "shares": "Shares held privately",
            },
            {
                "name": "General Partnership",
                "minimum_partners": 2,
                "liability": "Partners jointly liable for debts",
                "no_capital_requirement": True,
            },
            {
                "name": "Limited Partnership",
                "general_partners": "Min 1 (fully liable)",
                "limited_partners": "Min 1 (liability limited to capital)",
                "capital": "As agreed by partners",
            },
        ],
        "registration_process": [
            "Prepare memorandum of association (MOA)",
            "Get NOC from landlord (for office)",
            "Apply to authorities (DED/DET or free zone)",
            "Name reservation approval",
            "Document attestation",
            "Company registration",
            "Obtain trade license (commercial/professional/industrial)",
        ],
        "timeline": "7-14 days (standard); 2-3 days (express)",
    },
    "partnerships": {
        "general_partnership": {
            "partners": "All partners have equal rights unless MOA specifies",
            "liability": "Each partner liable for all debts (joint & several)",
            "decision": "All partners can bind company unless restricted by MOA",
            "dissolution": "On death/withdrawal of any partner",
        },
        "limited_partnership": {
            "structure": "General partners manage business; limited partners invest only",
            "general_liability": "Unlimited liability for general partners",
            "limited_liability": "Limited to capital contributed",
            "restrictions": "Limited partners cannot participate in management",
        },
    },
    "llc_structure": {
        "ownership": {
            "uae_national": "100% foreign ownership permitted in most mainland sectors since Cabinet Decision No. 16/2020 and Decree-Law No. 32/2021. Only 'strategic impact' activities retain local ownership requirements.",
            "foreign": "100% foreign ownership permitted in most mainland sectors. Exception: strategic impact activities may retain local ownership requirements.",
        },
        "minimum_capital": "No statutory minimum (abolished under Decree-Law 32/2021). Activity-specific minimums may apply.",
        "board": "Min 1 member (can be single member LLC)",
        "meeting": "Annual general assembly required",
        "records": "Must maintain accounting records for 3 years",
        "dissolution": "Requires unanimous vote of members",
    },
    "free_zone_advantages": {
        "foreign_ownership": "100% foreign ownership allowed",
        "no_local_sponsor": "No requirement for UAE national partner",
        "import_export": "No customs duty on import/export of goods",
        "lease_exemption": "No office/warehouse required (office space in free zone)",
        "visa_flexibility": "Easier visa sponsorship for employees",
    },
    "anti_competition": {
        "legal_reference": "Federal Law No. 4/2012 (Unfair Competition)",
        "prohibited": [
            "Monopolistic practices",
            "Price fixing cartels",
            "Bid rigging",
            "Market division agreements",
            "Predatory pricing",
        ],
        "enforcement": "UAE Competition Regulation Authority (FCCA)",
        "penalties": "Fines up to AED 10,000,000 + injunction",
    },
    "commercial_agency": {
        "definition": "Non-exclusive distribution right for foreign principal goods",
        "requirements": [
            "Notarized agency agreement",
            "Registered with authorities",
            "Agent must be licensed trader",
        ],
        "restrictions": [
            "Exclusive agency may require MOA amendment",
            "Cannot be terminated without cause (Federal Law 50/2022)",
        ],
        "protection": "Agent entitled to compensation if terminated",
    },
    "bankruptcy": {
        "legal_reference": "Federal Law No. 9/2016 (Bankruptcy Law)",
        "petition": "Filed by debtor or creditors (min AED 100,000 debt)",
        "options": [
            {
                "name": "Reorganization (Istidamah)",
                "period": "3-5 years",
                "goal": "Restructure & continue business",
            },
            {
                "name": "Liquidation",
                "goal": "Sell assets & pay creditors",
                "order": "Secured creditors first, then employees, then general creditors",
            },
        ],
    },
    "intellectual_property": {
        "trademarks": {
            "protection": "Registered with UAE Ministry of Economy",
            "validity": "10 years (renewable every 10 years)",
            "cost": "AED 1,500-3,000 per class",
            "process": "Application, examination, publication, registration (2-6 months)",
        },
        "patents": {
            "protection": "20 years from filing date",
            "authority": "UAE Ministry of Industry & Advanced Technology",
            "requirements": ["Non-obvious", "Novel", "Industrially applicable"],
        },
        "copyright": {
            "automatic": "Automatic upon creation (no registration needed)",
            "duration": "Author's life + 70 years",
            "registration": "Optional (provides legal evidence)",
        },
    },
}


# =============================================================================
# UAE CUSTOMS AND IMPORT REGULATIONS
# =============================================================================

UAE_CUSTOMS = {
    "tariff_rates": {
        "products": [
            {
                "category": "Electronics & IT",
                "rate": "5%",
                "special_rules": "Some components 0% if for manufacturing",
            },
            {
                "category": "Food & Beverages",
                "rate": "5%",
                "special_rules": "Alcohol prohibited; some items subject to excise duty",
            },
            {
                "category": "Textiles & Clothing",
                "rate": "5%",
                "special_rules": "Subject to free zone benefits if processed in UAE",
            },
            {
                "category": "Machinery & Equipment",
                "rate": "5%",
                "special_rules": "0% for manufacturing inputs",
            },
            {
                "category": "Vehicles",
                "rate": "5%",
                "special_rules": "Plus road tax 50-100% (for resale)",
            },
        ]
    },
    "documentation": {
        "required": [
            "Packing list (with HS codes)",
            "Commercial invoice (original + 1 copy)",
            "Bill of lading / Air waybill",
            "Certificate of origin",
            "Product certification (CE, FDA, ISO if required)",
            "Import permit (for restricted items)",
        ],
        "customs_clearance": "1-3 days (normal); 5-10 days (inspection required)",
    },
    "prohibited_items": [
        "Pork & pork products",
        "Alcohol & alcoholic beverages",
        "Firearms & ammunition (except licensed imports)",
        "Narcotics & psychotropic substances",
        "Counterfeited goods & pirated content",
        "Items promoting immoral content",
    ],
    "restricted_items": [
        "Medicines (require Ministry of Health approval)",
        "Chemicals (require safety certification)",
        "Electronics (may require frequency approval)",
        "Cosmetics (require ESMA standards compliance)",
        "Food items (require health certificate)",
    ],
    "free_zone_benefits": {
        "duty": "0% customs duty on goods in/out of free zone",
        "duration": "Goods can be stored indefinitely in free zone before payment of duty",
        "re_export": "Re-export without paying import duty",
        "zones": [
            "AFZA (Ajman)",
            "DMCC (Dubai)",
            "JAFZA (Dubai Jebel Ali)",
            "Ras Al Khaimah (RAK) Free Zone",
            "Others in Sharjah, Fujairah, UAQ",
        ],
    },
    "re_export_rules": {
        "definition": "Goods imported for subsequent re-export (no local consumption)",
        "documentation": "Re-export declaration at customs",
        "duty": "No import duty if documented as re-export",
        "time_limit": "Typically 6 months to re-export (can extend)",
    },
    "penalties": {
        "violations": [
            "Importing prohibited items: Seizure + fine AED 50,000-500,000",
            "False declaration: AED 100,000-1,000,000 fine + imprisonment 3-15 days",
            "Smuggling: Criminal prosecution + heavy penalties",
        ]
    },
}


# =============================================================================
# DUBAI RERA - REAL ESTATE REGULATORY AUTHORITY
# =============================================================================

DUBAI_RERA = {
    "legal_reference": "Dubai Law No. 26/2007 (RERA Law)",
    "authority": "Dubai Real Estate Regulatory Authority (RERA)",
    "regulations": {
        "rent": {
            "ejari_registration": {
                "definition": "Mandatory registration of all residential rental contracts",
                "authority": "Dubai Land Department (DLD)",
                "cost": "AED 170 (standard); AED 220 (express)",
                "timeline": "Same-day (express); 1-3 days (normal)",
                "benefits": [
                    "Legal proof of tenancy",
                    "Protection for both landlord & tenant",
                    "Basis for visa sponsorship",
                    "Dispute resolution evidence",
                ],
            },
            "rent_increase": {
                "legal_reference": "RERA Decree No. 43/2013",
                "rules": [
                    {
                        "scenario": "Less than 10% below market",
                        "increase": "0% increase allowed",
                        "notice": "90 days written notice required before renewal",
                    },
                    {
                        "scenario": "11-20% below market",
                        "increase": "Max 5% increase",
                        "notice": "90 days written notice required before renewal",
                    },
                    {
                        "scenario": "21-30% below market",
                        "increase": "Max 10% increase",
                        "notice": "90 days written notice required before renewal",
                    },
                    {
                        "scenario": "31-40% below market",
                        "increase": "Max 15% increase",
                        "notice": "90 days written notice required before renewal",
                    },
                    {
                        "scenario": "More than 40% below market",
                        "increase": "Max 20% increase",
                        "notice": "90 days written notice required before renewal",
                    },
                ],
                "rera_index": "Updated annually (varies by area and property type)",
            },
            "tenant_rights": [
                "Right to quiet enjoyment of property",
                "Landlord must maintain property in habitable condition",
                "Security deposit: Max 5% of annual rent",
                "Deposit refund: Within 30 days of eviction (minus damages)",
                "Notice period: 30 days for both parties",
            ],
            "landlord_rights": [
                "Collect rent on due date",
                "Evict for non-payment (after notice)",
                "Evict for property damage (beyond normal wear)",
                "Non-renewal after tenancy expires (with 90 days notice)",
            ],
        },
        "buy": {
            "off_plan": {
                "definition": "Purchase of property under construction",
                "protection": "RERA 'Escrow' account holds buyer funds (in developer account)",
                "requirements": [
                    "Signed booking form",
                    "Payment plan (typically 20% down, 80% during construction)",
                    "Completion guarantee insurance (5% of purchase price)",
                ],
                "timeline": "2-5 years (depending on project)",
            },
            "completed_property": {
                "transfer": "Direct transfer of title at DLD",
                "costs": [
                    "DLD registration fee: 4% of purchase price",
                    "Agent commission: ~2-3% (if using agent)",
                    "Legal/processing fees: AED 1,000-2,000",
                ],
                "transfer_timeline": "5-10 business days after payment",
            },
            "foreign_ownership": {
                "allowed_areas": [
                    "Designated freehold zones (Dubai, Ajman, Ras Al Khaimah, Fujairah)",
                    "Dubai: Downtown Dubai, Emirates Hills, Palm Jumeirah, Jumeirah Islands, etc.",
                    "Ajman: Free Zone areas",
                ],
                "restrictions": "Cannot own in certain strategic locations (military, border areas)",
            },
        },
        "commercial_lease": {
            "registration": "Must register at DLD (like residential)",
            "contract_terms": [
                "Clear specification of commercial use (office, retail, warehouse, etc.)",
                "Rent payment terms",
                "Tenant maintenance obligations",
                "Landlord repairs & maintenance obligations",
            ],
            "notice_period": "90 days for non-renewal",
            "rent_increase": "No RERA cap on commercial rent (market-driven)",
        },
    },
    "dispute_resolution": {
        "methods": [
            {"method": "Mediation (RERA)", "timeline": "15-30 days", "cost": "AED 200-500"},
            {"method": "Arbitration (RERA)", "timeline": "30-60 days", "cost": "AED 500-2,000"},
            {
                "method": "Dubai Court",
                "timeline": "6-12 months",
                "cost": "Court fees + lawyer fees",
            },
        ]
    },
}


# =============================================================================
# UAE TAX COMPLIANCE (Federal Decree-Law No. 8/2017 & No. 47/2022)
# =============================================================================

UAE_TAX_COMPLIANCE = {
    "vat": {
        "legal_reference": "Federal Decree-Law No. 8/2017",
        "rate": "5% (flat rate on most goods/services)",
        "registration": {
            "threshold": "Mandatory if turnover > AED 375,000/year",
            "voluntary": "Can register below threshold",
            "authority": "Federal Tax Authority (FTA)",
            "cost": "Free",
        },
        "filing": {
            "frequency": "Monthly (if turnover > AED 1.5M) or Quarterly",
            "deadline": "End of month/quarter + 20 days",
            "method": "Online via FTA portal",
        },
        "zero_rated": [
            "Exports of goods and services outside GCC",
            "International transport and related supplies",
            "First supply of residential property within 3 years of completion",
            "Certain healthcare services and related goods",
            "Certain educational services by recognized institutions",
            "Investment-grade precious metals (99%+ purity)",
            "Crude oil and natural gas",
        ],
        "exempt": [
            "Subsequent supplies of residential property (resale/rental)",
            "Bare land",
            "Local passenger transport (bus, metro, taxi)",
            "Certain financial services",
            "Life insurance",
        ],
        "penalties": {
            "late_filing": "AED 500-2,000 per month late",
            "non_payment": "15% + 1.5% monthly interest",
            "false_declaration": "AED 10,000-100,000 fine",
        },
    },
    "corporate_tax": {
        "legal_reference": "Federal Decree-Law No. 47/2022",
        "rate": "9% on taxable income (for businesses with > AED 375,000 revenue)",
        "exemption": "0% for businesses with < AED 375,000 annual revenue",
        "timeline": "Effective 1 June 2023",
        "taxable_income": "Revenue - Allowable expenses (depreciation, salaries, utilities, etc.)",
        "filing": {
            "deadline": "180 days after fiscal year end",
            "authority": "Federal Tax Authority (FTA)",
            "method": "Online filing",
        },
        "penalties": {
            "late": "AED 500-5,000 per month late",
            "non_payment": "25% penalty + 5% annual interest",
            "audit_failure": "Can result in reassessment + penalties",
        },
    },
    "excise_tax": {
        "legal_reference": "Federal Decree-Law No. 7/2017",
        "rate": "50% on carbonated soft drinks",
        "rate_extended": "100% on energy drinks (since 2021)",
        "rate_tobacco": "100% on tobacco & nicotine products",
        "application": "Tax on manufacture/import of listed goods",
        "collection": "Added to retail price",
    },
    "customs_duty": {
        "standard_rate": "5% (GCC Common External Tariff)",
        "exceptions": [
            "0% for manufacturing inputs (under certain conditions)",
            "0% for goods in free zones",
            "Varies by product category",
        ],
        "collection": "At point of import by customs authority",
    },
    "fta_registration": {
        "process": [
            "Apply online at FTA portal",
            "Provide business details, bank account, VAT registration (if applicable)",
            "Electronic signature required",
            "Approval typically same-day",
        ],
        "documents": [
            "Trade license copy",
            "MOA (if company)",
            "Passport copy",
            "Bank certificate",
            "VAT registration certificate",
        ],
    },
    "compliance_requirements": {
        "record_keeping": {
            "duration": "Minimum 5 years",
            "items": [
                "Invoices & receipts",
                "Supplier contracts",
                "Bank statements",
                "Audit reports",
                "VAT returns",
            ],
        },
        "audit": {
            "frequency": "Annual (mandatory for large companies)",
            "requirements": "External audit by Big 4 or approved auditor",
            "costs": "AED 5,000-50,000 depending on complexity",
        },
    },
    "transfer_pricing": {
        "legal_reference": "Federal Decree-Law No. 47/2022 (new rules)",
        "requirement": "Transactions with related parties must be at arm's length",
        "documentation": "Must maintain documentation of transfer pricing policy",
        "penalty": "Adjustment of income + interest + fine",
    },
}


# =============================================================================
# TOOL FUNCTIONS
# =============================================================================


@handle_tool_errors("research_uae_labor_law")
async def research_uae_labor_law(query: str, topic: str = "general") -> dict[str, Any]:
    """UAE Labor Law lookup with Federal Decree-Law No. 33/2021 references.

    Args:
        query: Specific legal question about UAE labor law
        topic: Topic area (general, termination, salary, leave, gratuity,
               visa_cancellation, part_time, probation, discrimination, work_hours)

    Returns:
        Dictionary with legal info, articles, and LLM analysis
    """
    result = {
        "query": query,
        "topic": topic,
        "source": "Federal Decree-Law No. 33/2021 (UAE Labour Law)",
        "data": UAE_LABOR_LAW_TOPICS.get(topic, UAE_LABOR_LAW_TOPICS["general"]),
    }

    # Attempt LLM enhancement for detailed analysis
    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide detailed legal analysis of UAE labor law question: {query}\n"
                f"Topic: {topic}\n"
                f"Reference: Federal Decree-Law No. 33/2021\n"
                f"Provide practical guidance for both employers and employees.",
                model="auto",
            )
            result["llm_analysis"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for labor_law: %s", e)

    return result


@handle_tool_errors("research_uae_trade_license")
async def research_uae_trade_license(
    business_type: str, emirate: str = "ajman", free_zone: bool = False
) -> dict[str, Any]:
    """UAE Trade License requirements and costs.

    Args:
        business_type: commercial, professional, or industrial
        emirate: dubai, ajman, sharjah (default: ajman)
        free_zone: Whether to include free zone options

    Returns:
        License requirements, costs, documents, timeline
    """
    license_info = UAE_TRADE_LICENSES.get(business_type, {})

    if not license_info:
        return {
            "error": f"Unknown business type: {business_type}",
            "valid_types": ["commercial", "professional", "industrial"],
        }

    result = {
        "business_type": business_type,
        "emirate": emirate,
        "license_info": license_info,
        "renewal": UAE_TRADE_LICENSES.get("renewal_requirements", {}),
    }

    # Add emirate-specific info if available
    if emirate and "emirates" in license_info:
        emirate_data = license_info["emirates"].get(emirate)
        if emirate_data:
            result["emirate_specific"] = emirate_data

    if free_zone and "free_zone" in UAE_TRADE_LICENSES:
        result["free_zone_options"] = UAE_TRADE_LICENSES["free_zone"]

    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide step-by-step guidance for obtaining a {business_type} "
                f"trade license in {emirate}, UAE. Include typical timeline, "
                f"required documents, and common pitfalls.",
                model="auto",
            )
            result["llm_guidance"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for trade_license: %s", e)

    return result


@handle_tool_errors("research_uae_food_safety")
async def research_uae_food_safety(
    query: str, business_type: str = "supermarket"
) -> dict[str, Any]:
    """UAE Food Safety regulations (ESMA standards, Municipality requirements).

    Args:
        query: Specific food safety question
        business_type: supermarket, restaurant, or food_manufacturing

    Returns:
        Food safety requirements, certifications, compliance rules
    """
    result = {
        "query": query,
        "business_type": business_type,
        "legal_references": UAE_FOOD_SAFETY["legal_references"],
        "requirements": UAE_FOOD_SAFETY["requirements"].get(
            business_type, UAE_FOOD_SAFETY["requirements"]["supermarket"]
        ),
        "temperature_control": UAE_FOOD_SAFETY["temperature_control"],
        "labeling_rules": UAE_FOOD_SAFETY["labeling_rules"],
        "halal_certification": UAE_FOOD_SAFETY["halal_certification"],
        "import_requirements": UAE_FOOD_SAFETY["import_requirements"],
        "penalties": UAE_FOOD_SAFETY["penalties"],
    }

    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide detailed food safety compliance guidance for {business_type} "
                f"in UAE. Question: {query}\n"
                f"References: ESMA UAE.S 5009, Federal Law No. 10/2015\n"
                f"Include inspection procedures and certification timelines.",
                model="auto",
            )
            result["llm_analysis"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for food_safety: %s", e)

    return result


@handle_tool_errors("research_uae_visa_rules")
async def research_uae_visa_rules(
    visa_type: str = "employment", nationality: str = "", query: str = ""
) -> dict[str, Any]:
    """UAE Visa and Residency rules (Cabinet Decision No. 65/2022 reforms).

    Args:
        visa_type: employment, investor, golden, green, tourist, family, domestic_worker
        nationality: Applicant nationality (for context, optional)
        query: Specific visa question

    Returns:
        Visa requirements, costs, duration, recent changes
    """
    _VISA_ALIASES = {
        "golden": "golden_visa",
        "green": "green_visa",
        "domestic": "domestic_worker",
    }
    lookup_key = _VISA_ALIASES.get(visa_type, visa_type)
    visa_info = UAE_VISA_TYPES.get(lookup_key, {})

    if not visa_info:
        valid_types = [k for k in UAE_VISA_TYPES if k != "recent_changes_2024_2026"]
        return {
            "error": f"Unknown visa type: {visa_type}",
            "valid_types": valid_types,
        }

    result = {
        "visa_type": visa_type,
        "nationality": nationality,
        "query": query,
        "visa_details": visa_info,
        "recent_changes": UAE_VISA_TYPES.get("recent_changes_2024_2026", []),
    }

    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide visa application guidance for {visa_type} visa to UAE. "
                f"Query: {query}\n"
                f"Recent reforms (Cabinet Decision No. 65/2022) streamlined visa processes. "
                f"Include application steps, estimated processing time, costs, and tips.",
                model="auto",
            )
            result["llm_guidance"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for visa_rules: %s", e)

    return result


@handle_tool_errors("research_uae_commercial_law")
async def research_uae_commercial_law(query: str, topic: str = "general") -> dict[str, Any]:
    """UAE Commercial Law (Federal Decree-Law No. 32/2021).

    Args:
        query: Specific commercial law question
        topic: company_formation, partnerships, llc, free_zone, foreign_ownership,
               anti_competition, commercial_agency, bankruptcy, intellectual_property

    Returns:
        Commercial law provisions, company structures, formation process
    """
    # Map alternative topic names to actual keys
    _TOPIC_ALIASES = {
        "llc": "llc_structure",
        "free_zone": "free_zone_advantages",
        "foreign_ownership": "company_formation",
    }
    lookup_topic = _TOPIC_ALIASES.get(topic, topic)

    result = {
        "query": query,
        "topic": topic,
        "legal_reference": "Federal Decree-Law No. 32/2021 (Commercial Companies Law)",
        "overview": UAE_COMMERCIAL_LAW.get(
            lookup_topic, UAE_COMMERCIAL_LAW.get("company_formation")
        ),
    }

    # Add general company info if not specific topic
    if topic == "general":
        result["company_types"] = UAE_COMMERCIAL_LAW.get("company_formation", {}).get("types", [])

    # Add note for foreign_ownership mapping
    if topic == "foreign_ownership":
        result["note"] = (
            "Foreign ownership rules are included in company_formation topic under Decree-Law No. 32/2021, which permits 100% foreign ownership in most mainland sectors."
        )

    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide detailed commercial law guidance on: {query}\n"
                f"Topic: {topic}\n"
                f"Reference: Federal Decree-Law No. 32/2021 (Commercial Companies Law)\n"
                f"Include practical steps, cost estimates, and legal considerations.",
                model="auto",
            )
            result["llm_analysis"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for commercial_law: %s", e)

    return result


@handle_tool_errors("research_uae_customs")
async def research_uae_customs(
    product_category: str, origin_country: str = "", query: str = ""
) -> dict[str, Any]:
    """UAE Customs and Import regulations.

    Args:
        product_category: food, electronics, cosmetics, textiles, machinery
        origin_country: Country of origin (optional)
        query: Specific customs question

    Returns:
        Tariff rates, documentation, prohibited items, free zone benefits
    """
    result = {
        "product_category": product_category,
        "origin_country": origin_country,
        "query": query,
        "tariff_rates": UAE_CUSTOMS["tariff_rates"],
        "documentation": UAE_CUSTOMS["documentation"],
        "prohibited_items": UAE_CUSTOMS["prohibited_items"],
        "restricted_items": UAE_CUSTOMS["restricted_items"],
        "free_zone_benefits": UAE_CUSTOMS["free_zone_benefits"],
        "re_export_rules": UAE_CUSTOMS["re_export_rules"],
        "penalties": UAE_CUSTOMS["penalties"],
    }

    # Filter tariff rates by product category if it exists
    if product_category:
        matching_rates = [
            item
            for item in UAE_CUSTOMS["tariff_rates"]["products"]
            if product_category.lower() in item["category"].lower()
        ]
        if matching_rates:
            result["matching_tariff_rates"] = matching_rates

    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide customs clearance guidance for importing {product_category} "
                f"from {origin_country or 'any country'} to UAE. Query: {query}\n"
                f"Include tariff codes, required documents, timelines, and free zone options.",
                model="auto",
            )
            result["llm_guidance"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for customs: %s", e)

    return result


@handle_tool_errors("research_uae_rera")
async def research_uae_rera(query: str, transaction_type: str = "rent") -> dict[str, Any]:
    """Dubai RERA (Real Estate Regulatory Authority) rules.

    Args:
        query: Specific RERA question
        transaction_type: rent, buy, off_plan, commercial_lease

    Returns:
        RERA regulations, Ejari registration, rent increase rules, tenant/landlord rights
    """
    # Handle off_plan special case
    if transaction_type == "off_plan":
        regulations = DUBAI_RERA["regulations"]["buy"]["off_plan"]
    else:
        regulations = DUBAI_RERA["regulations"].get(
            transaction_type, DUBAI_RERA["regulations"]["rent"]
        )

    result = {
        "query": query,
        "transaction_type": transaction_type,
        "legal_reference": "Dubai Law No. 26/2007 (RERA Law)",
        "authority": "Dubai Real Estate Regulatory Authority (RERA)",
        "regulations": regulations,
        "dispute_resolution": DUBAI_RERA["dispute_resolution"],
    }

    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide detailed RERA guidance for {transaction_type} in Dubai. "
                f"Query: {query}\n"
                f"Reference: Dubai Law No. 26/2007\n"
                f"Include Ejari registration, rent increase rules, dispute resolution options.",
                model="auto",
            )
            result["llm_analysis"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for rera: %s", e)

    return result


@handle_tool_errors("research_uae_tax_compliance")
async def research_uae_tax_compliance(query: str, tax_type: str = "vat") -> dict[str, Any]:
    """UAE Tax Compliance (VAT, Corporate Tax, Excise, Customs Duty).

    Args:
        query: Specific tax compliance question
        tax_type: vat, corporate_tax, excise_tax, customs_duty

    Returns:
        Tax rates, registration, filing deadlines, penalties, exemptions
    """
    tax_data = UAE_TAX_COMPLIANCE.get(tax_type, UAE_TAX_COMPLIANCE["vat"])

    result = {
        "query": query,
        "tax_type": tax_type,
        "tax_details": tax_data,
        "fta_registration": UAE_TAX_COMPLIANCE["fta_registration"],
        "compliance_requirements": UAE_TAX_COMPLIANCE["compliance_requirements"],
        "transfer_pricing": UAE_TAX_COMPLIANCE["transfer_pricing"],
    }

    if query_llm:
        try:
            llm_response = await query_llm(
                f"Provide comprehensive tax compliance guidance for {tax_type} in UAE. "
                f"Query: {query}\n"
                f"References: Federal Decree-Law No. 8/2017 (VAT), "
                f"Federal Decree-Law No. 47/2022 (Corporate Tax)\n"
                f"Include filing deadlines, exemptions, and penalty avoidance strategies.",
                model="auto",
            )
            result["llm_analysis"] = llm_response
        except Exception as e:
            logger.debug("llm_enhancement failed for tax_compliance: %s", e)

    return result
