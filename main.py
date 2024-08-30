from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import os
import sys

@dataclass
class EVChargingStation:
    """Holds EV charging station data"""
    name: str = None
    address: str = None
    type_of_guns: str = None
    power_in_kw: str = None
    
    

@dataclass
class EVChargingStationList:
    """Holds list of EVChargingStation objects and saves to both Excel and CSV"""
    charging_station_list: list[EVChargingStation] = field(default_factory=list)
    save_at: str = 'output'

    def dataframe(self):
        """Transforms charging_station_list to pandas dataframe"""
        return pd.json_normalize((asdict(station) for station in self.charging_station_list), sep="_")

    def save_to_excel(self, filename):
        """Saves pandas dataframe to Excel (xlsx) file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"{self.save_at}/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """Saves pandas dataframe to CSV file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"{self.save_at}/{filename}.csv", index=False)

    def save_popular_times(self, filename, popular_times):
        """Saves popular times to CSV and Excel files"""
        df = pd.DataFrame(popular_times)
        csv_path = f"{self.save_at}/{filename}.csv"
        excel_path = f"{self.save_at}/{filename}.xlsx"
        df.to_csv(csv_path, index=False)
        df.to_excel(excel_path, index=False)
        return csv_path, excel_path

def main():
    # Input handling
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    args = parser.parse_args()

    if args.search:
        search_list = [args.search]
    else:
        search_list = []
        input_file_name = 'input.txt'
        input_file_path = os.path.join(os.getcwd(), input_file_name)
        if os.path.exists(input_file_path):
            with open(input_file_path, 'r') as file:
                search_list = file.readlines()
        if len(search_list) == 0:
            print('Error: You must either pass the -s search argument, or add searches to input.txt')
            sys.exit()

    total = args.total if args.total else 1_000_000

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        page.wait_for_timeout(5000)

        for search_for_index, search_for in enumerate(search_list):
            print(f"-----\n{search_for_index} - {search_for}".strip())

            page.locator('//input[@id="searchboxinput"]').fill(search_for)
            page.wait_for_timeout(3000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

            previously_counted = 0
            while True:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(3000)

                if (
                    page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                    >= total
                ):
                    listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
                    listings = [listing.locator("xpath=..") for listing in listings]
                    print(f"Total Scraped: {len(listings)}")
                    break
                else:
                    if (
                        page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                        == previously_counted
                    ):
                        listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                        print(f"Arrived at all available\nTotal Scraped: {len(listings)}")
                        break
                    else:
                        previously_counted = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                        print(f"Currently Scraped: ", page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count())

            charging_station_list = EVChargingStationList()

            for listing in listings:
                try:
                    listing.click()
                    page.wait_for_timeout(5000)

                    name_xpath = '//h1[@class="DUwDvf lfPIob"]'
                    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    type_of_guns_xpath = 'xpath=.//div[contains(@class,"bfdHYd Ppzolf OFBs3e")]//span[@class="JpCtJf"]'
                    power_in_kw_xpath = 'xpath=.//div[contains(@class,"bfdHYd Ppzolf OFBs3e")]//span[@class="NiVgee WAmrC"]'
                    
                    


                    station = EVChargingStation()
                    station.name = page.locator(name_xpath).inner_text() if page.locator(name_xpath).count() > 0 else ""
                    station.address = page.locator(address_xpath).all()[0].inner_text() if page.locator(address_xpath).count() > 0 else ""
                    
                    # Extract types and kW for the particular station
                    type_of_guns_elements = listing.locator(type_of_guns_xpath).all()
                    power_in_kw_elements = listing.locator(power_in_kw_xpath).all()
                    
    
                    
                    types_kw = []
                    for gun, kw in zip(type_of_guns_elements, power_in_kw_elements):
                        types_kw.append(f"{gun.inner_text().strip()} - {kw.inner_text().strip()}")
                    

                    # Combine types and kW into a single column
                    station.type_of_guns = ', '.join([gun.inner_text().strip() for gun in type_of_guns_elements])
                    station.power_in_kw = ', '.join([kw.inner_text().strip() for kw in power_in_kw_elements])
                    
                    

                    
                    charging_station_list.charging_station_list.append(station)
                except Exception as e:
                    print(f'Error occurred: {e}')

            charging_station_list.save_to_excel(f"google_maps_data_{search_for}".replace(' ', '_'))
            charging_station_list.save_to_csv(f"google_maps_data_{search_for}".replace(' ', '_'))

        browser.close()

if __name__ == "__main__":
    main()
