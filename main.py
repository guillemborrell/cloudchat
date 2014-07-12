#!/usr/bin/python2.4

# pylint: disable-msg=C6310

import datetime
import logging
import os
import random
import json
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app


class ChatManager(ndb.Model):
    label = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    clients = ndb.StringProperty(repeated=True)

    def add_client(self, client):
        client_list = self.clients
        client_list.append(client)
        self.put()

    def remove_client(self, client):
        client_list = self.clients
        while client in client_list: client_list.remove(client)
        self.put()


class Message(ndb.Model):
    date = ndb.DateTimeProperty(auto_now_add=True)
    author = ndb.StringProperty()
    client = ndb.StringProperty()
    text = ndb.StringProperty()

    @classmethod
    def query_last_from_chat(cls,num,chat_key):
        query = cls.query(ancestor=ndb.Key(urlsafe=chat_key))
        return query.order(-cls.date).fetch(10)


class Event(ndb.Model):
    date = ndb.DateTimeProperty(auto_now_add=True)
    kind = ndb.StringProperty()
    data = ndb.JsonProperty()
    

class ServeToken(webapp.RequestHandler):
    def get(self,chat):
        ## Check if chat exists.
        chat = ndb.Key(urlsafe=chat).get()
        client_id = ''.join([chat.key,os.urandom(4).encode('hex')])
        token = channel.create_channel(client_id)
        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({'token':token,
                                            'id':client_id}))


class OpenedPage(webapp.RequestHandler):
    def post(self):
        body = json.loads(self.request.body)
        event = Event(kind = 'connection',
                      data = {'id':body['id'][-8:]})
        event.put()


class MessagePage(webapp.RequestHandler):
    def print_time(self):
        return datetime.datetime.now().strftime("%b %d %Y %H:%M:%S")
        
        
    def post(self):
        body = json.loads(self.request.body)
        chat_key = ndb.Key(urlsafe=body['id'][:-8])
        message = Message(parent = chat_key,
                          author = body['author'],
                          text   = body['text'],
                          client = body['id'][-8:])
                          
        message.put()

        for client_id in chat.clients:
            channel.send_message(
                client_id,
                json.dumps(
                    {"clients":len(chat.clients),
                     "message": [{"author": body['author'],
                                  "when": self.print_time(),
                                  "text": body['text']}]
                 }
                )
            )


class ConnectionPage(webapp.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        if len(chat) == 0:
            logging.warning("Creating new default chat")
            clients = [client_id[-8:]]
            newchat = ChatManager(label="default",clients=clients)
            newchat.put()
            
        else:
            chat = chat[0]
            for client in chat.clients:
                channel.send_message(
                    client,
                    json.dumps(
                        {"clients":len(chat.clients)+1,
                         "message": []
                     }
                    )
                )
                
            channel.send_message(
                client_id,
                json.dumps(
                    {"clients": len(chat.clients),
                     "message": Message.query_last_from_chat(10,chat.key.urlsafe())
                 }
                )
            )
            chat.add_client(client_id[-8:])

class DisconnectionPage(webapp.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        for client in chat.clients:
            channel.send_message(
                client,
                json.dumps(
                    {"clients":len(chat.clients)-1,
                     "message": []
                 }
                )
            )
        chat.remove_client(client[-8:])            


class NewChatPage(webapp.RequestHandler):
    def post(self):
        newchatinfo = json.loads(self.request.body)
        print newchatinfo


class ChatPage(webapp.RequestHandler):
    """The main UI page, renders the 'index.html' template."""
    def get(self):
        chat_key = self.request.get('key')
        chat = ndb.Key(urlsafe = chat_key).get()
        token = channel.create_channel(chat_key)
        with open(os.path.join(os.path.dirname(__file__), 'index.html')) as f:
            l = f.readlines()

        self.response.out.write(''.join(l))


class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.headers['Content-Type'] = 'text/html'
        self.response.out.write("<html><body><p>Chat in the cloud!</p></body></html>")


application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/chat', ChatPage),
    ('/new', NewChatPage),
    ('/_ah/channel/connected/',ConnectionPage),
    ('/_ah/channel/disconnected/',DisconnectionPage),
    ('/token', ServeToken),
    ('/opened', OpenedPage),
    ('/message', MessagePage)], debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
