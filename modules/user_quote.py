# -*- coding: utf-8 -*-
import itertools
import pickle
import random
import re
import urllib2

from modules import filename
import web

MAX_LOGS = 30
MAX_QUOTES = 100
QVERSION = 2


def upgrade(self, cur_version):
    if cur_version == 1:
        self.quotes = {
            user: [(msg, None) for msg in msgs]
            for user, msgs in self.quotes.items()
        }
        cur_version += 1
    else:
        return
    save_quotes(self)


def setup(self):
    self.logs = []
    self.quotes = {}
    try:
        f = open(filename(self, "quotes"), "r")
        num, self.quotes = pickle.load(f)
        f.close()
    except IOError:
        pass
    upgrade(self, num)


def save_quotes(self):
    try:
        f = open(filename(self, "quotes"), "w")
        pickle.dump((QVERSION, self.quotes), f)
        f.close()
    except IOError:
        pass


def log(phenny, input):
    if MAX_LOGS is not None:
        phenny.logs.append((input.nick.lower(), input.group(1).replace("\n", "").lstrip(" ")))
        phenny.logs = phenny.logs[-MAX_LOGS:]
log.rule = r"(.*)"


_format_quote = u"<{}> {}".format


def quote_me(phenny, input):
    if input.group(2) is None or input.group(3) is None:
        return phenny.say("I'm not convinced you're even trying to quote someone???")
    user, msg = input.group(2), input.group(3)
    user = re.sub(r"[\[\]<>: +@]", "", user.lower())
    if (user, msg) in phenny.logs:
        try:
            phenny.logs.remove((user, msg))
        except ValueError:  # well it's gone now anyway (threads amirite)
            pass
        phenny.quotes.setdefault(user, []).append((msg, input.nick))
        phenny.quotes[user] = phenny.quotes[user][-MAX_QUOTES:]
        save_quotes(phenny)
        phenny.say("Quote added")
    else:
        phenny.say("I'm not convinced %s ever said that." % user)
quote_me.rule = ('$nick', ['quote'], r'\[?(?:\d\d?:?\s?)*\]?(<[\[\]@+ ]?\S+>|\S+:?)\s+(.*)')


def get_quote(phenny, input):
    if input.group(2) is None:
        if not phenny.quotes:
            return phenny.say("You guys don't even have any quotes.")
        nick, get_quote.last_quote, get_quote.last_sender = random.choice([
            (nick, quote, sender)
            for nick, quotes in phenny.quotes.iteritems()
            for quote, sender in quotes])
        return phenny.say(_format_quote(nick, get_quote.last_quote))
    else:
        nick = input.group(2).lower()
    if nick in phenny.quotes:
        get_quote.last_quote, get_quote.last_sender = random.choice(phenny.quotes[nick])
        return phenny.say(_format_quote(nick, get_quote.last_quote))
    return phenny.say("%s has never said anything noteworthy." % input.group(2))
get_quote.rule = (["quote"], r"(\S+)", r"? *$")


def get_quotes(phenny, input):
    if input.group(2) is None:
        quotes_string = u"\n".join(
            _format_quote(nick, quote)
            for nick, quotes in phenny.quotes.items()
            for quote, submitter in quotes)
    else:
        nick = input.group(2).lower()
        quotes_string = u"\n".join(
            _format_quote(nick, quote)
            for quote, submitter in phenny.quotes.get(nick, []))
    if quotes_string:
        try:
            url = web.dpaste(phenny, quotes_string)
        except urllib2.HTTPError as e:
            return phenny.say(u"Could not create quotes file: error code {}, reason: {}".format(
                e.code, e.reason))
        else:
            return phenny.say(url)
    else:
        return phenny.say("No quotes were found.")
get_quotes.rule = (["quotes"], r"(\S+)", r"? *$")


def get_quoter(phenny, input):
    nick = input.group(1)
    if nick is None:  # Last message
        if not hasattr(get_quote, 'last_sender'):
            return phenny.say(u"¯\_(ツ)_/¯")
        sender = get_quote.last_sender
        message = get_quote.last_quote
    else:  # Match quote
        message = input.group(2)
        quotes = phenny.quotes.get(nick, [])
        sender = next((
            sender for quote, sender in quotes
            if quote == message
        ), None)
        if sender is None:
            return phenny.say("I'm not convinced {} ever said that.".format(nick))
    if message.startswith("Nethaera: quote"):
        return phenny.say("{} is the dunkass who quoted that.".format(sender))
    return phenny.say("{} is the one who quoted that.".format(sender))

get_quoter.rule = (["quoter"], r"<([^>]+)> (.*)", r"?$")


def qnuke(phenny, input):
    if input.group(2) is None:
        return
    if input.nick not in phenny.ident_admin:
        return phenny.notice(input.nick, 'Requires authorization. Use .auth to identify')
    nick = input.group(2).lower()
    if nick in phenny.quotes:
        del phenny.quotes[nick]
        save_quotes(phenny)
        return phenny.say("All of %s's memorable quotes erased." % nick)
    return phenny.say("Yeah whatever.")
qnuke.rule = (["qnuke"], r"(\S+)")


def debug_log(phenny, input):
    if input.nick not in phenny.ident_admin:
        return phenny.notice(input.nick, 'Requires authorization. Use .auth to identify')
    tor = "["
    for log in phenny.logs:
        if len(tor) + len(log) >= 490:
            phenny.notice(tor)
            tor = ""
        tor += log + ", "
    return phenny.notice(input.nick, tor + "]")
debug_log.rule = (["debuglog"], )
