from _sx126x import *
from sx126x import SX126X

_SX126X_PA_CONFIG_SX1268 = const(0x00)

class SX1268(SX126X):
    TX_DONE = SX126X_IRQ_TX_DONE
    RX_DONE = SX126X_IRQ_RX_DONE
    ERROR = ERROR

    def __init__(self, cs, irq, rst, gpio, clk='P10', mosi='P11', miso='P14'):
        super().__init__(cs, irq, rst, gpio, clk, mosi, miso)

    def begin(self, freq=434.0, bw=125.0, sf=9, cr=7, syncWord=SX126X_SYNC_WORD_PRIVATE,
              power=14, currentLimit=60.0, preambleLength=8, tcxoVoltage=1.6, useRegulatorLDO=False,
              trigger=False):
        state = super().begin(bw, sf, cr, syncWord, currentLimit, preambleLength, tcxoVoltage, useRegulatorLDO)
        ASSERT(state)

        state = self.setFrequency(freq)
        ASSERT(state)

        state = self.setOutputPower(power)
        ASSERT(state)

        state = super().fixPaClamping()
        ASSERT(state)

        state = self.setTrigger(trigger)

        return state

    def beginFSK(self, freq=434.0, br=48.0, freqDev=50.0, rxBw=156.2, power=14, currentLimit=60.0,
                 preambleLength=16, dataShaping=0.5, tcxoVoltage=1.6, useRegulatorLDO=False,
                 trigger=False):
        state = super().beginFSK(br, freqDev, rxBw, currentLimit, preambleLength, dataShaping, tcxoVoltage, useRegulatorLDO)
        ASSERT(state)

        state = self.setFrequency(freq)
        ASSERT(state)

        state = self.setOutputPower(power)
        ASSERT(state)

        state = super().fixPaClamping()
        ASSERT(state)

        state = self.setTrigger(trigger)

        return state

    def setFrequency(self, freq, calibrate=True):
        if freq < 410.0 or freq > 810.0:
            return ERR_INVALID_FREQUENCY

        state = ERR_NONE

        if calibrate:
            data = bytearray(2)
            if freq > 770.0:
                data[0] = SX126X_CAL_IMG_779_MHZ_1
                data[1] = SX126X_CAL_IMG_779_MHZ_2
            elif freq > 460.0:
                data[0] = SX126X_CAL_IMG_470_MHZ_1
                data[1] = SX126X_CAL_IMG_470_MHZ_2
            else:
                data[0] = SX126X_CAL_IMG_430_MHZ_1
                data[1] = SX126X_CAL_IMG_430_MHZ_2
            state = super().calibrateImage(data)
            ASSERT(state)

        return super().setFrequencyRaw(freq)

    def setOutputPower(self, power):
        if not ((power >= -9) and (power <= 22)):
            return ERR_INVALID_OUTPUT_POWER

        ocp = bytearray(1)
        ocp_mv = memoryview(ocp)
        state = super().readRegister(SX126X_REG_OCP_CONFIGURATION, ocp_mv, 1)
        ASSERT(state)

        state = super().setPaConfig(0x04, _SX126X_PA_CONFIG_SX1268)
        ASSERT(state)

        state = super().setTxParams(power)
        ASSERT(state)

        return super().writeRegister(SX126X_REG_OCP_CONFIGURATION, ocp, 1)

    def setTrigger(self, trigger, callback=None):
        self.trigger = trigger
        if self.trigger:
            state = super().startReceive()
            ASSERT(state)
            if callback != None:
                super().setDio1Action(self._onTX, callback)
            return state
        else:
            state = super().standby()
            ASSERT(state)
            super().clearDio1Action()
            return state   

    def recv(self, len_=0):
        if self.trigger:
            return self._readData(len_)
        else:
            return self._receive(len_)

    def send(self, data):
        if self.trigger:
            return self._startTransmit(data)
        else:
            return self._transmit(data)

    def _events(self):
        return super().getIrqStatus()

    def _receive(self, len_=0):
        state = ERR_NONE
        
        length = len_
        
        if len_ == 0:
            length = SX126X_MAX_PACKET_LENGTH

        data = bytearray(length)
        data_mv = memoryview(data)

        try:
            state = super().receive(data_mv, length)
        except AssertionError as e:
            state = list(ERROR.keys())[list(ERROR.values()).index(str(e))]

        if state == ERR_NONE:
            if len_ == 0:
                length = super().getPacketLength(False)
                data = data[:length]

        else:
            return b'', state

        return  bytes(data), state

    def _transmit(self, data):
        if isinstance(data, bytes) or isinstance(data, bytearray):
            pass
        else:
            return 0, ERR_INVALID_PACKET_TYPE

        state = super().transmit(data, len(data))
        return len(data), state

    def _readData(self, len_=0):
        state = ERR_NONE

        length = super().getPacketLength()

        if len_ < length and len_ != 0:
            length = len_

        data = bytearray(length)
        data_mv = memoryview(data)

        try:
            state = super().readData(data_mv, length)
        except AssertionError as e:
            state = list(ERROR.keys())[list(ERROR.values()).index(str(e))]

        ASSERT(super().startReceive())

        if state == ERR_NONE:
            return bytes(data), state

        else:
            return b'', state

    def _startTransmit(self, data):
        if isinstance(data, bytes) or isinstance(data, bytearray):
            pass
        else:
            return 0, ERR_INVALID_PACKET_TYPE

        state = super().startTransmit(data, len(data))
        return len(data), state

    def _onTX(self, callback):
        events = self._events()
        if events & self.TX_DONE:
            super().startReceive()
        callback(events)
