#!/usr/bin/env python3

# ------------------------------------------------------------------------------
# NB: It's best to run this in a virutal machine so it's minimizable/hideable.
# Selenium can't run browsers in the background.
# ------------------------------------------------------------------------------

# --------------
# Load modules
# --------------
# My modules
import config
import scrape_yio
from yio import DB

# Pip-installed modules
import logging

# Just parts of modules
from collections import namedtuple
from random import choice, sample
from time import sleep
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

# Start log
logger = logging.getLogger(__name__)


# Determine which pages to get
def get_ids(db, k):
    # Create sets of the primary and foreign key ids from all the tables
    db.c.execute("SELECT id_org FROM organizations")
    master_list = {row_id[0] for row_id in db.c.fetchall()}

    db.c.execute("SELECT fk_org FROM organizations_raw")
    already_processed = {row_id[0] for row_id in db.c.fetchall()}

    db.c.execute("SELECT fk_org FROM data_raw")
    saved_raw = {row_id[0] for row_id in db.c.fetchall()}

    # Determine which ids in the master list haven't already been processed
    orgs_todo = master_list - already_processed - saved_raw

    # Select a random subset of uncaptured organizations
    OrgInfo = namedtuple('OrgInfo', ['id_org', 'name', 'url'])
    db.add_factory(factory=OrgInfo)

    do_these = [str(org) for org in sample(orgs_todo, k)]
    subset_sql = ("SELECT id_org, org_name, org_url FROM organizations "
                  "WHERE id_org IN ({0})""".format(", ".join(do_these)))
    db.c.execute(subset_sql)
    orgs_to_process = db.c.fetchall()

    return(orgs_to_process)


# Manually get pages
def get_page(browser, url):
    browser.get(url)
    logger.info(browser.title)

    # Properly(!) handle the broken Google Maps warning alert
    # Via http://stackoverflow.com/a/19019311/120898
    try:
        WebDriverWait(browser, 3).until(EC.alert_is_present())
        browser.switch_to.alert.accept()
    except TimeoutException:
        pass

    # Scroll down, click, wait, scroll up, just for kicks
    browser.execute_script("window.scrollTo(0, " +
                           "document.body.scrollHeight/{0});"
                           .format(choice(range(2, 5))))
    # Clicking does weird things in Chrome
    # (i.e. clicks on the top centered element)
    # browser.find_element_by_tag_name("body").click()
    sleep(choice(range(1, 3)))
    browser.execute_script("window.scrollTo(0, {0});"
                           .format(choice(range(0, 200))))

    # We can just select just the #content div...
    # content = browser.find_element_by_id("content")
    # return(content.get_attribute('innerHTML'))

    # But, just to be safe, save the whole stinking page
    return(browser.page_source)


# Log in
def login_manually(browser):
    browser.get("http://ybio.brillonline.com.proxy.lib.duke.edu")

    assert "NetID Services" in browser.title
    logger.info("Logging in through Duke.")

    username_input = browser.find_element_by_id("j_username")
    password_input = browser.find_element_by_id("j_password")

    username_input.send_keys(config.duke_username)
    password_input.send_keys(config.duke_password)

    browser.find_element_by_id("Submit").click()


# Parse the raw HTML and save as raw columned data
def parse_raw_html():
    OrgPage = namedtuple('OrgPage', ['id_org', 'org_html'])

    # Open database and log into YIO
    db = DB()
    db.add_factory(factory=OrgPage)

    db.c.execute("SELECT fk_org, org_html FROM data_raw")

    orgs = db.c.fetchall()

    db.add_factory(None)  # Clear custom factory
    for org in orgs[0:1]:
        logger.info("Parsing details for {0}".format(org.id_org))
        scrape_yio.parse_individual_org(None, org, db)


# This is all totally procedural, not functional or object-oriented at all,
# but that's okay because it's really just replicating the exact procedures
# a human does (and I don't want to OOP it, since this is all just temporary)
#
# Chromedriver: https://sites.google.com/a/chromium.org/chromedriver/
#
# GA blocking extension from https://tools.google.com/dlpage/gaoptout
# Chrome's CRX: http://chrome-extension-downloader.com
# Firefox: https://dl.google.com/analytics/optout/gaoptoutaddon_0.9.6.xpi
#
def get_raw_html(num_orgs):
    # Choose a random browser
    if choice(["Firefox", "Firefox"]) is "Firefox":
        fp = webdriver.FirefoxProfile()
        fp.add_extension(extension='bin/gaoptoutaddon_0.9.6.xpi')
        browser = webdriver.Firefox(firefox_profile=fp)
    else:
        chrome_options = Options()
        chrome_options.add_extension('bin/ga-optout.crx')
        browser = webdriver.Chrome("bin/chromedriver",
                                   chrome_options=chrome_options)

    login_manually(browser)

    db = DB()
    orgs_to_get = get_ids(db, num_orgs)

    # Get, save, wait, repeat
    for i, org in enumerate(orgs_to_get):
        logger.info("{1}: Getting details for {0}.".format(org.name, i + 1))
        raw_html = get_page(browser, org.url)
        data_to_insert = {"fk_org": org.id_org, "org_html": raw_html}
        db.insert_dict(data_to_insert, table="data_raw")
        wait = choice(config.wait_time)
        logger.info("Waiting for {0} seconds before moving on".format(wait))
        sleep(wait)

    browser.close()
    db.close()


if __name__ == '__main__':
    get_raw_html(num_orgs=2)
