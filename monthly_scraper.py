import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from io import StringIO
import traceback

VAHAN_URL = "https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml"

def select_option_from_dropdown(driver, wait, dropdown_id, option_text):
    """Select an option from a dropdown menu."""
    dropdown = wait.until(EC.element_to_be_clickable((By.ID, dropdown_id)))
    dropdown.click()
    time.sleep(0.3)
    option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//li[normalize-space()='{option_text}']")))
    option.click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.ID, 'j_idt72'))).click()
    time.sleep(3)  

def scroll_and_collect_all_pages(driver, wait):
    """Scroll table for each page, collect all rows, and merge into one table HTML."""
    all_rows_html = ""
    table_header_html = None

    while True:
        prev_count = 0
        same_count_rounds = 0
        while True:
            table_body = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".ui-datatable-scrollable-body table tbody")
            ))
            rows = table_body.find_elements(By.TAG_NAME, "tr")
            curr_count = len(rows)

            if curr_count == prev_count:
                same_count_rounds += 1
            else:
                same_count_rounds = 0

            if same_count_rounds >= 2:
                break

            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", table_body)
            time.sleep(0.5)
            prev_count = curr_count

        if table_header_html is None:
            header_table = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".ui-datatable-scrollable-header table thead")
            ))
            table_header_html = header_table.get_attribute("outerHTML")

        all_rows_html += table_body.get_attribute("innerHTML")

        # Next page
        try:
            next_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@class,'ui-paginator-next') and not(contains(@class,'ui-state-disabled'))]")
            ))
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(0.2)
            next_btn.click()
            time.sleep(0.7)
        except:
            break

    full_table_html = f"<table>{table_header_html}<tbody>{all_rows_html}</tbody></table>"
    return full_table_html

def parse_table_html(html, year):
    df = pd.read_html(StringIO(html))[0]
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' '.join(col).strip() for col in df.columns.values]
    else:
        df.columns = [str(col).strip() for col in df.columns]
    # Add only Year column
    df["Year"] = year
    return df

def scrape_monthly_data():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)

    all_dataframes = []

    try:
        print(f"Opening Vahan Dashboard: {VAHAN_URL}")
        driver.get(VAHAN_URL)
        # select_option_from_dropdown(driver, wait, 'selectedYear', 2024)
        # Set Y-axis = Maker, X-axis = Month Wise
        select_option_from_dropdown(driver, wait, 'yaxisVar', 'Maker')
        select_option_from_dropdown(driver, wait, 'xaxisVar', 'Month Wise')

        years = ["2024", "2023", "2022"]  # Add all years you want

        for year in years:
            select_option_from_dropdown(driver, wait, 'selectedYear', year)
            # Click refresh
            # wait.until(EC.element_to_be_clickable((By.ID, 'j_idt71'))).click()
            # time.sleep(3)  # wait for table to fully load

            # Scroll and collect table
            table_html = scroll_and_collect_all_pages(driver, wait)
            df = parse_table_html(table_html, year)
            all_dataframes.append(df)

        # Combine all data and save
        if all_dataframes:
            final_df = pd.concat(all_dataframes, ignore_index=True)
            final_df.to_csv("vahan_monthly_data.csv", index=False)
            print("✅ Saved month-wise data with Year to vahan_monthly_data.csv")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        driver.quit()
        print("Browser closed.")

if __name__ == "__main__":
    scrape_monthly_data()
