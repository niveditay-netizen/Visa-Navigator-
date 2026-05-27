import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
import time
import os
import io

POLICY_MANUAL_URLS = [
    # Volume 2 Part H: H-1B Specialty Workers
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-5",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-6",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-7",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-8",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-9",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-10",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-11",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-12",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-13",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-14",
    "https://www.uscis.gov/policy-manual/volume-2-part-h-chapter-15",
    # Volume 2 Part L: L-1 Intracompany Transferees
    "https://www.uscis.gov/policy-manual/volume-2-part-l-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-l-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-l-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-l-chapter-4",
    # Volume 2 Part M: O-1 Extraordinary Ability
    "https://www.uscis.gov/policy-manual/volume-2-part-m-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-m-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-m-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-m-chapter-4",
    # Volume 2 Part A: General (Extension, Change of Status)
    "https://www.uscis.gov/policy-manual/volume-2-part-a-chapter-4",
    # Volume 6 Part F: Employment-Based Immigrants (EB-1/2/3)
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-5",
    # Volume 7: Adjustment of Status
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-6",
    "https://www.uscis.gov/policy-manual/volume-7-part-f-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-f-chapter-2",
    # Volume 10: Employment Authorization
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-3",
]

FORM_INSTRUCTION_PDFS = [
    {
        "url": "https://www.uscis.gov/sites/default/files/document/forms/i-140instr.pdf",
        "filename": "i-140-instructions.pdf",
        "title": "Form I-140 Instructions (Immigrant Petition for Alien Workers)",
    },
    {
        "url": "https://www.uscis.gov/sites/default/files/document/forms/i-485instr.pdf",
        "filename": "i-485-instructions.pdf",
        "title": "Form I-485 Instructions (Adjustment of Status)",
    },
    {
        "url": "https://www.uscis.gov/sites/default/files/document/forms/i-485supjinstr.pdf",
        "filename": "i-485-supplement-j-instructions.pdf",
        "title": "Form I-485 Supplement J Instructions (Job Portability)",
    },
    {
        "url": "https://www.uscis.gov/sites/default/files/document/forms/i-765instr.pdf",
        "filename": "i-765-instructions.pdf",
        "title": "Form I-765 Instructions (Employment Authorization)",
    },
    {
        "url": "https://www.uscis.gov/sites/default/files/document/forms/i-129instr.pdf",
        "filename": "i-129-instructions.pdf",
        "title": "Form I-129 Instructions (Petition for Nonimmigrant Worker)",
    },
    {
        "url": "https://www.uscis.gov/sites/default/files/document/forms/i-539instr.pdf",
        "filename": "i-539-instructions.pdf",
        "title": "Form I-539 Instructions (Extend/Change Nonimmigrant Status)",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0; +educational-use)"
}


def scrape_policy_page(url: str, output_dir: str):
    response = httpx.get(url, follow_redirects=True, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Try multiple selectors in priority order
    content = (
        soup.find("div", class_="field--name-body")
        or soup.find("div", {"id": "main-content"})
        or soup.find("main")
        or soup.find("article")
    )

    if not content:
        print(f"  WARNING: No content found for {url}")
        return 0

    text = content.get_text(separator="\n", strip=True)

    if len(text) < 200:
        print(f"  WARNING: Very short content ({len(text)} chars) for {url}")

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else url.split("/")[-1]

    slug = url.replace("https://www.uscis.gov/policy-manual/", "").replace("/", "-")
    filename = slug + ".txt"

    output = f"""---
source: USCIS Policy Manual
title: {title}
url: {url}
---

{text}
"""
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"  OK  {filename} ({len(text):,} chars)")
    return len(text)


def download_pdf(url: str, filename: str, title: str, output_dir: str):
    response = httpx.get(url, follow_redirects=True, headers=HEADERS, timeout=60)
    response.raise_for_status()

    reader = PdfReader(io.BytesIO(response.content))
    pages_text = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            pages_text.append(t)
    text = "\n".join(pages_text)

    if len(text) < 200:
        print(f"  WARNING: Very short PDF text ({len(text)} chars) for {filename}")

    txt_filename = filename.replace(".pdf", ".txt")
    output = f"""---
source: USCIS Form Instructions
title: {title}
url: {url}
---

{text}
"""
    txt_path = os.path.join(output_dir, txt_filename)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"  OK  {txt_filename} ({len(text):,} chars)")
    return len(text)


if __name__ == "__main__":
    output_dir = os.path.join(
        os.path.dirname(__file__), "..", "backend", "data", "uscis_docs"
    )
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Output directory: {output_dir}\n")

    errors = []
    total_chars = 0

    print(f"=== Scraping {len(POLICY_MANUAL_URLS)} Policy Manual pages ===")
    for url in POLICY_MANUAL_URLS:
        slug = url.split("/")[-1]
        print(f"[{slug}]")
        try:
            chars = scrape_policy_page(url, output_dir)
            total_chars += chars
        except Exception as e:
            print(f"  ERROR: {e}")
            errors.append((url, str(e)))
        time.sleep(1.5)

    print(f"\n=== Downloading {len(FORM_INSTRUCTION_PDFS)} Form Instruction PDFs ===")
    for pdf in FORM_INSTRUCTION_PDFS:
        print(f"[{pdf['filename']}]")
        try:
            chars = download_pdf(pdf["url"], pdf["filename"], pdf["title"], output_dir)
            total_chars += chars
        except Exception as e:
            print(f"  ERROR: {e}")
            errors.append((pdf["url"], str(e)))
        time.sleep(1.5)

    files = os.listdir(output_dir)
    print(f"\n{'='*50}")
    print(f"Done. {len(files)} files, ~{total_chars:,} total chars")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for url, err in errors:
            print(f"  {url}: {err}")
    print(f"{'='*50}")
