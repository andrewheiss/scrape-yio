#!/usr/bin/env python3

# --------------
# Load modules
# --------------
import config
import requests
from bs4 import BeautifulSoup
from random import choice


# ---------
# Classes
# ---------
class YIO():
    """Connect to the Yearbook of International Organizations through
    Duke's Shibboleth authentication system.
    """
    def __init__(self):
        self.s = requests.session()
        self.s.headers.update({"User-Agent": choice(config.user_agents)})

        self.login_through_duke()

    def login_through_duke(self):
        """Bounce between all the different authentication layers to log into
        the Yearbook site.

        Leaves self.s logged in and ready to be used for all other YIO URLs
        """

        # URLs to be used
        yio_url = "http://ybio.brillonline.com.proxy.lib.duke.edu/ybio"
        shib_url = "https://shib.oit.duke.edu/idp/profile/SAML2/POST/SSO"
        shib_login_url = "https://shib.oit.duke.edu/idp/authn/external"

        # ----------------------------------------------------------------
        # Step 1: Go to the first YIO page to get authentication cookies
        # ----------------------------------------------------------------
        initial_yio_page = self.s.get(yio_url).text

        if "Shibboleth Authentication Request" not in initial_yio_page:
            raise RuntimeError("Did not correctly connect to the initial YIO proxy page.")
        else:
            soup = BeautifulSoup(initial_yio_page)
            relaystate = soup.find(attrs={"name": "RelayState"})
            samlrequest = soup.find(attrs={"name": "SAMLRequest"})

            # Use these two values in the POST data
            saml_relay_data = {"RelayState": relaystate['value'],
                               "SAMLRequest": samlrequest['value']}

        # -------------------------------------------------------------
        # Step 2: Go to Duke's login page with the YIO SAML POST data
        # -------------------------------------------------------------
        duke_shib_page = self.s.post(shib_url, data=saml_relay_data).text

        if "This service requires cookies" in duke_shib_page:
            raise RuntimeError("Did not get the correct Duke login page.")
        else:
            duke_form_data = {
                "j_username": config.duke_username,
                "j_password": config.duke_password,
                "passwordEntered": "1"
            }

        # ------------------------------------------------------------
        # Step 3: Submit Duke's login form and get redirected to YIO
        # ------------------------------------------------------------
        response_yio = self.s.post(shib_login_url, data=duke_form_data).text

        if "you must press the Continue button once to proceed" not in response_yio:
            raise RuntimeError("Did not login to Duke or redirect to YIO.")
        else:
            soup = BeautifulSoup(response_yio)

            action_url = soup.find('form')['action']
            relaystate = soup.find(attrs={"name": "RelayState"})
            samlresponse = soup.find(attrs={"name": "SAMLResponse"})

            saml_response_data = {"RelayState": relaystate['value'],
                                  "SAMLResponse": samlresponse['value']}

        # --------------------------------------------------------------
        # Step 4: Submit the final authenticated SAML POST data to YIO
        # --------------------------------------------------------------
        self.s.post(action_url, data=saml_response_data)

        # \ (•◡•) /  All logged in!  \ (•◡•) /


# ------------
# Run script
# ------------
def main():
    """Run actual script."""
    yio = YIO()

    url = "http://ybio.brillonline.com.proxy.lib.duke.edu/ybio/v3/"
    print(yio.s.get(url).text)


if __name__ == '__main__':
    main()
