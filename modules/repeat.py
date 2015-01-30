import collections

REPEAT_LIMIT = 3
logs = collections.defaultdict(lambda: [None, collections.deque()])


def peer_pressure(phenny, input):
    global logs
    # Don't respond to PMs
    if input.sender[0] != "#":
        return
    try:  # Reload error garbage
        last_word, log_queue = logs[input.sender]
    except:
        return
    # Don't respond twice to the same chain
    if last_word == input:
        return
    log_queue.append(input)
    # Drop the excess
    while len(log_queue) > REPEAT_LIMIT:
        log_queue.popleft()
    # If all the messages are that last message.
    if all(q == input for q in log_queue) and len(log_queue) >= REPEAT_LIMIT:
        phenny.say(input)
        log_queue.clear()
        logs[input.sender][0] = input
peer_pressure.name = "repeat"
peer_pressure.rule = r'.*'
