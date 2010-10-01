# vim: set fileencoding=utf-8 :

from django.core.management.base import BaseCommand
from convertor.models import Message, Chat
from xml.dom.ext.reader import Sax2
import glob
import os
import xml.dom.minidom


from datetime import datetime, tzinfo, timedelta
import time

TZ_SECONDS = time.timezone

def adium_format_date(dt):
	return dt.strftime("%Y-%m-%dT%H:%M:%S%z")

class TZ(tzinfo):
	def utcoffset(self, dt): return timedelta(seconds=TZ_SECONDS)
	def dst(self, dt): return timedelta(hours=1)


def parse_file(filename):
	print u"*** Parse %s file ***" % filename
	reader = Sax2.Reader()
	fh = open(filename, 'r')
	s = fh.read()
	fh.close()
	d = reader.fromString(s)
	type = 'jabber' if filename.find('JabberProtocol') != -1 else 'icq'
	head = d.getElementsByTagName('head')[0]
	date_xml = head.getElementsByTagName('date')[0]
	my_from = ''
	with_account = None
	for c in head.getElementsByTagName('contact'):
		if c.hasAttribute('type'):
			if c.getAttribute('type') == 'myself':
				my_from = c.getAttribute('contactId')
		else:
			with_account = c.getAttribute('contactId')
	year = int(date_xml.getAttribute('year'))
	month = int(date_xml.getAttribute('month'))


	chat = Chat(
		account = my_from,
		type = type,
		with_account = with_account,
	)
	chat.save()


	for msg_xml in d.getElementsByTagName('msg'):
		day_time = msg_xml.getAttribute('time').split()
		day = int(day_time[0])
		time = day_time[1].split(':')
		hour = int(time[0])
		minutes = int(time[1])
		seconds = int(time[2])

		from_user = msg_xml.getAttribute('from')
		from_nick = msg_xml.getAttribute('nick')

		myself = True if from_user == my_from else False

		date = datetime(
				year = year,
				month = month,
				day = day,
				hour = hour,
				minute = minutes,
				second = seconds,
		)

		text = msg_xml.childNodes[0].nodeValue

		msg = Message(
			date = date,
			text = text,
			from_user = from_user,
			from_nick = from_nick,
			myself = myself,
			chat = chat,
		)
		msg.save()
		print msg


class Command(BaseCommand):
	def handle(self, *args, **kwargs):
		l = len(args)
		if not l in [2, 3]:
			print "Usage:\n ./manage.py <kopete_dir> <adium_dir> [TZ_SECONDS]"
			return
		kopete_dir = args[0]
		adium_dir = args[1]
		if l == 3:
			global TZ_SECONDS
			TZ_SECONDS = int(args[2])
		
		if not os.path.isdir(kopete_dir):
			print u"Kopete dir %s doesn't exist." % kopete_dir
			return

		if os.path.exists(adium_dir):
			if not os.path.isdir(adium_dir):
				print u"%s isn't dir" % adium_dir
				return
		else:
			print u"Create dir %s" % adium_dir
			os.makedirs(adium_dir)

		if kopete_dir[-1] != '/':
			kopete_dir += '/'
	
		Message.objects.all().delete()

		# Get information
		for f in glob.glob(kopete_dir + '*/*/*.xml'):
			parse_file(f)


		# Write information
		for chat_db in Chat.objects.all():
			msg_qs = chat_db.messages.all()
			if not msg_qs:
				continue

			first_date = msg_qs.order_by('date')[0].date
			from_user = chat_db.with_account
			adium_type = 'Jabber' if chat_db.type == 'jabber' else 'ICQ'


			doc = xml.dom.minidom.Document()
			chat = doc.createElement("chat")
			chat.setAttribute("xmlns", "http://purl.org/net/ulf/ns/0.4-02")
			chat.setAttribute("account", chat_db.account)
			chat.setAttribute("service", chat_db.type)
			doc.appendChild(chat)

			event = doc.createElement("event")
			event.setAttribute("type", "windowOpened")
			event.setAttribute("sender", from_user)

			chat.appendChild(event)
		
			for m in msg_qs.order_by('date'):
				# Write xml
# <?xml version="1.0" encoding="UTF-8" ?>
# <chat xmlns="http://purl.org/net/ulf/ns/0.4-02" account="11111111" service="ICQ"><event type="windowOpened" sender="11111111" time="2010-09-20T09:32:31+03:00"/>
# <message sender="11111111" time="2010-09-20T09:32:40+03:00" alias="Some Nickname"><div><span style="background-color: #ffffff; font-family: Helvetica; font-size: 12pt;">как дела?</span></div></message>
# </chat>
				msg = doc.createElement("message")
				msg.setAttribute("sender", m.from_user)
				msg.setAttribute("time", adium_format_date(  m.date.replace(tzinfo=TZ()) ) )
				msg.setAttribute("alias", m.from_user)
				
				div = doc.createElement("div")
				msg.appendChild(div)

				chat.appendChild(msg)

				span = doc.createElement("span")
				span.setAttribute("style", "background-color: #ffffff; font-family: Helvetica; font-size: 12pt;")
				div.appendChild(span)

				span_text = doc.createTextNode(m.text)
				span.appendChild(span_text)

			event.setAttribute("time", adium_format_date( first_date.replace(tzinfo=TZ()) ) )
			xml_str = doc.toxml(encoding='UTF-8')
			# print xml_str

			#Logs/Jabber.myaccount@example.com/toaccount@example.org/toaccount@example.org (2010-09-20T21.29.27+0300).chatlog/toaccount@example.org (2010-09-20T21.29.27+0300).xml
			seconds_dir = adium_type + '.' + chat_db.account
			user_and_date = from_user + ' (%s)' % adium_format_date( first_date.replace(tzinfo=TZ()) )
			path = os.path.join(
						adium_dir,
						'Logs',
						seconds_dir,
						from_user,
						user_and_date + '.chatlog',
						user_and_date + '.xml'
			)
			dir = os.path.dirname(path)
			if not os.path.exists(dir):
				print "Create %s dir" % dir
				os.makedirs(dir)

			fh = open(path, "w")
			fh.write(xml_str)
			fh.close()


