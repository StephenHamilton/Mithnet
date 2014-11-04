#!/usr/bin/env python
"""
bot.py - IRC Bot Engine
"""

import sys, os, re, threading, imp
import irc

home = os.getcwd()

def decode(bytes):
  try: text = bytes.decode('utf-8')
  except UnicodeDecodeError:
    try: text = bytes.decode('iso-8859-1')
    except UnicodeDecodeError:
      text = bytes.decode('cp1252')
  return text

class IRCBot(irc.Client):
  def __init__(self, config):
    args = (config.nick, config.user, config.name, config.channels, config.password)
    irc.Client.__init__(self, *args)
    self.config = config
    self.setup()

  def setup(self):
    self.modules = {}
    self.dpaste_cache = {}

    home = os.getcwd()

    # Load core modules first
    filenames = []
    for fn in os.listdir(os.path.join(home, 'core')):
      if fn.endswith('.py') and not fn[:8] == '__init__':
        filenames.append(os.path.join(home, 'core', fn))

    # Everything else
    if not hasattr(self.config, 'enable'):
      for fn in os.listdir(os.path.join(home, 'modules')):
        if fn.endswith('.py') and not fn.startswith('_'):
          filenames.append(os.path.join(home, 'modules', fn))
    else:
      for fn in self.config.enable:
        filenames.append(os.path.join(home, 'modules', fn + '.py'))
    excluded_modules = getattr(self.config, 'exclude', [])
    print repr(excluded_modules)
    for filename in filenames:
      name = os.path.basename(filename)[:-3]
      if name in excluded_modules: continue
      try: module = imp.load_source(name, filename)
      except Exception, e:
        print >> sys.stderr, "Error loading %s: %s (in bot.py)" % (name, e)
      else:
        if hasattr(module, 'setup'):
          module.setup(self)
        self.register(name, vars(module))

    if self.modules:
      print >> sys.stderr, 'Registered modules:', ', '.join(self.modules.keys())
    else: print >> sys.stderr, "Warning: Couldn't find any modules"

    self.bind_commands()
    self.runonce = {}

  def register(self, name, variables):
    self.modules[name] = {}
    for key, obj in variables.iteritems():
      if hasattr(obj, 'commands') or hasattr(obj, 'rule'):
        self.modules[name][key] = obj

  def unregister(self, name):
    del self.modules[name]

  def bind_commands(self):
    self.doc = {}
    self.commands = {'high': {}, 'medium': {}, 'low': {}}
    print '\nRegistering commands...'
    def bind(self, priority, regexp, func):
      print priority, '\t', regexp.pattern.encode('utf-8'), '\t', func
      # register documentation
      if not hasattr(func, 'name'):
        func.name = func.__name__
      if func.__doc__:
        if hasattr(func, 'example'):
          example = func.example
          example = example.replace('$nickname', self.nick)
        else: example = None
        self.doc[func.name] = (func.__doc__, example)
      self.commands[priority].setdefault(regexp, []).append(func)

    def sub(pattern, self=self):
      # These replacements have significant order
      pattern = pattern.replace('$nickname', re.escape(self.nick))
      return pattern.replace('$nick', r'%s[,:] +' % re.escape(self.nick))

    for module, variables in self.modules.iteritems():
      for name, func in variables.iteritems():
        # print name, func
        if not hasattr(func, 'priority'):
          func.priority = 'medium'

        if not hasattr(func, 'thread'):
          func.thread = True

        if not hasattr(func, 'event'):
          func.event = 'PRIVMSG'
        else: func.event = func.event.upper()

        if hasattr(func, 'rule'):
          if isinstance(func.rule, str):
            pattern = sub(func.rule)
            regexp = re.compile(pattern)
            bind(self, func.priority, regexp, func)

          if isinstance(func.rule, tuple):
            types = list(map(type, func.rule))
            # 1) e.g. ('$nick', '(.*)')
            if types == [str, str]:
              prefix, pattern = func.rule
              prefix = sub(prefix)
              regexp = re.compile(r"^" + prefix + pattern)
              bind(self, func.priority, regexp, func)

            # 2) e.g. (['p', 'q'], '(.*)')
            elif types == [list, str]:
              prefix = self.config.prefix
              commands, pattern = func.rule
              for command in commands:
                 command = r'(%s) +%s' % (command, pattern)
                 regexp = re.compile(r"^" + prefix + command)
                 bind(self, func.priority, regexp, func)

            # 3) e.g. ('$nick', ['p', 'q'], '(.*)')
            elif types == [str, list, str]:
              prefix, commands, pattern = func.rule
              prefix = sub(prefix)
              for command in commands:
                command = r'(%s) +' % command
                regexp = re.compile(''.join((r"^", prefix, command, pattern)))
                bind(self, func.priority, regexp, func)

            # 4) e.g. (['p', 'q'], '(.*)', '?')
            elif types == [list, str, str]:
              prefix = self.config.prefix
              commands, pattern, ending = func.rule
              for command in commands:
                 command = r'(%s)(?: +%s)%s' % (command, pattern, ending)
                 regexp = re.compile(r"^" + prefix + command)
                 bind(self, func.priority, regexp, func)

        if hasattr(func, 'commands'):
          for command in func.commands:
            template = r'^%s(%s)(?: +(.*))?$'
            pattern = template % (self.config.prefix, command)
            regexp = re.compile(pattern)
            bind(self, func.priority, regexp, func)

  def context(self, origin, text):
    class ContextWrapper(object):
      def __init__(self, phenny):
        self.bot = phenny
      # For compatibility with phenny-style modules that rely on this
      def __getattr__(self, attr):
        sender = origin.sender or text
        if attr == 'reply':
          if sender.startswith('#'):
            return (lambda msg:
              self.bot.msg(sender, origin.nick + ': ' + msg))
          else:
            return (lambda msg:
              self.bot.msg(origin.nick, msg))
        elif attr == 'say':
          return lambda msg: self.bot.msg(sender, msg)
        return getattr(self.bot, attr)

    return ContextWrapper(self)

  def input(self, origin, text, bytes, match, event, args, findall):
    class CommandInput(unicode):
      def __new__(cls, text, origin, bytes, match, event, args, findall):
        s = unicode.__new__(cls, text)
        s.sender = origin.sender
        s.nick = origin.nick
        s.event = event
        s.bytes = bytes
        s.match = match
        s.group = match.group
        s.groups = match.groups
        s.findall = findall
        s.args = args
        s.admin = origin.nick in self.config.adminnicks
        s.owner = origin.nick == self.config.owner
        s.user = origin.user
        s.host = origin.host
        return s

    return CommandInput(text, origin, bytes, match, event, args, findall)

  def call(self, func, origin, phenny, input):
    try: func(phenny, input)
    except Exception as e:
      self.error(origin)

  def dispatch(self, origin, args):
    if origin.nick.lower() in ["shellby", "spacenet"]:  # hardXcode
      return
    bytes, event, args = args[0], args[1], args[2:]
    text = decode(bytes)

    for priority in ('high', 'medium', 'low'):
      items = self.commands[priority].items()
      for regexp, funcs in items:
        for func in funcs:
          if event != func.event: continue
          match = regexp.search(text)
          if match:
            context = self.context(origin, text)
            input = self.input(origin, text, bytes, match, event, args,
              (lambda r, t: lambda: r.findall(t))(regexp, text))

            if func.thread:
              targs = (func, origin, context, input)
              t = threading.Thread(target=self.call, args=targs)
              t.start()
            else: self.call(func, origin, context, input)

if __name__ == '__main__':
   print __doc__
