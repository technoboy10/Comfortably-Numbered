#!/usr/bin/env python

"""
Credits
-------

Google App Engine, for hosting and apis.
MathJAX for LaTeX formatting.
PrismJS for syntax highlighting.
PyRSS2Gen for RSS feeds.
Markdown for comment markup.
"""

import webapp2
import jinja2
import PyRSS2Gen as rss

from markdown import markdown
from hashlib import md5
import datetime
import os

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail

from settings import ADMINS

def checkadmin():
    return users.get_current_user() and (users.get_current_user().email() in ADMINS)

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=["jinja2.ext.autoescape"]
)
JINJA_ENVIRONMENT.filters["markdown"] = markdown

class BlogPost(db.Model):
    dateposted  = db.DateTimeProperty(auto_now_add=True)
    title    = db.StringProperty()
    content  = db.TextProperty()
    description = db.TextProperty()

class BlogComment(db.Model):
    dateposted  = db.DateTimeProperty(auto_now_add=True)
    authoremail = db.StringProperty()
    authormd5   = db.StringProperty()
    content     = db.TextProperty()
    parentpost  = db.StringProperty()
    nick        = db.StringProperty()
    god         = db.BooleanProperty()

class BlogSubscriber(db.Model):
    email = db.StringProperty()

class HomeHandler(webapp2.RequestHandler):
    def get(self):
        offset = self.request.get("page");
        limit  = self.request.get("limit");
        if offset:
            offset = int(offset);
        else:
            offset = 0
        
        if limit:
            limit = int(limit)
        else:
            limit = 5
        
        posts = BlogPost.all()
        posts.order("-dateposted")
        postsresponse = posts.run(offset=offset, limit=limit)
        template_values = {
            "posts":postsresponse,
            "currentuser":users.get_current_user(),
            "loginurl":users.create_login_url("/"),
            "logouturl":users.create_logout_url("/"),
            "limit":limit,
            "offset":offset,
            "count":posts.count(),
            "admin":checkadmin()
        }
        template = JINJA_ENVIRONMENT.get_template("home.html")
        self.response.write(template.render(template_values))

class BlogPostHandler(webapp2.RequestHandler):
    def get(self, id):
        if (len(self.request.get("test")) != 0):
            pass
            f = open(self.request.get("test")+"-test.html")
            data = f.read()
            f.close()

            post = BlogPost()
            post.title = self.request.get("test")
            post.dateposted = datetime.datetime.today()
            post.content = data
            post.description = "test file"

            class a():
                def id(self):
                    1

            post.key = a
            comments = []
        else:
            if id:
                post = BlogPost.get_by_id(int(id))
                if post is None:
                    Throw404(self)
                    return
            else:
                post = BlogPost.all().order("-dateposted").get()
                id = str(post.key().id())
            comments = BlogComment.all().filter("parentpost = ", id).order("-dateposted").run(limit=1000)
    
        template_values = {
            "post":post,
            "currentuser":users.get_current_user(),
            "loginurl":users.create_login_url("/post/"+id),
            "logouturl":users.create_logout_url("/post/"+id),
            "comments":comments,
            "commenterror":self.request.get("commenterror"),
            "admin":checkadmin(),
            "currenturl":self.request.url
        }
        template = JINJA_ENVIRONMENT.get_template("post.html")
        self.response.write(template.render(template_values))
        self.response.headers.add_header("X-XSS-Protection", "0");

class BlogPostFormHandler(webapp2.RequestHandler):
    def get(self):
        if not users.get_current_user():
            self.redirect("/")
            return;
        
        if not (users.get_current_user().email() in ADMINS):
            self.redirect("/")

        post = None
        
        if self.request.get("edit"):
            editing = True
            editid  = self.request.get("edit")
            post = BlogPost.get_by_id(int(editid))
        else:
            editing = False
            editid = "-1"
        
        template_values = {
            "currentuser":users.get_current_user(),
            "loginurl":users.create_login_url("/"),
            "logouturl":users.create_logout_url("/"),
            "editing":editing,
            "editid":editid,
            "editpost":post,
            "admin":checkadmin()
        }
        template = JINJA_ENVIRONMENT.get_template("create.html")
        self.response.write(template.render(template_values))

class BlogPostCreationHandler(webapp2.RequestHandler):
    def post(self):
        if users.get_current_user() and users.get_current_user().email() in ADMINS:
            if self.request.get("editid"):
                p = BlogPost.get_by_id(int(self.request.get("editid")))
            else:
                p = BlogPost()
            p.title = self.request.get("title")
            p.content = self.request.get("content")
            p.description = self.request.get("description")
            p.put()
            self.redirect("/post/"+str(p.key().id()))
        else:
            self.redirect("/")

class CommentCreationHandler(webapp2.RequestHandler):
    def post(self):
        if users.get_current_user():
            try:
                com = BlogComment()
                com.authoremail = users.get_current_user().email()
                com.content = self.request.get("content")
                assert len(com.content) <= 500 and 0 < len(com.content)
                com.parentpost = self.request.get("parent")
                com.nick = self.request.get("nick")
                if len(com.nick) == 0:
                    com.nick = "Anonymous"
                com.god = checkadmin()
                com.authormd5 = md5(com.authoremail).hexdigest()

                newestpost = BlogComment.all().filter("authoremail =", com.authoremail).order("-dateposted").get()
                today = datetime.datetime.today()
                if newestpost and users.get_current_user().email() not in ADMINS: # admins don't have 60-second rule
                    assert (today - newestpost.dateposted).total_seconds() > 60
                
                com.put()
                self.redirect("/post/"+self.request.get("parent")+"#comments")
            except AssertionError:
                self.redirect("/post/i"+self.request.get("parent")+"?commenterror=1#comments")
        else:
            self.redirect("/post/"+self.request.get("parent")+"#comments")

class BlogPostDeletionHandler(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user().email() in ADMINS:
            com = BlogPost.get_by_id(int(self.request.get("id")))
            com.delete()
            comments = BlogComment.all().filter("parentpost = ", self.request.get("id")).order("-dateposted").run(limit=1000)
            for comment in comments:
                comment.delete()
        self.redirect("/")

class BlogCommentDeletionHandler(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user().email() in ADMINS:
            com = BlogComment.get_by_id(int(self.request.get("id")))
            com.delete()
            self.redirect("/post/"+com.parentpost)
        else:
            self.redirect("/")

class RSSHandler(webapp2.RequestHandler):
    def get(self):
        items = []
        posts = BlogPost.all()
        posts.order("-dateposted")
        postsresponse = posts.run(limit=1000)

        for post in postsresponse:
            items.append(
                rss.RSSItem(
                    title = post.title,
                    link = "http://comfortablynumbered.appspot.com/post/"+str(post.key().id()),
                    description = post.content,
                    guid = rss.Guid("http://comfortablynumbered.appspot.com/post/"+str(post.key().id())),
                    pubDate = post.dateposted
                )
            )

        self.response.write(rss.RSS2(
            title = "Comfortably Numbered: the Feed.",
            link = "http://comfortablynumbered.appspot.com",
            description = "The latest posts from Comfortably Numbered.",

            lastBuildDate = datetime.datetime.now(),
            items = items
        ).to_xml())

def Throw404(self):
    template_values = {
        "currentuser":users.get_current_user(),
        "loginurl":users.create_login_url("/"),
        "logouturl":users.create_logout_url("/"),
    }
    template = JINJA_ENVIRONMENT.get_template("404.html")
    self.error(404)
    self.response.write(template.render(template_values))

class NotFound(webapp2.RequestHandler):
    def get(self):
        Throw404(self);

class Robots(webapp2.RequestHandler):
    def get(self):
        self.redirect("/static/robots.txt");


def Email_Digest():
    now = date.today()
    posts = BlogPost.all()
    posts.order("-dateposted")
    postsresponse = posts.run(limit=10)

    body = """Greetings from Comfortably Numbered! Here are this week's posts:"""

    for post in postsresponse:
        if (now - post.dateposted).days < 7:
            body += """\n- {0}: {1}""".format(post.title, post.description)
    body += """Have a great weekend. \n\nCheers,\nHardmath123"""


app = webapp2.WSGIApplication([
    ("/", HomeHandler),
    ("/post/(\d*)\/?", BlogPostHandler),
    ("/new", BlogPostFormHandler),
    ("/create", BlogPostCreationHandler),
    ("/deletepost", BlogPostDeletionHandler),
    ("/deletecomment", BlogCommentDeletionHandler),
    ("/comment", CommentCreationHandler),
    ("/feed", RSSHandler),
    ("/robots.txt", Robots),
    ("/.*", NotFound),
], debug=True)
