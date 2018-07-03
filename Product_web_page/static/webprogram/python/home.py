"""

    Page Templating with Python 🌐🐍
    GitHub :: PCabralSoftware - 2K18 - Twitter :: @pedrogcabral

"""
# https://scrimba.com/c/cbBpPsk
from browser import document
from browser import html
from browser.template import Template
import os

pageName = "Python 🐍"
articleContent = open('/static/webprogram/python/news_file.txt').read()
articleTitle = articleContent.split('\n', 1)[0]
articleText = articleContent.split('\n', 1)[1]

# Article Object
article = [html.H1('{title}', Id='art_title'), html.P('{content}', Id="art_content")]

# Navigation
nav = html.DIV([html.H1('{title}', Id='title'), html.H2('☰', Id='navbtn')], Class='nav')

# Content
cnt = html.DIV(html.DIV(article, Class="article"), Class='content')

# Footer
ftr = html.DIV([html.P(('Copyright {} 2018 - All rights reserved.'.format(pageName)))], Class='footer')

# Push the elements to the DOM
document <= [nav, cnt, ftr]

# Render the template tags
Template(document['title']).render(title=pageName)
Template(document['art_title']).render(title=articleTitle)
Template(document['art_content']).render(content=articleText+" "+os.getcwd())