import inspect
import threading


class CommandInput(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True
        self.commands = []

    def run(self):
        while self.running:
            input = raw_input('> ')

            if input:
                self.parse_command(input)

    def parse_command(self, input):
        args = input.split(' ')
        command = args.pop(0)

        members = inspect.getmembers(self, predicate=inspect.ismethod)

        if command in [x[0] for x in members]:
            getattr(self, command)(args)
        else:
            self.invalid_command(input)

    def invalid_command(self, input):
        print 'ERR: Invalid command \'%s\'' % input

    def stop(self):
        self.running = False
