from scarf import app
from core import redirect_back, SiteImage, SiteImageEditor, NoImage, new_img
from main import page_not_found, PageData
from access import check_mod, check_logged_in
import core

from flask import make_response, url_for, request, render_template, session, flash, redirect, send_file
import logging
import base64

logger = logging.getLogger(__name__)

#TODO: rename to /image/new
@app.route('/newimg', methods=['POST'])
@check_logged_in
def newimg():
    """
    :URL: /newimg
    :Method: POST

    Upload a new image. 
    """
    pd = PageData()
    if request.method == 'POST':
        if 'img' in request.files:
            if request.form['title'] == '':
                title = request.files['img'].filename
            else:
                title = request.form['title']

            if 'username' in session:
                userid = pd.authuser.uid
            else:
                userid = None

            img = new_img(request.files['img'], title, request.form['parent'], userid, request.remote_addr)

            if img:
                flash('Uploaded {}'.format(request.files['img'].filename))
                return redirect_back('/image/' + str(img))
            else:
                flash('An error occurred while processing {}'.format(request.files['img'].filename))

        return redirect_back(url_for('index'))

@app.route('/image/<img_id>/reparent', methods=['POST'])
@check_mod
def reparent(img_id):
    """
    :URL: /reparent
    :Method: POST

    Reparent an image. 
    """
    pd = PageData()
    if request.method == 'POST':
        newid = request.form['parent']

        try:
            img = core.SiteImage.create(img_id)
            item = core.SiteItem.create(newid)
        except (core.NoItem, core.NoImage):
            return page_not_found()
            

        if img:
            img.reparent(newid)
            return redirect_back('/image/' + str(img))
        else:
            flash('Unable to reparent {}'.format(img_id))

        return redirect_back(url_for('index'))

@app.route('/image/<img_id>/delete')
@check_mod
def delete_image(img_id):
    """
    :URL: /image/<img_id>/delete

    Delete an image
    """

    pd = PageData()

    try:
        delimg = SiteImage.create(img_id)
        parent = delimg.parent
        delimg.delete()
    except NoImage:
        return page_not_found()

    flash(delimg.tag + " has been deleted")

    if 'mod' in request.referrer:
        return redirect(url_for('moderate'))
    else:
        return redirect('/item/' + str(parent))

@app.route('/image/<img_id>/flag')
@check_logged_in
def flag_image(img_id):
    """
    :URL: /image/<img_id>/flag

    Flag an image for review by a moderator.

    .. todo:: Add support for a note and record who flagged it.
    """

    pd = PageData()

    try:
        flagimg = SiteImage.create(img_id)
        flagimg.flag()
    except NoImage:
        return page_not_found()

    flash("The image has been flagged and will be reviewed by a moderator.")

    return redirect_back('index') 

@app.route('/image/<img_id>/full')
def serve_full(img_id):
    """
    :URL: /image/<img_id>/full

    Retrieve the raw image and return it.
    """

    try:
        simg = SiteImage.create(img_id)

        resp = make_response(base64.b64decode(simg.image()))
        resp.content_type = "image/jpeg"
        return resp
    except (IOError, NoImage):
        return page_not_found()

@app.route('/image/<img_id>')
def show_image(img_id):
    """
    :URL: /image/<img_id>

    Render a template for viewing an image.
    """

    pd = PageData()

    try:
        pd.img = SiteImage.create(img_id)
        pd.title=pd.img.tag
    except NoImage:
        return page_not_found()

    return render_template('image.html', pd=pd)

@app.route('/image/<img_id>/edit')
@check_mod
def edit_image(img_id):
    """
    :URL: /image/<img_id>/edit

    Very basic image editor. Applies a list of operations to an image
    and either presents a preview back to the user or saves it to the
    database as a new image.
    """

    pd = PageData()
    min_size = 200

    try:
        img = SiteImageEditor(img_id)
    except NoImage:
        return page_not_found()

    preview = request.args.get('preview')
    save = request.args.get('save')

    pd.img = img
    pd.ops = ''
    pd.num_ops = 0

    for op in range(1,20):
        command = request.args.get('op{}'.format(op))
        if command:
            if command == 'rotate':
                degrees = request.args.get('op{}_degrees'.format(op))

                try:
                    degrees = int(degrees)
                except:
                    return page_not_found()

                img.rotate(degrees)
                pd.ops = "{}&op{}=rotate&op{}_degrees={}".format(pd.ops, op, op, degrees)
                pd.num_ops = op
            elif command == 'crop':
                x1 = request.args.get('op{}_x1'.format(op))
                y1 = request.args.get('op{}_y1'.format(op))
                x2 = request.args.get('op{}_x2'.format(op))
                y2 = request.args.get('op{}_y2'.format(op))

                try:
                    x1 = int(x1)
                    y1 = int(y1)
                    x2 = int(x2)
                    y2 = int(y2)
                except:
                    return page_not_found()

                new_width = x2 - x1
                new_height = y2 - y1

                if new_width < min_size:
                    flash("The selection is too narrow, please make a larger selection. If your image is below {} pixels in width you will not be able to crop it.".format(min_size))
                    return redirect_back(url_for('index'))
                if new_height < min_size:
                    flash("The selection is too short, please make a larger selection. If your image is below {} pixels in width you will not be able to crop it.".format(min_size))
                    return redirect_back(url_for('index'))

                img.crop(x1, y1, x2, y2)
                pd.ops = "{base}&op{op}=crop&op{op}_x1={x1}&op{op}_y1={y1}&op{op}_x2={x2}&op{op}_y2={y2}".format(base=pd.ops, op=op, x1=x1, y1=y1, x2=x2, y2=y2)
                pd.num_ops = op
            else:
                return page_not_found()
 
    if preview == 'true':
        return send_file(img.preview(), mimetype='image/jpeg')

    if save:
        if 'username' in session:
            userid = pd.authuser.uid
        else:
            userid = None

        new_img = img.save(userid, request.remote_addr)
        return redirect('/image/' + str(new_img))

    return render_template('imageedit.html', pd=pd)
