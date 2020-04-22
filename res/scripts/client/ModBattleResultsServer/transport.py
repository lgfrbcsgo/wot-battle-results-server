class Transport(object):
    def send_message(self, data):
        raise NotImplementedError

    @property
    def host(self):
        raise NotImplementedError

    @property
    def port(self):
        raise NotImplementedError

    @property
    def origin(self):
        raise NotImplementedError