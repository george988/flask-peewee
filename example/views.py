# coding: utf-8
import json
import re
from functools import wraps

from functools import wraps
from flask import Flask, render_template, session, redirect, url_for, escape, request, current_app
from flask import jsonify
from pymongo import MongoClient


import datetime

from flask import request, redirect, url_for, render_template, flash

from flask_peewee.utils import get_object_or_404, object_list

from app import app
from auth import auth
from models import User, Message, Relationship


from flask.ext.assets import Environment, Bundle
assets = Environment(app)
css_all = Bundle('datatable/css/demo_page.css','datatable/css/demo_table_jui.css')
assets.register('css_all',css_all)


connection = MongoClient()

 
def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f(*args,**kwargs).data) + ')'
            return current_app.response_class(content, mimetype='application/javascript')
        else:
            return f(*args, **kwargs)
    return decorated_function


@app.route('/test', methods=['GET'])
@support_jsonp
def test():
    return jsonify({"foo":"bar"})


@app.route('/domainupload/', methods=['GET', 'POST'])
@auth.login_required
def domainupload():
    if request.method == 'POST':
        domain_str = request.form['domains']
        domain_regex=r'[a-z0-9A-Z][a-zA-Z0-9\-]*[a-zA-S0-9]?\.[a-zA-Z]+'
        da=set(re.findall(domain_regex, domain_str))
        ka=[];
        for da_item in da:
            ka.append(da_item.split('.')[0])

        #da=re.split('\s+',domain_str)
        #ka=da
        #domains = connection.test.domain1.find({'_id': {"$in":['zuqiu','ruanjian','mama','ma','abc','4399']}})
        domains = connection.test.keyword.find({'keyword': {"$in": ka}})
        objects = []
        for domain in domains:
            for da_item in da:
                if da_item.split('.')[0]==domain['keyword']:
                    domain=updatedomainfromdb(domain,da_item)
                    objects.append(domain)
        return render_template('domains.html', domains=objects)

    return '''
        <form action="" method="post">
            <p><textarea cols="40" rows="8" name="domains">
            google.com abc.com hao.com hao123.com ruanjian.com ha.com
                </textarea>
            <p><input type=submit value='upload and process'>
        </form>
    '''



@app.route("/domain/<dn>")
#@support_jsonp
def show_domain_detail(dn):
   domainname=dn
   keyword=domainname.split('.')[0]
   domain = connection.test.keyword.find_one({'keyword': keyword})
   if domain:
    domain=updatedomainfromdb(domain,domainname)
    return render_template('domain.html', domain=domain)
   else:
    return domainname+ " not found"


def updatedomainfromdb(domain,domainname):
    if 'alexa_content' in domain:
      result=dict( (n,int(v)) for n,v in (a.split('=') for a in domain['alexa_content'].split(";") ) )
      sorted_result= sorted(result.items(), key=lambda x: int(x[1])-1000000 if x[0].endswith(".cn")  else  int(x[1]) )
      domain['alexa_content_list']=sorted_result
    if 'alexa_rank' in domain:
        for alexa_dict in domain['alexa_rank']:
            if domainname in alexa_dict:
                domain['alexa']=alexa_dict.get(domainname)
                break
    domain['domainname']=domainname 
    return domain            


@app.route("/keyword/<_id>")
#@support_jsonp
def show_post(_id):
   # NOTE!: converting _id from string to ObjectId before passing to find_one
   #if _id.isnumeric():
    #_id=int(_id)
   domain = connection.test.keyword.find_one({'keyword': _id})
   if domain:
    #return jsonify(domain)
    #return domain['alexa_content']
    if 'alexa_content' in domain:
      result=dict( (n,int(v)) for n,v in (a.split('=') for a in domain['alexa_content'].split(";") ) )
      sorted_result= sorted(result.items(), key=lambda x: int(x[1])-1000000 if x[0].endswith(".cn")  else  int(x[1]) )
      domain['alexa_content']=sorted_result
    #return  jsonify(sorted_result)
    #return jsonify(domain),200, {'Content-Type': 'application/json; charset=utf-8'}
    #return domain['pinyin']
    #return jsonify(domain)
    #return jsonify( unicode(domain, 'utf-8'))
    #if 'pinyin' in domain:
    #  domain['pinyin']=domain['pinyin'].decode("utf-8")
    # return json.dumps(domain),200, {'Content-Type': 'application/json; charset=utf-8'}
    #return jsonify(domain)
    return render_template('domain.html', domain=domain)



   return 'Nothing found for this keyword'



@app.route('/')
def homepage():
    if auth.get_logged_in_user():
        return private_timeline()
    else:
        return public_timeline()

@app.route('/private/')
@auth.login_required
def private_timeline():
    user = auth.get_logged_in_user()

    messages = Message.select().where(
        Message.user << user.following()
    ).order_by(Message.pub_date.desc())

    return object_list('private_messages.html', messages, 'message_list')

@app.route('/public/')
def public_timeline():
    messages = Message.select().order_by(Message.pub_date.desc())
    return object_list('public_messages.html', messages, 'message_list')

@app.route('/join/', methods=['GET', 'POST'])
def join():
    if request.method == 'POST' and request.form['username']:
        try:
            user = User.select().where(User.username==request.form['username']).get()
            flash('That username is already taken')
        except User.DoesNotExist:
            user = User(
                username=request.form['username'],
                email=request.form['email'],
                join_date=datetime.datetime.now()
            )
            user.set_password(request.form['password'])
            user.save()

            auth.login_user(user)
            return redirect(url_for('homepage'))

    return render_template('join.html')

@app.route('/following/')
@auth.login_required
def following():
    user = auth.get_logged_in_user()
    return object_list('user_following.html', user.following(), 'user_list')

@app.route('/followers/')
@auth.login_required
def followers():
    user = auth.get_logged_in_user()
    return object_list('user_followers.html', user.followers(), 'user_list')

@app.route('/users/')
def user_list():
    users = User.select().order_by(User.username)
    return object_list('user_list.html', users, 'user_list')

@app.route('/users/<username>/')
def user_detail(username):
    user = get_object_or_404(User, User.username==username)
    messages = user.message_set.order_by(Message.pub_date.desc())
    return object_list('user_detail.html', messages, 'message_list', person=user)

@app.route('/users/<username>/follow/', methods=['POST'])
@auth.login_required
def user_follow(username):
    user = get_object_or_404(User, User.username==username)
    Relationship.get_or_create(
        from_user=auth.get_logged_in_user(),
        to_user=user,
    )
    flash('You are now following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@app.route('/users/<username>/unfollow/', methods=['POST'])
@auth.login_required
def user_unfollow(username):
    user = get_object_or_404(User, User.username==username)
    Relationship.delete().where(
        Relationship.from_user==auth.get_logged_in_user(),
        Relationship.to_user==user,
    ).execute()
    flash('You are no longer following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@app.route('/create/', methods=['GET', 'POST'])
@auth.login_required
def create():
    user = auth.get_logged_in_user()
    if request.method == 'POST' and request.form['content']:
        message = Message.create(
            user=user,
            content=request.form['content'],
        )
        flash('Your message has been created')
        return redirect(url_for('user_detail', username=user.username))

    return render_template('create.html')

@app.route('/edit/<int:message_id>/', methods=['GET', 'POST'])
@auth.login_required
def edit(message_id):
    user = auth.get_logged_in_user()
    message = get_object_or_404(Message, Message.user==user, Message.id==message_id)
    if request.method == 'POST' and request.form['content']:
        message.content = request.form['content']
        message.save()
        flash('Your changes were saved')
        return redirect(url_for('user_detail', username=user.username))

    return render_template('edit.html', message=message)
