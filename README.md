Comfortably-Numbered
====================

My blog: http://comfortablynumbered.appspot.com

Comfortably Numbered runs on GAE, with the following awesome libraries:
- PrismJS for Syntax Highlighting
- Markdown for comments
- MathJAX for LaTeX
- PyRSS2Gen for the RSS feed

To run it yourself, `git clone` the repo and create the file `settings.py`, with the content `ADMINS = ["an_admin_email@addess"]`. Then run with the GAE SDK.

To test a post, view `/post/?test=NAME`, where `NAME-test.html` resides in the root directory.