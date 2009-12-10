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

######################## Setting area below ########################

TARGET_URL_SHORTER = "drip.lostriver.net"   #the domain which GAE fetch from
PROXY_SER_URL = "www.lostriver.net"         #domain of your GAE app
APP_ID = "lostriver-net"                    #the app-id of GAE
SHORTLINK_URL = "s.lostriver.net"           #the short-links domain

#Set whether using MEMCACHE or not
IF_USE_MEMCACHE = True

#Set forcing https when visit through *.appspot.com
IF_FORCE_HTTPS = False

#Set which HTTP response status to be cached. 
TO_BE_CACHED_STATUS = frozenset([
        200,
        301,
        302,
        404
])
######################## Setting area above ########################

TARGET_URL = "http://" + TARGET_URL_SHORTER
APP_ID_HOST = APP_ID + ".appspot.com"

#Below are HEADERS already sent by Google
IGNORE_RESPONSE_HEADERS = frozenset([
        'cache-control',
        'content-type',
        'set-cookie',
])

class Bot_Rule(webapp.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "text/plain"
        self.response.out.write("User-agent: *\r\nDisallow: /")

class Short_links(db.Model):
    url_short = db.StringProperty(required=True)
    url_redirect_to = db.StringProperty(required=True)
    count = db.IntegerProperty(required=True)
    create_time = db.DateTimeProperty(required=True)

class MainPage(webapp.RequestHandler):

  def loggingreq(self, response_status, response_content_length, if_use_cache):
      header_referer = ''
      header_user_agent = ''
      for name, address in self.request.headers.items():
          if name.lower() == "referer":
              header_referer = address
          elif name.lower() == "user-agent":
              header_user_agent = address
      request_get = {'ip_addr'      : self.request.remote_addr,
                     'time'         : datetime.datetime.now(),
                     'req_method'   : self.request.environ["REQUEST_METHOD"],
                     'req_url'      : self.request.url,
                     'req_PROTOCOL' : self.request.environ["SERVER_PROTOCOL"],
                     'resp_status'  : response_status,
                     'resp_length'  : response_content_length,
                     'referer'      : header_referer,
                     'user_agent'   : header_user_agent,
                     'if_cache'     : if_use_cache
                     }
      count = memcache.get('AccessLogNo')
      if count is not None:
          memcache.incr('AccessLogNo')
          count = count + 1
      else:
          memcache.set('AccessLogNo', 1)
          count = 1
      memcache.set("AccessLogNo" + repr(count), request_get)
      
  def myError(self, status, description):
        # header
        self.response.set_status(500, None)
        # body
        content = '<h1>Oops!</h1><p>Error Code: %d<p>Message: <br><br>%s' % (status, description)
        self.response.out.write(content)
#        self.loggingreq(500, 0, False)

  def get_cached_response(self, item):
    modified_response_content = {}
    modified_response_content = memcache.get(item)
    if modified_response_content is not None:
        if_content = True
        for name, address in self.request.headers.items():
          for name2, address2 in modified_response_content.items():
              if name.lower() == "if-none-match" \
                 and name2.lower() == "etag" \
                 and address == address2:
                        if_content = False
                        modified_response_content["code"] = 304
        self.content_response(modified_response_content, if_content)
        '''self.loggingreq(modified_response_content["code"], \
                len(modified_response_content["main_content"]), \
                True)'''
        return True
    else:
        return False

  def fetch_content(self, fetch_method, item, modified_request_headers):
      url =  TARGET_URL + item #self.request.path_qs
      for _ in range(3):
            try:
                result = urlfetch.fetch(url=url,
                                    payload=self.request.body,
                                    method=fetch_method,
                                    headers = modified_request_headers,
                                    allow_truncated = False,
                                    follow_redirects = False,
                                    deadline = 10)
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


  def content_response(self, response_content, if_content):
      self.response.set_status(response_content["code"], None)
      #Set-Cookie. Refer to Solrex.cn in solving the muti-cookie problem in GAppProxy
      for name, address in response_content.items():
          if name.lower() == "set-cookie":
              scs = re.sub(r',([^,;]+=)', r'\n\1', address).split('\n')
              for sc in scs:
                if self.request.host == APP_ID_HOST:
                    self.response.headers.add_header("Set-Cookie", re.sub(PROXY_SER_URL, \
                                                                          APP_ID_HOST, \
                                                                          sc.strip()))
                else:
                    self.response.headers.add_header("Set-Cookie", sc.strip())
      #Modify and add HEADERS
      for name, address in response_content.items():
          if name.lower()!="main_content" and name.lower()!="code":
            if self.request.host == APP_ID_HOST:
                if self.request.environ["SERVER_PORT"] == "443":
                    address = re.sub("http://" + PROXY_SER_URL, \
                                     "https://" + APP_ID_HOST, \
                                     address)
                address = re.sub(PROXY_SER_URL, \
                                 APP_ID_HOST, \
                                 address)
            else:
                address = address
            if name.lower() not in IGNORE_RESPONSE_HEADERS:
                self.response.headers.add_header(name, address)
            elif name.lower() != 'set-cookie':
                self.response.headers[name] = address
      #Main content is here
      if if_content:
          if self.request.host == APP_ID_HOST:
              if self.request.environ["SERVER_PORT"] == "443":
                  response_content["main_content"] = re.sub("http://" + PROXY_SER_URL, \
                                                            "https://" + APP_ID_HOST, \
                                                            response_content["main_content"])
              response_content["main_content"] = re.sub(PROXY_SER_URL, \
                                                        APP_ID_HOST, \
                                                        response_content["main_content"])
        #Strip DRIP Host ADs
          response_content["main_content"]=re.sub( \
              r"<CENTER>[\s\S]*?</CENTER>", '', response_content["main_content"])
          response_content["main_content"]=re.sub( \
              r"<CENTER>[\s\S]*?</CENTER>", '', response_content["main_content"])
          self.response.out.write(response_content["main_content"])

  def cache_content(self, item, to_be_cached):
      if to_be_cached["code"] in TO_BE_CACHED_STATUS:
          if not memcache.set(item, to_be_cached):
              logging.error("Memcache set failed.")

  def post(self, base_url):
    fetched_content = self.fetch_content(urlfetch.POST, self.request.path_qs, self.request.headers)
    if fetched_content is not None:
        self.content_response(fetched_content, 1)
        if fetched_content["code"] is 200:
            for name, address in self.request.headers.items():
                if name.lower() == "referer":
                    item = re.sub(r'(^http://)' + PROXY_SER_URL + '/' , '/', address)
                    #refresh the memcache of referer page
                    #often do not work very well due to the structure of site.
                    self.cache_content(item ,self.fetch_content(urlfetch.GET, item, {}))
#        self.loggingreq(fetched_content["code"], len(fetched_content["main_content"]), False)
    else:
        count = memcache.get("pending_post_no")
        if count is not None:
            memcache.incr('pending_post_no')
            count = count + 1
        else:
        #Store pending post(incomplete fetch due to network problems) in memcache
            memcache.set('pending_post_no', 1)
            count = 1
        pending_post = {'ip_addr'  : self.request.remote_addr,
                        'time'     : datetime.datetime.now(),
                        'req_url'  : self.request.path_qs,
                        'content'  : self.request.body
                        }
        memcache.set("pending_post_no" + repr(count) + "info", pending_post)
        pending_post_headers = {}
        for name, address in self.request.headers.items():
            pending_post_headers[name] = address
        memcache.set("pending_post_no" + repr(count) + "headers", \
                     pending_post_headers)

    
  def get(self, base_url):
    if self.request.host == "t.lostriver.net":
        self.redirect("http://twitter.com/LucienLu")
    elif ((self.request.host == "s.lostriver.net") or \
          (self.request.host == "s." + APP_ID + ".appspot.com")):
        short_item = db.get(db.Key.from_path('Short_links', 'N:%s' % self.request.path_qs))
        if not short_item:
            self.response.set_status(404, None)
            not_found_error_cont = \
'''<html><head>
<meta http-equiv="content-type" content="text/html; charset=utf-8">
<title>ShortLinks - 404 - lostriver.net</title>
<body>
<h1>Shared by Lostriver.net<br></h1>
<h3>404 Not Found<br></h3>
Sorry but what you are looking for does not exist.<br>
Visit home page <a href="http://www.lostriver.net/">http://www.lostriver.net/</a><br>
<hr>
<center>History</center>
<table width="800" border="1" align="center">
<tr><td>Share link</td><td>Total click</td><td>Create time(UTC)</td></tr>
'''
	    self.response.out.write(not_found_error_cont)
            q = db.GqlQuery("select * from Short_links order by create_time desc")
            results = q.fetch(1000)
            for r in results:
                self.response.out.write('''<tr><td><a rel="nofollow" target="_blank" href="''' \
                                        + r.url_short + '">' + r.url_redirect_to + \
                                        '</a></td>')
                self.response.out.write('<td>' + str(r.count) + '</td>')
                self.response.out.write('<td>' + str(r.create_time) + '</td></tr>')
            self.response.out.write('''</table><br><center>CopyRight2009 <font color=blue>lostriver.net</font><br>
					Powered by <a rel="nofollow" target="_blank" href="http://code.google.com/intl/zh-CN/appengine/">Google AppEngine</a></center></body></html>''')
        else:
            self.response.out.write('''<html><head><title>Redirecting...</title></head>
<body><h1>Redirecting...</h1><script type="text/javascript"><!--
window.parent.location = "%s"
//--></script></body></html>''' % short_item.url_redirect_to)
            short_item.count +=1
            short_item.put()
#            self.loggingreq(302, 0, False)
    elif self.request.host == APP_ID_HOST and self.request.environ["SERVER_PORT"] == "80" and IF_FORCE_HTTPS:
        self.redirect("https://" + APP_ID_HOST + "/")
    else:
        item = self.request.path_qs
#        memcache.flush_all()
        if (not users.is_current_user_admin()) and IF_USE_MEMCACHE:
            if not self.get_cached_response(item):
              fetched_content = self.fetch_content(urlfetch.GET, item, {})
              if fetched_content is not None:  
                self.content_response(fetched_content, True)
                self.cache_content(item, fetched_content)
                '''self.loggingreq(fetched_content["code"], \
                                len(fetched_content["main_content"]), \
                                False)'''
        else:
            fetched_content = self.fetch_content(urlfetch.GET ,item, self.request.headers)
            if fetched_content is not None:
                if fetched_content["code"] == 304:
                    self.content_response(fetched_content, False)
                else:
                    self.content_response(fetched_content, True)
                '''self.loggingreq(fetched_content["code"], \
                                len(fetched_content["main_content"]), \
                                False)'''

application = webapp.WSGIApplication([
                (r"([\s\S]*)", MainPage)
                ], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
