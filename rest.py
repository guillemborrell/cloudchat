import datetime
import os
import json
import webapp2
import cgi
from google.appengine.api import channel, users
from google.appengine.ext import ndb
from models import Event, Message, ChatManager

def prettify(message):
    image_formats = ['.png','.gif','.jpg','.jpeg']
    video_formats = ['.mp4','.ogg','.webm']
    youtube_urls = ['youtube.com','youtu.be']
    newmessage = list()
    for w in message.split():
        if any([fmt in w for fmt in video_formats]):
            newmessage.append(
                '<video class="img-responsive" controls><source src="{}" type="video/webm"></video>'.format(w)
            )
        elif any([fmt in w for fmt in youtube_urls]):
            newmessage.append(
                '<iframe width="480" height="320" src="//www.youtube.com/embed/{}" frameborder="0" allowfullscreen></iframe>'.format(w[-11:])
            )
        elif any([fmt in w for fmt in image_formats]):
            newmessage.append(
                '<img src="{}" class="img-responsive">'.format(w)
            )
        elif 'cloudchatroom.appspot.com' in w:
            newmessage.append(
                '<a href="{}" target="_blank">{}...</a>'.format(w,w[:20])
            )
        else:
            newmessage.append(w)

    return ' '.join(newmessage)


class TokenResource(webapp2.RequestHandler):
    def get(self):
        ## Check if chat exists.
        chat_key = self.request.get('key')
        chat = ndb.Key(urlsafe=chat_key).get()
        client_id = ''.join([chat.key.urlsafe(),os.urandom(4).encode('hex')])
        token = channel.create_channel(client_id)
        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(
            json.dumps(
                {'token':token,
                 'id':client_id,
                 'conversations':chat.options['conversations']
             }
            )
        )


class DownloadResource(webapp2.RequestHandler):
    def get(self):
        chat_key = self.request.get('key')
        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(
            json.dumps(
                Message.query_all_from_chat(chat_key)
            )
        )


class OpenResource(webapp2.RequestHandler):
    def post(self):
        body = json.loads(self.request.body)
        event = Event(kind = 'connection',
                      data = {'id':body['id'][-8:]})
        event.put()


class InviteResource(webapp2.RequestHandler):
    def print_time(self):
        return datetime.datetime.now().strftime("%b %d %Y %H:%M:%S")        

    def post(self):
        body = json.loads(self.request.body)
        client_id = body['from']
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        if body['to'] in chat.clients:
            newchat = ChatManager()
            newchat.name = 'Private'
            newchat.active = True
            newchat.private = True
            newchat.owner = users.User("anonymous@none.com")
            newchat.options = {"save": False,
                            "conversations": False,
                            "persistent": False}
            newchat_key = newchat.put()

            channel.send_message(
                body['from'],
                json.dumps(
                    {"clients":len(chat.clients),
                     "name": chat.name,
                     "message": [
                         {"author": 'ADMIN',
                          "id": '0',
                          "when": self.print_time(),
                          "text": 'You have sent a private <a target="_blank" href="/chat?key={}">room</a>'.format(newchat_key.urlsafe())
                      }
                     ]
                 }
                )
            )

            channel.send_message(
                body['to'],
                json.dumps(
                    {"clients":len(chat.clients),
                     "name": chat.name,
                     "message": [
                         {"author": 'ADMIN',
                          "id": '0',
                          "when": self.print_time(),
                          "text": 'You have been invited to a private <a target="_blank" href="/chat?key={}">room</a> by {}'.format(newchat_key.urlsafe(),body['author'])
                      }
                     ]
                 }
                )
            )


        else:
            channel.send_message(
                body['from'],
                json.dumps(
                    {"clients":len(chat.clients),
                     "name": chat.name,
                     "message": [{"author": 'ADMIN',
                                  "id": '0',
                                  "when": self.print_time(),
                                  "text": 'This user is no longer connected'
                              }]
                 }
                )
            )
            


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

        if users.get_current_user() == chat.owner:
            author = '<u>'+cgi.escape(body['author'])+'</u>'
        else:
            author = cgi.escape(body['author'])


        for client_id in chat.clients:
            channel.send_message(
                client_id,
                json.dumps(
                    {"clients":len(chat.clients),
                     "name": chat.name,
                     "message": [{"author": author,
                                  "id": body['id'],
                                  "when": self.print_time(),
                                  "text": prettify(cgi.escape(body['text']))
                              }]
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

        messages = Message.query_last_from_chat(chat.key.urlsafe())
        message_list = [{"author": cgi.escape(m.author),
                         "id": ''.join([client_id[:-8],m.client]),
                         "when": m.date.strftime("%b %d %Y %H:%M:%S"),
                         "text": prettify(cgi.escape(m.text))} for m in messages]

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
                 "save": c.options['save'],
                 "conversations": c.options['conversations'],
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

