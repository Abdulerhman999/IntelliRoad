from scrapers.nha_scraper import run_nha
from scrapers.ppra_scraper import run_ppra
from utils.price_processor import aggregate_yearly_prices, recompute_all

def run_full_ingest():
    print("Scraping NHA...")
    run_nha()

    print("Scraping PPRA...")
    run_ppra()

    print("Aggregating yearly prices...")
    recompute_all(years=[2023, 2024, 2025])

    print("Done.")
