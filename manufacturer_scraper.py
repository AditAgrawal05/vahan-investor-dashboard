import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import traceback
from io import StringIO

VAHAN_URL = "https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml"
SAVE_DEBUG = True  # Save HTML + screenshots for debugging


def select_category_from_dropdown(driver, wait, category_name):
    """Select category from dropdown menu without submitting."""
    dropdown = wait.until(EC.element_to_be_clickable((By.ID, "vchgroupTable:selectCatgGrp")))
    dropdown.click()
    time.sleep(0.3)
    option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//li[normalize-space()='{category_name}']")))
    option.click()
    time.sleep(1)


def scroll_and_collect_all_pages(driver, wait, category, year):
    """Scroll table for each page, collect all rows, and merge into one table HTML."""
    all_rows_html = ""
    table_header_html = None

    while True:
        # Scroll current page fully
        prev_count = 0
        same_count_rounds = 0
        while True:
            table_body = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".ui-datatable-scrollable-body table tbody")
            ))
            rows = table_body.find_elements(By.TAG_NAME, "tr")
            curr_count = len(rows)
            print(f"    ↳ Loaded {curr_count} rows so far on current page...")

            if curr_count == prev_count:
                same_count_rounds += 1
            else:
                same_count_rounds = 0

            if same_count_rounds >= 2:
                break

            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", table_body)
            time.sleep(0.5)
            prev_count = curr_count

        # Save header only once
        if table_header_html is None:
            header_table = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".ui-datatable-scrollable-header table thead")
            ))
            table_header_html = header_table.get_attribute("outerHTML")

        # Append only rows of this page
        all_rows_html += table_body.get_attribute("innerHTML")

        # Try to go to next page
        try:
            next_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@class,'ui-paginator-next') and not(contains(@class,'ui-state-disabled'))]")
            ))
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(0.2)
            next_btn.click()
            time.sleep(0.7)
        except:
            break  # No more pages

    # Build full table HTML
    full_table_html = f"<table>{table_header_html}<tbody>{all_rows_html}</tbody></table>"
    return full_table_html


def scrape_table(driver, category, year, wait):
    """Scroll through all pages and extract table data, return DataFrame."""
    table_html_full = scroll_and_collect_all_pages(driver, wait, category, year)

    # Save HTML for debug
    if SAVE_DEBUG:
        os.makedirs("debug_tables", exist_ok=True)
        with open(f"debug_tables/{category}_{year}.html", "w", encoding="utf-8") as f:
            f.write(table_html_full)

    df = pd.read_html(StringIO(table_html_full))[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' '.join(col).strip() for col in df.columns.values]
    else:
        df.columns = [str(col).strip() for col in df.columns]

    manufacturer_col = next((c for c in df.columns if "maker" in c.lower() or "manufacturer" in c.lower()), None)
    registrations_col = next((c for c in df.columns if "total" in c.lower() or "registrations" in c.lower()), None)

    if not manufacturer_col or not registrations_col:
        print(f"❌ {category} {year} - Columns not found.")
        return None

    df.rename(columns={manufacturer_col: "Manufacturer", registrations_col: "Registrations"}, inplace=True)
    df.dropna(subset=["Manufacturer"], inplace=True)
    df = df[~df["Manufacturer"].str.contains("Total", case=False, na=False)]

    if df.empty:
        print(f"⚠ No rows found for {category} {year} after cleaning.")
        if SAVE_DEBUG:
            driver.save_screenshot(f"debug_tables/{category}_{year}.png")
        return None

    print(f"✅ {category} {year} - Final row count: {len(df)}")
    df["Date"] = pd.to_datetime(f"01-01-{year}")
    df["Category"] = category
    return df[["Manufacturer", "Registrations", "Date", "Category"]]


def scrape_vahan_data():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)
    all_dataframes = []

    try:
        print(f"Opening Vahan Dashboard: {VAHAN_URL}")
        driver.get(VAHAN_URL)

        # Select 'Maker' in Y-axis
        y_axis_dropdown = wait.until(EC.element_to_be_clickable((By.ID, 'yaxisVar')))
        y_axis_dropdown.click()
        time.sleep(1)
        maker_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[text()='Maker']")))
        maker_option.click()
        time.sleep(1)

        # Refresh after selecting Maker
        wait.until(EC.element_to_be_clickable((By.ID, 'j_idt72'))).click()
        time.sleep(2)

        categories = ["FOUR WHEELER", "TWO WHEELER", "THREE WHEELER"]
        years = ["2024", "2023", "2022"]

        for year in years:
            print(f"\n=== Processing Year: {year} ===")

            # Select year and refresh
            year_dropdown = wait.until(EC.element_to_be_clickable((By.ID, 'selectedYear')))
            year_dropdown.click()
            time.sleep(0.5)
            year_option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//li[text()='{year}']")))
            year_option.click()
            time.sleep(0.5)
            wait.until(EC.element_to_be_clickable((By.ID, 'j_idt72'))).click()
            time.sleep(1)

            for category in categories:
                print(f"--- Processing Category: {category} ---")
                if category != "FOUR WHEELER":
                    select_category_from_dropdown(driver, wait, category)

                df = scrape_table(driver, category, year, wait)
                if df is not None:
                    all_dataframes.append(df)

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        driver.quit()
        print("Browser closed.")

        if all_dataframes:
            final_df = pd.concat(all_dataframes, ignore_index=True)
            final_df.to_csv("vahan_manufacturer_data_clean.csv", index=False)
            print("\nSUCCESS! Saved final data to vahan_manufacturer_data_clean.csv")
        else:
            print("\nNo data was scraped. The final CSV was not created.")


if __name__ == "__main__":
    scrape_vahan_data()
