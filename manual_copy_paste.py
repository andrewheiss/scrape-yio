#!/usr/bin/env python3

# --------------
# Load modules
# --------------
# My modules
import config
from yio import DB

# Pip-installed modules
import logging

# Just parts of modules
from collections import namedtuple
from random import choice
from time import sleep
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException

# Start log
logger = logging.getLogger(__name__)


# --------------------
# Manually get pages
# --------------------
# TODO: Switch randomly between Chrome and Firefox
# TODO: Run in VM so I can minimize it while it does its thing
# Or use PhantomJS: http://stackoverflow.com/a/23898148/120898

# This is all totally procedural, not functional or object-oriented at all,
# but that's okay because it's really just replicating the exact procedures
# a human does (and I don't want to OOP it, since this is all just temporary)

def get_page(browser, url):
    browser.get(url)
    logger.info(browser.title)

    # There are actual ways to check for alerts with Selenium,
    # but this works well enough.
    try:
        browser.switch_to.alert.accept()
    except NoAlertPresentException:
        pass

    content = browser.find_element_by_id("content")
    return(content.get_attribute('innerHTML'))


# Log in through Duke
browser = webdriver.Firefox()
browser.get("http://ybio.brillonline.com.proxy.lib.duke.edu")

assert "NetID Services" in browser.title
logger.info("Logging in through Duke.")

username_input = browser.find_element_by_id("j_username")
password_input = browser.find_element_by_id("j_password")

username_input.send_keys(config.duke_username)
password_input.send_keys(config.duke_password)

browser.find_element_by_id("Submit").click()

# Get, save, wait, repeat
print(get_page(browser, "http://ybio.brillonline.com.proxy.lib.duke.edu/s/or/en/1100045464"))
sleep(10)
print(get_page(browser, "http://ybio.brillonline.com.proxy.lib.duke.edu/s/or/en/1122271397"))

# All done
browser.close()
