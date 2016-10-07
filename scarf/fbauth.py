from scarf import app
from core import SiteUser, new_user, NoUser, AuthFail, redirect_back, check_key_exists, new_key, SiteKey, NoKey
from user import check_new_user
from main import PageData
from config import FB_CLIENT_ID, FB_SECRET_ID, SITEURL

import json
import urllib3.contrib.pyopenssl
import certifi
import urllib3
import string
import random
import logging

from flask import redirect, url_for, request, render_template, session, flash
from oauthlib.oauth2 import MismatchingStateError, MissingTokenError
from requests_oauthlib import OAuth2Session
from requests_oauthlib.compliance_fixes import facebook_compliance_fix

authorization_base_url = 'https://www.facebook.com/dialog/oauth'
token_url = 'https://graph.facebook.com/oauth/access_token'

# https://urllib3.readthedocs.io/en/latest/user-guide.html#ssl-py2
urllib3.contrib.pyopenssl.inject_into_urllib3()
http = urllib3.PoolManager(
    cert_reqs='CERT_REQUIRED',
    ca_certs=certifi.where())

logger = logging.getLogger(__name__)

def redirect_uri():
    if SITEURL:
        return "{}{}".format(SITEURL, url_for('fblogin'))
    else:
        return "{}{}".format('https://test.scarfage.com/', url_for('fblogin'))

@app.route('/login_with_facebook', methods=['GET', 'POST'])
def fbredirect():
    """
    :URL: /login_with_facebook
    :Methods: GET, POST

    Redirects the user to a Facebook login page
    """

    facebook = OAuth2Session(FB_CLIENT_ID, redirect_uri=redirect_uri())
    facebook = facebook_compliance_fix(facebook)
    authorization_url, state = facebook.authorization_url(authorization_base_url)

    logger.info('Facebook redirect for ip {}'.format(request.remote_addr))
    session['facebook_state'] = state
    return redirect('{}&scope=public_profile,email'.format(authorization_url))

@app.route('/oauth/facebook')
def fblogin():
    """
    :URL: /fbauth
    :Methods: GET

    Facebook auth callback URI
    """

    try:
        facebook = OAuth2Session(FB_CLIENT_ID, redirect_uri=redirect_uri(), state=session['facebook_state'])
        facebook = facebook_compliance_fix(facebook)
    except KeyError:
        flash('Unable to log in via Facebook, do you have cookies enabled for this site?')
        logger.info('Failed to find Facebook state information for {}'.format(request.remote_addr))
        return redirect_back(url_for('index'))

    try:
        token = facebook.fetch_token(token_url, client_secret=FB_SECRET_ID, authorization_response=request.url)
        response = facebook.get('https://graph.facebook.com/v2.5/me?fields=id,name,email').content
    except (MismatchingStateError, MissingTokenError) as e:
        flash('Facebook was not able to provide us with the information we need to authenticate your account.')
        logger.info('Facebook auth exception for {}: {}'.format(request.remote_addr, e))
        return redirect_back(url_for('index'))

    decoded = json.loads(response)

    user_key = 'oauth-facebook-{}'.format(decoded['id'])

    try:
        username = SiteKey(user_key)
        user = SiteUser(username.value)

        if user.accesslevel is 0:
            flash('Your account has been banned')
            logger.info('Successful Facebook auth for {} but user is banned'.format(user.username))
            session.pop('username', None)
            session.pop('facebook_id', None)
            username.delete()
            return redirect_back(url_for('index'))

        user.seen()
        session['username'] = user.username
        session['facebook_token'] = token
        session['facebook_id'] = decoded['id']
        session['facebook_name'] = decoded['name']
        session['facebook_email'] = decoded['email']
        session.permanent = True

        # This profile update block won't be needed out of testing
        profile = user.profile()
        profile.profile['facebook_id'] = session['facebook_id']
        profile.update()
        # end block

        flash('You were successfully logged in')
        logger.info('Successful Facebook auth for {} (ID {})'.format(user.username, decoded['id']))
        return redirect_back(url_for('index'))
    except NoKey:
        session['facebook_token'] = token
        session['facebook_id'] = decoded['id']
        session['facebook_name'] = decoded['name']
        session['facebook_email'] = decoded['email']

        pd = PageData();
        pd.title = "Log in with Facebook"
        logger.info('Successful Facebook auth for ID {} but this person has no linked account'.format(decoded['id']))
        return render_template('new_facebook_user.html', pd=pd)

    flash('Facebook authentication failed :(')
    logger.info('Facebook auth error for {}'.format(request.remote_addr))
    return redirect_back(url_for('index'))

@app.route('/user/<username>/facebook/link', methods=['GET', 'POST'])
def link_facebook_account(username):
    pd = PageData();

    if 'username' in session:
        try:
            user = SiteUser.create(session['username'])
            user.authenticate(request.form['password'])
        except (NoUser, AuthFail):
            flash('Authentication failed, please check your password and try again.')
            logger.info('Facebook auth link failed for username {} ip {}'.format(user.username, request.remote_addr))
            return redirect_back(url_for('index'))

        user_key = 'oauth-facebook-{}'.format(session['facebook_id'])
        new_key(user_key, session['username'])

        profile = user.profile()
        profile.profile['facebook_id'] = session['facebook_id']
        profile.update()

        flash('Your account is now linked to Facebook.')
        logger.info('Facebook auth linked for username {} ID {} ip {}'.format(user.username, session['facebook_id'], request.remote_addr))
        return redirect(url_for('index'))

    return redirect_back(url_for('index'))

@app.route('/newuser/facebook', methods=['POST'])
def new_facebook_user():
    pd = PageData();

    if not check_new_user(request, nopass=True):
        pd.username = request.form['username']
        pd.email = request.form['email']
        return redirect_back(url_for('index'))

    password = ''.join(random.choice(string.printable) for _ in range(100))
    if not new_user(request.form['username'], password, request.form['email'], request.remote_addr):
        return render_template('error.html', pd=pd)

    user_key = 'oauth-facebook-{}'.format(session['facebook_id'])
    new_key(user_key, request.form['username'])

    try:
        user = SiteUser.create(request.form['username'])
        session['username'] = user.username
        profile = user.profile()
        profile.profile['facebook_id'] = session['facebook_id']
        profile.update()
    except (NoUser, AuthFail):
        return render_template('error.html', pd=pd)

    logger.info('New Facebook user {} ID {} ip {}'.format(user.username, session['facebook_id'], request.remote_addr))
    flash('Welcome ' + request.form['username'])
    return redirect(url_for('index'))
