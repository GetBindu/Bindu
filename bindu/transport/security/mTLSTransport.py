import ssl

class mTLSTransport:
    """
    mTLS Transport for secure agent-to-agent communication.
    Ensures that only authorized agents can communicate in the Bindu network.
    """
    def __init__(self, cert_path, key_path, ca_path):
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        self.context.load_verify_locations(cafile=ca_path)
        self.context.verify_mode = ssl.CERT_REQUIRED

    def wrap_socket(self, sock, server_side=False):
        return self.context.wrap_socket(sock, server_side=server_side)
