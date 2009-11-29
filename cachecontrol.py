from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import logging
import datetime
import pickle
import re
import wsgiref.handlers

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch_errors
from google.appengine.runtime import apiproxy_errors
from google.appengine.api import memcache
from google.appengine.api import users

#Modivy below

TARGET_URL_SHORTER = "edu.lostriver.net"
TARGET_URL = "http://" + TARGET_URL_SHORTER
PROXY_SER_URL = "www.lostriver.net"
SHORTLINK_URL = "http://s.lostriver.net/"

#Modify above

FIXED_RESPONSE_HEADERS = frozenset([
        'last-modified',
        'content-type',
        'x-pingback'
])
FIXED_REQUEST_HEADERS = frozenset([
        'host',
        'if-none-match',
        'if-modified-since',
])

#Below are HEADERS already sent by Google
IGNORE_RESPONSE_HEADERS = frozenset([
        'cache-control',
        'content-type',
        'set-cookie',
])

class Short_links(db.Model):
    url_short = db.StringProperty(required=True)
    url_redirect_to = db.StringProperty(required=True)
    count = db.IntegerProperty(required=True)
    create_time = db.DateTimeProperty(required=True)

modified_request_headers = {}

class MainPage(webapp.RequestHandler):

  def myError(self, status, description):
        # header
        self.response.set_status(500, None)
        # body
        content = '<h1>Oops!</h1><p>Error Code: %d<p>Message: <br><br>%s' % (status, description)
        self.response.out.write(content)

  def fetch_content(self, fetch_method, item, modified_request_headers, modified_request_body):
      url =  TARGET_URL + item #self.request.path_qs
      for _ in range(3):
            try:
                result = urlfetch.fetch(url=url,
                                    payload=modified_request_body,
                                    method=fetch_method,
                                    headers = modified_request_headers,
                                    allow_truncated = False,
                                    follow_redirects = False)
                break
            except urlfetch_errors.ResponseTooLargeError:
                self.myError(500, 'Fetch server error, Sorry, Google\'s limit, file size up to 1MB.')
                return
            except Exception:
                continue
      else:
            self.myError(500, '''INTERNAL ERROR <br>There are something wrong at present. But you may just <A href="#"  onclick="window.location.reload()">click here to refresh</a> the page and it would be OK!<br>
                    <br>读取服务器失败<br>出问题了。。。可能由于网络繁忙所致，<A href="#"  onclick="window.location.reload()">点此刷新</a>一下就好！<br>
                    <br><img src="http://code.google.com/appengine/images/appengine-silver-120x30.gif" alt="由 Google App Engine 提供支持" />''')
            return
      modified_response_headers = result.headers
      modified_response_headers["code"] = result.status_code
      modified_response_headers["main_content"] = result.content      
      return modified_response_headers

  def post(self, base_url):
    user = users.get_current_user()
    if users.is_current_user_admin():
      if "cached_url" in self.request.POST:
        url =  TARGET_URL + self.request.POST["cached_url"]
        
      modified_request_headers = {}
      if self.request.POST["op"] == "View":
        self.response.out.write("<!-- content")
        self.response.out.write(memcache.get(self.request.POST["cached_url"]))
        self.response.out.write(" -->")
        
      elif self.request.POST["op"] == "Del":
              for name in FIXED_RESPONSE_HEADERS:
                      if not memcache.delete(self.request.POST["cached_url"]):
                          logging.error("Memcache delete failed.")
                          self.response.out.write("Memcache delete failed.")
              if not memcache.delete(self.request.POST["cached_url"] + "content"):
                  logging.error("Memcache delete failed.")
                  self.response.out.write("Memcache delete failed.")
              else:
                  self.response.out.write("Memcache delete Success!")
                  
      elif self.request.POST["op"] == "Clear":
          if not memcache.flush_all():
              logging.error("Memcache clear failed.")
              self.response.out.write("Memcache clear failed.")
          else:
              self.response.out.write("Memcache clear Success!")
              
      elif self.request.POST["op"] == "ViewAccessLog":
        self.response.headers.add_header("Contnet-Type", "text/plain")
        total_count = memcache.get("AccessLogNo")
        count_no = []
        for count in range(1, total_count + 1):
          count_no.append(str(count))
        access_all = memcache.get_multi(count_no, key_prefix='AccessLogNo')
#        self.response.out.write(access_all)
        for count in range(1, total_count + 1):
          try:
            access_entry = access_all[str(count)]
#            self.response.out.write(access_entry)
            for name, address in access_entry.items():
                self.response.out.write(' ')
                self.response.out.write(address)
          except:
            self.response.out.write("Accesslog Read Error")
          self.response.out.write("\r\n")
          
      elif self.request.POST["op"] == "DeleteAccessLog":
          if memcache.delete("AccessLogNo") == 2:
            self.response.out.write("AccessLog delete successful!")
          else:
            self.response.out.write("AccessLog delete Error")
            
      elif self.request.POST["op"] == "ViewPendingPost":
        self.response.out.write('''<form action="cachecontrol.py"  method="post">''')
        for count in range(1, memcache.get("pending_post_no") + 1):
            self.response.out.write('''<input type="Submit" name="op" value="''')
            self.response.out.write(count)
            self.response.out.write('''" style="width:40px;"/><br>''')
            access_entry = memcache.get("pending_post_no" + repr(count) + "info")
            if access_entry is not None:
              for name, address in access_entry.items():
                self.response.out.write(' ')
                self.response.out.write(address)
            self.response.out.write("<br>\r\n")
        self.response.out.write('''</form>''')
        
      elif self.request.POST["op"] == "DeletePendingPost":
          if memcache.delete("pending_post_no") == 2:
            self.response.out.write("PendingPost delete successful!")
          else:
            self.response.out.write("PendingPost delete Error")
            
      elif self.request.POST["op"] == "ViewShortLinks":
          q = db.GqlQuery("select * from Short_links order by create_time desc")
          results = q.fetch(1000)
          for r in results:
            self.response.out.write(r.url_short + " " + r.url_redirect_to + " ")
            self.response.out.write(r.count)
            self.response.out.write(" ")
            self.response.out.write(r.create_time)
            self.response.out.write("<br>")

      elif self.request.POST["op"] == "DeleteShortLinks":
          short_item = db.get(db.Key.from_path('Short_links', 'N:/%s' % self.request.POST["url_short"]))
          if short_item is not None:
            short_item.delete()
            self.response.out.write("DeleteShortLink Success!")
          else:
            self.response.out.write("ShortLink Delete Error")


      elif self.request.POST["op"] == "CreateShortLinks":
          short_item = Short_links(url_short = '/' + self.request.POST["url_short"], \
                          url_redirect_to = self.request.POST["url_redirect_to"], \
                          count = 0, \
                          create_time = datetime.datetime.now(), \
                          key_name='N:/%s' % self.request.POST["url_short"])
          short_item.put()
          self.response.out.write("Set shortlink success")

      elif self.request.POST["op"] == "ViewAShortlink":
        self.response.headers.add_header("Contnet-Type", "text/plain")
        total_count = memcache.get("AccessLogNo")
        count_no = []
        for count in range(1, total_count + 1):
          count_no.append(str(count))
        access_all = memcache.get_multi(count_no, key_prefix='AccessLogNo')
#        self.response.out.write(access_all)
        for count in range(1, total_count + 1):
          try:
            access_entry = access_all[str(count)]
#            self.response.out.write(access_entry)
            if access_entry["req_url"] == SHORTLINK_URL + self.request.POST["url_short"]:
                for name, address in access_entry.items():
                    self.response.out.write(' ')
                    self.response.out.write(address)
          except:
            self.response.out.write("Accesslog Read Error")
          self.response.out.write("\r\n")

      elif int(self.request.POST["op"]) in range(100):
          count = self.request.POST["op"]
          modified_request_content = memcache.get("pending_post_no" + count + "info")
          modified_request_headers = memcache.get("pending_post_no" + count + "headers")
          self.response.out.write(modified_request_content['req_url'] + "<br>")
          if modified_request_headers is not None:
            if modified_request_content is not None:
              post_result = self.fetch_content(urlfetch.POST, modified_request_content['req_url'], \
                                    modified_request_headers, modified_request_content['content'])
              if post_result:
                  memcache.delete("pending_post_no" + count + "info")
                  self.response.out.write("POST Successful!")
                  self.response.out.write(post_result)
      self.response.out.write("\r\n")
      self.response.out.write(memcache.get_stats())
      
    else:
      self.redirect("/cachecontrol.py")
    
  def get(self, base_url):
      user = users.get_current_user()
      if users.is_current_user_admin():
        self.response.out.write(
              '''<html><body>
                 <form action="cachecontrol.py"  method="post">
                 <input type="text" name="cached_url" value="" style="width:500px;"/><br>
                 <input type="submit" name="op" value="View" />
                 <input type="submit" name="op" value="Del" />
                 <input type="submit" name="op" value="Clear" />
                 <br>
                 <input type="submit" name="op" value="ViewAccessLog" />
                 <input type="submit" name="op" value="DeleteAccessLog" />
                 <br>
                 <input type="submit" name="op" value="ViewPendingPost" />
                 <input type="submit" name="op" value="DeletePendingPost" />
                 <br>
                 <input type="text" name="url_short" value="" style="width:100px;"/>
                 <input type="text" name="url_redirect_to" value="" style="width:500px;"/><br>
                 <input type="submit" name="op" value="CreateShortLinks" />
                 <input type="submit" name="op" value="ViewShortLinks" />
                 <input type="submit" name="op" value="DeleteShortLinks" />
                 <input type="submit" name="op" value="ViewAShortlink" />
                 </form>
              ''')
        self.response.out.write("Welcome, %s! (<a href=\"%s\">sign out</a>)" %
                  (user.nickname(), users.create_logout_url("/")))
        self.response.out.write("<br><a href=\"%s\">Sign in or register</a>.</body></html>" %
                    users.create_login_url("/cachecontrol.py"))
      else:
        self.response.out.write("<a href=\"%s\">Sign in or register</a>." %
                    users.create_login_url("/cachecontrol.py"))

        

application = webapp.WSGIApplication([
                (r"([\s\S]*)", MainPage)
                ], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
