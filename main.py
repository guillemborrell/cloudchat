import os
import webapp2
from google.appengine.api import users
from rest import TokenResource, OpenResource, MessageResource, ChatResource
from rest import ConnectionResource, DisconnectionResource

    
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
            self.response.out.write(''.join(l))

        else:
            self.response.out.headers['Content-Type'] = 'text/html'
            self.response.out.write(
                '<html><body><a href={}>Sign in</a></body></html>'.format(
                    users.create_login_url('/new')
                )
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
    ('/_ah/channel/connected/',ConnectionResource),
    ('/_ah/channel/disconnected/',DisconnectionResource),
    ('/API/token', TokenResource),
    ('/API/opened', OpenResource),
    ('/API/message', MessageResource),
    ('/API/chat', ChatResource)], debug=True)


