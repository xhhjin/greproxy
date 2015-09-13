A reverse proxy run on Appengine, tiny and fast. Especially fits small personal blogs.

Features:

1.Using memcache to speed up the request. About than 90% of the request hits the memcache and the response delay can be as short as 10 millisecond.（用memcache加速）

2.Employed administration page for controlling the memcache and view accesslog in a convenience way.（管理员控制缓存）

3.Cache the POST data when connection between GAE and the source webhost goes wrong. And then rePOST the data manually later. This would protect user data, like comments to blog.（连接出错可缓存POST数据）

4.A small addition widget for abbreviating url is employed.（一个山寨的缩短网址功能）

5.可以用于在教育网内的站点向全球发布，也可用于反向代理国外网站。但仍常常受限于ghs的可靠性。

See Page Wiki Howto for details http://code.google.com/p/greproxy/wiki/HowTo