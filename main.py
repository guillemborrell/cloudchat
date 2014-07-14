import datetime
import logging
import os
import random
import json
import webapp2
import jinja2
from google.appengine.api import channel, users
from google.appengine.ext import ndb
from models import *


JINJA_ENVIRONMENT = jinja2.Environment(
    loader = jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__),
                     'templates')),
    extensions = ['jinja2.ext.autoescape'],
    autoescape = True)
    

class ServeToken(webapp2.RequestHandler):
    def get(self):
        ## Check if chat exists.
        chat_key = self.request.get('key')
        chat = ndb.Key(urlsafe=chat_key).get()
        client_id = ''.join([chat.key.urlsafe(),os.urandom(4).encode('hex')])
        token = channel.create_channel(client_id)
        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({'token':token,
                                            'id':client_id}))


class OpenedPage(webapp2.RequestHandler):
    def post(self):
        body = json.loads(self.request.body)
        event = Event(kind = 'connection',
                      data = {'id':body['id'][-8:]})
        event.put()


class MessagePage(webapp2.RequestHandler):
    def print_time(self):
        return datetime.datetime.now().strftime("%b %d %Y %H:%M:%S")        
        
    def post(self):
        body = json.loads(self.request.body)
        chat_key = body['id'][:-8]
        chat = ndb.Key(urlsafe=chat_key).get()
        message = Message(parent = chat.key,
                          author = body['author'],
                          text   = body['text'],
                          client = body['id'][-8:])
                          
        message.put()

        for client_id in chat.clients:
            channel.send_message(
                client_id,
                json.dumps(
                    {"clients":len(chat.clients),
                     "name": chat.name,
                     "message": [{"author": body['author'],
                                  "when": self.print_time(),
                                  "text": body['text']}]
                 }
                )
            )


class ConnectionPage(webapp2.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        for client in chat.clients:
            channel.send_message(
                client,
                json.dumps(
                    {"clients":len(chat.clients)+1,
                     "name": chat.name,
                     "message": []
                 }
                )
            )

        messages = Message.query_last_from_chat(10,chat.key.urlsafe())
        message_list = [{"author": m.author,
                         "when": m.date.strftime("%b %d %Y %H:%M:%S"),
                         "text": m.text} for m in messages]

        channel.send_message(
            client_id,
            json.dumps(
            {"clients": len(chat.clients),
             "name": chat.name,
             "message": message_list[::-1]
         }
            )
        )
        chat.add_client(client_id)

class DisconnectionPage(webapp2.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        for client in chat.clients:
            channel.send_message(
                client,
                json.dumps(
                    {"name": chat.name,
                     "clients":len(chat.clients)-1,
                     "message": []
                 }
                )
            )
        
        if len(chat.clients) == 1:
            # No connections
            if not chat.options['persistent']:
                # If chat is not persistent
                chat.active = False

        chat.remove_client(client_id)


class ChatPage(webapp2.RequestHandler):
    """The main UI page, renders the 'index.html' template."""
    def get(self):
        chat_key = self.request.get('key')
        chat = ndb.Key(urlsafe = chat_key).get()

        with open(os.path.join(
                os.path.dirname(__file__),
                'templates',
                'chat.html')) as f:
            l = f.readlines()

        self.response.out.headers['Content-Type'] = 'text/html'
        self.response.out.write(''.join(l))


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
                '<a href={}>Sign in</a>'.format(
                    users.create_login_url('/new')
                )
            )
            

    def post(self):
        user = users.get_current_user()
        body = json.loads(self.request.body)
        print body
        chat = ChatManager()
        chat.name = body['name']
        chat.active = True
        chat.owner = user
        chat.options = {"save": body['save'],
                        "conversations": body['conversations'],
                        "persistent": body['persistent']}
        chat.put()
        

class MainPage(webapp2.RequestHandler):
    def get(self):
        active_chats = ChatManager.query_last(10)

        template_values = {'active_chats' : active_chats}

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.out.write(template.render(template_values))



application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/chat', ChatPage),
    ('/new', NewChatPage),
    ('/_ah/channel/connected/',ConnectionPage),
    ('/_ah/channel/disconnected/',DisconnectionPage),
    ('/token', ServeToken),
    ('/opened', OpenedPage),
    ('/message', MessagePage)], debug=True)


