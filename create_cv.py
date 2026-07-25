"""
CV GENERATOR - Muhammad Dawam
Generate professional CV berdasarkan data yang terkumpul
"""
import os


def create_cv_text():
    """Buat CV dalam format teks"""
    cv_content = """
================================================================================
                           MUHAMMAD DAWAM
  Web3 Growth Marketer | DeFi Business Developer | Community & Partnership Specialist
================================================================================

CONTACT INFORMATION
-------------------
Email:      muhdawam94@gmail.com
Phone:      +62 812-3185-9894
LinkedIn:   linkedin.com/in/muh-dawam
GitHub:     github.com/muhdawam94
Portfolio:  muhdawam94.wixsite.com/muhdawam
Location:   Surabaya, Indonesia (Remote Worldwide Available)
Timezone:   UTC+7 (WIB) - Flexible for global teams

================================================================================

PROFESSIONAL SUMMARY
---------------------
Results-driven Growth Marketing and Business Development professional with 8+ years of
experience in e-commerce, digital products, and community-driven growth. Proven track
record of scaling user acquisition, managing marketplace ecosystems, and driving revenue
across international markets. Passionate about Web3, DeFi, and decentralized ecosystems.
Experienced in remote-first environments with distributed global teams. Seeking Growth
Marketing, Community Management, Partnership, and Business Development roles in Web3,
DeFi, and blockchain startups.

Unique Value: I combine traditional growth marketing expertise with deep understanding
of Web3 ecosystems - I can bridge the gap between Web2 customer acquisition and Web3
community-driven growth.

================================================================================

CORE SKILLS
-----------
Web3 & DeFi:
  • Web3 Growth Marketing & User Acquisition
  • Community Management (Discord, Telegram, Twitter/X)
  • DAO Operations & Governance Participation
  • DeFi Protocol Understanding (DEX, Lending, Staking, Yield)
  • Token Economy & Incentive Design
  • NFT Community Building & Marketplace Management
  • On-chain Analytics & Wallet Tracking

Growth Marketing:
  • Digital Marketing Strategy & Execution
  • SEO/SEM & Content Marketing
  • Email Marketing & Lifecycle Campaigns
  • Data Reporting & Analytics
  • A/B Testing & Conversion Optimization

Business Development:
  • B2B Sales & Lead Generation
  • Account Management & Customer Success
  • Partnership Development & BD Outreach
  • CRM Systems & Pipeline Management
  • Remote Team Collaboration

Community & Partnerships:
  • Discord/Telegram Community Growth
  • Twitter/X Growth & Engagement
  • Influencer & KOL Partnerships
  • Ambassador Program Management
  • Event Coordination (AMAs, Twitter Spaces)

Design & Tools:
  • Figma, Adobe Photoshop, Canva
  • Google Workspace, Microsoft Office
  • Amazon/eBay/Etsy/Walmart Seller Tools
  • Analytics Dashboards & CRM Systems
  • Notion, Slack, Asana (Remote Work Tools)

================================================================================

PROFESSIONAL EXPERIENCE
------------------------

BUSINESS MARKETING SUPERVISOR | PT. Yoewono Jaya Mandiri | Jan 2025 - Jul 2025
(E-commerce & B2B Sales)

Key Achievements:
  • Developed and executed B2B sales strategies for PET resin products
  • Conducted prospecting, negotiations, presentations, and relationship management
  • Produced company profiles, marketing materials, and social media content
  • Successfully closed a two-container sales agreement within the first three months
  • Managed cross-functional team collaboration across remote settings

Relevance to Web3:
  • Experience in B2B sales translates directly to Web3 partnership development
  • Skilled in stakeholder management - essential for protocol partnerships
  • Content creation experience applicable to Web3 thought leadership

--------------------------------------------------------------------------------

SALES MARKETING EXECUTIVE | PT. Indopopanen Sejahtera | Jun 2024 - Dec 2024
(Digital Marketing & Growth)

Key Achievements:
  • Developed digital marketing strategies for agricultural products
  • Expanded retail partnerships and increased market exposure
  • Managed daily sales reporting, cash-flow tracking, and performance monitoring
  • Generated significant revenue growth within a short period

Relevance to Web3:
  • Growth marketing strategies directly applicable to DeFi user acquisition
  • Partnership expansion experience valuable for ecosystem growth
  • Data-driven decision making aligns with Web3 analytics culture

--------------------------------------------------------------------------------

FREELANCE UI/UX DESIGNER | Jun 2022 - Mar 2024
(Design & Product)

Key Achievements:
  • Designed responsive website interfaces and conversion-focused landing pages
  • Created wireframes, user flows, and prototypes using Figma
  • Delivered user-centered design solutions for clients across industries
  • Collaborated with distributed teams across different time zones

Relevance to Web3:
  • UX design experience valuable for dApp interface optimization
  • Understanding of user psychology applies to token economics
  • Remote collaboration experience essential for Web3 work culture

--------------------------------------------------------------------------------

DIGITAL MARKETING SUPERVISOR | PT. Getei Teknologi Utama | Sep 2013 - Mar 2022
(E-commerce & Marketplace Operations)

Key Achievements:
  • Managed operations across eBay, Amazon, Etsy, Walmart, PayPal, and email channels
  • Led digital marketing initiatives and supervised marketing team members
  • Resolved customer issues, account risks, and operational challenges
  • Increased company profit by approximately 20% within a quarter through optimization initiatives

Relevance to Web3:
  • Multi-platform management experience applies to Web3 ecosystem management
  • Customer success expertise translates to community management
  • Operational optimization skills valuable for protocol governance

================================================================================

WEB3 PROJECTS & INITIATIVES
-----------------------------

1. WEB3 JOB AUTOMATION SYSTEM
   • Built automated job search and application system for Web3 positions
   • Integrated multiple job boards (Greenhouse, Lever, Ashby) for remote opportunities
   • Developed AI-powered form filling and cover letter generation
   • Implemented Telegram notifications for real-time job alerts

2. CRYPTO & DEFI RESEARCH
   • Active participant in DeFi protocols across multiple chains
   • Experience with DEX trading, liquidity provision, and yield farming
   • Knowledge of token economics, governance systems, and DAO structures
   • Regular engagement with Web3 communities on Twitter/X and Discord

3. WEB3 COMMUNITY CONTRIBUTION
   • Active member of various Web3 Discord communities
   • Participated in governance discussions and proposal voting
   • Provided feedback on DeFi protocols and dApp UX
   • Connected with Web3 founders and builders globally

================================================================================

SELECTED ACHIEVEMENTS
----------------------
  • Increased company profitability through marketing optimization and operational improvements
  • Managed international marketplace operations serving global customers
  • Built and maintained long-term B2B customer relationships
  • Successfully negotiated and closed high-value business deals
  • Delivered freelance design projects focused on usability and conversion
  • Developed Web3 automation tools for job searching and application management

================================================================================

EDUCATION & CERTIFICATIONS
---------------------------
Formal Education:
  • Bachelor-Level Studies - STAI YPBWI (2013-2017)

Web3 & Professional Development:
  • Web3 Growth Marketing (Online Learning)
  • DeFi Fundamentals & Protocol Analysis
  • Community Management Best Practices
  • Digital Marketing Analytics & Growth Hacking
  • Remote Team Leadership & Collaboration

================================================================================

TARGET REMOTE ROLES (WEB3 FOCUSED)
------------------------------------
  • Web3 Growth Marketing Specialist
  • DeFi Business Development Representative
  • Community Manager (Discord/Telegram)
  • Partnership & Ecosystem Development
  • DAO Operations & Governance
  • Customer Success Manager (Web3)
  • Token Economy & Incentive Designer
  • Web3 Content & Marketing Manager

================================================================================

LANGUAGES
---------
  • Indonesian - Native
  • English - Professional working proficiency

================================================================================

INTERESTS
---------
  • DeFi protocol innovation and governance
  • Web3 adoption in Southeast Asia
  • DAO operations and community management
  • Token economics and incentive design
  • Decentralized identity and reputation systems
  • Open source contribution to Web3 projects

================================================================================
                              END OF CV
================================================================================
"""
    return cv_content


def save_cv():
    """Simpan CV ke file"""
    cv_content = create_cv_text()
    
    # Save as text file
    cv_file = os.path.join(os.path.dirname(__file__), "cv.txt")
    with open(cv_file, 'w', encoding='utf-8') as f:
        f.write(cv_content)
    
    print(f"[OK] CV created: {cv_file}")
    print("[INFO] Review the CV and make any necessary adjustments")
    print("[INFO] Convert to PDF using online tools or MS Word")
    
    return cv_file


if __name__ == "__main__":
    save_cv()
    print("\n" + create_cv_text())