# vim: set fileencoding=utf-8 :

from django.core.management.base import BaseCommand
from convertor.models import Message
import datetime
from xml.dom.ext.reader import Sax2
import glob
import os
import xml.dom.minidom


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
	for c in head.getElementsByTagName('contact'):
		if c.hasAttribute('type') and c.getAttribute('type') == 'myself':
			my_from = c.getAttribute('contactId')
	year = int(date_xml.getAttribute('year'))
	month = int(date_xml.getAttribute('month'))

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

		date = datetime.datetime(
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
			type = type,
			text = text,
			from_user = from_user,
			from_nick = from_nick,
			myself = myself,
			account = my_from,
		)
		msg.save()
		print msg


class Command(BaseCommand):
	def handle(self, *args, **kwargs):
		if len(args) != 2:
			print "Usage:\n ./manage.py <kopete_dir> <adium_dir>"
			return
		kopete_dir = args[0]
		adium_dir = args[1]
		
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
		for el in Message.objects.filter(myself=False).values('from_user', 'account', 'type').annotate():
			print el
			first_date = False
			from_user = el['from_user']
			account = el['account']
			type = el['type']
			adium_type = 'Jabber' if type == 'jabber' else 'ICQ'






			doc = xml.dom.minidom.Document()
			chat = doc.createElement("chat")
			chat.setAttribute("xmlns", "http://purl.org/net/ulf/ns/0.4-02")
			chat.setAttribute("account", account)
			chat.setAttribute("service", type)
			doc.appendChild(chat)

			event = doc.createElement("event")
			event.setAttribute("type", "windowOpened")
			event.setAttribute("sender", from_user)

			chat.appendChild(event)
		
			for m in Message.objects.filter(from_user=from_user, account=account, type=type).order_by('date'):

				if not first_date:
					first_date = m.date
				# Write xml
# <?xml version="1.0" encoding="UTF-8" ?>
# <chat xmlns="http://purl.org/net/ulf/ns/0.4-02" account="11111111" service="ICQ"><event type="windowOpened" sender="11111111" time="2010-09-20T09:32:31+03:00"/>
# <message sender="11111111" time="2010-09-20T09:32:40+03:00" alias="Some Nickname"><div><span style="background-color: #ffffff; font-family: Helvetica; font-size: 12pt;">как дела?</span></div></message>
# </chat>
				msg = doc.createElement("message")
				msg.setAttribute("sender", m.from_user)
				msg.setAttribute("time", m.date.isoformat())
				msg.setAttribute("alias", m.from_nick)
				
				div = doc.createElement("div")
				msg.appendChild(div)

				chat.appendChild(msg)

				span = doc.createElement("span")
				span.setAttribute("style", "background-color: #ffffff; font-family: Helvetica; font-size: 12pt;")
				div.appendChild(span)

				span_text = doc.createTextNode(m.text)
				span.appendChild(span_text)

			if not first_date:
				continue

			event.setAttribute("time", first_date.isoformat())
			xml_str = doc.toxml(encoding='UTF-8')
			# print xml_str

			#Logs/Jabber.myaccount@example.com/toaccount@example.org/toaccount@example.org (2010-09-20T21.29.27+0300).chatlog/toaccount@example.org (2010-09-20T21.29.27+0300).xml
			seconds_dir = adium_type + '.' + account
			user_and_date = from_user + ' (%s)' % first_date.isoformat()
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


