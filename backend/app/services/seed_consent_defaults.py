"""
Seed default consent purposes and initial privacy policy for ContraRed.

Called during app startup to ensure the product's processing purposes exist.
Idempotent: safe to run on every startup.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import ConsentPurpose, ConsentPolicy

logger = logging.getLogger(__name__)

# ContraRed's 8 consent purposes
CONSENT_PURPOSES = [
    {
        "purpose_code": "account_management",
        "name": "Account Management",
        "description": (
            "We store your email address and name to create and manage your ContraRed account. "
            "This data is used for authentication, account recovery, and to personalise your experience."
        ),
        "personal_data_categories": ["email", "name"],
        "third_parties": [],
        "retention_period": "Duration of account + 90 days after deletion",
        "is_required": True,
        "translations": {
            "hi": {
                "name": "खाता प्रबंधन",
                "description": (
                    "हम आपका ईमेल पता और नाम आपका ContraRed खाता बनाने और प्रबंधित करने के लिए संग्रहीत करते हैं। "
                    "इस डेटा का उपयोग प्रमाणीकरण, खाता पुनर्प्राप्ति और आपके अनुभव को वैयक्तिकृत करने के लिए किया जाता है।"
                ),
            }
        },
    },
    {
        "purpose_code": "contract_analysis",
        "name": "AI Contract Analysis",
        "description": (
            "Your contract text is sent to AI services (Google Vertex AI or Azure OpenAI) for "
            "clause detection, risk identification, and legal analysis. Contract text is processed "
            "in-memory and never stored permanently on our servers (Zero Data Retention mode)."
        ),
        "personal_data_categories": ["contract_content", "document_metadata"],
        "third_parties": [
            "Google Cloud Vertex AI (configured region)",
            "Azure OpenAI (configured region)",
        ],
        "retention_period": "Not stored (processed in-memory only)",
        "is_required": False,
        "translations": {
            "hi": {
                "name": "AI अनुबंध विश्लेषण",
                "description": (
                    "आपका अनुबंध टेक्स्ट क्लॉज़ डिटेक्शन, जोखिम पहचान और कानूनी विश्लेषण के लिए "
                    "AI सेवाओं (Google Vertex AI या Azure OpenAI) को भेजा जाता है। अनुबंध टेक्स्ट "
                    "इन-मेमोरी प्रोसेस किया जाता है और हमारे सर्वर पर स्थायी रूप से संग्रहीत नहीं किया जाता है।"
                ),
            }
        },
    },
    {
        "purpose_code": "ai_drafting",
        "name": "AI Contract Drafting",
        "description": (
            "AI-powered contract drafting and suggested clause modifications. Your contract context "
            "is sent to AI services to generate alternative clause language and fix suggestions."
        ),
        "personal_data_categories": ["contract_content", "clause_context"],
        "third_parties": [
            "Google Cloud Vertex AI (configured region)",
            "Azure OpenAI (configured region)",
        ],
        "retention_period": "Not stored (processed in-memory only)",
        "is_required": False,
        "translations": {
            "hi": {
                "name": "AI अनुबंध ड्राफ्टिंग",
                "description": (
                    "AI-संचालित अनुबंध ड्राफ्टिंग और सुझाई गई क्लॉज़ संशोधन। "
                    "वैकल्पिक क्लॉज़ भाषा और सुधार सुझाव उत्पन्न करने के लिए आपका अनुबंध संदर्भ AI सेवाओं को भेजा जाता है।"
                ),
            }
        },
    },
    {
        "purpose_code": "risk_assessment",
        "name": "Automated Risk Assessment",
        "description": (
            "Automated risk scoring of your contracts using AI. Each clause is evaluated against "
            "legal standards and your organisation's playbook to generate risk ratings (Red/Yellow/Green)."
        ),
        "personal_data_categories": ["contract_content", "risk_metadata"],
        "third_parties": [
            "Google Cloud Vertex AI (configured region)",
            "Azure OpenAI (configured region)",
        ],
        "retention_period": (
            "Not stored in Zero Data Retention mode; deployment policy applies when ZDR is disabled"
        ),
        "is_required": False,
        "translations": {
            "hi": {
                "name": "स्वचालित जोखिम मूल्यांकन",
                "description": (
                    "AI का उपयोग करके आपके अनुबंधों का स्वचालित जोखिम स्कोरिंग। "
                    "जोखिम रेटिंग (लाल/पीला/हरा) उत्पन्न करने के लिए प्रत्येक क्लॉज़ का कानूनी मानकों के विरुद्ध मूल्यांकन किया जाता है।"
                ),
            }
        },
    },
    {
        "purpose_code": "billing",
        "name": "Payment Processing",
        "description": (
            "Processing your subscription payments through Razorpay (for INR) or Stripe (for USD/EUR/GBP). "
            "Your payment details are handled directly by the payment processor; we store only "
            "customer IDs and transaction references."
        ),
        "personal_data_categories": ["payment_customer_id", "transaction_references"],
        "third_parties": ["Razorpay (India)", "Stripe (US)"],
        "retention_period": "Applicable tax, accounting, chargeback, and dispute-retention schedule",
        "is_required": False,
        "translations": {
            "hi": {
                "name": "भुगतान प्रसंस्करण",
                "description": (
                    "Razorpay (INR के लिए) या Stripe (USD/EUR/GBP के लिए) के माध्यम से आपके सदस्यता भुगतान का प्रसंस्करण। "
                    "आपके भुगतान विवरण सीधे भुगतान प्रोसेसर द्वारा संभाले जाते हैं।"
                ),
            }
        },
    },
    {
        "purpose_code": "analytics",
        "name": "Product Analytics",
        "description": (
            "Internal usage tracking to improve ContraRed. We log which features you use, "
            "scan counts, and performance metrics. This data is stored on our servers only "
            "and is never shared with third parties. No third-party analytics tools are used."
        ),
        "personal_data_categories": ["usage_logs", "feature_interaction_data"],
        "third_parties": [],
        "retention_period": "1 year",
        "is_required": False,
        "translations": {
            "hi": {
                "name": "उत्पाद विश्लेषण",
                "description": (
                    "ContraRed को बेहतर बनाने के लिए आंतरिक उपयोग ट्रैकिंग। "
                    "हम लॉग करते हैं कि आप कौन सी सुविधाओं का उपयोग करते हैं, स्कैन काउंट और प्रदर्शन मेट्रिक्स। "
                    "यह डेटा केवल हमारे सर्वर पर संग्रहीत है और कभी भी तीसरे पक्ष के साथ साझा नहीं किया जाता है।"
                ),
            }
        },
    },
    {
        "purpose_code": "error_monitoring",
        "name": "Error Monitoring",
        "description": (
            "Error tracking using Sentry to identify and fix bugs. The integration is configured "
            "to scrub personal data and not intentionally send email, contract text, or "
            "authentication tokens; residual diagnostic-data risk is monitored."
        ),
        "personal_data_categories": ["anonymised_error_context"],
        "third_parties": ["Sentry (US)"],
        "retention_period": "Up to 90 days, subject to the configured provider schedule",
        "is_required": False,
        "translations": {
            "hi": {
                "name": "त्रुटि निगरानी",
                "description": (
                    "बग्स की पहचान करने और ठीक करने के लिए Sentry का उपयोग करके त्रुटि ट्रैकिंग। "
                    "त्रुटियाँ भेजने से पहले सभी व्यक्तिगत पहचान योग्य जानकारी हटा दी जाती है।"
                ),
            }
        },
    },
    {
        "purpose_code": "sso_integration",
        "name": "Enterprise SSO",
        "description": (
            "Single Sign-On integration via WorkOS for enterprise customers. Your identity "
            "information (email, name, SSO provider ID) is shared with WorkOS to enable "
            "Azure AD, Okta, or Google Workspace authentication."
        ),
        "personal_data_categories": ["email", "name", "sso_provider_id"],
        "third_parties": ["WorkOS (US)"],
        "retention_period": "Duration of SSO configuration",
        "is_required": False,
        "translations": {
            "hi": {
                "name": "एंटरप्राइज SSO",
                "description": (
                    "एंटरप्राइज ग्राहकों के लिए WorkOS के माध्यम से सिंगल साइन-ऑन एकीकरण। "
                    "Azure AD, Okta, या Google Workspace प्रमाणीकरण सक्षम करने के लिए आपकी पहचान जानकारी WorkOS के साथ साझा की जाती है।"
                ),
            }
        },
    },
]

# Default privacy policy (v1)
DEFAULT_PRIVACY_POLICY = {
    "version": 2,
    "title": "ContraRed Privacy Policy v2.0",
    "language": "en",
    "content": """ContraRed Privacy Policy

Effective Date: July 2026

1. DATA CONTROLLER
ContraRed ("we", "us") processes your personal data as a Data Fiduciary under India's Digital Personal Data Protection Act, 2023 (DPDP Act).

2. PERSONAL DATA WE COLLECT
- Account data: Email address, name
- Contract data: Contract text submitted for analysis (processed in-memory, never stored permanently)
- Usage data: Feature usage logs, scan counts, performance metrics
- Payment data: Customer IDs and transaction references (payment details handled by Razorpay/Stripe)
- Technical data: IP address, browser type (for security and error monitoring)

3. PURPOSES OF PROCESSING
We process your data only for the specific purposes you have consented to. Each purpose can be independently controlled from your Privacy Settings.

4. THIRD-PARTY PROCESSORS
- Google Cloud Vertex AI (configured region): AI contract analysis and drafting
- Azure OpenAI (configured region): Alternative AI processing
- Razorpay (India): INR payment processing
- Stripe (US): International payment processing
- Sentry (US): Error monitoring (PII-stripped)
- WorkOS (US): Enterprise SSO (optional)

5. DATA RETENTION
- Account data: Duration of account + 90 days
- Contract text: Not stored (Zero Data Retention mode)
- Usage logs: 1 year
- Payment records: Applicable tax, accounting, chargeback, and dispute-retention schedule
- Consent evidence: Deployment retention policy; the 7-year minimum applies only if ContraRed is a registered Consent Manager

6. YOUR RIGHTS (DPDP Act Sections 11-14)
- Right to access your personal data
- Right to correction of inaccurate data
- Right to erasure when purpose is fulfilled
- Right to nominate a representative
- Right to grievance redressal

7. CROSS-BORDER TRANSFERS
Provider regions depend on the deployment configuration. Transfers are subject to current Government restrictions, Rule 15 requirements when effective, contractual safeguards, and any stricter applicable Indian sectoral law. Consent alone does not override a transfer restriction.

8. DATA SECURITY
We use transport encryption, role-based access control, hash-chained audit records, and field-level encryption when configured. Deployment-specific controls and residual risks are described in the security schedule.

9. GRIEVANCE OFFICER
For privacy concerns, use the Grievance Redressal section in account settings to contact our privacy contact or, where applicable, our Data Protection Officer.

10. CHANGES TO THIS POLICY
We will notify you of material changes via email or in-app notification. If a change introduces a new or incompatible consent-based purpose, we will request fresh affirmative consent before that processing begins.
""",
}


async def seed_consent_purposes(db: AsyncSession) -> None:
    """Seed version 2 purpose definitions without overwriting historical versions."""
    created_count = 0
    purpose_version = 2

    for purpose_data in CONSENT_PURPOSES:
        # Keep the old definition for auditability and add a new active version.
        result = await db.execute(
            select(ConsentPurpose)
            .where(
                ConsentPurpose.purpose_code == purpose_data["purpose_code"],
                ConsentPurpose.version == purpose_version,
            )
            .limit(1)
        )
        existing = result.scalar()

        if not existing:
            prior_result = await db.execute(
                select(ConsentPurpose).where(
                    ConsentPurpose.purpose_code == purpose_data["purpose_code"],
                    ConsentPurpose.is_active.is_(True),
                )
            )
            for prior in prior_result.scalars().all():
                prior.is_active = False

            purpose = ConsentPurpose(**purpose_data, version=purpose_version)
            db.add(purpose)
            created_count += 1

    if created_count > 0:
        await db.commit()
        logger.info("Seeded %d consent purposes", created_count)
    else:
        logger.debug("All consent purposes already exist")


async def seed_consent_policy(db: AsyncSession) -> None:
    """Seed the current privacy policy version if it doesn't exist."""
    result = await db.execute(
        select(ConsentPolicy)
        .where(
            ConsentPolicy.version == DEFAULT_PRIVACY_POLICY["version"],
            ConsentPolicy.language == DEFAULT_PRIVACY_POLICY["language"],
        )
        .limit(1)
    )
    existing = result.scalar()

    if not existing:
        content = DEFAULT_PRIVACY_POLICY["content"]
        policy = ConsentPolicy(
            version=DEFAULT_PRIVACY_POLICY["version"],
            title=DEFAULT_PRIVACY_POLICY["title"],
            content=content,
            language=DEFAULT_PRIVACY_POLICY["language"],
            checksum=ConsentPolicy.compute_checksum(content),
        )
        db.add(policy)
        await db.commit()
        logger.info("Seeded default privacy policy v%d", policy.version)
    else:
        logger.debug(
            "Privacy policy v%d already exists",
            DEFAULT_PRIVACY_POLICY["version"],
        )


async def seed_all_consent_defaults(db: AsyncSession) -> None:
    """Seed all consent defaults. Called during app startup."""
    await seed_consent_purposes(db)
    await seed_consent_policy(db)
