from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(30, 60, 120)
        self.cell(0, 10, 'PatchCourt Activation Instructions', new_x="LMARGIN", new_y="NEXT", align='C')
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    def section_title(self, title):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(30, 60, 120)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_title(self, title):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def code_block(self, code):
        self.set_font('Courier', '', 9)
        self.set_fill_color(245, 245, 245)
        self.set_draw_color(200, 200, 200)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        y = self.get_y()
        lines = code.split('\n')
        line_h = 5
        h = len(lines) * line_h + 6
        self.rect(x, y, 190, h, style='DF')
        self.set_xy(x + 3, y + 3)
        for line in lines:
            self.cell(0, line_h, line, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def bullet(self, text, indent=15):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(5, 5.5, '-')
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def table_row(self, col1, col2, header=False):
        if header:
            self.set_font('Helvetica', 'B', 9)
            self.set_fill_color(30, 60, 120)
            self.set_text_color(255, 255, 255)
        else:
            self.set_font('Helvetica', '', 9)
            self.set_fill_color(250, 250, 250)
            self.set_text_color(40, 40, 40)
        self.cell(55, 7, col1, border=1, fill=True)
        self.cell(0, 7, col2, border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# Title page
pdf.set_font('Helvetica', 'B', 24)
pdf.set_text_color(30, 60, 120)
pdf.ln(40)
pdf.cell(0, 15, 'PatchCourt', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.set_font('Helvetica', '', 16)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 10, 'Activation & Usage Instructions', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.ln(20)
pdf.set_font('Helvetica', 'I', 11)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 8, 'Multi-agent, evidence-tiered AI code-review system', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.cell(0, 8, 'for GitHub Pull Requests', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.ln(40)
pdf.set_font('Helvetica', '', 10)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 8, 'Generated for local deployment', new_x="LMARGIN", new_y="NEXT", align='C')

# Page 2 - Prerequisites
pdf.add_page()
pdf.section_title('1. Prerequisites')
pdf.bullet('Docker & Docker Compose installed')
pdf.bullet('(Optional) SonarQube running on localhost:9000 for Live tab')
pdf.bullet('(Optional) GitHub token + LLM API keys for real reviews')

pdf.section_title('2. Clone & Configure')
pdf.code_block('cd /path/to/patchcourt\ncp .env.example .env\n# Edit .env if you want real LLM/GitHub/SonarQube; leave as-is for offline mock mode')

pdf.section_title('3. Build & Start Core Stack')
pdf.code_block('docker compose up -d --build api postgres redis qdrant')
pdf.body_text('Wait for health checks (~30s):')
pdf.code_block('docker compose ps  # all should show "healthy" or "Up"')
pdf.body_text('Verify API:')
pdf.code_block('curl http://localhost:8000/health\n# {"status":"ok"}')

pdf.section_title('4. Start Dashboard')
pdf.code_block('docker compose --profile dashboard up -d --build dashboard')
pdf.body_text('Open: http://localhost:3000')

pdf.section_title('5. Optional Services')
pdf.table_row('Service', 'Command', header=True)
pdf.table_row('Background Worker', 'docker compose --profile worker up -d worker')
pdf.table_row('Sandbox Image', 'docker compose --profile tools build sandbox')

pdf.section_title('6. Useful Commands')
pdf.table_row('Action', 'Command', header=True)
pdf.table_row('View logs', 'docker compose logs -f api')
pdf.table_row('Stop all', 'docker compose down')
pdf.table_row('Stop + remove volumes', 'docker compose down -v')
pdf.table_row('Restart API', 'docker compose restart api')
pdf.table_row('Run offline demo', 'Click "Offline Demo" in top-bar')
pdf.table_row('Run real review', 'Enter PR URL + click "Run Review"')

pdf.section_title('7. Default Ports')
pdf.table_row('Service', 'Port', header=True)
pdf.table_row('Dashboard', '3000')
pdf.table_row('API', '8000')
pdf.table_row('Qdrant', '6333')
pdf.table_row('SonarQube (external)', '9000')

pdf.section_title('8. Default Modes')
pdf.bullet('Mock (default): Fully offline, no keys needed')
pdf.bullet('Real review: Add GITHUB_TOKEN, LLM_API_KEY, LLM_PROVIDER=gemini|openai|claude')
pdf.bullet('SonarQube Live: Needs SonarQube on host.docker.internal:9000')

pdf.section_title('9. Default Environment Variables')
pdf.table_row('Variable', 'Default / Purpose', header=True)
pdf.table_row('LLM_PROVIDER', 'mock | openai | claude | gemini | ollama (default: mock)')
pdf.table_row('LLM_API_KEY', 'Required for non-mock providers')
pdf.table_row('GITHUB_TOKEN', 'For private repos / higher rate limits')
pdf.table_row('SONAR_URL', 'http://localhost:9000 (baseline)')
pdf.table_row('SONAR_HOST_URL', 'http://host.docker.internal:9000 (Live tab, inside Docker)')

output_path = os.path.expanduser('~/Downloads/execInst.pdf')
pdf.output(output_path)
print(f'PDF saved to: {output_path}')