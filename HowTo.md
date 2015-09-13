> Setup Instructions:

1.Download the files (4 files and a folder) from downloads page.

2.Modify edu.py and cachecontrol.py in the beginning.

3.Upload it to your Google Appengine, Do not forget to modify app-id.

(下载，修改edu.py文件开头的源代码设置区，上传GAE；修改DNS，将主域名绑定到GAE，辅助的被代理域名指向被代理站。)


---


NOTICE:The reverse proxy is written based on my wordpress blog, which has low viewers and tipically static. So websites with high trafic or with a lot of dynamic pages (i.e. forums) would significantly slow down the performance.（静态页比较有用，论坛之类很慢。）

Tipically you should set the source website 2 domains TARGET\_URL\_SHORTER and PROXY\_SER\_URL in your virtual host cpanel, and then point your dns server TARGET\_URL\_SHORTER to your virtual host, point PROXY\_SER\_URL to ghs.google.com(or 216.239.36.21, any google host IP).Here my source domain is edu.lostriver.net, my GAE domain is www.lostriver.net.（典型情况虚拟主机上要帮定2个域名，只有一个TARGET\_URL\_SHORTER（被代理网站）用DNS指过去，GAE绑主域名）. Set APP\_ID to access your website throught http(s)://APP\_ID.appspot.com. But all these settings are not necessary. You could modify it by your own.

About memcache: Google Appengine memcache have a relatively high performance - within 10 ms delay and very fast speed. Theoretically memcache would be kept forever. while during my trial , it could keeps about 1 day or several days. The expire time is set as long as possible as default. You can also modify the expire time by add a argument to the memcache.set() function. for example: edu.py:193: if not memcache.set(item, to\_be\_cached, 2600):  means keep the memcache item for 1 hour.（memcache如果不设置过期一般也只有1天或几天。）

Demo: Due to GFW, I deleted the dns item pointing to GAE, you could visit http://lostriver-net.appspot.com/ to see the performance.

About administration: Visit http://APP_ID.appspot.com/cachecontrol.py or http://PROXY_SER_URL/cachecontrol.py。then login. Administrators did not use memcache, instead, they fetch from the source every time.

> The first textarea you type /pageid to view or delete the memcache, returns None when cache does not exist. Do not forget the prefix'/'. 'Clear' means to clear ALL THE MEMCACHE including pending posts mentioned below.（要管理某个网页缓存，只需要输入/pageid）

> Accesslog gives a quick but not so accurate view to recent access, in nearly Apache accesslog. Uses memcache to store the date. It is not encoded into HTML so do not show very well in some browers. Try to view the webpage source in your brower.(NOW HAVE BEEN REMOVED FOR FASTER PERFORMANCE.)

> Click ViewPendingPost those POST did not accomplete due to network errors is listed. Click the number to retry the POST. Click DeletePendingPost means deleting ALL PENDINGPOSTS. Anyway, it is not very stable to store pending posts into memcache. If possible I would turn to datebase.（用memcache保存了未完成的POST，点击条目可以手动完成）

Shortlink:in the first input area you input sth like jiql then in paste the URI in the right textarea including "http://" prefix. Then visit http://SHORTLINK_URL/jiql would return the URI by a 302 relocation. here I have http://s.lostriver.net/   Visit shortlinks does not exist would show a page which show your shortlink history.（两个框分别输入段网址名和包含 http:// 前缀的目标地址，如果有人访问不存在的地址，404页是短网址的历史纪录。）

PROBLEMS AND BUGS:
There are many many bugs in cachecontrol.py, anyway it is not very important. The primary problem is the fetch server error, mainly caused by 3 reason: The delay between the source site and GAE is too long, and the bandwidth is too slow. In addition, Google limit the fetch content to 1MB. All these problems have solutions now but I didnot bring it into true. Large files could break into small pieces through the HTTP range header. Use rpc fetch service to fetch all the pieces and combine them into one item, cache it and response it. I would accomplish it later or never. If you are interested in the reverse proxy , you can join in and contribute it. （网速慢会出错，超过1M会出错，可以通过rpc分段请求完成，完善方向。）