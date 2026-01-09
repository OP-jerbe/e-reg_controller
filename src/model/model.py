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
        self.calibrated_pressure = self._get_calibrated_pressure()

    @staticmethod
    def _get_IP_address() -> str:
        config_data = h.load_ini()
        ip = h.find_selection(config_data, 'IPAddress', 'IPAddress')
        return ip

    @staticmethod
    def _get_calibrated_pressure() -> int:
        config_data = h.load_ini()
        calibrated_pressure = h.find_selection(
            config_data, 'CalibratePressure', 'Pressure'
        )
        return int(calibrated_pressure)

    # --- Connections Methods ---

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

    # --- Read Commands ---

    @property
    def model_num(self) -> str:
        """
        GETTER: Reads the model number of the device.
        """
        command = 'mnc'
        return self._send_query(command).replace('mnr:', '').strip()

    @property
    def fault_pressure(self) -> str:
        """
        GETTER: Reads the current default fault pressure setting in psig.
        """
        command = 'rfpc'
        return self._send_query(command).replace('rfpr:', '').strip()

    @fault_pressure.setter
    def fault_pressure(self, value: int) -> None:
        """
        SETTER: Sets the default fault pressure setting.

        Args:
            value (int): The pressure setting in psig the device goes to if there is a fault or power loss.
                Must be be between 0 and the calibrated pressure (set in config.ini file).
        """
        if not isinstance(value, int):
            raise ValueError(f'Received {type(value).__name__} but expected int.')

        if not 0 <= value <= self.calibrated_pressure:
            raise ValueError(
                f'Invalid fault pressure value. Must be between 0 and {self.calibrated_pressure}.'
            )

        command = f'sfpc:{value}'
        self._send_query(command)

    @property
    def heartbeat(self) -> str:
        """
        GETTER: Reads the current default heartbeat timer setting.
        """
        command = 'rhbc'
        return self._send_query(command).replace('rhbr:', '').strip()

    @heartbeat.setter
    def heartbeat(self, value: int) -> None:
        """
        SETTER: Sets the default heartbeat timer setting.

        Args:
            value (int): Timeout setting in milliseconds. Must be between `50-65000` or `0` to disable.
        """
        if not isinstance(value, int):
            raise ValueError(f'Received {type(value).__name__} but expected int.')

        if not 50 <= value <= 65000 or value != 0:
            raise ValueError(
                'Invalid heartbeat value. Must be `0` to disable or set between `50-65000`.'
            )
            return
        command = f'shbc:{value}'
        self._send_query(command)

    @property
    def defaults(self) -> str:
        """
        GETTER: Reads current device defaults in the form
            [samplesTaken],[sampleRate],[heartBeatTime],[faultPressure],[relayFaultTime],[CalibrationPressure]
        """
        command = 'rdc'
        return self._send_query(command).replace('rdr:', '').strip()

    @property
    def pressure(self) -> str:
        """
        GETTER: Reads the current output pressure value.
        """
        command = 'rpc'
        return self._send_query(command).replace('rpr:', '').strip()

    @pressure.setter
    def pressure(self, value: int) -> None:
        """
        SETTER: Sets the output pressure setting.

        Args:
            value (int): The pressure setting in psig.
                Must be between 0 and the calibrated pressure (set in the config.ini file).
        """
        if not isinstance(value, int):
            raise ValueError(f'Received {type(value).__name__} but expected int.')

        if not 0 <= value <= self.calibrated_pressure:
            raise ValueError(
                f'Invalid fault pressure value. Must be between 0 and {self.calibrated_pressure}.'
            )

        command = f'spc:{value}'
        self._send_query(command)

    @property
    def relay_timeout(self) -> str:
        """
        GETTER: Reads the current relay timout command in milliseconds.
        """
        command = 'rrtc'
        return self._send_query(command).replace('rrtr:', '')

    @relay_timeout.setter
    def relay_timeout(self, value: int) -> None:
        """
        SETTER: Sets the relay timeout command.

        Args:
            value (int): The timeout setting in milliseconds
        """
        if not isinstance(value, int):
            raise ValueError(f'Received {type(value).__name__} but expected int.')

        if not 0 <= value <= 65000:
            raise ValueError('Invalid relay timeout value. Must be between 0 and 65000')

        command = f'srtc:{value}'
        self._send_query(command)

    @property
    def sample_rate(self) -> str:
        """
        GETTER: Reads the current default sample rate in milliseconds/sample.
        """
        command = 'rsrc'
        return self._send_query(command).replace('rsrr:', '').strip()

    def send_buffer(self) -> str:
        """
        GETTER: Reads the sample buffer in a space delimited format where vvv.vv is a value.
            Will return a *send buffer error "sbe"* response if a send buffer request
            is sent to the device before the buffer is full.
        """
        command = 'sbc'
        return self._send_query(command).replace('sbr:', '')


class NegativeAcknowledgementError(Exception):
    """Raised when the e-reg responds with an error code."""

    pass


if __name__ == '__main__':
    ereg = Model()
    ereg.open_connection()
    model_num = ereg.model_num
    fault_pressure = ereg.fault_pressure
    heartbeat = ereg.heartbeat
    defaults = ereg.defaults
    pressure_command = ereg.pressure
    relay_timeout_command = ereg.relay_timeout
    sample_rate = ereg.sample_rate
    buffer = ereg.send_buffer()
    print(f'{model_num = }')
    print(f'{fault_pressure = }')
    print(f'{heartbeat = }')
    print(f'{defaults = }')
    print(f'{pressure_command = }')
    print(f'{relay_timeout_command = }')
    print(f'{sample_rate = }')
    print(f'{buffer = }')

    # setters
    ereg.heartbeat = 20
    print(f'{ereg.heartbeat = }')
