# vim: set fileencoding=utf-8 :

from django.db import models

TYPES = (
('icq', 'ICQ'),
('jabber', 'Jabber'),
)

class Chat(models.Model):
	account = models.CharField(u'Аккаунт', max_length=100)
	type = models.SlugField(u'Тип', choices=TYPES)

class Message(models.Model):
	date = models.DateTimeField(u'Дата')
	text = models.TextField(u'Текст')
	from_user = models.CharField(u'От', max_length=100)
	from_nick = models.CharField(u'От (ник)', max_length=100)
	myself = models.BooleanField(u'От меня', default=False)
	chat = models.ForeignKey(Chat, related_name='messages')

	def __unicode__(self):
		return u'%s. %s: %s' % (self.date, self.from_nick, self.text)


