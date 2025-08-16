# Vahan Dashboard: Investor Insights into India's Vehicle Registration Data

## Objective
This project is an interactive dashboard built to provide investors with key insights into India's vehicle registration data. It focuses on analyzing Year-over-Year (YoY) and Quarter-over-Quarter (QoQ) growth trends for vehicle manufacturers, sourced directly from the public Vahan Parivahan dashboard.

## Features
* **Interactive UI:** A clean, investor-friendly interface built with Streamlit.
* **Key Performance Metrics:** At-a-glance cards for Total Registrations, Overall YoY Growth, and Overall QoQ Growth.
* **Dynamic Filtering:** Filter data by **Year**, **Quarter**, and **Vehicle Category** (FOUR WHEELER, TWO WHEELER, THREE WHEELER).
* **Growth Analysis:** Bar charts showing the top 15 manufacturers by both YoY and QoQ growth, making it easy to spot emerging players.
* **Market Share Visualization:** A pie chart that breaks down the market share for the selected category and year.
* **Detailed Data View:** Expandable tables to view the raw, processed data.

## Setup and Installation

Follow these steps to run the dashboard locally:

**1. Prerequisites:**
* Python 3.8+
* Google Chrome installed

**2. Clone the Repository:**
```bash
git clone [Your GitHub Repo URL]
cd [Your-Repo-Name]
```

**3. Install Dependencies:**
Create a virtual environment (optional but recommended) and install the required libraries from the `requirements.txt` file.
```bash
pip install -r requirements.txt
```

**4. Run the Dashboard:**
Launch the Streamlit application from your terminal.
```bash
streamlit run dashboard.py
```
The application will open in your web browser.

## Data Collection
The data for this dashboard was collected from the official [Vahan Parivahan Dashboard](https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml) using two custom Python scrapers built with Selenium and BeautifulSoup.

* `manufacturer_scraper.py`: Scrapes the total yearly vehicle registrations for each manufacturer.
* `monthly_scraper.py`: Scrapes the monthly registration data for each manufacturer, which is then used to calculate quarterly figures.

The generated CSV files are included in this repository.

> **⚠️ Important Note for Re-running Scrapers:**
> The element ID for the "Refresh" button on the Vahan website changes daily. If you need to re-run the scrapers, you must **manually inspect the webpage** to find the new ID for the refresh button and **update it in both scraper `.py` files**. Look for a line similar to `wait.until(EC.element_to_be_clickable((By.ID, 'j_idt71'))).click()`.

## Feature Roadmap (Future Enhancements)
* **State-Wise Filtering:** Add a filter to analyze registration data for individual states.
* **EV vs. Non-EV Analysis:** Introduce a feature to specifically compare the growth of electric vehicle manufacturers against traditional ICE manufacturers.
* **Deeper Trend Analysis:** Incorporate moving averages and more advanced time-series analysis to predict future trends.