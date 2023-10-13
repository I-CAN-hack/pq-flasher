## VW PQ35 EPS flasher
This repository conatains tools to reflash a PQ35 VW EPS, it also contains some useful libraries to deal with the TP 2.0 transport layer and abstracts away the KWP2000 diagnsotics protocol.

See the related [blog series](https://blog.willemmelching.nl/carhacking/2022/01/02/vw-part1/) for reference.

## Read this first
 - THIS IS AT YOUR OWN RISK
 - Making changes to your EPS might have unintended consequences. You can lose power steering, or the steering motor may put large amounts of torque on the wheel unexpectedly. Ensure the patches to the calibration values are safe before using.
 - This may brick your EPS. Only attempt this if you're willing to replace the EPS if needed.
 - This was only tested by the author on a 2010 VW Golf with the 2501 FW. Your milage may vary on other firmware versions or cars. There are reports of things working as expected on the 3501 FW.
 - A [comma.ai panda](https://comma.ai/shop/products/panda-obd-ii-dongle) is needed to communicate over CAN, and the latest panda python library needs to be installed (`pip install -r requirements.txt`).

## Procedure
### Dump the existing firmware
Dump the existing firmware + calibration using CCP. Technically it’s possible to use the update files to skip this step, but this ensures the exact same firmware is flashed back. This needs to be done using a direct connection to the EPS, and can’t be done through the OBD-II port since there is a gateway that blocks the CCP addresses. For example, this can be done using a [J533 harness](https://github.com/commaai/openpilot/wiki/VW-J533-%28Gateway%29-Cable).

This step takes about 15 minutes. Store the ouput in a safe location if you ever want to restore the original firmware. The dump script will also output the current firmware version.

```bash
./01_dump.py --bus 0 --output firmware/orig.bin

Connecting using KWP2000...
Reading ecu identification & flash status
ECU identification b'1K0909144E  2501\x00\x00\x00\x00------EPS_ZFLS Kl. 184    '
Flash status b'\x00\x1b\x0f\x00--------.--.--'

Connecting using CCP...
  0%|▏                       | 928/393215 [00:02<16:24, 398.35it/s]
```

### Apply patches
The patching script will change the minimum speed to 0 km/h and HCA timer and fix the necesarry checksums. It verifies it’s patching the right firmware version based on the version string, and checks the existing values before changing them. These patches should be tested on a spare ECU first if you don't want to risk bricking the EPS in your car.

```bash
./02_patcher.py --input firmware/orig.bin --output firmware/patched.bin --version 2501
```

### Flashing
You can choose to flash back the whole firmware, but this is not recommended since this takes about 10 minutes, and can risk bricking the ECU if you apply the wrong patches. By default the flasher script will only overwrite the calibration area that contains the values we actually changed.

#### 2501 FW
```bash
./03_flasher.py --bus 0 --input firmware/patched.bin

[READY TO FLASH]
WARNING! USE AT YOUR OWN RISK! THIS COULD BREAK YOUR ECU AND REQUIRE REPLACEMENT!
before proceeding:
* put vehicle in park, and accessory mode (your engine should not be running)
* ensure battery is fully charged. A full flash can take up to 15 minutes
continue [y/n]y

Connecting...

Entering programming mode
Done. Waiting to reconnect...

Reconnecting...

Reading ecu identification & flash status
ECU identification b'1K0909144Y  2501\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00EPS_ZFLS BB        \x00'
Flash status b'\x00\x1d\x11\x00--------.--.--'

<...>

Transfer data
100%|███████████████████████▌| 4080/4096 [00:06<00:00, 618.70it/s]

<...>
```

#### 3501 FW
The 3501 firmware has two calibration areas, but only the one from `0x5D000` to `0x5DFFF` needs to be reflashed.

```bash
./03_flasher.py --bus 0 --input firmware/patched.bin --start-address 380928 --end-address 385023
```

#### Flash whole file
To flash the whole firmware use:

```bash
./03_flasher.py --bus 0 --input firmware/patched.bin --start-address 40960 --end-address 393215
```

## License
Code in this repository is released under the MIT license.

USING ANYTHING FROM THIS REPOSITY IS AT YOUR OWN RISK!


If you like this kind of projects, consider donating so I can buy more random ECUs:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/X8X17MSBD)
