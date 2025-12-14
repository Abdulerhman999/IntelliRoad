import argparse
import asyncio
import datetime
import os
import re
from playwright.async_api import async_playwright
from backend.database import insert_tender_record, insert_boq_file, insert_boq_line

try:
    from pdf2image import convert_from_path
    import pytesseract
    import PyPDF2
    
    # Set Tesseract path explicitly
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    OCR_AVAILABLE = True
except Exception as e:
    print(f"[Warning] OCR libraries not fully available: {e}")
    OCR_AVAILABLE = False

ORG_URL = "https://ppra.gov.pk/#/tenders/procurementContractDetail/{org_id}"
DOWNLOAD_DIR = "downloads/ppra/"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def extract_additional_metadata_from_text(text, existing_metadata):
    """Extract additional metadata from OCR/extracted text"""
    metadata = existing_metadata.copy()
    
    # Extract contract number if not already present
    if not metadata.get("tender_no") or metadata.get("tender_no") == "":
        contract_patterns = [
            r'CONTRACT\s+NO[\.:]?\s*([A-Z0-9\-\/]+)',
            r'TENDER\s+NO[\.:]?\s*([A-Z0-9\-\/]+)',
            r'PCN[:\s]*([A-Z0-9\-]+)',
        ]
        for pattern in contract_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["tender_no"] = match.group(1).strip()
                break
    
    # Extract project description/title if missing
    if not metadata.get("title") or metadata.get("title") == "Unknown":
        for_patterns = [
            r'CONTRACT\s+NO[^F]+FOR\s+([^\n]{20,200})',
            r'PROJECT\s+TITLE[:\s]+([^\n]{20,200})',
            r'SUBJECT[:\s]+([^\n]{20,200})',
        ]
        for pattern in for_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up
                title = re.sub(r'\s+', ' ', title)
                if len(title) > 20:
                    metadata["title"] = title[:500]
                    break
    
    # Extract location/city
    if not metadata.get("city"):
        # Common Pakistan cities
        cities = ['Islamabad', 'Karachi', 'Lahore', 'Rawalpindi', 'Multan', 'Faisalabad', 
                  'Quetta', 'Peshawar', 'Sialkot', 'Gujranwala', 'Hyderabad']
        for city in cities:
            if city.lower() in text.lower():
                metadata["city"] = city
                break
    
    # Extract dates
    date_pattern = r'(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})'
    dates = re.findall(date_pattern, text)
    
    # Look for date context
    if dates and not metadata.get("publish_date"):
        for i, date_str in enumerate(dates):
            context_start = max(0, text.find(date_str) - 50)
            context_end = min(len(text), text.find(date_str) + 50)
            context = text[context_start:context_end].lower()
            
            if any(kw in context for kw in ['publish', 'advertise', 'issue']):
                metadata["publish_date"] = date_str
                break
    
    if dates and not metadata.get("closing_date"):
        for date_str in dates:
            context_start = max(0, text.find(date_str) - 50)
            context_end = min(len(text), text.find(date_str) + 50)
            context = text[context_start:context_end].lower()
            
            if any(kw in context for kw in ['closing', 'deadline', 'submission']):
                metadata["closing_date"] = date_str
                break
    
    return metadata


def parse_date(date_str):
    """Parse date string to YYYY-MM-DD format for MySQL DATE field."""
    if not date_str:
        return None
    
    # Common date formats to try
    formats = [
        "%d/%m/%Y",      # 25/12/2024
        "%d-%m-%Y",      # 25-12-2024
        "%Y-%m-%d",      # 2024-12-25
        "%d %b %Y",      # 25 Dec 2024
        "%d %B %Y",      # 25 December 2024
        "%b %d, %Y",     # Dec 25, 2024
        "%B %d, %Y",     # December 25, 2024
        "%d.%m.%Y",      # 25.12.2024
        "%d/%m/%y",      # 25/12/24
        "%d-%m-%y",      # 25-12-24
    ]
    
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            continue
    
    return None


def is_scanned_pdf(pdf_path):
    """
    Determine if a PDF is scanned (image-based) or native text.
    Returns True if scanned (needs OCR), False if native text.
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Check first 3 pages (or all pages if less than 3)
            pages_to_check = min(3, len(pdf_reader.pages))
            
            for page_num in range(pages_to_check):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # If we find meaningful text (more than 50 chars), it's not scanned
                if text and len(text.strip()) > 50:
                    return False
            
            # If we checked all pages and found no significant text, it's scanned
            return True
            
    except Exception as e:
        print(f"[Debug] Error checking PDF type: {e}")
        # If we can't determine, assume it's scanned and try OCR
        return True


def extract_text_from_pdf(pdf_path):
    """
    Intelligently extract text from PDF.
    - If native text PDF: extract directly
    - If scanned PDF: use OCR
    """
    print(f"[Debug] Analyzing PDF: {os.path.basename(pdf_path)}")
    
    # First, try direct text extraction
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = []
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
            
            extracted = "\n\n".join(full_text)
            
            # If we got substantial text, it's a native PDF
            if len(extracted.strip()) > 100:
                print(f"[Info] Native text PDF detected - extracted {len(extracted)} characters")
                return extracted
            else:
                print("[Info] Little/no text found - likely scanned PDF")
    except Exception as e:
        print(f"[Debug] Direct extraction failed: {e}")
    
    # If direct extraction failed or yielded little text, use OCR
    print("[Info] Attempting OCR extraction...")
    
    if not OCR_AVAILABLE:
        print("[Warning] OCR libraries not available")
        return ""
    
    try:
        # Check if it's actually a scanned PDF
        if is_scanned_pdf(pdf_path):
            print("[Info] Scanned PDF confirmed - running OCR (this may take a while)...")
        else:
            print("[Info] Running OCR as fallback...")
        
        # Convert PDF to images and run OCR
        pages_imgs = convert_from_path(
            pdf_path,
            poppler_path=r"C:\Program Files (x86)\Poppler\Library\bin",
            dpi=300,  # Higher DPI for better OCR accuracy
            fmt='jpeg'
        )
        
        full_text = []
        for page_num, img in enumerate(pages_imgs, start=1):
            print(f"[Debug] OCR processing page {page_num}/{len(pages_imgs)}...")
            
            # Use Tesseract with English language
            text = pytesseract.image_to_string(img, lang='eng')
            
            if text.strip():
                full_text.append(f"--- Page {page_num} ---\n{text}")
        
        extracted = "\n\n".join(full_text)
        
        if extracted.strip():
            print(f"[OK] OCR completed - extracted {len(extracted)} characters")
            return extracted
        else:
            print("[Warning] OCR completed but no text found")
            return ""
            
    except Exception as e:
        print(f"[Error] OCR extraction failed: {e}")
        return ""


def parse_boq_lines_from_text(text):
    """Parse BOQ line items from extracted text - handles both clean and OCR text"""
    lines = text.splitlines()
    candidates = []

    # Pattern 1: Structured BOQ with clear columns
    # Format: item_no | description | quantity | unit | rate | total
    pattern1 = re.compile(
        r'^\s*(\d+[\.\d\-]*)\s+(.{10,200}?)\s+([0-9,\.]+)\s*(m3|m2|mt|ton|tonne|kg|cft|rm|ft2|ft|bag|nos|cum|sqm|rmt)?\s+([Rs\.\s0-9,\.]+)\s+([Rs\.\s0-9,\.]+)',
        re.IGNORECASE,
    )
    
    # Pattern 2: Relaxed pattern for OCR text (more spaces, potential errors)
    pattern2 = re.compile(
        r'(\d{1,4}[\.\d]*)\s+(.{15,150}?)\s+([0-9,\.]+)\s*(m3|m2|mt|ton|kg|cft|rm|ft2|bag|nos|cum|sqm|rmt|cubic|square|meter|tonne)?\s+([0-9,\.]+)\s+([0-9,\.]+)',
        re.IGNORECASE,
    )
    
    # Pattern 3: Look for "Rs" or currency indicators
    pattern3 = re.compile(
        r'(\d{1,3}[\.\d]*)\s+(.{10,100})\s+([0-9,\.]+)\s+(?:Rs\.?|PKR)?\s*([0-9,\.]+)',
        re.IGNORECASE,
    )

    def parse_money(s):
        if not s:
            return None
        # Remove everything except digits and decimal point
        s = re.sub(r'[^\d\.]', '', str(s))
        try:
            val = float(s)
            # Sanity check: BOQ prices usually between 1 and 1 billion
            if 0.01 < val < 1000000000:
                return val
            return None
        except:
            return None
    
    def parse_quantity(s):
        if not s:
            return None
        s = str(s).replace(',', '').replace(' ', '')
        try:
            val = float(s)
            # Sanity check: quantities usually between 0.01 and 1 million
            if 0.01 < val < 10000000:
                return val
            return None
        except:
            return None

    # Try Pattern 1 (structured)
    for ln in lines:
        m = pattern1.search(ln)
        if m:
            item_no = m.group(1).strip()
            desc = m.group(2).strip()
            qty = parse_quantity(m.group(3))
            if qty is None:
                continue
            unit = (m.group(4) or "").strip().lower()
            unit_price = parse_money(m.group(5))
            total_price = parse_money(m.group(6))
            
            if unit_price or total_price:
                candidates.append({
                    "item_no": item_no,
                    "description": desc,
                    "unit": unit,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "raw": ln,
                })

    # Try Pattern 2 (relaxed for OCR)
    if len(candidates) < 5:  # If we didn't find many items, try looser pattern
        for ln in lines:
            # Skip if already matched
            if any(c["raw"] == ln for c in candidates):
                continue
                
            m = pattern2.search(ln)
            if m:
                item_no = m.group(1).strip()
                desc = m.group(2).strip()
                qty = parse_quantity(m.group(3))
                if qty is None:
                    continue
                unit = (m.group(4) or "").strip().lower()
                unit_price = parse_money(m.group(5))
                total_price = parse_money(m.group(6))
                
                # Validate: at least one price must be present
                if unit_price or total_price:
                    # If we have both, check if they make sense
                    if unit_price and total_price and qty:
                        expected = unit_price * qty
                        # Allow 20% tolerance for rounding
                        if abs(total_price - expected) / expected > 0.2:
                            continue
                    
                    candidates.append({
                        "item_no": item_no,
                        "description": desc,
                        "unit": unit,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "total_price": total_price,
                        "raw": ln,
                    })

    # Pattern 3: Very loose pattern for badly OCR'd text
    if len(candidates) < 3:
        for ln in lines:
            if any(c["raw"] == ln for c in candidates):
                continue
            
            m = pattern3.search(ln)
            if m:
                item_no = m.group(1).strip()
                desc = m.group(2).strip()
                qty = parse_quantity(m.group(3))
                if qty is None or qty < 0.01:
                    continue
                unit_price = parse_money(m.group(4))
                
                if unit_price and unit_price > 0:
                    total_price = qty * unit_price
                    
                    candidates.append({
                        "item_no": item_no,
                        "description": desc,
                        "unit": "",
                        "quantity": qty,
                        "unit_price": unit_price,
                        "total_price": total_price,
                        "raw": ln,
                    })

    # Additional fallback: Look for lines with common BOQ keywords
    if len(candidates) < 3:
        boq_keywords = [
            'cement', 'concrete', 'steel', 'bitumen', 'aggregate', 'sand',
            'excavation', 'filling', 'compaction', 'asphalt', 'paint',
            'reinforcement', 'formwork', 'brick', 'stone', 'gravel',
            'mobilization', 'demobilization', 'earthwork', 'structure'
        ]
        
        # Pattern: keyword + numbers
        keyword_pattern = re.compile(
            r'(.{5,80}(?:' + '|'.join(boq_keywords) + r').{5,80})\s+([0-9,\.]+)\s+([0-9,\.]+)',
            re.IGNORECASE
        )
        
        for ln in lines:
            if any(c["raw"] == ln for c in candidates):
                continue
            
            m = keyword_pattern.search(ln)
            if m:
                desc = m.group(1).strip()
                qty = parse_quantity(m.group(2))
                price = parse_money(m.group(3))
                
                if qty and price and qty > 0 and price > 0:
                    candidates.append({
                        "item_no": None,
                        "description": desc,
                        "unit": "",
                        "quantity": qty,
                        "unit_price": price,
                        "total_price": qty * price,
                        "raw": ln,
                    })

    # Clean up duplicates (same description)
    seen_descriptions = set()
    unique_candidates = []
    for c in candidates:
        desc_lower = c["description"].lower()[:50]  # First 50 chars
        if desc_lower not in seen_descriptions:
            seen_descriptions.add(desc_lower)
            unique_candidates.append(c)
    
    return unique_candidates


async def extract_contract_blocks(page, debug=False):
    """Extract all contract rows from the table structure."""
    results = []
    
    # Wait for the table to load
    try:
        await page.wait_for_selector("table tbody tr", timeout=10000)
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"[Warning] Table not found: {e}")
        return results
    
    # Get all table rows
    rows = await page.query_selector_all("table tbody tr")
    print(f"[Debug] Found {len(rows)} table rows")
    
    for idx, row in enumerate(rows, start=1):
        try:
            # Extract all cells
            cells = await row.query_selector_all("td")
            
            if len(cells) < 2:
                continue
            
            # Cell 0: PCN number
            pcn = ""
            try:
                pcn = (await cells[0].inner_text()).strip()
            except:
                pass
            
            # Cell 1: Main content - get full text
            metadata = {"pcn": pcn}
            
            try:
                # Get full text from cell 1
                cell1_text = await cells[1].inner_text()
                
                # Split into lines
                lines = [l.strip() for l in cell1_text.split("\n") if l.strip()]
                
                # First non-empty line is usually the organization
                if lines:
                    # Check if first line looks like an organization (contains specific keywords)
                    first_line = lines[0]
                    if any(keyword in first_line.lower() for keyword in ['authority', 'nha', 'department', 'ministry', 'corporation', 'company']):
                        metadata["organization"] = first_line
                        title_start = 1
                    else:
                        title_start = 0
                    
                    # Collect title lines (non key-value pairs before we hit structured data)
                    title_parts = []
                    for i in range(title_start, len(lines)):
                        line = lines[i]
                        # Stop collecting title when we hit key-value pairs
                        if ":" in line and any(kw in line.lower() for kw in ['contract', 'worth', 'amount', 'bidder', 'date', 'ts']):
                            break
                        # Skip PCN line
                        if pcn and pcn in line:
                            continue
                        # Skip very short fragments
                        if len(line) > 5:
                            title_parts.append(line)
                    
                    # Take first 3-5 lines as title
                    if title_parts:
                        metadata["title"] = " ".join(title_parts[:5])
                
                # Parse key-value pairs from the rest
                for line in lines:
                    if ":" not in line:
                        continue
                    
                    key, _, value = line.partition(":")
                    key_clean = key.strip().lower()
                    value_clean = value.strip()
                    
                    if not value_clean:
                        continue
                    
                    # Map to database columns
                    if "contract worth" in key_clean or "tender value" in key_clean:
                        metadata["contract_worth"] = value_clean
                    elif "awarded amount" in key_clean or "contract awarded" in key_clean:
                        metadata["awarded_amount"] = value_clean
                    elif "successful bidder" in key_clean or "bidder" in key_clean:
                        metadata["bidder"] = value_clean
                    elif "publish" in key_clean or "advertisement" in key_clean:
                        metadata["publish_date"] = value_clean
                    elif "closing" in key_clean or "submission" in key_clean:
                        metadata["closing_date"] = value_clean
                    elif "opening" in key_clean:
                        metadata["opening_date"] = value_clean
                    elif "category" in key_clean:
                        metadata["category"] = value_clean
                    elif "method" in key_clean:
                        metadata["procurement_method"] = value_clean
                    elif "status" in key_clean:
                        metadata["status"] = value_clean
                    elif "department" in key_clean:
                        metadata["department"] = value_clean
                    elif "city" in key_clean or "location" in key_clean:
                        metadata["city"] = value_clean
                    elif "province" in key_clean:
                        metadata["province"] = value_clean
                
                if debug:
                    print(f"[Debug] Row {idx} metadata: {metadata}")
                    
            except Exception as e:
                if debug:
                    print(f"[Debug] Error parsing cell 1 for row {idx}: {e}")
            
            # Find download link
            download_link = None
            
            try:
                await row.wait_for_selector("a, button, i, [onclick]", timeout=2000)
            except:
                pass
            
            selectors = [
                "i.fa-file-download",
                "i.fas.fa-file-download",
                "i.fa-download",
                "i[class*='fa-file']",
                "i[class*='download']",
                "a[href]",
            ]
            
            for selector in selectors:
                try:
                    download_link = await row.query_selector(selector)
                    if download_link:
                        is_visible = await download_link.is_visible()
                        if is_visible:
                            break
                        else:
                            download_link = None
                except:
                    continue
            
            results.append({
                "metadata": metadata,
                "row_element": row,
                "download_link": download_link
            })
            
        except Exception as e:
            print(f"[Warning] Failed to parse row {idx}: {e}")
            continue
    
    return results


async def download_pdf_from_modal(page, download_link, card_index):
    """Handle PDF download that opens through a modal dialog."""
    
    if not download_link:
        print(f"[Warning] No download link for contract {card_index}")
        return None
    
    try:
        # Check for direct PDF link
        href = await download_link.get_attribute("href")
        
        if href and href.endswith(".pdf"):
            print(f"[Debug] Direct PDF link found: {href}")
            try:
                from urllib.parse import urljoin
                url = urljoin(page.url, href)
                resp = await page.request.get(url, timeout=60000)
                if resp.ok:
                    content = await resp.body()
                    filename = os.path.basename(href.split("?")[0]) or f"contract_{card_index}.pdf"
                    path = os.path.join(DOWNLOAD_DIR, filename)
                    with open(path, "wb") as f:
                        f.write(content)
                    print(f"[OK] Downloaded via direct link: {filename}")
                    return path
            except Exception as e:
                print(f"[Debug] Direct download failed: {e}")
        
        # Modal-based download
        print(f"[Debug] Attempting modal-based download...")
        
        async with page.expect_download(timeout=30000) as download_info:
            await download_link.click()
            await page.wait_for_timeout(1000)
            
            try:
                modal = await page.wait_for_selector("#publicationModal.show, .modal.show", timeout=5000)
                
                if modal:
                    print("[Debug] Modal opened, looking for download button...")
                    
                    download_btn_selectors = [
                        "a[href*='.pdf']",
                        "button:has-text('Download')",
                        "a:has-text('Download')",
                        ".btn-primary",
                        "i.fa-download",
                    ]
                    
                    download_btn = None
                    for selector in download_btn_selectors:
                        try:
                            download_btn = await modal.query_selector(selector)
                            if download_btn:
                                break
                        except:
                            continue
                    
                    if download_btn:
                        print("[Debug] Found download button in modal, clicking...")
                        await download_btn.click()
                    else:
                        print("[Warning] Could not find download button in modal")
                        try:
                            close_btn = await page.query_selector(".modal .btn-close, .modal button[data-bs-dismiss='modal']")
                            if close_btn:
                                await close_btn.click()
                        except:
                            pass
                        return None
                        
            except Exception as e:
                print(f"[Debug] Modal handling: {e}")
        
        download = await download_info.value
        filename = download.suggested_filename or f"contract_{card_index}.pdf"
        path = os.path.join(DOWNLOAD_DIR, filename)
        await download.save_as(path)
        print(f"[OK] Downloaded: {filename}")
        
        # Close modal
        try:
            close_btn = await page.query_selector(".modal.show .btn-close, .modal.show button[data-bs-dismiss='modal']")
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(500)
        except:
            pass
        
        return path
        
    except Exception as e:
        print(f"[Error] PDF download failed for contract {card_index}: {e}")
        
        try:
            close_btn = await page.query_selector(".modal.show .btn-close, .modal.show button[data-bs-dismiss='modal']")
            if close_btn:
                await close_btn.click()
        except:
            pass
        
        return None


async def get_total_pages(page):
    """Get total number of pages from pagination info."""
    try:
        pagination_selectors = [
            "text=Total Pages",
            ".pagination-info",
            "div:has-text('Total Pages')",
        ]
        
        for selector in pagination_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if "Total Pages" in text:
                        parts = text.split("Total Pages")
                        if len(parts) > 1:
                            match = re.search(r'\d+', parts[1])
                            if match:
                                return int(match.group())
            except:
                continue
        
        # Fallback: look for pagination buttons
        last_page_btn = await page.query_selector(".pagination li:not(.next):last-child a")
        if last_page_btn:
            text = await last_page_btn.inner_text()
            if text.isdigit():
                return int(text)
                
    except Exception as e:
        print(f"[Debug] Could not determine total pages: {e}")
    
    return 1


async def click_next_page(page):
    """Navigate to the next page."""
    try:
        await page.wait_for_timeout(1000)
        
        next_selectors = [
            "ul.pagination li.next:not(.disabled) a",
            "ul.pagination li:has-text('Next'):not(.disabled) a",
            ".pagination .next:not(.disabled) a",
            "a[aria-label='Next']:not([disabled])",
            "button:has-text('Next'):not([disabled])",
        ]
        
        next_btn = None
        for selector in next_selectors:
            try:
                next_btn = await page.query_selector(selector)
                if next_btn:
                    classes = await next_btn.get_attribute("class") or ""
                    parent_classes = ""
                    try:
                        parent = await next_btn.evaluate_handle("el => el.parentElement")
                        parent_classes = await parent.get_attribute("class") or ""
                    except:
                        pass
                    
                    if "disabled" not in classes and "disabled" not in parent_classes:
                        print(f"[Debug] Found Next button with selector: {selector}")
                        break
                    else:
                        next_btn = None
            except:
                continue
        
        if not next_btn:
            print("[Debug] Next button not found or is disabled")
            return False
        
        current_text = ""
        try:
            current_indicator = await page.query_selector(".pagination li.active, .pagination li.current")
            if current_indicator:
                current_text = await current_indicator.inner_text()
        except:
            pass
        
        print(f"[Debug] Current page indicator: {current_text}")
        print("[Debug] Clicking Next button...")
        
        await next_btn.click()
        
        try:
            await page.wait_for_timeout(2000)
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            await page.wait_for_timeout(3000)
        
        try:
            new_indicator = await page.query_selector(".pagination li.active, .pagination li.current")
            if new_indicator:
                new_text = await new_indicator.inner_text()
                print(f"[Debug] New page indicator: {new_text}")
                if new_text != current_text:
                    print("[OK] Successfully navigated to next page")
                    return True
        except:
            pass
        
        print("[OK] Clicked Next button")
        return True
        
    except Exception as e:
        print(f"[Error] Failed to click Next button: {e}")
        return False


async def scrape_ppra_org(org_id=38, debug=False, headless=True):
    """Scrape all pages of the PPRA organization tenders page."""
    print("[DEBUG] Scraper started...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        page.set_default_timeout(60000)
        
        print(f"Loading PPRA org page for org_id={org_id}")
        try:
            await page.goto(ORG_URL.format(org_id=org_id), wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"[Warning] Page load issue: {e}, continuing...")
        
        await page.wait_for_timeout(5000)
        
        try:
            await page.wait_for_selector("table tbody tr i, table tbody tr a, table tbody tr button", timeout=5000)
        except:
            print("[Warning] Download buttons may not have loaded yet")
        
        total_pages = await get_total_pages(page)
        print(f"Total pages detected: {total_pages}")
        
        global_index = 0
        
        for page_no in range(1, total_pages + 1):
            print(f"\n{'='*60}")
            print(f"=== Scraping Page {page_no}/{total_pages} ===")
            print(f"{'='*60}")
            
            contracts = await extract_contract_blocks(page, debug=debug)
            print(f"Found {len(contracts)} contracts on page {page_no}")
            
            for contract in contracts:
                global_index += 1
                metadata = contract["metadata"]
                download_link = contract["download_link"]
                
                # Get info
                title = metadata.get("title", "Unknown")
                pcn = metadata.get("pcn", "")
                organization = metadata.get("organization", "")
                
                print(f"\nProcessing #{global_index}: {title[:80]}...")
                if pcn:
                    print(f"  PCN: {pcn}")
                if organization:
                    print(f"  Org: {organization}")
                
                # Download PDF
                pdf_path = await download_pdf_from_modal(page, download_link, global_index)
                
                if pdf_path:
                    # Prepare record for database
                    record = {
                        "source_site": "ppra.gov.pk",
                        "tender_url": page.url,
                        "tender_no": pcn,
                        "title": title,
                        "department": metadata.get("department", ""),
                        "city": metadata.get("city", ""),
                        "province": metadata.get("province", ""),
                        "publish_date": parse_date(metadata.get("publish_date", "")),
                        "closing_date": parse_date(metadata.get("closing_date", "")),
                        "category": metadata.get("category", ""),
                        "procurement_method": metadata.get("procurement_method", ""),
                        "opening_date": parse_date(metadata.get("opening_date", "")),
                        "status": metadata.get("status", ""),
                        "organization": organization,
                        "raw_pdf_path": pdf_path,
                        "cleaned_pdf_path": None
                    }
                    
                    tid = insert_tender_record(record)
                    print(f"[OK] Inserted tender record #{global_index} -> tender_id {tid}")
                    
                    # Extract text from PDF
                    extracted_text = extract_text_from_pdf(pdf_path)
                    
                    if extracted_text:
                        # Enhance metadata from extracted text
                        metadata = extract_additional_metadata_from_text(extracted_text, metadata)
                        
                        # Update record with enhanced metadata
                        title = metadata.get("title", "Unknown")
                        pcn = metadata.get("pcn", "")
                        
                        # Insert BOQ file record
                        boq_id = insert_boq_file(tid, pdf_path, extracted_text)
                        print(f"[OK] Inserted BOQ file record -> boq_id {boq_id}")
                        
                        # Save sample for debugging (first 2000 chars)
                        if debug and global_index <= 2:
                            sample_path = os.path.join(DOWNLOAD_DIR, f"sample_text_{tid}.txt")
                            with open(sample_path, 'w', encoding='utf-8') as f:
                                f.write(extracted_text[:2000])
                            print(f"[Debug] Saved text sample to {sample_path}")
                        
                        # Parse BOQ items
                        try:
                            items = parse_boq_lines_from_text(extracted_text)
                            if items:
                                print(f"[Info] Found {len(items)} BOQ line items, inserting...")
                                for item in items:
                                    insert_boq_line(
                                        tender_id=tid,
                                        boq_id=boq_id,
                                        item_code=item.get("item_no"),
                                        description=item["description"],
                                        unit=item.get("unit"),
                                        quantity=item.get("quantity"),
                                        rate=item.get("unit_price"),
                                        cost=item.get("total_price"),
                                        raw_line=item["raw"]
                                    )
                                print(f"[OK] Inserted {len(items)} BOQ items for tender {tid}")
                            else:
                                print(f"[Info] No BOQ items found in tender {tid}")
                                if debug:
                                    # Show first 500 chars of text for inspection
                                    print(f"[Debug] First 500 chars of text:\n{extracted_text[:500]}\n")
                        except Exception as e:
                            print(f"[Warning] BOQ parsing failed: {e}")
                            import traceback
                            if debug:
                                traceback.print_exc()
                    else:
                        print(f"[Skip] No text extracted for tender {tid}")
                        insert_boq_file(tid, pdf_path, "")
                else:
                    print(f"[Skip] No PDF downloaded for contract #{global_index}")
            
            if page_no < total_pages:
                print(f"\n{'='*60}")
                print("Moving to next page...")
                print(f"{'='*60}")
                moved = await click_next_page(page)
                if not moved:
                    print("[Warning] Could not navigate to next page. Stopping.")
                    break
        
        await browser.close()
        print(f"\n{'='*60}")
        print(f"Scraping completed! Total contracts processed: {global_index}")
        print(f"{'='*60}")


def run_ppra_org():
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", type=int, default=38, help="Organization ID to scrape")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--headful", action="store_true", help="Run browser with head visible")
    args = parser.parse_args()
    
    asyncio.run(scrape_ppra_org(org_id=args.org, debug=args.debug, headless=not args.headful))


if __name__ == "__main__":
    run_ppra_org()