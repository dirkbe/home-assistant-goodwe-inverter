import io
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Tuple, Optional

from .protocol import ProtocolCommand


class SensorKind(Enum):
    """
    Enumeration of sensor kinds.

    Possible values are:
    PV - photo-voltaic (e.g. dc voltage of pv panels)
    AC - grid side (e.g. ac voltage of grid connected output)
    UPS - ups/eps/backup side (e.g. ac voltage of backup/off-grid connected output)
    BAT - battery (e.g. dc voltage of connected battery pack)
    """

    PV = 1
    AC = 2
    UPS = 3
    BAT = 4


@dataclass
class Sensor:
    """Definition of inverter sensor and its attributes"""

    id_: str
    offset: int
    name: str
    unit: str
    kind: Optional[SensorKind]

    def read(self, data: io.BytesIO):
        """Read the sensor value from data"""
        raise NotImplementedError()


class Inverter:
    """
    Common superclass for various inverter models implementations.
    Represents the inverter state and its basic behavior
    """

    def __init__(
            self,
            host: str,
            port: int,
            timeout: int = 2,
            retries: int = 3,
            model_name: str = "",
            serial_number: str = "",
            software_version: str = "",
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.model_name = model_name
        self.serial_number = serial_number
        self.software_version = software_version

    async def _read_from_socket(self, command: ProtocolCommand) -> bytes:
        return await command.execute(self.host, self.port, self.timeout, self.retries)

    async def read_device_info(self):
        """
        Request the device information from the inverter.
        The inverter instance variables will be loaded with relevant data.
        """
        raise NotImplementedError()

    async def read_runtime_data(self, include_unknown_sensors: bool = False) -> Dict[str, Any]:
        """
        Request the runtime data from the inverter.
        Answer dictionary of individual sensors and their values.
        List of supported sensors (and their definitions) is provided by sensors() method.

        If include_unknown_sensors parameter is set to True, return all runtime values,
        including those "xx*" sensors whose meaning is not yet identified.
        """
        raise NotImplementedError()

    async def read_settings_data(self) -> Dict[str, Any]:
        """
        Request the settings data from the inverter.
        Answer dictionary of individual settings and their values.
        List of supported settings (and their definitions) is provided by settings() method.
        """
        raise NotImplementedError()

    async def send_command(
            self, command: bytes, validator: Callable[[bytes], bool] = lambda x: True
    ) -> bytes:
        """
        Send low level udp command (as bytes).
        Answer command's raw response data.
        """
        return await self._read_from_socket(ProtocolCommand(command, validator))

    async def set_work_mode(self, work_mode: int):
        """
        BEWARE !!!
        This method modifies inverter operational parameter accessible to installers only.
        Use with caution and at your own risk !

        Set the inverter work mode
        0 - General mode
        1 - Off grid mode
        2 - Backup mode
        """
        raise NotImplementedError()

    async def set_ongrid_battery_dod(self, ongrid_battery_dod: int):
        """
        BEWARE !!!
        This method modifies On-Grid Battery DoD parameter accessible to installers only.
        Use with caution and at your own risk !

        Set the On-Grid Battery DoD
        0% - 89%
        """
        raise NotImplementedError()

    @classmethod
    def sensors(cls) -> Tuple[Sensor, ...]:
        """
        Return tuple of sensor definitions
        """
        raise NotImplementedError()

    @classmethod
    def settings(cls) -> Tuple[Sensor, ...]:
        """
        Return tuple of settings definitions
        """
        raise NotImplementedError()

    @staticmethod
    def _map_response(resp_data: bytes, sensors: Tuple[Sensor, ...], incl_xx: bool = True) -> Dict[str, Any]:
        """Process the response data and return dictionary with runtime values"""
        with io.BytesIO(resp_data) as buffer:
            result = {}
            for sensor in sensors:
                if incl_xx or not sensor.id_.startswith("xx"):
                    result[sensor.id_] = sensor.read(buffer)
            return result