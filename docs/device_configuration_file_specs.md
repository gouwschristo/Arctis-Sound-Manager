# Device configuration file specifications

Device configuration files are in the YAML file format, as follows:

```yaml
device:
  name: Friendly name # for example: SteelSeries Arctis Nova Pro Wireless
  vendor_id: 0x1038 # Should always be 0x1038, but double check via lsusb
  product_ids: [0x1234] # At least one identifier. Multiple identifiers might apply for different SKUs
  command_padding: # This defines the command's message length and the filler. Typically 64 bytes zero-padded.
    length: 64
    position: end
    filler: 0x00

  command_interface_index: [4, 0] # USB interface number and alternate setting to write commands (status request, device initialization). The former can be analyzed via usb-devices, or by chance. The latter should typically be 0.
  listen_interface_indexes: [4] # USB interface number to listen for the status.

  device_init: # OPTIONAL, the list of commands to initialize the device, for example the GameDAC
    - [0x06, 0x20]
    # ...
    - [0x06, 0xc3, 'settings.wireless_mode']      # Can accept also values from the settings (settings.NAME_OF_THE_SETTING)
    - ['status.request']                          # Can accept the special 'status.request' to send device.status.request's value
    - ['sleep', 500]                              # Not sent: pauses the sequence for N milliseconds, for devices that abandon a mode switch when the next command follows too quickly (Nova Pro Omni)
  status:
    request: 0x06b0 # Message to be sent to request the device's status
    response_mapping: # A list of objects having
                      # (1) starts_with (the message sent from the device must start with the given sequence)
                      # (2, n) the status' name and its position in the message
      - starts_with: 0x0725 # The whole device's message will be 0x0725NN (where NN is the station_volume)
        station_volume: 0x02

      - starts_with: 0x0745 # Message: 0x0745XXYY
        media_mix: 0x02     # ⚠️ media_mix is a special name for the channels mixer, it is required to use this one and not similar ones!
        chat_mix: 0x03      # ⚠️ chat_mix is a special name for the channels mixer, it is required to use this one and not similar ones!

      - starts_with: 0x06b0 # Message: 0x06b0XXYYZZKK...
        bluetooth_powerup_state: 0x02
        bluetooth_auto_mute: 0x03
        bluetooth_power_status: 0x04
        bluetooth_connection: 0x05
        # ...
    representation:      # Categorization and ordering
      category1:         # Translation in [status] section of language file
        - station_volume # List of settings that apply to the category
        - station_charge # If you want to omiss one or more settings in the representation, it's ok
  
  online_status: # OPTIONAL. Used to detect whether the device is connected AND online (useful for wireless devices). If not defined, it will be considered always online if connected via USB
    status_variable: status_variable_to_check_against     # The settings variable's name
    online_value: status_variable's_mapped_value_to_check # The (mapped) variable's value

  settings: # OPTIONAL section
    microphone:                                # Settings section
      mic_volume:                              # Setting's name
        type: slider                           # Setting's type
        default: 0x0a                          # Setting's default value
        update_sequence: [0x06, 0x37, 'value'] # 'value' is a special token replaced with the setting's value at runtime
        min: 0x01                              # Type-specific parameter
        max: 0x0a                              # Type-specific parameter
        step: 1                                # Type-specific parameter
        min_label: mic_muted                   # Type-specific parameter
        max_label: perc_100                    # Type-specific parameter
    another_section:
      another_setting:
        type: ...

  status_parse:               # Each status found in device.status.response_mapping[n] requires a counterpart in this section
    station_volume:
      type: percentage
      perc_min: -56
      perc_max: 0
    media_mix:
      type: percentage
      perc_min: 0
      perc_max: 100
    # ...

```

⚠️ As highlighted in the example above, `media_mix` and `chat_mix` status entries are key to the mixer management. Please avoid using different names, like `game_mix` in order to enable proper channels mixing.

⚠️ The `status_parse` section of `media_mix` and `chat_mix` requires the values to be normalized between 0 and 100.

## YAML's device.hardware_eq section

OPTIONAL. How the custom EQ reaches the headset's own equaliser, for models that have one ASM can
drive. Omit the section entirely when the model has none — the curve then stays software-side and
neither the GUI nor `asm-cli tools read-hardware-eq` offers a hardware one.

```yaml
hardware_eq:
  format: parametric            # Encoder name from hardware_eq.ENCODERS, for families whose curve is a
                                # parametric description over several frames. Omit for families that
                                # take one command of flat gain bytes
  band_command: 0x33            # Opcode of the band frame (parametric families)
  bt_band_command: 0x34         # OPTIONAL: the same frame for the Bluetooth slot, for families that
                                # store one curve per radio mode. Omit ⇒ a write for connection 0x01 is
                                # refused rather than aimed at the live 2.4 GHz curve
  name_command: 0xa5            # Opcode of the preset-name frame (parametric families)
  bands_carry_connection: false # Whether the band frame repeats connection_type after the opcode
  gain_encoding: offset_binary  # How a band's gain byte is written, in both directions:
                                # decibel_signed (0 dB = 0x00) | offset_binary (0 dB = 0x14)
  frame_delay_ms: 600           # Gap between the name frame and the band frame, for devices that
                                # abandon the curve when they follow too closely
  band_layout: graphic          # How ASM's sliders become bands: graphic | shelving
  range_db: 10                  # Gain the on-device curve reaches either way
  zero_at: 20                   # Firmware value standing for 0 dB
  feature_report_size: 0        # Non-zero for families whose curve goes out as one HIDFEATURE chunk
  readback:                     # OPTIONAL: opcodes to read the stored curve back
    band_query: 0x20            # Curve read (0x32 on most parametric families)
    bt_band_query: 0x22         # OPTIONAL: a separate read for the Bluetooth slot
    name_query: 0xa6            # Preset-name read
    band_start: 1               # Offset of band 1 in the reply (0x32 echoes connection_type ⇒ 2)
    bt_band_start: 2            # OPTIONAL: same offset for bt_band_query, when it differs
```

⚠️ The read-back defaults describe the `0x32` reply. A family whose reply differs must set
`band_start`: the wrong offset still decodes into ten plausible-looking bands (32 Hz/LowShelf/−5.0 dB
reads as 1024 Hz/type 10/−12.2 dB at offset 2), so it must come from a reply seen on the hardware,
never by analogy with a sibling family. The Bluetooth reply can sit at a different offset from the
2.4 GHz one — on a Nova 5, `0x22` echoes `connection_type` and `0x20` does not, and decoding `0x22` at
offset 1 returns ten bands of −9.5 dB instead of the stored curve — so `bt_band_start` names it
separately rather than assuming the two frames share a layout. `gain_encoding` is shared with the write
path: a family that stored one encoding and reported the other would round-trip into a curve nobody
asked for.

## YAML's device.settings.[section].[setting] types

Arctis Sound Manager supports out of the box the following settings. Additional types need to be implemented in the code.

```yaml
# Linear multi-value setting (for example 1..n)
type: slider
min: int                               # the minimum valid value
max: int                               # the maximum valid valud
step: 1                                # the number each step sums to the next one (ex. min 1, max 5, step 2; values: 1, 3, 5)
min_label: slider_setting_min          # As found in the language ini file
max_label: slider_setting_max          # As found in the language ini file
default: 0x0a                          # The value set if none was before
update_sequence: [0x06, 0x37, 'value'] # The setting's command update sequence
values_mapping:                        # OPTIONAL: if the slider needs different representation of the values
  0: off                               # Labels as found in [settings_values]
  1: low
  2: medium
  3: high
```

```yaml
# Boolean values (with custom on/off values and labels)
type: toggle
values:
  off: 0x00                            # Value in the "off" position
  on: 0x01                             # Value in the "on" position
  off_label: high                      # As found in the language ini file
  on_label: low                        # As found in the language ini file
default: 0x01                          # The value set if none was before
update_sequence: [0x06, 0x37, 'value'] # The setting's command update sequence
```

```yaml
# Drop-downs
type: select
default: null
options_source: pulse_audio_devices                # pulse_audio_devices only for now
options_mapping: { value: id, label: description } # Depends on options_source. "pulse_audio_devices": id and description only for now
update_sequence: [0x06, 0x37, 'value']             # The setting's command update sequence
```

## YAML's device.status_parse.[status_name] types

Arctis Sound Manager supports out of the box the following status types. Additional types need to be implemented in the code.

To add a new parser, define the function in the [status_parser_fn.py](./src/arctis_sound_manager/status_parser_fn.py) file and add the tests in the [relative file](./tests/test_status_parser_fn.py). New functions will be added to the application automatically.

```yaml
# Percentage (0-100%)
type: percentage
perc_min: -56    # The absolute value of 0%
perc_max: 0      # The absolute value of 100%
```

```yaml
# Togglable (on/off)
type: on_off
off: 0x00       # The value to represent the off status
on: 0x01        # The value to represent the on status
```

```yaml
# Value (int) to string (label)
type: int_str_mapping
values:
  0x00: off    # Value: label (label as found in the language ini file)
  0x01: -12db
  0x02: on
  ...
```

```yaml
# Value (int) to mapped int
type: int_int_mapping
values:
  0x00: 0 
  0x01: 1
  0x02: 5
  ...
```
