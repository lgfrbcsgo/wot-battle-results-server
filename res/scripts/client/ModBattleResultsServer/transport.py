class Transport(object):
    def send_message(self, data):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
