
HOWTO configure lighttpd 

* INSTALLING

** MAC OS
On the mac, use brew:
https://redmine.lighttpd.net/projects/lighttpd/wiki/HowToInstallOnOSX

brew install lighttpd

Docroot is: /usr/local/var/www
default port: 8080
conf file is /usr/local/etc/lighttpd/lighttpd.conf to 8080 so that
lighttpd can run without sudo.

You can start/stop lighttpd with brew service s:
brew services list
brew services start lighttpd
brew services stop lighttpd
brew services restart lighttpd

* BASIC CONFIGURING
Put readme.html into docroot:

<!DOCTYPE html>
<html lang="en">
      <body>
hello world
      </body>      
</html>

Make sure you can see readme.html via web browser or curl, port 8080

* CONFIGURE MOD_AUTH
create a new user:
 htdigest -c /usr/local/etc/lighttpd/.passwd 'authorized users only' ryu


modify /usr/local/var/lighttpd/lighttpd.conf:

server.modules += ("mod_auth", "mod_authn_file")
auth.backend = "htdigest"
auth.backend.htdigest.userfile = "/usr/local/etc/lighttpd/.passwd"

auth.require = ( "/" =>
  (
    "method" => "digest",
    "realm" => "authorized users only",
    "require" => "valid-user"
  )
)

NOTE: it's important that the value of "realm" matches the "realm" specified during htdigest setup, e.g. "authorized users only".

then restart lighttpd and test it. you should get authentication challenge.







