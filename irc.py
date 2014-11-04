#!/usr/bin/env python
"""
irc.py - IRC Handler
"""

import sys, re, time, traceback
import socket, asyncore, asynchat
import threading

class Origin(object): 
  source = re.compile(r'([^!]*)!?~?([^@]*)@?(.*)')

  def __init__(self, bot, source, args): 
    match = Origin.source.match(source or '')
    self.nick, self.user, self.host = match.groups()

    if len(args) > 1: 
      target = args[1]
    else: target = None
    # Resolve sender to user's name for PM, default to channel name
    mappings = {bot.nick: self.nick, None: None}
    self.sender = mappings.get(target, target)

class Client(asynchat.async_chat):
  def __init__(self, nick, user, name, channels=[], password=None): 
    asynchat.async_chat.__init__(self)
    self.set_terminator('\r\n')
    self.buffer = ''

    self.nick = nick
    self.user = user
    self.name = name
    self.password = password
    self.channels = channels or []
    
    # Rate limiting
    self.sending = threading.RLock()
    self.rate = 5.0 # Messages every
    self.per = 6.0 # Seconds
    self.allowance = self.rate # Messages
    self.last_check = time.time()
    
    # Loop detection
    self.stack = []

    self.debug = False
  
  def run(self, host, port=6667):
    if self.debug:
      message = 'Connecting to %s:%s...' % (host, port)
      print >> sys.stderr, message,
    s = None
    # for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
    for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
      af, socktype, proto, canonname, sa = res
      try:
        s = socket.socket(af, socktype, proto)
      except socket.error as msg:
        s = None
        continue
      try:
        self.addr = sa
        s.connect(sa)
      except socket.error as msg:
        s.close()
        s = None
        continue
      break
    if s is None:
      if self.debug:
        print >> sys.stderr, 'could not open socket'
      sys.exit(1)
    # Lets hope asyncore doesnt change anything in create_socket and connect
    # Emulating http://hg.python.org/cpython/file/2.7/Lib/asyncore.py#l295
    s.setblocking(0)
    self.set_socket(s)
    # Emulating http://hg.python.org/cpython/file/2.7/Lib/asyncore.py#l344
    self.connected = False
    self.connecting = True
    self.handle_connect_event()
    try: asyncore.loop()
    except KeyboardInterrupt:
      sys.exit()
  
  def handle_connect(self):
    if self.debug:
      print >> sys.stderr, 'Connected!'
    if self.password:
      self.__woob(('PASS', self.password))
    self.__woob(('NICK', self.nick))
    self.__woob(('USER', self.user, '+i', self.nick), self.name)
    
  def handle_close(self):
    if self.debug:
      print >> sys.stderr, 'Closed!'
    self.close()
  
  # Unthrottled (outside of race conditions) write
  def __woob(self, args, text=None):
    self.sending.acquire()
    if self.debug:
      message = '%r %r' % (args, text)
      print >> sys.stderr, message
    try:
      if text is not None:
        self.push((' '.join(args) + ' :' + text)[:510] + '\r\n')
      else: self.push(' '.join(args)[:510] + '\r\n')
    except IndexError: pass
    self.sending.release()
  
  # Throttled write
  def __write(self, args, text, important):
    self.sending.acquire()
    now = time.time()
    elapsed = now - self.last_check
    self.last_check = now
    self.allowance += elapsed * (self.rate / self.per)
    if self.allowance > self.rate:
      self.allowance = self.rate # Throttle
    if self.allowance < 1.0:
      if important:
        # Can't drop, wait until we can send it
        wait = (1.0 - self.allowance) * (self.per / self.rate)
        time.sleep(wait)
        self.allowance += wait * (self.rate / self.per)
      else:
        # Drop message
        self.sending.release()
        return
    self.allowance -= 1.0
    if self.debug:
      message = '%r %r %r' % (args, text, self.allowance)
      print >> sys.stderr, message
    try:
      if text is not None:
        self.push((' '.join(args) + ' :' + text)[:510] + '\r\n')
      else: self.push(' '.join(args)[:510] + '\r\n')
    except IndexError: pass
    self.sending.release()
  
  # Safe write
  def write(self, args, text=None, important=True):
    def safe(input):
      input = input.replace('\n', '')
      input = input.replace('\r', '')
      if isinstance(input, unicode):
        return input.encode('utf-8')
      else:
        return input
    try:
      args = [safe(arg) for arg in args]
      if text is not None:
        text = safe(text)
      self.__write(args, text, important)
    except Exception, e: pass
  
  def collect_incoming_data(self, data):
    self.buffer += data
  
  def found_terminator(self):
    line = self.buffer
    self.buffer = ''
    
    if self.debug:
      print >> sys.stderr, line
    if line.startswith(':'):
      source, line = line[1:].split(' ', 1)
    else: source = None
    
    if ' :' in line: 
      argstr, text = line.split(' :', 1)
    else: argstr, text = line, ''
    args = argstr.split()

    origin = Origin(self, source, args)
    self.dispatch(origin, tuple([text] + args))

    # move ping pong to core module?
    if args[0] == 'PING': 
      self.__woob(('PONG', text))
  
  def dispatch(self, origin, args):
    pass
    
  # Shortcuts
  def __writecmd(self, command, recipient, text):
    # if isinstance(text, unicode): 
      # try: text = text.encode('utf-8')
      # except UnicodeEncodeError, e: 
        # text = e.__class__ + ': ' + str(e)
    # if isinstance(recipient, unicode): 
      # try: recipient = recipient.encode('utf-8')
      # except UnicodeEncodeError, e: 
        # return

    # Loop detection, do not send more than 4 identical messages in 24 seconds
    now = time.time()
    if self.stack and (now - self.stack[0][0]) > 24:
      self.stack = [i for i in self.stack if (now - i[0]) < 24]
    messages = [m[1] for m in self.stack]
    if messages.count(text) >= 4: 
      text = '<loop detected>'
      if messages.count('<loop detected>') > 0: 
        return
    self.stack.append((time.time(), text))
    self.stack = self.stack[-12:]

    self.write((command, recipient), text)
  
  def msg(self, recipient, text): 
    self.__writecmd("PRIVMSG", recipient, text)
  
  def notice(self, recipient, text): 
    self.__writecmd("NOTICE", recipient, text)
    
  def error(self, origin): 
    try:
      trace = traceback.format_exc()
      print >> sys.stderr, trace
      lines = list(reversed(trace.splitlines()))

      report = [lines[0].strip()]
      for line in lines: 
        line = line.strip()
        if line.startswith('File "/'): 
          report.append(line[0].lower() + line[1:])
          break
      else: report.append('source unknown')

      self.msg(origin.sender, report[0] + ' (' + report[1] + ')')
    except: self.msg(origin.sender, "Got an error while attempting to report an error. This is probably bad.")

if __name__=="__main__":
  print __doc__