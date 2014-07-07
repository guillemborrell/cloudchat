#!/usr/bin/python2.4

# pylint: disable-msg=C6310

import datetime
import logging
import os
import random
import re
import json
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app


class ChatManager(ndb.Model):
    label = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    clients = ndb.StringProperty(repeated=True)
    
    def query_label(cls, label):
        return cls.query(ChatManager.label == label).fetch(1)


class Event(ndb.Model):
    date = ndb.DateTimeProperty(auto_now_add=True)
    kind = ndb.StringProperty()
    data = ndb.JsonProperty()


class ServeToken(webapp.RequestHandler):
    def get(self):
        connection_id = os.urandom(16).encode('hex')
        token = channel.create_channel(connection_id)
        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({'token':token,
                                            'id':connection_id}))


class OpenedPage(webapp.RequestHandler):
    def post(self):
        body = json.loads(self.request.body)
        event = Event(kind = 'connection',
                      data = {'id':body['id']})
        event.put()


class MessagePage(webapp.RequestHandler):
    def post(self):
        body = json.loads(self.request.body)
        event = Event(kind='message',data={'author':body['author'],
                                           'text':body['text'],
                                           'id':body['id']}
                  )
        event.put()
        chat = ChatManager().query_label("default")[0]
        for client_id in chat.clients:
            channel.send_message(client_id,
                                 json.dumps(
                                     {"author": body['author'],
                                      "when": datetime.datetime.now().strftime(
                                          "%b %d %Y %H:%M:%S"),
                                      "text": body['text']}))
      

class MainPage(webapp.RequestHandler):
    """The main UI page, renders the 'index.html' template."""
    def get(self):
        token = channel.create_channel("default")
        with open(os.path.join(os.path.dirname(__file__), 'index.html')) as f:
            l = f.readlines()

        self.response.out.write(''.join(l))


class ConnectionPage(webapp.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        chat = ChatManager().query_label('default')

        if len(chat) == 0:
            print "Creating new default chat"
            clients = [client_id]
            newchat = ChatManager(label="default",clients=clients)
            newchat.put()
       
        else:
            chat = chat[0]
            clients = chat.clients
            if client_id not in clients:
                clients.append(client_id)
            chat.clients = clients
            chat.put()


class DisconnectionPage(webapp.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        chat = ChatManager().query_label('default')[0]
        clients = chat.clients

        try:
            clients.remove(client_id)
            chat.clients = clients
            chat.put()
        except ValueError:
            pass


application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/_ah/channel/connected/',ConnectionPage),
    ('/_ah/channel/disconnected/',DisconnectionPage),
    ('/token', ServeToken),
    ('/opened', OpenedPage),
    ('/message', MessagePage)], debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
