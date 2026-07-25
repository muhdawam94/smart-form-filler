"""
CV to PDF Converter - Muhammad Dawam
Convert cv.txt to professional PDF format
"""
import os
from fpdf import FPDF


class CV_PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(99, 102, 241)  # Purple accent
        self.cell(0, 12, 'MUHAMMAD DAWAM', new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font('Helvetica', '', 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, 'Web3 Growth Marketer | DeFi Business Developer | Community & Partnership Specialist', new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln()
        
        # Contact info
        self.set_font('Helvetica', '', 9)
        self.set_text_color(60, 60, 60)
        contact = 'muhdawam94@gmail.com | +62 812-3185-9894 | linkedin.com/in/muh-dawam'
        self.cell(0, 5, contact, new_x="LMARGIN", new_y="NEXT", align='C')
        contact2 = 'github.com/muhdawam94 | muhdawam94.wixsite.com/muhdawam | linktr.ee/muhdawam'
        self.cell(0, 5, contact2, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln()
        
        # Line separator
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln()
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')
    
    def section_title(self, title):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(99, 102, 241)
        self.cell(0, 8, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln()
    
    def subsection_title(self, title, subtitle=None):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(40, 40, 40)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            self.set_font('Helvetica', 'I', 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, subtitle, new_x="LMARGIN", new_y="NEXT")
        self.ln()
    
    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, text)
        self.ln()
    
    def bullet_list(self, items):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(50, 50, 50)
        for item in items:
            self.cell(8, 5, '')
            x = self.get_x()
            self.cell(5, 5, '-')
            self.multi_cell(170, 5, f' {item}')
        self.ln()
    
    def skill_category(self, title, skills):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(99, 102, 241)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.set_font('Helvetica', '', 9)
        self.set_text_color(50, 50, 50)
        skills_text = ' | '.join(skills)
        self.multi_cell(0, 5, skills_text)
        self.ln()


def convert_cv_to_pdf():
    """Convert CV text to PDF"""
    cv_file = os.path.join(os.path.dirname(__file__), "cv.txt")
    pdf_file = os.path.join(os.path.dirname(__file__), "Muhammad_Dawam_CV.pdf")
    
    # Read CV content
    with open(cv_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create PDF
    pdf = CV_PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Professional Summary
    pdf.section_title('Professional Summary')
    summary = (
        "Results-driven Growth Marketing and Business Development professional with 8+ years of "
        "experience in e-commerce, digital products, and community-driven growth. Proven track "
        "record of scaling user acquisition, managing marketplace ecosystems, and driving revenue "
        "across international markets. Passionate about Web3, DeFi, and decentralized ecosystems. "
        "Experienced in remote-first environments with distributed global teams. Seeking Growth "
        "Marketing, Community Management, Partnership, and Business Development roles in Web3, "
        "DeFi, and blockchain startups."
    )
    pdf.body_text(summary)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 6, 'Unique Value:', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    value = (
        "I combine traditional growth marketing expertise with deep understanding of Web3 "
        "ecosystems - I can bridge the gap between Web2 customer acquisition and Web3 "
        "community-driven growth."
    )
    pdf.multi_cell(0, 5, value)
    pdf.ln(4)
    
    # Core Skills
    pdf.section_title('Core Skills')
    
    pdf.skill_category('Web3 & DeFi:', [
        'Web3 Growth Marketing & User Acquisition',
        'Community Management (Discord, Telegram, Twitter/X)',
        'DAO Operations & Governance Participation',
        'DeFi Protocol Understanding (DEX, Lending, Staking, Yield)',
        'Token Economy & Incentive Design'
    ])
    
    pdf.skill_category('Growth Marketing:', [
        'Digital Marketing Strategy & Execution',
        'SEO/SEM & Content Marketing',
        'Email Marketing & Lifecycle Campaigns',
        'Data Reporting & Analytics',
        'A/B Testing & Conversion Optimization'
    ])
    
    pdf.skill_category('Business Development:', [
        'B2B Sales & Lead Generation',
        'Account Management & Customer Success',
        'Partnership Development & BD Outreach',
        'CRM Systems & Pipeline Management',
        'Remote Team Collaboration'
    ])
    
    pdf.skill_category('Community & Design:', [
        'Discord/Telegram Community Growth',
        'Twitter/X Growth & Engagement',
        'Influencer & KOL Partnerships',
        'Figma, Adobe Photoshop, Canva',
        'Notion, Slack, Asana (Remote Work Tools)'
    ])
    
    # Professional Experience
    pdf.section_title('Professional Experience')
    
    # Job 1
    pdf.subsection_title(
        'Business Marketing Supervisor | PT. Yoewono Jaya Mandiri',
        'Jan 2025 - Jul 2025 | E-commerce & B2B Sales'
    )
    pdf.bullet_list([
        'Developed and executed B2B sales strategies for PET resin products',
        'Conducted prospecting, negotiations, presentations, and relationship management',
        'Produced company profiles, marketing materials, and social media content',
        'Successfully closed a two-container sales agreement within the first three months',
        'Managed cross-functional team collaboration across remote settings'
    ])
    
    # Job 2
    pdf.subsection_title(
        'Sales Marketing Executive | PT. Indopopanen Sejahtera',
        'Jun 2024 - Dec 2024 | Digital Marketing & Growth'
    )
    pdf.bullet_list([
        'Developed digital marketing strategies for agricultural products',
        'Expanded retail partnerships and increased market exposure',
        'Managed daily sales reporting, cash-flow tracking, and performance monitoring',
        'Generated significant revenue growth within a short period'
    ])
    
    # Job 3
    pdf.subsection_title(
        'Freelance UI/UX Designer',
        'Jun 2022 - Mar 2024 | Design & Product'
    )
    pdf.bullet_list([
        'Designed responsive website interfaces and conversion-focused landing pages',
        'Created wireframes, user flows, and prototypes using Figma',
        'Delivered user-centered design solutions for clients across industries',
        'Collaborated with distributed teams across different time zones'
    ])
    
    # Job 4
    pdf.subsection_title(
        'Digital Marketing Supervisor | PT. Getei Teknologi Utama',
        'Sep 2013 - Mar 2022 | E-commerce & Marketplace Operations'
    )
    pdf.bullet_list([
        'Managed operations across eBay, Amazon, Etsy, Walmart, PayPal, and email channels',
        'Led digital marketing initiatives and supervised marketing team members',
        'Resolved customer issues, account risks, and operational challenges',
        'Increased company profit by approximately 20% within a quarter'
    ])
    
    # Web3 Projects
    pdf.section_title('Web3 Projects & Initiatives')
    
    pdf.subsection_title('Web3 Job Automation System')
    pdf.bullet_list([
        'Built automated job search and application system for Web3 positions',
        'Integrated multiple job boards (Greenhouse, Lever, Ashby) for remote opportunities',
        'Developed AI-powered form filling and cover letter generation',
        'Implemented Telegram notifications for real-time job alerts'
    ])
    
    pdf.subsection_title('Crypto & DeFi Research')
    pdf.bullet_list([
        'Active participant in DeFi protocols across multiple chains',
        'Experience with DEX trading, liquidity provision, and yield farming',
        'Knowledge of token economics, governance systems, and DAO structures',
        'Regular engagement with Web3 communities on Twitter/X and Discord'
    ])
    
    pdf.subsection_title('Web3 Community Contribution')
    pdf.bullet_list([
        'Active member of various Web3 Discord communities',
        'Participated in governance discussions and proposal voting',
        'Provided feedback on DeFi protocols and dApp UX',
        'Connected with Web3 founders and builders globally'
    ])
    
    # Education
    pdf.section_title('Education & Certifications')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 6, 'Formal Education:', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 5, 'Bachelor-Level Studies - STAI YPBWI (2013-2017)', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 6, 'Web3 & Professional Development:', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.bullet_list([
        'Web3 Growth Marketing (Online Learning)',
        'DeFi Fundamentals & Protocol Analysis',
        'Community Management Best Practices',
        'Digital Marketing Analytics & Growth Hacking',
        'Remote Team Leadership & Collaboration'
    ])
    
    # Languages
    pdf.section_title('Languages')
    pdf.bullet_list([
        'Indonesian - Native',
        'English - Professional working proficiency'
    ])
    
    # Target Roles
    pdf.section_title('Target Remote Roles (Web3 Focused)')
    pdf.bullet_list([
        'Web3 Growth Marketing Specialist',
        'DeFi Business Development Representative',
        'Community Manager (Discord/Telegram)',
        'Partnership & Ecosystem Development',
        'DAO Operations & Governance',
        'Customer Success Manager (Web3)',
        'Token Economy & Incentive Designer',
        'Web3 Content & Marketing Manager'
    ])
    
    # Save PDF
    pdf.output(pdf_file)
    print(f"[OK] PDF created: {pdf_file}")
    print(f"[INFO] File size: {os.path.getsize(pdf_file) / 1024:.1f} KB")
    print("[INFO] Ready to use for job applications!")
    
    return pdf_file


if __name__ == "__main__":
    convert_cv_to_pdf()