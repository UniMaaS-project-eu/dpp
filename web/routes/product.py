from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from utils import fillInData, httpSession
import config
import forms
import logging
import json
import requests
from urllib.parse import quote

# Logging and Blueprint setup
logger = logging.getLogger(__name__)
productBP = Blueprint('product', __name__)

@productBP.route("/registerProduct", methods=['GET', 'POST'])
def registerProduct():
    userinfo = session.get("userinfo", {})

    if any(role in userinfo.get('roles', []) for role in ['testRole1', 'admin']): # TODO: this shouldn't be like this. It should be a role or something similar rather than a user
        form = forms.RegisterProductForm()
        if form.validate_on_submit():
            data = fillInData(form)
            orionURL = f"{config.orionURL}/ngsi-ld/v1/entities"
            headers = {
                "Content-Type": "application/ld+json"
            }

            try:
                # Register the product in Orion-LD
                response = httpSession.post(orionURL, json=data, headers=headers)
                if response.status_code in [201, 204]:
                    flash('Product successfully registered on the website.', 'success')
                    return redirect(url_for('general.home'))
                else:
                    flash(f'Error registering product in Orion‑LD: {response.status_code} - {response.text}', 'danger')

            except requests.exceptions.RequestException as e:
                logger.error(f"Connection error to Orion-LD: {e}")
                flash(f'Connection error with Orion‑LD: {str(e)}', 'danger')

        return render_template('register_product.html', title='Register product', form=form, userinfo=userinfo)
    else:
        flash('You must be an administrator to access this function.', 'warning')
        return redirect(url_for('general.home'))


@productBP.route("/search", methods=['GET', 'POST'])
def search():
    itemsSearch = None
    searchQuery = ""
    characteristic = ""
    warningMsg = ""

    userinfo = session.get("userinfo", {})

    if request.method == 'POST':
        searchQuery = request.form.get('search')
        characteristic = request.form.get('characteristic')

        if not characteristic:
            warningMsg = "You must select a characteristic to query the products"
        else:
            itemsSearch = searchItems(searchQuery, characteristic)
            if config.debug:
                logger.info(f"Items search: {itemsSearch}")  # Debugging
        
    return render_template('search.html', title='Search', items_search=itemsSearch, search_query=searchQuery, warning_message=warningMsg, userinfo=userinfo)


def searchItems(search_query, characteristic):
    apiURL = f"{config.apiRestURL}/unimaas/query?characteristic={quote(characteristic)}&searchTerm={quote(search_query)}"

    try:
        response = requests.get(apiURL)
        response.raise_for_status()  # Throw an error for bad responses (4xx or 5xx)

        try: 
            if response.status_code != 200:
                return []
            data = response.json()
            if config.debug:
                logger.info(f"Data received from API: {data}")
            return data
        except ValueError:
            # If the response is not valid JSON, log the error
            logger.error("The API response is not valid JSON.")
            return []

    except requests.exceptions.RequestException as e:
        logger.error(f"Error in API request: {e}")
        return []