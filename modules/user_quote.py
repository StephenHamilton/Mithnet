import pickle
import random
import re
import urllib
import urllib2
from modules import filename

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
        nick = random.choice(phenny.quotes.keys())
    else:
        nick = input.group(2).lower()
    if nick in phenny.quotes:
        return phenny.say("<%s> %s" % (nick, random.choice(phenny.quotes[nick])[0]))
    return phenny.say("%s has never said anything noteworthy." % input.group(2))
get_quote.rule = (["quote"], r"(\S+)", r"?$")

def get_quotes(phenny, input):
    if input.group(2) is None:
        quotes_string = "\n".join(["<%s> %s" % (nick, quote[0]) for nick,quotes in phenny.quotes.items() for quote in quotes])
    else:
        nick = input.group(2).lower()
        quotes_string = "\n".join(["<%s> %s" % (nick, quote[0]) for quote in phenny.quotes[nick]])
    if quotes_string:
        data = urllib.urlencode({"content": quotes_string})
        request = urllib2.Request("http://dpaste.com/api/v2",data)
        response = urllib2.urlopen(request)
        return phenny.say(response.geturl())
    else:
        return phenny.say("no quotes were found")
get_quotes.rule = (["quotes"], r"(\S+)", r"?$")

def qnuke(phenny, input):
    if input.group(2) is None:
        return
    if input.nick not in phenny.ident_admin: return phenny.notice(input.nick, 'Requires authorization. Use .auth to identify')
    nick = input.group(2).lower()
    if nick in phenny.quotes:
        del phenny.quotes[nick]
        save_quotes(phenny)
        return phenny.say("All of %s's memorable quotes erased." % nick)
    return phenny.say("Yeah whatever.")
qnuke.rule = (["qnuke"], r"(\S+)")


def debug_log(phenny, input):
    if input.nick not in phenny.ident_admin: return phenny.notice(input.nick, 'Requires authorization. Use .auth to identify')
    tor = "["
    for log in phenny.logs:
        if len(tor) + len(log) >= 490:
            phenny.notice(tor)
            tor = ""
        tor += log + ", "
    return phenny.notice(input.nick, tor + "]")
debug_log.rule = (["debuglog"], )
