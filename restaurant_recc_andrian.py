from jamaibase import JamAI, protocol as p
import requests
import math
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import pandas as pd
import json
import streamlit as st
import re
from selenium.webdriver.chrome.options import Options



PROJECT_ID = "proj_1e898518d69ddc4fd7f14985"  # Replace with your project ID
PAT = "jamai_pat_c5f3edb108d1ec7187a0fc545852dabec48fb2d85597e5e3"        # Replace with your SK
TABLE_TYPE = p.TableType.chat
OPENER = "Hello! How can I help you today?"
api_key = "" #Replace with google api key


jamai = JamAI(project_id=PROJECT_ID, token=PAT)
print(jamai.api_base)



def get_user_location():
    """Fetch user's location using IP-based geolocation."""
    response = requests.get("https://ipinfo.io")
    data = response.json()
    return data["loc"]

def get_location_google(api_key):
    """Get user location using Google Geolocation API."""
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={api_key}"
    response = requests.post(url)
    if response.status_code == 200:
        data = response.json()
        print(data)
        return {
            "latitude": data["location"]["lat"],
            "longitude": data["location"]["lng"],
            "accuracy": data["accuracy"],
        }
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")




def search_restaurants(api_key, query, latitude, longitude, radius=10000):
    """
    Search for restaurants based on a query using Google Places API.

    Args:
        api_key (str): Google API key.
        query (str): User query (e.g., "spicy food").
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        radius (int): Search radius in meters (default: 2000).

    Returns:
        list: List of nearby restaurants matching the query.
    """
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "key": api_key,
        "query": query,
        "location": f"{latitude},{longitude}",
        "radius": radius,
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        # print(data)
        return data['results']
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    
def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def sort_restaurants(restaurants, user_lat, user_lon):
    """Sort restaurants by 'open now', distance (ascending), and combined score (rating * user_ratings)."""
    for restaurant in restaurants:
        # Extract restaurant coordinates
        location = restaurant["geometry"]["location"]
        rest_lat = location["lat"]
        rest_lon = location["lng"]

        # Calculate distance
        distance = haversine(user_lat, user_lon, rest_lat, rest_lon)
        restaurant["distance"] = distance

        # Calculate combined score
        rating = restaurant.get("rating", 0)
        user_ratings = restaurant.get("user_ratings_total", 0)
        restaurant["combined_score"] = rating * user_ratings

        # Check if the restaurant is open now using your method
        restaurant["open_now"] = restaurant.get("opening_hours", {}).get("open_now", False)

    sorted_restaurants = sorted(
        restaurants,
        key=lambda r: (-r["open_now"], r["distance"], -r["combined_score"])
    )
    return sorted_restaurants


def get_website_link(api_key, place_id):
    """
    Fetch the website link of a restaurant using the Google Places Details API.

    Args:
        api_key (str): Your Google API key.
        place_id (str): Place ID of the restaurant.

    Returns:
        str: Website link or Google Maps URL if available.
    """
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "key": api_key,
        "place_id": place_id,
        "fields": "name,website,url",
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        result = response.json().get("result", {})
        return {
            "name": result.get("name"),
            "website": result.get("website", "No website available"),
            "google_maps_url": result.get("url", "No Google Maps URL available"),
        }
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")



def scrape_menu(sorted_restaurants):
    image_info = []
    menu_info = []
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode (no visible window)
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration for headless mode
    chrome_options.add_argument("--no-sandbox")  # For better compatibility
    chrome_options.add_argument("--disable-dev-shm-usage")  # For overcoming resource limitations
    chrome_options.add_argument("--window-size=1920x1080")  # Set a standard window size

    # Disable logging and other UI components
    chrome_options.add_argument("--disable-extensions")  # Disable extensions if any
    chrome_options.add_argument("--remote-debugging-port=0")  # Disable remote debugging
    chrome_options.add_argument("start-maximized")  # Start the browser maximized (even in headless)
    chrome_options.add_argument("--disable-infobars")  # Disable any info bars or popups in the browser
    chrome_options.add_argument("--disable-browser-side-navigation")  # Disable browser side navigation

    # Ensure that the driver runs without opening any GUI or any browser window
    chrome_options.add_argument("--headless")  # This will ensure it's running without a display.

    driver = webdriver.Chrome(options=chrome_options)
    driver = webdriver.Chrome()
    try:
        for idx, restaurant in enumerate(sorted_restaurants[:5], start=1):
            print(f"Processing restaurant #{idx}: {restaurant['name']}")
            url = "https://gofood.co.id/en"
            driver.get(url)
            try:
                # Set location
                location_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "location-picker"))
                )
                location_value = restaurant['formatted_address']
                driver.execute_script("arguments[0].value = arguments[1];", location_field, location_value)

                # Trigger input and change events
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", location_field)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", location_field)
                # print(f"Location set to: {location_value}")

                # Click Explore button
                explore_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Explore']]"))
                )
                explore_button.click()
                # print("Clicked the Explore button")

                # Click Search button
                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@href='/en/search' and @type='button']"))
                )
                search_button.click()
                # print("Clicked the search button")

                # Enter search query
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "search-query"))
                )
                search_value = restaurant['name']
                search_field.clear()
                search_field.send_keys(search_value)
                # print(f"Entered value into the search field: {search_value}")

                # Click the first div
                first_div = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "(//div[contains(@class, 'bg-gf-background-fill-primary rounded-2xl flex cursor-pointer')])[1]")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", first_div)
                first_div.click()
                # print("Clicked the first div")

                time.sleep(1)  # Allow the page to load

                # Extract JSON data from script tags
                script_tags = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
                json_data = []
                for script in script_tags:
                    try:
                        data = json.loads(script.get_attribute('innerHTML'))
                        json_data.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")

                # Extract image and menu information
                if len(json_data) > 2:
                    menu_info.append(json_data[2])
                else:
                    print("Menu information not found in JSON data.")

                images = driver.find_elements(By.TAG_NAME, "img")
                img_info = [img.get_attribute('src') for img in images if img.get_attribute('src') and img.get_attribute('src').startswith('https:')]
                image_info.append(img_info)

            except TimeoutException as e:
                print(f"Timeout while processing restaurant {restaurant['name']}: {e}")
            except Exception as e:
                print(f"An error occurred for restaurant {restaurant['name']}: {e}")
    finally:
        driver.quit()

    return menu_info, image_info
def main_w_scrape():
    st.title("Simple Restaurant Recommendation")
    user_query = st.text_input("### Enter your location or what you're craving 🍔🍣☕:", placeholder="e.g., Sushi in Jakarta")

    # Initialize progress bar
    progress_bar = st.progress(0)  # Start at 0%
    progress_step = 20  # Increment for each step

    if st.button("Find Restaurants"):
        if user_query.strip():
            # try:
            #     # Step 1: Generate user query
            #     with st.spinner("Generating user query..."):
            #         completion = jamai.table.add_table_rows(
            #             "action",
            #             p.RowAddRequest(
            #                 table_id="search_prompt_generation",
            #                 data=[dict(length=5, user=user_query.strip())],
            #                 stream=False,
            #             ),
            #         )
            #         user_query = completion.rows[0].columns["search prompt"].text
            #     progress_bar.progress(progress_step)  # Update progress
            # except Exception as e:
            #     st.error(f"Error creating user prompt: {str(e)}")

            try:
                # Step 2: Get user location
                with st.spinner("Retrieving your location..."):
                    loc = get_location_google(api_key)
                    lat, lon = loc['latitude'], loc['longitude']
                progress_step += 25
                progress_bar.progress(progress_step)
            except Exception as e:
                st.error(f"Error retrieving user location: {str(e)}")

            try:
                # Step 3: Search for restaurants
                with st.spinner("Searching for nearby restaurants..."):
                    restaurants = search_restaurants(api_key, user_query, lat, lon)
                    if restaurants:
                        sorted_restaurants = sort_restaurants(restaurants, lat, lon)
                        progress_step += 25
                        progress_bar.progress(progress_step)
                    else:
                        st.warning("No restaurants found.")
                        return
            except Exception as e:
                st.error(f"Error retrieving nearby restaurants: {str(e)}")

            try:
                # Step 4: Scrape restaurant menu and images
                with st.spinner("Fetching restaurant menu and images..."):
                    menu_info, image_info = scrape_menu(sorted_restaurants)
                progress_step += 25
                progress_bar.progress(progress_step)
            except Exception as e:
                st.error(f"Error retrieving restaurant menu: {str(e)}")

            try:
                # Step 5: Get recommendations
                with st.spinner("Generating recommendations..."):
                    completion = jamai.table.add_table_rows(
                        "action",
                        p.RowAddRequest(
                            table_id="get_recommendation",
                            data=[dict(length=5, user=user_query.strip(), restaurants_information=menu_info)],
                            stream=False,
                        ),
                    )
                    recommendations = completion.rows[0].columns["summary"].text
                progress_step += 25
                progress_bar.progress(progress_step)
            except Exception as e:
                st.error(f"Error generating recommendations: {str(e)}")

            # Display recommendations and images
            if recommendations:
                recs = recommendations.split("[END]")[0]
                start = recs.split("[SEP]")[0]
                rec = recs.split("[SEP]")[1:]

                st.write(start)
                for i, rest_rec in enumerate(rec):
                    pattern = r"\*\*(.*?)\*\*"
                    parts = re.split(pattern, rest_rec)

                    for j, part in enumerate(parts):
                        if j % 2 == 1:
                            st.header(f"**{part}**")
                        else:
                            st.write(part)

                # st.write("\nHere are some photos of the restaurant food")
                # columns = st.columns(len(image_info[0]))
                # for col, image_url in zip(columns, image_info[0]):
                #     with col:
                #         st.image(image_url, caption="Photo", use_column_width=True)
                    

def main_w_search_jamai():
    st.title("Simple Restaurant Recommendation")
    user_query = st.text_input("### Enter your location or what you're craving 🍔🍣☕:", placeholder="e.g., Sushi in Jakarta")

    # Initialize progress bar
    progress_bar = st.progress(0)  # Start at 0%
    progress_step = 25  # Increment for each step

    if st.button("Find Restaurants"):
        if user_query.strip():
            try:
                # Step 2: Get user location
                with st.spinner("Retrieving your location..."):
                    loc = get_location_google(api_key)
                    lat, lon = loc['latitude'], loc['longitude']
                progress_step += 25
                progress_bar.progress(progress_step)
            except Exception as e:
                st.error(f"Error retrieving user location: {str(e)}")

            try:
                # Step 5: Get recommendations
                with st.spinner("Generating recommendations..."):
                    completion = jamai.table.add_table_rows(
                        "action",
                        p.RowAddRequest(
                            table_id="get_recommendation",
                            data=[dict(length=5, user=user_query.strip())],
                            stream=False,
                        ),
                    )
                    recommendations = completion.rows[0].columns["search_recommendation"].text
                progress_step += 50
                progress_bar.progress(progress_step)
            except Exception as e:
                st.error(f"Error generating recommendations: {str(e)}")

            # Display recommendations and images
            if recommendations:
                recs = recommendations.split("[END]")[0]
                close = recommendations.split("[END]")[1]
                start = recs.split("[SEP]")[0]
                rec = recs.split("[SEP]")[1:]

                st.write(start)
                for i, rest_rec in enumerate(rec):
                    pattern = r"<title>(.*?)</title>*"
                    parts = re.split(pattern, rest_rec)

                    for j, part in enumerate(parts):
                        if j % 2 == 1:
                            st.markdown(f"<h1 style='font-size:32px;'>{part}</h1>", unsafe_allow_html=True)
                        else:
                            img_pattern = r"<img\s+src=['\"](.*?)['\"]></img>"
                            text_parts = re.split(img_pattern, part)
                            
                            for k, sub_part in enumerate(text_parts):
                                if k % 2 == 1:
                                    st.image(sub_part, use_container_width=True)
                                else:
                                    st.write(sub_part)
                st.write(close)
                # st.write("\nHere are some photos of the restaurant food")
                # columns = st.columns(len(image_info[0]))
                # for col, image_url in zip(columns, image_info[0]):
                #     with col:
                #         st.image(image_url, caption="Photo", use_column_width=True)
                    

if __name__ == "__main__":
    main_w_search_jamai()


            

                
