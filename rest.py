import datetime
import os
import json
import webapp2
import cgi
import re
import logging
from google.appengine.api import channel, users
from google.appengine.ext import ndb
from models import Event, Message, ChatManager, Activity
try:
    from matplotlib import mathtext
except ImportError:
    pass

from StringIO import StringIO
from threading import Thread

# global font properties for math
try:
    font_properties = mathtext.FontProperties()
    font_properties.set_size(12)
except NameError:
    pass

#global regexp
regexp_latex = re.compile("\\$.*?(?<!\\\\)\\$")

def parse_math(message):
    equations = regexp_latex.findall(message)

    replacements = list()
    for eq in equations:
        output = StringIO()
        try:
            mathtext.math_to_image(eq,
                                   output,
                                   dpi = 72,
                                   prop = font_properties,
                                   format = 'svg')
            svg_equation = ''.join(output.getvalue().split('\n')[4:])
            replacements.append(svg_equation)

        except ValueError:
            replacements.append('<i>Error in equation</i>')

        output.close()

    newmessage = regexp_latex.sub('{}', message)
    
    try:
        newmessage = newmessage.format(*replacements)
    except:
        newmessage = 'Could not understand your message'
        
    return newmessage


def prettify(message):
    image_formats = ['.png','.gif','.jpg','.jpeg']
    video_formats = ['.mp4','.ogg','.webm']
    youtube_urls = ['youtube.com','youtu.be']
    urls = ['http://','https://','cloudchatroom.appspot.com']
    newmessage = list()

    message = parse_math(message)

    for w in message.split():
        if any([fmt in w for fmt in video_formats]):
            newmessage.append(
                u'<video class="img-responsive" controls><source src="{}" type="video/webm"></video>'.format(w)
            )
        elif any([fmt in w for fmt in youtube_urls]):
            newmessage.append(
                u'<iframe width="480" height="320" src="//www.youtube.com/embed/{}" frameborder="0" allowfullscreen></iframe>'.format(w[-11:])
            )
        elif any([fmt in w for fmt in image_formats]):
            newmessage.append(
                u'<img src="{}" class="img-responsive">'.format(w)
            )
        elif any([fmt in w for fmt in urls]):
            newmessage.append(
                u'<a href="{}" target="_blank">{}...</a>'.format(w,w[:20])
            )
        else:
            newmessage.append(w)
          
    newmessage = ' '.join(newmessage)
      
    if len(newmessage) < 32000:
        return newmessage
    else:
        return 'Message too long'


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
        form = self.request.get('format')
        
        if form == 'json':
            self.response.out.headers['Content-Type'] = 'application/json'
            self.response.out.write(
                json.dumps(
                    Message.query_all_from_chat(chat_key)
                )
            )
            
        else:
            text = []
            for message in Message.query_all_from_chat(chat_key,limit=True):
                text.append(u'{}, {}: {}'.format(message['author'],
                                                 message['date'],
                                                 message['text'])
                        )
            
            text.reverse()
            self.response.out.headers['Content-Type'] = 'text/plain'
            self.response.out.write(u'\n'.join(text))


class OpenResource(webapp2.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        user = users.get_current_user()
        client_id = data['id']
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        if user:
            Activity(
                user = user,
                chat = chat.key).put()
        
        for client in chat.clients:
            channel.send_message(
                client,
                json.dumps(
                    {"clients":len(chat.clients)+1,
                     "name": chat.name,
                     "cursor": False,
                     "message": []
                 }
                )
            )


        last_message_when = Message.query_time_from_chat(chat.key)
        if last_message_when < (
                datetime.datetime.now()-datetime.timedelta(hours=4)):
            logging.info('Reset clients in chat {}'.format(chat.key.urlsafe()))
            chat.reset_clients()
        
        chat.add_client(client_id)


class CloseResource(webapp2.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        client_id = data['id']
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        for client in chat.clients:
            channel.send_message(
                client,
                json.dumps(
                    {"name": chat.name,
                     "clients":len(chat.clients)-1,
                     "cursor": False,
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
            newchat.save = False
            newchat.options = {"save": False,
                               "conversations": False,
                               "persistent": False}
            newchat_key = newchat.put()

            channel.send_message(
                body['from'],
                json.dumps(
                    {"clients":len(chat.clients),
                     "name": chat.name,
                     "cursor": False,
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
                     "cursor": False,
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
                     "cursor": False,
                     "message": [{"author": 'ADMIN',
                                  "id": '0',
                                  "when": self.print_time(),
                                  "text": 'This user is no longer connected'
                              }]
                 }
                )
            )
            

class ArchiveResource(webapp2.RequestHandler):
    def get(self):
        cursor_key = self.request.get('cursor')
        client_id = self.request.get('id')
        chat = ndb.Key(urlsafe=client_id[:-8]).get()

        messages, cursor, more = Message.query_cursor_from_chat(
            chat.key.urlsafe(),
            cursor_key)
        messages_sent = list()

        for m in messages:
            messages_sent.append({"author": cgi.escape(m.author),
                                  "id": ''.join([client_id[:-8],m.client]),
                                  "when": m.date.strftime("%b %d %Y %H:%M:%S"),
                                  "text": prettify(cgi.escape(m.text))}
            )
            
        try:
            cursor_key = cursor.urlsafe()
        except AttributeError:
            cursor_key = ''

        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({'cursor': cursor_key,
                                            'more': more,
                                            'messages': messages_sent}))


class ThreadedMessage(Thread):
    def __init__(self,client,message):
        Thread.__init__(self)
        self.client = client
        self.message = message

    def run(self):
        channel.send_message(self.client,self.message)        


class MessageResource(webapp2.RequestHandler):
    def print_time(self):
        return datetime.datetime.now().strftime("%b %d %Y %H:%M:%S")        
        
    def post(self):
        body = json.loads(self.request.body)
        chat_key = body['id'][:-8]
        chat = ndb.Key(urlsafe=chat_key).get()
        threads = []
        message = Message(parent = chat.key,
                          author = body['author'],
                          text   = body['text'],
                          peers  = len(chat.clients),
                          client = body['id'][-8:])
                          
        future = message.put_async()

        if users.get_current_user() == chat.owner:
            author = '<u>'+cgi.escape(body['author'])+'</u>'
        else:
            author = cgi.escape(body['author'])

        for i,client_id in enumerate(chat.clients):
            message_string = json.dumps(
                {"clients":len(chat.clients),
                 "name": chat.name,
                 "cursor": False,
                 "message": [{"author": author,
                              "id": body['id'],
                              "when": self.print_time(),
                              "text": prettify(cgi.escape(body['text']))
                          }]
             }
            )
            threads.append(ThreadedMessage(client_id,message_string))
            threads[i].start()

        for thread in threads:
            thread.join()

        future.get_result()


class ConnectionResource(webapp2.RequestHandler):
    def post(self):
        pass


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
                     "cursor": False,
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
                activity = Activity.query_user(user,10)

        else:
            chats = ChatManager.query_public(10)
            activity = []

        chat_list = list()
        for c in chats:
            chat_list.append(
                {"name": c.name,
                 "date": c.date.strftime("%b %d %Y %H:%M:%S"),
                 "owner": c.owner.nickname(),
                 "key": c.key.urlsafe(),
                 "persistent": c.options['persistent'],
                 "save": c.save,
                 "conversations": c.options['conversations'],
                 "num_clients": c.num_clients(),
                 "private": c.private}
            )

        activity_list = list()
        for a in activity:
            thischat = a.chat.get()
            activity_list.append(
                {"name": thischat.name,
                 "date": a.date.strftime("%b %d %Y %H:%M:%S"),
                 "key":  thischat.key.urlsafe(),
                 "last": Message.query_time_from_chat(a.chat).strftime("%b %d %Y %H:%M:%S"),
                 "creator": thischat.owner.nickname()}
            )

        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps({'chats': chat_list,
                                            'activity': activity_list}))


    def post(self):
        user = users.get_current_user()
        body = json.loads(self.request.body)
        chat = ChatManager()
        chat.name = body['name']
        chat.active = True
        chat.private = body['private']
        chat.owner = user
        chat.save = body['save']
        chat.options = {"save": body['save'],
                        "conversations": body['conversations'],
                        "persistent": body['persistent']}
        chat.put()

    @ndb.transactional
    def delete(self):
        chat = ndb.Key(urlsafe=self.request.get('id')).get()
        chat.active = False
        chat.put()
