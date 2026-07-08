[app]
title = 企信查
package.name = johnny
package.domain = com.qxx
source.dir = .
source.include_exts = py,png,jpg,ttf,json,db
source.include_patterns = fonts/*,*.json
version = 1.0.0
requirements = python3, kivy==2.3.1, requests
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 36
android.minapi = 31
android.ndk = 25b
android.sdk = 36
android.accept_sdk_license = True
log_level = 2
warn_on_root = 0

[buildozer]
verbose = 0