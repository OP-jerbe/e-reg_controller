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

    @staticmethod
    def _get_IP_address() -> str:
        config_data = h.load_ini()
        ip = h.find_selection(config_data, 'IPAddress', 'IPAddress')
        return ip

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

        if not 0 <= value <= float(self.calibration_pressure):
            raise ValueError(
                f'Invalid fault pressure value. Must be between 0 and {self.calibration_pressure}.'
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
    def samples_taken(self) -> str:
        """
        GETTER: Reads the number of samples taken from the ***defaults*** string.
        """
        defaults: list = self.defaults.split(',')
        return defaults[0]

    @property
    def calibration_pressure(self) -> str:
        """
        GETTER: Reads the calibration pressure from the ***defaults*** string.
        """
        defaults = self.defaults.split(',')
        return defaults[-1]

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

        if not 0 <= value <= float(self.calibration_pressure):
            raise ValueError(
                f'Invalid fault pressure value. Must be between 0 and {self.calibration_pressure}.'
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
        GETTER: Reads the current default time between samples in milliseconds.
        """
        command = 'rsrc'
        return self._send_query(command).replace('rsrr:', '').strip()

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        """
        SETTER: Sets the default time between samples in milliseconds.

        Args:
            value (int): The sample rate in milliseconds.
        """
        if not isinstance(value, int):
            raise ValueError(f'Received {type(value).__name__} but expected int.')

        if not 1 <= value <= 200:
            raise ValueError('Invalid sample rate. Must be between 1 and 200.')

        command = f'ssrc:{value}'
        self._send_query(command)

    @property
    def metadata(self) -> str:
        """
        GETTER: Reads the metadata from the device in the form
            [serialNumber], [softwareVersion], [pcBoardRev]
        """
        command = 'stc'
        return self._send_query(command).replace('str:', '').strip()

    @property
    def serial_number(self) -> str:
        """
        GETTER: Reads the serial number from the metadata.
        """
        metadata = self.metadata.split(', ')
        return metadata[0]

    @property
    def software_ver(self) -> str:
        """
        GETTER: Reads the software version from the metadata.
        """
        metadata = self.metadata.split(', ')
        return metadata[1]

    @property
    def pc_board_rev(self) -> str:
        """
        GETTER: Reads the PC board rev from the metadata.
        """
        metadata = self.metadata.split(', ')
        return metadata[-1]

    def send_buffer(self) -> str:
        """
        Reads the sample buffer in a space delimited format where vvv.vv is a value.
            Will return a *send buffer error "sbe"* response if a send buffer request
            is sent to the device before the buffer is full.
        """
        command = 'sbc'
        return self._send_query(command).replace('sbr:', '')

    def start_sampling(self, number: int | None = None) -> None:
        """
        Begin taking a number of samples. If number == None, then sampling will begin
        filling the sampling buffer up to the number set by the ***sszc*** command.

        Args:
            number (int): The number of samples to take. Must be between 1 and 10000
        """
        if number is None:
            command = 'ssc'
            self._send_query(command)
            return

        if not isinstance(number, int):
            raise ValueError(f'Received {type(number).__name__} but expected int.')

        if not 1 <= number <= 10000:
            raise ValueError('Invalid sampling number. Must be between 1 and 10000.')

        command = f'ssc:{number}'
        self._send_query(command)

    def set_sample_size(self, number: int) -> None:
        """
        Sets the number of samples to be stored in the sample buffer.

        Args:
            number (int): The number of samples to be stored in the sample buffer.
        """
        if not isinstance(number, int):
            raise ValueError(f'Received {type(number).__name__} but expected int.')

        if not 1 <= number <= 10000:
            raise ValueError('Invalid sampling number. Must be between 1 and 10000.')

        command = f'sszc:{number}'
        self._send_query(command)

    def test_cont_A(self) -> None:
        """
        Test contact A: close A, open B.
        """
        command = 'tac'
        self._send_query(command)

    def test_cont_B(self) -> None:
        """
        Test contact B: close B, open A.
        """
        command = 'tbc'
        self._send_query(command)

    def test_cont_norm(self) -> None:
        """
        Both contacts are returned to the closed position.
        """
        command = 'tnc'
        self._send_query(command)

    def valves_off(self) -> None:
        """
        Disables both pressure control solenoids.
        """
        command = 'vfc'
        self._send_query(command)

    def valves_on(self) -> None:
        """
        Enables both pressure control solenoids.
        """
        command = 'voc'
        self._send_query(command)


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
    calibration_pressure = ereg.calibration_pressure
    metadata = ereg.metadata
    serial_number = ereg.serial_number
    software_ver = ereg.software_ver
    pc_board_rev = ereg.pc_board_rev
    print(f'{model_num = }')
    print(f'{fault_pressure = }')
    print(f'{heartbeat = }')
    print(f'{defaults = }')
    print(f'{pressure_command = }')
    print(f'{relay_timeout_command = }')
    print(f'{sample_rate = }')
    print(f'{calibration_pressure = }')
    print(f'{metadata = }')
    print(f'{serial_number = }')
    print(f'{software_ver = }')
    print(f'{pc_board_rev = }')
