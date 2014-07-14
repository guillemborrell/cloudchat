import datetime
import os
import random
import json
import webapp2
from google.appengine.api import channel, users
from google.appengine.ext import ndb
from models import Event, Message, ChatManager

class TokenResource(webapp2.RequestHandler):
    def get(self):
        ## Check if chat exists.
        chat_key = self.request.get('key')
        chat = ndb.Key(urlsafe=chat_key).get()
        client_id = ''.join([chat.key.urlsafe(),os.urandom(4).encode('hex')])
        token = channel.create_channel(client_id)
        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({'token':token,
                                            'id':client_id}))


class OpenResource(webapp2.RequestHandler):
    def post(self):
        body = json.loads(self.request.body)
        event = Event(kind = 'connection',
                      data = {'id':body['id'][-8:]})
        event.put()


class MessageResource(webapp2.RequestHandler):
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


class ConnectionResource(webapp2.RequestHandler):
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

class DisconnectionResource(webapp2.RequestHandler):
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


class ChatResource(webapp2.RequestHandler):
    def print_time(self):
        return datetime.datetime.now().strftime("%b %d %Y %H:%M:%S") 

    def get(self):
        if self.request.get('user'):
            user = users.get_current_user()
            if user:
                chats = ChatManager.query_user(user,10)
            else:
                pass

        else:
            chats = ChatManager.query_public(10)

        chat_list = list()
        for c in chats:
            chat_list.append(
                {"name": c.name,
                 "date": c.date.strftime("%b %d %Y %H:%M:%S"),
                 "owner": c.owner.nickname(),
                 "key": c.key.urlsafe(),
                 "persistent": c.options['persistent'],
                 "num_clients": c.num_clients(),
                 "private": c.private}
            )

        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({'chats': chat_list}))


    def post(self):
        user = users.get_current_user()
        body = json.loads(self.request.body)
        chat = ChatManager()
        chat.name = body['name']
        chat.active = True
        chat.private = body['private']
        chat.owner = user
        chat.options = {"save": body['save'],
                        "conversations": body['conversations'],
                        "persistent": body['persistent']}
        chat.put()

