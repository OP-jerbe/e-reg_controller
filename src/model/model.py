import socket
from socket import SocketType
from threading import Lock
from typing import Optional

import src.helpers.helpers as h

ERROR_RESPONSES = {
    'bcr': 'bad command response',
    'bdr': 'bad data response',
    'cfe': 'communication failure error',
    'ine': 'internal unrecoverable error',
}


class Model:
    DEFAULT_PORT: int = 10001
    DEFAULT_TIMEOUT: float = 5.0

    def __init__(self) -> None:
        self._lock = Lock()
        self._sock: Optional[SocketType] = None
        self._term_char = '\n'
        self.defalut_ip_address = self._get_IP_address()

    # --- Connections Methods ---

    @staticmethod
    def _get_IP_address() -> str:
        config_data = h.load_ini()
        ip = h.find_selection(config_data, 'IPAddress', 'IPAddress')
        return ip

    def _send_query(self, query: str) -> str:
        """
        Sends a command query to the HVPS, waits for a response, and handles protocol-level errors.

        Args:
            query (str): The command string to send to the instrument. The termination
                character will be automatically appended if missing.

        Returns:
            str: The decoded and stripped string response from the instrument.
        """
        if not self._sock:
            raise ConnectionError('Socket is not connected')
        # print(f'Command: {query}')
        if not query.endswith(self._term_char):
            query += self._term_char

        with self._lock:
            try:
                self._sock.sendall(query.encode())
                response = self._sock.recv(1024)
                # print(f'Raw response: "{response.decode()}"')
            except socket.error as e:
                raise ConnectionError(f'Socket communication error {str(e)}')

        response_str = response.decode().strip()

        if response_str in ERROR_RESPONSES:
            error_description = ERROR_RESPONSES[response_str]
            raise NegativeAcknowledgementError(
                f'E-Reg returned an error response - "{response_str}": {error_description}'
            )

        return response_str

    def open_connection(
        self,
        ip: str | None = None,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> SocketType | None:
        """
        Establishes a TCP connection to the instrument at the specified IP address and port.

        Args:
            ip (str): The IP address of the instrument. Defaults to `DEFAULT_IP`.
            port (int): The port number to connect to. Defaults to `DEFAULT_PORT`.
            timeout (float): The connection timeout in seconds. Defaults to `DEFAULT_TIMEOUT`.

        Returns:
            SocketType | None: The active socket object if the connection is successful,
                or None if a connection error occurred.
        """
        if not ip:
            ip = self.defalut_ip_address
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(timeout)
            self._sock.connect((ip, port))
            print(f'Socket open at {ip}:{port}')
            return self._sock
        except socket.error as e:
            print(f'Connection error\n\n{str(e)}')
            self._sock = None
            return self._sock

    def close_connection(self) -> None:
        """
        Closes the underlying TCP socket connection to the instrument if one is currently open.
        """
        if self._sock:
            self._sock.close()
            print('Socket closed')
            self._sock = None


class NegativeAcknowledgementError(Exception):
    """Raised when the e-reg responds with an error code."""

    pass


if __name__ == '__main__':
    ereg = Model()
    conn = ereg.open_connection()
    print(conn)
