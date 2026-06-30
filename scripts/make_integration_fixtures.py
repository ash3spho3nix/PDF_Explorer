from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader, PdfWriter


def create_pdf(path: Path, title: str, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(path), pagesize=letter)
    c.setTitle(title)
    c.setAuthor('Test Author')
    c.drawString(72, 720, text)
    c.save()


def create_encrypted_pdf(source: Path, target: Path):
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt('secret')
    with open(target, 'wb') as f:
        writer.write(f)


def main():
    root = Path(__file__).resolve().parent.parent / 'tests' / 'integration' / 'fixtures' / 'sample_pdfs'
    create_pdf(root / 'invoice_001.pdf', 'Invoice 001', 'Invoice Amount Due: $100')
    create_pdf(root / 'resume_001.pdf', 'Resume 001', 'Experience')
    create_pdf(root / 'dup_a.pdf', 'Duplicate A', 'Duplicate file content')
    create_pdf(root / 'dup_b.pdf', 'Duplicate B', 'Duplicate file content')
    create_pdf(root / 'notes.pdf', 'Notes', 'Some generic note text.')

    corrupted_path = root / 'corrupted.pdf'
    with open(corrupted_path, 'wb') as f:
        f.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\n')

    create_encrypted_pdf(root / 'notes.pdf', root / 'encrypted.pdf')
    print(f'Created fixtures in {root}')


if __name__ == '__main__':
    main()
