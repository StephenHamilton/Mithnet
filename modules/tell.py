#!/usr/bin/env python
"""
tell.py - Phenny Tell and Ask Module
Copyright 2008, Sean B. Palmer, inamidst.com
Licensed under the Eiffel Forum License 2.

http://inamidst.com/phenny/
"""

import os, re, time, random, datetime

maximum = 3

def loadReminders(fn): 
   result = {}
   f = open(fn)
   for line in f: 
      line = line.strip()
      if line: 
         try: tellee, teller, verb, timenow, msg = line.split('\t', 4)
         except ValueError: continue # @@ hmm
         result.setdefault(tellee, []).append((teller, verb, timenow, msg))
   f.close()
   return result

def dumpReminders(fn, data): 
   f = open(fn, 'w')
   for tellee in data.iterkeys(): 
      for remindon in data[tellee]: 
         line = '\t'.join((tellee,) + remindon)
         try: f.write(line + '\n')
         except IOError: break
   try: f.close()
   except IOError: pass
   return True

def setup(self): 
   fn = self.nick + '-' + self.config.host + '.tell.db'
   self.tell_filename = os.path.join(os.path.expanduser('~/.phenny'), fn)
   if not os.path.exists(self.tell_filename): 
      try: f = open(self.tell_filename, 'w')
      except OSError: pass
      else: 
         f.write('')
         f.close()
   self.reminders = loadReminders(self.tell_filename) # @@ tell


def f_remind(phenny, input): 
   if re.match("zellio",input.nick.lower()) or re.match("zellio",input.user.lower()) or  re.match(".*\.es\.its\.nyu\.edu",input.host.lower()):
      return
   teller = input.nick

   # @@ Multiple comma-separated tellees? Cf. Terje, #swhack, 2006-04-15
   verb, tellee, msg = input.groups()
   verb = verb.encode('utf-8')
   tellee = tellee.encode('utf-8')
   msg = msg.encode('utf-8')

   tellee_original = tellee.rstrip('.,:;')
   tellee = tellee_original.lower()

   if not os.path.exists(phenny.tell_filename): 
      return

   if len(tellee) > 20: 
      return phenny.reply('That nickname is too long.')
   if not msg:
      return phenny.reply(verb + ' ' + tellee + ' what?')

   timenow = repr(time.time())
   if not tellee in (teller.lower(), phenny.nick.lower(), 'me'): # @@
      # @@ <deltab> and year, if necessary
      warn = False
      if not phenny.reminders.has_key(tellee): 
         phenny.reminders[tellee] = [(teller, verb, timenow, msg)]
      else: 
         if len(phenny.reminders[tellee]) >= 2*maximum:
            return phenny.reply("No. I can't remember that many things")
         #    warn = True
         phenny.reminders[tellee].append((teller, verb, timenow, msg))
      # @@ Stephanie's augmentation
      response = "I'll pass that on when %s is around." % tellee_original
      # if warn: response += (" I'll have to use a pastebin, though, so " + 
      #                       "your message may get lost.")

      rand = random.random()
      if rand > 0.999: response = "yeah, yeah"
      elif rand > 0.95: response = "yeah, sure, whatever"

      phenny.reply(response)
   elif teller.lower() == tellee: 
      phenny.say('You can %s yourself that.' % verb)
   else: phenny.say("Hey, I may be a bot, but that doesnt mean I'm stupid!")
   dumpReminders(phenny.tell_filename, phenny.reminders) # @@ tell
f_remind.name = 'remind'
f_remind.rule = ('$nick', ['tell', 'ask', 'show'], r'(\S+) (.*)')

def getReminders(phenny, channel, key, tellee): 
   lines = []
   template = "%s: <%s> %s %s %s (%s)"

   for (teller, verb, timethen, msg) in phenny.reminders[key]: 
      lines.append(template % (tellee, teller, verb, tellee, msg, prettydate(datetime.datetime.utcfromtimestamp(float(timethen)))))

   try: del phenny.reminders[key]
   except KeyError: phenny.msg(channel, 'Er...')
   return lines

def message(phenny, input): 
   if not input.sender.startswith('#'): return

   tellee = input.nick
   channel = input.sender

   if not os.path.exists(phenny.tell_filename): 
      return

   reminders = []
   remkeys = list(reversed(sorted(phenny.reminders.keys())))
   for remkey in remkeys: 
      if not remkey.endswith('*') or remkey.endswith(':'): 
         if tellee.lower() == remkey: 
            reminders.extend(getReminders(phenny, channel, remkey, tellee))
      elif tellee.lower().startswith(remkey.rstrip('*:')): 
         reminders.extend(getReminders(phenny, channel, remkey, tellee))

   for line in reminders[:maximum]: 
      phenny.say(line)

   if reminders[maximum:]: 
      phenny.say('Further messages sent privately')
      for line in reminders[maximum:]: 
         phenny.msg(tellee, line)

   if len(phenny.reminders.keys()) != remkeys: 
      dumpReminders(phenny.tell_filename, phenny.reminders) # @@ tell
message.rule = r'(.*)'
message.priority = 'low'

def clearreminders(phenny, input):
   if input.nick not in phenny.ident_admin: return phenny.reply('Requires authorization. Use .auth to identify')
   phenny.reminders.clear()
   dumpReminders(phenny.tell_filename, phenny.reminders)
   phenny.say('Reminders cleared')
clearreminders.commands = ['clearrem']
clearreminders.priority = 'low'

def reloadreminders(phenny, input):
   setup(phenny.bot)
reloadreminders.commands = ['rerem']
reloadreminders.priority = 'medium'

def prettydate(d):
   diff = datetime.datetime.utcnow() - d
   s = diff.seconds
   if diff.days > 7:
      return d.strftime('%d %b')
   elif diff.days == 1:
      return '1 day ago'
   elif diff.days > 1:
      return '%d days ago' % diff.days
   elif s <= 1:
      return 'just now'
   elif s < 60:
      return '%d seconds ago' % s
   elif s < 120:
      return '1 minute ago'
   elif s < 3600:
      return '%d minutes ago' % (s/60)
   elif s < 7200:
      return '1 hour ago'
   else:
      return '%d hours ago' % (s/3600)

if __name__ == '__main__': 
   print __doc__.strip()
