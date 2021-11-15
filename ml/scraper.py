#!/usr/bin/env python3
# -*- coding: utf-8 -*-from bs4 import BeautifulSoup

from bs4 import BeautifulSoup as bs
from datetime import date
import os
import pandas as pd
from selenium import webdriver
import time
from typing import List

#working directories
BASE_DIR = os.path.dirname(os.path.abspath('__file__'))
DATA_DIR = os.path.join(BASE_DIR,'data', 'raw')

def get_all_urls(num_years: int) -> List[str]:
    '''
    Returns the url list from current season to specified number of years ago.
    '''
    end_year = int(date.today().year)
    start_year = end_year - num_years

    # range of seasons to scrape
    seasons = list(reversed(range(start_year,end_year)))

    results_url = '/results/'
    root_url = 'https://www.oddsportal.com/soccer/england/premier-league'
    first_url = root_url + results_url
    #all other season url
    seasons_url = [root_url + '-' + str(season) + '-' + str(season + 1) + results_url for season in seasons]
    #complete url list to be scraped
    all_urls = [first_url] + seasons_url

    return all_urls

def get_text(col):
    '''
    Returns the text of the column.
    '''
    try:
        result = col.text
    except:
        result = None
    return result

if __name__ == '__main__':
    num_years = 10
    driver = webdriver.Chrome('./ml/chromedriver')
    df = pd.DataFrame()
    
    for url in get_all_urls(num_years):
        driver.get(url)
        html = driver.page_source
        soup = bs(html, 'html.parser', from_encoding="utf-8")

        while True:
            prev_page = soup.find_all( 'span', attrs = {'class' : 'active-page'})[0].text

            for col in soup.find_all('tr', attrs = {'deactivate'}):
                df = df.append(
                    {
                        'season' : soup.find_all('span', attrs = {'class' : 'active'})[1].text,
                        'date' : col.findPreviousSibling(attrs = {'center nob-border'}).text[0:-6],
                        'match_name' : col.find('td', attrs = {'class' : 'name table-participant'}).text.replace('\xa0', ''),
                        'result' : col.find('td', attrs = {'class' : 'center bold table-odds table-score'}).text,
                        'h_odd' : get_text(col.find('td', attrs = {'class' : "odds-nowrp"})),
                        'd_odd' : get_text(col.find('td', attrs = {'class' : "odds-nowrp"}).findNext( attrs = {'class' : "odds-nowrp"})),
                        'a_odd' : get_text(col.find('td', attrs = {'class' : "odds-nowrp"}).findNext( attrs = {'class' : "odds-nowrp"}).findNext( attrs = {'class' : "odds-nowrp"}))
                    }, ignore_index=True
                )

            # Go to next page 
            element = driver.find_element_by_partial_link_text('»')
            driver.execute_script("arguments[0].click();", element)
            time.sleep(2)

            # Reload beatifulsoup
            html = driver.page_source
            soup = bs(html, 'html.parser', from_encoding="utf-8")
            #get new page number
            new_page = soup.find_all('span', attrs = {'class' : 'active-page'})[0].text

            if prev_page != new_page:
                continue
            else:
                break

    driver.quit()
    df.to_csv(os.path.join(DATA_DIR, 'epl_matches.csv'), index = False)
