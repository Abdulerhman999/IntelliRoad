import argparse
import asyncio
import datetime
import os
from playwright.async_api import async_playwright
from backend.database import insert_tender_record, insert_boq_file
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

ORG_URL = "https://ppra.gov.pk/#/tenders/procurementContractDetail/{org_id}"
DOWNLOAD_DIR = "downloads/ppra/"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def extract_contract_blocks(page, debug=False):
    """Extract all contract blocks from the current page.

    This function is more defensive than before: it waits for the page to render,
    attempts a few fallback selectors if `.card` isn't present, and builds
    results from download links when card containers are not available.
    """
    results = []

    # Prefer `.card` if available, but try several fallbacks (including table rows)
    candidate_selectors = [
        ".card",
        "div.tender",
        "div.contract",
        "table tbody tr",
        "table tr",
        ".table tbody tr",
        ".tenderRow",
        ".dataRow",
        "a[title='Download']",
        "i.fa-download",
        "a[href$='.pdf']",
        "td a",
    ]
    found_selector = None

    for sel in candidate_selectors:
        try:
            els = await page.query_selector_all(sel)
            if len(els) > 0:
                found_selector = sel
                break
        except Exception:
            continue

    if not found_selector:
        print("[Warning] No known contract selector was found on the page.")
        if debug:
            # dump HTML and screenshot for inspection
            ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(DOWNLOAD_DIR, f"debug_page_{ts}.html")
            shot_path = os.path.join(DOWNLOAD_DIR, f"debug_page_{ts}.png")
            try:
                content = await page.content()
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(content)
                await page.screenshot(path=shot_path, full_page=True)
                print(f"[Debug] Saved HTML to {html_path} and screenshot to {shot_path}")
            except Exception as e:
                print(f"[Debug] Failed to save debug artifacts: {e}")
        return results

    # If we found `.card` (or similar container), prefer treating those as cards
    if found_selector in (".card", "div.tender", "div.contract"):
        cards = await page.query_selector_all(found_selector)

        for card in cards:
            try:
                text = await card.inner_text()
            except Exception:
                text = ""

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            data = {}
            for ln in lines:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    data[k.strip().lower().replace(" ", "_")] = v.strip()

            pdf_button = await card.query_selector("i.fa-download, .fa-file-pdf, a[title='Download'], a[href$='.pdf']")

            results.append({
                "metadata": data,
                "pdf_button": pdf_button
            })

        return results

    # Otherwise build pseudo-cards from download links
    link_selectors = "i.fa-download, .fa-file-pdf, a[title='Download'], a[href$='.pdf'], td a"
    links = await page.query_selector_all(link_selectors)

    for idx, link in enumerate(links, start=1):
        try:
            # try to get surrounding text by looking up the closest block-level ancestor
            surrounding = await link.evaluate("el => (el.closest('div') && el.closest('div').innerText) || el.innerText")
        except Exception:
            surrounding = ""

        lines = [l.strip() for l in surrounding.split("\n") if l.strip()]
        data = {}
        for ln in lines:
            if ":" in ln:
                k, v = ln.split(":", 1)
                data[k.strip().lower().replace(" ", "_")] = v.strip()

        results.append({
            "metadata": data,
            "pdf_button": link
        })

    return results


async def download_pdf(card_index, pdf_button, page):
    """Download a contract PDF.

    Strategy:
    1. Close any blocking modals (e.g., #publicationModal).
    2. If the element has an `href` attribute, fetch it via page.request.
    3. Otherwise, intercept response with content-type:application/pdf after click.
    4. Fallback: try expect_download.
    """
    if not pdf_button:
        print(f"[Warning] No PDF button for contract {card_index}")
        return None

    try:
        href = await pdf_button.get_attribute("href")
    except Exception:
        href = None

    # Helper to save bytes to path
    def _save_bytes(bts, filename):
        path = os.path.join(DOWNLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(bts)
        return path

    try:
        # Close blocking modals
        try:
            modal = await page.query_selector("#publicationModal.show")
            if modal:
                close_btn = await page.query_selector("#publicationModal .btn-close, #publicationModal button[aria-label='Close'], #publicationModal [data-bs-dismiss='modal']")
                if close_btn:
                    await close_btn.click()
                    await page.wait_for_timeout(500)
        except Exception as e:
            print(f"[Debug] Could not close modal: {e}")

        if href:
            # Resolve relative hrefs
            from urllib.parse import urljoin

            url = urljoin(page.url, href)
            # Quick guard for data URIs
            if url.startswith("data:"):
                url = None

            if url:
                # Try to fetch via page.request
                try:
                    resp = await page.request.get(url, timeout=60000)
                    if resp.ok:
                        content = await resp.body()
                        import os as _os
                        suggested = _os.path.basename(url.split("?")[0]) or f"contract_{card_index}.pdf"
                        return _save_bytes(content, suggested)
                except Exception as e:
                    print(f"[Debug] href fetch failed for contract {card_index}: {e}")
                    # fall back to click below

        # Simple fallback: try expect_download
        async with page.expect_download(timeout=5000) as d_info:
            await pdf_button.click()
        download = await d_info.value
        fname = download.suggested_filename or f"contract_{card_index}.pdf"
        path = os.path.join(DOWNLOAD_DIR, fname)
        await download.save_as(path)
        return path
    except Exception as e:
        print(f"[Error] PDF download failed for contract {card_index}: {e}")
        return None


async def get_total_pages(page):
    """Reads total pages text if available on screen."""
    try:
        total_text = await page.inner_text("text=Total Pages", timeout=5000)
        # Example: '10 Records Per Page | Total Pages 3'
        parts = total_text.split("Total Pages")
        total_pages = int(parts[1].strip())
        return total_pages
    except:
        return 1


async def click_next(page):
    """Clicks Next button if enabled."""
    selectors = [
        "button:has-text('Next')",
        "a[aria-label='Next']",
        "li.next a",
        ".paginate_button.next a",
        ".pagination .next a",
    ]

    for sel in selectors:
        try:
            btn = await page.query_selector(sel)
            if not btn:
                continue

            # If the button is disabled (has attribute or disabled class), stop
            disabled_attr = await btn.get_attribute("disabled")
            cls = (await btn.get_attribute("class")) or ""
            if disabled_attr or "disabled" in cls:
                return False

            # capture first visible item text to detect change
            prev_text = ""
            try:
                first = await page.query_selector("table tbody tr td, .card")
                if first:
                    prev_text = (await first.inner_text())[:200]
            except Exception:
                prev_text = ""

            await btn.click()

            # wait for either content to change or a short timeout
            try:
                await page.wait_for_function(
                    "(prev) => { const el = document.querySelector('table tbody tr td, .card'); return !el || el.innerText.slice(0,200) !== prev; }",
                    prev_text,
                    timeout=7000,
                )
            except Exception:
                # fallback small wait
                await page.wait_for_timeout(1500)

            return True
        except Exception:
            continue

    return False


async def scrape_ppra_org(org_id=38, debug=False, headless=True):
    """Scrape all pages of the PPRA organization tenders page."""
    print("[DEBUG] Scraper started...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print(f"Loading PPRA org page for org_id={org_id}")
        try:
            await asyncio.wait_for(
                page.goto(ORG_URL.format(org_id=org_id), timeout=30000, wait_until="domcontentloaded"),
                timeout=35
            )
        except asyncio.TimeoutError:
            print("[Warning] Page load timed out, continuing anyway...")
        await page.wait_for_timeout(2000)

        total_pages = await get_total_pages(page)
        print(f"Total pages detected: {total_pages}")

        global_index = 0

        for page_no in range(1, total_pages + 1):
            print(f"\n=== Scraping Page {page_no}/{total_pages} ===")

            contracts = await extract_contract_blocks(page, debug=debug)
            print(f"Found {len(contracts)} contracts on this page")

            for contract in contracts:
                global_index += 1
                metadata = contract["metadata"]
                pdf_button = contract["pdf_button"]

                print(f"Processing #{global_index}: {metadata.get('contract_title','Unknown')}")

                pdf_path = await download_pdf(global_index, pdf_button, page)

                # Only insert if we have a PDF path or the button has an href
                has_href = False
                try:
                    has_href = (await pdf_button.get_attribute("href")) is not None
                except Exception:
                    pass

                if pdf_path or has_href:
                    record = {
                        **metadata,
                        "org_id": org_id,
                        "pdf_path": pdf_path
                    }
                    tid = insert_tender_record(record)
                    print(f"[OK] Inserted tender record #{global_index} (pdf: {pdf_path}) -> id {tid}")

                    # If OCR available and we downloaded a file, extract text and store in boq_files
                    if pdf_path and OCR_AVAILABLE:
                        try:
                            # convert PDF to images and run pytesseract
                            pages = convert_from_path(pdf_path)
                            full_text = []
                            for img in pages:
                                text = pytesseract.image_to_string(img)
                                full_text.append(text)
                            extracted = "\n\n".join(full_text)
                            insert_boq_file(tid, pdf_path, extracted)
                            print(f"[OK] OCR extracted and saved for tender {tid}")
                        except Exception as e:
                            print(f"[Warn] OCR failed for {pdf_path}: {e}")
                    elif pdf_path and not OCR_AVAILABLE:
                        print("[Info] OCR not available in environment; install pytesseract + pdf2image + system deps to enable OCR.")
                else:
                    print(f"[Skip] No PDF for contract #{global_index}, skipping DB insert")

            if page_no != total_pages:
                print("Moving to next page…")
                moved = await click_next(page)
                if not moved:
                    print("Could not navigate further. Stopping early.")
                    break
                await page.wait_for_load_state("networkidle")

        await browser.close()


def run_ppra_org():
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", type=int, default=38, help="Organization ID to scrape")
    parser.add_argument("--debug", action="store_true", help="Enable debug output (save html + screenshot on failures)")
    parser.add_argument("--headful", action="store_true", help="Run browser with head visible (headful)")
    args = parser.parse_args()

    asyncio.run(scrape_ppra_org(org_id=args.org, debug=args.debug, headless=not args.headful))

if __name__ == "__main__":
    run_ppra_org()