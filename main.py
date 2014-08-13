import os
import webapp2
from google.appengine.api import users
from rest import TokenResource, OpenResource, MessageResource, ChatResource
from rest import ConnectionResource, DisconnectionResource, DownloadResource
from rest import InviteResource, BuildArchiveResource

    
class NewChatPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            with open(os.path.join(
                    os.path.dirname(__file__),
                    'templates',
                    'create.html')) as f:
                l = f.readlines()

            self.response.out.headers['Content-Type'] = 'text/html'
            self.response.out.write(''.join(l)%(users.create_logout_url('/'))
                                )

        else:
            with open(os.path.join(
                    os.path.dirname(__file__),
                    'templates',
                    'signin.html')) as f:
                l = f.readlines()

            self.response.out.headers['Content-Type'] = 'text/html'
            self.response.out.write(
                ''.join(l).format(users.create_login_url('/new'))
            )
            

class ChatPage(webapp2.RequestHandler):
    """The main UI page, renders the 'index.html' template."""
    def get(self):
        with open(os.path.join(
                os.path.dirname(__file__),
                'templates',
                'chat.html')) as f:
            l = f.readlines()

        self.response.out.headers['Content-Type'] = 'text/html'
        self.response.out.write(''.join(l))


class EmbedPage(webapp2.RequestHandler):
    def get(self):
        with open(os.path.join(
                os.path.dirname(__file__),
                'templates',
                'embed.html')) as f:
            l = f.readlines()

        self.response.out.headers['Content-Type'] = 'text/html'
        self.response.out.write(''.join(l))


class FaqPage(webapp2.RequestHandler):
    def get(self):
        with open(os.path.join(
                os.path.dirname(__file__),
                'templates',
                'faq.html')) as f:
            l = f.readlines()
            
        self.response.out.headers['Content-Type'] = 'text/html'
        self.response.out.write(''.join(l))


class MainPage(webapp2.RequestHandler):
    def get(self):
        with open(os.path.join(
                os.path.dirname(__file__),
                'templates',
                'index.html')) as f:
            l = f.readlines()
            
        self.response.out.headers['Content-Type'] = 'text/html'
        self.response.out.write(''.join(l))


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/chat', ChatPage),
    ('/new', NewChatPage),
    ('/embed', EmbedPage),
    ('/faq', FaqPage),
    ('/_ah/channel/connected/',ConnectionResource),
    ('/_ah/channel/disconnected/',DisconnectionResource),
    ('/API/token', TokenResource),
    ('/API/opened', OpenResource),
    ('/API/message', MessageResource),
    ('/API/download', DownloadResource),
    ('/API/invite', InviteResource),
    ('/API/buildarchive', BuildArchiveResource),
    ('/API/chat', ChatResource)], debug=True)


