# backend/scrapers/nha_scraper.py

import asyncio
import os
import re
import time
import urllib.parse
import aiohttp

from playwright.async_api import async_playwright
from backend.database import insert_tender_record
from backend.utils.pdf_parser import parse_and_store_boq

NHA_TENDERS_URL = "https://ebidding.nha.gov.pk/Web/Tenders"


# -----------------------------------------------
# PDF Downloader
# -----------------------------------------------
async def _download_pdf(session: aiohttp.ClientSession, url: str, dest_path: str):
    async with session.get(url, timeout=60) as resp:
        resp.raise_for_status()
        data = await resp.read()
        with open(dest_path, "wb") as f:
            f.write(data)


# -----------------------------------------------
# Extract year from title
# -----------------------------------------------
def extract_year_from_text(text):
    m = re.search(r"20\d{2}", text)
    if m:
        return int(m.group(0))

    m2 = re.search(r"(20\d{2})\D+(?:\d{2})", text)
    if m2:
        return int(m2.group(1))

    return 2025


# -----------------------------------------------
# Extract tender rows from ONE page
# -----------------------------------------------
async def scrape_page(page, session, save_pdfs_to):
    rows = await page.query_selector_all("table tbody tr")

    for r in rows:
        try:
            tds = await r.query_selector_all("td")
            vals = [await td.inner_text() for td in tds]

            tender_no = vals[0].strip() if len(vals) > 0 else None
            title = vals[1].strip() if len(vals) > 1 else ""
            region = vals[2].strip() if len(vals) > 2 else None
            closing = vals[3].strip() if len(vals) > 3 else None

            link = await r.query_selector("a[href$='.pdf']")
            pdf_path = None

            if link and tender_no:
                href = await link.get_attribute("href")
                if href:
                    pdf_url = urllib.parse.urljoin(NHA_TENDERS_URL, href)
                    local_name = os.path.join(save_pdfs_to, f"nha_{tender_no}.pdf")

                    try:
                        await _download_pdf(session, pdf_url, local_name)
                        pdf_path = local_name
                        print(f"[OK] PDF downloaded: {local_name}")
                    except Exception as e:
                        print("[ERR] PDF fetch failed:", e)

            tender = {
                "source": "NHA",
                "external_id": tender_no,
                "title": title,
                "department": "NHA",
                "location": region,
                "published_date": None,
                "closing_date": closing,
                "pdf_path": pdf_path
            }

            tid = insert_tender_record(tender)

            if pdf_path:
                try:
                    year = extract_year_from_text(title)
                    parse_and_store_boq(pdf_path, tid, tender_year=year)
                except Exception as e:
                    print("[ERR] BOQ parse failed:", e)

            await asyncio.sleep(0.25)

        except Exception as e:
            print("[ERR] Row parsing failed:", e)


# -----------------------------------------------
# Full scrape with pagination handling
# -----------------------------------------------
async def scrape_nha(save_pdfs_to="data/nha_pdfs"):
    os.makedirs(save_pdfs_to, exist_ok=True)
    print("[DEBUG] Scraper started...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(NHA_TENDERS_URL, timeout=60000)
        await page.wait_for_selector("table", timeout=15000)

        # Detect total pages
        pagination_buttons = await page.query_selector_all("ul.pagination li a")
        last_page = 1

        for btn in pagination_buttons:
            t = (await btn.inner_text()).strip()
            if t.isdigit():
                last_page = max(last_page, int(t))

        print(f"[INFO] Detected total pages: {last_page}")

        async with aiohttp.ClientSession() as session:
            for current_page in range(1, last_page + 1):
                print(f"\n[INFO] Scraping page {current_page}/{last_page}")

                if current_page > 1:
                    nav_js = f"document.querySelector('ul.pagination li a[href*=\"page={current_page}\"]').click()"
                    await page.evaluate(nav_js)
                    await page.wait_for_timeout(2000)
                    await page.wait_for_selector("table")

                await scrape_page(page, session, save_pdfs_to)
                await asyncio.sleep(1)

        await browser.close()


def run_nha():
    asyncio.run(scrape_nha())

if __name__ == "__main__":
    run_nha()