#!/usr/bin/env python3
"""
Planet Fitness Crowd Meter Scraper
------------------------------------
Setup:
    pip install playwright
    playwright install chromium

Usage:
    python pf_crowd_meter.py --slug hanford-ca
    python pf_crowd_meter.py --slug hanford-ca --headless false
"""

import argparse
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Run: pip install playwright && playwright install chromium")

BASE_URL = "https://www.planetfitness.com/gyms"


def scrape_crowd(slug: str, headless: bool) -> None:
    url = f"{BASE_URL}/{slug}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))

        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        all_meters = page.locator("meter").all()

        # Live indicator: 10 small bars, pink = filled, black = empty.
        # Exclude hourly chart bars which have id="bar_N".
        indicator_bars = [
            m for m in all_meters
            if ("bg-accent-pink" in (m.get_attribute("class") or "")
                or "bg-common-black" in (m.get_attribute("class") or ""))
            and not (m.get_attribute("id") or "").startswith("bar_")
        ]

        if indicator_bars:
            pink_count = sum(
                1 for m in indicator_bars
                if "bg-accent-pink" in (m.get_attribute("class") or "")
            )
            print(pink_count)
        else:
            print("?")

        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Planet Fitness Crowd Meter")
    parser.add_argument("--slug", "-s", help="Club URL slug (after /gyms/ in the URL)")
    parser.add_argument("--headless", default="true", choices=["true", "false"])
    args = parser.parse_args()

    slug = args.slug
    if not slug:
        slug = input("Enter slug: ").strip().strip("/")

    scrape_crowd("hanford-ca", headless=True)


if __name__ == "__main__":
    main()