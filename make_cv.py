"""
Make CV PDF from environment variables (no hardcoded personal data).
Output: Muhammad_Dawam_CV.pdf in the repo root.
"""
import os
from fpdf import FPDF

OUTPUT = os.path.join(os.path.dirname(__file__), "Muhammad_Dawam_CV.pdf")


class CV_PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(99, 102, 241)
        self.cell(0, 11, os.getenv('FULL_NAME', 'FULL NAME').upper(),
                  new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font('Helvetica', '', 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 7, os.getenv('DESIRED_ROLE', ''), new_x="LMARGIN",
                  new_y="NEXT", align='C')
        self.ln()
        self.set_font('Helvetica', '', 9)
        self.set_text_color(60, 60, 60)
        parts = [os.getenv('EMAIL'), os.getenv('PHONE'), os.getenv('LINKEDIN')]
        contact = ' | '.join([p for p in parts if p])
        if contact:
            self.cell(0, 5, contact, new_x="LMARGIN", new_y="NEXT", align='C')
        parts2 = [os.getenv('GITHUB'), os.getenv('PORTFOLIO')]
        contact2 = ' | '.join([p for p in parts2 if p])
        if contact2:
            self.cell(0, 5, contact2, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln()
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
            self.cell(5, 5, '-')
            self.multi_cell(170, 5, f' {item}')
        self.ln()


def _split_list(value: str) -> list:
    return [s.strip() for s in value.split(',') if s.strip()]


def make_cv():
    role = os.getenv('DESIRED_ROLE', 'Web3 Professional')
    years = os.getenv('YEARS_EXPERIENCE', '')
    work_type = os.getenv('WORK_TYPE', '')
    location = os.getenv('LOCATION', '') or os.getenv('CITY', '')
    country = os.getenv('COUNTRY', '')

    pdf = CV_PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.section_title('Professional Summary')
    summary = (
        f"Results-driven professional{(' with ' + years + ' of experience') if years else ''} "
        f"seeking a {role} role in Web3, DeFi, and blockchain. Proven ability to combine "
        f"hands-on technical execution with growth, communication, and cross-functional "
        f"collaboration. Experienced in remote-first environments with distributed global "
        f"teams, and passionate about decentralized ecosystems."
    )
    pdf.body_text(summary)

    skills = _split_list(os.getenv('SKILLS', ''))
    if skills:
        pdf.section_title('Core Skills')
        pdf.bullet_list(skills)

    pdf.section_title('Work Preferences')
    prefs = []
    if work_type:
        prefs.append(f"Work type: {work_type}")
    if os.getenv('EXPECTED_SALARY'):
        prefs.append(f"Expected salary: {os.getenv('EXPECTED_SALARY')}")
    if os.getenv('AVAILABILITY'):
        prefs.append(f"Availability: {os.getenv('AVAILABILITY')}")
    loc_parts = [p for p in [location, country] if p]
    if loc_parts:
        prefs.append(f"Location: {', '.join(loc_parts)}")
    pdf.bullet_list(prefs)

    pdf.section_title('Web3 Projects & Initiatives')
    pdf.subsection_title('Web3 Job Automation System')
    pdf.bullet_list([
        'Built automated job search and application system for Web3 positions',
        'Integrated multiple job boards (Greenhouse, Lever, Ashby) for remote opportunities',
        'Developed AI-powered form filling and cover letter generation',
        'Implemented Telegram notifications for real-time job alerts',
    ])
    pdf.subsection_title('Crypto & DeFi Research')
    pdf.bullet_list([
        'Active participant in DeFi protocols across multiple chains',
        'Experience with DEX trading, liquidity provision, and yield farming',
        'Knowledge of token economics, governance systems, and DAO structures',
        'Regular engagement with Web3 communities on Twitter/X and Discord',
    ])

    education = os.getenv('EDUCATION', '')
    if education:
        pdf.section_title('Education')
        pdf.bullet_list([education])

    languages = _split_list(os.getenv('LANGUAGES', ''))
    if languages:
        pdf.section_title('Languages')
        pdf.bullet_list(languages)

    pdf.output(OUTPUT)
    print(f"[OK] PDF created: {OUTPUT}")
    print(f"[INFO] File size: {os.path.getsize(OUTPUT) / 1024:.1f} KB")
    return OUTPUT


if __name__ == "__main__":
    make_cv()
